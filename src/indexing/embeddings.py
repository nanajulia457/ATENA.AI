"""
Geração de embeddings (etapa 5 da metodologia).

Usa Sentence-BERT (via sentence-transformers) para converter cada chunk de
texto em um vetor numérico de dimensão fixa, que captura o significado
semântico do trecho e permite busca por similaridade no pgvector.

Modelo padrão: paraphrase-multilingual-MiniLM-L12-v2 (384 dimensões), leve e
com bom desempenho em português — adequado para um TCC que roda em máquina
sem GPU dedicada. Pode ser trocado por um modelo maior via variável de
ambiente EMBEDDING_MODEL, se houver recursos computacionais disponíveis.
"""
from typing import List

from src.config import settings


class EmbeddingModel:
    def __init__(self, model_name: str = None):
        # Import tardio: sentence-transformers/torch são pesados para
        # carregar e baixam o modelo na primeira execução (precisa de rede).
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or settings.embedding_model
        self._model = SentenceTransformer(self.model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]


def get_llama_index_embed_model(model_name: str = None):
    """
    Retorna o wrapper de embeddings no formato esperado pelo LlamaIndex
    (usado em VectorStoreManager). Mantido separado de EmbeddingModel para
    permitir usar esta última isoladamente (ex.: nos scripts de avaliação
    de precisão/revocação, objetivo específico 'g').
    """
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    return HuggingFaceEmbedding(model_name=model_name or settings.embedding_model)
