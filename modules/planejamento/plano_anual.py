"""
Módulo do Plano Anual de Auditoria
"""
import streamlit as st
import os
import json
from datetime import datetime
import time as time_module
from streamlit_pdf_viewer import pdf_viewer
from database import engine
from sqlalchemy import text

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def carregar_evolucao(ano=2026):
    """Carrega o texto de evolução salvo (JSON)"""
    arquivo = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "comunicacaoresultados",
        f"evolucao_auditoria_{ano}.json"
    )
    
    # Texto padrão
    padrao = {
        "situacao_inicial": "Nenhuma informação cadastrada.",
        "evolucao": "Nenhuma informação cadastrada.",
        "proximos_passos": "Nenhuma informação cadastrada."
    }
    
    # Se o arquivo não existe, retorna padrão
    if not os.path.exists(arquivo):
        return padrao
    
    # Tentar ler o arquivo
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
        # Verificar se os campos essenciais existem
        if not isinstance(dados, dict):
            return padrao
        
        # Garantir que todos os campos existem
        resultado = {}
        for campo in ["situacao_inicial", "evolucao", "proximos_passos"]:
            resultado[campo] = dados.get(campo, padrao.get(campo, "Não informado"))
        
        return resultado
        
    except Exception as e:
        print(f"Erro ao carregar evolução: {e}")
        return padrao

def salvar_evolucao(dados, ano=2026):
    """Salva o texto de evolução em JSON"""
    arquivo = f"evolucao_auditoria_{ano}.json"
    with open(arquivo, 'w', econding='utf-8') as f:
        json.dumps(dados, f, ensure_ascii=False, indent=2)
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
        AND status = 'Concluido'
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

# ============================================
# TELA PRINCIPAL
# ============================================


def tela_plano_anual():
    """Exibe o Plano Anual de Auditoria em PDF e a evolução"""
    
    st.markdown("""
        <style>
            .block-container {
                max-width: 95% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            
            /* Remove qualquer padding lateral que possa estar limitando */
            .stApp {
                padding: 0 !important;
            }
            
            /* Força o PDF a ocupar toda a largura */
            iframe, .stElement, .stMarkdown {
                width: 100% !important;
            }
            
            /* Container do PDF */
            .stElement iframe {
                width: 100% !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Tabs para organizar o conteúdo
    tab1, tab2 = st.tabs([
        "📄 Plano Anual", 
        "📈 Evolução da Auditoria"
    ])

    # ========== TAB 1: PLANO ANUAL ==========
    with tab1:

        st.title("📊 Plano Anual de Auditoria - 2026")
        st.write("Visualize abaixo as diretrizes e o cronograma para o ano atual.")

        # Caminho para o arquivo PDF (ajustado para funcionar a partir do módulo)
        caminho_pdf = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "plano_auditoria_2026.pdf")

        if os.path.exists(caminho_pdf):
            try:
                pdf_viewer(caminho_pdf, height=900)
            except Exception as e:
                st.error(f"Erro ao carregar o visualizador: {e}")
            
            st.divider()
            
            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label="📥 Baixar Plano Anual (PDF)",
                    data=f,
                    file_name="Plano_Auditoria_2026.pdf",
                    mime="application/pdf",
                    use_container_width=False
                )
        else:
            st.warning("⚠️ Arquivo não encontrado na pasta assets.")
            st.write(f"Caminho procurado: {caminho_pdf}")
    
    # ========== TAB 2: EVOLUÇÃO DA AUDITORIA ==========
    with tab2:
        st.title("📈 Evolução da Auditoria - 2026")
        
        # Botão de edição no canto superior direito
        col_header, col_btn = st.columns([4, 1])
        with col_header:
            st.subheader("📊 Métricas de Execução")
        with col_btn:
            modo_edicao = st.button("✏️ Editar Evolução", key="btn_editar_evolucao", use_container_width=True)
        
        # Verificar se está em modo edição
        if 'modo_edicao_evolucao' not in st.session_state:
            st.session_state.modo_edicao_evolucao = False
        
        if modo_edicao:
            st.session_state.modo_edicao_evolucao = not st.session_state.modo_edicao_evolucao
            st.rerun()
        
        # Métricas automáticas (sempre visíveis)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            qtd_auditores = contar_auditores()
            st.metric("👥 Auditores", qtd_auditores, delta=None)
        
        with col2:
            qtd_processos = contar_processos_ano(2026)
            st.metric("📋 Processos Mapeados", qtd_processos, delta=None)
        
        with col3:
            qtd_checklists = contar_checklists_realizados(2026)
            st.metric("✅ Checklists Concluídas", qtd_checklists, delta=None)
        
        with col4:
            qtd_auditorias = contar_auditorias_realizadas(2026)
            st.metric("🎯 Auditorias Concluídas", qtd_auditorias, delta=None)
        
        st.divider()
        
        # ========== MODO EDIÇÃO ==========
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
            
            st.divider()
            
            # Exibir último salvamento
            if os.path.exists(f"evolucao_auditoria_2026.json"):
                with open(f"evolucao_auditoria_2026.json", 'r', encoding='utf-8') as f:
                    dados_salvos = json.load(f)
                    if "data_atualizacao" in dados_salvos:
                        st.caption(f"🕐 Última atualização: {dados_salvos['data_atualizacao']}")
        
        # ========== MODO VISUALIZAÇÃO ==========
        else:
            evolucao = carregar_evolucao(2026)
            
            # Situação Inicial
            with st.expander("📌 Situação Inicial (Planejado)", expanded=True):
                situacao = evolucao.get("situacao_inicial", "Não informado")
                if isinstance(situacao, list):
                    situacao = "\n".join(situacao)
                st.markdown(situacao)

            # Evolução
            with st.expander("📈 Evolução (Realizado)", expanded=True):
                evolucao_texto = evolucao.get("evolucao", "Não informado")
                if isinstance(evolucao_texto, list):
                    evolucao_texto = "\n".join(evolucao_texto)
                st.markdown(evolucao_texto)

            # Próximos Passos
            with st.expander("🚀 Próximos Passos", expanded=False):
                proximos = evolucao.get("proximos_passos", "Não informado")
                if isinstance(proximos, list):
                    proximos = "\n".join(proximos)
                st.markdown(proximos)
            
            # Barra de progresso geral
            st.divider()
            st.subheader("📊 Progresso Geral")
            
            # Calcular progresso baseado nas métricas
            metas = {
                "auditores": {"atual": qtd_auditores, "meta": 5, "nome": "Equipe"},
                "processos": {"atual": qtd_processos, "meta": 20, "nome": "Processos"},
                "checklists": {"atual": qtd_checklists, "meta": 50, "nome": "Checklists"},
                "auditorias": {"atual": qtd_auditorias, "meta": 4, "nome": "Auditorias"}
            }
            
            for key, meta in metas.items():
                percentual = min(100, int((meta["atual"] / meta["meta"]) * 100)) if meta["meta"] > 0 else 0
                st.write(f"**{meta['nome']}:** {meta['atual']}/{meta['meta']} ({percentual}%)")
                st.progress(percentual / 100)
            
            # Comparativo final
            st.divider()
            st.subheader("🎯 Comparativo Final")
            
            col_comp1, col_comp2 = st.columns(2)
            with col_comp1:
                st.info("**Planejado**")
                situacao = evolucao.get("situacao_inicial", "Não informado")
                if isinstance(situacao, list):
                    situacao = "\n".join(situacao)
                st.markdown(situacao[:300] + "..." if len(situacao) > 300 else situacao)

            with col_comp2:
                st.success("**Realizado**")
                evolucao_texto = evolucao.get("evolucao", "Não informado")
                if isinstance(evolucao_texto, list):
                    evolucao_texto = "\n".join(evolucao_texto)
                st.markdown(evolucao_texto[:300] + "..." if len(evolucao_texto) > 300 else evolucao_texto)