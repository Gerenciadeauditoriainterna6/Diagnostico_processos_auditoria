# database.py - Versão para Flask + Render
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (apenas em desenvolvimento)
load_dotenv()

def get_db_engine():
    # Tenta pegar a DATABASE_URL das variáveis de ambiente
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        raise Exception("❌ DATABASE_URL não encontrada! Verifique seu arquivo .env")
    
    # Configuração SSL para o Supabase
    if 'supabase' in db_url:
        if '?' not in db_url:
            db_url = db_url + '?sslmode=require'
        else:
            db_url = db_url + '&sslmode=require'
    
    # Cria a engine de conexão
    engine = create_engine(
        db_url,
        pool_pre_ping=True,  # Mantém conexão ativa
        pool_recycle=3600     # Reconecta a cada hora
    )
    
    return engine

# Cria a engine global
engine = get_db_engine()