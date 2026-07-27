from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, graph, ingestion, listings, pipeline, projects
from app.core.config import settings

app = FastAPI(title=settings.app_name)

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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
