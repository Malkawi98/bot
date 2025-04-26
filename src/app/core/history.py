"""
Chat history management module for the bot.
"""
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# In-memory storage for chat history (for demo purposes)
# In production, this should be replaced with a database solution
history_store: Dict[str, List[Dict[str, Any]]] = {}

def save_history(session_id: str, messages: List[BaseMessage]) -> None:
    """
    Save chat history for a session.
    
    Args:
        session_id: The unique session identifier
        messages: List of LangChain message objects
    """
    # Convert LangChain messages to serializable dictionaries
    serialized_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            serialized_messages.append({
                "type": "human",
                "content": msg.content
            })
        elif isinstance(msg, AIMessage):
            serialized_messages.append({
                "type": "ai",
                "content": msg.content
            })
        # Other message types can be added as needed
    
    # Save to the store
    history_store[session_id] = serialized_messages

def load_history(session_id: str) -> List[BaseMessage]:
    """
    Load chat history for a session.
    
    Args:
        session_id: The unique session identifier
        
    Returns:
        List of LangChain message objects
    """
    # Get from store or return empty list if not found
    serialized_messages = history_store.get(session_id, [])
    
    # Convert serialized dictionaries back to LangChain messages
    messages = []
    for msg in serialized_messages:
        if msg["type"] == "human":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["type"] == "ai":
            messages.append(AIMessage(content=msg["content"]))
        # Other message types can be added as needed
    
    return messages
