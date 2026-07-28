# utils/__init__.py
"""
Utilitários gerais do sistema
"""

from .storage_utils import (
    # Funções genéricas de storage
    upload_arquivo_storage,
    baixar_arquivo_storage,
    excluir_arquivo_storage,
    obter_url_assinada,
    extrair_caminho_da_url,
)

__all__ = [
    # Storage
    'upload_arquivo_storage',
    'baixar_arquivo_storage',
    'excluir_arquivo_storage',
    'obter_url_assinada',
    'extrair_caminho_da_url',
]