# supabase_client.py
from supabase import create_client
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

class SupabaseClient:
    """
    Cliente Supabase em padrão Singleton.
    Garante que apenas UMA conexão seja criada e reutilizada.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Retorna a instância única do cliente Supabase.
        Se não existir, cria uma nova.
        """
        if cls._instance is None:
            print("🔧 Inicializando cliente Supabase (Singleton)...")
            
            # Pega as credenciais do ambiente
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            # Fallback para outros nomes de chave
            if not supabase_key:
                supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            if not supabase_key:
                supabase_key = os.getenv('SUPABASE_KEY')
            if not supabase_key:
                supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            # Valida se as credenciais existem
            if not supabase_url or not supabase_key:
                raise Exception("❌ Credenciais do Supabase não configuradas!")
            
            # Cria a única instância
            cls._instance = create_client(supabase_url, supabase_key)
            print("✅ Cliente Supabase inicializado com sucesso!")
        
        return cls._instance