"""Offline check of the ask_user human-in-the-loop flow (fake model, no OpenAI calls)."""
from app.agent import graph as graph_module
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command


class FakeModel:
    """First asks a clarifying question, then answers once it sees the tool result."""

    def __init__(self, **kwargs):
        self.calls = []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        if isinstance(messages[-1], HumanMessage):
            return AIMessage(content="", tool_calls=[{
                "id": "call_1",
                "name": "ask_user",
                "args": {"question": "Which definition?", "options": ["first order", "signup"]},
            }])
        return AIMessage(content="done")


def test_ask_user_pauses_and_resumes(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(graph_module, "ChatOpenAI", lambda **kwargs: model)
    graph = graph_module.create_graph()
    config = {"configurable": {"thread_id": "hitl-test"}}

    paused = graph.invoke({"messages": [HumanMessage("new customers last quarter?")]}, config)

    interrupt_value = paused["__interrupt__"][0].value
    assert interrupt_value["reason"] == "ask_user"
    assert interrupt_value["message"] == "Which definition?"
    assert interrupt_value["options"] == ["first order", "signup"]

    finished = graph.invoke(Command(resume="first order"), config)

    tool_message = finished["messages"][-2]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.content == "The user answered: first order"
    assert finished["messages"][-1].content == "done"


def test_ask_user_cancelled(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(graph_module, "ChatOpenAI", lambda **kwargs: model)
    graph = graph_module.create_graph()
    config = {"configurable": {"thread_id": "hitl-cancel"}}

    graph.invoke({"messages": [HumanMessage("new customers?")]}, config)
    # The AG-UI adapter resumes a cancelled interrupt with a sentinel dict, not a string.
    finished = graph.invoke(Command(resume={"__agui_cancelled__": True}), config)

    assert finished["messages"][-2].content.startswith("The user did not answer")


class MixedCallsModel(FakeModel):
    """Calls ask_user together with a query in one turn (what the prompt forbids)."""

    def invoke(self, messages):
        self.calls.append(messages)
        if isinstance(messages[-1], HumanMessage):
            return AIMessage(content="", tool_calls=[
                {"id": "q1", "name": "sql_db_query", "args": {"query": "SELECT 1"}},
                {"id": "a1", "name": "ask_user", "args": {"question": "Which?", "options": ["a", "b"]}},
                {"id": "a2", "name": "ask_user", "args": {"question": "Again?", "options": ["c", "d"]}},
            ])
        return AIMessage(content="done")


def test_ask_user_is_enforced_alone(monkeypatch):
    monkeypatch.setattr(graph_module, "ChatOpenAI", lambda **kwargs: MixedCallsModel())
    graph = graph_module.create_graph()
    config = {"configurable": {"thread_id": "alone"}}

    paused = graph.invoke({"messages": [HumanMessage("q")]}, config)
    assert paused["__interrupt__"][0].value["message"] == "Which?"

    finished = graph.invoke(Command(resume="a"), config)
    ai_message = finished["messages"][1]
    assert [c["name"] for c in ai_message.tool_calls] == ["ask_user"]
    # The dropped sql_db_query never ran: only one tool result exists.
    tool_messages = [m for m in finished["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1


def test_interrupt_survives_restart(monkeypatch, tmp_path):
    """A paused ask_user can be resumed by a fresh graph on the same SQLite file."""
    import asyncio

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    monkeypatch.setattr(graph_module, "ChatOpenAI", lambda **kwargs: FakeModel())
    db = str(tmp_path / "checkpoints.db")
    config = {"configurable": {"thread_id": "restart"}}

    async def run():
        async with AsyncSqliteSaver.from_conn_string(db) as saver:
            graph = graph_module.create_graph(saver)
            paused = await graph.ainvoke({"messages": [HumanMessage("new customers?")]}, config)
            assert paused["__interrupt__"][0].value["reason"] == "ask_user"

        # "Restart": a new saver and graph on the same file.
        async with AsyncSqliteSaver.from_conn_string(db) as saver:
            graph = graph_module.create_graph(saver)
            return await graph.ainvoke(Command(resume="signup"), config)

    finished = asyncio.run(run())
    assert finished["messages"][-2].content == "The user answered: signup"
    assert finished["messages"][-1].content == "done"
