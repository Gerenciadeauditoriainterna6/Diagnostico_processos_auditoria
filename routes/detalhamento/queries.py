# routes/detalhamento/queries.py
from database import engine
from sqlalchemy import text

def buscar_auditoria_id_do_processo(processo_id):
    """Busca o auditoria_id de um processo"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT auditoria_id FROM processos WHERE id = :pid"),
            {'pid': processo_id}
        ).fetchone()
        return result[0] if result else None


def buscar_codigo_processo(processo_id):
    """Busca o código de um processo"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT codigo_processo FROM processos WHERE id = :pid"),
            {'pid': processo_id}
        ).fetchone()
        return result[0] if result else None


def buscar_proximo_numero_etapa(processo_id):
    """Busca o próximo número sequencial de etapa para um processo"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT MAX(CAST(SUBSTRING(codigo_etapa FROM '[^.]+$') AS INTEGER))
            FROM etapas_processo
            WHERE processo_id = :pid
        """), {'pid': processo_id}).fetchone()
        return (result[0] or 0) + 1


def atualizar_etapa(etapa_id, params):
    """Atualiza uma etapa existente"""

    # ⭐ Garantir valores padrão
    if 'criticidade_etapa' not in params or not params['criticidade_etapa']:
        params['criticidade_etapa'] = 'EM APROVAÇÃO'
    if 'analise_critica' not in params or params['analise_critica'] is None:
        params['analise_critica'] = ''
    if 'sugestao_melhoria' not in params or params['sugestao_melhoria'] is None:
        params['sugestao_melhoria'] = ''
    if 'necessidade_implantacao' not in params or params['necessidade_implantacao'] is None:
        params['necessidade_implantacao'] = ''
    if 'ganho_previsto' not in params or params['ganho_previsto'] is None:
        params['ganho_previsto'] = ''

    base_fields = """
        nome_etapa = :nome_etapa,
        descricao_etapa = :descricao_etapa,
        como_e_feito = :como_e_feito,
        objetivo_etapa = :objetivo_etapa,
        status_etapa = :status_etapa,
        criticidade_etapa = :criticidade_etapa,
        politica_interna = :politica_interna,
        analise_critica = :analise_critica,
        sugestao_melhoria = :sugestao_melhoria,
        necessidade_implantacao = :necessidade_implantacao,
        ganho_previsto = :ganho_previsto,
        obrigacoes_regulatorias = :obrigacoes_regulatorias,
        executores_etapa = :executores_etapa,
        manual_em_andamento = :manual_em_andamento
    """
    
    if params.get('auditoria_id'):
        base_fields += ", auditoria_id = :auditoria_id"
    
    update_fields = []
    
    if params.get('atualizar_diagrama'):
        update_fields.extend([
            "diagrama_bpmn = :diagrama_bpmn",
            "diagrama_nome = :diagrama_nome",
            "diagrama_tipo = :diagrama_tipo"
        ])
    
    if params.get('atualizar_manual'):
        update_fields.extend([
            "manual_nome = :manual_nome",
            "manual_url = :manual_url"
        ])
    
    if params.get('atualizar_mapeamento'):
        update_fields.extend([
            "arquivo_mapeamento = :arquivo_mapeamento",
            "arquivo_mapeamento_nome = :arquivo_mapeamento_nome",
            "arquivo_mapeamento_tipo = :arquivo_mapeamento_tipo"
        ])
    
    if update_fields:
        query_sql = f"UPDATE etapas_processo SET {base_fields}, {', '.join(update_fields)}, updated_at = NOW() WHERE id = :etapa_id"
    else:
        query_sql = f"UPDATE etapas_processo SET {base_fields}, updated_at = NOW() WHERE id = :etapa_id"
    
    with engine.connect() as conn:
        conn.execute(text(query_sql), params)
        conn.commit()


def inserir_etapa(params):
    """Insere uma nova etapa e retorna o ID"""

    # ⭐ Garantir valores padrão para campos que podem vir vazios
    defaults = {
        'criticidade_etapa': 'EM APROVAÇÃO',
        'analise_critica': '',
        'sugestao_melhoria': '',
        'necessidade_implantacao': '',
        'ganho_previsto': '',
        'politica_interna': '',
        'descricao_etapa': '',
        'como_e_feito': '',
        'objetivo_etapa': '',
        'executores_etapa': '',
        'obrigacoes_regulatorias': '[]',
        'diagrama_bpmn': None,
        'diagrama_nome': None,
        'diagrama_tipo': None,
        'manual_nome': None,
        'manual_url': None,
        'arquivo_mapeamento': None,
        'arquivo_mapeamento_nome': None,
        'arquivo_mapeamento_tipo': None,
    }
    
    for key, value in defaults.items():
        if key not in params or params[key] is None:
            params[key] = value

    query = text("""
        INSERT INTO etapas_processo (
            processo_id, auditoria_id, codigo_etapa, nome_etapa,
            descricao_etapa, como_e_feito, objetivo_etapa,
            status_etapa, criticidade_etapa,
            politica_interna, analise_critica, sugestao_melhoria,
            necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
            executores_etapa,
            diagrama_bpmn, diagrama_nome, diagrama_tipo,
            manual_nome, manual_url,
            arquivo_mapeamento, arquivo_mapeamento_nome, arquivo_mapeamento_tipo,
            manual_em_andamento, created_at
        ) VALUES (
            :processo_id, :auditoria_id, :codigo_etapa, :nome_etapa,
            :descricao_etapa, :como_e_feito, :objetivo_etapa,
            :status_etapa, :criticidade_etapa,
            :politica_interna, :analise_critica, :sugestao_melhoria,
            :necessidade_implantacao, :ganho_previsto, :obrigacoes_regulatorias,
            :executores_etapa,
            :diagrama_bpmn, :diagrama_nome, :diagrama_tipo,
            :manual_nome, :manual_url,
            :arquivo_mapeamento, :arquivo_mapeamento_nome, :arquivo_mapeamento_tipo,
            :manual_em_andamento, NOW()
        )
        RETURNING id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, params)
        conn.commit()
        return result.fetchone()[0]

def buscar_arquivo_etapa(etapa_id, tipo):
    """Busca arquivo de uma etapa para download"""
    with engine.connect() as conn:
        if tipo == 'manual':
            result = conn.execute(text(
                "SELECT manual_url, manual_nome FROM etapas_processo WHERE id = :eid"
            ), {'eid': etapa_id}).fetchone()
            if result:
                return {'url': result[0], 'nome': result[1]}
                
        elif tipo == 'diagrama':
            result = conn.execute(text(
                "SELECT diagrama_bpmn, diagrama_nome FROM etapas_processo WHERE id = :eid"
            ), {'eid': etapa_id}).fetchone()
            if result:
                return {'bytes': result[0], 'nome': result[1]}
                
        elif tipo == 'mapeamento':
            result = conn.execute(text(
                "SELECT arquivo_mapeamento, arquivo_mapeamento_nome FROM etapas_processo WHERE id = :eid"
            ), {'eid': etapa_id}).fetchone()
            if result:
                return {'bytes': result[0], 'nome': result[1]}
    
    return None

# ============================================================
# QUERIES DE ETAPAS
# ============================================================

def buscar_etapa_por_id(etapa_id):
    """Busca uma etapa pelo ID"""
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, processo_id, codigo_etapa, nome_etapa, descricao_etapa,
                   como_e_feito, objetivo_etapa, status_etapa, criticidade_etapa,
                   politica_interna, analise_critica, sugestao_melhoria,
                   necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                   executores_etapa,
                   diagrama_bpmn, diagrama_nome, diagrama_tipo,
                   manual_nome, manual_url,
                   arquivo_mapeamento, arquivo_mapeamento_nome, arquivo_mapeamento_tipo,
                   manual_em_andamento
            FROM etapas_processo WHERE id = :eid
        """), {'eid': etapa_id}).fetchone()
        
        if not result:
            return None
        
        return {
            'id': result[0], 'processo_id': result[1], 'codigo_etapa': result[2] or '',
            'nome_etapa': result[3] or '', 'descricao_etapa': result[4] or '',
            'como_e_feito': result[5] or '', 'objetivo_etapa': result[6] or '',
            'status_etapa': result[7] or 'Ativa', 'criticidade_etapa': result[8] or '',
            'politica_interna': result[9] or '', 'analise_critica': result[10] or '',
            'sugestao_melhoria': result[11] or '', 'necessidade_implantacao': result[12] or '',
            'ganho_previsto': result[13] or '', 'obrigacoes_regulatorias': result[14] or '',
            'executores_etapa': result[15] or '',
            'diagrama_nome': result[17] or '', 'diagrama_tipo': result[18] or '',
            'manual_nome': result[19] or '', 'manual_url': result[20] or '',
            'arquivo_mapeamento_nome': result[22] or '', 'arquivo_mapeamento_tipo': result[23] or '',
            'manual_em_andamento': bool(result[24]) if len(result) > 24 else False
        }


def excluir_etapa(etapa_id):
    """Exclui uma etapa"""
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM etapas_processo WHERE id = :eid"), {'eid': etapa_id})
        conn.commit()


def gerar_codigo_etapa(processo_id):
    """Gera o próximo código de etapa"""
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT UPPER(codigo_processo) FROM processos WHERE id = :pid"), {'pid': processo_id}).fetchone()
        if not result:
            return None
        
        codigo_processo = result[0]
        result = conn.execute(text("""
            SELECT MAX(CAST(COALESCE(REGEXP_REPLACE(codigo_etapa, '^.*\\.', ''), '0') AS INTEGER))
            FROM etapas_processo WHERE processo_id = :pid
        """), {'pid': processo_id}).fetchone()
        
        ultimo = result[0] if result[0] else 0
        return f"{codigo_processo}.{ultimo + 1}"


def buscar_manual_etapa(etapa_id):
    """Busca URL e nome do manual da etapa"""
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT manual_url, manual_nome FROM etapas_processo WHERE id = :eid
        """), {'eid': etapa_id}).fetchone()
        if result:
            return {'url': result[0], 'nome': result[1]}
    return None


def remover_manual_etapa(etapa_id):
    """Remove o manual da etapa (limpa URL e nome)"""
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE etapas_processo SET manual_url = NULL, manual_nome = NULL,
            manual_em_andamento = FALSE, updated_at = NOW() WHERE id = :eid
        """), {'eid': etapa_id})
        conn.commit()