import io
import tempfile
import textwrap
from datetime import date as _date
from pathlib import Path

import streamlit as st
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas

import fill_pdf_overlay as rec
from formato_string import build_string

TEMPLATE_PDF = Path(__file__).parent / "Guia sem lista e radio.pdf"

# Page height from template (pdfplumber measured 842.04)
_H = 842.04

EXAMES = [
    "HEMOGRAMA", "TGO", "TGP", "GGT", "PSA", "TESTOSTERONA", "SOROL SÍFILIS",
    "VDRL", "Ácido Úrico", "AGHBS", "SUMÁRIO DE URINA", "Na+", "K+",
    "URÉIA", "CREATININA", "ANTI-HBC TOTAL", "ANTI-HBs", "ANTI-HCV",
    "ANTI-HVA IGG", "CMV IgM/IgG", "ANTI-HTLV 1/2",
    "BILIRRUBINAS TOTAIS E FRAÇÕES", "PROTEÍNAS TOTAIS E FRAÇÕES",
    "COLESTEROL TOTAIS E FRAÇÕES", "TRIGLICÉRIDES",
    "TOXOPLASMOSE IgM/IgG", "T3", "T4 LIVRE", "TSH", "FERRITINA",
    "P. DE FEZES", "GLICEMIA JEJUM", "HbA1c", "VITAMINA B 12",
    "MAGNÉSIO", "VITAMINA D", "Anti-Chagas", "MICROALBUMINÚRIA",
]

COL_SIZE = len(EXAMES) // 3 + (1 if len(EXAMES) % 3 else 0)

# Exames restritos a particular/plano — nunca incluídos na guia SUS
EXAMES_ESPECIAIS = ["Carga Viral HIV", "Contagem de Células CD4+"]

ROTINA_BASICA = {
    "HEMOGRAMA", "URÉIA", "CREATININA", "TGO", "TGP",
    "COLESTEROL TOTAIS E FRAÇÕES", "TRIGLICÉRIDES", "GLICEMIA JEJUM", "SUMÁRIO DE URINA",
    "VDRL", "ANTI-HCV",
}
SAUDE_HOMEM = ROTINA_BASICA | {"PSA", "TESTOSTERONA"}
INICIAL = set(EXAMES) - {
    "Anti-Chagas", "TESTOSTERONA", "TOXOPLASMOSE IgM/IgG", "CMV IgM/IgG", "PSA",
    "BILIRRUBINAS TOTAIS E FRAÇÕES", "PROTEÍNAS TOTAIS E FRAÇÕES", "MICROALBUMINÚRIA",
}


_LINK_STYLE_DIM = (
    "font-weight:normal;font-size:0.82em;color:inherit;opacity:0.5;text-decoration:none"
)
_BOOKMARKLET_JS = (
    "javascript:(function(){"
    "const g=s=>{const el=document.querySelector('[id$=\"'+s+'\"]');if(!el)return'Não encontrado';"
    "return(el.value!==undefined&&el.value!==''?el.value:el.innerText).trim()||'Não encontrado';};"
    "const pront=g('txtNumeroProntuario')||g('lblProntuario');"
    "const c='Nome: '+g('lblNome')+' | SUS: '+g('lblCartao')+' | Prontuário: '+pront"
    "+' | Nascimento: '+g('lblDataNascimento')+' | Mãe: '+g('lblNomeMae');"
    "navigator.clipboard.writeText(c).then(()=>{"
    "const d=document.createElement('div');d.innerText='Dados copiados!';"
    "d.style.cssText='position:fixed;top:20px;right:20px;background:#28a745;color:#fff;"
    "padding:15px;z-index:99999;border-radius:5px;box-shadow:0 2px 10px rgba(0,0,0,0.3);"
    "font-family:sans-serif;';document.body.appendChild(d);setTimeout(()=>d.remove(),2000);"
    "}).catch(e=>alert('Erro ao copiar: '+e));"
    "})();"
)


def _parse_nome(text: str) -> str | None:
    for part in text.replace("|", "\n").splitlines():
        if ":" not in part:
            continue
        label, _, value = part.partition(":")
        if label.strip().lower() == "nome" and value.strip():
            return value.strip()
    return None


def _do_import_paciente():
    nome_val = _parse_nome(st.session_state.get("import_paste_sol", ""))
    if nome_val:
        st.session_state["nome_sol"] = nome_val
        st.session_state["import_paste_sol"] = ""
        st.session_state.pop("import_warn_sol", None)


def _y(pdfplumber_top: float) -> float:
    return _H - pdfplumber_top


def gerar_pdf_solicitacao(dados: dict, exames_sel: list) -> bytes:
    overlay_buf = io.BytesIO()
    c = rl_canvas.Canvas(overlay_buf, pagesize=(595.56, _H))

    c.setFont("Helvetica", 10)

    # +4 pts offset applied to all fields
    c.drawString(48.2,  _y(104), dados.get("nome", ""))
    c.drawString(422.6, _y(104), dados.get("doc", ""))
    c.drawString(48.2,  _y(130), dados.get("endereco", ""))
    c.drawString(48.2,  _y(156), "Avaliação Clínica")

    y_exame = _y(185)
    if exames_sel:
        col_w = (595.56 - 96.4) / 3
        chunk = -(-len(exames_sel) // 3)  # ceil division
        rows = [exames_sel[i * chunk:(i + 1) * chunk] for i in range(3)]
        n_rows = max(len(r) for r in rows)
        c.setFont("Helvetica", 8.5)
        for row_i in range(n_rows):
            y = y_exame - row_i * 10
            if y < _y(315):
                break
            for col_i in range(3):
                if row_i < len(rows[col_i]):
                    c.drawString(48.2 + col_i * col_w, y, rows[col_i][row_i])

    c.setFont("Helvetica", 10)

    c.save()
    overlay_buf.seek(0)

    template = PdfReader(str(TEMPLATE_PDF))
    overlay = PdfReader(overlay_buf)

    writer = PdfWriter()
    page = template.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)
    return out_buf.read()


def _gerar_receita_bytes(nome: str, data: str, linhas: list, vias: int) -> bytes:
    rec.NOME = nome
    rec.DATA = data
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        rec.gerar_receita_paisagem(linhas, tmp_path, vias=vias)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _gerar_exames_particular_bytes(nome: str, exames_sel: list) -> bytes:
    rec.NOME = nome
    rec.DATA = _date.today().strftime("%d/%m/%Y")
    rec.EXAMES = exames_sel
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        rec.gerar_exames(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


_MAX_MEDS_LINES = 24
_MAX_MEDS_CHARS = 80


def _validate_meds(meds_text: str) -> list:
    """Retorna lista de mensagens de erro; lista vazia = válido."""
    erros = []
    linhas = meds_text.splitlines()
    if len(linhas) > _MAX_MEDS_LINES:
        erros.append(
            f"Texto tem {len(linhas)} linhas — limite é {_MAX_MEDS_LINES}. "
            "Remova linhas excedentes para não sobrepor a assinatura."
        )
    for i, linha in enumerate(linhas, 1):
        if len(linha) > _MAX_MEDS_CHARS:
            erros.append(
                f"Linha {i} tem {len(linha)} caracteres (limite: {_MAX_MEDS_CHARS}): "
                f'"{linha[:50]}{"..." if len(linha) > 50 else ""}"'
            )
    return erros


@st.cache_data(show_spinner=False)
def _cached_receita(nome: str, data: str, meds_text: str, vias: int) -> bytes:
    return _gerar_receita_bytes(nome, data, meds_text.splitlines(), vias)


@st.cache_data(show_spinner=False)
def _cached_exames_particular(nome: str, exames_tuple: tuple) -> bytes:
    return _gerar_exames_particular_bytes(nome, list(exames_tuple))


st.set_page_config(page_title="LACS — Extrator de Exames", layout="centered")

st.markdown("""
<style>
div[data-testid="stButton"] button {
    background-color: #1565c0 !important;
    border-color: #1565c0 !important;
    color: white !important;
}
div[data-testid="stButton"] button:hover {
    background-color: #0d47a1 !important;
    border-color: #0d47a1 !important;
}
div[data-testid="stDownloadButton"] button {
    background-color: #1565c0 !important;
    border-color: #1565c0 !important;
    color: white !important;
}
div[data-testid="stDownloadButton"] button:hover {
    background-color: #0d47a1 !important;
    border-color: #0d47a1 !important;
}
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "home"

if st.query_params.get("show_config_exames") == "1":
    st.query_params.clear()
    st.session_state.page = "solicitar_config"
    st.rerun()

# ── HOME ─────────────────────────────────────────────────────────────────────
if st.session_state.page == "home":
    st.title("LABORATÓRIO CENTRAL DE SALVADOR")
    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Extrair", use_container_width=True):
            st.session_state.page = "extrator"
            st.rerun()
    with c2:
        if st.button("Solicitar", use_container_width=True):
            st.session_state.page = "solicitar"
            st.session_state.solicitar_initialized = False
            st.rerun()
    with c3:
        if st.button("Receita", use_container_width=True):
            st.session_state.page = "receita"
            st.session_state.receita_initialized = False
            st.rerun()
    st.stop()

# ── RECEITA ───────────────────────────────────────────────────────────────────
if st.session_state.page == "receita":
    if not st.session_state.get("receita_initialized", False):
        # Limpa chaves antigas para forçar re-inicialização dos campos
        for _k in list(st.session_state.keys()):
            if _k.startswith(("nome_rec_", "data_rec_", "meds_rec_")):
                del st.session_state[_k]
        st.session_state.rec_nome_count = 0
        st.session_state.rec_meds_count = 0
        st.session_state.receita_initialized = True

    st.title("Receituário")

    if st.button("Voltar", key="voltar_rec_top"):
        st.session_state.page = "home"
        st.rerun()

    nome_rec = st.text_input("Nome", key=f"nome_rec_{st.session_state.rec_nome_count}")

    _data_key = f"data_rec_{st.session_state.rec_nome_count}"
    if _data_key not in st.session_state:
        # Primeira entrada na sessão → preenche com hoje; após "Limpar Tudo" → em branco
        st.session_state[_data_key] = (
            _date.today().strftime("%d/%m/%Y")
            if st.session_state.rec_nome_count == 0
            else ""
        )
    data_rec = st.text_input("Data", key=_data_key)

    _EXEMPLO_MEDS = (
        "Losartano 50mg -------------------- contínuo\n"
        "Uso: 01 cp, via oral, de 12/12 horas."
    )
    _meds_key = f"meds_rec_{st.session_state.rec_meds_count}"
    if _meds_key not in st.session_state:
        # Primeira entrada na sessão → exemplo Losartano; após "Limpar" → em branco
        st.session_state[_meds_key] = (
            _EXEMPLO_MEDS if st.session_state.rec_meds_count == 0 else ""
        )
    meds_text = st.text_area(
        "Medicações",
        key=_meds_key,
        height=420,
        help="Cada medicamento em 2 linhas (nome + posologia). Linha em branco entre eles.",
    )

    # ── contador em tempo real ────────────────────────────────────────────────
    _linhas_atual = meds_text.splitlines() if meds_text else []
    _n_linhas = len(_linhas_atual)
    _max_chars_atual = max((len(l) for l in _linhas_atual), default=0)
    _cor_linhas = "red" if _n_linhas > _MAX_MEDS_LINES else ("orange" if _n_linhas >= _MAX_MEDS_LINES - 2 else "gray")
    _cor_chars  = "red" if _max_chars_atual > _MAX_MEDS_CHARS else "gray"
    st.markdown(
        f"<small style='color:{_cor_linhas}'>Linhas: {_n_linhas}/{_MAX_MEDS_LINES}</small>"
        f"&nbsp;&nbsp;&nbsp;"
        f"<small style='color:{_cor_chars}'>Maior linha: {_max_chars_atual}/{_MAX_MEDS_CHARS} chars</small>",
        unsafe_allow_html=True,
    )

    # ── validação (erros controlam botões; contador acima sinaliza visualmente)
    _erros = _validate_meds(meds_text) if meds_text.strip() else []

    # 2 vias: sempre liberado (formulário em branco permitido); bloqueia só se há erros
    # 1 via:  exige nome; formulário sem medicação é permitido; bloqueia se há erros
    can_1via  = bool(nome_rec.strip()) and not _erros
    can_2vias = not _erros

    if can_1via:
        pdf_1via  = _cached_receita(nome_rec.strip(), data_rec.strip(), meds_text, 1)
    if can_2vias:
        pdf_2vias = _cached_receita(nome_rec.strip(), data_rec.strip(), meds_text, 2)

    rb1, rb2, rb3, rb4 = st.columns(4)
    with rb1:
        if can_1via:
            st.download_button(
                "1 via",
                data=pdf_1via,
                file_name="receita_1via.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.download_button("1 via", data=b"", file_name="receita_1via.pdf",
                               mime="application/pdf", use_container_width=True, disabled=True)
    with rb2:
        if can_2vias:
            st.download_button(
                "2 vias",
                data=pdf_2vias,
                file_name="receita_2vias.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.download_button("2 vias", data=b"", file_name="receita_2vias.pdf",
                               mime="application/pdf", use_container_width=True, disabled=True)
    with rb3:
        if st.button("Limpar medicações", key="limpar_meds_rec", use_container_width=True):
            st.session_state.rec_meds_count += 1
            st.rerun()
    with rb4:
        if st.button("Limpar Tudo", key="limpar_tudo_rec", use_container_width=True):
            st.session_state.rec_nome_count += 1
            st.session_state.rec_meds_count += 1
            st.rerun()

    st.stop()

# ── SOLICITAR ─────────────────────────────────────────────────────────────────
if st.session_state.page == "solicitar":
    if not st.session_state.get("solicitar_initialized", False):
        for _e in EXAMES:
            st.session_state[f"chk_{_e}"] = _e in INICIAL
        for _esp in EXAMES_ESPECIAIS:
            st.session_state[f"chk_esp_{_esp}"] = False
        st.session_state.solicitar_initialized = True

    st.title("Solicitação de Exame")

    if st.button("Voltar", key="voltar_sol_top"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown(
        "**Importar dados do paciente**&nbsp;"
        f"<a href='?show_config_exames=1' style='{_LINK_STYLE_DIM}'>(configurar)</a>",
        unsafe_allow_html=True,
    )
    st.text_input(
        "Cole o texto copiado do sistema",
        placeholder="Nome: ... | SUS: ... | Nascimento: ... | Mãe: ...",
        key="import_paste_sol",
        label_visibility="collapsed",
        on_change=_do_import_paciente,
        autocomplete="off",
    )
    if st.button("Importar", key="btn_importar_sol"):
        _do_import_paciente()
        st.rerun()
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        nome = st.text_input("Nome", key="nome_sol")
    with fc2:
        doc = st.text_input("Doc de Identificação")
    endereco = st.text_input("Endereço")

    pc1, pc2, pc3, pc4 = st.columns(4)
    with pc1:
        if st.button("Inicial", key="preset_inicial", use_container_width=True):
            for _e in EXAMES:
                st.session_state[f"chk_{_e}"] = _e in INICIAL
            for _esp in EXAMES_ESPECIAIS:
                st.session_state[f"chk_esp_{_esp}"] = False
            st.rerun()
    with pc2:
        if st.button("Rotina básica", key="preset_rotina", use_container_width=True):
            for _e in EXAMES:
                st.session_state[f"chk_{_e}"] = _e in ROTINA_BASICA
            for _esp in EXAMES_ESPECIAIS:
                st.session_state[f"chk_esp_{_esp}"] = False
            st.rerun()
    with pc3:
        if st.button("Saúde do homem", key="preset_homem", use_container_width=True):
            for _e in EXAMES:
                st.session_state[f"chk_{_e}"] = _e in SAUDE_HOMEM
            for _esp in EXAMES_ESPECIAIS:
                st.session_state[f"chk_esp_{_esp}"] = False
            st.rerun()
    with pc4:
        if st.button("Limpar", key="preset_limpar", use_container_width=True):
            for _e in EXAMES:
                st.session_state[f"chk_{_e}"] = False
            for _esp in EXAMES_ESPECIAIS:
                st.session_state[f"chk_esp_{_esp}"] = False
            st.rerun()
    # ── Exames especiais (particular/plano) ──────────────────────────────────
    st.markdown("---")
    checks_esp = {}
    for _esp in EXAMES_ESPECIAIS:
        checks_esp[_esp] = st.checkbox(
            f"{_esp} *(somente particular/plano de saúde)*",
            key=f"chk_esp_{_esp}",
        )
    st.markdown("---")

    # ── Exames regulares ──────────────────────────────────────────────────────
    ec1, ec2, ec3 = st.columns(3)
    checks = {}
    for i, exam in enumerate(EXAMES):
        col = [ec1, ec2, ec3][min(i // COL_SIZE, 2)]
        with col:
            checks[exam] = st.checkbox(exam, key=f"chk_{exam}")

    selecionados_sus  = [e for e, v in checks.items() if v]
    selecionados_esp  = [e for e, v in checks_esp.items() if v]
    selecionados_part = selecionados_sus + selecionados_esp

    dados = {
        "nome": nome,
        "doc": doc,
        "endereco": endereco,
    }
    pdf_sus = gerar_pdf_solicitacao(dados, selecionados_sus)

    bot1, bot2, bot3 = st.columns(3)
    with bot1:
        st.download_button(
            "Exames SUS",
            data=pdf_sus,
            file_name="solicitacao_sus.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with bot2:
        if selecionados_part:
            pdf_part = _cached_exames_particular(nome.strip(), tuple(selecionados_part))
            st.download_button(
                "Exames Particular",
                data=pdf_part,
                file_name="solicitacao_particular.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.download_button(
                "Exames Particular",
                data=b"",
                file_name="solicitacao_particular.pdf",
                mime="application/pdf",
                use_container_width=True,
                disabled=True,
            )
    with bot3:
        if st.button("Voltar", key="voltar_sol_bot", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

    st.stop()

# ── SOLICITAR CONFIG ─────────────────────────────────────────────────────────
if st.session_state.page == "solicitar_config":
    if st.button("← Voltar"):
        st.session_state.page = "solicitar"
        st.session_state.solicitar_initialized = False
        st.rerun()

    st.title("Configurar importação de dados do paciente")
    st.markdown(
        "O **bookmarklet VIDA** é um favorito especial no navegador. "
        "Ao ser clicado na página do prontuário do paciente no sistema VIDA, "
        "ele copia automaticamente os dados cadastrais para a área de transferência — "
        "pronto para colar no campo de importação."
    )

    st.subheader("1. Copie o código abaixo")
    st.code(_BOOKMARKLET_JS, language="javascript")

    st.subheader("2. Crie um favorito no navegador")
    st.markdown(
        "- Pressione **Ctrl+Shift+O** (Chrome/Edge) para abrir o gerenciador de favoritos  \n"
        "- Clique em **Adicionar favorito** ou **Novo favorito**  \n"
        "- No campo **Nome**, escreva: `VIDA - Copiar dados`  \n"
        "- No campo **URL**, cole o código copiado acima (começando com `javascript:`)  \n"
        "- Salve"
    )

    st.subheader("3. Como usar no dia a dia")
    st.markdown(
        "1. Abra o sistema VIDA e navegue até o prontuário do paciente  \n"
        "2. Clique no favorito **\"VIDA - Copiar dados\"** na barra de favoritos  \n"
        "3. A notificação **\"Dados copiados!\"** aparecerá brevemente na tela  \n"
        "4. Volte para esta aba e cole o texto no campo de importação (**Ctrl+V**)"
    )

    st.stop()

# ── EXTRATOR ──────────────────────────────────────────────────────────────────
if "clear_count" not in st.session_state:
    st.session_state.clear_count = 0
if "result" not in st.session_state:
    st.session_state.result = ""
if "msg" not in st.session_state:
    st.session_state.msg = None

st.title("Extrator de Exames LACS Salvador")

uploaded = st.file_uploader(
    "Enviar laudo PDF",
    type=["pdf"],
    key=f"uploader_{st.session_state.clear_count}",
)

if uploaded is not None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded.read())
        tmp_path = Path(tmp.name)
    try:
        result = build_string(tmp_path)
        if result.startswith("Lab None"):
            st.session_state.result = ""
            st.session_state.msg = "not_found"
        else:
            st.session_state.result = result
            st.session_state.msg = None
    except Exception:
        st.session_state.result = ""
        st.session_state.msg = "error"
    finally:
        tmp_path.unlink(missing_ok=True)

if st.session_state.msg in ("not_found", "error"):
    st.warning("Nenhum exame reconhecido no arquivo enviado.")

if st.session_state.result:
    wrapped = "\n".join(textwrap.wrap(st.session_state.result, width=80))
    st.text(wrapped)
    st.code(st.session_state.result, language=None)

if st.button("Limpar"):
    st.session_state.result = ""
    st.session_state.msg = None
    st.session_state.clear_count += 1
    st.rerun()

if st.button("Voltar"):
    st.session_state.page = "home"
    st.rerun()
