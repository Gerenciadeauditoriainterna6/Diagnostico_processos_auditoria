"""
Módulo de Comunicação dos Resultados - Evolução da Auditoria
"""
import streamlit as st
import json
import os
from datetime import datetime
import time as time_module
from database import engine
from sqlalchemy import text
import pandas as pd


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def listar_anos_disponiveis():
    """Lista todos os anos que têm auditorias cadastradas"""
    query = text("""
        SELECT DISTINCT ano
        FROM auditorias
        ORDER BY ano DESC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        return df['ano'].tolist() if not df.empty else [datetime.now().year]

def carregar_evolucao(ano=2026):
    """Carrega o texto de evolução salvo (JSON)"""
    # Caminho para o arquivo na raiz do projeto
    arquivo = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          f"evolucao_auditoria_{ano}.json")
    
    # Texto padrão se não existir
    padrao = {
        "situacao_inicial": "- Equipe: Nenhum auditor formal designado\n- Processos: Nenhum processo mapeado\n- Sistema: Nenhum sistema automatizado\n- Metodologia: Processos manuais e descentralizados",
        "evolucao": "- Equipe: 5 auditores contratados e treinados\n- Processos: Processos sendo mapeados via sistema\n- Sistema: Sistema em desenvolvimento e testes\n- Metodologia: Padronização em andamento",
        "proximos_passos": "- Expandir equipe para 7 auditores\n- Finalizar mapeamento de 20 processos\n- Concluir desenvolvimento do sistema\n- Implementar melhorias contínuas"
    }
    
    if os.path.exists(arquivo):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                return dados
        except:
            return padrao
    return padrao


def salvar_evolucao(dados, ano=2026):
    """Salva o texto de evolução em JSON"""
    arquivo = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          f"evolucao_auditoria_{ano}.json")
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return True


def contar_auditores():
    """Conta quantos auditores estão cadastrados"""
    query = text("""
        SELECT COUNT(*) FROM funcionarios_area
        WHERE id_area = 2
    """)
    with engine.connect() as conn:
        result = conn.execute(query).scalar()
        return result if result else 0


def contar_processos_ano(ano=2026):
    """Conta processos mapeados no ano"""
    query = text("""
        SELECT COUNT(*) FROM processos 
        WHERE EXTRACT(YEAR FROM created_at) = :ano
    """)
    with engine.connect() as conn:
        return conn.execute(query, {"ano": ano}).scalar() or 0


def contar_checklists_realizados(ano=2026):
    """Conta checklists concluídos no ano"""
    query = text("""
        SELECT COUNT(*) FROM checklist_sessoes 
        WHERE EXTRACT(YEAR FROM data_inicio) = :ano 
        AND status = 'Concluído'
    """)
    with engine.connect() as conn:
        return conn.execute(query, {"ano": ano}).scalar() or 0


def contar_auditorias_realizadas(ano=2026):
    """Conta auditorias concluídas no ano"""
    query = text("""
        SELECT COUNT(*) FROM auditorias 
        WHERE ano = :ano AND status = 'Concluída'
    """)
    with engine.connect() as conn:
        return conn.execute(query, {"ano": ano}).scalar() or 0


def barra_progresso_personalizada(percentual):
    """Exibe barra de progresso com cores personalizadas"""
    if percentual < 33:
        cor = "#dc3545"
    elif percentual < 66:
        cor = "#ffc107"
    else:
        cor = "#28a745"
    
    st.markdown(f"""
        <div style="margin: 5px 0;">
            <div style="background-color: #e0e0e0; border-radius: 10px; height: 8px; overflow: hidden;">
                <div style="width: {percentual}%; background: {cor}; height: 100%; border-radius: 10px; transition: width 0.3s ease;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ============================================
# TELA PRINCIPAL
# ============================================

def tela_evolucao_auditoria():
    """Exibe a evolução da auditoria (Comunicação dos Resultados)"""
    
    st.title("📈 Evolução da Auditoria - 2026")

    # ==== SELETOR DE ANO ====
    anos_disponiveis = listar_anos_disponiveis()
    col_ano1, col_ano2 = st.columns([1, 3])
    with col_ano1:
            ano_selecionado = st.selectbox(
            "Selecione o ano:",
            options=anos_disponiveis,
            index=0,
            key="ano_evolucao"
        )
    
    # ===== MÉTRICAS AUTOMÁTICAS =====
    st.subheader("Métricas de Execução")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        qtd_auditores = contar_auditores()
        st.metric("👥 Auditores", qtd_auditores)
    
    with col2:
        qtd_processos = contar_processos_ano(2026)
        st.metric("📋 Processos Mapeados", qtd_processos)
    
    with col3:
        qtd_checklists = contar_checklists_realizados(2026)
        st.metric("✅ Checklists Concluídos", qtd_checklists)
    
    with col4:
        qtd_auditorias = contar_auditorias_realizadas(2026)
        st.metric("🎯 Auditorias Concluídas", qtd_auditorias)
    
    st.divider()
    
    # ===== BOTÃO DE EDIÇÃO =====
    if 'modo_edicao_evolucao' not in st.session_state:
        st.session_state.modo_edicao_evolucao = False
    
    col_header, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("✏️ Editar Evolução", key="btn_editar_evolucao", use_container_width=True):
            st.session_state.modo_edicao_evolucao = not st.session_state.modo_edicao_evolucao
            st.rerun()
    
    # ===== MODO EDIÇÃO =====
    if st.session_state.modo_edicao_evolucao:
        st.info("✏️ **Modo de Edição** - Altere os textos abaixo e clique em Salvar")
        
        evolucao = carregar_evolucao(2026)
        
        with st.form("form_evolucao"):
            st.subheader("📌 Situação Inicial (Planejado)")
            situacao_inicial = st.text_area(
                "Descreva como estávamos no início do ano:",
                value=evolucao.get("situacao_inicial", ""),
                height=150,
                help="Use marcadores (- item) para melhor visualização"
            )
            
            st.subheader("📈 Evolução (Realizado)")
            evolucao_texto = st.text_area(
                "Descreva o que foi alcançado durante o ano:",
                value=evolucao.get("evolucao", ""),
                height=150,
                help="Use marcadores (- item) para melhor visualização"
            )
            
            st.subheader("🚀 Próximos Passos")
            proximos_passos = st.text_area(
                "Descreva os próximos passos para o próximo ano:",
                value=evolucao.get("proximos_passos", ""),
                height=150,
                help="Use marcadores (- item) para melhor visualização"
            )
            
            col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
            with col_s1:
                submitted = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
            with col_s2:
                cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            if submitted:
                dados = {
                    "situacao_inicial": situacao_inicial,
                    "evolucao": evolucao_texto,
                    "proximos_passos": proximos_passos,
                    "data_atualizacao": datetime.now().isoformat()
                }
                if salvar_evolucao(dados, 2026):
                    st.success("✅ Evolução salva com sucesso!")
                    st.balloons()
                    st.session_state.modo_edicao_evolucao = False
                    time_module.sleep(1)
                    st.rerun()
            
            if cancelar:
                st.session_state.modo_edicao_evolucao = False
                st.rerun()
    
    # ===== MODO VISUALIZAÇÃO =====
    else:
        evolucao = carregar_evolucao(2026)
        
        # Situação Inicial
        with st.expander("📌 Situação Inicial (Planejado)", expanded=True):
            st.markdown(evolucao.get("situacao_inicial", "Não informado"))
        
        # Evolução
        with st.expander("📈 Evolução (Realizado)", expanded=True):
            st.markdown(evolucao.get("evolucao", "Não informado"))
        
        # Próximos Passos
        with st.expander("🚀 Próximos Passos", expanded=False):
            st.markdown(evolucao.get("proximos_passos", "Não informado"))
        
        # Barra de progresso geral
        st.divider()
        st.subheader("📊 Progresso Geral")
        
        metas = {
            "auditores": {"atual": qtd_auditores, "meta": 5, "nome": "👥 Tamanho da Equipe"},
            "processos": {"atual": qtd_processos, "meta": 20, "nome": "📋 Processos Mapeados"},
            "checklists": {"atual": qtd_checklists, "meta": 100, "nome": "✅ Checklists Concluídos"},
            "auditorias": {"atual": qtd_auditorias, "meta": 12, "nome": "🎯 Auditorias Concluídas"}
        }
        
        for key, meta in metas.items():
            percentual = min(100, int((meta["atual"] / meta["meta"]) * 100)) if meta["meta"] > 0 else 0
            st.write(f"**{meta['nome']}** {meta['atual']}/{meta['meta']} ({percentual}%)")
            barra_progresso_personalizada(percentual)
        
        # Comparativo final
        st.divider()
        st.subheader("🎯 Comparativo Final")
        
        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            st.info("**Planejado**")
            st.markdown(evolucao.get("situacao_inicial", "Não informado")[:200] + "...")
        with col_comp2:
            st.success("**Realizado**")
            st.markdown(evolucao.get("evolucao", "Não informado")[:200] + "...")