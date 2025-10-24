Here is the complete `README.md` file.

This version is updated to reflect our final change: using the **1024-dim** embedding model (`all-roberta-large-v1`) to match the assignment's PDF.


# Founding Data Engineer: AI-Driven Marketing Platform

This repository is my submission for the Founding Data Engineer take-home assignment. It implements a modular, multi-database data platform designed to power an AI-driven marketing personalization system.

The solution includes a batch data pipeline (using Prefect) to ingest and process data, a set of specialized databases (MongoDB, Milvus, Neo4j, Redis, and SQLite), and a low-latency hybrid retrieval API (using FastAPI) to serve personalized recommendations.

## Tech Stack

* **Orchestration:** Prefect (for pipeline DAGs)
* **API:** FastAPI (for the retrieval API)
* **Databases:**
    * **Document Store (MongoDB):** Stores raw conversation text and metadata.
    * **Vector DB (Milvus):** Stores **1024-dim** embeddings for similarity search.
    * **Graph DB (Neo4j):** Maps relationships between users, campaigns, and intents.
    * **Cache (Redis):** Caches final recommendations to reduce latency.
    * **Analytics DB (SQLite):** A mock for BigQuery; stores aggregated metrics for ranking.
* **Embeddings:** `sentence-transformers/all-roberta-large-v1` (Hugging Face)
* **Infrastructure:** Docker & Docker Compose

## How to Run

This project is fully containerized with Docker.

**Prerequisites:** Docker and Docker Compose must be installed.

### 1. (Optional) Clean Previous Runs

If you have run this project before, run this command to start with a clean slate (this will delete all old data volumes).

```bash
docker-compose down -v --remove-orphans
````

### 2\. Build and Start All Services

This command builds the custom `api` and `pipeline_runner` images and starts all 7 database containers and the API service in the background.

```bash
# Build the images (first time or after code changes)
docker-compose build

# Start all services
docker-compose up -d
```

### 3\. Run the Data Pipeline

With the services running, manually trigger the Prefect pipeline. This script will load the data from `data/sample_conversations.json`, generate the 1024-dim embeddings, and populate all five databases.

**Note:** The first run will take a few minutes as it downloads the large `roberta-large` model.

```bash
docker-compose run pipeline_runner
```

You will see logs as the pipeline extracts, transforms, and loads the data. Wait for it to show `Flow run '...' - Finished in state Completed()`.

### 4\. Test the Hybrid Retrieval API

Once the pipeline is complete, the platform is loaded with data. You can now query the API for recommendations.

```bash
curl http://localhost:8000/recommendations/u_001
```

**Expected Output (Cache Miss):**

```json
{
  "user_id": "u_001",
  "recommendations": [
    {
      "campaign_id": "c_102",
      "ranking_score": 3,
      "reason": "Recommended based on users with similar interests."
    },
    {
      "campaign_id": "c_101",
      "ranking_score": 3,
      "reason": "Recommended based on users with similar interests."
    },
    {
      "campaign_id": "c_103",
      "ranking_score": 1,
      "reason": "Recommended based on users with similar interests."
    }
  ],
  "retrieval_source": "computed"
}
```

**Run it again to test the cache:**

```bash
curl http://localhost:8000/recommendations/u_001
```

**Expected Output (Cache Hit):**

```json
{
  "user_id": "u_001",
  "recommendations": [
    {
      "campaign_id": "c_102",
      "ranking_score": 3,
      "reason": "Recommended based on users with similar interests."
    },
    {
      "campaign_id": "c_101",
      "ranking_score": 3,
      "reason": "Recommended based on users with similar interests."
    },
    {
      "campaign_id": "c_103",
      "ranking_score": 1,
      "reason": "Recommended based on users with similar interests."
    }
  ],
  "retrieval_source": "cache"
}
```
