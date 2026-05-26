import tempfile
import textwrap
from pathlib import Path

import streamlit as st

from formato_string import build_string

st.set_page_config(page_title="LACS — Extrator de Exames", layout="centered")
st.title("Extrator de Exames LACS Salvador")

if "clear_count" not in st.session_state:
    st.session_state.clear_count = 0
if "result" not in st.session_state:
    st.session_state.result = ""
if "msg" not in st.session_state:
    st.session_state.msg = None  # None | "not_found" | "error"

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

if st.session_state.msg == "not_found":
    st.warning("Nenhum exame reconhecido no arquivo enviado.")
elif st.session_state.msg == "error":
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
