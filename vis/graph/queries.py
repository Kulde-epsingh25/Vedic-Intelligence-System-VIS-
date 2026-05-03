"""
Graph query module for Neo4j cypher queries.

This module provides a library of common queries for graph traversal,
relationship analysis, and subgraph extraction.
"""

from typing import List, Optional, Dict
from loguru import logger


class GraphQuery:
    """Query and traverse the Neo4j knowledge graph."""

    def __init__(self):
        """
        Initialize GraphQuery with Neo4j connection.

        Example:
            >>> query = GraphQuery()
            >>> relations = query.get_character_relations("rama")
        """
        try:
            from py2neo import Graph
            import os

            neo4j_uri = os.getenv("NEO4J_URI")
            neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD")

            if not neo4j_uri or not neo4j_password:
                raise ValueError("NEO4J_URI and NEO4J_PASSWORD must be set")

            self.graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_password))
            logger.info("Neo4j connection established for queries")

        except ImportError:
            logger.error("py2neo library not installed")
            raise ImportError("Install via: pip install py2neo")
        except Exception as e:
            logger.error(f"Error connecting to Neo4j: {e}")
            raise

    def get_character_relations(self, char_id: str) -> Dict:
        """
        Get all relationships for a character.

        Args:
            char_id: Character identifier

        Returns:
            Dictionary with relationship types and target characters

        Example:
            >>> query = GraphQuery()
            >>> relations = query.get_character_relations("arjuna")
            >>> print(relations)
        """
        try:
            cypher = """
            MATCH (c:Character {char_id: $char_id})-[r]->(target)
            RETURN type(r) as relation_type, target.char_id as target_id, 
                   target.name_sa as target_name, count(*) as count
            """

            results = self.graph.run(cypher, {"char_id": char_id}).data()

            relations_dict = {}
            for result in results:
                rel_type = result.get("relation_type")
                target = {
                    "id": result.get("target_id"),
                    "name": result.get("target_name"),
                }

                if rel_type not in relations_dict:
                    relations_dict[rel_type] = []

                relations_dict[rel_type].append(target)

            logger.debug(f"Found {len(relations_dict)} relation types for {char_id}")
            return relations_dict

        except Exception as e:
            logger.error(f"Error getting relations for {char_id}: {e}")
            return {}

    def find_path(self, from_char: str, to_char: str, max_hops: int = 5) -> Optional[List]:
        """
        Find shortest path between two characters.

        Args:
            from_char: Source character ID
            to_char: Target character ID
            max_hops: Maximum path length

        Returns:
            List of character IDs representing the path, or None

        Example:
            >>> query = GraphQuery()
            >>> path = query.find_path("arjuna", "krishna")
            >>> print(path)  # ["arjuna", "krishna"]
        """
        try:
            cypher = f"""
            MATCH path = shortestPath(
                (a:Character {{char_id: $from_char}}) -[*..{max_hops}]- 
                (b:Character {{char_id: $to_char}})
            )
            RETURN [node in nodes(path) | node.char_id] as path_ids
            LIMIT 1
            """

            result = self.graph.run(
                cypher,
                {"from_char": from_char, "to_char": to_char}
            ).data()

            if result and len(result) > 0:
                path = result[0].get("path_ids", [])
                logger.debug(f"Found path from {from_char} to {to_char}: {path}")
                return path

            logger.debug(f"No path found between {from_char} and {to_char}")
            return None

        except Exception as e:
            logger.error(f"Error finding path: {e}")
            return None

    def get_concept_network(self, concept_id: str, depth: int = 2) -> Dict:
        """
        Get all concepts within N hops of a concept.

        Args:
            concept_id: Root concept ID
            depth: Number of hops

        Returns:
            Dictionary with nodes and edges

        Example:
            >>> query = GraphQuery()
            >>> network = query.get_concept_network("dharma", depth=2)
        """
        try:
            cypher = f"""
            MATCH (c:Concept {{concept_id: $concept_id}}) -[*..{depth}]- (neighbor:Concept)
            RETURN distinct neighbor.concept_id as concept_id, 
                   neighbor.name_sa as name, 
                   neighbor.category as category
            """

            results = self.graph.run(cypher, {"concept_id": concept_id}).data()

            network = {
                "root": concept_id,
                "depth": depth,
                "concepts": results,
                "count": len(results),
            }

            logger.debug(f"Found {len(results)} concepts within {depth} hops")
            return network

        except Exception as e:
            logger.error(f"Error getting concept network: {e}")
            return {"root": concept_id, "concepts": [], "count": 0}

    def get_character_events(self, char_id: str) -> List[Dict]:
        """
        Get all events involving a character.

        Args:
            char_id: Character identifier

        Returns:
            List of event dictionaries

        Example:
            >>> query = GraphQuery()
            >>> events = query.get_character_events("arjuna")
        """
        try:
            cypher = """
            MATCH (c:Character {char_id: $char_id})
            MATCH (c) -[:PARTICIPATES_IN]-> (e:Event)
            RETURN e.event_id as event_id, e.title_en as title, 
                   e.event_type as type, e.yuga as yuga
            ORDER BY e.sequence_no
            """

            events = self.graph.run(cypher, {"char_id": char_id}).data()
            logger.debug(f"Found {len(events)} events for {char_id}")
            return events

        except Exception as e:
            logger.error(f"Error getting events for {char_id}: {e}")
            return []

    def get_texts_mentioning_concept(self, concept_id: str) -> List[str]:
        """
        Get all source texts that mention a concept.

        Args:
            concept_id: Concept identifier

        Returns:
            List of source text names

        Example:
            >>> query = GraphQuery()
            >>> texts = query.get_texts_mentioning_concept("karma")
        """
        try:
            cypher = """
            MATCH (concept:Concept {concept_id: $concept_id})
            MATCH (concept) -[:APPEARS_IN]-> (text:Text)
            RETURN distinct text.text_id as text_id, text.title as title
            """

            results = self.graph.run(cypher, {"concept_id": concept_id}).data()
            texts = [r.get("title") or r.get("text_id") for r in results]

            logger.debug(f"Found {len(texts)} texts mentioning {concept_id}")
            return texts

        except Exception as e:
            logger.error(f"Error getting texts: {e}")
            return []

    def export_for_d3(self, subgraph: str = "Mahabharata") -> Dict:
        """
        Export subgraph in D3.js force graph format.

        Args:
            subgraph: Subgraph to export (text name)

        Returns:
            Dictionary with nodes and links for D3

        Example:
            >>> query = GraphQuery()
            >>> d3_data = query.export_for_d3("Mahabharata")
            >>> import json
            >>> print(json.dumps(d3_data))
        """
        try:
            # Get nodes
            nodes_cypher = """
            MATCH (c:Character)
            WHERE $subgraph IN c.appears_in
            RETURN c.char_id as id, c.name_sa as name, 
                   c.char_type as type, c.verse_count as size
            """

            nodes_results = self.graph.run(nodes_cypher, {"subgraph": subgraph}).data()
            nodes = [
                {
                    "id": n.get("id"),
                    "name": n.get("name"),
                    "type": n.get("type"),
                    "size": (n.get("size") or 0) + 5,
                }
                for n in nodes_results
            ]

            # Get edges
            edges_cypher = """
            MATCH (a:Character) -[r]-> (b:Character)
            WHERE $subgraph IN a.appears_in AND $subgraph IN b.appears_in
            RETURN a.char_id as source, b.char_id as target, 
                   type(r) as type, count(*) as weight
            """

            edges_results = self.graph.run(edges_cypher, {"subgraph": subgraph}).data()
            links = [
                {
                    "source": e.get("source"),
                    "target": e.get("target"),
                    "type": e.get("type"),
                    "weight": e.get("weight", 1),
                }
                for e in edges_results
            ]

            result = {"nodes": nodes, "links": links}
            logger.debug(f"Exported D3 graph: {len(nodes)} nodes, {len(links)} links")
            return result

        except Exception as e:
            logger.error(f"Error exporting for D3: {e}")
            return {"nodes": [], "links": []}
