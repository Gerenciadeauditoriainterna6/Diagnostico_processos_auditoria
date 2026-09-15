# routes/followups/api.py

from flask import jsonify, request, session
from . import followups_bp
from database import engine
from sqlalchemy import text
from datetime import datetime, timedelta


# ============================================================
# BUSCAR TODOS OS FOLLOW-UPS
# ============================================================

@followups_bp.route('/api/todos')
def api_followups_todos():
    """Busca todas as análises com sugestão 'Será implantada' e seus follow-ups"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    
    try:
        with engine.connect() as conn:
            base_query = """
                SELECT 
                    ac.id as analise_id,
                    ac.analise_critica,
                    ac.categoria,
                    ac.tipo,
                    ac.sugestao_sera_implantada,
                    ac.plano_de_acao_implantado,
                    ac.data_execucao_plano_acao,
                    p.codigo_processo,
                    p.nome_processo,
                    ep.codigo_etapa,
                    afu.id as follow_up_id,
                    afu.etapa,
                    afu.data_prevista,
                    afu.data_realizada,
                    afu.status,
                    afu.comentario,
                    afu.responsavel,
                    pa.id as plano_id,
                    pa.oque as plano_oque,
                    pa.por_que as plano_por_que,
                    pa.onde as plano_onde,
                    pa.quando_inicio as plano_quando_inicio,
                    pa.quando_fim as plano_quando_fim,
                    pa.quem as plano_quem,
                    pa.como as plano_como,
                    pa.quanto_custa as plano_quanto_custa,
                    pa.comentario as plano_comentario
                FROM analises_criticas ac
                LEFT JOIN processos p ON ac.processo_id = p.id
                LEFT JOIN etapas_processo ep ON ac.etapa_id = ep.id
                LEFT JOIN analises_follow_up afu ON ac.id = afu.analise_id
                LEFT JOIN planos_acao pa ON ac.id = pa.analise_id
                WHERE ac.sugestao_sera_implantada = 'true'
            """
            
            params = {}
            if processo_id:
                base_query += " AND ac.processo_id = :processo_id"
                params['processo_id'] = processo_id
            
            base_query += " ORDER BY ac.id, afu.data_prevista"
            
            query = text(base_query)
            result = conn.execute(query, params).fetchall()
            
            analises_map = {}
            
            for row in result:
                analise_id = row._mapping['analise_id']
                
                if analise_id not in analises_map:
                    # ⭐ VERIFICAR PLANO DE AÇÃO
                    plano = None
                    if row._mapping['plano_id'] is not None:
                        plano = {
                            'id': row._mapping['plano_id'],
                            'oque': row._mapping['plano_oque'] or '',
                            'por_que': row._mapping['plano_por_que'] or '',
                            'onde': row._mapping['plano_onde'] or '',
                            'quando_inicio': row._mapping['plano_quando_inicio'].isoformat() if row._mapping['plano_quando_inicio'] else None,
                            'quando_fim': row._mapping['plano_quando_fim'].isoformat() if row._mapping['plano_quando_fim'] else None,
                            'quem': row._mapping['plano_quem'] or '',
                            'como': row._mapping['plano_como'] or '',
                            'quanto_custa': str(row._mapping['plano_quanto_custa']) if row._mapping['plano_quanto_custa'] else None,
                            'comentario': row._mapping['plano_comentario'] or ''
                        }
                    
                    analises_map[analise_id] = {
                        'id': analise_id,
                        'analise_critica': row._mapping['analise_critica'] or 'Análise sem título',
                        'categoria': row._mapping['categoria'] or '',
                        'tipo_analise': row._mapping['tipo'] or 'auditado',
                        'codigo_etapa': row._mapping['codigo_etapa'] or '',
                        'sugestao_sera_implantada': row._mapping['sugestao_sera_implantada'] == True,
                        'plano_de_acao_implantado': row._mapping['plano_de_acao_implantado'] == True,
                        'data_execucao_plano_acao': row._mapping['data_execucao_plano_acao'].isoformat() if row._mapping['data_execucao_plano_acao'] else None,
                        'codigo_processo': row._mapping['codigo_processo'] or '',
                        'nome_processo': row._mapping['nome_processo'] or '',
                        'plano_acao': plano,
                        'follow_ups': []
                    }
                
                follow_up_id = row._mapping['follow_up_id']
                if follow_up_id is not None:
                    data_prevista = row._mapping['data_prevista']
                    status = row._mapping['status'] or 'Pendente'
                    
                    if data_prevista and status == 'Pendente':
                        if isinstance(data_prevista, str):
                            data_prevista_date = datetime.strptime(data_prevista, '%Y-%m-%d').date()
                        else:
                            data_prevista_date = data_prevista
                        
                        if data_prevista_date < datetime.now().date():
                            status = 'Atrasado'
                    
                    analises_map[analise_id]['follow_ups'].append({
                        'id': follow_up_id,
                        'etapa': row._mapping['etapa'],
                        'data_prevista': data_prevista.isoformat() if data_prevista else None,
                        'data_realizada': row._mapping['data_realizada'].isoformat() if row._mapping['data_realizada'] else None,
                        'status': status,
                        'comentario': row._mapping['comentario'] or '',
                        'responsavel': row._mapping['responsavel'] or ''
                    })
            
            return jsonify({'success': True, 'analises': list(analises_map.values())})
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises para acompanhamento: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# BUSCAR FOLLOW-UPS POR ANÁLISE
# ============================================================

@followups_bp.route('/api/por-analise/<int:analise_id>')
def api_followups_por_analise(analise_id):
    """Busca os follow-ups de uma análise específica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa, data_prevista, data_realizada, status, comentario, responsavel
                FROM analises_follow_up
                WHERE analise_id = :analise_id
                ORDER BY data_prevista ASC
            """)
            result = conn.execute(query, {'analise_id': analise_id}).fetchall()
            
            follow_ups = []
            for row in result:
                # Determinar se está atrasado
                data_prevista = row[2]
                status = row[4] or 'Pendente'
                
                if data_prevista and status == 'Pendente':
                    if isinstance(data_prevista, str):
                        data_prevista_date = datetime.strptime(data_prevista, '%Y-%m-%d').date()
                    else:
                        data_prevista_date = data_prevista
                    
                    if data_prevista_date < datetime.now().date():
                        status = 'Atrasado'
                
                follow_ups.append({
                    'id': row[0],
                    'etapa': row[1],
                    'data_prevista': row[2].isoformat() if row[2] else None,
                    'data_realizada': row[3].isoformat() if row[3] else None,
                    'status': status,
                    'comentario': row[5] or '',
                    'responsavel': row[6] or ''
                })
            
            return jsonify({'success': True, 'follow_ups': follow_ups})
            
    except Exception as e:
        print(f"❌ Erro ao buscar follow-ups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# ATUALIZAR FOLLOW-UP (REGISTRAR RESULTADO)
# ============================================================

@followups_bp.route('/api/atualizar/<int:follow_up_id>', methods=['PUT'])
def api_followup_atualizar(follow_up_id):
    """Atualiza um follow-up (registra resultado)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    status = data.get('status')
    comentario = data.get('comentario')
    usuario_nome = session.get('usuario_nome', 'Sistema')
    
    if not status:
        return jsonify({'success': False, 'error': 'Status é obrigatório'}), 400
    
    if not comentario or not comentario.strip():
        return jsonify({'success': False, 'error': 'Comentário é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE analises_follow_up 
                SET status = :status,
                    comentario = :comentario,
                    data_realizada = NOW(),
                    responsavel = :responsavel,
                    updated_at = NOW()
                WHERE id = :id
            """)
            result = conn.execute(query, {
                'id': follow_up_id,
                'status': status,
                'comentario': comentario,
                'responsavel': usuario_nome
            })
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Follow-up não encontrado'}), 404
            
            return jsonify({
                'success': True, 
                'message': 'Follow-up registrado com sucesso!'
            })
            
    except Exception as e:
        print(f"❌ Erro ao atualizar follow-up: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ESTATÍSTICAS DOS FOLLOW-UPS
# ============================================================

@followups_bp.route('/api/estatisticas')
def api_followups_estatisticas():
    """Retorna estatísticas dos follow-ups"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            # Total
            total_query = text("SELECT COUNT(*) FROM analises_follow_up")
            total = conn.execute(total_query).scalar() or 0
            
            # Por status
            status_query = text("""
                SELECT status, COUNT(*) 
                FROM analises_follow_up 
                GROUP BY status
            """)
            status_result = conn.execute(status_query).fetchall()
            
            status_counts = {}
            for row in status_result:
                status_counts[row[0]] = row[1]
            
            # Atrasados
            atrasados_query = text("""
                SELECT COUNT(*) 
                FROM analises_follow_up 
                WHERE status = 'Pendente' AND data_prevista < CURDATE()
            """)
            atrasados = conn.execute(atrasados_query).scalar() or 0
            
            return jsonify({
                'success': True,
                'estatisticas': {
                    'total': total,
                    'pendentes': status_counts.get('Pendente', 0),
                    'aderentes': status_counts.get('Aderente', 0),
                    'nao_aderentes': status_counts.get('Nao aderente', 0),
                    'parcialmente_aderentes': status_counts.get('Parcialmente aderente', 0),
                    'atrasados': atrasados
                }
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    
@followups_bp.route('/api/follow-up/<int:follow_up_id>')
def api_followup_buscar(follow_up_id):
    """Busca um follow-up específico"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, analise_id, etapa, data_prevista, data_realizada, 
                       status, comentario, responsavel
                FROM analises_follow_up
                WHERE id = :id
            """)
            result = conn.execute(query, {'id': follow_up_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Follow-up não encontrado'}), 404
            
            return jsonify({
                'success': True,
                'follow_up': {
                    'id': result[0],
                    'analise_id': result[1],
                    'etapa': result[2],
                    'data_prevista': result[3].isoformat() if result[3] else None,
                    'data_realizada': result[4].isoformat() if result[4] else None,
                    'status': result[5] or 'Pendente',
                    'comentario': result[6] or '',
                    'responsavel': result[7] or ''
                }
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar follow-up: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PLANO DE AÇÃO 5W2H
# ============================================================

@followups_bp.route('/api/plano-acao/<int:analise_id>')
def api_plano_acao_buscar(analise_id):
    """Busca o plano de ação de uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, analise_id, oque, por_que, onde, 
                       quando_inicio, quando_fim, 
                       quem, como, quanto_custa, comentario
                FROM planos_acao
                WHERE analise_id = :analise_id
                ORDER BY id DESC
                LIMIT 1
            """)
            result = conn.execute(query, {'analise_id': analise_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Plano de ação não encontrado'}), 404
            
            return jsonify({
                'success': True,
                'plano': {
                    'id': result[0],
                    'analise_id': result[1],
                    'oque': result[2] or '',
                    'por_que': result[3] or '',
                    'onde': result[4] or '',
                    'quando_inicio': result[5].isoformat() if result[5] else None,
                    'quando_fim': result[6].isoformat() if result[6] else None,
                    'quem': result[7] or '',
                    'como': result[8] or '',
                    'quanto_custa': str(result[9]) if result[9] else None,
                    'comentario': result[10] or ''
                }
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar plano de ação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@followups_bp.route('/api/plano-acao/salvar', methods=['POST'])
def api_plano_acao_salvar():
    """Salva ou atualiza o plano de ação de uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('analise_id')
    oque = data.get('oque')
    quem = data.get('quem')
    quando_inicio = data.get('quando_inicio')
    quando_fim = data.get('quando_fim')
    
    if not analise_id:
        return jsonify({'success': False, 'error': 'analise_id é obrigatório'}), 400
    
    if not oque:
        return jsonify({'success': False, 'error': 'O campo "O que?" é obrigatório'}), 400
    
    if not quem:
        return jsonify({'success': False, 'error': 'O campo "Quem?" é obrigatório'}), 400
    
    # ⭐ VALIDAÇÃO: quando_inicio e quando_fim são obrigatórios
    if not quando_inicio:
        return jsonify({'success': False, 'error': 'A data de início é obrigatória'}), 400
    
    if not quando_fim:
        return jsonify({'success': False, 'error': 'A data de término é obrigatória'}), 400
    
    if quando_fim < quando_inicio:
        return jsonify({'success': False, 'error': 'A data de término não pode ser antes da data de início'}), 400
    
    usuario_nome = session.get('usuario_nome', 'Sistema')
    
    try:
        with engine.connect() as conn:
            # Verificar se já existe um plano para esta análise
            check_query = text("SELECT id FROM planos_acao WHERE analise_id = :analise_id")
            existing = conn.execute(check_query, {'analise_id': analise_id}).fetchone()
            
            if existing:
                # Atualizar
                update_query = text("""
                    UPDATE planos_acao 
                    SET oque = :oque,
                        por_que = :por_que,
                        onde = :onde,
                        quando_inicio = :quando_inicio,
                        quando_fim = :quando_fim,
                        quem = :quem,
                        como = :como,
                        quanto_custa = :quanto_custa,
                        comentario = :comentario,
                        updated_at = NOW()
                    WHERE analise_id = :analise_id
                """)
                conn.execute(update_query, {
                    'analise_id': analise_id,
                    'oque': oque,
                    'por_que': data.get('por_que') or None,
                    'onde': data.get('onde') or None,
                    'quando_inicio': quando_inicio,
                    'quando_fim': quando_fim,
                    'quem': quem,
                    'como': data.get('como') or None,
                    'quanto_custa': data.get('quanto_custa') or None,
                    'comentario': data.get('comentario') or None
                })
                message = 'Plano de ação atualizado com sucesso!'
            else:
                # Inserir
                insert_query = text("""
                    INSERT INTO planos_acao (
                        analise_id, oque, por_que, onde, 
                        quando_inicio, quando_fim, 
                        quem, como, quanto_custa, comentario, 
                        created_by, created_at, updated_at
                    ) VALUES (
                        :analise_id, :oque, :por_que, :onde,
                        :quando_inicio, :quando_fim,
                        :quem, :como, :quanto_custa, :comentario,
                        :created_by, NOW(), NOW()
                    )
                """)
                conn.execute(insert_query, {
                    'analise_id': analise_id,
                    'oque': oque,
                    'por_que': data.get('por_que') or None,
                    'onde': data.get('onde') or None,
                    'quando_inicio': quando_inicio,
                    'quando_fim': quando_fim,
                    'quem': quem,
                    'como': data.get('como') or None,
                    'quanto_custa': data.get('quanto_custa') or None,
                    'comentario': data.get('comentario') or None,
                    'created_by': usuario_nome
                })
                message = 'Plano de ação criado com sucesso!'
            
            # ⭐⭐ AGORA: CRIAR OS FOLLOW-UPS A PARTIR DO QUANDO_FIM ⭐⭐
            from datetime import datetime, timedelta
            
            data_fim = datetime.strptime(quando_fim, '%Y-%m-%d').date()
            data_30 = data_fim + timedelta(days=30)
            data_60 = data_fim + timedelta(days=60)
            data_90 = data_fim + timedelta(days=90)
            
            # Verificar se já existem follow-ups para esta análise
            check_fu = text("SELECT COUNT(*) FROM analises_follow_up WHERE analise_id = :analise_id")
            existe_fu = conn.execute(check_fu, {'analise_id': analise_id}).fetchone()[0] > 0
            
            if not existe_fu:
                # Criar os 3 follow-ups
                for etapa, data_prevista in [
                    ('FOLLOW_UP_30', data_30),
                    ('FOLLOW_UP_60', data_60),
                    ('FOLLOW_UP_90', data_90)
                ]:
                    insert_fu = text("""
                        INSERT INTO analises_follow_up (
                            analise_id, etapa, data_prevista, status, 
                            comentario, created_at, updated_at
                        ) VALUES (
                            :analise_id, :etapa, :data_prevista, 'Pendente',
                            'Aguardando registro', NOW(), NOW()
                        )
                    """)
                    conn.execute(insert_fu, {
                        'analise_id': analise_id,
                        'etapa': etapa,
                        'data_prevista': data_prevista
                    })
            else:
                # ⭐ Recalcular datas dos follow-ups existentes
                for etapa, data_prevista in [
                    ('FOLLOW_UP_30', data_30),
                    ('FOLLOW_UP_60', data_60),
                    ('FOLLOW_UP_90', data_90)
                ]:
                    update_fu = text("""
                        UPDATE analises_follow_up 
                        SET data_prevista = :data_prevista, updated_at = NOW()
                        WHERE analise_id = :analise_id AND etapa = :etapa AND status = 'Pendente'
                    """)
                    conn.execute(update_fu, {
                        'analise_id': analise_id,
                        'etapa': etapa,
                        'data_prevista': data_prevista
                    })
            
            # ⭐ Marcar plano como implantado
            update_analise = text("""
                UPDATE analises_criticas 
                SET plano_de_acao_implantado = true,
                    data_execucao_plano_acao = :quando_fim,
                    updated_at = NOW()
                WHERE id = :analise_id
            """)
            conn.execute(update_analise, {
                'analise_id': analise_id,
                'quando_fim': quando_fim
            })
            
            conn.commit()
            
            return jsonify({'success': True, 'message': message})
            
    except Exception as e:
        print(f"❌ Erro ao salvar plano de ação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500