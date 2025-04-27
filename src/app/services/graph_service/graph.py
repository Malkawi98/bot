from langgraph.graph import StateGraph, END
from .state import ConversationState
from .nodes import classify_intent_node, action_node, generate_response_node, frustration_node, manager_approval_node, decide_tool_or_fetch_data_node
from .edges import route_based_on_intent, route_after_action, route_after_entity_extraction

# Create the graph
workflow = StateGraph(ConversationState)

# Add nodes
workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("decide_tool_or_fetch_data_node", decide_tool_or_fetch_data_node)
workflow.add_node("action_node", action_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("frustration_node", frustration_node)
workflow.add_node("manager_approval_node", manager_approval_node)

# Define edges
workflow.set_entry_point("classify_intent")

# Conditional edge after classification
workflow.add_conditional_edges(
    "classify_intent",
    route_based_on_intent,
    {
        "action_node": "action_node",
        "decide_tool_or_fetch_data_node": "decide_tool_or_fetch_data_node",
        "generate_response_node": "generate_response",
        "frustration_node": "frustration_node",
        "manager_approval_node": "manager_approval_node",
    }
)

# Edge after entity extraction
workflow.add_conditional_edges(
    "decide_tool_or_fetch_data_node",
    route_after_entity_extraction,
    {
        "action_node": "action_node"
    }
)

# Edge after action is performed
workflow.add_conditional_edges(
    "action_node",
    route_after_action,
    {
        "generate_response_node": "generate_response"
    }
)

# The final response generation leads to the end
workflow.add_edge("generate_response", END)

# Route frustration_node to generate_response
workflow.add_edge("frustration_node", "generate_response")

# Route manager_approval_node to generate_response
workflow.add_edge("manager_approval_node", "generate_response")

# Compile the graph
graph_app = workflow.compile()

# Optional: Visualize the graph
try:
    # Uncomment to generate visualization
    # graph_app.get_graph().draw_mermaid_png(output_file_path="graph.png")
    # print("Graph visualization saved to graph.png")
    pass
except Exception as e:
    print(f"Could not draw graph: {e}")
