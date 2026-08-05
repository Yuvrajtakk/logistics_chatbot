"""
chat_cli.py
-----------
Phase 8: The terminal interface for the logistics chatbot.

Ties together orchestrator.py, answer_synth.py, and memory.py into an
interactive loop. Handles setting the LLM provider globally at startup.
"""

import argparse
import sys
import os

# Ensure the script can run from anywhere by adding the project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import src.llm_client
from src.orchestrator import orchestrate
from src.answer_synth import synthesize_answer
from src.memory import ConversationMemory

def main():
    parser = argparse.ArgumentParser(description="Logistics & Order Intelligence Chatbot")
    parser.add_argument(
        "--provider",
        type=str,
        default=src.llm_client.DEFAULT_PROVIDER,
        help="LLM provider to use (groq, gemini, ollama). Defaults to groq."
    )
    args = parser.parse_args()

    # Override the default provider globally so downstream files (orchestrator,
    # sql_agent, answer_synth) use the chosen provider when calling get_llm().
    src.llm_client.DEFAULT_PROVIDER = args.provider

    print("=" * 60)
    print(f"📦 Logistics Chatbot initialized (Provider: {args.provider.upper()})")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 60)

    memory = ConversationMemory()

    while True:
        try:
            # Prompt the user
            question = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not question:
            continue

        if question.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        print("\n[Thinking...]")
        
        # 1. Orchestrate (classify, run pipelines)
        result = orchestrate(question, memory=memory)
        
        # 2. Synthesize plain English answer
        answer = synthesize_answer(question, result)
        
        # 3. Present to user
        print(f"\nBot: {answer}")
        
        # 4. Record the turn in memory
        route = result.get("route", "unknown")
        memory.add_turn(question=question, tool=route, answer=answer)


if __name__ == "__main__":
    main()
