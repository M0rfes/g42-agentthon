import os
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Document,
    PropertyGraphIndex,
    Settings,
)
from llama_index.graph_stores.memgraph import MemgraphPropertyGraphStore
from models.llm import get_llama_index_llm, get_llama_index_embed_model
from utils.logging import logger

# Configure LlamaIndex globally to use centralized GitHub Models or standard OpenAI
Settings.llm = get_llama_index_llm()
Settings.embed_model = get_llama_index_embed_model()


PERSIST_DIR = "/app/data/storage" if os.path.exists("/.dockerenv") else "./data/storage"

def get_vector_index(documents=None) -> VectorStoreIndex:
    """
    Retrieves or creates a LlamaIndex VectorStoreIndex.
    If documents are provided, the index is built and persisted.
    """
    if documents:
        logger.info("index_manager_vector_create", document_count=len(documents))
        index = VectorStoreIndex.from_documents(documents)
        os.makedirs(PERSIST_DIR, exist_ok=True)
        index.storage_context.persist(persist_dir=PERSIST_DIR)
    else:
        if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
            logger.info("index_manager_vector_load_existing", directory=PERSIST_DIR)
            storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
            index = load_index_from_storage(storage_context)
        else:
            logger.info("index_manager_vector_create_empty")
            index = VectorStoreIndex.from_documents([])
    return index

def get_property_graph_index(documents=None) -> PropertyGraphIndex:
    """
    Retrieves or creates a LlamaIndex PropertyGraphIndex backed by Memgraph.
    If documents are provided, entities and relationships are extracted and loaded into Memgraph.
    """
    memgraph_url = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
    username = os.getenv("MEMGRAPH_USER", "")
    password = os.getenv("MEMGRAPH_PASSWORD", "")
    
    logger.info("index_manager_memgraph_connect", url=memgraph_url)
    
    graph_store = MemgraphPropertyGraphStore(
        username=username,
        password=password,
        url=memgraph_url,
    )
    
    # We define a custom LLM for property graph extraction
    llm = get_llama_index_llm()
    
    if documents:
        logger.info("index_manager_graph_create", document_count=len(documents))
        index = PropertyGraphIndex.from_documents(
            documents,
            property_graph_store=graph_store,
            llm=llm,
        )
    else:
        logger.info("index_manager_graph_load_existing")
        index = PropertyGraphIndex.from_existing(
            property_graph_store=graph_store,
            llm=llm,
        )
    return index

def index_scraped_content(url: str, title: str, text: str):
    """
    Wrapper function to index scraped text and load it into both Vector index and Memgraph.
    """
    logger.info("index_manager_scraped_content_start", url=url, title=title)
    
    # Construct LlamaIndex Document with metadata
    doc = Document(
        text=text,
        metadata={
            "url": url,
            "title": title
        }
    )
    
    # Update Vector Index
    vector_index = get_vector_index()
    vector_index.insert(doc)
    # Re-persist vector index
    os.makedirs(PERSIST_DIR, exist_ok=True)
    vector_index.storage_context.persist(persist_dir=PERSIST_DIR)
    
    # Update Property Graph Index (Memgraph)
    # GraphIndex does not have a simple .insert() in some LlamaIndex versions, so we re-initialize it with the document.
    get_property_graph_index(documents=[doc])
    
    logger.info("index_manager_scraped_content_success", url=url)
