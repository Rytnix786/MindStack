"""Document ingestion pipeline for the RAG system."""

import hashlib
import importlib
import pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from .config import settings
except ImportError:  # pragma: no cover
    from config import settings


COLLECTION_NAME = "rag_documents"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
BM25_INDEX_PATH = Path("./bm25_index.pkl")


def _get_chroma_persist_dir() -> str:
    """Return persist dir from settings with compatibility for different naming styles."""
    return str(
        getattr(
            settings,
            "CHROMA_PERSIST_DIR",
            getattr(settings, "chroma_persist_dir", "./chroma_db"),
        )
    )


def _load_documents(data_dir: Path) -> Tuple[List[Any], int]:
    """Load PDF and document files; continue on per-file errors."""
    supported = {".pdf", ".md", ".txt", ".doc", ".docx"}
    loaded_docs: List[Any] = []

    loaders_module = importlib.import_module("langchain_community.document_loaders")
    py_pdf_loader = getattr(loaders_module, "PyPDFLoader")
    text_loader = getattr(loaders_module, "TextLoader")
    docx_loader = getattr(loaders_module, "Docx2txtLoader", None)
    documents_processed = 0

    for file_path in sorted(data_dir.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in supported:
            continue

        try:
            if file_path.suffix.lower() == ".pdf":
                loader = py_pdf_loader(str(file_path))
            elif file_path.suffix.lower() == ".docx" and docx_loader is not None:
                loader = docx_loader(str(file_path))
            else:
                loader = text_loader(str(file_path), encoding="utf-8", autodetect_encoding=True)

            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = file_path.name
            loaded_docs.extend(docs)
            documents_processed += 1
            print(f"Loaded: {file_path.name}")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Failed to load {file_path.name}: {exc}")

    return loaded_docs, documents_processed


def _split_and_enrich_metadata(documents: List[Any]) -> List[Any]:
    """Split input documents and enrich each chunk with required metadata fields."""
    splitter_module = importlib.import_module("langchain.text_splitter")
    recursive_splitter = getattr(splitter_module, "RecursiveCharacterTextSplitter")
    splitter = recursive_splitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    per_source_total = Counter(doc.metadata.get("source", "unknown") for doc in chunks)
    per_source_index = defaultdict(int)

    for chunk in chunks:
        source = str(chunk.metadata.get("source", "unknown"))
        per_source_index[source] += 1
        chunk.metadata["source"] = source
        chunk.metadata["chunk_index"] = per_source_index[source]
        chunk.metadata["total_chunks"] = per_source_total[source]

    return chunks


def _build_chunk_id(chunk: Any) -> str:
    source = str(chunk.metadata.get("source", "unknown"))
    chunk_index = int(chunk.metadata.get("chunk_index", 0))
    digest = hashlib.md5(chunk.page_content.encode("utf-8")).hexdigest()[:12]
    return f"{source}:{chunk_index}:{digest}"


def _store_in_chroma(chunks: List[Any], persist_dir: str) -> None:
    """Store chunks in Chroma and avoid duplicate writes based on deterministic IDs."""
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    embeddings_module = importlib.import_module("langchain_community.embeddings")
    vectorstores_module = importlib.import_module("langchain_community.vectorstores")
    huggingface_embeddings = getattr(embeddings_module, "HuggingFaceEmbeddings")
    chroma = getattr(vectorstores_module, "Chroma")

    embeddings = huggingface_embeddings(model_name=EMBEDDING_MODEL_NAME)
    vectorstore = chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

    existing_ids = set(vectorstore.get(include=[]).get("ids", []))
    new_docs: List[Any] = []
    new_ids: List[str] = []

    for chunk in chunks:
        chunk_id = _build_chunk_id(chunk)
        if chunk_id in existing_ids:
            continue
        new_docs.append(chunk)
        new_ids.append(chunk_id)

    if new_docs:
        vectorstore.add_documents(new_docs, ids=new_ids)
        vectorstore.persist()
        print(f"Added {len(new_docs)} new chunks to Chroma collection '{COLLECTION_NAME}'.")
    else:
        print("No new chunks to add to Chroma; all chunks already exist.")


def _build_and_save_bm25(chunks: List[Any], output_path: Path) -> None:
    """Create a BM25 index from chunk text and persist it as a pickle file."""
    bm25_module = importlib.import_module("rank_bm25")
    bm25_okapi = getattr(bm25_module, "BM25Okapi")
    tokenized_corpus = [chunk.page_content.lower().split() for chunk in chunks]
    bm25 = bm25_okapi(tokenized_corpus) if tokenized_corpus else None

    payload = {
        "bm25": bm25,
        "documents": [
            {"page_content": chunk.page_content, "metadata": chunk.metadata} for chunk in chunks
        ],
        "tokenized_corpus": tokenized_corpus,
    }
    with output_path.open("wb") as file_obj:
        pickle.dump(payload, file_obj)

    print(f"BM25 index saved to {output_path}")


def load_and_chunk_documents(data_dir: str) -> List[Dict[str, object]]:
    """Compatibility helper returning chunk records as dictionaries."""
    data_path = Path(data_dir)
    if not data_path.exists():
        return []

    documents, _ = _load_documents(data_path)
    chunks = _split_and_enrich_metadata(documents) if documents else []

    return [
        {
            "source": str(chunk.metadata.get("source", "unknown")),
            "chunk_id": int(chunk.metadata.get("chunk_index", 0)),
            "content": chunk.page_content,
        }
        for chunk in chunks
    ]


def ingest_documents(data_dir: str) -> dict:
    """Run full ingestion pipeline and return summary statistics."""
    print("Starting ingestion pipeline...")

    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    print("Step 1/5: Loading source documents...")
    documents, documents_processed = _load_documents(data_path)
    print(f"Loaded {documents_processed} documents.")

    print("Step 2/5: Splitting documents into chunks...")
    chunks = _split_and_enrich_metadata(documents) if documents else []
    print(f"Created {len(chunks)} chunks.")

    print("Step 3/5: Generating embeddings and storing in ChromaDB...")
    chroma_persist_dir = _get_chroma_persist_dir()
    _store_in_chroma(chunks, chroma_persist_dir)

    print("Step 4/5: Building BM25 index from chunks...")
    _build_and_save_bm25(chunks, BM25_INDEX_PATH)

    print("Step 5/5: Finalizing ingestion summary...")
    summary = {
        "chunks_created": len(chunks),
        "documents_processed": documents_processed,
        "collection_name": COLLECTION_NAME,
    }
    print(f"Ingestion complete: {summary}")
    return summary


if __name__ == "__main__":
    ingest_documents("./data")
