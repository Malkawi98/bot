from .state import ConversationState
from .tools import tools
from .llm import llm, classifier_llm
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.tools.render import format_tool_to_openai_function
import json

# Helper to convert tools for LLM function calling
functions = [format_tool_to_openai_function(t) for t in tools]
llm_with_tools = llm.bind_functions(functions)
classifier_llm_with_tools = classifier_llm.bind_functions(functions)

def classify_intent_node(state: ConversationState):
    """Classifies the user's intent based on the latest message."""
    print("--- Node: Classify Intent ---")
    user_message = state['user_message']
    messages = state['messages']

    # Simple prompt for classification
    prompt = f"""Based on the following user message and conversation history, classify the primary intent. Choose ONE from: 'order_status', 'knowledge_base_query', 'product_availability', 'greeting', 'other'.

    Conversation History:
    {[f'{m.type}: {m.content}' for m in messages]}

    User Message: {user_message}

    Intent:"""

    response = classifier_llm.invoke(prompt)
    intent = response.content.strip().lower()

    # Basic validation/cleanup
    allowed_intents = ['order_status', 'knowledge_base_query', 'product_availability', 'greeting', 'other']
    if intent not in allowed_intents:
        print(f"--- Classified intent '{intent}' not in allowed list, defaulting to 'knowledge_base_query'. ---")
        intent = 'knowledge_base_query'

    print(f"--- Classified Intent: {intent} ---")
    return {"intent": intent}

def action_node(state: ConversationState):
    """Invokes the appropriate tool based on the classified intent."""
    print("--- Node: Action ---")
    intent = state['intent']
    user_message = state['user_message']
    messages = state['messages']
    
    # Regular tool handling for other intents
    tool_map = {tool.name: tool for tool in tools}
    tool_to_call = None
    
    if intent == 'order_status':
        tool_to_call = tool_map.get('order_status_checker')
        input_value = user_message  # String input for order status
    elif intent == 'knowledge_base_query':
        # For other knowledge base queries, try the regular tool
        tool_to_call = tool_map.get('knowledge_base_retriever')
        input_value = user_message  # Use string input instead of state
    elif intent == 'product_availability':
        tool_to_call = tool_map.get('product_availability_checker')
        input_value = user_message  # String input for product availability
    else:
        input_value = user_message

    # If a specific tool is identified for the intent
    if tool_to_call:
        print(f"--- Calling Tool: {tool_to_call.name} with input: {input_value} ---")
        try:
            # Invoke the tool with the string input
            observation = tool_to_call.invoke(input_value)
            
            # Special handling for knowledge base retrieval
            if intent == 'knowledge_base_query' and isinstance(observation, str):
                # For knowledge base retriever, we get back a string with the context
                print(f"--- Tool Observation: Knowledge base context retrieved, length: {len(observation)} ---")
                # Return both the action result and the retrieved context
                return {
                    "retrieved_context": observation if observation != "No relevant information found in the knowledge base." else None,
                    "action_result": {intent: {"found": observation != "No relevant information found in the knowledge base."}}
                }
            else:
                # For other tools, handle as before
                # Ensure observation is serializable if it's complex
                if not isinstance(observation, (str, dict, list, int, float, bool, type(None))):
                    observation = str(observation)
                    
                print(f"--- Tool Observation: {observation} ---")
                return {"action_result": {intent: observation}}

        except Exception as e:
            print(f"--- Tool Invocation Error: {e} ---")
            observation = {"error": f"Failed to execute action: {e}"}
            return {"action_result": {intent: observation}}
    else:
        print(f"--- No specific tool for intent '{intent}', skipping action. ---")
        # No specific tool, maybe pass directly to response generation
        return {"action_result": None}

def generate_response_node(state: ConversationState):
    """Generates the final response to the user."""
    print("--- Node: Generate Response ---")
    user_message_content = state['user_message']
    messages = state['messages']
    intent = state['intent']
    context = state.get('retrieved_context')
    action_result = state.get('action_result')

    # Prepare prompt for LLM
    prompt_context = ""
    if context:
        prompt_context += f"\n\nRelevant Information from Knowledge Base:\n{context}"
    if action_result:
        # Convert dict result to string for the prompt
        action_result_str = json.dumps(action_result, indent=2)
        prompt_context += f"\n\nResult from Action ({intent}):\n{action_result_str}"

    # Add the current user message to the history for the LLM call
    current_history = messages + [HumanMessage(content=user_message_content)]

    # Construct the prompt
    prompt = f"""You are a helpful e-commerce customer support assistant.
    Answer the user's query based on the conversation history and the provided context or action results.
    Be concise and helpful. If you performed an action, summarize the result clearly.
    If relevant information was found in the knowledge base, use it to answer.
    If the intent was a greeting, respond politely.
    If you cannot answer, politely say so.

    Conversation History:
    {[f'{m.type}: {m.content}' for m in current_history]}
    {prompt_context}

    Assistant Response:"""

    print(f"--- Generating response with prompt: {prompt[:300]}... ---")

    # Invoke the main LLM
    response = llm.invoke(prompt)
    ai_response_content = response.content

    print(f"--- Generated AI Response: {ai_response_content} ---")

    # Add the AI response to the message history
    updated_messages = current_history + [AIMessage(content=ai_response_content)]

    return {"messages": updated_messages}
