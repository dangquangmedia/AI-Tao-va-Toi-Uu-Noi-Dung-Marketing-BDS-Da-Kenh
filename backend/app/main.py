import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    content,
    dataset,
    experiments,
    generation,
    graph,
    ingestion,
    listings,
    pipeline,
    projects,
    search,
)
from app.core.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Nạp sẵn model embedding ở nền: lần tìm kiếm đầu tiên không phải chờ tải model."""
    if settings.embedding_backend != "hashing":
        from app.services.embeddings import get_embedder

        threading.Thread(target=get_embedder, daemon=True).start()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(ingestion.router)
app.include_router(pipeline.router)
app.include_router(listings.router)
app.include_router(graph.router)
app.include_router(generation.router)
app.include_router(content.router)
app.include_router(search.router)
app.include_router(dataset.router)
app.include_router(experiments.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
