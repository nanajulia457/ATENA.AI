"""
Processamento de documentos com Docling.

Responsável pela etapa (3) da metodologia: extração de texto de documentos
acadêmicos em formato PDF e DOCX, preservando, quando possível, a estrutura
(títulos, tabelas) para facilitar o chunking posterior.

Docling normaliza diferentes formatos de entrada em uma representação única
(DoclingDocument), da qual extraímos o texto em Markdown — isso preserva
títulos e tabelas de forma legível tanto para humanos quanto para o LLM.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class ProcessedDocument:
    source_path: str
    title: str
    text: str  # conteúdo em Markdown, já normalizado pelo Docling


class DocumentProcessor:
    """Extrai texto de documentos acadêmicos (PDF, DOCX, TXT)."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

    def __init__(self):
        # Import tardio: Docling é uma dependência pesada (baixa modelos de
        # layout na primeira execução), então só é carregada se realmente
        # formos processar PDF/DOCX.
        self._docling_converter = None

    def _get_docling_converter(self):
        if self._docling_converter is None:
            from docling.document_converter import DocumentConverter

            self._docling_converter = DocumentConverter()
        return self._docling_converter

    def process_file(self, path: str) -> ProcessedDocument:
        file_path = Path(path)
        ext = file_path.suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato não suportado: {ext} ({path})")

        if ext in {".txt", ".md"}:
            # Atalho para dados de exemplo/fictícios em texto puro, sem
            # precisar do Docling (útil para testes sem os documentos
            # oficiais da disciplina ainda em mãos).
            text = file_path.read_text(encoding="utf-8")
        else:
            converter = self._get_docling_converter()
            result = converter.convert(str(file_path))
            text = result.document.export_to_markdown()

        return ProcessedDocument(
            source_path=str(file_path),
            title=file_path.stem,
            text=text,
        )

    def process_directory(self, directory: str) -> List[ProcessedDocument]:
        dir_path = Path(directory)
        documents = []
        for file_path in sorted(dir_path.iterdir()):
            # Ignora arquivos temporários (o Word cria "~$nome.docx" enquanto o
            # documento está aberto) e arquivos ocultos.
            if file_path.name.startswith(("~$", ".")) or not file_path.is_file():
                continue
            if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                documents.append(self.process_file(str(file_path)))
        return documents
