# routes/diagnostico/queries.py
# RESPONSABILIDADE: Apenas funções de banco de dados (SQL)

from database import engine
from sqlalchemy import text


def buscar_auditorias_por_area(area_id):
    """Busca todas as auditorias de uma área"""
    query = text("""
        SELECT id, codigo_auditoria, titulo, trimestre, ano, status, unidade, emergencial
        FROM auditorias
        WHERE id_area = :area_id
        ORDER BY ano DESC, trimestre DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"area_id": area_id})
        return [dict(row._mapping) for row in result]


def buscar_processos_por_area(area_id, auditoria_id=None):
    """Busca processos de uma área (opcionalmente filtra por auditoria)"""
    from database import engine
    from sqlalchemy import text
    
    if auditoria_id:
        query = text("""
            SELECT 
                p.id, 
                p.codigo_processo, 
                p.nome_processo, 
                p.objetivo,
                p.auditoria_id, 
                a.codigo_auditoria,
                COALESCE(MAX(r.score_risco), 0) as score_maximo,
                COUNT(r.id) as qtd_riscos
            FROM processos p
            LEFT JOIN auditorias a ON p.auditoria_id = a.id
            LEFT JOIN riscos r ON p.id = r.processo_id
            WHERE p.id_area = :area_id 
                AND p.status = 'Ativo'
                AND p.auditoria_id = :auditoria_id
            GROUP BY p.id, p.codigo_processo, p.nome_processo, p.objetivo, p.auditoria_id, a.codigo_auditoria
            ORDER BY CAST(SPLIT_PART(p.codigo_processo, '.', 2) AS INTEGER)
        """)
        params = {"area_id": area_id, "auditoria_id": auditoria_id}
    else:
        query = text("""
            SELECT 
                p.id, 
                p.codigo_processo, 
                p.nome_processo, 
                p.objetivo,
                p.auditoria_id, 
                a.codigo_auditoria,
                COALESCE(MAX(r.score_risco), 0) as score_maximo,
                COUNT(r.id) as qtd_riscos
            FROM processos p
            LEFT JOIN auditorias a ON p.auditoria_id = a.id
            LEFT JOIN riscos r ON p.id = r.processo_id
            WHERE p.id_area = :area_id 
                AND p.status = 'Ativo'
            GROUP BY p.id, p.codigo_processo, p.nome_processo, p.objetivo, p.auditoria_id, a.codigo_auditoria
            ORDER BY CAST(SPLIT_PART(p.codigo_processo, '.', 2) AS INTEGER)
        """)
        params = {"area_id": area_id}
    
    with engine.connect() as conn:
        result = conn.execute(query, params).fetchall()
        
        
        processos = []
        for row in result:
            score = row[6] or 0

            # Define cor e texto baseado no score
            if score == 0:
                texto_score = ''
                cor_score = ''
            elif score <= 3:
                texto_score = 'score-baixo'
                cor_score = '🟢'
            elif score <= 7:
                texto_score = 'score-medio'
                cor_score = '🟡'
            elif score <= 11:
                texto_score = 'score-alto'
                cor_score = '🟠'
            else:
                texto_score = 'score-critico'
                cor_score = '🔴'

            processos.append({
                'id': row[0],
                'codigo_processo': row[1] or '',
                'nome_processo': row[2] or '',
                'objetivo': row[3] or '',
                'auditoria_id': row[4],
                'codigo_auditoria': row[5] or f'Auditoria {row[4]}' if row[4] else '-',
                'score_maximo': score,
                'qtd_riscos': row[7] or 0,
                'texto_score': texto_score,
                'cor_score': cor_score
            })
        
        return processos

def buscar_score_maximo_e_qtd_riscos_por_processo(processo_id):
    """Retorna o score máximo e quantidade de riscos de um processo"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT 
            COUNT(id) as qtd_riscos,
            COALESCE(MAX(score_risco), 0) as score_maximo
        FROM riscos
        WHERE processo_id = :processo_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'processo_id': processo_id}).fetchone()
        
        if result:
            return {
                'qtd_riscos': result[0] or 0,
                'score_maximo': result[1] or 0
            }
        return {'qtd_riscos': 0, 'score_maximo': 0}


def buscar_riscos_por_processo(processo_id):
    """Retorna os riscos de um processo"""
    query = text("""
        SELECT 
            id, nome_risco, fator_risco, melhoria,
            impacto, probabilidade, motivo_risco,
            categoria, causas,
            tratamento_risco, descricao_tratamento, prazo_implantacao,
            score_risco, apetite_impacto, apetite_probabilidade
        FROM riscos
        WHERE processo_id = :processo_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'processo_id': processo_id}).fetchall()
        
        riscos = []
        for row in result:
            categorias_str = row[7] or ''
            causas_str = row[8] or ''
            
            categorias = [c.strip() for c in categorias_str.split(',') if c.strip()]
            causas_list = [c.strip() for c in causas_str.split(',') if c.strip()]
            prazo = row[11] if row[11] else ''
            
            risco = {
                'id': row[0],
                'nome_risco': row[1] or '',
                'fator_risco': row[2] or '',
                'melhoria': row[3] or '',
                'impacto': row[4] or 'Médio',
                'probabilidade': row[5] or 'Médio',
                'motivo_risco': row[6] or '',
                'categorias': categorias,
                'categoria_causa': causas_list,
                'score_risco': row[12] or 0,
                'como_tratar': row[9] or '',
                'desc_tratamento': row[10] or '',
                'prazo_implantacao': prazo,
                'apetite_impacto': row[13] or 'Médio',
                'apetite_probabilidade': row[14] or 'Médio'
            }
            riscos.append(risco)
        
        return riscos

def buscar_funcionarios_por_area(area_id):
    """Retorna funcionários de uma área"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT id, nome_funcionario, cargo
        FROM funcionarios_area
        WHERE id_area = :area_id AND ativo = true
        ORDER BY nome_funcionario
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'area_id': area_id})
        return [{'id': row[0], 'nome': row[1], 'cargo': row[2] or ''} for row in result]

def buscar_ultimo_sequencial(area_id):
    """Retorna o último número sequencial de uma área"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT COALESCE(
            MAX(CAST(SPLIT_PART(codigo_processo, '.', 2) AS INTEGER)), 
            0
        ) as ultimo
        FROM processos 
        WHERE id_area = :area_id 
          AND codigo_processo ~ '^[0-9]+\\.[0-9]+$'
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'area_id': area_id}).fetchone()
        return result[0] if result else 0

def salvar_processo_basico(nome_processo, codigo_processo, area_id, auditoria_id, entrevistado):
    """Salva um processo básico e retorna o ID"""
    from database import engine
    from sqlalchemy import text
    
    nome_upper = nome_processo.strip().upper()
    
    with engine.connect() as conn:
        # Buscar nome da área
        busca_area = text("SELECT UPPER(nome_area) FROM informacoes_area WHERE id_area = :id_area")
        result_area = conn.execute(busca_area, {'id_area': area_id}).fetchone()
        nome_area = result_area[0] if result_area else ''
        
        # Verificar se já existe
        check_query = text("""
            SELECT id, codigo_processo FROM processos 
            WHERE UPPER(nome_processo) = UPPER(:nome) 
            AND id_area = :id_area 
            AND auditoria_id = :auditoria_id
        """)
        existing = conn.execute(check_query, {
            'nome': nome_upper,
            'id_area': area_id,
            'auditoria_id': auditoria_id
        }).fetchone()
        
        if existing:
            processo_id = existing[0]
            codigo = existing[1]
            
            conn.execute(text("""
                UPDATE processos 
                SET nome_processo = UPPER(:nome), 
                    area = UPPER(:area),
                    auditoria_id = :auditoria_id,
                    entrevistado = UPPER(:entrevistado),
                    updated_at = NOW()
                WHERE id = :id
            """), {
                'nome': nome_upper,
                'area': nome_area,
                'auditoria_id': auditoria_id,
                'entrevistado': entrevistado.strip().upper(),
                'id': processo_id
            })
        else:
            result = conn.execute(text("""
                INSERT INTO processos (
                    nome_processo, codigo_processo, id_area, area, 
                    auditoria_id, entrevistado, created_at, updated_at
                )
                VALUES (
                    UPPER(:nome), :codigo, :id_area, UPPER(:area), 
                    :auditoria_id, UPPER(:entrevistado), NOW(), NOW()
                )
                RETURNING id
            """), {
                'nome': nome_upper,
                'codigo': codigo_processo,
                'id_area': area_id,
                'area': nome_area,
                'auditoria_id': auditoria_id,
                'entrevistado': entrevistado.strip().upper()
            })
            processo_id = result.fetchone()[0]
        
        conn.commit()
        
        return processo_id


def salvar_executores_processo(processo_id, funcionarios_ids):
    """Salva os executores de um processo"""
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Remove vínculos antigos
        conn.execute(text("DELETE FROM processo_executores WHERE processo_id = :pid"), {'pid': processo_id})
        
        # Insere novos vínculos
        if funcionarios_ids:
            for fid in funcionarios_ids:
                conn.execute(text("""
                    INSERT INTO processo_executores (processo_id, funcionario_id, created_at, updated_at)
                    VALUES (:pid, :fid, NOW(), NOW())
                """), {'pid': processo_id, 'fid': fid})
    
        conn.commit()