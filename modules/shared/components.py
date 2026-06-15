"""
Componentes visuais reutilizáveis
"""
# ===== MIGRAÇÃO PARA FLASK =====
# Streamlit removido - sistema agora usa Flask
# import streamlit as st  # REMOVIDO

# Placeholder para evitar erros (as funções Streamlit não serão chamadas no Flask)
class _DummyStreamlit:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

st = _DummyStreamlit()
import pandas as pd
from logic import get_estilo_risco

def formatar_risco_para_card(valor):
    """Formata o valor do risco para exibição no card"""
    if pd.isna(valor) or valor is None or valor <= 0:
        return "#6c757d", "⚪", "N/A"
    else:
        cor, emoji = get_estilo_risco(valor)
        return cor, emoji, str(int(valor))