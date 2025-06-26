#!/usr/bin/env python3
"""
Simple test for streaming functionality without external dependencies
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_streaming_logic():
    """Test the streaming logic with mocked dependencies"""

    # Mock the dependencies
    class MockAIService:
        async def generate_streaming_response(self, message, context, settings=None):
            # Simulate streaming response
            response_parts = ["Hello", " ", "world", "!", " How", " are", " you", "?"]
            for part in response_parts:
                await asyncio.sleep(0.1)  # Simulate network delay
                yield part

    class MockMemoryService:
        async def add_message(self, session_id, message):
            print(f"Mock: Added message to session {session_id}")
            return True

        async def get_conversation_history(self, session_id, limit=10):
            return []

    class MockVectorMemoryService:
        async def add_document(self, text, metadata):
            print(f"Mock: Added document to vector memory: {text[:50]}...")
            return True

    # Create a simplified version of ChatLogicService for testing
    class TestChatLogicService:
        def __init__(self):
            self.ai_service = MockAIService()
            self.memory_service = MockMemoryService()
            self.vector_memory_service = MockVectorMemoryService()

        async def process_chat_message_streaming(self, message_data, session_id):
            """Simplified streaming implementation for testing"""
            user_message_text = message_data.get("message", "").strip()
            if not user_message_text:
                yield {"type": "error", "message": "Empty message"}
                return

            if not session_id:
                session_id = "test_session"

            # Add user message to memory
            await self.memory_service.add_message(session_id, {"content": user_message_text, "role": "user"})

            # Get context
            context = await self.memory_service.get_conversation_history(session_id, limit=10)

            # Send initial message
            yield {
                "type": "new_message",
                "message_id": "msg_123",
                "session_id": session_id,
                "role": "assistant",
                "content": ""
            }

            # Stream AI response
            full_response = ""
            try:
                async for chunk in self.ai_service.generate_streaming_response(user_message_text, context):
                    full_response += chunk
                    yield {
                        "type": "stream_chunk",
                        "chunk": chunk,
                        "message_id": "msg_123"
                    }
            except Exception as e:
                yield {
                    "type": "error",
                    "message": f"Failed to generate AI response: {str(e)}"
                }
                return

            # Add AI message to memory
            await self.memory_service.add_message(session_id, {"content": full_response, "role": "assistant"})

            # Send stream end
            yield {
                "type": "stream_end",
                "message_id": "msg_123",
                "final_content": full_response
            }

    # Test the streaming
    print("🧪 Testing streaming functionality...")

    service = TestChatLogicService()
    message_data = {"message": "Hi there!"}
    session_id = "test_session_123"

    events = []
    async for event in service.process_chat_message_streaming(message_data, session_id):
        events.append(event)
        print(f"📡 Event: {event['type']} - {event.get('chunk', event.get('message', ''))}")

    print(f"\n✅ Test completed! Total events: {len(events)}")

    # Verify events
    event_types = [e['type'] for e in events]
    print(f"📊 Event sequence: {' -> '.join(event_types)}")

    # Check for required events
    assert "new_message" in event_types, "Missing new_message event"
    assert "stream_chunk" in event_types, "Missing stream_chunk events"
    assert "stream_end" in event_types, "Missing stream_end event"

    print("🎉 All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_streaming_logic())
