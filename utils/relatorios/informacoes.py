from utils.formatters import formatar_telefone

def buscar_responsaveis_auditoria(auditoria_id):
    """
    Busca os responsáveis pela auditoria na tabela auditorias
    Retorna uma lista de nomes
    """
    from database import engine
    from sqlalchemy import text
    
    if not auditoria_id:
        return []
    
    with engine.connect() as conn:
        query = text("""
            SELECT responsavel_equipe
            FROM auditorias
            WHERE id = :auditoria_id
        """)
        result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
        
        if result and result[0]:
            # responsavel_equipe é um array text[] no PostgreSQL
            return result[0]  # Já retorna como lista
        return []

def buscar_dados_gerencia_auditoria():
    """
    Busca os dados da Gerência de Auditoria Interna na tabela informacoes_area
    Retorna o email e telefone da GAI
    """
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT email, telefone 
                FROM informacoes_area 
                WHERE nome_area ILIKE '%Auditoria Interna%' 
                   OR nome_area ILIKE '%GAI%'
                   OR id_area = 99 
                LIMIT 1
            """)
            result = conn.execute(query).fetchone()
            
            if result:
                telefone = result[1] or '(21) 99999-9999'
                # ⭐ APLICAR FORMATAÇÃO
                telefone_formatado = formatar_telefone(telefone)
                return {
                    'email': result[0] or 'auditoria@fusve.com.br',
                    'telefone': telefone_formatado
                }
            else:
                return {
                    'email': 'auditoria@fusve.com.br',
                    'telefone': '(21) 99999-9999'
                }
    except Exception as e:
        print(f"⚠️ Erro ao buscar dados da GAI: {e}")
        return {
            'email': 'auditoria@fusve.com.br',
            'telefone': '(21) 99999-9999'
        }