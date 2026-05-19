from state import State


def write_plan_node(state: State):
    with open("plan.md", "w") as f:
        f.write(state["plan"])
    print("\nPlan written to plan.md")
    return state
