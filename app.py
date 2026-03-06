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
    opcao = st.radio("Menu", ["Diagnóstico do Processo", "Geração de Relatórios"])

# --- 7. LÓGICA PRINCIPAL ---
if opcao == "Diagnóstico do Processo":
    st.title("Diagnóstico de Processos - FUSVE")
    st.markdown("""
    <div style='font-family: helvetica; color: #000000; font-size: 14px; line-height: 1.5;'>
        <p><strong>PASSO 1:</strong> PEDIR AO GESTOR PARA ESCREVER EM UM PAPEL O FLUXO DO PASSO A PASSO DO PROCESSO, INICIO AO FIM.</p>
        <p style='margin-top: 15px;'><strong>PASSO 2:</strong> ESCREVER ABAIXO OS PROCESSOS QUE FORAM SINALIZADOS NO FLUXO.</p>
    </div>
""", unsafe_allow_html=True)
    st.subheader("1. Dados do Processo")
    st.selectbox("Selecione a Área:", list(MAPPING_AREAS.keys()), key="area", on_change=lambda: st.session_state.update({'codigo_processo': ''}))
    st.text_input("Nome do Processo:", key="input_processo", on_change=processar_codigo_inteligente,
                  help="PROCESSOS OU ATIVIDADES REALIZADOS: São todas as atividades realizadas pela área. (Existem fluxos distintos dentro desse processo? Se sim é preciso criar um processo para cada fluxo).")
    st.text_input("Código do Processo:", key="codigo_processo", disabled=True)
    st.text_area("O que é o processo?:", key="input_descricao")
    st.text_area("Funcionário(s) Que Executa(m)", key="input_executor", help="Funcionário(s) que executa(m) - Alçadas (Gestão ou operação?)")
    st.text_area("Onde Começa o Proceso?:", key="input_etapa_ini", help="Onde começa o processo? (Ex: Do envio do relatório x pela área y) - ETAPA INICIAL")
    st.text_area("Qual (is) o Produto (s) Final Desse Processo?:", key="input_produto", help="Qual(is) o(s) produto(s) final(is) desse processo? (Ex: Relatório, Planilha, Sistema, Word, etc)")
    st.text_area("Depois de Acabado, para onde envia?", key="input_etapa_fim", help="Depois de acabado, para onde envia? (Ex: Área x, Arquivo físico localizado em y, Arquivo Digital localizado no z, etc.) - ETAPA FINAL")
    st.text_area("Qual o Objetivo do Processo? e Por que faz?", key="input_objetivo")
    
    st.markdown("""
    <div style='font-family: helvetica; color: #ff0000; font-size: 16px; line-height: 1;'>
        <p><strong>AVALIAÇÃO DA MAGNITUDE DO RISCO</strong></p>
        </div>
""", unsafe_allow_html=True)
    st.subheader("2. Riscos Associados")
    for i, _ in enumerate(st.session_state['riscos']):
        st.markdown(f"**Risco {i+1}**")
        st.text_input(f"Nome do Risco:", key=f"nome_{i}", help="1º Existem Incertezas ou Riscos do OBJETIVO DO PROCESSO não ser cumprido corretamente? 2º  Categorizar os Riscos identificados em: (RISCOS INERENTES ao processo, RISCO DE T.I E RISCO DE FRAUDE vunerabilidades de atos de irregularidades)")
        st.text_area(f"Fator de Risco:", key=f"fator_{i}", help="Fator de risco, causa ou motivo desse risco acontecer?")
        st.text_area(f"Ponto de Melhoria:", key=f"melhoria_{i}", help="O que mais te incomoda nesse processo e pensa que deveria ser melhor?")
        st.text_area(f"Apetite ao risco:", key=f"apetite_{i}", help="Dentro do critério e classificação do risco, quanto o Gestor entende ser o mínimo aceitável de ocorrência de risco, levando em consideração as combinações para chegar ao risco bruto.")
        col_i, col_p = st.columns(2)
        with col_i: st.selectbox(f"Impacto:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"imp_{i}", help="Impacto do risco materializado")
        with col_p: st.selectbox(f"Probabilidade:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"prob_{i}", help="Probabilidade do risco acontecer? Mediante isso, podemos criar os níveis que iremos classificar a probabilidade do risco acontecer.")
        
        score_v = MAPA_RISCO.get((st.session_state.get(f"imp_{i}"), st.session_state.get(f"prob_{i}")), 0)
        cor, emoji = get_estilo_risco(score_v)
        st.markdown(f'<div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white;">{emoji} Risco Bruto (Impacto + Probabilidade): {score_v}</div>', unsafe_allow_html=True)
        st.text_area(f"Motivo:", key=f"motivo_{i}", help="Qual o motivo da classificação do nivel da probabilidade? - ANÁLISE")
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
    
    if st.button("Atualizar Lista de Processos"):
        st.session_state['df_pendentes'] = buscar_processos_pendentes()
    
    if not st.session_state['df_pendentes'].empty:
        df = st.session_state['df_pendentes']
        st.dataframe(df)
        
        # O on_change limpa o 'pdf_pronto' toda vez que o usuário escolhe um processo novo
        codigo_selecionado = st.selectbox(
            "Selecione o Código do Processo:", 
            df['codigo_processo'].tolist(),
            on_change=lambda: st.session_state.pop('pdf_pronto', None)
        )

        if st.button("Gerar e Marcar como Pronto"):
            marcar_relatorio_gerado(codigo_selecionado)
            pdf_bytes = gerar_pdf_em_memoria(codigo_selecionado)
            
            if pdf_bytes:
                st.session_state['pdf_pronto'] = bytes(pdf_bytes)
                st.success(f"Processo {codigo_selecionado} concluído! Clique em baixar.")
                st.rerun() 
            else:
                st.error("Erro ao gerar PDF.")
        
        # Download button preenchido corretamente
        if 'pdf_pronto' in st.session_state:
            st.download_button(
                label="📥 Baixar Relatório em PDF",
                data=st.session_state['pdf_pronto'],
                file_name=f"relatorio_processo_{codigo_selecionado}.pdf",
                mime="application/pdf"
            )
    else:
        st.info("Nenhum processo pendente para gerar relatório.")