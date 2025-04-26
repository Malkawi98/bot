from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from sqlalchemy.orm import Session

class ConversationState(TypedDict, total=False):
    messages: List[BaseMessage]  # Conversation history (LangChain format)
    user_message: str           # The latest user input
    intent: Optional[str]       # Detected intent (e.g., 'order_status', 'rag_query', 'ecomm_action', 'greeting')
    retrieved_context: Optional[str] # Context from RAG
    action_result: Optional[Dict[str, Any]] # Result from order lookup or other actions
    db: Optional[Session]       # Database session
    language: Optional[str]     # User's preferred language
    frustration_count: int     # Number of errors or frustration signals
    last_error: Optional[str]  # Last error message or signal
