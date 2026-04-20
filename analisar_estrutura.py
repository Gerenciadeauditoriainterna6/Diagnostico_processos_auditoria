import json
from database import engine
from sqlalchemy import text
import pandas as pd

def extrair_estrutura_completa():
    """Extrai estrutura completa do banco de dados"""
    
    with engine.connect() as conn:
        # Buscar TODAS as tabelas
        tabelas = pd.read_sql("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """, conn)
        
        print(f"📋 Encontradas {len(tabelas)} tabelas:")
        for t in tabelas['table_name']:
            print(f"   - {t}")
        
        estrutura = {}
        
        for tabela in tabelas['table_name']:
            print(f"\n📊 Analisando: {tabela}...")
            
            # Colunas
            colunas = pd.read_sql(f"""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = '{tabela}'
                ORDER BY ordinal_position
            """, conn)
            
            # Chaves estrangeiras
            fks = pd.read_sql(f"""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = '{tabela}'
            """, conn)
            
            # Chaves primárias
            pks = pd.read_sql(f"""
                SELECT
                    kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_name = '{tabela}'
            """, conn)
            
            # Contagem de registros
            try:
                total = pd.read_sql(f"SELECT COUNT(*) as total FROM {tabela}", conn)['total'][0]
            except:
                total = 0
            
            estrutura[tabela] = {
                'colunas': colunas.to_dict('records'),
                'primary_keys': pks['column_name'].tolist() if not pks.empty else [],
                'foreign_keys': fks.to_dict('records') if not fks.empty else [],
                'total_registros': total
            }
        
        return estrutura

# Executar
print("🚀 Iniciando análise do banco de dados...")
print("=" * 50)

estrutura = extrair_estrutura_completa()

# Salvar como JSON completo
with open('estrutura_banco_completa.json', 'w', encoding='utf-8') as f:
    json.dump(estrutura, f, indent=2, ensure_ascii=False, default=str)

print("\n" + "=" * 50)
print(f"✅ Estrutura salva em 'estrutura_banco_completa.json'")
print(f"📁 Arquivo criado em: {__file__}")