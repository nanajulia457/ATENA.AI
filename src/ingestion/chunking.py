"""
Estratégia de chunking (etapa 4 da metodologia).

Divide o texto de cada documento em trechos ("chunks") de tamanho controlado,
com sobreposição entre trechos vizinhos para não perder contexto que caia na
fronteira entre dois chunks (ex.: uma frase cortada ao meio).

Texto corrido: a divisão é feita por sentenças/parágrafos sempre que possível,
e só quebra no meio de uma frase se ela sozinha já ultrapassar o tamanho do chunk.

Tabelas (o Docling exporta tabelas em Markdown, com linhas começando por "|"):
- cada linha que começa com uma data (ex.: "16/03") vira UM chunk próprio, no
  formato "16/03 (março): <atividade>". Assim a busca encontra a data certa e o
  modelo não mistura atividades de datas diferentes;
- grades de calendário (dias da semana, números soltos, títulos de mês) e
  cabeçalhos repetidos são descartados, pois só atrapalham a busca;
- as demais linhas de tabela entram no fluxo de texto corrido.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.ingestion.document_processor import ProcessedDocument


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_path: str
    document_title: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/\d{2,4})?$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->")
_TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")
_MONTH_TITLE_RE = re.compile(r"^(" + "|".join(_MONTHS) + r")\s+\d{4}$", re.IGNORECASE)
_WEEKDAYS = {"dom", "seg", "ter", "qua", "qui", "sex", "sab", "sáb"}


def _split_into_sentences(text: str) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    sentences = []
    for paragraph in paragraphs:
        sentences.extend(_SENTENCE_SPLIT_RE.split(paragraph))
    return [s for s in sentences if s]


def _parse_table_row(line: str) -> Optional[List[str]]:
    """
    Devolve as células de uma linha de tabela Markdown, sem células vazias nem
    repetidas em sequência (células mescladas saem repetidas do Docling).
    Devolve None se a linha não for de tabela, e [] se for só separador.
    """
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    stripped = _HTML_COMMENT_RE.sub("", stripped)
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    cells = [c for c in cells if c]
    if cells and all(_TABLE_SEPARATOR_CELL_RE.match(c) for c in cells):
        return []
    deduped: List[str] = []
    for cell in cells:
        if not deduped or deduped[-1] != cell:
            deduped.append(cell)
    return deduped


def _is_noise_row(cells: List[str]) -> bool:
    """Linhas sem informação útil: vazias, cabeçalhos repetidos e grades de calendário."""
    if not cells:
        return True
    lowered = [c.lower() for c in cells]
    if all(c == "atividades" for c in lowered):
        return True
    if all(_MONTH_TITLE_RE.match(c) for c in cells):
        return True
    if all(c in _WEEKDAYS for c in lowered):
        return True
    # números soltos ("1 | 2 | 3 ...") ou marcadores curtos: grade de dias
    return max(len(c) for c in cells) <= 4


def _date_prefix(date_cell: str) -> str:
    match = _DATE_RE.match(date_cell)
    month = int(match.group(2))
    if 1 <= month <= 12:
        return f"{date_cell} ({_MONTHS[month - 1]}):"
    return f"{date_cell}:"


class Chunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        """
        chunk_size e chunk_overlap são medidos em caracteres (aproximação
        simples e determinística; para produção, considerar usar a contagem
        de tokens do tokenizer do modelo de embedding).
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap deve ser menor que chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _chunk_text(self, text: str) -> List[str]:
        """Divide texto corrido em trechos com sobreposição."""
        sentences = _split_into_sentences(text)
        pieces: List[str] = []
        current = ""

        def flush(current_text: str):
            if current_text.strip():
                pieces.append(current_text.strip())

        for sentence in sentences:
            candidate = f"{current} {sentence}".strip()
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue

            # Chunk atual está cheio: fecha e inicia o próximo com overlap.
            flush(current)
            overlap_text = current[-self.chunk_overlap:] if current else ""
            if len(current) > self.chunk_overlap and " " in overlap_text:
                overlap_text = overlap_text.split(" ", 1)[1]  # começa em palavra inteira
            current = f"{overlap_text} {sentence}".strip()

            # Sentença isolada maior que o chunk: quebra à força.
            while len(current) > self.chunk_size:
                flush(current[: self.chunk_size])
                current = current[self.chunk_size - self.chunk_overlap:]

        flush(current)
        return pieces

    def _chunk_date_row(self, cells: List[str]) -> List[str]:
        prefix = _date_prefix(cells[0])
        body = " ".join(cells[1:])
        text = f"{prefix} {body}"
        if len(text) <= self.chunk_size:
            return [text]
        # Linha muito longa: divide, repetindo a data em cada parte.
        return [f"{prefix} {part}" for part in self._chunk_text(body)]

    def chunk_document(self, document: ProcessedDocument) -> List[Chunk]:
        prose_lines: List[str] = []
        row_texts: List[str] = []

        for line in document.text.splitlines():
            cells = _parse_table_row(line)
            if cells is None:
                prose_lines.append(line)
            elif _is_noise_row(cells):
                continue
            elif _DATE_RE.match(cells[0]) and len(cells) > 1:
                row_texts.extend(self._chunk_date_row(cells))
            else:
                prose_lines.append(" — ".join(cells))

        texts = self._chunk_text("\n".join(prose_lines)) + row_texts
        return [
            Chunk(
                chunk_id=f"{document.title}-{i}",
                text=text,
                source_path=document.source_path,
                document_title=document.title,
                chunk_index=i,
            )
            for i, text in enumerate(texts)
        ]

    def chunk_documents(self, documents: List[ProcessedDocument]) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        for document in documents:
            all_chunks.extend(self.chunk_document(document))
        return all_chunks
