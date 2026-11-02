"""
Armazenamento e recuperação vetorial (etapas 5 e 6 da metodologia).

Usa o PGVectorStore do LlamaIndex como camada de orquestração sobre uma
extensão pgvector em PostgreSQL. O LlamaIndex cuida de criar a tabela,
inserir os nós (chunks + embeddings) e executar a busca por similaridade
(distância de cosseno) no momento da consulta.
"""
from typing import List

from src.config import settings
from src.ingestion.chunking import Chunk


class VectorStoreManager:
    def __init__(self):
        self._index = None

    def _build_vector_store(self):
        from llama_index.vector_stores.postgres import PGVectorStore

        return PGVectorStore.from_params(
            database=settings.db_name,
            host=settings.db_host,
            password=settings.db_password,
            port=str(settings.db_port),
            user=settings.db_user,
            table_name=settings.vector_table,
            embed_dim=settings.embedding_dim,
        )

    def _reset_table(self) -> None:
        """
        Apaga a tabela vetorial existente, para que a ingestão sempre parta
        do zero. Sem isso, rodar a ingestão duas vezes duplicaria os chunks
        no banco e distorceria a recuperação (e as métricas de avaliação).
        O LlamaIndex cria a tabela com o prefixo "data_".
        """
        import psycopg2
        from psycopg2 import sql

        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
        )
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}").format(
                        sql.Identifier(f"data_{settings.vector_table.lower()}")
                    )
                )
        finally:
            conn.close()

    def build_index(self, chunks: List[Chunk], embed_model, reset: bool = True) -> None:
        """
        Reconstrói o índice vetorial a partir de uma lista de chunks já
        processados, gerando embeddings e persistindo no pgvector.

        Com reset=True (padrão), a tabela anterior é apagada antes, então a
        ingestão sempre reflete exatamente os documentos da pasta de entrada.
        """
        from llama_index.core import Document, StorageContext, VectorStoreIndex
        from llama_index.core.settings import Settings as LlamaSettings

        LlamaSettings.embed_model = embed_model

        documents = [
            Document(
                text=chunk.text,
                doc_id=chunk.chunk_id,
                metadata={
                    "source_path": chunk.source_path,
                    "document_title": chunk.document_title,
                    "chunk_index": chunk.chunk_index,
                },
            )
            for chunk in chunks
        ]

        if reset:
            self._reset_table()

        vector_store = self._build_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        self._index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context
        )

    def load_index(self, embed_model):
        """Reabre um índice já existente no pgvector, sem reprocessar documentos."""
        from llama_index.core import VectorStoreIndex
        from llama_index.core.settings import Settings as LlamaSettings

        LlamaSettings.embed_model = embed_model
        vector_store = self._build_vector_store()
        self._index = VectorStoreIndex.from_vector_store(vector_store)
        return self._index

    def as_retriever(self, top_k: int = None):
        if self._index is None:
            raise RuntimeError(
                "Índice ainda não construído/carregado. Chame build_index() "
                "ou load_index() antes."
            )
        return self._index.as_retriever(similarity_top_k=top_k or settings.top_k)
