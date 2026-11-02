"""
Configurações centrais do sistema.

Todos os valores sensíveis (chaves de API, credenciais de banco) devem vir
de variáveis de ambiente (.env), nunca hardcoded no código-fonte.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # --- Banco vetorial (Postgres + pgvector) ---
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "rag_assistant")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")
    vector_table: str = os.getenv("VECTOR_TABLE", "document_chunks")

    # --- Embeddings ---
    # Modelo multilíngue leve, funciona bem para português.
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "384"))

    # --- Chunking ---
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "64"))

    # --- Geração (LLM) ---
    # Suporta "openai", "anthropic" ou "groq" (opção gratuita, sem cartão de
    # crédito, compatível com o SDK da OpenAI através de uma base_url própria).
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    # --- Recuperação ---
    top_k: int = int(os.getenv("TOP_K", "5"))

    # --- Caminhos ---
    raw_docs_dir: str = os.getenv("RAW_DOCS_DIR", "data/raw")

    # --- API ---
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
