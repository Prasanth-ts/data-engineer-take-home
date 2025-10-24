# src/utils/config.py
import os

# --- Database Hosts ---
# These names come from your docker-compose.yml service names
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
NEO4J_HOST = os.getenv("NEO4J_HOST", "localhost")
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")

# --- Database Ports ---
MONGO_PORT = 27017
REDIS_PORT = 6379
NEO4J_BOLT_PORT = 7687
MILVUS_PORT = 19530

# --- Neo4j Credentials ---
NEO4J_USER = "neo4j"
NEO4J_PASS = "password" # From your docker-compose.yml

# --- Milvus ---
MILVUS_COLLECTION_NAME = "conversations"
EMBEDDING_DIM = 1024 #

# --- ML Model ---
EMBEDDING_MODEL = 'sentence-transformers/all-roberta-large-v1'

# --- API Cache ---
RECOMMENDATION_CACHE_TTL_SECONDS = 300 # 5 minutes