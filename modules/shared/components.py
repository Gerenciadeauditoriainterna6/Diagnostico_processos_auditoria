"""
Componentes visuais reutilizáveis
"""
import streamlit as st
import pandas as pd
from logic import get_estilo_risco

def formatar_risco_para_card(valor):
    """Formata o valor do risco para exibição no card"""
    if pd.isna(valor) or valor is None or valor <= 0:
        return "#6c757d", "⚪", "N/A"
    else:
        cor, emoji = get_estilo_risco(valor)
        return cor, emoji, str(int(valor))

def criar_container(titulo=None, tipo="padrao"):
    """Cria um container estilizado
    
    Args:
        titulo (str): Título do container
        tipo (str): "padrao", "primary", "danger"

    Uso:
        with criar_container("Dados do Processo"):
            st.text_input(...)
    """
    class Container:
        def __enter__(self):
            classe = "custom-container"
            if tipo == "primary":
                classe = "custom-container-primary"
            elif tipo == "danger":
                classe = "custom-container-danger"
            
            st.markdown(f'<div class="{classe}">', unsafe_allow_html=True)

            if titulo:
                title_class = "custom-container-title"
                if tipo == "danger":
                    title_class += " custom-container-title-danger"
                st.markdown(f'<div class="{title_class}">{titulo}</div>', unsafe_allow_html=True)
                return self
        
        def __exit__(self, *args):
            st.markdown('</div>', unsafe_allow_html=True)
        
    return Container()

def criar_card(titulo, conteudo_func):
    """
    cria um card com título e conteúdo.

    Args:
        titulo (str): Título do card
        conteudo_func (callable): Função que contém os elementos do card
    """
    with criar_container(titulo):
        conteudo_func()