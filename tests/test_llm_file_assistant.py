"""
Tests for llm_file_assistant.py.

We don't call the real Claude API here. Instead, FakeClient pretends to be
the Anthropic client and returns answers we decide in advance.
"""

import json
from types import SimpleNamespace

from llm_file_assistant import TOOL_FUNCTIONS, TOOLS, FileAssistant, run_tool

# ---------- helpers to build fake Claude responses ----------


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(block_id, name, arguments):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=arguments)


def fake_response(blocks, stop_reason="end_turn"):
    return SimpleNamespace(content=blocks, stop_reason=stop_reason)


def tool_response(*blocks):
    return fake_response(list(blocks), stop_reason="tool_use")


class FakeClient:
    """Pretends to be anthropic.Anthropic(). Returns the given responses one by one."""

    def __init__(self, responses):
        self.responses = responses
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        # save a copy of the messages, because the assistant keeps adding to the list
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


# ---------- run_tool ----------


def test_every_tool_has_a_function():
    tool_names = [tool["name"] for tool in TOOLS]
    assert sorted(tool_names) == sorted(TOOL_FUNCTIONS.keys())


def test_run_tool_list_files():
    result = run_tool("list_files", {"directory": "sample_data/resumes"})
    assert result["success"] is True
    assert result["count"] == 8


def test_run_tool_read_file():
    result = run_tool("read_file", {"filepath": "sample_data/resumes/resume_john_doe.pdf"})
    assert result["success"] is True
    assert "John Doe" in result["content"]


def test_run_tool_unknown_tool():
    result = run_tool("delete_everything", {})
    assert result["success"] is False


def test_run_tool_arguments_not_a_dict():
    result = run_tool("read_file", "not a dict")
    assert result["success"] is False


def test_run_tool_wrong_arguments():
    result = run_tool("read_file", {"wrong_name": "x"})
    assert result["success"] is False


# ---------- FileAssistant ----------


def test_answer_without_tools():
    client = FakeClient([fake_response([text_block("Hello!")])])
    assistant = FileAssistant(client=client, model="test-model", show_tool_calls=False)

    assert assistant.ask("hi") == "Hello!"
    assert client.requests[0]["model"] == "test-model"
    assert client.requests[0]["tools"] == TOOLS


def test_assistant_calls_a_tool():
    client = FakeClient(
        [
            tool_response(tool_use_block("tool_1", "list_files", {"directory": "sample_data/resumes"})),
            fake_response([text_block("There are 8 resumes.")]),
        ]
    )
    assistant = FileAssistant(client=client, show_tool_calls=False)

    answer = assistant.ask("How many resumes are there?")

    assert answer == "There are 8 resumes."
    # The tool result should be sent back to Claude in the second request
    last_message = client.requests[1]["messages"][-1]
    assert last_message["role"] == "user"
    tool_result = last_message["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "tool_1"
    assert json.loads(tool_result["content"])["count"] == 8


def test_several_tools_in_one_reply():
    client = FakeClient(
        [
            tool_response(
                text_block("Let me search both files."),
                tool_use_block(
                    "a", "search_in_file",
                    {"filepath": "sample_data/resumes/resume_john_doe.pdf", "keyword": "python"},
                ),
                tool_use_block(
                    "b", "search_in_file",
                    {"filepath": "sample_data/resumes/resume_alex_johnson.txt", "keyword": "python"},
                ),
            ),
            fake_response([text_block("Only John Doe mentions Python.")]),
        ]
    )
    assistant = FileAssistant(client=client, show_tool_calls=False)
    assistant.ask("Who knows Python?")

    # Both results must come back together in one message
    results = client.requests[1]["messages"][-1]["content"]
    assert [result["tool_use_id"] for result in results] == ["a", "b"]
    counts = [json.loads(result["content"])["match_count"] for result in results]
    assert counts[0] > 0
    assert counts[1] == 0


def test_assistant_creates_summary_file(tmp_path):
    summary_path = str(tmp_path / "summary_john_doe.txt")
    client = FakeClient(
        [
            tool_response(
                tool_use_block("t1", "read_file", {"filepath": "sample_data/resumes/resume_john_doe.pdf"})
            ),
            tool_response(
                tool_use_block(
                    "t2", "write_file",
                    {"filepath": summary_path, "content": "John is a Python developer."},
                )
            ),
            fake_response([text_block("Summary saved.")]),
        ]
    )
    assistant = FileAssistant(client=client, show_tool_calls=False)

    assert assistant.ask("Create a summary for John Doe") == "Summary saved."
    with open(summary_path) as file:
        assert file.read() == "John is a Python developer."


def test_assistant_stops_after_too_many_steps():
    # The fake Claude keeps asking for tools and never gives an answer
    responses = [
        tool_response(tool_use_block(f"t{i}", "list_files", {"directory": "."}))
        for i in range(10)
    ]
    assistant = FileAssistant(client=FakeClient(responses), show_tool_calls=False)

    answer = assistant.ask("loop forever")
    assert "could not finish" in answer


def test_assistant_handles_refusal():
    client = FakeClient([fake_response([], stop_reason="refusal")])
    assistant = FileAssistant(client=client, show_tool_calls=False)
    assert "declined" in assistant.ask("something bad")


def test_assistant_remembers_conversation():
    client = FakeClient(
        [fake_response([text_block("First answer")]), fake_response([text_block("Second")])]
    )
    assistant = FileAssistant(client=client, show_tool_calls=False)

    assistant.ask("first question")
    assistant.ask("second question")

    messages = client.requests[1]["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == "first question"
    assert messages[2]["content"] == "second question"
