"""
graph/loader.py
===============
Loads all Sanskrit entities (characters, concepts, places, events)
and their relationships into Neo4j Aura as a knowledge graph.
"""

import os
from dataclasses import dataclass
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "password")


@dataclass
class CharNode:
    char_id: str
    name_sa: str
    name_devanagari: str
    name_en: str
    char_type: str
    gender: str
    appears_in: list[str]
    verse_count: int = 0
    attributes: list[str] = None
    description_en: str = ""


@dataclass
class RelEdge:
    char_a: str
    char_b: str
    relation_type: str          # SON_OF / BATTLES / TEACHES etc.
    source_text: str = ""
    source_verse: str = ""
    notes: str = ""


@dataclass
class ConceptNode:
    concept_id: str
    name_sa: str
    name_devanagari: str
    category: str
    definition_en: str
    era: str
    frequency: int = 0


class GraphLoader:
    """
    Loads the Sanskrit knowledge graph into Neo4j Aura.

    Nodes:
        Character, Place, Deity, Concept, Event, Weapon, Herb, Text

    Edges:
        SON_OF, FATHER_OF, MOTHER_OF, MARRIED_TO, BATTLES,
        ALLY_OF, ENEMY_OF, TEACHES, DISCIPLE_OF, CURSED_BY,
        KILLED_BY, MENTIONS, APPEARS_IN, PARALLELS_SCIENCE

    Example:
        >>> g = GraphLoader()
        >>> g.create_indexes()
        >>> g.load_all_characters()
    """

    def __init__(self):
        self.graph = None
        self._connect()

    def _connect(self) -> None:
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASS))
            self.driver.verify_connectivity()
            logger.success(f"Neo4j connected: {NEO4J_URI}")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            logger.info("Start Neo4j: docker run -p 7687:7687 -p 7474:7474 "
                       "-e NEO4J_AUTH=neo4j/password neo4j:latest")
            self.driver = None

    def _run(self, query: str, **params):
        if self.driver is None:
            return []
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def create_indexes(self) -> None:
        """Creates all necessary Neo4j indexes for fast lookup."""
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Character) REQUIRE c.char_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Place) REQUIRE p.place_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Text) REQUIRE t.text_id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (c:Character) ON (c.name_sa)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.category)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.yuga)",
        ]
        for q in queries:
            try:
                self._run(q)
            except Exception as e:
                logger.warning(f"Index creation: {e}")
        logger.success("Neo4j indexes created")

    def load_character(self, char: CharNode) -> None:
        """MERGE a Character node (creates or updates)."""
        self._run("""
            MERGE (c:Character {char_id: $char_id})
            SET c.name_sa = $name_sa,
                c.name_devanagari = $name_devanagari,
                c.name_en = $name_en,
                c.char_type = $char_type,
                c.gender = $gender,
                c.appears_in = $appears_in,
                c.verse_count = $verse_count,
                c.attributes = $attributes,
                c.description_en = $description_en
        """,
            char_id=char.char_id,
            name_sa=char.name_sa,
            name_devanagari=char.name_devanagari,
            name_en=char.name_en,
            char_type=char.char_type,
            gender=char.gender,
            appears_in=char.appears_in,
            verse_count=char.verse_count,
            attributes=char.attributes or [],
            description_en=char.description_en
        )

    def load_relation(self, rel: RelEdge) -> None:
        """Creates a typed relationship between two characters."""
        query = f"""
            MATCH (a:Character {{char_id: $char_a}})
            MATCH (b:Character {{char_id: $char_b}})
            MERGE (a)-[r:{rel.relation_type}]->(b)
            SET r.source_text = $source_text,
                r.source_verse = $source_verse,
                r.notes = $notes
        """
        self._run(query,
            char_a=rel.char_a,
            char_b=rel.char_b,
            source_text=rel.source_text,
            source_verse=rel.source_verse,
            notes=rel.notes
        )

    def load_concept(self, concept: ConceptNode) -> None:
        """MERGE a Concept node."""
        self._run("""
            MERGE (c:Concept {concept_id: $concept_id})
            SET c.name_sa = $name_sa,
                c.name_devanagari = $name_devanagari,
                c.category = $category,
                c.definition_en = $definition_en,
                c.era = $era,
                c.frequency = $frequency
        """, **concept.__dict__)

    def link_verse_to_character(self, verse_id: str, char_id: str,
                                 text_id: str) -> None:
        """Creates (Verse)-[:MENTIONS]->(Character) edge."""
        self._run("""
            MERGE (v:Verse {verse_id: $verse_id})
            MERGE (c:Character {char_id: $char_id})
            MERGE (v)-[:MENTIONS {text: $text_id}]->(c)
        """, verse_id=verse_id, char_id=char_id, text_id=text_id)

    def link_concept_to_science(self, concept_id: str,
                                 modern_concept: str, domain: str,
                                 confidence: float) -> None:
        """Creates (Concept)-[:PARALLELS_SCIENCE]->(ModernConcept) edge."""
        self._run("""
            MERGE (a:Concept {concept_id: $concept_id})
            MERGE (b:ModernConcept {name: $modern_concept, domain: $domain})
            MERGE (a)-[r:PARALLELS_SCIENCE]->(b)
            SET r.confidence = $confidence
        """, concept_id=concept_id, modern_concept=modern_concept,
             domain=domain, confidence=confidence)

    def load_all_characters(self) -> int:
        """
        Loads the complete character roster from all major texts.
        Returns number of characters loaded.
        """
        characters = [
            # MAHABHARATA
            CharNode("yudhishthira", "yudhiṣṭhira", "युधिष्ठिर",
                     "Yudhishthira", "Human", "m",
                     ["MBH", "BG"], 2800, ["eldest Pandava", "dharma-king"],
                     "Eldest of the five Pandava brothers, known for righteousness"),
            CharNode("bhima", "bhīma", "भीम", "Bhima", "Human", "m",
                     ["MBH"], 2200, ["second Pandava", "strongest", "gada-wielder"]),
            CharNode("arjuna", "arjuna", "अर्जुन", "Arjuna", "Human", "m",
                     ["MBH", "BG"], 4200,
                     ["third Pandava", "archer", "Gandiva-wielder", "Nara"],
                     "Greatest archer of his age, hero of the Bhagavad Gita"),
            CharNode("nakula", "nakula", "नकुल", "Nakula", "Human", "m",
                     ["MBH"], 600, ["fourth Pandava", "twin", "horse-expert"]),
            CharNode("sahadeva", "sahadeva", "सहदेव", "Sahadeva", "Human", "m",
                     ["MBH"], 600, ["fifth Pandava", "twin", "astrologer"]),
            CharNode("krishna", "kṛṣṇa", "कृष्ण", "Krishna", "Deity", "m",
                     ["MBH", "BG", "BHAG", "VISH"], 18000,
                     ["Vishnu avatar", "charioteer", "Sudarshana-wielder",
                      "Dwarka-king", "flute-player"],
                     "Avatar of Vishnu, divine guide of Arjuna in the Gita"),
            CharNode("duryodhana", "duryodhana", "दुर्योधन", "Duryodhana",
                     "Human", "m", ["MBH"], 3500,
                     ["eldest Kaurava", "mace-fighter", "prince of Hastinapura"]),
            CharNode("bhishma", "bhīṣma", "भीष्म", "Bhishma", "Human", "m",
                     ["MBH"], 2800, ["grandsire", "Devavrata", "invincible vow"]),
            CharNode("drona", "droṇa", "द्रोण", "Drona", "Human", "m",
                     ["MBH"], 2200, ["military teacher", "brahmin", "acharya"]),
            CharNode("karna", "karṇa", "कर्ण", "Karna", "Human", "m",
                     ["MBH"], 2600, ["Surya's son", "greatest donor", "Suta-putra"]),
            CharNode("dhritarashtra", "dhṛtarāṣṭra", "धृतराष्ट्र",
                     "Dhritarashtra", "Human", "m", ["MBH"], 1800,
                     ["blind king", "father of Kauravas"]),
            CharNode("draupadi", "draupadī", "द्रौपदी", "Draupadi",
                     "Human", "f", ["MBH"], 2100,
                     ["Panchali", "wife of five Pandavas", "agni-born"]),
            CharNode("kunti", "kuntī", "कुन्ती", "Kunti", "Human", "f",
                     ["MBH"], 900, ["mother of Pandavas"]),
            CharNode("vyasa", "vyāsa", "व्यास", "Vyasa", "Rishi", "m",
                     ["MBH", "BHAG", "VISH"], 600,
                     ["author of Mahabharata", "compiler of Vedas"]),
            CharNode("sanjaya", "sañjaya", "सञ्जय", "Sanjaya", "Human", "m",
                     ["MBH", "BG"], 1200, ["narrator", "divine sight granted"]),

            # RAMAYANA
            CharNode("rama", "rāma", "राम", "Rama", "Deity", "m",
                     ["RAM", "BHAG", "GAR"], 24000,
                     ["Vishnu avatar", "Ayodhya-king", "Kodanda-wielder",
                      "Maryada Purushottam"],
                     "Seventh avatar of Vishnu, protagonist of the Ramayana"),
            CharNode("sita", "sītā", "सीता", "Sita", "Human", "f",
                     ["RAM"], 8000, ["Janaka's daughter", "Rama's wife", "earth-born"]),
            CharNode("lakshmana", "lakṣmaṇa", "लक्ष्मण", "Lakshmana",
                     "Human", "m", ["RAM"], 7000, ["Rama's brother", "devoted"]),
            CharNode("hanuman", "hanumān", "हनुमान", "Hanuman", "Deva", "m",
                     ["RAM", "MBH"], 5000,
                     ["Vayu's son", "devotee of Rama", "greatest devotee"]),
            CharNode("ravana", "rāvaṇa", "रावण", "Ravana", "Asura", "m",
                     ["RAM"], 6000, ["Lanka-king", "ten-headed", "Shiva devotee"]),
            CharNode("dasharatha", "daśaratha", "दशरथ", "Dasharatha",
                     "Human", "m", ["RAM"], 1800, ["Ayodhya-king", "Rama's father"]),
            CharNode("vibhishana", "vibhīṣaṇa", "विभीषण", "Vibhishana",
                     "Asura", "m", ["RAM"], 1200, ["Ravana's brother", "Lanka-king"]),

            # VEDIC DEITIES
            CharNode("vishnu", "viṣṇu", "विष्णु", "Vishnu", "Deity", "m",
                     ["RV", "VISH", "BHAG", "MBH", "RAM"], 40000,
                     ["preserver", "Narayana", "ten avatars"]),
            CharNode("shiva", "śiva", "शिव", "Shiva", "Deity", "m",
                     ["SHIV", "MBH", "RV"], 30000,
                     ["destroyer", "Mahadeva", "Nataraja", "Trishula-wielder"]),
            CharNode("brahma", "brahmā", "ब्रह्मा", "Brahma", "Deity", "m",
                     ["BRAH", "MBH", "RAM"], 15000, ["creator", "four-headed"]),
            CharNode("indra", "indra", "इन्द्र", "Indra", "Deity", "m",
                     ["RV", "AV", "MBH"], 12000, ["king of devas", "Vajra-wielder"]),
            CharNode("agni", "agni", "अग्नि", "Agni", "Deity", "m",
                     ["RV", "AV", "YV"], 8000, ["fire deity", "messenger"]),
            CharNode("varuna", "varuṇa", "वरुण", "Varuna", "Deity", "m",
                     ["RV", "AV"], 5000, ["cosmic order", "water deity"]),
            CharNode("saraswati", "sarasvatī", "सरस्वती", "Saraswati",
                     "Deity", "f", ["RV", "AV"], 4000, ["goddess of knowledge"]),
            CharNode("lakshmi", "lakṣmī", "लक्ष्मी", "Lakshmi",
                     "Deity", "f", ["VISH", "BHAG"], 5000,
                     ["goddess of wealth", "Vishnu's consort"]),
            CharNode("parvati", "pārvatī", "पार्वती", "Parvati",
                     "Deity", "f", ["SHIV", "MBH"], 4000,
                     ["Shiva's consort", "Durga", "Kali"]),
            CharNode("durga", "durgā", "दुर्गा", "Durga", "Deity", "f",
                     ["MARK", "SHIV"], 3000, ["warrior goddess", "Mahishasura-slayer"]),
            CharNode("yama", "yama", "यम", "Yama", "Deity", "m",
                     ["RV", "AV", "GAR", "KU"], 3000, ["death deity", "dharma-king"]),
        ]

        for char in characters:
            self.load_character(char)
        logger.success(f"Loaded {len(characters)} characters into Neo4j")
        return len(characters)

    def load_all_relations(self) -> int:
        """Loads all known character relationships."""
        relations = [
            # PANDAVA FAMILY
            RelEdge("yudhishthira", "kunti", "SON_OF", "MBH"),
            RelEdge("bhima", "kunti", "SON_OF", "MBH"),
            RelEdge("arjuna", "kunti", "SON_OF", "MBH"),
            RelEdge("yudhishthira", "bhima", "BROTHER_OF", "MBH"),
            RelEdge("yudhishthira", "arjuna", "BROTHER_OF", "MBH"),
            RelEdge("bhima", "arjuna", "BROTHER_OF", "MBH"),
            RelEdge("arjuna", "nakula", "BROTHER_OF", "MBH"),
            RelEdge("arjuna", "sahadeva", "BROTHER_OF", "MBH"),
            RelEdge("yudhishthira", "draupadi", "MARRIED_TO", "MBH"),
            RelEdge("bhima", "draupadi", "MARRIED_TO", "MBH"),
            RelEdge("arjuna", "draupadi", "MARRIED_TO", "MBH"),
            RelEdge("arjuna", "krishna", "DISCIPLE_OF", "BG",
                    "BG.2.7", "Arjuna asks Krishna for guidance"),
            RelEdge("bhima", "duryodhana", "BATTLES", "MBH"),
            RelEdge("arjuna", "karna", "BATTLES", "MBH"),
            RelEdge("arjuna", "bhishma", "BATTLES", "MBH"),
            RelEdge("drona", "arjuna", "TEACHER_OF", "MBH",
                    notes="Taught archery to Arjuna"),
            RelEdge("drona", "duryodhana", "TEACHER_OF", "MBH"),

            # KAURAVA
            RelEdge("duryodhana", "dhritarashtra", "SON_OF", "MBH"),
            RelEdge("karna", "duryodhana", "ALLY_OF", "MBH"),
            RelEdge("arjuna", "duryodhana", "ENEMY_OF", "MBH"),

            # RAMAYANA
            RelEdge("rama", "dasharatha", "SON_OF", "RAM"),
            RelEdge("lakshmana", "dasharatha", "SON_OF", "RAM"),
            RelEdge("rama", "sita", "MARRIED_TO", "RAM"),
            RelEdge("rama", "lakshmana", "BROTHER_OF", "RAM"),
            RelEdge("rama", "ravana", "BATTLES", "RAM",
                    "RAM_06_yuddha", "Final battle of Ramayana"),
            RelEdge("hanuman", "rama", "ALLY_OF", "RAM",
                    notes="Greatest devotee of Rama"),
            RelEdge("ravana", "sita", "ENEMY_OF", "RAM",
                    notes="Ravana abducted Sita"),
            RelEdge("vibhishana", "ravana", "BROTHER_OF", "RAM"),
            RelEdge("vibhishana", "rama", "ALLY_OF", "RAM"),

            # DIVINE HIERARCHY
            RelEdge("krishna", "vishnu", "ALLY_OF", "BHAG",
                    notes="Krishna is avatar of Vishnu"),
            RelEdge("rama", "vishnu", "ALLY_OF", "RAM",
                    notes="Rama is avatar of Vishnu"),
            RelEdge("brahma", "vishnu", "ALLY_OF", "BHAG"),
            RelEdge("brahma", "shiva", "ALLY_OF", "SHIV"),
            RelEdge("indra", "agni", "ALLY_OF", "RV"),
            RelEdge("indra", "varuna", "ALLY_OF", "RV"),
            RelEdge("saraswati", "brahma", "MARRIED_TO", "BRAH"),
            RelEdge("lakshmi", "vishnu", "MARRIED_TO", "VISH"),
            RelEdge("parvati", "shiva", "MARRIED_TO", "SHIV"),
        ]

        for rel in relations:
            try:
                self.load_relation(rel)
            except Exception as e:
                logger.warning(f"Relation {rel.char_a}→{rel.char_b}: {e}")

        logger.success(f"Loaded {len(relations)} relationships")
        return len(relations)

    def load_all_concepts(self) -> int:
        """Loads Vedic concepts as graph nodes."""
        concepts = [
            ConceptNode("dharma", "dharma", "धर्म", "Philosophy",
                        "Cosmic order, righteousness, duty", "Vedic", 50000),
            ConceptNode("karma", "karma", "कर्म", "Philosophy",
                        "Action and its consequences", "Vedic", 35000),
            ConceptNode("moksha", "mokṣa", "मोक्ष", "Philosophy",
                        "Liberation from the cycle of rebirth", "Upanishadic", 20000),
            ConceptNode("atman", "ātman", "आत्मन्", "Philosophy",
                        "Individual self/soul", "Upanishadic", 25000),
            ConceptNode("brahman", "brahman", "ब्रह्मन्", "Philosophy",
                        "Ultimate reality, cosmic consciousness", "Upanishadic", 30000),
            ConceptNode("maya", "māyā", "माया", "Philosophy",
                        "Illusion, the veil of material reality", "Vedanta", 15000),
            ConceptNode("yoga", "yoga", "योग", "Practice",
                        "Union, discipline, path to liberation", "Classical", 22000),
            ConceptNode("ahimsa", "ahiṃsā", "अहिंसा", "Ethics",
                        "Non-violence, harmlessness", "Classical", 8000),
            ConceptNode("satya", "satya", "सत्य", "Ethics",
                        "Truth, reality", "Vedic", 12000),
            ConceptNode("rita", "ṛta", "ऋत", "Cosmic",
                        "Cosmic order, natural law", "Vedic", 10000),
            ConceptNode("prana", "prāṇa", "प्राण", "Science",
                        "Life force, vital energy", "Vedic", 18000),
            ConceptNode("chakra", "cakra", "चक्र", "Medicine",
                        "Energy centers in the subtle body", "Classical", 5000),
            ConceptNode("kundalini", "kuṇḍalinī", "कुण्डलिनी", "Medicine",
                        "Dormant spiritual energy at the base of spine", "Classical", 3000),
            ConceptNode("paramanu", "paramāṇu", "परमाणु", "Science",
                        "Ultimate indivisible particle (atomic theory)", "Vaisheshika", 500),
            ConceptNode("akasha", "ākāśa", "आकाश", "Cosmology",
                        "Space/ether, fifth element", "Vedic", 8000),
            ConceptNode("satya_yuga", "satyayuga", "सत्ययुग", "Cosmology",
                        "Age of Truth, first and purest cosmic age", "Puranic", 3000),
            ConceptNode("kali_yuga", "kaliyuga", "कलियुग", "Cosmology",
                        "Current dark age, last of four cosmic ages", "Puranic", 5000),
            ConceptNode("ahankara", "ahaṃkāra", "अहंकार", "Philosophy",
                        "Ego, sense of individual identity", "Samkhya", 6000),
            ConceptNode("samsara", "saṃsāra", "संसार", "Philosophy",
                        "Cycle of birth, death and rebirth", "Upanishadic", 10000),
            ConceptNode("varna", "varṇa", "वर्ण", "Social",
                        "Social order (Brahmin/Kshatriya/Vaishya/Shudra)", "Vedic", 8000),
        ]

        for concept in concepts:
            self.load_concept(concept)

        # Link related concepts
        concept_links = [
            ("karma", "dharma"), ("moksha", "karma"), ("moksha", "atman"),
            ("atman", "brahman"), ("brahman", "maya"), ("yoga", "moksha"),
            ("dharma", "ahimsa"), ("ahimsa", "satya"), ("prana", "chakra"),
            ("samsara", "karma"), ("samsara", "moksha"), ("ahankara", "maya"),
        ]
        for a, b in concept_links:
            self._run("""
                MATCH (a:Concept {concept_id: $a}), (b:Concept {concept_id: $b})
                MERGE (a)-[:RELATED_TO]->(b)
            """, a=a, b=b)

        logger.success(f"Loaded {len(concepts)} concepts with links")
        return len(concepts)

    def get_character_graph(self, char_id: str) -> dict:
        """
        Returns full relationship graph for a character.

        Returns:
            dict: {nodes: [...], edges: [...]} for D3.js visualisation
        """
        results = self._run("""
            MATCH (c:Character {char_id: $char_id})-[r]-(other)
            RETURN c, r, other, type(r) as rel_type
            LIMIT 100
        """, char_id=char_id)

        nodes, edges = {}, []
        for record in results:
            c = dict(record["c"])
            o = dict(record["other"])
            rel_type = record["rel_type"]
            nodes[c.get("char_id", "")] = c
            nodes[o.get("char_id", o.get("concept_id", "?"))] = o
            edges.append({
                "source": c.get("char_id", ""),
                "target": o.get("char_id", o.get("concept_id", "?")),
                "type": rel_type
            })

        return {"nodes": list(nodes.values()), "edges": edges}

    def find_path(self, from_char: str, to_char: str) -> list:
        """Finds shortest path between two characters."""
        results = self._run("""
            MATCH p = shortestPath(
                (a:Character {char_id: $from_char})-[*..8]-(b:Character {char_id: $to_char})
            )
            RETURN p, length(p) as hops
        """, from_char=from_char, to_char=to_char)

        paths = []
        for r in results:
            paths.append({"hops": r["hops"], "path": str(r["p"])})
        return paths

    def export_for_d3(self, filter_text: str = None,
                      limit: int = 200) -> dict:
        """
        Exports character graph as D3.js force-graph JSON.
        {nodes: [{id, name, type, size}], links: [{source, target, type}]}
        """
        where = f"WHERE c.appears_in IS NOT NULL AND '{filter_text}' IN c.appears_in" \
                if filter_text else ""
        results = self._run(f"""
            MATCH (c:Character)-[r]-(other:Character)
            {where}
            RETURN c, r, other, type(r) as rel_type
            LIMIT {limit}
        """)

        nodes_map, links = {}, []
        for record in results:
            c = dict(record["c"])
            o = dict(record["other"])
            c_id = c.get("char_id", "")
            o_id = o.get("char_id", "")
            if c_id and c_id not in nodes_map:
                nodes_map[c_id] = {"id": c_id, "name": c.get("name_en", c_id),
                                    "type": c.get("char_type", ""), "size": min(c.get("verse_count", 1), 500)}
            if o_id and o_id not in nodes_map:
                nodes_map[o_id] = {"id": o_id, "name": o.get("name_en", o_id),
                                    "type": o.get("char_type", ""), "size": min(o.get("verse_count", 1), 500)}
            links.append({"source": c_id, "target": o_id, "type": record["rel_type"]})

        return {"nodes": list(nodes_map.values()), "links": links}

    def close(self):
        if self.driver:
            self.driver.close()
