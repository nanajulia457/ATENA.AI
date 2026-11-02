"""
Pipeline de geração de respostas (etapa 7 da metodologia).

Combina os trechos recuperados do pgvector (via LlamaIndex) com um modelo de
linguagem (LLM) para gerar uma resposta em linguagem natural, contextualizada
e restrita ao conteúdo dos documentos da disciplina — evitando que o sistema
responda com base em conhecimento externo não verificado (fora do escopo
definido na justificativa do TCC).
"""
from dataclasses import dataclass
from typing import List

from src.config import settings

SYSTEM_PROMPT = """\
Você é a Atena, assistente educacional que responde exclusivamente com base nos
trechos de documentos da disciplina fornecidos como contexto abaixo.

Regras:
- Se a resposta não estiver no contexto, diga claramente que a informação
  não foi encontrada nos materiais da disciplina — não invente informações.
- Leia com atenção a data de cada trecho e não misture atividades de datas
  diferentes.
- Se a pergunta puder se referir a mais de uma data ou etapa (por exemplo,
  entrega ao professor e entrega ao orientador), liste todas e diga o que
  acontece em cada uma.
- Não acrescente detalhes (meio de entrega, local, responsável) que não
  estejam escritos nos trechos.
- Cite, quando possível, de qual documento a informação foi extraída.
- Seja direto e objetivo, no idioma da pergunta do usuário.
"""


@dataclass
class RetrievedChunk:
    text: str
    document_title: str
    score: float


@dataclass
class RAGResponse:
    answer: str
    sources: List[RetrievedChunk]


class RAGPipeline:
    def __init__(self, retriever):
        self.retriever = retriever

    def _retrieve(self, question: str) -> List[RetrievedChunk]:
        nodes = self.retriever.retrieve(question)
        return [
            RetrievedChunk(
                text=node.get_content(),
                document_title=node.metadata.get("document_title", "desconhecido"),
                score=node.score or 0.0,
            )
            for node in nodes
        ]

    def _build_prompt(self, question: str, chunks: List[RetrievedChunk]) -> str:
        context = "\n\n".join(
            f"[Documento: {c.document_title}]\n{c.text}" for c in chunks
        )
        return (
            f"Contexto recuperado dos documentos da disciplina:\n\n{context}\n\n"
            f"Pergunta do estudante: {question}\n\n"
            f"Resposta:"
        )

    def _call_llm(self, prompt: str) -> str:
        if settings.llm_provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            response = client.messages.create(
                model=settings.llm_model,
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                block.text for block in response.content if block.type == "text"
            )

        if settings.llm_provider == "groq":
            # Groq oferece um plano gratuito e usa o mesmo formato de API da
            # OpenAI — só muda o endereço do servidor (base_url) e a chave.
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.groq_api_key, base_url=settings.groq_base_url
            )
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content

        # padrão: OpenAI
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def answer(self, question: str) -> RAGResponse:
        chunks = self._retrieve(question)
        if not chunks:
            return RAGResponse(
                answer=(
                    "Não encontrei informações relacionadas nos documentos "
                    "da disciplina disponíveis."
                ),
                sources=[],
            )
        prompt = self._build_prompt(question, chunks)
        answer_text = self._call_llm(prompt)
        return RAGResponse(answer=answer_text, sources=chunks)
