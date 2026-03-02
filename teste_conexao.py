import streamlit as st
from sqlalchemy import create_engine, text

st.title("Teste de Conexão")

try:
    # Busca a URL que você colocou no secrets.toml
    url = st.secrets["connections"]["url"]
    
    # Tenta criar a conexão
    engine = create_engine(url)
    
    # Tenta uma operação simples (SELECT 1 é só para ver se o banco responde)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        
    st.success("Sucesso! O Python está falando com o seu banco de dados na nuvem.")
    st.balloons() # Uma pequena comemoração visual

except Exception as e:
    st.error("Ops, algo deu errado. Verifique o erro abaixo:")
    st.write(e)
    st.info("Dica: Verifique se a senha no secrets.toml está correta e se o caractere especial foi substituído.")