"""
llm_file_assistant.py

Connects the tools from fs_tools.py to Claude (Anthropic).
Claude decides which tool to call, we run the tool,
send the result back, and Claude writes the final answer.
"""

import json
import os

import anthropic

import fs_tools

DEFAULT_MODEL = "claude-opus-5-5"
MAX_STEPS = 10  # stop if Claude keeps calling tools forever

SYSTEM_PROMPT = """You are a helpful assistant that works with resume files.
The resumes are in the folder 'sample_data/resumes'.

Rules:
- Use list_files to see which files exist before reading or searching them.
- To find resumes that mention a skill, use search_in_file on every resume.
- When asked to create a summary, read the resume first, then save the summary
  with write_file in the 'output' folder (for example output/summary_john_doe.txt).
- Only use information that comes from the tools. Do not make things up.
- Keep your answers short and clear."""

# Descriptions of our tools in the format Claude expects
TOOLS = [
    {
        "name": "read_file",
        "description": "Read a resume file (PDF, TXT or DOCX) and return its text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to the file"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "list_files",
        "description": "List the files in a folder. Can filter by extension like '.pdf'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Folder to list"},
                "extension": {"type": "string", "description": "Optional, e.g. '.pdf'"},
            },
            "required": ["directory"],
        },
    },
    {
        "name": "write_file",
        "description": "Write text to a file. Creates folders if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Where to save the file"},
                "content": {"type": "string", "description": "Text to write"},
            },
            "required": ["filepath", "content"],
        },
    },
    {
        "name": "search_in_file",
        "description": "Search for a keyword in a file (case-insensitive).",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "File to search in"},
                "keyword": {"type": "string", "description": "Word to look for"},
            },
            "required": ["filepath", "keyword"],
        },
    },
]

# Connects each tool name to the real Python function
TOOL_FUNCTIONS = {
    "read_file": fs_tools.read_file,
    "list_files": fs_tools.list_files,
    "write_file": fs_tools.write_file,
    "search_in_file": fs_tools.search_in_file,
}


def run_tool(name, arguments):
    """Run the tool Claude asked for and return the result as a dict."""
    if name not in TOOL_FUNCTIONS:
        return {"success": False, "error": f"Unknown tool: {name}"}

    if not isinstance(arguments, dict):
        return {"success": False, "error": "Tool arguments must be a dictionary"}

    try:
        result = TOOL_FUNCTIONS[name](**arguments)
    except TypeError as error:
        return {"success": False, "error": f"Wrong arguments for {name}: {error}"}

    # list_files returns a list, so wrap it in a dict like the other tools
    if name == "list_files":
        result = {"success": True, "count": len(result), "files": result}

    return result


def get_text(response):
    """Join all the text blocks in Claude's reply into one string."""
    parts = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)


class FileAssistant:
    """A chat assistant that can use the file tools."""

    def __init__(self, client=None, model=None, show_tool_calls=True):
        self.client = client or anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        self.model = model or os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
        self.show_tool_calls = show_tool_calls
        self.messages = []

    def ask(self, question):
        """Send a question to Claude and return its final answer."""
        self.messages.append({"role": "user", "content": question})

        for _ in range(MAX_STEPS):
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.messages,
                # If Claude declines a request, retry it on a fallback model automatically
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )

            # Save Claude's whole reply (text and tool requests) in the history
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "Sorry, Claude declined to answer this request."

            # If Claude is not asking for a tool, this is the final answer
            if response.stop_reason != "tool_use":
                return get_text(response)

            # Run every tool Claude asked for and collect the results
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if self.show_tool_calls:
                    print(f"  [tool] {block.name}({json.dumps(block.input)})")

                result = run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

            # Send all the results back to Claude in one message
            self.messages.append({"role": "user", "content": tool_results})

        return "Sorry, I could not finish this request. Please try again."
