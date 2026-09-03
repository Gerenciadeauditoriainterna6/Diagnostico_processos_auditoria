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
    
    # ⭐ Garantir campos de política interna
    if 'politica_interna_url' not in params or params['politica_interna_url'] is None:
        params['politica_interna_url'] = ''
    if 'politica_interna_nome' not in params or params['politica_interna_nome'] is None:
        params['politica_interna_nome'] = ''

    base_fields = """
        nome_etapa = :nome_etapa,
        descricao_etapa = :descricao_etapa,
        como_e_feito = :como_e_feito,
        objetivo_etapa = :objetivo_etapa,
        status_etapa = :status_etapa,
        criticidade_etapa = :criticidade_etapa,
        politica_interna = :politica_interna,
        politica_interna_url = :politica_interna_url,
        politica_interna_nome = :politica_interna_nome,
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
        # ⭐ NOVO: Campos de política interna
        'politica_interna_url': '',
        'politica_interna_nome': '',
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
            politica_interna, politica_interna_url, politica_interna_nome,
            analise_critica, sugestao_melhoria,
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
            :politica_interna, :politica_interna_url, :politica_interna_nome,
            :analise_critica, :sugestao_melhoria,
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
                   politica_interna, politica_interna_url, politica_interna_nome,
                   analise_critica, sugestao_melhoria,
                   necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                   executores_etapa,
                   diagrama_bpmn, diagrama_nome, diagrama_tipo,
                   manual_nome, manual_url,
                   arquivo_mapeamento, arquivo_mapeamento_nome, arquivo_mapeamento_tipo,
                   manual_em_andamento
            FROM etapas_processo WHERE id = :eid
        """), {'eid': etapa_id}).mappings().fetchone()
        
        if not result:
            return None
        
        # ⭐ Usar row mapping (acesso por nome, não por índice)
        return {
            'id': result['id'],
            'processo_id': result['processo_id'],
            'codigo_etapa': result['codigo_etapa'] or '',
            'nome_etapa': result['nome_etapa'] or '',
            'descricao_etapa': result['descricao_etapa'] or '',
            'como_e_feito': result['como_e_feito'] or '',
            'objetivo_etapa': result['objetivo_etapa'] or '',
            'status_etapa': result['status_etapa'] or 'Ativa',
            'criticidade_etapa': result['criticidade_etapa'] or '',
            'politica_interna': result['politica_interna'] or '',
            'politica_interna_url': result['politica_interna_url'] or '',
            'politica_interna_nome': result['politica_interna_nome'] or '',
            'analise_critica': result['analise_critica'] or '',
            'sugestao_melhoria': result['sugestao_melhoria'] or '',
            'necessidade_implantacao': result['necessidade_implantacao'] or '',
            'ganho_previsto': result['ganho_previsto'] or '',
            'obrigacoes_regulatorias': result['obrigacoes_regulatorias'] or '',
            'executores_etapa': result['executores_etapa'] or '',
            'diagrama_nome': result['diagrama_nome'] or '',
            'diagrama_tipo': result['diagrama_tipo'] or '',
            'manual_nome': result['manual_nome'] or '',
            'manual_url': result['manual_url'] or '',
            'arquivo_mapeamento_nome': result['arquivo_mapeamento_nome'] or '',
            'arquivo_mapeamento_tipo': result['arquivo_mapeamento_tipo'] or '',
            'manual_em_andamento': bool(result['manual_em_andamento']) if result['manual_em_andamento'] is not None else False
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

def inserir_risco_etapa(dados):
    """Insere um novo risco de etapa"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        INSERT INTO riscos_etapa (
            etapa_id, auditoria_id, nome_risco, categoria,
            fator_risco, consequencia, impacto, probabilidade,
            magnitude, impacto_aceitavel,
            probabilidade_aceitavel, tratamento, origem, causas,
            desc_tratamento, financeiro, info_adicional, 
            motivo_classificacao, prazo_implantacao, descricao_prazo, 
            ativo, created_at
        ) VALUES (
            :etapa_id, :auditoria_id, :nome_risco, :categoria,
            :fator_risco, :consequencia, :impacto, :probabilidade,
            :magnitude, :impacto_aceitavel, :probabilidade_aceitavel, 
            :tratamento, :origem, :causas,
            :desc_tratamento, :financeiro, :info_adicional,
            :motivo_classificacao, :prazo_implantacao, :descricao_prazo,
            :ativo, NOW()
        )
        RETURNING id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, dados)
        novo_id = result.fetchone()[0]
        conn.commit()
        return novo_id


def atualizar_risco_etapa(risco_id, dados):
    """Atualiza um risco de etapa existente"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        UPDATE riscos_etapa
        SET nome_risco = :nome_risco,
            categoria = :categoria,
            fator_risco = :fator_risco,
            consequencia = :consequencia,
            impacto = :impacto,
            probabilidade = :probabilidade,
            magnitude = :magnitude,
            impacto_aceitavel = :impacto_aceitavel,
            probabilidade_aceitavel = :probabilidade_aceitavel,
            tratamento = :tratamento,
            origem = :origem,
            desc_tratamento = :desc_tratamento,
            financeiro = :financeiro,
            info_adicional = :info_adicional,
            motivo_classificacao = :motivo_classificacao,
            prazo_implantacao = :prazo_implantacao,
            descricao_prazo = :descricao_prazo,
            causas = :causas,
            ativo = :ativo,
            updated_at = NOW()
        WHERE id = :risco_id
    """)
    
    dados['risco_id'] = risco_id
    
    with engine.connect() as conn:
        conn.execute(query, dados)
        conn.commit()
        return risco_id

# routes/detalhamento/queries.py

# ⭐ Adicione no final do arquivo:

def buscar_risco_etapa_por_id(risco_id):
    """Busca um risco de etapa específico pelo ID"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT id, etapa_id, nome_risco, categoria, fator_risco,
               consequencia, impacto, probabilidade, magnitude,
               impacto_aceitavel, probabilidade_aceitavel, tratamento, 
               origem, desc_tratamento, motivo_classificacao, financeiro,
               info_adicional, ativo, causas, prazo_implantacao, descricao_prazo
        FROM riscos_etapa
        WHERE id = :risco_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'risco_id': risco_id}).mappings().fetchone()
        
        if not result:
            return None
        
        return {
            'id': result['id'],
            'etapa_id': result['etapa_id'],
            'nome_risco': result['nome_risco'] or '',
            'categoria': result['categoria'] or '',
            'fator_risco': result['fator_risco'] or '',
            'consequencia': result['consequencia'] or '',
            'impacto': result['impacto'] or 'Médio',
            'probabilidade': result['probabilidade'] or 'Médio',
            'magnitude': result['magnitude'] or 0,
            'impacto_aceitavel': result['impacto_aceitavel'] or 'Médio',
            'probabilidade_aceitavel': result['probabilidade_aceitavel'] or 'Médio',
            'tratamento': result['tratamento'] or '',
            'origem': result['origem'] or '',
            'desc_tratamento': result['desc_tratamento'] or '',
            'motivo_classificacao': result['motivo_classificacao'] or '',
            'financeiro': result['financeiro'] or False,
            'info_adicional': result['info_adicional'] or '',
            'ativo': result['ativo'] if result['ativo'] is not None else True,
            'causas': [c.strip() for c in result['causas'].split(',')] if result['causas'] else [],
            'prazo_implantacao': result['prazo_implantacao'] or '',
            'descricao_prazo': result['descricao_prazo'] or '',
        }


def alternar_status_risco_etapa(risco_id, ativo):
    """Alterna o status (ativo/inativo) de um risco de etapa"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        UPDATE riscos_etapa 
        SET ativo = :ativo, updated_at = NOW()
        WHERE id = :risco_id
        RETURNING id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {
            'ativo': ativo,
            'risco_id': risco_id
        })
        
        if result.rowcount == 0:
            return False
        
        conn.commit()
        return True


def buscar_riscos_etapa(etapa_id, apenas_ativos=True):
    """
    Busca riscos de uma etapa
    
    Args:
        etapa_id: ID da etapa
        apenas_ativos: Se True, retorna apenas riscos ativos. Se False, retorna todos.
    """
    from database import engine
    from sqlalchemy import text
    
    if apenas_ativos:
        query = text("""
            SELECT id, nome_risco, categoria, fator_risco, consequencia,
                   impacto, probabilidade, magnitude, impacto_aceitavel, 
                   probabilidade_aceitavel, tratamento,
                   origem, desc_tratamento, motivo_classificacao, 
                   financeiro, info_adicional, ativo, causas, prazo_implantacao
            FROM riscos_etapa
            WHERE etapa_id = :etapa_id AND (ativo IS NULL OR ativo = true)
            ORDER BY id
        """)
    else:
        query = text("""
            SELECT id, nome_risco, categoria, fator_risco, consequencia,
                   impacto, probabilidade, magnitude, impacto_aceitavel, 
                   probabilidade_aceitavel, tratamento,
                   origem, desc_tratamento, motivo_classificacao, 
                   financeiro, info_adicional, ativo, causas, prazo_implantacao
            FROM riscos_etapa
            WHERE etapa_id = :etapa_id
            ORDER BY id
        """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'etapa_id': etapa_id}).fetchall()
        
        riscos = []
        for row in result:
            riscos.append({
                'id': row[0],
                'nome_risco': row[1] or '',
                'categoria': row[2] or '',
                'fator_risco': row[3] or '',
                'consequencia': row[4] or '',
                'impacto': row[5] or 'Médio',
                'probabilidade': row[6] or 'Médio',
                'magnitude': row[7] or 0,
                'impacto_aceitavel': row[8] or 'Médio',
                'probabilidade_aceitavel': row[9] or 'Médio',
                'tratamento': row[10] or '',
                'origem': row[11] or '',
                'desc_tratamento': row[12] or '',
                'motivo_classificacao': row[13] or '',
                'financeiro': row[14] or False,
                'info_adicional': row[15] or '',
                'ativo': row[16] if row[16] is not None else True,
                'causas': [c.strip() for c in row[17].split(',')] if row[17] else [],
                'prazo_implantacao': row[18] or ''
            })
        
        return riscos


def contar_riscos_etapa(etapa_id, apenas_ativos=True):
    """Conta o número de riscos de uma etapa"""
    from database import engine
    from sqlalchemy import text
    
    if apenas_ativos:
        query = text("""
            SELECT COUNT(*) 
            FROM riscos_etapa 
            WHERE etapa_id = :etapa_id 
            AND (ativo IS NULL OR ativo = true)
        """)
    else:
        query = text("""
            SELECT COUNT(*) 
            FROM riscos_etapa 
            WHERE etapa_id = :etapa_id
        """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
        return result[0] if result[0] else 0


def excluir_risco_etapa(risco_id):
    """Exclui um risco de etapa"""
    from database import engine
    from sqlalchemy import text
    
    query = text("DELETE FROM riscos_etapa WHERE id = :risco_id")
    
    with engine.connect() as conn:
        result = conn.execute(query, {'risco_id': risco_id})
        conn.commit()
        return result.rowcount > 0


def inserir_risco_etapa(dados):
    """Insere um novo risco de etapa"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        INSERT INTO riscos_etapa (
            etapa_id, auditoria_id, nome_risco, categoria,
            fator_risco, consequencia, impacto, probabilidade,
            magnitude, impacto_aceitavel,
            probabilidade_aceitavel, tratamento, origem, causas,
            desc_tratamento, financeiro, info_adicional, 
            motivo_classificacao, prazo_implantacao, descricao_prazo, 
            ativo, created_at
        ) VALUES (
            :etapa_id, :auditoria_id, :nome_risco, :categoria,
            :fator_risco, :consequencia, :impacto, :probabilidade,
            :magnitude, :impacto_aceitavel, :probabilidade_aceitavel, 
            :tratamento, :origem, :causas,
            :desc_tratamento, :financeiro, :info_adicional,
            :motivo_classificacao, :prazo_implantacao, :descricao_prazo,
            :ativo, NOW()
        )
        RETURNING id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, dados)
        novo_id = result.fetchone()[0]
        conn.commit()
        return novo_id


def atualizar_risco_etapa(risco_id, dados):
    """Atualiza um risco de etapa existente"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        UPDATE riscos_etapa
        SET nome_risco = :nome_risco,
            categoria = :categoria,
            fator_risco = :fator_risco,
            consequencia = :consequencia,
            impacto = :impacto,
            probabilidade = :probabilidade,
            magnitude = :magnitude,
            impacto_aceitavel = :impacto_aceitavel,
            probabilidade_aceitavel = :probabilidade_aceitavel,
            tratamento = :tratamento,
            origem = :origem,
            desc_tratamento = :desc_tratamento,
            financeiro = :financeiro,
            info_adicional = :info_adicional,
            motivo_classificacao = :motivo_classificacao,
            prazo_implantacao = :prazo_implantacao,
            descricao_prazo = :descricao_prazo,
            causas = :causas,
            ativo = :ativo,
            updated_at = NOW()
        WHERE id = :risco_id
    """)
    
    dados['risco_id'] = risco_id
    
    with engine.connect() as conn:
        conn.execute(query, dados)
        conn.commit()
        return risco_id

def buscar_riscos_processo_vinculados(etapa_id):
    """Busca os IDs dos riscos do processo vinculados à etapa"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT riscos_processo_ids 
        FROM etapas_processo 
        WHERE id = :etapa_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
        if result and result[0]:
            return [x.strip() for x in result[0].split(',') if x.strip()]
        return []


def buscar_riscos_processo_por_ids(lista_ids):
    """Busca os dados dos riscos do processo pelos IDs"""
    from database import engine
    from sqlalchemy import text
    
    if not lista_ids:
        return []
    
    query = text("""
        SELECT 
            id,
            nome_risco,
            fator_risco,
            melhoria,
            impacto,
            probabilidade,
            apetite_impacto,
            motivo_risco,
            validacao_gerencia,
            validacao_superintendencia,
            score_risco,
            categoria,
            causas,
            tratamento_risco,
            descricao_tratamento,
            prazo_implantacao,
            apetite_probabilidade
        FROM riscos
        WHERE id IN :ids
        ORDER BY id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'ids': tuple(lista_ids)}).mappings().fetchall()
        return [dict(r) for r in result]


def vincular_risco_processo(etapa_id, risco_id):
    """Vincula um risco do processo à etapa"""
    from database import engine
    from sqlalchemy import text
    
    # Buscar IDs atuais
    ids_atuais = buscar_riscos_processo_vinculados(etapa_id)
    
    # Adicionar novo ID se não existir
    if str(risco_id) not in ids_atuais:
        ids_atuais.append(str(risco_id))
    
    novo_valor = ', '.join(ids_atuais)
    
    query = text("""
        UPDATE etapas_processo 
        SET riscos_processo_ids = :ids
        WHERE id = :etapa_id
    """)
    
    with engine.connect() as conn:
        conn.execute(query, {'ids': novo_valor, 'etapa_id': etapa_id})
        conn.commit()
        return True

def desvincular_risco_processo(etapa_id, risco_id):
    """Desvincula um risco do processo da etapa"""
    from database import engine
    from sqlalchemy import text
    
    ids_atuais = buscar_riscos_processo_vinculados(etapa_id)
    
    # Remover o ID
    ids_atuais = [x for x in ids_atuais if x != str(risco_id)]
    
    novo_valor = ', '.join(ids_atuais) if ids_atuais else None
    
    query = text("""
        UPDATE etapas_processo 
        SET riscos_processo_ids = :ids
        WHERE id = :etapa_id
    """)
    
    with engine.connect() as conn:
        conn.execute(query, {'ids': novo_valor, 'etapa_id': etapa_id})
        conn.commit()
        return True


def buscar_riscos_processo_disponiveis(processo_id):
    """Busca riscos do processo disponíveis para vincular"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT id, nome_risco, categoria, impacto, probabilidade
        FROM riscos
        WHERE processo_id = :processo_id
        ORDER BY id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'processo_id': processo_id}).mappings().fetchall()
        return [dict(r) for r in result]



def salvar_controle_etapa(data):
    """Salva um controle de etapa (insert ou update)"""
    from database import engine
    from sqlalchemy import text
    
    controle_id = data.get('id')
    risco_id = data.get('risco_id')
    auditoria_id = data.get('auditoria_id')
    
    nome_controle = data.get('nome_controle', '')
    como_executado = data.get('como_executado', '')
    objetivo_controle = data.get('objetivo_controle', '')
    periodicidade_execucao = data.get('periodicidade_execucao', '')
    natureza = data.get('natureza', '')
    forma_execucao = data.get('forma_execucao', '')
    status_controle = data.get('status_controle', '')
    evidencia_realizacao = data.get('evidencia_realizacao', '')
    responsaveis_tratamento = data.get('responsaveis_tratamento', '')
    risco_avaliacao = data.get('risco_avaliacao', '')
    causa_motivo = data.get('causa_motivo', '')
    frequencia_evidencia = data.get('frequencia_evidencia', '')
    local_evidencia = data.get('local_evidencia', '')
    lgpd = data.get('lgpd', '')
    
    # ⭐ NOVOS CAMPOS
    apetite_impacto = data.get('apetite_impacto', '')
    apetite_probabilidade = data.get('apetite_probabilidade', '')
    tratamento_risco = data.get('tratamento_risco', '')
    descricao_tratamento = data.get('descricao_tratamento', '')
    prazo_implantacao = data.get('prazo_implantacao', '')
    
    try:
        with engine.connect() as conn:
            if controle_id:
                query = text("""
                    UPDATE controles_etapa
                    SET nome_controle = :nome_controle,
                        como_executado = :como_executado,
                        objetivo_controle = :objetivo_controle,
                        periodicidade_execucao = :periodicidade_execucao,
                        natureza = :natureza,
                        forma_execucao = :forma_execucao,
                        status_controle = :status_controle,
                        evidencia_realizacao = :evidencia_realizacao,
                        local_evidencia = :local_evidencia,
                        lgpd = :lgpd,
                        responsaveis_tratamento = :responsaveis_tratamento,
                        risco_avaliacao = :risco_avaliacao,
                        causa_motivo = :causa_motivo,
                        frequencia_evidencia = :frequencia_evidencia,
                        apetite_impacto = :apetite_impacto,
                        apetite_probabilidade = :apetite_probabilidade,
                        tratamento_risco = :tratamento_risco,
                        descricao_tratamento = :descricao_tratamento,
                        prazo_implantacao = :prazo_implantacao,
                        updated_at = CURRENT_DATE
                    WHERE id = :controle_id
                """)
                
                conn.execute(query, {
                    'controle_id': controle_id,
                    'nome_controle': nome_controle,
                    'como_executado': como_executado,
                    'objetivo_controle': objetivo_controle,
                    'periodicidade_execucao': periodicidade_execucao,
                    'natureza': natureza,
                    'forma_execucao': forma_execucao,
                    'status_controle': status_controle,
                    'evidencia_realizacao': evidencia_realizacao,
                    'local_evidencia': local_evidencia,
                    'lgpd': lgpd,
                    'responsaveis_tratamento': responsaveis_tratamento,
                    'risco_avaliacao': risco_avaliacao,
                    'causa_motivo': causa_motivo,
                    'frequencia_evidencia': frequencia_evidencia,
                    'apetite_impacto': apetite_impacto,
                    'apetite_probabilidade': apetite_probabilidade,
                    'tratamento_risco': tratamento_risco,
                    'descricao_tratamento': descricao_tratamento,
                    'prazo_implantacao': prazo_implantacao
                })

                conn.commit()
                
                return {'success': True, 'message': 'Controle atualizado', 'controle_id': controle_id}
                
            else:
                query = text("""
                    INSERT INTO controles_etapa (
                        risco_id, auditoria_id, nome_controle,
                        como_executado, objetivo_controle,
                        periodicidade_execucao, natureza, forma_execucao,
                        status_controle, evidencia_realizacao,
                        responsaveis_tratamento, risco_avaliacao, causa_motivo,
                        local_evidencia, lgpd,
                        frequencia_evidencia,
                        apetite_impacto, apetite_probabilidade,
                        tratamento_risco, descricao_tratamento, prazo_implantacao,
                        created_at, updated_at
                    ) VALUES (
                        :risco_id, :auditoria_id, :nome_controle,
                        :como_executado, :objetivo_controle,
                        :periodicidade_execucao, :natureza, :forma_execucao,
                        :status_controle, :evidencia_realizacao,
                        :responsaveis_tratamento, :risco_avaliacao, :causa_motivo,
                        :local_evidencia, :lgpd,
                        :frequencia_evidencia,
                        :apetite_impacto, :apetite_probabilidade,
                        :tratamento_risco, :descricao_tratamento, :prazo_implantacao,
                        CURRENT_TIMESTAMP, CURRENT_DATE
                    )
                    RETURNING id
                """)
                
                result = conn.execute(query, {
                    'risco_id': risco_id,
                    'auditoria_id': auditoria_id,
                    'nome_controle': nome_controle,
                    'como_executado': como_executado,
                    'objetivo_controle': objetivo_controle,
                    'periodicidade_execucao': periodicidade_execucao,
                    'natureza': natureza,
                    'forma_execucao': forma_execucao,
                    'status_controle': status_controle,
                    'evidencia_realizacao': evidencia_realizacao,
                    'responsaveis_tratamento': responsaveis_tratamento,
                    'risco_avaliacao': risco_avaliacao,
                    'causa_motivo': causa_motivo,
                    'local_evidencia': local_evidencia,
                    'lgpd': lgpd,
                    'frequencia_evidencia': frequencia_evidencia,
                    'apetite_impacto': apetite_impacto,
                    'apetite_probabilidade': apetite_probabilidade,
                    'tratamento_risco': tratamento_risco,
                    'descricao_tratamento': descricao_tratamento,
                    'prazo_implantacao': prazo_implantacao
                })
                
                novo_id = result.fetchone()[0]
                conn.commit()
                return {'success': True, 'message': 'Controle criado', 'controle_id': novo_id}
                
    except Exception as e:
        print(f"❌ Erro ao salvar controle: {e}")
        return {'success': False, 'error': str(e)}

def buscar_controle_etapa_por_id(controle_id):
    """Busca um controle de etapa pelo ID"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT id, risco_id, nome_controle, como_executado, objetivo_controle,
               periodicidade_execucao, natureza, forma_execucao, status_controle,
               evidencia_realizacao, responsaveis_tratamento, risco_avaliacao, causa_motivo,
               frequencia_evidencia, local_evidencia, lgpd,
               apetite_impacto, apetite_probabilidade,
               tratamento_risco, descricao_tratamento, prazo_implantacao
        FROM controles_etapa
        WHERE id = :controle_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'controle_id': controle_id}).fetchone()
        
        if not result:
            return None
        
        return {
            'id': result[0],
            'risco_id': result[1],
            'nome_controle': result[2] or '',
            'como_executado': result[3] or '',
            'objetivo_controle': result[4] or '',
            'periodicidade_execucao': result[5] or '',
            'natureza': result[6] or '',
            'forma_execucao': result[7] or '',
            'status_controle': result[8] or '',
            'evidencia_realizacao': result[9] or '',
            'responsaveis_tratamento': result[10] or '',
            'risco_avaliacao': result[11] or '',
            'causa_motivo': result[12] or '',
            'frequencia_evidencia': result[13] or '',
            'local_evidencia': result[14] or '',
            'lgpd': result[15] or '',
            'apetite_impacto': result[16] or '',
            'apetite_probabilidade': result[17] or '',
            'tratamento_risco': result[18] or '',
            'descricao_tratamento': result[19] or '',
            'prazo_implantacao': result[20] or ''
        }

def buscar_risco_etapa_basico(risco_id):
    """Busca impacto e probabilidade de um risco da etapa"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT impacto, probabilidade
        FROM riscos_etapa
        WHERE id = :risco_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'risco_id': risco_id}).fetchone()
        
        if not result:
            return None
        
        return {
            'impacto': result[0] or '',
            'probabilidade': result[1] or ''
        }