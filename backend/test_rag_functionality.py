#!/usr/bin/env python3
"""
Test RAG (Retrieval-Augmented Generation) functionality
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_rag_functionality():
    """Test RAG functionality with VectorMemoryService"""

    print("🧪 Testing RAG functionality...")

    try:
        from app.services.vector_memory_service import VectorMemoryService
        from app.services.ai_service import AIService
        from app.models.chat import Message

        # Initialize services
        vector_service = VectorMemoryService()
        ai_service = AIService()

        print("✅ Services initialized successfully")

        # Test 1: Add documents to vector memory
        print("\n📝 Test 1: Adding documents to vector memory...")

        test_documents = [
            {
                "text": "Python is a high-level programming language known for its simplicity and readability.",
                "metadata": {"topic": "programming", "language": "python", "timestamp": datetime.now().isoformat()}
            },
            {
                "text": "Machine learning is a subset of artificial intelligence that enables computers to learn without being explicitly programmed.",
                "metadata": {"topic": "ai", "subtopic": "machine_learning", "timestamp": datetime.now().isoformat()}
            },
            {
                "text": "WebSocket is a computer communications protocol that provides full-duplex communication channels over a single TCP connection.",
                "metadata": {"topic": "networking", "protocol": "websocket", "timestamp": datetime.now().isoformat()}
            },
            {
                "text": "FastAPI is a modern, fast web framework for building APIs with Python based on standard Python type hints.",
                "metadata": {"topic": "programming", "framework": "fastapi", "timestamp": datetime.now().isoformat()}
            }
        ]

        for doc in test_documents:
            await vector_service.add_document(doc["text"], doc["metadata"])
            print(f"  ✅ Added: {doc['text'][:50]}...")

        print(f"✅ Added {len(test_documents)} documents to vector memory")

        # Test 2: Query vector memory
        print("\n🔍 Test 2: Querying vector memory...")

        test_queries = [
            "What is Python?",
            "Tell me about machine learning",
            "How does WebSocket work?",
            "What is FastAPI?"
        ]

        for query in test_queries:
            print(f"\n  Query: '{query}'")
            results = await vector_service.query(query, top_k=2)

            for i, result in enumerate(results, 1):
                print(f"    Result {i}: {result['document'][:80]}...")
                print(f"    Distance: {result['distance']:.4f}")
                print(f"    Metadata: {result['metadata']}")

        # Test 3: Test RAG integration with AIService
        print("\n🤖 Test 3: Testing RAG integration with AIService...")

        # Create a mock context
        context = [
            Message(
                content="You are a helpful AI assistant.",
                role="system",
                session_id="test_session"
            )
        ]

        # Test query that should benefit from RAG
        test_query = "What programming languages do you know about?"

        print(f"  Query: '{test_query}'")
        print("  Testing with RAG enabled...")

        # This would normally call the AI service, but we'll just test the RAG part
        retrieved_docs = await vector_service.query(test_query, top_k=3)

        if retrieved_docs:
            print("  ✅ RAG found relevant documents:")
            for i, doc in enumerate(retrieved_docs, 1):
                print(f"    {i}. {doc['document'][:60]}...")
        else:
            print("  ⚠️ No relevant documents found")

        print("\n🎉 All RAG tests completed successfully!")

        # Test 4: Test similarity threshold
        print("\n🎯 Test 4: Testing similarity threshold...")

        # Test with a very specific query
        specific_query = "What is the difference between Python and JavaScript?"
        results = await vector_service.query(specific_query, top_k=3)

        print(f"  Query: '{specific_query}'")
        print(f"  Found {len(results)} results")

        for i, result in enumerate(results, 1):
            similarity_score = 1 - result['distance'] if result['distance'] else 0
            print(f"    {i}. Similarity: {similarity_score:.4f} - {result['document'][:60]}...")

        return True

    except Exception as e:
        print(f"❌ RAG test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_rag_with_mock():
    """Test RAG functionality with mocked dependencies"""

    print("\n🧪 Testing RAG with mocked dependencies...")

    # Mock VectorMemoryService
    class MockVectorMemoryService:
        def __init__(self):
            self.documents = []

        async def add_document(self, text: str, metadata=None, doc_id=None):
            self.documents.append({
                "text": text,
                "metadata": metadata or {},
                "id": doc_id or f"doc_{len(self.documents)}"
            })
            print(f"  Mock: Added document '{text[:30]}...'")

        async def query(self, query_text: str, top_k: int = 3):
            # Simple mock search - return documents containing query words
            query_words = query_text.lower().split()
            results = []

            for doc in self.documents:
                doc_text = doc["text"].lower()
                if any(word in doc_text for word in query_words):
                    results.append({
                        "document": doc["text"],
                        "metadata": doc["metadata"],
                        "distance": 0.1  # Mock distance
                    })

            return results[:top_k]

    # Test with mock
    mock_service = MockVectorMemoryService()

    # Add test documents
    await mock_service.add_document(
        "Python is a programming language",
        {"topic": "programming", "language": "python"}
    )
    await mock_service.add_document(
        "JavaScript is used for web development",
        {"topic": "programming", "language": "javascript"}
    )

    # Test query
    results = await mock_service.query("Python programming", top_k=2)
    print(f"  Mock query results: {len(results)} documents found")

    for i, result in enumerate(results, 1):
        print(f"    {i}. {result['document']}")

    print("✅ Mock RAG test completed")

if __name__ == "__main__":
    print("🚀 Starting RAG functionality tests...")

    # Run tests
    success1 = asyncio.run(test_rag_functionality())
    success2 = asyncio.run(test_rag_with_mock())

    if success1 and success2:
        print("\n🎉 All RAG tests passed!")
    else:
        print("\n❌ Some RAG tests failed!")
        sys.exit(1)
