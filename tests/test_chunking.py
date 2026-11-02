"""
Testes unitários da etapa de chunking.

Estes testes não dependem de Docling, pgvector ou LLMs — rodam com apenas a
biblioteca padrão, servindo para validar a lógica de divisão de texto de
forma isolada e rápida.

Rodar: pytest tests/test_chunking.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.chunking import Chunker
from src.ingestion.document_processor import ProcessedDocument


def make_document(text: str) -> ProcessedDocument:
    return ProcessedDocument(source_path="teste.txt", title="doc_teste", text=text)


def test_chunk_respects_max_size():
    text = "Esta é uma frase de teste. " * 100
    chunker = Chunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk_document(make_document(text))

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 100 + 20  # margem para a última sentença


def test_chunk_preserves_all_content_words():
    text = "Primeira frase importante. Segunda frase relevante. Terceira frase final."
    chunker = Chunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_document(make_document(text))

    # Texto curto o suficiente para caber em um único chunk.
    assert len(chunks) == 1
    assert "Primeira frase importante" in chunks[0].text
    assert "Terceira frase final" in chunks[0].text


def test_chunk_ids_are_sequential():
    text = "Frase. " * 200
    chunker = Chunker(chunk_size=80, chunk_overlap=10)
    chunks = chunker.chunk_document(make_document(text))

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert chunk.document_title == "doc_teste"


def test_overlap_smaller_than_size_is_enforced():
    try:
        Chunker(chunk_size=50, chunk_overlap=50)
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass


def test_empty_document_produces_no_chunks():
    chunker = Chunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk_document(make_document("   \n\n  "))
    assert chunks == []


if __name__ == "__main__":
    test_chunk_respects_max_size()
    test_chunk_preserves_all_content_words()
    test_chunk_ids_are_sequential()
    test_overlap_smaller_than_size_is_enforced()
    test_empty_document_produces_no_chunks()
    print("Todos os testes passaram.")
