"""
API REST (etapa 8 da metodologia), construída com FastAPI.

Expõe o pipeline RAG por meio de endpoints HTTP, permitindo que qualquer
aplicação cliente (a incluída neste projeto ou outra) envie perguntas e
receba respostas contextualizadas.

Rodar localmente:
    uvicorn src.api.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.config import settings
from src.indexing.embeddings import get_llama_index_embed_model
from src.indexing.vector_store import VectorStoreManager
from src.rag.pipeline import RAGPipeline

_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Carrega o modelo de embeddings e conecta ao índice vetorial já
    # existente no pgvector uma única vez, na inicialização da API —
    # evita recarregar o modelo a cada requisição.
    embed_model = get_llama_index_embed_model()
    vector_store_manager = VectorStoreManager()
    vector_store_manager.load_index(embed_model)
    retriever = vector_store_manager.as_retriever(top_k=settings.top_k)
    _state["pipeline"] = RAGPipeline(retriever)
    yield
    _state.clear()


app = FastAPI(
    title="Atena.AI",
    description=(
        "API do assistente educacional baseado em Retrieval-Augmented "
        "Generation para consulta inteligente a materiais de disciplina."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Pergunta do estudante")
    top_k: int | None = Field(None, ge=1, le=20)


class SourceItem(BaseModel):
    document_title: str
    excerpt: str
    score: float


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    pipeline: RAGPipeline = _state.get("pipeline")
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Índice ainda não carregado.")

    result = pipeline.answer(request.question)
    return AnswerResponse(
        answer=result.answer,
        sources=[
            SourceItem(
                document_title=s.document_title,
                excerpt=s.text[:300],
                score=round(s.score, 4),
            )
            for s in result.sources
        ],
    )
