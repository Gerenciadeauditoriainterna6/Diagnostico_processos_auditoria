import streamlit as st
import os
import pandas as pd
from sqlalchemy import text
from database import engine
from logic import (
    MAPPING_AREAS, MAPA_RISCO, processar_codigo_inteligente, 
    get_estilo_risco, salvar_no_banco, gerar_pdf_em_memoria, buscar_processos_pendentes
)

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Diagnóstico FUSVE", layout="centered")

# --- 2. INICIALIZAÇÃO DE ESTADO ---
if 'riscos' not in st.session_state: st.session_state['riscos'] = []
if 'deve_limpar' not in st.session_state: st.session_state['deve_limpar'] = False
if 'df_pendentes' not in st.session_state: st.session_state['df_pendentes'] = pd.DataFrame()

# --- 3. LIMPEZA PÓS-SALVO ---
if st.session_state['deve_limpar']:
    campos_to_reset = ["input_processo", "input_objetivo", "input_executor", "input_descricao", "input_etapa_ini", "input_etapa_fim", "input_produto", "codigo_processo", "area"]
    for campo in campos_to_reset:
        st.session_state[campo] = None if campo == "area" else ""
    st.session_state['riscos'] = []
    st.session_state['deve_limpar'] = False
    st.rerun()

# --- 4. FUNÇÕES DE SUPORTE ---
def validar_formulario():
    campos = ["input_processo", "input_objetivo", "input_executor", "input_descricao", "input_etapa_ini", "input_etapa_fim", "input_produto", "codigo_processo"]
    for c in campos:
        if not st.session_state.get(c):
            st.error(f"O campo '{c.replace('input_', '').replace('_', ' ').capitalize()}' é obrigatório.")
            return False
    if not st.session_state['riscos']:
        st.error("Adicione pelo menos um risco.")
        return False
    return True

def marcar_relatorio_gerado(codigo_processo):
    """Atualiza o status para 'Sim' na tabela de riscos, filtrando pelo código na tabela pai."""
    query = text("""
        UPDATE riscos 
        SET relatorio_gerado = 'Sim' 
        WHERE processo_id IN (
            SELECT id FROM processos WHERE codigo_processo = :codigo
        )
    """)
    with engine.begin() as conn:
        conn.execute(query, {"codigo": codigo_processo})

# --- 5. CONFIGURAÇÃO DE ATIVOS ---
caminho_script = os.path.dirname(os.path.abspath(__file__))
logo_fusve = os.path.join(caminho_script, "assets", "logo_fusve.png")

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists(logo_fusve): st.image(logo_fusve, width=200)
    opcao = st.radio("Menu", ["Cadastro de Processos", "Geração de Relatórios"])

# --- 7. LÓGICA PRINCIPAL ---
if opcao == "Cadastro de Processos":
    st.title("Diagnóstico de Processos - FUSVE")
    st.subheader("1. Dados do Processo")
    st.selectbox("Selecione a Área:", list(MAPPING_AREAS.keys()), key="area", on_change=lambda: st.session_state.update({'codigo_processo': ''}))
    st.text_input("Nome do Processo:", key="input_processo", on_change=processar_codigo_inteligente)
    st.text_input("Código do Processo:", key="codigo_processo", disabled=True)
    st.text_area("Objetivo:", key="input_objetivo")
    st.text_area("Quem Executa?", key="input_executor")
    st.text_area("Descrição:", key="input_descricao")
    st.text_area("Etapa Inicial:", key="input_etapa_ini")
    st.text_area("Etapa Final:", key="input_etapa_fim")
    st.text_area("Produto:", key="input_produto")

    st.subheader("2. Riscos Associados")
    for i, _ in enumerate(st.session_state['riscos']):
        st.markdown(f"**Risco {i+1}**")
        st.text_input(f"Nome do Risco:", key=f"nome_{i}")
        st.text_area(f"Fator de Risco:", key=f"fator_{i}")
        st.text_area(f"Melhoria:", key=f"melhoria_{i}")
        st.text_area(f"Apetite ao risco:", key=f"apetite_{i}")
        col_i, col_p = st.columns(2)
        with col_i: st.selectbox(f"Impacto:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"imp_{i}")
        with col_p: st.selectbox(f"Probabilidade:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"prob_{i}")
        
        score_v = MAPA_RISCO.get((st.session_state.get(f"imp_{i}"), st.session_state.get(f"prob_{i}")), 0)
        cor, emoji = get_estilo_risco(score_v)
        st.markdown(f'<div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white;">{emoji} Score Atual: {score_v}</div>', unsafe_allow_html=True)
        st.text_area(f"Motivo:", key=f"motivo_{i}")
        st.markdown("---")

    col_add, col_save = st.columns(2)
    if col_add.button("➕ Adicionar Risco"):
        st.session_state['riscos'].append({})
        st.rerun()
    if col_save.button("💾 Salvar Todos os Dados", type="primary"):
        if validar_formulario() and salvar_no_banco():
            st.success("Dados salvos!")
            st.session_state['deve_limpar'] = True
            st.rerun()

elif opcao == "Geração de Relatórios":
    st.title("Relatórios - FUSVE")
    
    # 1. Atualizar lista
    if st.button("Atualizar Lista de Processos"):
        st.session_state['df_pendentes'] = buscar_processos_pendentes()
    
    # 2. Seleção
    if not st.session_state['df_pendentes'].empty:
        df = st.session_state['df_pendentes']
        st.dataframe(df)
        
        # Seleciona pelo Código (assumindo que sua query retorna 'codigo_processo')
        codigo_selecionado = st.selectbox("Selecione o Código do Processo:", df['codigo_processo'].tolist())

        # 3. Botão para preparar o PDF
        if st.button("Gerar e Marcar como Pronto"):
            # Marca no banco
            marcar_relatorio_gerado(codigo_selecionado)
            
            # Gera o PDF
            pdf_bytes = gerar_pdf_em_memoria(codigo_selecionado)
            
            if pdf_bytes:
                st.session_state['pdf_pronto'] = bytes(pdf_bytes)
                st.success(f"Relatório do processo {codigo_selecionado} pronto para download!")
            else:
                st.error("Erro ao gerar PDF.")
        
        # 4. Botão de Download (só aparece se o PDF estiver pronto na memória)
        if 'pdf_pronto' in st.session_state:
            st.download_button(
                label="📥 Baixar Relatório",
                data=st.session_state['pdf_pronto'],
                file_name=f"relatorio_processo_{codigo_selecionado}.pdf",
                mime="application/pdf"
            )
    else:
        st.info("Nenhum processo na lista. Clique em 'Atualizar'.")