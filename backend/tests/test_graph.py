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
