"""
Funções de validação
"""
import streamlit as st

def validar_formulario():
    """Valida apenas os campos obrigatórios: nome do processo e executor"""
    
    if not st.session_state.get("input_processo", "").strip():
        st.error("O campo 'Nome do Processo' é obrigatório.")
        return False
    
    # Validação dos riscos
    if not st.session_state['riscos']:
        st.error("Adicione pelo menos um risco.")
        return False
    
    if not st.session_state.get("nome_0"):
        st.error("O Risco 1 precisa de uma descrição/nome")
        return False
    
    return True