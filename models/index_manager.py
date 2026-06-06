import os
import neo4j
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Document,
    PropertyGraphIndex,
    Settings,
)
from llama_index.graph_stores.memgraph import MemgraphPropertyGraphStore
from llama_index.graph_stores.memgraph.property_graph import (
    VECTOR_INDEX_NAME,
    BASE_ENTITY_LABEL,
)
from models.llm import get_llama_index_llm, get_llama_index_embed_model
from utils.logging import logger

# Configure LlamaIndex globally to use centralized GitHub Models or standard OpenAI
Settings.llm = get_llama_index_llm()
Settings.embed_model = get_llama_index_embed_model()


PERSIST_DIR = "/app/data/storage" if os.path.exists("/.dockerenv") else "./data/storage"

# ── Monkey-patch: fix MemgraphPropertyGraphStore's hardcoded 1536 dimension ───
#
# LlamaIndex's MemgraphPropertyGraphStore.verify_vector_support() always creates
# the vector index with dimension=1536 (the Ada-002 default). When using
# text-embedding-3-large (dim=3072) every entity upsert throws:
#   "Vector index property must have the same number of dimensions as specified in the index."
# Since we cannot change the library source, we monkey-patch the method to use
# the actual embedding dimension detected at runtime.

_EMBED_DIM: int | None = None


def _get_embed_dim() -> int:
    """Detect and cache the actual embedding dimension (one API call ever)."""
    global _EMBED_DIM
    if _EMBED_DIM is not None:
        return _EMBED_DIM
    try:
        em = get_llama_index_embed_model()
        _EMBED_DIM = len(em.get_text_embedding("dim"))
        logger.info("index_manager_embed_dim_detected", dimension=_EMBED_DIM)
    except Exception as e:
        logger.warning("index_manager_embed_dim_fallback", error=str(e), fallback=3072)
        _EMBED_DIM = 3072
    return _EMBED_DIM


def _patched_verify_vector_support(self) -> None:
    """
    Replacement for MemgraphPropertyGraphStore.verify_vector_support().
    Uses the actual embedding dimension instead of the hardcoded 1536.
    Only drops/recreates the index when the stored dimension marker doesn't match,
    preventing unnecessary drops across multiple MemgraphPropertyGraphStore instances.
    """
    dim = _get_embed_dim()
    response = self.structured_query("SHOW VERSION;")
    current_version = tuple(map(int, response[0]["version"].split(".")))
    required_version = (2, 22)

    if current_version < required_version:
        self._supports_vector_index = False
        logger.warning(
            "index_manager_memgraph_version_too_old",
            current=current_version,
            required=required_version,
        )
        return

    # Check stored dimension marker
    try:
        marker = self.structured_query(
            "MATCH (n:__VectorIndexMeta__) RETURN n.dimension AS dim LIMIT 1"
        )
        stored_dim = marker[0]["dim"] if marker else None
    except Exception:
        stored_dim = None

    if stored_dim == dim:
        # Index already correct — just mark as supported
        self._supports_vector_index = True
        logger.info("index_manager_vector_index_ok", dimension=dim)
        return

    # Dimension mismatch or first run — drop old index and recreate
    logger.warning(
        "index_manager_vector_index_recreating", old_dim=stored_dim, new_dim=dim
    )

    # Clear stale entities that have wrong-dimension embeddings
    try:
        self.structured_query(
            "MATCH (n:__Entity__) WHERE n.embedding IS NOT NULL DETACH DELETE n;"
        )
        logger.info("index_manager_stale_entities_cleared")
    except Exception:
        pass

    # Drop old vector index
    try:
        self.structured_query("DROP INDEX ON :__Entity__(embedding);")
        logger.info("index_manager_old_vector_index_dropped")
    except Exception:
        pass

    # Create correct-dimension index
    try:
        self.structured_query(
            f"CREATE VECTOR INDEX {VECTOR_INDEX_NAME} ON :{BASE_ENTITY_LABEL}(embedding) "
            f'WITH CONFIG {{"dimension": {dim}, "capacity": 1000}};'
        )
        self._supports_vector_index = True
        logger.info("index_manager_vector_index_created", dimension=dim)
    except neo4j.exceptions.Neo4jError as e:
        self._supports_vector_index = True
        logger.info(
            "index_manager_vector_index_already_exists", dimension=dim, detail=str(e)
        )

    # Store dimension marker for future checks
    try:
        self.structured_query(
            "MERGE (n:__VectorIndexMeta__) SET n.dimension = $dim",
            param_map={"dim": dim},
        )
    except Exception:
        pass


# Apply the monkey-patch once at import time
MemgraphPropertyGraphStore.verify_vector_support = _patched_verify_vector_support
logger.info("index_manager_memgraph_patch_applied")


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


_GRAPH_STORE: MemgraphPropertyGraphStore | None = None


def get_property_graph_index(documents=None) -> PropertyGraphIndex:
    """
    Retrieves or creates a LlamaIndex PropertyGraphIndex backed by Memgraph.
    Entity node embedding is disabled (embed_kg_nodes=False) because:
    - The synthesis node uses a separate VectorStoreIndex for semantic search.
    - Entity embeddings in Memgraph trigger a vector index dimension check that
      conflicts with LlamaIndex's hardcoded 1536-dim default vs our 3072-dim model.
    - Triplet extraction (entities + relationships) works fully without embeddings.
    """
    global _GRAPH_STORE
    memgraph_url = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
    username = os.getenv("MEMGRAPH_USER", "")
    password = os.getenv("MEMGRAPH_PASSWORD", "")

    if _GRAPH_STORE is None:
        logger.info("index_manager_memgraph_connect", url=memgraph_url)
        _GRAPH_STORE = MemgraphPropertyGraphStore(
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
            property_graph_store=_GRAPH_STORE,
            llm=llm,
            embed_kg_nodes=False,  # Avoid Memgraph vector index dimension conflicts
        )
    else:
        logger.info("index_manager_graph_load_existing")
        index = PropertyGraphIndex.from_existing(
            property_graph_store=_GRAPH_STORE,
            llm=llm,
            embed_kg_nodes=False,  # Avoid Memgraph vector index dimension conflicts
        )
    return index


def index_scraped_content(url: str, title: str, text: str):
    """
    Wrapper function to index scraped text and load it into both Vector index and Memgraph.
    """
    logger.info("index_manager_scraped_content_start", url=url, title=title)

    # Construct LlamaIndex Document with metadata
    doc = Document(text=text, metadata={"url": url, "title": title})

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
