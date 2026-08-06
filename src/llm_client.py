import os
from contextvars import ContextVar
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

load_dotenv()

DEFAULT_PROVIDER = "groq"
REQUEST_PROVIDER: ContextVar[str | None] = ContextVar("request_provider", default=None)
TEMPERATURE = 0

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
OLLAMA_MODEL = "qwen2.5:7b"

def get_llm(provider: str = None):
    """
    Returns a LangChain chat model instance based on the specified provider.
    
    Args:
        provider (str, optional): The name of the provider ('groq', 'gemini', 'ollama').
                                  Defaults to DEFAULT_PROVIDER.
                                  
    Returns:
        BaseChatModel: A LangChain chat model instance.
    """
    if provider is None:
        provider = REQUEST_PROVIDER.get() or DEFAULT_PROVIDER
    provider = provider.lower()

    if provider == "groq":
        return ChatGroq(model=GROQ_MODEL, temperature=TEMPERATURE)
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=TEMPERATURE)
    elif provider == "ollama":
        return ChatOllama(model=OLLAMA_MODEL, temperature=TEMPERATURE)
    else:
        print(f"[llm_client] Unknown provider '{provider}', falling back to '{DEFAULT_PROVIDER}'.")
        return get_llm(DEFAULT_PROVIDER)
