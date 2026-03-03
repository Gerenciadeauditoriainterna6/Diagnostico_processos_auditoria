import streamlit as st
from sqlalchemy import create_engine

# A conexão fica centralizada aqui
db_url = st.secrets["connections"]["url"]
engine = create_engine(db_url)