"""Source VECTORIELLE mock — cosinus sur TF-IDF (défaut) ou embeddings denses (fastembed).

Deux modes, même contrat MCP (vector_search), même signature de search() :
  - TF-IDF creux (défaut) : zéro dépendance, hors-ligne, instanciation immédiate.
  - fastembed dense (optionnel) : `pip install fastembed`, active automatiquement
    le modèle `intfloat/multilingual-e5-small` (~120 MB, multilingue FR/EN).
    Téléchargé une seule fois dans le cache fastembed (~/.cache/fastembed).

En prod, on remplace par le vrai Qdrant + embeddings denses : le contrat MCP reste identique.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_TOKEN = re.compile(r"\w+", re.UNICODE)

# Fastembed optionnel — activé si le package est installé.
# Modèle multilingue FR/EN, léger (~120 MB), pas de service externe requis.
try:
    from fastembed import TextEmbedding as _FE
    _EMBED_MODEL: "_FE | None" = _FE("intfloat/multilingual-e5-small")
except ImportError:
    _EMBED_MODEL = None


def _tok(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


def _cosine_np(a: "Any", b: "Any") -> float:
    """Cosinus entre deux vecteurs numpy."""
    import numpy as np
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class VectorSource:
    def __init__(self, data: dict[str, Any]) -> None:
        self.chunks = data.get("chunks", [])

        if _EMBED_MODEL is not None:
            # --- mode dense (fastembed) ---
            texts = [c["text"] for c in self.chunks]
            self._embeds = list(_EMBED_MODEL.embed(texts)) if texts else []
            self._tfidf = None
        else:
            # --- mode TF-IDF creux (défaut) ---
            self._embeds = []
            docs_tokens = [_tok(c["text"]) for c in self.chunks]
            df: Counter = Counter()
            for toks in docs_tokens:
                for term in set(toks):
                    df[term] += 1
            n = max(len(docs_tokens), 1)
            idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
            self._idf = idf
            self._vecs = [self._tfidf_vec(toks, idf) for toks in docs_tokens]
            self._norms = [math.sqrt(sum(w * w for w in v.values())) or 1.0
                           for v in self._vecs]
            self._tfidf = True

    @staticmethod
    def _tfidf_vec(toks: list[str], idf: dict[str, float]) -> dict[str, float]:
        tf = Counter(toks)
        return {t: (tf[t] / len(toks)) * idf.get(t, 0.0) for t in tf} if toks else {}

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Renvoie les top_k chunks les plus proches sémantiquement (cosinus)."""
        if _EMBED_MODEL is not None:
            return self._search_dense(query, top_k)
        return self._search_tfidf(query, top_k)

    def _search_dense(self, query: str, top_k: int) -> list[dict]:
        qv = next(iter(_EMBED_MODEL.embed([query])))  # type: ignore[union-attr]
        scored = [
            {"chunk_id": c["id"], "doc_id": c["doc_id"], "text": c["text"],
             "score": round(_cosine_np(qv, ev), 4)}
            for c, ev in zip(self.chunks, self._embeds)
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _search_tfidf(self, query: str, top_k: int) -> list[dict]:
        qv = self._tfidf_vec(_tok(query), self._idf)
        qn = math.sqrt(sum(w * w for w in qv.values())) or 1.0
        scored = []
        for i, v in enumerate(self._vecs):
            dot = sum(w * v.get(t, 0.0) for t, w in qv.items())
            score = dot / (qn * self._norms[i])
            if score > 0:
                c = self.chunks[i]
                scored.append({"chunk_id": c["id"], "doc_id": c["doc_id"],
                               "text": c["text"], "score": round(score, 4)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
