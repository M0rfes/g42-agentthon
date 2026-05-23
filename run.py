import argparse
from langgraph.graph import StateGraph, END
from state import State
from nodes import read_prd_node, planner_node, write_plan_node, scaffolder_node


def create_harness(ask_allowed: bool):
    workflow = StateGraph(State)

    workflow.add_node("read_prd", read_prd_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("write_plan", write_plan_node)
    workflow.add_node("scaffolder", scaffolder_node)

    workflow.set_entry_point("read_prd")
    workflow.add_edge("read_prd", "planner")
    workflow.add_edge("planner", "write_plan")
    workflow.add_edge("write_plan", "scaffolder")
    workflow.add_edge("scaffolder", END)

    return workflow.compile()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PRD to Plan Harness")
    parser.add_argument("prd_path", help="Path to the PRD markdown file")
    parser.add_argument(
        "--ask", action="store_true", help="Allow the agent to ask for clarification"
    )
    args = parser.parse_args()

    app = create_harness(args.ask)
    app.invoke(
        {
            "messages": [],
            "prd_path": args.prd_path,
            "prd_content": "",
            "plan": "",
            "ask_allowed": args.ask,
            "output_dir": "",
        }
    )
