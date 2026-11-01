from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph  # noqa: F401
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import ASK_USER_TOOL_NAME, TOOLS
from app.config import OPENAI_MODEL


def keep_only_ask_user(response: AIMessage) -> AIMessage:
    """If the model calls ask_user together with other tools, keep only ask_user.

    ask_user pauses the graph for a human answer, so it must not run beside other
    tools: they would run twice on resume, and the question usually exists because
    those queries should wait for the answer. Enforced here, not just in the prompt.
    """
    ask_calls = []
    for call in response.tool_calls:
        if call["name"] == ASK_USER_TOOL_NAME:
            ask_calls.append(call)

    if not ask_calls or len(ask_calls) == len(response.tool_calls):
        return response
    # Only the first question; several at once would be several interrupts.
    return response.model_copy(update={"tool_calls": ask_calls[:1]})


def create_graph(checkpointer=None):
    """Build and compile the SQL agent graph (agent <-> tools loop).

    `checkpointer` stores thread state, including paused ask_user interrupts. Defaults
    to in-memory (tests); the app passes a SQLite one so state survives restarts.
    """
    model = ChatOpenAI(model=OPENAI_MODEL).bind_tools(tools=TOOLS)
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    graph = StateGraph(MessagesState)

    def call_model(state: MessagesState):
        # The server prompt is the only instruction source: system messages sent by
        # the client (AG-UI allows them) are dropped. Not stored in state, so prompt
        # changes apply to existing threads too.
        history = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
        response = model.invoke([system_message, *history])
        return {"messages": [keep_only_ask_user(response)]}

    graph.add_node(node="agent", action=call_model)
    graph.add_node(node="tools", action=ToolNode(tools=TOOLS))

    graph.add_edge(start_key=START, end_key="agent")

    graph.add_conditional_edges(
        source="agent",
        path=tools_condition
    )

    graph.add_edge(start_key="tools", end_key="agent")

    # AG-UI's LangGraph adapter reads thread state, so a checkpointer is required.
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
