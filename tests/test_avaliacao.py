"""
Testes das métricas de avaliação (precisão, revocação e medida F).
Rodam sem banco, sem modelo e sem internet.

Rodar: pytest tests/test_avaliacao.py -v   (ou: python tests/test_avaliacao.py)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scripts.evaluate import evaluate_question, f_measure, normalize


def test_normalize_ignora_acento_caixa_e_espacos():
    assert normalize("  Frequência   MÍNIMA ") == "frequencia minima"


def test_recuperacao_perfeita_no_topo():
    r = evaluate_question("q", ["peso 3,0"], ["o peso 3,0 vale muito", "outro texto"], k=1)
    assert r.precision == 1.0 and r.recall == 1.0 and r.f1 == 1.0
    assert r.first_relevant_rank == 1


def test_precisao_cai_quando_ha_chunks_irrelevantes():
    retrieved = ["irrelevante", "peso 3,0 aqui", "outro", "mais um"]
    r = evaluate_question("q", ["peso 3,0"], retrieved, k=4)
    assert r.precision == 0.25
    assert r.recall == 1.0
    assert r.first_relevant_rank == 2


def test_revocacao_parcial_com_varios_trechos_esperados():
    r = evaluate_question("q", ["alfa", "beta"], ["texto com alfa"], k=1)
    assert r.recall == 0.5
    assert r.precision == 1.0


def test_nada_relevante():
    r = evaluate_question("q", ["alfa"], ["x", "y"], k=2)
    assert r.precision == 0.0 and r.recall == 0.0 and r.f1 == 0.0
    assert r.first_relevant_rank == 0


def test_medida_f():
    assert f_measure(0.0, 0.0) == 0.0
    assert abs(f_measure(0.5, 1.0) - 2 / 3) < 1e-9


if __name__ == "__main__":
    test_normalize_ignora_acento_caixa_e_espacos()
    test_recuperacao_perfeita_no_topo()
    test_precisao_cai_quando_ha_chunks_irrelevantes()
    test_revocacao_parcial_com_varios_trechos_esperados()
    test_nada_relevante()
    test_medida_f()
    print("Todos os testes passaram.")
