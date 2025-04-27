from .state import ConversationState

def route_based_on_intent(state: ConversationState) -> str:
    """Routes to the appropriate node based on classified intent and frustration level."""
    intent = state.get('intent')
    
    # Get frustration_count from the state returned by classify_intent_node
    # This ensures we're using the latest value
    frustration_count = state.get('frustration_count', 0)
    print(f"--- Router: Routing based on intent '{intent}', frustration_count={frustration_count} ---")

    # Route to frustration_node if user is frustrated
    # We prioritize handling frustration over other intents when frustration is high
    if frustration_count >= 2:
        print("--- Router: Routing to frustration_node due to high frustration level ---")
        return "frustration_node"
        
    # Handle manager approval intent (e.g., for refund requests)
    if intent == 'manager_approval':
        print("--- Router: Routing to manager approval node for special handling ---")
        return "manager_approval_node"

    # For intents that need entity extraction before taking action
    if intent in ['order_status', 'product_availability', 'coupon_query']:
        # First route to the entity extraction node
        print(f"--- Router: Routing {intent} to decide_tool_or_fetch_data_node for entity extraction ---")
        return "decide_tool_or_fetch_data_node"
        
    elif intent in ['knowledge_base_query']:
        # These intents can go directly to action node
        print(f"--- Router: Routing {intent} directly to action_node ---")
        return "action_node"
        
    elif intent == 'greeting':
        # Simple greetings might not need tools/context
        # But if there's any frustration, we should acknowledge it
        if frustration_count > 0:
            print("--- Router: Routing greeting with slight frustration to frustration_node ---")
            return "frustration_node"
        else:
            print("--- Router: Routing greeting directly to response generation ---")
            return "generate_response_node"
        
    else: # 'other', 'refund_request' that doesn't need approval, or fallback
        # Check if there's some frustration even if below threshold
        if frustration_count == 1:
            print("--- Router: Routing 'other' intent with mild frustration to action_node with caution ---")
            # Mark state to indicate mild frustration for action_node to handle carefully
            state['mild_frustration'] = True
            return "action_node"
        else:
            print("--- Router: Routing 'other' intent to action_node ---")
            return "action_node" # Let action_node decide if KB tool is needed or skip

def route_after_entity_extraction(state: ConversationState) -> str:
    """Routes to the action node after entity extraction."""
    print("--- Router: Routing after entity extraction to action_node ---")
    return "action_node"


def route_after_action(state: ConversationState) -> str:
    """Always routes back to generate the response after an action."""
    print("--- Router: Routing after action to generate response ---")
    return "generate_response_node"
