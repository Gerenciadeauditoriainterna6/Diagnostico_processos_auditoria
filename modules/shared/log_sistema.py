"""
Módulo de Auditoria/Log do Sistema
Registra todas as ações dos usuários
"""

import json
from datetime import datetime
from sqlalchemy import text
from database import engine
# ===== MIGRAÇÃO PARA FLASK =====
# Streamlit removido - sistema agora usa Flask
# import streamlit as st  # REMOVIDO

# Placeholder para evitar erros (as funções Streamlit não serão chamadas no Flask)
class _DummyStreamlit:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

st = _DummyStreamlit()
# ===== FIM DA MIGRAÇÃO =====
import pandas as pd
from flask import session, request

def registrar_log(tabela, registro_id, operacao, dados_anteriores=None, dados_novos=None, query_sql=None):
    """
    Registra uma ação do usuário na tabela de log (adaptado para Flask)
    """
    try:
        with engine.begin() as conn:
            # Pega informações do usuário logado (agora do Flask session)
            usuario_id = session.get('usuario_id', None)
            usuario_nome = session.get('usuario_nome', session.get('usuario_logado', 'Sistema'))

            # Pega o IP do cliente (Flask request)
            ip_origem = request.remote_addr if request else '0.0.0.0'

            # Converte dicionários para JSON (STRING)
            dados_anteriores_json = json.dumps(dados_anteriores, default=str) if dados_anteriores else None
            dados_novos_json = json.dumps(dados_novos, default=str) if dados_novos else None

            conn.execute(text("""
                INSERT INTO log_auditoria
                    (tabela_afetada, registro_id, operacao, dados_anteriores, dados_novos,
                     usuario_id, usuario_nome, ip_origem, query_sql, data_hora)
                VALUES
                    (:tabela, :registro_id, :operacao, :dados_anteriores, :dados_novos,
                     :usuario_id, :usuario_nome, :ip_origem, :query_sql, :data_hora)
            """), {
                'tabela': tabela,
                'registro_id': registro_id,
                'operacao': operacao,
                'dados_anteriores': dados_anteriores_json,
                'dados_novos': dados_novos_json,
                'usuario_id': usuario_id,
                'usuario_nome': usuario_nome,
                'ip_origem': ip_origem,
                'query_sql': query_sql,
                'data_hora': datetime.now()
            })

            print(f"✅ Log registrado: {tabela} - {operacao} - ID: {registro_id}")
            return True
    except Exception as e:
        print(f"❌ Erro ao registrar log: {e}")
        import traceback
        traceback.print_exc()
        return False

def consultar_log(tabela=None, registro_id=None, usuario_id=None, operacao=None, limite=100):
    """
    Consulta o log de auditoria com filtros opcionais
    
    Retorna um DataFrame com os registros
    """
    query = """
        SELECT id, tabela_afetada, registro_id, operacao, 
               dados_anteriores, dados_novos, usuario_nome, data_hora
        FROM log_auditoria
        WHERE 1=1
    """
    params = {}
    
    if tabela:
        query += " AND tabela_afetada = :tabela"
        params['tabela'] = tabela
    
    if registro_id:
        query += " AND registro_id = :registro_id"
        params['registro_id'] = registro_id
    
    if usuario_id:
        query += " AND usuario_id = :usuario_id"
        params['usuario_id'] = usuario_id
    
    if operacao:
        query += " AND operacao = :operacao"
        params['operacao'] = operacao
    
    # LIMIT não aceita placeholder, usamos f-string (valor é inteiro, seguro)
    query += f" ORDER BY data_hora DESC LIMIT {limite}"
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)
    
def exibir_log_interface():
    """Exibe uma interface no Streamlit para consultar logs"""
    st.subheader("📋 Histórico de Alterações")

    col1, col2 = st.columns(2)
    with col1:
        tabela_filtro = st.selectbox(
            'Filtrar por tabela:',
            ['Todas', 'processos', 'riscos', 'auditorias', 'funcionarios_area']
        )
    with col2:
        limite = st.slider("Quantidade de registros:", 10, 500, 50)

        if st.button("🔍 Consultar Log"):
            tabela_param = None if tabela_filtro == "Todas" else tabela_filtro

            df = consultar_log(tabela=tabela_param)

            if not df.empty:
                st.dataframe(df.head(limite), use_container_width=True)

                # Expandir para ver detalhes
                for idx, row in df.head(limite).iterrows():
                    with st.expander(f"🔹 {row['data_hora']} - {row['usuario_nome']} - {row['operacao']} em {row['tabela_afetada']}"):
                        st.write(f"**Registro ID:** {row['registro_id']}")
                        if row['dados_anteriores']:
                            st.write(f"**Dados anteriores:**")
                            st.json(row['dados_anteriores'])
                        if row['dados_novos']:
                            st.write(f"**Dados novos:**")
                            st.json(row['dados_novos'])
        else:
            st.info("Nenhum registro encontrado")


# def tela_historico():
#     """
#     Tela para mostrar o histórico de alterações do sistema
#     """

#     # ===== CONTROLE DE ACESSO =====
#     usuario_perfil = st.session_state.get('usuario_perfil', 'auditor')

#     if usuario_perfil != 'administrador':
#         st.error("⛔ Acesso negado! Esta área é restrita a administradores.")
#         st.info("Você não tem permissão para visualizar o histórico de alterações do sistema.")
#     else:
    
#         # ==== TELA DE HISTÓRICO (apenas para adminsitradores) ====

#         st.subheader("📜 Histórico de Alterações")
        
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             tabela_filtro = st.selectbox("Filtrar por tabela:", 
#                 ["Todas", "processos", "riscos", "auditorias", "funcionarios_area",
#                 "etapas_processo", "controles_etapa", "checklist_sessoes"])
            
#         with col2:
#             # CORRIGIDO: agora são opções de OPERAÇÃO
#             operacao_filtro = st.selectbox("Filtrar por operação:", 
#                 ["Todas", "INSERT", "UPDATE", "DELETE"])

#         with col3:
#             limite = st.slider("Quantidade de registros:", 10, 500, 50)
        
#         if st.button("🔍 Consultar"):
#             tabela = None if tabela_filtro == "Todas" else tabela_filtro
#             operacao = None if operacao_filtro == "Todas" else operacao_filtro
#             df = consultar_log(tabela=tabela, limite=limite)

#             if operacao:
#                 df = df[df['operacao'] == operacao]
            
#             if not df.empty:
#                 st.dataframe(df, use_container_width=True)
                
#                 # Ver detalhes
#                 for _, row in df.iterrows():
#                     with st.expander(f"{row['data_hora']} - {row['usuario_nome']} - {row['operacao']}"):
#                         st.write(f"**Tabela:** {row['tabela_afetada']}")
#                         st.write(f"**Registro ID:** {row['registro_id']}")
#                         if row['dados_anteriores']:
#                             st.write("**Antes:**")
#                             st.json(row['dados_anteriores'])
#                         if row['dados_novos']:
#                             st.write("**Depois:**")
#                             st.json(row['dados_novos'])
#             else:
#                 st.info("Nenhum registro encontrado")