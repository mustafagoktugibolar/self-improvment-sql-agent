from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph  # noqa: F401
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS
from app.config import OPENAI_MODEL


def create_graph():
    """Build and compile the SQL agent graph (agent <-> tools loop)."""
    model = ChatOpenAI(model=OPENAI_MODEL).bind_tools(tools=TOOLS)
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    graph = StateGraph(MessagesState)

    def call_model(state: MessagesState):
        # The server prompt is the only instruction source: system messages sent by
        # the client (AG-UI allows them) are dropped. Not stored in state, so prompt
        # changes apply to existing threads too.
        history = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
        response = model.invoke([system_message, *history])
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
