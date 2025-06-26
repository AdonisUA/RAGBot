import structlog
from typing import List, Dict, Any, Optional
from chromadb import Client, Settings
from chromadb.utils import embedding_functions
from app.core.config import get_settings
import uuid

logger = structlog.get_logger()

class VectorMemoryService:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.settings = get_settings()
            self.client = self._initialize_chroma_client()
            self.collection = self._get_or_create_collection()
            self._initialized = True

    def _initialize_chroma_client(self) -> Client:
        """Always initialize ChromaDB HTTP client using chroma_api_url from settings."""
        if not self.settings.chroma_api_url:
            logger.error("chroma_api_url is not set in config. Cannot initialize ChromaDB HTTP client.")
            raise RuntimeError("chroma_api_url is required for ChromaDB HTTP client.")
        url = self.settings.chroma_api_url
        host = url.split('//')[1].split(':')[0]
        port = int(url.split(':')[-1])
        return Client(Settings(
            chroma_api_impl="chromadb.api.fastapi.FastAPI",
            chroma_server_host=host,
            chroma_server_http_port=port
        ))

    def _get_or_create_collection(self):
        """Get or create ChromaDB collection using collection_name from settings."""
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2" # Or a configurable model
        )
        return self.client.get_or_create_collection(
            name=self.settings.chroma_collection_name,
            embedding_function=embedding_function
        )

    async def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None, doc_id: Optional[str] = None):
        """Add a document to the vector database."""
        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[doc_id or str(uuid.uuid4())]
            )
            logger.info("Document added to ChromaDB", text_preview=text[:50], metadata=metadata)
        except Exception as e:
            logger.error("Failed to add document to ChromaDB", error=str(e))
            raise

    async def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Query the vector database for relevant documents."""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k
            )
            formatted_results = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results["distances"] else None
                    })
            logger.info("ChromaDB query successful", query=query_text, num_results=len(formatted_results))
            return formatted_results
        except Exception as e:
            logger.error("Failed to query ChromaDB", error=str(e))
            raise

    async def health_check(self) -> dict:
        try:
            # Проверяем доступность ChromaDB через list_collections
            collections = self.client.list_collections()
            return {"status": "healthy", "collections": [c.name for c in collections]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
