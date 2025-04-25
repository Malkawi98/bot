from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class ConversationState(TypedDict):
    messages: List[BaseMessage]  # Conversation history (LangChain format)
    user_message: str           # The latest user input
    intent: Optional[str]       # Detected intent (e.g., 'order_status', 'rag_query', 'ecomm_action', 'greeting')
    retrieved_context: Optional[str] # Context from RAG
    action_result: Optional[Dict[str, Any]] # Result from order lookup or other actions
    # Add other fields as needed, e.g., session_id, user_info
