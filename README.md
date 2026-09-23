# Vedic Intelligence System (VIS)

An open-source AI & RAG system to ingest, embed, graph, and query ancient Sanskrit texts (Vedas, Upanishads, Puranas, Mahabharata, Ramayana, Darshanas).

---

## Architecture Overview

* **`api/`**: FastAPI REST API service (`main.py`) providing endpoints for queries, verse lookups, and full RAG responses.
* **`ai/`**: Retrieval-Augmented Generation (`rag_chain.py`) using LLM & reranking.
* **`pipeline/`**: Text ingestion, normalization, parsing, science linking, and vector embedding.
* **`vector/`**: Vector database connectors (ChromaDB local and Pinecone cloud).
* **`graph/`**: Knowledge graph loaders for Neo4j Aura (nodes, relationships, and lineage).
* **`database/`**: Relational PostgreSQL / Supabase client and schema definitions.

---

## Quickstart

### 1. Create a Python Virtual Environment
```powershell
# From the VIS directory:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Credentials
Review and edit `.env` with your API keys:
* Supabase (PostgreSQL)
* Neo4j (Graph database)
* Pinecone (Vector cloud) or local ChromaDB
* HuggingFace token

### 4. Run the API Server
```powershell
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
Open interactive docs in browser: `http://localhost:8000/docs`

### 5. Run the Ingestion Pipeline
```powershell
python pipeline/run_pipeline.py
```
