# # rag_engine.py
# """
# Retrieval engine over the unified knowledge corpus (knowledge_base.KnowledgeBase).

# Two backends, same interface (`.search(query, top_k) -> List[dict]`):

#   * ChromaEmbeddingBackend  -- BAAI/bge-small-en-v1.5 + ChromaDB. Used when
#     sentence-transformers/chromadb are installed. Semantic search.

#   * TfidfBackend            -- scikit-learn TF-IDF + cosine similarity.
#     Zero extra downloads, works anywhere pandas/sklearn already run.
#     Used automatically when the embedding stack isn't available.

# This means `rag_engine.search()` NEVER silently returns nothing just
# because a heavy dependency wasn't installed â€” which was the core bug in
# the previous version (the corpus was never populated at all, in either
# backend).
# """
# from typing import Dict, List

# import config

# try:
#     from sentence_transformers import SentenceTransformer
#     import chromadb
#     from chromadb.config import Settings
#     _EMBEDDING_STACK_AVAILABLE = True
# except ImportError:
#     _EMBEDDING_STACK_AVAILABLE = False

# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity


# class ChromaEmbeddingBackend:
#     def __init__(self, collection_name: str = config.RAG_COLLECTION_NAME):
#         self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
#         client = chromadb.PersistentClient(
#             path=config.CHROMA_DIR,
#             settings=Settings(anonymized_telemetry=False),
#         )
#         # Fresh collection every load so it always matches the current corpus
#         # (avoids stale/half-populated collections from earlier runs).
#         try:
#             client.delete_collection(collection_name)
#         except Exception:
#             pass
#         self.collection = client.create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

#     def index(self, chunks: List[str], sources: List[str]) -> None:
#         batch_size = 100
#         for i in range(0, len(chunks), batch_size):
#             batch = chunks[i:i + batch_size]
#             batch_sources = sources[i:i + batch_size]
#             embeddings = self.embedding_model.encode(batch, show_progress_bar=False).tolist()
#             self.collection.add(
#                 embeddings=embeddings,
#                 documents=batch,
#                 metadatas=[{"source": s} for s in batch_sources],
#                 ids=[f"doc_{i + j}" for j in range(len(batch))],
#             )

#     def search(self, query: str, top_k: int) -> List[Dict]:
#         query_embedding = self.embedding_model.encode([query]).tolist()
#         results = self.collection.query(
#             query_embeddings=query_embedding, n_results=top_k,
#             include=["documents", "metadatas", "distances"],
#         )
#         docs = results.get("documents", [[]])[0]
#         metas = results.get("metadatas", [[]])[0]
#         dists = results.get("distances", [[]])[0]
#         out = []
#         for doc, meta, dist in zip(docs, metas, dists):
#             similarity = max(0.0, 1 - dist)
#             out.append({
#                 "text": doc,
#                 "source": meta.get("source", "unknown"),
#                 "relevance_score": round(similarity, 3),
#                 "confidence": _confidence_label(similarity),
#             })
#         return out


# class TfidfBackend:
#     def __init__(self):
#         self.vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
#         self.matrix = None
#         self.chunks: List[str] = []
#         self.sources: List[str] = []

#     def index(self, chunks: List[str], sources: List[str]) -> None:
#         self.chunks = chunks
#         self.sources = sources
#         self.matrix = self.vectorizer.fit_transform(chunks)

#     def search(self, query: str, top_k: int) -> List[Dict]:
#         if self.matrix is None or not self.chunks:
#             return []
#         q_vec = self.vectorizer.transform([query])
#         sims = cosine_similarity(q_vec, self.matrix)[0]
#         top_idx = sims.argsort()[::-1][:top_k]
#         out = []
#         for i in top_idx:
#             score = float(sims[i])
#             if score <= 0:
#                 continue
#             out.append({
#                 "text": self.chunks[i],
#                 "source": self.sources[i],
#                 "relevance_score": round(score, 3),
#                 "confidence": _confidence_label(score),
#             })
#         return out


# def _confidence_label(score: float) -> str:
#     if score > 0.55:
#         return "HIGH"
#     if score > 0.3:
#         return "MEDIUM"
#     return "LOW"


# class RAGEngine:
#     def __init__(self):
#         self.backend_name = "none"
#         self.backend = None
#         self.corpus_size = 0

#     def build(self, chunks: List[str], sources: List[str]) -> None:
#         if not chunks:
#             return
#         if _EMBEDDING_STACK_AVAILABLE:
#             try:
#                 self.backend = ChromaEmbeddingBackend()
#                 self.backend.index(chunks, sources)
#                 self.backend_name = "chroma+bge-small"
#                 self.corpus_size = len(chunks)
#                 return
#             except Exception:
#                 # Falls through to TF-IDF below (e.g. no internet to
#                 # download the embedding model weights the first time)
#                 pass
#         self.backend = TfidfBackend()
#         self.backend.index(chunks, sources)
#         self.backend_name = "tfidf"
#         self.corpus_size = len(chunks)

#     def search(self, query: str, top_k: int = config.RAG_TOP_K) -> List[Dict]:
#         if not self.backend:
#             return []
#         return self.backend.search(query, top_k)

#     @property
#     def is_active(self) -> bool:
#         return self.backend is not None
# rag_engine.py
"""
Retrieval engine over the unified knowledge corpus (knowledge_base.KnowledgeBase).
"""
from typing import Dict, List
import time
import hashlib

import config

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    _EMBEDDING_STACK_AVAILABLE = True
except ImportError:
    _EMBEDDING_STACK_AVAILABLE = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ChromaEmbeddingBackend:
    def __init__(self, collection_name: str = config.RAG_COLLECTION_NAME):
        print("ðŸ”„ Loading embedding model (BAAI/bge-small-en-v1.5)...")
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
        print("âœ… Embedding model loaded")
        
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection_name = collection_name
        self.collection = None
        
        # Check if collection already exists
        existing_collections = self.client.list_collections()
        collection_names = [c.name for c in existing_collections]
        
        if collection_name in collection_names:
            print(f"ðŸ“š Found existing ChromaDB collection '{collection_name}'")
            print("   âœ… Using cached index (no re-indexing needed)")
            self.collection = self.client.get_collection(collection_name)
            self._is_cached = True
        else:
            print(f"ðŸ†• Creating new ChromaDB collection '{collection_name}'")
            self.collection = self.client.create_collection(
                name=collection_name, 
                metadata={"hnsw:space": "cosine"}
            )
            self._is_cached = False

    def index(self, chunks: List[str], sources: List[str]) -> None:
        # If collection already exists, skip indexing
        if self._is_cached:
            # Verify the count matches
            count = self.collection.count()
            if count == len(chunks):
                print(f"âœ… Using existing index with {count:,} chunks")
                return
            else:
                print(f"âš ï¸ Cache mismatch: expected {len(chunks):,} chunks, found {count:,}")
                print("   Rebuilding index...")
                # Delete and recreate
                try:
                    self.client.delete_collection(self.collection_name)
                except Exception:
                    pass
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                self._is_cached = False
        
        # If we get here, we need to index
        batch_size = 100
        total = len(chunks)
        print(f"\nðŸ“¦ Indexing {total:,} chunks into ChromaDB...")
        print(f"   Batch size: {batch_size} chunks per batch")
        
        start_time = time.time()
        
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            batch_sources = sources[i:i + batch_size]
            
            # Progress bar
            progress = int((i / total) * 100)
            chunks_done = min(i + batch_size, total)
            
            if i > 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (total - i) / rate if rate > 0 else 0
                eta_min = int(remaining // 60)
                eta_sec = int(remaining % 60)
                eta_str = f" ETA: {eta_min}m{eta_sec:02d}s" if eta_min > 0 else f" ETA: {eta_sec}s"
            else:
                eta_str = ""
            
            bar_length = 30
            filled = int(bar_length * i // total)
            bar = 'â–ˆ' * filled + 'â–‘' * (bar_length - filled)
            print(f"   [{bar}] {progress:3d}% ({chunks_done:,}/{total:,}){eta_str}", end="\r")
            
            embeddings = self.embedding_model.encode(batch, show_progress_bar=False).tolist()
            self.collection.add(
                embeddings=embeddings,
                documents=batch,
                metadatas=[{"source": s} for s in batch_sources],
                ids=[f"doc_{i + j}" for j in range(len(batch))],
            )
        
        elapsed = time.time() - start_time
        print(f"\nâœ… Indexing complete! {total:,} chunks indexed in {elapsed:.1f} seconds.\n")

    def search(self, query: str, top_k: int) -> List[Dict]:
        if self.collection is None:
            return []
        query_embedding = self.embedding_model.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding, n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        out = []
        for doc, meta, dist in zip(docs, metas, dists):
            similarity = max(0.0, 1 - dist)
            out.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "relevance_score": round(similarity, 3),
                "confidence": _confidence_label(similarity),
            })
        return out


class TfidfBackend:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
        self.matrix = None
        self.chunks: List[str] = []
        self.sources: List[str] = []

    def index(self, chunks: List[str], sources: List[str]) -> None:
        print(f"ðŸ“Š Building TF-IDF index with {len(chunks):,} chunks...")
        self.chunks = chunks
        self.sources = sources
        self.matrix = self.vectorizer.fit_transform(chunks)
        print("âœ… TF-IDF index built")

    def search(self, query: str, top_k: int) -> List[Dict]:
        if self.matrix is None or not self.chunks:
            return []
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix)[0]
        top_idx = sims.argsort()[::-1][:top_k]
        out = []
        for i in top_idx:
            score = float(sims[i])
            if score <= 0:
                continue
            out.append({
                "text": self.chunks[i],
                "source": self.sources[i],
                "relevance_score": round(score, 3),
                "confidence": _confidence_label(score),
            })
        return out


def _confidence_label(score: float) -> str:
    if score > 0.55:
        return "HIGH"
    if score > 0.3:
        return "MEDIUM"
    return "LOW"


class RAGEngine:
    def __init__(self):
        self.backend_name = "none"
        self.backend = None
        self.corpus_size = 0

    def build(self, chunks: List[str], sources: List[str]) -> None:
        if not chunks:
            return
        if _EMBEDDING_STACK_AVAILABLE:
            try:
                self.backend = ChromaEmbeddingBackend()
                self.backend.index(chunks, sources)  # This will check cache
                self.backend_name = "chroma+bge-small"
                self.corpus_size = len(chunks)
                return
            except Exception as e:
                print(f"âš ï¸ Chroma indexing failed: {e}")
                print("   Falling back to TF-IDF...")
        self.backend = TfidfBackend()
        self.backend.index(chunks, sources)
        self.backend_name = "tfidf"
        self.corpus_size = len(chunks)

    def search(self, query: str, top_k: int = config.RAG_TOP_K) -> List[Dict]:
        if not self.backend:
            return []
        return self.backend.search(query, top_k)

    @property
    def is_active(self) -> bool:
        return self.backend is not None
