# Founding Data Engineer: AI-Driven Marketing Platform

[cite_start]This repository is my submission for the Founding Data Engineer take-home assignment[cite: 1]. [cite_start]It implements a modular, multi-database data platform designed to power an AI-driven marketing personalization system[cite: 4].

[cite_start]The solution includes a batch data pipeline (using Prefect) to ingest and process data, a set of specialized databases (MongoDB, Milvus, Neo4j, Redis, and SQLite), and a low-latency hybrid retrieval API (using FastAPI) to serve personalized recommendations[cite: 13].

## Tech Stack

* [cite_start]**Orchestration:** Prefect (for pipeline DAGs) [cite: 73]
* [cite_start]**API:** FastAPI (for the retrieval API) [cite: 48, 83]
* [cite_start]**Databases:** [cite: 10, 72]
    * [cite_start]**Document Store (MongoDB):** Stores raw conversation text and metadata[cite: 41].
    * [cite_start]**Vector DB (Milvus):** Stores 384-dim embeddings for similarity search[cite: 43].
    * [cite_start]**Graph DB (Neo4j):** Maps relationships between users, campaigns, and intents[cite: 44].
    * [cite_start]**Cache (Redis):** Caches final recommendations to reduce latency[cite: 28].
    * [cite_start]**Analytics DB (SQLite):** A mock for BigQuery; stores aggregated metrics for ranking[cite: 45].
* [cite_start]**Embeddings:** `sentence-transformers` (Hugging Face) [cite: 74]
* [cite_start]**Infrastructure:** Docker & Docker Compose [cite: 75]

## How to Run

This project is fully containerized with Docker.

**Prerequisites:** Docker and Docker Compose must be installed.

### 1. (Optional) Clean Previous Runs

If you have run this project before, run this command to start with a clean slate (this will delete all old data volumes).

```bash
docker-compose down -v --remove-orphans