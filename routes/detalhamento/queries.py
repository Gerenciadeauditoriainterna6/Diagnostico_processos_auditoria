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