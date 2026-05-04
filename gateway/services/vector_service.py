import faiss
import numpy as np
from threading import Lock
from fastapi import HTTPException

class VectorService:
    def __init__(self, dimension: int, modality: str = "text"):
        self.dimension = dimension
        self.modality = modality
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata_store = {}
        self.lock = Lock()
        self.current_id = 0

    def _validate_dim(self, vectors: list[list[float]]):
        for i, v in enumerate(vectors):
            if len(v) != self.dimension:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"[{self.modality}] Vector at index {i} has dimension "
                        f"{len(v)}, expected {self.dimension}."
                    ),
                )

    def add_vectors(self, vectors: list[list[float]], metadata: list[dict]):
        if len(vectors) != len(metadata):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"vectors length ({len(vectors)}) must equal "
                    f"metadata length ({len(metadata)})."
                ),
            )
        self._validate_dim(vectors)
        with self.lock:
            np_vectors = np.array(vectors).astype('float32')
            start_id = self.current_id
            self.index.add(np_vectors)
            for i, meta in enumerate(metadata):
                self.metadata_store[start_id + i] = meta
                self.current_id += 1
        return {"status": "success", "count": len(vectors)}

    def search(self, query_vector: list[float], k: int):
        self._validate_dim([query_vector])
        with self.lock:
            np_query = np.array([query_vector]).astype('float32')
            distances, indices = self.index.search(np_query, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx in self.metadata_store:
                results.append({
                    "score": float(dist),
                    "metadata": self.metadata_store[idx],
                })
        return results