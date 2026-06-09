"""Source CORPUS mock — accès aux documents bruts ingérés."""
from __future__ import annotations

import json
from typing import Any


class DocumentStore:
    def __init__(self, data: dict[str, Any]) -> None:
        self.docs = {d["id"]: d for d in data.get("documents", [])}

    def get(self, doc_id: str) -> dict | None:
        return self.docs.get(doc_id)

    def search(self, query: str) -> list[dict]:
        q = query.lower().strip()
        return [d for d in self.docs.values()
                if q in json.dumps(d, ensure_ascii=False).lower()]
