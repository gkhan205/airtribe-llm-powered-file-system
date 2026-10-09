# LLM-Powered File System Assistant

A terminal chat app where Claude (Anthropic) reads, lists, searches and writes resume files by calling Python functions (tools).

## Demo video

[demo-video.mov](demo-video.mov) is a 2-3 minute recording of the assistant answering questions by calling the file tools.

<video src="demo-video.mov" controls width="100%"></video>
## Project structure

```
main.py                  -> run this to chat in the terminal
demo-video.mov           -> demo video of tool calling in action
fs_tools.py              -> Part A: the file tools (read, list, write, search)
llm_file_assistant.py    -> Part B: connects the tools to Claude
sample_data/resumes/     -> 8 dummy resumes (PDF, DOCX, TXT)
tests/                   -> pytest tests
requirements.txt
```

## Setup

1. Create a virtual environment and install the packages:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Add your Claude API key:

   ```bash
   cp .env.example .env
   ```

   Then open `.env` and set `CLAUDE_API_KEY=sk-ant-...`. `CLAUDE_MODEL` is optional (default: `claude-haiku-5-5`).

## How to run

```bash
python main.py
```

Then type a question. Example:

```
You: Find resumes mentioning Python experience
  [tool] list_files({"directory": "sample_data/resumes"})
  [tool] search_in_file({"filepath": "sample_data/resumes/resume_john_doe.pdf", "keyword": "Python"})
  ...

Assistant: These resumes mention Python: John Doe, Jane Smith, Carlos Mendez and Emily Chen.
```

More things to try:

- `Read all resumes in the resumes folder`
- `Create a summary file for resume_john_doe.pdf` (the summary is saved in `output/`)
- `List only the PDF resumes`

Type `exit` to quit.

## The tools (fs_tools.py)

| Function                                  | What it does                                                                                      |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `read_file(filepath)`                   | Reads a`.pdf`, `.docx` or `.txt` file and returns its text and metadata                     |
| `list_files(directory, extension=None)` | Lists the files in a folder with name, size and modified date. Can filter by extension            |
| `write_file(filepath, content)`         | Writes text to a file and creates the folders if needed                                           |
| `search_in_file(filepath, keyword)`     | Finds lines containing the keyword (case-insensitive) and returns them with the lines around them |

The tools return a dictionary with `"success": True` or `"success": False` plus an `"error"` message, so the program does not crash on bad input.

You can also use them directly:

```python
import fs_tools

fs_tools.list_files("sample_data/resumes", ".pdf")
fs_tools.read_file("sample_data/resumes/resume_john_doe.pdf")
fs_tools.search_in_file("sample_data/resumes/resume_john_doe.pdf", "python")
fs_tools.write_file("output/notes.txt", "Hello")
```

## How the LLM part works

1. The user's question and a description of the 4 tools (`TOOLS`) are sent to Claude.
2. If Claude wants a tool, it replies with `stop_reason == "tool_use"` and one or more `tool_use` blocks (a tool name plus arguments).
3. `run_tool()` runs the matching Python function, and all the results are sent back together as `tool_result` blocks.
4. Steps 2 and 3 repeat until Claude gives its final answer. There are at most 10 steps.

## Running the tests

```bash
pytest
```

- `tests/test_fs_tools.py` tests each file tool, including error cases.
- `tests/test_llm_file_assistant.py` tests the assistant with a fake Claude client, so no API key or internet is needed.

## Sample data

The 8 resumes in `sample_data/resumes/` are made up (3 PDF, 3 DOCX, 2 TXT). Four of them mention Python, so you can try the search example.
