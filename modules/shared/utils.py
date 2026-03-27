"""
Funções utilitárias compartilhadas
"""
import streamlit as st


def exibir_criterios_risco():
    """Exibe os critérios de Probabilidade e Impacto em um expander"""
    with st.expander("📋 **Critérios para Avaliação de Riscos**", expanded=False):
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.markdown("""
            ### 📊 **PROBABILIDADE**
            
            | Nível | Descrição |
            |-------|-----------|
            | **Baixa** | Pode ser que ocorra uma vez dentro de um ano. |
            | **Média** | Pode ser que ocorra mais de uma vez dentro de um ano. |
            | **Alta** | Pode ser que ocorra mensalmente. |
            | **Muito Alta** | Pode ser que ocorra diariamente. |
            """)
        
        with col_c2:
            st.markdown("""
            ### 💰 **IMPACTO**
            
            | Nível | Descrição |
            |-------|-----------|
            | **Baixo** | Desembolsos de até R$ 15.000,00. |
            | **Médio** | Desembolsos de R$ 15.000,00 até R$ 55.000,00. |
            | **Alto** | Desembolso de R$ 55.000,00 até R$ 100.000,00. |
            | **Muito Alto** | Desembolso acima de R$ 100.000,00. |
            """)

def limpar_campos_por_prefixo(prefixo):
    for key in st.session_state.keys():
        if key.startswith(prefixo):
            st.session_state[key] = ""

def limpar_todos_campos():
    """Limpa todos os campos da tela de diagnóstico - usa reset de formulário"""
    st.session_state['deve_limpar_diagnostico'] = True