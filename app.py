"""Entry point: the tool and its reference pages.

    streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="Voz experta de las mujeres", layout="wide")

from navegacion import PAGES  # noqa: E402  (after set_page_config)

st.navigation(list(PAGES.values())).run()
