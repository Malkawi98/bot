from langgraph.graph import StateGraph, END
from .state import ConversationState
from .nodes import classify_intent_node, action_node, generate_response_node
from .edges import route_based_on_intent, route_after_action

# Create the graph
workflow = StateGraph(ConversationState)

# Add nodes
workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("action_node", action_node)
workflow.add_node("generate_response", generate_response_node)

# Define edges
workflow.set_entry_point("classify_intent")

# Conditional edge after classification
workflow.add_conditional_edges(
    "classify_intent",
    route_based_on_intent,
    {
        "action_node": "action_node",
        "generate_response_node": "generate_response",
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
