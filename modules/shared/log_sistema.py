"""
Módulo de Auditoria/Log do Sistema
Registra todas as ações dos usuários
"""

import json
from datetime import datetime
from sqlalchemy import text
from database import engine
import streamlit as st
import pandas as pd

def registrar_log(tabela, registro_id, operacao, dados_anteriores=None, dados_novos=None):
    """
    Registra uma ação do usuário na tabela de log
    
    Parâmetros:
    - tabela: nome da tabela afetada
    - registro_id: ID do registro afetado
    - operacao: 'INSERT', 'UPDATE', 'DELETE'
    - dados_anteriores: dicionário com dados antes da alteração
    - dados_novos: dicionário com dados depois da alteração
    """
    try:
        with engine.begin() as conn:
            # Pega informações do usuário logado (se existir)
            usuario_id = st.session_state.get('usuario_id', None)
            usuario_nome = st.session_state.get('usuario_logado', 'Sistema')

            # Converte dicionários para JSON (STRING)
            dados_anteriores_json = json.dumps(dados_anteriores, default=str) if dados_anteriores else None
            dados_novos_json = json.dumps(dados_novos, default=str) if dados_novos else None

            conn.execute(text("""
                INSERT INTO log_auditoria
                    (tabela_afetada, registro_id, operacao, dados_anteriores, dados_novos,
                     usuario_id, usuario_nome, data_hora)
                VALUES
                    (:tabela, :registro_id, :operacao, :dados_anteriores, :dados_novos,
                     :usuario_id, :usuario_nome, :data_hora)
            """), {
                'tabela': tabela,
                'registro_id': registro_id,
                'operacao': operacao,
                'dados_anteriores': dados_anteriores_json,  # ← USAR A VARIÁVEL JSON
                'dados_novos': dados_novos_json,            # ← USAR A VARIÁVEL JSON
                'usuario_id': usuario_id,
                'usuario_nome': usuario_nome,
                'data_hora': datetime.now()
            })

            return True
    except Exception as e:
        print(f"Erro ao registrar log: {e}")
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


def tela_historico():
    """
    Tela para mostrar o histórico de alterações do sistema
    """

    st.subheader("📜 Histórico de Alterações")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        tabela_filtro = st.selectbox("Filtrar por tabela:", 
            ["Todas", "processos", "riscos", "auditorias", "funcionarios_area",
             "etapas_processo", "controles_etapa", "checklist_sessoes"])
        
    with col2:
        # CORRIGIDO: agora são opções de OPERAÇÃO
        operacao_filtro = st.selectbox("Filtrar por operação:", 
            ["Todas", "INSERT", "UPDATE", "DELETE"])

    with col3:
        limite = st.slider("Quantidade de registros:", 10, 500, 50)
    
    if st.button("🔍 Consultar"):
        tabela = None if tabela_filtro == "Todas" else tabela_filtro
        operacao = None if operacao_filtro == "Todas" else operacao_filtro
        df = consultar_log(tabela=tabela, limite=limite)

        if operacao:
            df = df[df['operacao'] == operacao]
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            # Ver detalhes
            for _, row in df.iterrows():
                with st.expander(f"{row['data_hora']} - {row['usuario_nome']} - {row['operacao']}"):
                    st.write(f"**Tabela:** {row['tabela_afetada']}")
                    st.write(f"**Registro ID:** {row['registro_id']}")
                    if row['dados_anteriores']:
                        st.write("**Antes:**")
                        st.json(row['dados_anteriores'])
                    if row['dados_novos']:
                        st.write("**Depois:**")
                        st.json(row['dados_novos'])
        else:
            st.info("Nenhum registro encontrado")