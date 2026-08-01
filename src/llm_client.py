# os lets us read environment variables (our API keys) once dotenv
# has loaded them from the .env file into the process's environment.
import os

# load_dotenv() reads the .env file sitting in the repo root and
# copies its contents (GROQ_API_KEY=..., GOOGLE_API_KEY=...) into
# os.environ, as if you'd typed them into the terminal by hand.
from dotenv import load_dotenv

# The three provider-specific chat model classes. This is the ONLY
# file in the whole project allowed to import these directly —
# PROJECT.md Section 9 is explicit about this. Every other file
# only ever touches whatever get_llm() hands back.
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama


# Run this once, at import time, so the keys are in os.environ
# before anything below tries to use them.
load_dotenv()

# If someone calls get_llm() with no argument, or a misspelled one,
# this is what we quietly fall back to instead of crashing.
# (Your call, Yuraj — Option B: never crash, fall back safely.)
DEFAULT_PROVIDER = "groq"

# temperature=0 means "always pick the most likely next word, no
# randomness." For SQL generation this matters a lot — you want the
# SAME question to produce the SAME query every time, not a slightly
# different one each run. Creative writing wants temperature UP;
# correctness-critical code generation wants it at 0.
TEMPERATURE = 0

# Exact model name each provider expects. If a provider updates their
# lineup later, this is the only place you'd ever need to change it.
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
OLLAMA_MODEL = "qwen2.5:7b"   # matches what you already pulled

def get_llm(provider: str = None):
    """
    The one and only place in this project that knows how to build
    an LLM. Give it a provider name, get back a ready-to-use
    LangChain chat model with an identical interface no matter which
    one you asked for.

    provider: "groq", "gemini", "ollama", or None/anything else
               (falls back to DEFAULT_PROVIDER, never crashes).
    """

    # Normalize input: None becomes the default, and whatever string
    # comes in gets lowercased so "Groq", "GROQ", "groq" all work
    # the same way — small kindness, costs nothing.
    if provider is None:
        provider = DEFAULT_PROVIDER
    provider = provider.lower()

    if provider == "groq":
        # ChatGroq automatically reads GROQ_API_KEY from os.environ —
        # we don't have to pass it in by hand, dotenv already put it there.
        return ChatGroq(model=GROQ_MODEL, temperature=TEMPERATURE)

    elif provider == "gemini":
        # Same story — ChatGoogleGenerativeAI auto-reads GOOGLE_API_KEY.
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=TEMPERATURE)

    elif provider == "ollama":
        # No API key needed at all — this one talks to the Ollama
        # service running locally on your machine, not the internet.
        return ChatOllama(model=OLLAMA_MODEL, temperature=TEMPERATURE)

    else:
        # Unknown provider name (a typo, or someone testing us on
        # purpose). Per your choice: don't crash — warn plainly on
        # the console so it's visible if something looks "off" later,
        # then quietly hand back the default provider instead.
        print(f"[llm_client] Unknown provider '{provider}', falling back to '{DEFAULT_PROVIDER}'.")
        return get_llm(DEFAULT_PROVIDER)