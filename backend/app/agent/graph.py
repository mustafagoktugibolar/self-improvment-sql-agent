from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph  # noqa: F401
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.tools import TOOLS
from app.config import OPENAI_MODEL


def create_graph():
    """Build and compile the SQL agent graph (agent <-> tools loop)."""
    model = ChatOpenAI(model=OPENAI_MODEL).bind_tools(tools=TOOLS)
    graph = StateGraph(MessagesState)

    def call_model(state: MessagesState):
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    graph.add_node(node="agent", action=call_model)
    graph.add_node(node="tools", action=ToolNode(tools=TOOLS))

    graph.add_edge(start_key=START, end_key="agent")

    graph.add_conditional_edges(
        source="agent",
        path=tools_condition
    )

    graph.add_edge(start_key="tools", end_key="agent")

    # AG-UI's LangGraph adapter reads thread state, so a checkpointer is required.
    return graph.compile(checkpointer=MemorySaver())
