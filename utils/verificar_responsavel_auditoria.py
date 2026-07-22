def verificar_responsavel_auditoria(auditoria_id, usuario_nome):
    """Verifica se o usuário é responsável pela auditoria ou administrador"""
    from database import engine
    from sqlalchemy import text
    import json
    
    if not usuario_nome:
        return False
    
    try:
        with engine.connect() as conn:
            # ⭐ VERIFICAR SE É ADMIN
            query_admin = text("""
                SELECT perfil FROM usuarios WHERE nome = :usuario_nome
            """)
            result_admin = conn.execute(query_admin, {'usuario_nome': usuario_nome}).fetchone()
            
            if result_admin:
                perfil = result_admin[0]
                if perfil and perfil.lower() in ['administrador', 'admin']:
                    return True
            
            # ⭐ VERIFICAR SE É RESPONSÁVEL
            query = text("""
                SELECT responsavel_equipe FROM auditorias WHERE id = :auditoria_id
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            if not result:
                return False
            
            responsaveis_raw = result[0]
            
            if isinstance(responsaveis_raw, str):
                try:
                    responsaveis = json.loads(responsaveis_raw)
                except:
                    responsaveis = [r.strip() for r in responsaveis_raw.split(',') if r.strip()]
            elif isinstance(responsaveis_raw, list):
                responsaveis = responsaveis_raw
            else:
                responsaveis = []
            
            usuario_normalizado = usuario_nome.strip().upper()
            for resp in responsaveis:
                if resp.strip().upper() == usuario_normalizado:
                    return True
            
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar permissão: {e}")
        return False
    
def verificar_administrador(usuario_nome):
    """Verifica se o usuário é administrador"""
    from database import engine
    from sqlalchemy import text
    
    if not usuario_nome:
        return False
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT perfil FROM usuarios WHERE nome = :usuario_nome
            """)
            result = conn.execute(query, {'usuario_nome': usuario_nome}).fetchone()
            
            if result:
                perfil = result[0]
                return perfil and perfil.lower() in ['administrador', 'admin']
            return False
    except:
        return False