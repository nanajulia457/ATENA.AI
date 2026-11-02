"""
Testes do chunking de tabelas (linhas de calendário) e de texto corrido.
Usa um texto que simula a saída do Docling para o calendário da disciplina
(tests/fixtures/calendario_simulado.md). Roda sem banco, modelo ou internet.

Rodar: pytest tests/test_chunking_tabelas.py -v   (ou: python tests/test_chunking_tabelas.py)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingestion.chunking import Chunker
from src.ingestion.document_processor import ProcessedDocument
from src.scripts.evaluate import load_gold, snippet_is_covered


def calendario_chunks():
    text = (ROOT / "tests" / "fixtures" / "calendario_simulado.md").read_text(encoding="utf-8")
    doc = ProcessedDocument("calendario_simulado.md", "CALENDARIO", text)
    return [c.text for c in Chunker(512, 64).chunk_document(doc)]


def make_doc(text):
    return ProcessedDocument("t.md", "t", text)


def test_cada_data_vira_um_chunk_proprio():
    chunks = calendario_chunks()
    linha_16 = [c for c in chunks if c.startswith("16/03")]
    linha_23 = [c for c in chunks if c.startswith("23/03")]
    assert len(linha_16) == 1 and len(linha_23) == 1
    assert "Entrega da Proposta Inicial de Pesquisa" in linha_16[0]
    assert "orientador" not in linha_16[0]          # não mistura com o dia 23/03
    assert "entrega ao orientador" in linha_23[0]
    assert "23/03" not in linha_16[0]


def test_chunk_de_data_traz_o_nome_do_mes():
    chunks = calendario_chunks()
    assert any(c.startswith("16/03 (março):") for c in chunks)
    assert any(c.startswith("01/07 (julho):") for c in chunks)


def test_grades_e_cabecalhos_sao_descartados():
    chunks = calendario_chunks()
    for c in chunks:
        assert "Dom" not in c and "Fevereiro 2026" not in c
        assert c.strip() != "Atividades"
        assert "<!--" not in c


def test_texto_corrido_do_calendario_continua_indexado():
    chunks = " ".join(calendario_chunks())
    assert "NProp × 20% + NRevi × 20% + NProj × 60%" in chunks
    assert "exclusivamente pela orientação" in chunks


def test_linha_com_celula_inicial_vazia_tambem_e_reconhecida():
    doc = make_doc("| | 27/04 | Aula 10 - Acompanhamento do TCC |\n| | 03/05 | Entrega no Moodle |")
    textos = [c.text for c in Chunker(200, 20).chunk_document(doc)]
    assert "27/04 (abril): Aula 10 - Acompanhamento do TCC" in textos
    assert "03/05 (maio): Entrega no Moodle" in textos


def test_linha_muito_longa_repete_a_data_em_cada_parte():
    longa = "Alunos entregam o relatório completo. " * 30
    doc = make_doc(f"| 10/05 | {longa} |")
    partes = [c.text for c in Chunker(200, 20).chunk_document(doc)]
    assert len(partes) > 1
    assert all(p.startswith("10/05 (maio):") for p in partes)


def test_texto_sem_tabelas_nao_muda():
    doc = make_doc("Primeira frase importante. Segunda frase relevante. Terceira frase final.")
    chunks = Chunker(500, 50).chunk_document(doc)
    assert len(chunks) == 1 and "Segunda frase relevante" in chunks[0].text


def test_sobreposicao_comeca_em_palavra_inteira():
    texto = " ".join(f"palavra{i}." for i in range(80))
    chunks = Chunker(100, 30).chunk_document(make_doc(texto))
    assert len(chunks) > 2
    for c in chunks[1:]:
        assert c.text.split()[0].startswith("palavra")


def test_gabarito_do_calendario_e_satisfazivel():
    chunks = calendario_chunks()
    gold = load_gold(str(ROOT / "data" / "eval" / "perguntas_calendario.json"))
    for item in gold:
        for trecho in item["trechos_esperados"]:
            assert snippet_is_covered(trecho, chunks), f"trecho ausente: {trecho}"


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_"):
            fn()
    print("Todos os testes passaram.")
