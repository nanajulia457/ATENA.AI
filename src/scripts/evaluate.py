"""
Avaliação da recuperação (objetivo específico "g" do TCC).

Mede a qualidade da etapa de recuperação de trechos com as métricas clássicas
de recuperação de informação (Baeza-Yates & Ribeiro-Neto, 2013): precisão,
revocação e medida F.

Como a relevância é definida
----------------------------
Cada pergunta do "gabarito" (arquivo JSON) traz uma lista de
`trechos_esperados`: pedaços de texto que precisam aparecer no contexto
recuperado para que a pergunta possa ser respondida corretamente.

- Um chunk recuperado é RELEVANTE se contém pelo menos um trecho esperado.
- Precisão@k  = chunks relevantes entre os k recuperados / k recuperados.
- Revocação@k = trechos esperados encontrados nos k recuperados / total de
                trechos esperados da pergunta.
- Medida F@k  = média harmônica entre precisão e revocação.

A comparação ignora maiúsculas, acentos e diferenças de espaçamento.

Atenção ao interpretar a precisão: se uma pergunta tem só 1 chunk relevante
no acervo, a precisão@5 nunca passa de 0,20 (1 relevante em 5 recuperados),
mesmo com a recuperação perfeita. Por isso vale reportar vários valores de k.

Uso (com o banco no ar e a ingestão já feita):
    python -m src.scripts.evaluate --gold data/eval/perguntas_exemplo.json --k 1 3 5
"""
import argparse
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List


def normalize(text: str) -> str:
    """Minúsculas, sem acentos, travessão = hífen e com espaços colapsados."""
    text = text.replace("–", "-").replace("—", "-")  # o Docling costuma trocar travessão por hífen
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    return re.sub(r"\s+", " ", text).strip()


def chunk_is_relevant(chunk_text: str, expected_snippets: List[str]) -> bool:
    chunk_norm = normalize(chunk_text)
    return any(normalize(s) in chunk_norm for s in expected_snippets)


def snippet_is_covered(snippet: str, chunks: List[str]) -> bool:
    snippet_norm = normalize(snippet)
    return any(snippet_norm in normalize(c) for c in chunks)


def f_measure(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class QuestionResult:
    question: str
    k: int
    precision: float
    recall: float
    f1: float
    first_relevant_rank: int  # 0 = nenhum chunk relevante encontrado


def evaluate_question(
    question: str, expected: List[str], retrieved: List[str], k: int
) -> QuestionResult:
    top = retrieved[:k]

    relevant_flags = [chunk_is_relevant(c, expected) for c in top]
    precision = sum(relevant_flags) / len(top) if top else 0.0

    covered = sum(snippet_is_covered(s, top) for s in expected)
    recall = covered / len(expected) if expected else 0.0

    first_rank = next((i + 1 for i, ok in enumerate(relevant_flags) if ok), 0)

    return QuestionResult(
        question=question,
        k=k,
        precision=precision,
        recall=recall,
        f1=f_measure(precision, recall),
        first_relevant_rank=first_rank,
    )


def evaluate(
    gold: List[dict],
    retrieve_fn: Callable[[str, int], List[str]],
    ks: List[int],
) -> List[QuestionResult]:
    """
    retrieve_fn(pergunta, k) devolve os textos dos k chunks recuperados,
    do mais para o menos similar. A recuperação roda uma vez por pergunta,
    com o maior k, e os cortes menores reaproveitam o mesmo ranking.
    """
    max_k = max(ks)
    results: List[QuestionResult] = []
    for item in gold:
        retrieved = retrieve_fn(item["pergunta"], max_k)
        for k in sorted(ks):
            results.append(
                evaluate_question(
                    item["pergunta"], item["trechos_esperados"], retrieved, k
                )
            )
    return results


def summarize(results: List[QuestionResult]) -> Dict[int, Dict[str, float]]:
    summary: Dict[int, Dict[str, float]] = {}
    for k in sorted({r.k for r in results}):
        rows = [r for r in results if r.k == k]
        n = len(rows)
        p = sum(r.precision for r in rows) / n
        r_ = sum(r.recall for r in rows) / n
        summary[k] = {
            "precisao": p,
            "revocacao": r_,
            "medida_f": f_measure(p, r_),
            "perguntas": n,
        }
    return summary


def load_gold(path: str) -> List[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for i, item in enumerate(data, start=1):
        if "pergunta" not in item or not item.get("trechos_esperados"):
            raise ValueError(
                f"Item {i} do gabarito precisa de 'pergunta' e de pelo menos "
                f"um item em 'trechos_esperados'."
            )
    return data


def build_real_retrieve_fn(max_k: int) -> Callable[[str, int], List[str]]:
    # Imports tardios: só carregam o modelo e o banco quando realmente
    # rodamos a avaliação de verdade (os testes usam um retriever falso).
    from src.indexing.embeddings import get_llama_index_embed_model
    from src.indexing.vector_store import VectorStoreManager

    manager = VectorStoreManager()
    manager.load_index(get_llama_index_embed_model())
    retriever = manager.as_retriever(top_k=max_k)

    def retrieve(question: str, k: int) -> List[str]:
        nodes = retriever.retrieve(question)
        return [n.get_content() for n in nodes[:k]]

    return retrieve


def print_report(results: List[QuestionResult], summary: Dict[int, Dict[str, float]]):
    ks = sorted(summary)
    print("\n=== Resultado por pergunta (1º relevante = posição no ranking) ===")
    questions = list(dict.fromkeys(r.question for r in results))
    for q in questions:
        rows = {r.k: r for r in results if r.question == q}
        first = rows[ks[-1]].first_relevant_rank
        pos = f"{first}º" if first else "não encontrado"
        print(f"- {q}\n    1º relevante: {pos}")
        for k in ks:
            r = rows[k]
            print(
                f"    k={k}: precisão={r.precision:.2f}  "
                f"revocação={r.recall:.2f}  F={r.f1:.2f}"
            )

    print("\n=== Média geral ===")
    print(f"{'k':>3} | {'precisão':>8} | {'revocação':>9} | {'medida F':>8} | perguntas")
    for k in ks:
        s = summary[k]
        print(
            f"{k:>3} | {s['precisao']:>8.3f} | {s['revocacao']:>9.3f} | "
            f"{s['medida_f']:>8.3f} | {s['perguntas']}"
        )
    print(
        "\nLembrete: a precisão@k fica limitada quando há poucos chunks "
        "relevantes por pergunta; compare também a revocação e a precisão@1."
    )


def save_csv(results: List[QuestionResult], path: str) -> None:
    # utf-8-sig para o Excel abrir os acentos corretamente
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(
            ["pergunta", "k", "precisao", "revocacao", "medida_f", "posicao_primeiro_relevante"]
        )
        for r in results:
            writer.writerow(
                [
                    r.question,
                    r.k,
                    f"{r.precision:.4f}".replace(".", ","),
                    f"{r.recall:.4f}".replace(".", ","),
                    f"{r.f1:.4f}".replace(".", ","),
                    r.first_relevant_rank,
                ]
            )


def main():
    parser = argparse.ArgumentParser(description="Avaliação da recuperação (precisão, revocação, medida F)")
    parser.add_argument("--gold", default="data/eval/perguntas_exemplo.json", help="Arquivo JSON com o gabarito")
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5], help="Valores de k a avaliar")
    parser.add_argument("--csv", default=None, help="Se informado, salva os resultados por pergunta neste CSV")
    args = parser.parse_args()

    gold = load_gold(args.gold)
    print(f"{len(gold)} pergunta(s) no gabarito. Carregando modelo e conectando ao banco...")
    retrieve_fn = build_real_retrieve_fn(max(args.k))

    results = evaluate(gold, retrieve_fn, args.k)
    summary = summarize(results)
    print_report(results, summary)

    if args.csv:
        save_csv(results, args.csv)
        print(f"\nResultados salvos em {args.csv}")


if __name__ == "__main__":
    main()
