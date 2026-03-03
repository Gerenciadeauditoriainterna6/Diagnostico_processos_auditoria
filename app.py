import streamlit as st
import os
from logic import (
    MAPPING_AREAS, MAPA_RISCO, processar_codigo_inteligente, 
    get_estilo_risco, salvar_no_banco
)

# --- 1. CONFIGURAÇÃO INICIAL (DEVE SER A PRIMEIRA CHAMADA) ---
st.set_page_config(page_title="Diagnóstico FUSVE", layout="centered")

# --- 2. INICIALIZAÇÃO DE ESTADO ---
if 'riscos' not in st.session_state: st.session_state['riscos'] = []
if 'deve_limpar' not in st.session_state: st.session_state['deve_limpar'] = False

# --- 3. LIMPEZA PÓS-SALVO ---
# Roda antes da UI para garantir que os campos sejam resetados antes de desenhar
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
    for i in range(len(st.session_state['riscos'])):
        for campo in ["nome", "fator", "melhoria", "apetite", "motivo"]:
            if not st.session_state.get(f"{campo}_{i}"):
                st.error(f"Preencha todos os campos do Risco {i+1}.")
                return False
    return True

# --- 5. CONFIGURAÇÃO DE ATIVOS ---
caminho_script = os.path.dirname(os.path.abspath(__file__))
logo_fusve = os.path.join(caminho_script, "assets", "logo_fusve.png")
logo_auditoria = os.path.join(caminho_script, "assets", "logo_auditoria.png")

# --- 6. SIDEBAR (NAVEGAÇÃO) ---
with st.sidebar:
    if os.path.exists(logo_fusve): st.image(logo_fusve, width=200)
    opcao = st.radio("Menu", ["Cadastro de Processos", "Geração de Relatórios"])

# --- 7. LÓGICA DE NAVEGAÇÃO PRINCIPAL ---
if opcao == "Cadastro de Processos":
    st.title("Diagnóstico de Processos - FUSVE")
    
    # Seção 1: Dados do Processo
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

    st.divider()

    # Seção 2: Riscos
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
        
        imp_v = st.session_state.get(f"imp_{i}", "Baixo")
        prob_v = st.session_state.get(f"prob_{i}", "Baixo")
        score_v = MAPA_RISCO.get((imp_v, prob_v), 0)
        cor, emoji = get_estilo_risco(score_v)
        st.markdown(f'<div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white;">{emoji} Score Atual: {score_v}</div>', unsafe_allow_html=True)
        
        st.text_area(f"Motivo:", key=f"motivo_{i}")
        st.markdown("---")

    col_add, col_save = st.columns(2)
    with col_add:
        if st.button("➕ Adicionar Novo Risco", use_container_width=True):
            st.session_state['riscos'].append({})
            st.rerun()
    with col_save:
        if st.button("💾 Salvar Todos os Dados", type="primary", use_container_width=True):
            if validar_formulario():
                if salvar_no_banco():
                    st.success("Dados salvos com sucesso!")
                    st.session_state['deve_limpar'] = True
                    st.rerun()

elif opcao == "Geração de Relatórios":
    st.title("Relatórios e Consultas - FUSVE")
    if os.path.exists(logo_auditoria):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2: st.image(logo_auditoria, width=300)
        
    st.subheader("Gerador de Relatórios")
    st.write("Aqui você poderá consultar os processos e gerar o PDF.")
    
    if st.button("Consultar Processos Pendentes"):
        # Aqui entra a chamada da função que criaremos no logic.py
        st.info("Funcionalidade em desenvolvimento.")