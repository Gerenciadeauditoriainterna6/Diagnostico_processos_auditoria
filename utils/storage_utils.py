# utils/storage_utils.py
"""
Utilitários genéricos para operações no Supabase Storage
Todas as funções são independentes de bucket ou estrutura de pastas
"""

import base64
import uuid
import os
from datetime import datetime
from urllib.parse import urlparse, unquote

def upload_arquivo_storage(arquivo, caminho_destino, bucket_name, content_type=None):
    """
    Função genérica para upload de qualquer arquivo no storage
    
    Args:
        arquivo: File object, bytes ou caminho do arquivo
        caminho_destino: Caminho completo no storage (ex: "pasta/subpasta/arquivo.pdf")
        bucket_name: Nome do bucket
        content_type: Tipo MIME (opcional)
    
    Returns:
        str: URL assinada do arquivo ou None
    """
    if not arquivo:
        return None
    
    try:
        # Ler o arquivo
        if hasattr(arquivo, 'read'):
            file_bytes = arquivo.read()
        elif isinstance(arquivo, bytes):
            file_bytes = arquivo
        else:
            with open(arquivo, 'rb') as f:
                file_bytes = f.read()
        
        # Detectar content-type se não fornecido
        if not content_type:
            if caminho_destino.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif caminho_destino.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                content_type = 'image/png'
            elif caminho_destino.lower().endswith(('.doc', '.docx')):
                content_type = 'application/msword'
            else:
                content_type = 'application/octet-stream'
        
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        print(f"📎 Upload: bucket={bucket_name}, path={caminho_destino}")
        
        # Fazer upload
        response = supabase.storage.from_(bucket_name).upload(
            caminho_destino,
            file_bytes,
            file_options={"content-type": content_type}
        )
        
        if response:
            # Gerar URL assinada (válida por 1 ano)
            signed_url = supabase.storage.from_(bucket_name).create_signed_url(
                caminho_destino, 31536000
            )
            
            if signed_url and signed_url.get('signedURL'):
                print(f"✅ Upload concluído: {signed_url['signedURL']}")
                return signed_url['signedURL']
        
        return None
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return None


def baixar_arquivo_storage(caminho, bucket_name):
    """
    Função genérica para baixar qualquer arquivo do storage
    
    Args:
        caminho: Caminho completo no storage
        bucket_name: Nome do bucket
    
    Returns:
        bytes: Conteúdo do arquivo ou None
    """
    try:
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        print(f"📎 Download: bucket={bucket_name}, path={caminho}")
        
        response = supabase.storage.from_(bucket_name).download(caminho)
        return response
        
    except Exception as e:
        print(f"❌ Erro no download: {e}")
        import traceback
        traceback.print_exc()
        return None


def excluir_arquivo_storage(caminho, bucket_name):
    """
    Função genérica para excluir qualquer arquivo do storage
    
    Args:
        caminho: Caminho completo no storage
        bucket_name: Nome do bucket
    
    Returns:
        bool: True se excluído com sucesso
    """
    try:
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        print(f"📎 Excluindo: bucket={bucket_name}, path={caminho}")
        
        response = supabase.storage.from_(bucket_name).remove([caminho])
        
        print(f"✅ Arquivo excluído: {caminho}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao excluir: {e}")
        import traceback
        traceback.print_exc()
        return False


def obter_url_assinada(caminho, bucket_name, expires_in=31536000):
    """
    Função genérica para obter URL assinada de qualquer arquivo
    
    Args:
        caminho: Caminho completo no storage
        bucket_name: Nome do bucket
        expires_in: Tempo de expiração em segundos (padrão: 1 ano)
    
    Returns:
        str: URL assinada ou None
    """
    try:
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        signed_url = supabase.storage.from_(bucket_name).create_signed_url(
            caminho, expires_in
        )
        
        if signed_url and signed_url.get('signedURL'):
            return signed_url['signedURL']
        
        # Fallback: URL pública
        public_url = supabase.storage.from_(bucket_name).get_public_url(caminho)
        return public_url
        
    except Exception as e:
        print(f"❌ Erro ao gerar URL assinada: {e}")
        return None


def extrair_caminho_da_url(arquivo_url):
    """
    Extrai o caminho e o bucket de qualquer URL do Supabase Storage
    
    Args:
        arquivo_url: URL completa do arquivo
    
    Returns:
        tuple: (caminho, bucket) ou (None, None)
    """
    if not arquivo_url:
        return None, None
    
    try:
        parsed_url = urlparse(arquivo_url)
        path = unquote(parsed_url.path)
        
        # Detectar bucket na URL
        bucket = None
        caminho = None
        
        # Padrões de URL do Supabase
        padroes = [
            r'/storage/v1/object/public/([^/]+)/(.*)',
            r'/storage/v1/object/signed/([^/]+)/(.*)',
            r'/storage/v1/object/authenticated/([^/]+)/(.*)',
            r'/object/public/([^/]+)/(.*)',
            r'/object/signed/([^/]+)/(.*)',
            r'/object/authenticated/([^/]+)/(.*)',
        ]
        
        import re
        for padrao in padroes:
            match = re.search(padrao, path)
            if match:
                bucket = match.group(1)
                caminho = match.group(2)
                break
        
        if caminho:
            # Remover parâmetros de consulta
            caminho = caminho.split('?')[0]
            # Remover barras no início
            if caminho.startswith('/'):
                caminho = caminho[1:]
        
        return caminho, bucket
        
    except Exception as e:
        print(f"❌ Erro ao extrair caminho da URL: {e}")
        return None, None