"""Pages of the app and the links between them, shared by every page."""

import os
import re
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
REPO_URL = os.environ.get(
    "REPO_URL",
    "https://github.com/ComunidadIA-OS/voz-experta-de-las-mujeres",
)

PAGES = {
    "herramienta": st.Page("herramienta.py", title="Herramienta", default=True),
    "definiciones": st.Page("paginas/definiciones.py", title="Cómo se calculan los indicadores", url_path="indicadores"),
    "terminos": st.Page("paginas/terminos.py", title="Términos y condiciones", url_path="terminos"),
    "privacidad": st.Page("paginas/privacidad.py", title="Privacidad", url_path="privacidad"),
    "aviso_legal": st.Page("paginas/aviso_legal.py", title="Aviso legal", url_path="aviso-legal"),
}


def nav_links():
    """A row of links to every page, at the top of each one."""
    columns = st.columns(len(PAGES))
    for column, page in zip(columns, PAGES.values()):
        column.page_link(page)
    st.divider()


def show_document(filename):
    """Show one of the legal texts kept next to the code, so the app and the repository match.

    Links to the other legal texts become plain text, because the row of links above
    opens them inside the app without losing the analysis in progress.
    """
    text = (ROOT / filename).read_text(encoding="utf-8")
    text = re.sub(r"\[([^\]]+)\]\((?:TERMINOS_Y_CONDICIONES|PRIVACIDAD|AVISO_LEGAL)\.md\)", r"«\1»", text)
    text = text.replace("](LICENSE)", f"]({REPO_URL}/blob/main/LICENSE)")
    text = text.replace("](README.md)", f"]({REPO_URL}#readme)")
    nav_links()
    st.markdown(text)
