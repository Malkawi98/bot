from .state import ConversationState

def route_based_on_intent(state: ConversationState) -> str:
    """Routes to the appropriate node based on classified intent."""
    intent = state.get('intent')
    print(f"--- Router: Routing based on intent '{intent}' ---")

    if intent in ['order_status', 'knowledge_base_query', 'product_availability']:
        # These intents require specific actions/tools
        return "action_node"
    elif intent == 'greeting':
        # Simple greetings might not need tools/context
        return "generate_response_node"
    else: # 'other' or fallback
        # Default to trying the knowledge base for 'other'
        return "action_node" # Let action_node decide if KB tool is needed or skip

def route_after_action(state: ConversationState) -> str:
    """Always routes back to generate the response after an action."""
    print("--- Router: Routing after action to generate response ---")
    return "generate_response_node"
