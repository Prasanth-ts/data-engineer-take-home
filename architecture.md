# Architecture & Design Justification

This document details the architectural choices for the AI-Driven Marketing Platform, focusing on modularity and using the right tool for each data shape.

## 1. Guiding Principles

* **Right Tool for the Job:** The platform processes structured, unstructured, vector, and graph data. No single database excels at all four. This design uses a specialized database for each task to ensure high performance and scalability.
* **Separation of Concerns:** The system is split into two distinct flows:
    1.  **Batch Pipeline:** A reliable, observable Prefect flow handles the heavy, asynchronous work of embedding generation and data transformation.
    2.  **Serving API:** A lightweight FastAPI server handles low-latency, real-time user requests.

## 2. Component Justification

* **MongoDB (Document Store):**
    * **Role:** Serves as the primary "data lake" for raw conversation data.
    * **Why:** Its schemaless, document-native (JSON) structure is perfect for storing unstructured chat data. It's flexible and easy to query for individual user histories.

* **Milvus (Vector Database):**
    * **Role:** Stores vector embeddings for Approximate Nearest Neighbor (ANN) search.
    * **Why:** This is the core of the AI matching. Milvus is designed to find the "top 5 most similar users" from millions of vectors at extremely low latency, a task traditional databases cannot perform.

* **Neo4j (Graph Database):**
    * **Role:** Stores the complex relationships between users, campaigns, and intents.
    * **Why:** A graph is the most natural and efficient way to model this. It allows the API to instantly answer the key business question: "Which campaigns are connected to this group of similar users?".

* **SQLite (Analytics Layer Mock):**
    * **Role:** Stores pre-aggregated metrics, such as engagement frequency
    * **Why:** This is a mock for a production OLAP system like BigQuery or Snowflake. We *pre-calculate* the ranking scores in the batch pipeline. This prevents the real-time API from running slow `COUNT(*)` or `GROUP BY` queries, allowing it to simply fetch a pre-computed score for fast ranking.

* **Redis (Cache):**
    * **Role:** Caches the final recommendation JSON for a user.
    * **Why:** This is our primary latency optimization. If two requests for the same user arrive within 5 minutes, the second request is served in single-digit milliseconds from Redis, completely bypassing the expensive hybrid retrieval (Milvus + Neo4j + SQLite).

## 3. Data Flow & Orchestration

* **Orchestration (Prefect):** Prefect was chosen for its Python-native approach. It manages the pipeline's DAG (Directed Acyclic Graph), ensuring that data is extracted, transformed (embedded), and then loaded into all databases in the correct order. It also provides logging and observability for pipeline status and failures.
* **Data Lineage & Validation:**
    * **Validation:** Pydantic models (in `src/db/schemas.py`) are used in the pipeline to validate all incoming data before it's processed, ensuring data quality.
    * **Lineage:** Basic lineage is tracked via Prefect's logs, which show the flow of data from the source file to the target databases.


# AI-Driven Marketing Platform: Architecture

This document contains the system architecture diagram (Phase 1) and the design justifications (Phase 3) for the take-home assignment.

## Architecture Diagram

This diagram shows the end-to-end flow of data, from the batch pipeline that processes data to the real-time API that serves recommendations.

```mermaid
graph TD
    subgraph "Ingestion & Processing (Batch Pipeline)"
        A(data/sample_conversations.json) --> B(Prefect Flow: pipeline_runner);
        B -- "1. Validate & Embed" --> C(Sentence Transformer);
        C --> D[Load Raw Text] --> E(MongoDB);
        C --> F[Load Embeddings] --> G(Milvus);
        C --> H[Load Relationships] --> I(Neo4j);
        C --> J[Load Aggregates] --> K(SQLite);
    end

    subgraph "Serving & Retrieval (Real-time API)"
        L[User Request] -- "GET /recommendations/<user_id>" --> M(FastAPI);
        M -- "1. Check Cache" --> N(Redis);
        M -- "Cache Miss" --> O[Get Query Vector];
        O -- "2. Find Similar Users" --> G;
        O -- "3. Find Campaigns" --> I;
        O -- "4. Get Rankings" --> K;
        O -- "5. Rank & Cache Result" --> N;
        N -- "Return Result" --> L;
    end
    
    style E fill:#4DB33D,stroke:#333
    style G fill:#00A3E0,stroke:#333
    style I fill:#008CC1,stroke:#333
    style K fill:#669DF6,stroke:#333
    style N fill:#D82C20,stroke:#333