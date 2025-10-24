# Founding Data Engineer: AI-Driven Marketing Platform

This repository is my submission for the Founding Data Engineer take-home assignment. It implements a modular, multi-database data platform designed to power an AI-driven marketing personalization system.

The solution includes a batch data pipeline (using Prefect) to ingest and process data, a set of specialized databases (MongoDB, Milvus, Neo4j, Redis, and SQLite), and a low-latency hybrid retrieval API (using FastAPI) to serve personalized recommendations.

## Tech Stack

* **Orchestration:** Prefect (for pipeline DAGs) * **API:** FastAPI (for the retrieval API) * **Databases:**     * **Document Store (MongoDB):** Stores raw conversation text and metadata.
    * **Vector DB (Milvus):** Stores 384-dim embeddings for similarity search.
    * **Graph DB (Neo4j):** Maps relationships between users, campaigns, and intents.
    * **Cache (Redis):** Caches final recommendations to reduce latency.
    * **Analytics DB (SQLite):** A mock for BigQuery; stores aggregated metrics for ranking.
* **Embeddings:** `sentence-transformers` (Hugging Face) * **Infrastructure:** Docker & Docker Compose 
## How to Run

This project is fully containerized with Docker.

**Prerequisites:** Docker and Docker Compose must be installed.

### 1. (Optional) Clean Previous Runs

If you have run this project before, run this command to start with a clean slate (this will delete all old data volumes).

```bash
docker-compose down -v --remove-orphans