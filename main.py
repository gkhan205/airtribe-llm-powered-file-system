"""
main.py

Run this file to chat with the file assistant in the terminal:
    python main.py
"""

import os

from dotenv import load_dotenv

from llm_file_assistant import FileAssistant


def main():
    # Load CLAUDE_API_KEY and CLAUDE_MODEL from the .env file
    load_dotenv()

    if not os.getenv("CLAUDE_API_KEY"):
        print("Error: CLAUDE_API_KEY is not set.")
        print("Copy .env.example to .env and add your Claude API key.")
        return

    assistant = FileAssistant()

    print("=== LLM File Assistant ===")
    print("Ask me about the resumes. Type 'exit' to quit.")
    print("Examples:")
    print("  - Read all resumes in the resumes folder")
    print("  - Find resumes mentioning Python experience")
    print("  - Create a summary file for resume_john_doe.pdf")

    while True:
        try:
            question = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if question == "":
            continue

        if question.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            answer = assistant.ask(question)
        except Exception as error:
            print(f"Something went wrong: {error}")
            continue

        print(f"\nAssistant: {answer}")


if __name__ == "__main__":
    main()
