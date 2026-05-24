import os
from llama_index.llms.openai import OpenAI as LlamaIndexOpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from langchain_openai import ChatOpenAI as LangChainChatOpenAI
from utils.logging import logger

def get_llama_index_llm() -> LlamaIndexOpenAI:
    """
    Constructs and returns the LlamaIndex LLM using GitHub Models as the inference backend.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    backend = os.getenv("BACKEND")

    logger.info("llm_construction_llama_index", backend=backend, model=model_name)
    return LlamaIndexOpenAI(
        model=model_name,
        api_key=api_key,
        api_base=base_url,
        temperature=0,
        max_tokens=4096
    )

def get_langchain_llm() -> LangChainChatOpenAI:
    """
    Constructs and returns the LangChain ChatOpenAI LLM using GitHub Models as the inference backend.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    backend = os.getenv("BACKEND")
    
    logger.info("llm_construction_langchain", backend=backend, model=model_name)
    return LangChainChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        max_tokens=4096
    )

def get_llama_index_embed_model() -> OpenAIEmbedding:
    """
    Constructs and returns the LlamaIndex embedding model using GitHub Models or fallback standard OpenAI.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    backend = os.getenv("BACKEND")
    
    logger.info("embed_construction_llama_index", backend=backend, model=model_name)
    return OpenAIEmbedding(
        model=model_name,
        api_key=api_key,
        api_base=base_url,
    )
