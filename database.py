import streamlit as st
from sqlalchemy import create_engine

# Sua conexão que já funciona
db_url = st.secrets["connections"]["url"]
engine = create_engine(db_url)

# Não vamos mais importar o 'supabase' aqui para não dar erro