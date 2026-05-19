import json
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from state import State
from utils import log_token_usage
from tools.clarification import ask_clarification
from githubmodel import default_model


def planner_node(state: State):
    # Bind tools only if clarification is allowed
    model = default_model
    if state["ask_allowed"]:
        model = model.bind_tools([ask_clarification])

    with open("metadata.json", "r") as f:
        metadata = json.load(f)

    system_prompt = SystemMessage(content=metadata["planner_system_prompt"])

    messages = [system_prompt, HumanMessage(content=f"PRD:\n{state['prd_content']}")]

    response = model.invoke(messages)

    if hasattr(response, "usage_metadata"):
        log_token_usage("planner_initial", response.usage_metadata)

    if response.tool_calls and state["ask_allowed"]:
        messages.append(response)
        for tool_call in response.tool_calls:
            if tool_call["name"] == "ask_clarification":
                result = ask_clarification.invoke(tool_call["args"])
                messages.append(
                    ToolMessage(tool_call_id=tool_call["id"], content=result)
                )

        response = model.invoke(messages)

        if hasattr(response, "usage_metadata"):
            log_token_usage("planner_final", response.usage_metadata)

    return {"plan": response.content}
