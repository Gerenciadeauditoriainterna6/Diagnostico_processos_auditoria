import streamlit as st
from sqlalchemy import create_engine

# A conexão fica centralizada aqui
def get_engine():
    db_url = st.secrets["connections"]["url"]
    return create_engine(db_url)