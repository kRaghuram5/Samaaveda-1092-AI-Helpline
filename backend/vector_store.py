"""
Vector Store for Samaaveda using ChromaDB.
Stores past corrections as embeddings for Few-Shot RAG memory.
"""
import chromadb
from chromadb.utils import embedding_functions
import logging
import json
from config import FEEDBACK_LOG_DIR, GEMINI_API_KEY

logger = logging.getLogger(__name__)

class VectorMemory:
    def __init__(self):
        try:
            # Initialize ChromaDB (local persistence)
            self.db_path = str(FEEDBACK_LOG_DIR / "vector_db")
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Use a more stable model name for embeddings
            self.ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=GEMINI_API_KEY,
                model_name="models/text-embedding-004"
            )
            
            self.collection = self.client.get_or_create_collection(
                name="helpline_memory",
                embedding_function=self.ef
            )
            logger.info(f"Vector Memory initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Vector Store initialization failed: {e}")
            self.collection = None

    def add_memory(self, session_id: str, transcript: str, corrected_summary: dict):
        """Add a corrected session to memory."""
        if not self.collection: return
        
        try:
            # Clean summary for metadata (flattened)
            metadata = {
                "session_id": session_id,
                "intent": str(corrected_summary.get("intent", ""))[:100],
                "location": str(corrected_summary.get("location", "unknown"))
            }
            
            self.collection.add(
                ids=[session_id],
                documents=[transcript],
                metadatas=[metadata]
            )
            logger.info(f"Memory added for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")

    def get_similar_memories(self, transcript: str, limit: int = 2) -> str:
        """Find past similar calls and format them for the LLM prompt."""
        if not self.collection: return ""
        
        try:
            results = self.collection.query(
                query_texts=[transcript],
                n_results=limit
            )
            
            if not results or not results['documents'] or not results['documents'][0]:
                return ""

            examples = "PAST SIMILAR CASES (LEARNED FROM FEEDBACK):\n"
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                examples += f"- Similar past transcript: '{doc}'\n"
                
            return examples + "\n"
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return ""
