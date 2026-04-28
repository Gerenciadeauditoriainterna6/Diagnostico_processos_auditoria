import streamlit as st
from sqlalchemy import text
from database import engine
import pandas as pd

def usuario_tem_acesso_auditoria(auditoria_id):
    """
    Verifica se o usuário logado tem acesso à auditoria.
    Administrador sempre tem acesso.
    """

    # Administrador vê tudo
    if st.session_state.get('usuario_perfil') == 'administrador':
        return True

    usuario_nome = st.session_state.get('usuario_nome')
    if not usuario_nome:
        return False
    
    query = text("""
        SELECT responsavel_equipe FROM auditorias
        WHERE id = :auditoria_id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"auditoria_id": auditoria_id}).scalar()

    if not result:
        return False
    
    # Verifica se o nome do usuário está no array
    return usuario_nome in result

def filtrar_auditorias_por_usuario(df_auditorias):
    """
    Filtra o DataFrame de auditorias para mostrar apenas as que o usuário tem acesso.
    Adminsitrador vê todas.
    """

    if st.session_state.get("usuario_perfil") == 'administrador':
        return df_auditorias
    
    usuario_nome = st.session_state.get('usuario_nome')
    if not usuario_nome or df_auditorias.empty:
        return pd.DataFrame() # Retorna vazio
    
    # Filtra mantendo apenas auditorias onde usuário está no responsavel_equipe
    def usuario_esta_no_time(responsaveis):
        if not responsaveis:
            return False
        return usuario_nome in responsaveis
    
    df_filtrado = df_auditorias[df_auditorias['responsavel_equipe'].apply(usuario_esta_no_time)]
    return df_filtrado