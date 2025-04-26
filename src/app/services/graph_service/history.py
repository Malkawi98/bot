from typing import Dict, List, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import json

# In-memory session store for LangGraph (for demo only)
session_store: Dict[str, List[BaseMessage]] = {}

def load_history(session_id: str) -> List[BaseMessage]:
    """Load conversation history for a session."""
    if session_id not in session_store:
        # Initialize with empty history
        session_store[session_id] = []
    
    return session_store[session_id]

def save_history(session_id: str, messages: List[BaseMessage]) -> None:
    """Save conversation history for a session."""
    session_store[session_id] = messages
    
    # For debugging, print the number of messages saved
    print(f"Saved {len(messages)} messages for session {session_id}")

def serialize_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """Convert LangChain message objects to serializable dictionaries."""
    serialized = []
    for msg in messages:
        serialized.append({
            "type": msg.type,
            "content": msg.content
        })
    return serialized

def deserialize_messages(serialized: List[Dict[str, Any]]) -> List[BaseMessage]:
    """Convert serialized dictionaries back to LangChain message objects."""
    messages = []
    for msg in serialized:
        if msg["type"] == "human":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["type"] == "ai":
            messages.append(AIMessage(content=msg["content"]))
    return messages
