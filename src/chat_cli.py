import argparse
import sys
import os

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

    # Override the default provider globally for all downstream modules
    src.llm_client.DEFAULT_PROVIDER = args.provider

    print("=" * 60)
    print(f"📦 Logistics Chatbot initialized (Provider: {args.provider.upper()})")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 60)

    memory = ConversationMemory()

    while True:
        try:
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
        
        result = orchestrate(question, memory=memory)
        answer = synthesize_answer(question, result)
        
        print(f"\nBot: {answer}")
        
        route = result.get("route", "unknown")
        memory.add_turn(question=question, tool=route, answer=answer)

if __name__ == "__main__":
    main()
