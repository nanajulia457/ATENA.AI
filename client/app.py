"""
Aplicação cliente (etapa 9 da metodologia), construída com Streamlit.

Interface de chat da Atena.AI para que o estudante envie perguntas sobre os
materiais da disciplina e visualize as fontes usadas na resposta.

Tema escuro (padrão) e claro, alternados pelo botão no canto superior direito.
A escolha também vai para o endereço (?tema=claro), então sobrevive ao F5.

Rodar localmente (com a API já em execução em outro terminal):
    streamlit run client/app.py
"""
import base64
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

ASSETS = Path(__file__).parent / "assets"
HERO_LOGO = {
    "claro": ASSETS / "athena_logo_ameixa.png",   # silhueta ameixa sobre fundo claro
    "escuro": ASSETS / "athena_logo_dourada.png",  # silhueta dourada sobre fundo escuro
}
TOPBAR_MARK = ASSETS / "athena_marca_dourada.png"
AVATAR_PATH = ASSETS / "athena_avatar.png"

# Se a imagem não estiver disponível, cai para emojis em vez de quebrar.
ASSISTANT_AVATAR = str(AVATAR_PATH) if AVATAR_PATH.exists() else "🦉"
USER_AVATAR = "🎓"

# Troque estas sugestões por perguntas que façam sentido para a sua disciplina.
SUGGESTIONS = [
    "📅  Quando é a próxima prova?",
    "📊  Como é calculada a nota final?",
    "🕒  Qual o horário de atendimento do professor?",
    "📝  Como devo entregar o Trabalho Prático 2?",
]

st.set_page_config(
    page_title="Atena.AI",
    page_icon=str(AVATAR_PATH) if AVATAR_PATH.exists() else "🦉",
    layout="centered",
)

# --- Friso de meandro grego (detalhe da barra superior), como SVG no CSS ---
_MEANDRO_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='12' height='10.5' "
    "viewBox='0 0 8 7'>"
    "<path d='M0.5 6.5 V0.5 H6.5 V4.5 H2.5 V2.5 H4.5 V3.5' "
    "fill='none' stroke='#C9A24D' stroke-width='0.8' stroke-linejoin='miter'/>"
    "</svg>"
)
_MEANDRO_URL = "data:image/svg+xml," + quote(_MEANDRO_SVG)

# --- Paletas dos dois temas (o CSS abaixo só usa estas variáveis) ---
_TEMAS = {
    "claro": {
        "esquema": "light", "fundo": "#FFFBF8", "superficie": "#FFFFFF",
        "superficie-suave": "#FFF8F5", "borda": "#EEDFD8", "borda-forte": "#E6D3CB",
        "ink": "#26102A", "texto-suave": "#6B5670", "destaque": "#5A1A5E",
        "botao": "#5A1A5E", "user-1": "#5A1A5E", "user-2": "#8B2C6F",
        "hero-bg": "#FBDCCF", "hero-art-bg": "#FFF3ED", "hero-desc": "#4A3550",
        "selo-bg": "#FFFFFF", "selo-cor": "#5A1A5E",
        "sombra": "rgba(90, 26, 94, .10)", "sombra-forte": "rgba(90, 26, 94, .22)",
        "foco": "rgba(90, 26, 94, .14)",
    },
    "escuro": {
        "esquema": "dark", "fundo": "#150818", "superficie": "#22102A",
        "superficie-suave": "#2A1533", "borda": "#3B2144", "borda-forte": "#4E2C5A",
        "ink": "#F6ECF4", "texto-suave": "#BBA5C2", "destaque": "#EED8A0",
        "botao": "#8B2C6F", "user-1": "#6A2470", "user-2": "#A23A86",
        "hero-bg": "linear-gradient(135deg, #341340 0%, #521E5C 100%)",
        "hero-art-bg": "#22102A", "hero-desc": "#E3D1E6",
        "selo-bg": "rgba(255, 255, 255, .10)", "selo-cor": "#EED8A0",
        "sombra": "rgba(0, 0, 0, .35)", "sombra-forte": "rgba(0, 0, 0, .55)",
        "foco": "rgba(238, 216, 160, .22)",
    },
}

_CSS_BASE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

__VARS__

/* Fundo e texto em todas as camadas do Streamlit */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: var(--fundo) !important; }
.stApp { font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif; color: var(--ink) !important; }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] strong,
[data-testid="stSpinner"] * { color: var(--ink) !important; }
::selection { background: rgba(240, 103, 58, .35); }

/* Tela limpa: sem cabeçalho, menu, rodapé ou botão de deploy do Streamlit */
#MainMenu, footer, .stAppDeployButton, [data-testid="stHeader"],
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }

.block-container { max-width: 820px; padding-top: 6rem; padding-bottom: 7rem; }

/* Barra superior (fixa, largura total) */
.topbar {
  position: fixed; top: 0; left: 0; right: 0; height: 66px; z-index: 1000001;
  background: #2A0F2C; box-sizing: border-box;
  padding: 0 max(1rem, calc((100vw - 820px) / 2)) 12px;
  display: flex; align-items: center; justify-content: space-between;
}
.topbar-marca { display: flex; align-items: center; gap: .6rem; }
.topbar-mark { width: 34px; height: 34px; display: block; }
.topbar-nome { color: #FFFFFF; font-weight: 800; font-size: 1.2rem; letter-spacing: .01em; }
.topbar-nome span { color: #EED8A0; }
.topbar-selo {
  color: #FBDCCF; border: 1px solid rgba(251, 220, 207, .45); margin-right: 132px;
  border-radius: 999px; padding: .28rem .8rem; font-size: .75rem; font-weight: 600;
}
.topbar-friso {
  position: absolute; left: 0; right: 0; bottom: 0; height: 12px;
  background-image: url("__MEANDRO__"); background-repeat: repeat-x;
  background-position: center; opacity: .9;
}

/* Botão de tema (fixo, dentro da barra superior).
   Os seletores repetem .stButton para ter mais prioridade que os cartões de sugestão. */
.st-key-botao_tema {
  position: fixed; top: 15px; right: max(1rem, calc((100vw - 820px) / 2));
  z-index: 1000002; width: auto !important;
}
.st-key-botao_tema .stButton > button {
  min-height: auto !important; height: auto; padding: .3rem .85rem; border-radius: 999px;
  background: rgba(255, 255, 255, .08); border: 1px solid rgba(251, 220, 207, .5);
  box-shadow: none; justify-content: center; width: auto;
}
.st-key-botao_tema .stButton > button:hover {
  background: rgba(255, 255, 255, .18); border-color: #FBDCCF;
  transform: none; box-shadow: none;
}
.st-key-botao_tema .stButton > button p {
  color: #FBDCCF !important; font-size: .75rem; font-weight: 600;
  white-space: nowrap !important; text-align: center;
}

/* Cabeçalho de boas-vindas */
.hero {
  display: flex; align-items: center; gap: 2rem; flex-wrap: wrap;
  background: var(--hero-bg); border-radius: 26px; padding: 1.7rem 2rem;
  margin-bottom: 1.8rem;
}
.hero-art {
  flex: 0 0 230px; background: var(--hero-art-bg); border-radius: 30px;
  padding: 1.1rem; box-shadow: 0 10px 24px var(--sombra);
}
.hero-art img { width: 100%; display: block; }
.hero-text { flex: 1 1 260px; min-width: 240px; }
.hero-title { font-weight: 800; font-size: 2.05rem; line-height: 1.15; color: var(--ink); margin: 0 0 .6rem; }
.hero-desc { font-size: 1rem; color: var(--hero-desc); line-height: 1.55; margin: 0 0 .9rem; }
.hero-selo {
  display: inline-block; background: var(--selo-bg); color: var(--selo-cor); font-weight: 600;
  font-size: .78rem; padding: .35rem .8rem; border-radius: 999px;
}
.sugestoes-titulo {
  color: var(--texto-suave); font-size: .78rem; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; margin: 0 0 .6rem .2rem;
}

/* Cartões de sugestão (botões) */
.stButton > button {
  background: var(--superficie); color: var(--ink); border: 1px solid var(--borda);
  border-radius: 18px; min-height: 4.4rem; height: auto; padding: .9rem 1.1rem;
  justify-content: flex-start; text-align: left;
  box-shadow: 0 2px 8px var(--sombra); transition: all .15s ease;
}
.stButton > button:hover {
  background: var(--superficie); border-color: var(--destaque); transform: translateY(-2px);
  box-shadow: 0 10px 22px var(--sombra-forte);
}
.stButton > button p, .stButton > button div {
  color: var(--ink); font-weight: 600; font-size: .95rem; text-align: left;
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}
.st-key-nova_conversa .stButton > button {
  min-height: auto !important; padding: .35rem .95rem; border-radius: 999px;
  background: transparent; box-shadow: none;
}
.st-key-nova_conversa .stButton > button p {
  font-size: .85rem; font-weight: 600; color: var(--destaque) !important;
}

/* Mensagens do chat */
[data-testid="stChatMessage"] {
  background: var(--superficie); border: 1px solid var(--borda); border-radius: 20px;
  padding: 1rem 1.2rem; margin-bottom: .9rem; box-shadow: 0 2px 8px var(--sombra);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: linear-gradient(135deg, var(--user-1), var(--user-2)); border: none;
  box-shadow: 0 8px 18px var(--sombra-forte);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) * { color: #FFFFFF !important; }
[data-testid^="stChatMessageAvatar"] { background-color: #FBDCCF !important; border: none; }

/* Fontes consultadas */
[data-testid="stExpander"] { border: 1px solid var(--borda); border-radius: 14px; background: var(--superficie-suave); }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: var(--destaque) !important; font-weight: 700; }
[data-testid="stExpander"] blockquote { border-left: 3px solid #F0673A; }
[data-testid="stExpander"] blockquote p { color: var(--texto-suave) !important; }

/* Barra de pergunta */
[data-testid="stChatInput"], [data-testid="stChatInput"] > div,
[data-testid="stChatInput"] div[data-baseweb="textarea"],
[data-testid="stChatInput"] textarea { background: var(--superficie) !important; }
[data-testid="stChatInput"] textarea { color: var(--ink) !important; caret-color: var(--ink); }
[data-testid="stChatInput"] textarea::placeholder { color: var(--texto-suave) !important; opacity: 1; }
[data-testid="stChatInput"] {
  border: 1.5px solid var(--borda-forte); border-radius: 30px; box-shadow: 0 6px 20px var(--sombra);
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--destaque); box-shadow: 0 0 0 4px var(--foco);
}
[data-testid="stChatInput"] button {
  background: var(--botao) !important; color: #FFFFFF !important; border-radius: 50%;
}
</style>
"""


def build_css(tema):
    variables = ";".join(f"--{nome}: {valor}" for nome, valor in _TEMAS[tema].items())
    root = ":root { " + variables + "; color-scheme: " + _TEMAS[tema]["esquema"] + "; }"
    return _CSS_BASE.replace("__VARS__", root).replace("__MEANDRO__", _MEANDRO_URL)


@lru_cache(maxsize=8)
def _data_uri(path_str):
    data = Path(path_str).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def render_topbar():
    if TOPBAR_MARK.exists():
        mark = f'<img class="topbar-mark" src="{_data_uri(str(TOPBAR_MARK))}" alt="">'
    else:
        mark = "🦉"
    st.markdown(
        '<div class="topbar">'
        f'<div class="topbar-marca">{mark}<span class="topbar-nome">Atena<span>.AI</span></span></div>'
        '<div class="topbar-selo">Assistente da disciplina</div>'
        '<div class="topbar-friso"></div>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_hero(tema):
    logo = HERO_LOGO[tema]
    art = ""
    if logo.exists():
        art = f'<div class="hero-art"><img src="{_data_uri(str(logo))}" alt="Athena"></div>'
    st.markdown(
        '<div class="hero">'
        f"{art}"
        '<div class="hero-text">'
        '<div class="hero-title">Olá! Eu sou a Atena.</div>'
        '<div class="hero-desc">Tire suas dúvidas sobre provas, notas, prazos e entregas. '
        "Eu respondo com base nos documentos oficiais da sua disciplina.</div>"
        '<span class="hero-selo">📄 Respostas baseadas nos materiais da disciplina</span>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def render_sources(sources):
    """Mostra os trechos dos documentos usados para gerar a resposta."""
    with st.expander("📜 Fontes consultadas"):
        for source in sources:
            excerpt = source["excerpt"].replace("\n", " ")
            st.markdown(
                f"**{source['document_title']}** · similaridade {source['score']:.2f}\n\n"
                f"> {excerpt}..."
            )


def avatar_for(role):
    return ASSISTANT_AVATAR if role == "assistant" else USER_AVATAR


def use_suggestion(text):
    # Callback do botão: roda antes da página recarregar.
    st.session_state["pending_question"] = text.split("  ", 1)[-1].strip()


def new_conversation():
    st.session_state.history = []


def toggle_theme():
    novo = "claro" if st.session_state["tema"] == "escuro" else "escuro"
    st.session_state["tema"] = novo
    st.query_params["tema"] = novo


# --- Tema: escuro por padrão; lembra a escolha do endereço (?tema=claro) ---
if "tema" not in st.session_state:
    escolhido = st.query_params.get("tema")
    st.session_state["tema"] = escolhido if escolhido in _TEMAS else "escuro"
tema = st.session_state["tema"]

st.markdown(build_css(tema), unsafe_allow_html=True)
render_topbar()
st.button(
    "☀️ Tema claro" if tema == "escuro" else "🌙 Tema escuro",
    key="botao_tema", on_click=toggle_theme,
)

if "history" not in st.session_state:
    st.session_state.history = []

# Pergunta vinda de um cartão de sugestão (se houver)
question = st.session_state.pop("pending_question", None)

if not st.session_state.history and not question:
    render_hero(tema)
    st.markdown('<div class="sugestoes-titulo">Experimente perguntar</div>', unsafe_allow_html=True)
    for start in range(0, len(SUGGESTIONS), 2):
        columns = st.columns(2)
        for offset, column in enumerate(columns):
            index = start + offset
            if index < len(SUGGESTIONS):
                text = SUGGESTIONS[index]
                column.button(
                    text, key=f"sugestao_{index}", on_click=use_suggestion,
                    args=(text,), use_container_width=True,
                )
elif st.session_state.history:
    st.button("＋ Nova conversa", key="nova_conversa", on_click=new_conversation)

for message in st.session_state.history:
    with st.chat_message(message["role"], avatar=avatar_for(message["role"])):
        st.markdown(message["content"])
        if message.get("sources"):
            render_sources(message["sources"])

typed = st.chat_input("Pergunte à Atena sobre a disciplina...")
question = question or typed

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(question)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        with st.spinner("A Atena está consultando os materiais da disciplina..."):
            try:
                response = requests.post(
                    f"{API_URL}/ask", json={"question": question}, timeout=180
                )
                response.raise_for_status()
                data = response.json()
                st.markdown(data["answer"])
                if data.get("sources"):
                    render_sources(data["sources"])
                st.session_state.history.append(
                    {
                        "role": "assistant",
                        "content": data["answer"],
                        "sources": data.get("sources", []),
                    }
                )
            except requests.exceptions.RequestException as exc:
                error_msg = f"Erro ao consultar a API: {exc}"
                st.error(error_msg)
                st.session_state.history.append(
                    {"role": "assistant", "content": error_msg}
                )
