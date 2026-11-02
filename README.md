# Atena.AI — Assistente Educacional RAG

Implementação do sistema proposto no TCC **"Assistente educacional baseado em
Retrieval-Augmented Generation para consulta inteligente a materiais de
disciplina"**.

Cada módulo do código corresponde diretamente a uma etapa da metodologia
descrita no capítulo 5 do trabalho:

| Etapa da metodologia | Módulo |
|---|---|
| Processamento com Docling | `src/ingestion/document_processor.py` |
| Chunking | `src/ingestion/chunking.py` |
| Embeddings | `src/indexing/embeddings.py` |
| pgvector + LlamaIndex (retrieval) | `src/indexing/vector_store.py` |
| Geração de respostas (LLM) | `src/rag/pipeline.py` |
| API REST (FastAPI) | `src/api/main.py` |
| Aplicação cliente | `client/app.py` (Streamlit) |
| Script de ingestão | `src/scripts/ingest.py` |
| Testes | `tests/test_chunking.py` |

## Estrutura do repositório

```
├── client/            aplicação cliente (Streamlit) e imagens da marca
├── data/
│   ├── raw/           documentos de entrada da ingestão
│   ├── debug/         texto extraído e chunks gerados (conferência)
│   └── eval/          gabaritos de perguntas para a avaliação
├── resultados/        métricas da avaliação (antes.csv e depois.csv)
├── src/               código do sistema (ingestão, indexação, RAG, API, scripts)
├── tests/             testes automatizados
└── .streamlit/        tema da interface
```

## 1. Pré-requisitos

- Python 3.10+
- Docker (para subir o Postgres com pgvector facilmente) — ou uma instância
  Postgres própria com a extensão `pgvector` instalada.
- Uma chave de API da OpenAI **ou** da Anthropic.

## 2. Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edite o .env e preencha OPENAI_API_KEY ou ANTHROPIC_API_KEY (e LLM_PROVIDER)
```

## 3. Subir o banco vetorial

```bash
docker compose up -d
```

## 4. Colocar os documentos da disciplina

Coloque os arquivos PDF/DOCX reais (planos de ensino, cronogramas etc.) em
`data/raw/`. Já incluí `data/raw/plano_de_ensino_exemplo.txt`, um documento
**fictício**, só para você testar o pipeline de ponta a ponta antes de ter
os documentos oficiais em mãos.

## 5. Rodar a ingestão (processa, chunka, gera embeddings e indexa)

```bash
python -m src.scripts.ingest --dir data/raw
```

## 6. Subir a API

```bash
uvicorn src.api.main:app --reload --port 8000
```

Testar rapidamente:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual o peso do Trabalho Prático 1 na nota final?"}'
```

## 7. Subir a aplicação cliente

Em outro terminal, com a API já rodando:

```bash
streamlit run client/app.py
```

Acesse `http://localhost:8501`.

## 8. Rodar os testes

```bash
pytest tests/ -v
```

## Trocando o modelo de embeddings ou o LLM

Tudo é configurável via `.env`:
- `EMBEDDING_MODEL` / `EMBEDDING_DIM`: para usar outro modelo do
  sentence-transformers (lembre de ajustar a dimensão correspondente).
- `LLM_PROVIDER` (`openai` ou `anthropic`) e `LLM_MODEL`.

## Provedor de LLM gratuito (Groq)

Além de OpenAI e Anthropic, o projeto aceita o Groq, que tem plano gratuito
sem cartão. No `.env`:

```
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=sua_chave_sem_espacos
```

Os catálogos de modelos mudam com frequência. Se aparecer `model_not_found`,
consulte https://console.groq.com/docs/models e troque o `LLM_MODEL`.

## Usando documentos reais (PDF/DOCX)

1. Copie os arquivos para `data/raw/`.
2. Pare a API (`Ctrl+C`) e rode a ingestão:
   ```bash
   python -m src.scripts.ingest --dir data/raw
   ```
   A ingestão **recria o índice do zero** com todos os arquivos da pasta, então
   não há chunks duplicados ao rodar de novo. Na primeira vez com PDF/DOCX, o
   Docling baixa seus modelos de layout (precisa de internet e demora mais).
3. Suba a API de novo e teste perguntas cuja resposta você conhece.

## Avaliação da recuperação (precisão, revocação e medida F)

O gabarito fica em JSON, com perguntas e os trechos que precisam aparecer no
contexto recuperado (veja `data/eval/perguntas_exemplo.json`):

```json
[{"pergunta": "Quando é a Prova 1?", "trechos_esperados": ["Semana 8 (28/09): Prova 1"]}]
```

Rodar (com o banco no ar e a ingestão feita):

```bash
python -m src.scripts.evaluate --gold data/eval/perguntas_exemplo.json --k 1 3 5 --csv resultados.csv
```

Um chunk é relevante se contém pelo menos um trecho esperado. A precisão@k é
limitada quando há poucos chunks relevantes por pergunta (com 1 relevante,
a precisão@5 é no máximo 0,20), por isso o script reporta vários valores de k.
Para a avaliação do TCC, crie um gabarito com perguntas sobre os seus
documentos reais.

## Iniciar tudo com um clique (Windows)

Com o Docker Desktop aberto ("Engine running"), dê duplo clique em
`iniciar_atena.bat`. Ele sobe o banco, a API e a aplicação em janelas separadas.

## Documentos da disciplina (`data/raw/`)

- `CALENDARIO CMPMPSI 2026-1.pdf` e `Atividade 1 - Revisão de Banco de Dados 1 - 367540).docx`:
  documentos reais da disciplina, publicados com autorização dos professores.
- `plano_de_ensino_exemplo.txt`: documento **fictício**, usado pelo gabarito
  `data/eval/perguntas_exemplo.json` para testar o pipeline de ponta a ponta.

A ingestão processa todos os arquivos da pasta.

## Arquivos de conferência (`data/debug/`)

Gerados automaticamente pelo `src/scripts/ingest.py` a cada ingestão. Servem
para verificar o que o sistema "enxergou" de cada documento:

- `<documento>.extraido.md`: texto que o Docling extraiu do PDF/DOCX, em
  Markdown. Mostra, por exemplo, como as tabelas do calendário foram lidas.
- `chunks.txt`: lista de todos os chunks gerados, com o documento de origem,
  a posição e o tamanho em caracteres. Nele é possível ver o chunking de
  tabelas em ação: cada linha do calendário vira um chunk próprio, no
  formato `16/03 (março): ...`.

Como a ingestão recria esses arquivos, eles refletem sempre a última execução.

## Resultados da avaliação (`resultados/`)

`antes.csv` e `depois.csv` trazem as métricas de recuperação calculadas pelo
`src/scripts/evaluate.py` para as 10 perguntas do gabarito
`data/eval/perguntas_calendario.json`:

- **antes**: segmentação inicial, em que linhas da tabela do calendário eram
  misturadas no mesmo chunk; acervo só com o calendário;
- **depois**: segmentação refinada, sensível à estrutura das tabelas (um chunk
  por linha de data); acervo com o calendário e a atividade de Banco de Dados 2.

Cada linha é uma pergunta em um valor de k (1, 3 e 5), com precisão,
revocação, medida F e a posição do primeiro chunk relevante no ranking
(0 = nenhum relevante encontrado). Os arquivos usam `;` como separador e
vírgula decimal, para abrir direto no Excel.

Médias das 10 perguntas (medida F = média das medidas F por pergunta):

| k | Precisão (antes → depois) | Revocação (antes → depois) | Medida F (antes → depois) |
|---|---|---|---|
| 1 | 0,200 → 0,100 | 0,150 → 0,100 | 0,167 → 0,100 |
| 3 | 0,100 → 0,133 | 0,200 → 0,400 | 0,130 → 0,200 |
| 5 | 0,100 → 0,100 | 0,400 → 0,500 | 0,157 → 0,167 |

A comparação não isola o efeito da segmentação, pois o acervo também mudou
entre as duas execuções. A discussão completa está no texto do TCC.

Observação: o resumo impresso pelo `evaluate.py` calcula a medida F geral como
a média harmônica entre a precisão e a revocação médias, por isso pode diferir
um pouco dos valores acima (ex.: k = 5 antes dá 0,160 por esse método).
