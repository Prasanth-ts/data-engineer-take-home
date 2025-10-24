import json
import logging
import pandas as pd
from prefect import task, flow
from sentence_transformers import SentenceTransformer
from src.utils.db import (
    get_mongo_client, 
    get_milvus_connection, 
    get_neo4j_driver,
    get_sqlite_conn
)
from src.db.schemas import Conversation
from pydantic import ValidationError
from src.utils import config

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Tasks ---

@task
def extract_raw_data() -> list[dict]:
    """Reads raw data from the sample JSON file[cite: 38]."""
    logger.info("Extracting raw data from data/sample_conversations.json...")
    
    # This path works because the Dockerfile copies the 'data' folder
    file_path = "data/sample_conversations.json" 
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Successfully extracted {len(data)} records from file.")
        return data
    except FileNotFoundError:
        logger.error(f"Data file not found at {file_path}. Did you create it?")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {file_path}. Check for syntax errors.")
        return []

@task
def transform_and_validate(data: list[dict]) -> list[Conversation]:
    """
    Validates data with Pydantic and generates embeddings[cite: 39, 46].
    Also detects and logs anomalies (e.g., empty embeddings)[cite: 57].
    """
    logger.info(f"Transforming {len(data)} records...")
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    
    valid_data = []
    for item in data:
        try:
            # 1. Validate
            convo = Conversation(**item)
            
            # 2. Generate Embedding [cite: 20]
            embedding = model.encode(convo.message, convert_to_numpy=True)
            
            # Anomaly check
            if embedding is None or embedding.size == 0:
                logger.warning(f"Empty embedding for message_id: {convo.message_id}")
                continue
                
            convo.embedding = embedding.tolist()
            valid_data.append(convo)
            
        except ValidationError as e:
            logger.warning(f"Invalid data skipped: {item.get('message_id')}. Error: {e}")
            
    logger.info(f"Successfully transformed {len(valid_data)} records.")
    return valid_data

@task
def load_to_dbs(data: list[Conversation]):
    """Loads the transformed data into all four target databases."""
    logger.info(f"Loading {len(data)} records into databases...")
    
    # Get clients
    mongo = get_mongo_client()
    milvus = get_milvus_connection()
    neo_driver = get_neo4j_driver()
    sqlite_conn = get_sqlite_conn()
    
    # Prepare data for bulk insertion
    # Use model_dump() per Pydantic v2
    mongo_data = [d.model_dump(exclude={'embedding'}) for d in data] 
    milvus_data = [
        [d.message_id for d in data],
        [d.user_id for d in data],
        [d.embedding for d in data]
    ]

    # --- 1. Load to MongoDB (Document Store) [cite: 41] ---
    mongo.conversations.delete_many({}) # Clear old data
    mongo.conversations.insert_many(mongo_data)
    logger.info(f"Loaded {len(mongo_data)} records to MongoDB.")
    
    # --- 2. Load to Milvus (Vector DB) [cite: 43] ---
    # We clear old data by dropping/re-creating the collection in db.py
    milvus.insert(milvus_data)
    milvus.flush() # Ensure data is indexed
    logger.info(f"Loaded {len(milvus_data[0])} vectors to Milvus.")
    
    # --- 3. Load to Neo4j (Graph DB) [cite: 44] ---
    with neo_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n") # Clear old data
        for d in data:
            # Create nodes and relationships
            session.run("""
            MERGE (u:User {id: $user_id})
            MERGE (c:Campaign {id: $campaign_id})
            MERGE (i:Intent {name: $intent})
            MERGE (u)-[:PARTICIPATED_IN {timestamp: $ts}]->(c)
            MERGE (u)-[:EXPRESSED {timestamp: $ts}]->(i)
            """, 
            user_id=d.user_id, 
            campaign_id=d.campaign_id, 
            intent=d.intent,
            ts=d.timestamp
            )
    logger.info(f"Loaded {len(data)} relationships to Neo4j.")

    # --- 4. Load to SQLite (Analytics DB) [cite: 45] ---
    df = pd.DataFrame([d.model_dump() for d in data])
    analytics_df = df.groupby(['user_id', 'campaign_id']).size().reset_index(name='engagement_count')
    
    sqlite_conn.execute("DELETE FROM user_analytics") # Clear old data
    analytics_df.to_sql('user_analytics', sqlite_conn, if_exists='append', index=False)
    sqlite_conn.commit()
    sqlite_conn.close()
    logger.info(f"Loaded {len(analytics_df)} aggregates to SQLite.")

# --- Main Flow ---

@flow(name="Main ETL and Embedding Flow")
def main_data_pipeline():
    """The main orchestrated workflow[cite: 37]."""
    logger.info("Pipeline starting...")
    start_time = pd.Timestamp.now()
    
    raw_data = extract_raw_data()
    if not raw_data:
        logger.error("No raw data found. Exiting.")
        return
        
    transformed_data = transform_and_validate(raw_data)
    if not transformed_data:
        logger.error("No data survived transformation. Exiting.")
        return
        
    load_to_dbs(transformed_data)
    
    end_time = pd.Timestamp.now()
    latency = (end_time - start_time).total_seconds()
    logger.info(f"Pipeline finished successfully. Total time: {latency:.2f}s")

if __name__ == "__main__":
    main_data_pipeline()