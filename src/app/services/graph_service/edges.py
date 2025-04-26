from .state import ConversationState

def route_based_on_intent(state: ConversationState) -> str:
    """Routes to the appropriate node based on classified intent."""
    intent = state.get('intent')
    
    # Get frustration_count from the state returned by classify_intent_node
    # This ensures we're using the latest value
    frustration_count = state.get('frustration_count', 0)
    print(f"--- Router: Routing based on intent '{intent}', frustration_count={frustration_count} ---")

    # Route to frustration_node if user is frustrated
    if frustration_count >= 2:
        print("--- Router: Routing to frustration_node due to frustration threshold ---")
        return "frustration_node"

    if intent == 'coupon_query':
        # Coupon queries need to be handled by the action node
        print("--- Router: Routing coupon query to action node ---")
        return "action_node"
    elif intent in ['order_status', 'knowledge_base_query', 'product_availability']:
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
