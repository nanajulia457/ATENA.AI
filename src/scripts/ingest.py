"""
Script de ingestão: executa as etapas 3, 4 e 5 da metodologia em sequência.

Uso:
    python -m src.scripts.ingest [--dir data/raw]

Lê todos os documentos de um diretório, processa com Docling, divide em
chunks, gera embeddings e persiste no pgvector via LlamaIndex.
"""
import argparse
from pathlib import Path

from src.config import settings
from src.indexing.embeddings import get_llama_index_embed_model
from src.indexing.vector_store import VectorStoreManager
from src.ingestion.chunking import Chunker
from src.ingestion.document_processor import DocumentProcessor


def save_debug_files(documents, chunks, debug_dir="data/debug"):
    """
    Salva em data/debug o texto que o Docling extraiu de cada documento e a
    lista de chunks gerados. Serve para conferir o que o sistema "enxergou" do
    PDF e para documentar o pré-processamento no TCC.
    """
    out = Path(debug_dir)
    out.mkdir(parents=True, exist_ok=True)
    for doc in documents:
        (out / f"{Path(doc.source_path).stem}.extraido.md").write_text(doc.text, encoding="utf-8")
    lines = []
    for c in chunks:
        lines.append(f"=== [{c.chunk_index}] {c.document_title} ({len(c.text)} caracteres)")
        lines.append(c.text)
        lines.append("")
    (out / "chunks.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"       Arquivos de conferência salvos em '{debug_dir}'.")


def main():
    parser = argparse.ArgumentParser(description="Ingestão de documentos da disciplina")
    parser.add_argument("--dir", default=settings.raw_docs_dir, help="Diretório com os documentos")
    args = parser.parse_args()

    print(f"[1/4] Processando documentos em '{args.dir}' com Docling...")
    processor = DocumentProcessor()
    documents = processor.process_directory(args.dir)
    print(f"       {len(documents)} documento(s) processado(s).")

    print("[2/4] Dividindo documentos em chunks...")
    chunker = Chunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunks = chunker.chunk_documents(documents)
    print(f"       {len(chunks)} chunk(s) gerado(s).")
    save_debug_files(documents, chunks)

    print("[3/4] Carregando modelo de embeddings...")
    embed_model = get_llama_index_embed_model()

    print("[4/4] Gerando embeddings e indexando no pgvector...")
    vector_store_manager = VectorStoreManager()
    vector_store_manager.build_index(chunks, embed_model)
    print("       Índice construído com sucesso.")


if __name__ == "__main__":
    main()
