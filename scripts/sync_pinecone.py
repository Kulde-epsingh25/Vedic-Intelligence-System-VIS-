"""
sync_pinecone.py
================
Embeds all verses from the database and syncs them to Pinecone serverless vector index.
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from pinecone import Pinecone
from database.local_db import get_connection
from pipeline.embedder import Embedder

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "vis-verses")

print("Connecting to Pinecone...")
pc = Pinecone(api_key=api_key)
idx = pc.Index(index_name)

print("Loading embedding model...")
embedder = Embedder()

conn = get_connection()
c = conn.cursor()
c.execute("SELECT * FROM verses")
rows = [dict(r) for r in c.fetchall()]

vectors_to_upsert = []
print(f"Embedding and upserting {len(rows)} verses into Pinecone index '{index_name}'...")

for v in rows:
    text_to_embed = f"{v['iast']} {v['translation_en']}"
    vector = embedder.embed_text(text_to_embed)
    vectors_to_upsert.append({
        "id": v["verse_id"],
        "values": vector,
        "metadata": {
            "verse_id": v["verse_id"],
            "source_text_id": v["source_text_id"],
            "devanagari": v["devanagari"],
            "iast": v["iast"],
            "translation_en": v.get("translation_en", ""),
            "era": v.get("era", "")
        }
    })

idx.upsert(vectors=vectors_to_upsert)
print(f"SUCCESS: Upserted {len(vectors_to_upsert)} vectors to Pinecone!")
stats = idx.describe_index_stats()
print("Pinecone index stats:", stats)
conn.close()
