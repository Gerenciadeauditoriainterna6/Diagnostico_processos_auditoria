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
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    ac.id as analise_id,
                    ac.analise_critica,
                    ac.categoria,
                    ac.sugestao_sera_implantada,
                    p.codigo_processo,
                    p.nome_processo,
                    ep.codigo_etapa,
                    afu.id as follow_up_id,
                    afu.etapa,
                    afu.data_prevista,
                    afu.data_realizada,
                    afu.status,
                    afu.comentario,
                    afu.responsavel
                FROM analises_criticas ac
                LEFT JOIN processos p ON ac.processo_id = p.id
                LEFT JOIN etapas_processo ep ON ac.etapa_id = ep.id
                LEFT JOIN analises_follow_up afu ON ac.id = afu.analise_id
                WHERE ac.sugestao_sera_implantada = 'true'
                ORDER BY ac.id, afu.data_prevista
            """)
            result = conn.execute(query).fetchall()
            
            analises_map = {}
            
            for row in result:
                # ⭐ USANDO row._mapping PARA ACESSAR POR NOME
                analise_id = row._mapping['analise_id']
                
                if analise_id not in analises_map:
                    analises_map[analise_id] = {
                        'id': analise_id,
                        'analise_critica': row._mapping['analise_critica'] or 'Análise sem título',
                        'categoria': row._mapping['categoria'] or '',
                        'codigo_etapa': row._mapping['codigo_etapa'] or '',
                        'sugestao_sera_implantada': row._mapping['sugestao_sera_implantada'] == True,
                        'codigo_processo': row._mapping['codigo_processo'] or '',
                        'nome_processo': row._mapping['nome_processo'] or '',
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
# CRIAR FOLLOW-UPS (AUTOMÁTICO)
# ============================================================

@followups_bp.route('/api/criar', methods=['POST'])
def api_followups_criar():
    """Cria follow-ups automáticos para uma análise (30, 60, 90 dias)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('analise_id')
    data_implantacao = data.get('data_implantacao')
    
    if not analise_id:
        return jsonify({'success': False, 'error': 'analise_id é obrigatório'}), 400
    
    if not data_implantacao:
        return jsonify({'success': False, 'error': 'data_implantacao é obrigatória'}), 400
    
    try:
        # Calcular as datas
        data_base = datetime.strptime(data_implantacao, '%Y-%m-%d').date()
        
        follow_ups = [
            {'etapa': 'FOLLOW_UP_30', 'data_prevista': (data_base + timedelta(days=30)).isoformat()},
            {'etapa': 'FOLLOW_UP_60', 'data_prevista': (data_base + timedelta(days=60)).isoformat()},
            {'etapa': 'FOLLOW_UP_90', 'data_prevista': (data_base + timedelta(days=90)).isoformat()}
        ]
        
        with engine.connect() as conn:
            for fu in follow_ups:
                query = text("""
                    INSERT INTO analises_follow_up (
                        analise_id, etapa, data_prevista, status, 
                        comentario, created_at, updated_at
                    ) VALUES (
                        :analise_id, :etapa, :data_prevista, 'Pendente',
                        'Aguardando registro', NOW(), NOW()
                    )
                """)
                conn.execute(query, {
                    'analise_id': analise_id,
                    'etapa': fu['etapa'],
                    'data_prevista': fu['data_prevista']
                })
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': f'{len(follow_ups)} follow-ups criados',
                'follow_ups': follow_ups
            })
            
    except Exception as e:
        print(f"❌ Erro ao criar follow-ups: {e}")
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
    

# ============================================================
# INICIAR ACOMPANHAMENTO (CRIAR FOLLOW-UPS)
# ============================================================

@followups_bp.route('/api/iniciar-acompanhamento', methods=['POST'])
def api_iniciar_acompanhamento():
    """Cria follow-ups de 30, 60 e 90 dias para uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('analise_id')
    
    if not analise_id:
        return jsonify({'success': False, 'error': 'analise_id é obrigatório'}), 400
    
    try:
        # Calcular as datas (a partir de hoje)
        data_base = datetime.now().date()
        
        follow_ups = [
            {'etapa': 'FOLLOW_UP_30', 'data_prevista': (data_base + timedelta(days=30)).isoformat()},
            {'etapa': 'FOLLOW_UP_60', 'data_prevista': (data_base + timedelta(days=60)).isoformat()},
            {'etapa': 'FOLLOW_UP_90', 'data_prevista': (data_base + timedelta(days=90)).isoformat()}
        ]
        
        with engine.connect() as conn:
            for fu in follow_ups:
                query = text("""
                    INSERT INTO analises_follow_up (
                        analise_id, etapa, data_prevista, status, 
                        comentario, created_at, updated_at
                    ) VALUES (
                        :analise_id, :etapa, :data_prevista, 'Pendente',
                        'Aguardando registro', NOW(), NOW()
                    )
                """)
                conn.execute(query, {
                    'analise_id': analise_id,
                    'etapa': fu['etapa'],
                    'data_prevista': fu['data_prevista']
                })
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Acompanhamento iniciado! 3 follow-ups criados (30, 60 e 90 dias).'
            })
            
    except Exception as e:
        print(f"❌ Erro ao iniciar acompanhamento: {e}")
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