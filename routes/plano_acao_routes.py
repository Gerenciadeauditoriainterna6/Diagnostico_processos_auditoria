# routes/plano_acao_routes.py
from flask import request, jsonify, session
from database import engine
from sqlalchemy import text
from . import plano_acao_bp

# ============================================================
# ====== API PARA PLANO DE AÇÃO 5W2H ======
# ============================================================

@plano_acao_bp.route('/planos-acao', methods=['POST'])
def criar_plano_acao():
    """
    Cria um novo plano de ação 5W2H para uma análise
    """
    data = request.json
    
    # ⭐ ADICIONAR LOG PARA VER O QUE CHEGA
    print("=" * 50)
    print("📥 DADOS RECEBIDOS NO BACKEND:")
    print(f"  {data}")
    print("=" * 50)
    
    analise_id = data.get('analise_id')
    
    if not analise_id:
        print("❌ analise_id não informado!")
        return jsonify({'success': False, 'error': 'ID da análise é obrigatório'}), 400
    
    # Validar campos obrigatórios
    oque = data.get('oque', '').strip()
    por_que = data.get('por_que', '').strip()
    onde = data.get('onde', '').strip()
    quando = data.get('quando')
    quem = data.get('quem', '').strip()
    como = data.get('como', '').strip()
    
    print(f"📋 Campos extraídos:")
    print(f"  oque: '{oque}'")
    print(f"  por_que: '{por_que}'")
    print(f"  onde: '{onde}'")
    print(f"  quando: '{quando}'")
    print(f"  quem: '{quem}'")
    print(f"  como: '{como}'")
    
    if not oque:
        print("❌ Campo 'oque' vazio!")
        return jsonify({'success': False, 'error': 'Campo "O que será feito?" é obrigatório'}), 400
    if not por_que:
        print("❌ Campo 'por_que' vazio!")
        return jsonify({'success': False, 'error': 'Campo "Por que será feito?" é obrigatório'}), 400
    if not onde:
        print("❌ Campo 'onde' vazio!")
        return jsonify({'success': False, 'error': 'Campo "Onde será feito?" é obrigatório'}), 400
    if not quando:
        print("❌ Campo 'quando' vazio!")
        return jsonify({'success': False, 'error': 'Campo "Quando será feito?" é obrigatório'}), 400
    if not quem:
        print("❌ Campo 'quem' vazio!")
        return jsonify({'success': False, 'error': 'Campo "Quem fará?" é obrigatório'}), 400
    if not como:
        print("❌ Campo 'como' vazio!")
        return jsonify({'success': False, 'error': 'Campo "Como será feito?" é obrigatório'}), 400
    
    print("✅ Todos os campos validados com sucesso!")
    
    usuario_nome = session.get('usuario_nome', 'Usuário')
    
    try:
        with engine.connect() as conn:
            # Verificar se a análise existe
            check_analise = text("""
                SELECT id FROM analises_criticas WHERE id = :analise_id
            """)
            analise_exists = conn.execute(check_analise, {'analise_id': analise_id}).fetchone()
            
            if not analise_exists:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            # Verificar se já existe um plano para esta análise
            check_plano = text("""
                SELECT id FROM planos_acao WHERE analise_id = :analise_id
            """)
            plano_existente = conn.execute(check_plano, {'analise_id': analise_id}).fetchone()
            
            if plano_existente:
                # Se já existe, atualizar em vez de criar
                update_query = text("""
                    UPDATE planos_acao SET
                        oque = :oque,
                        por_que = :por_que,
                        onde = :onde,
                        quando = :quando,
                        quem = :quem,
                        como = :como,
                        quanto_custa = :quanto_custa,
                        comentario = :comentario,
                        updated_at = NOW()
                    WHERE id = :plano_id
                    RETURNING id
                """)
                
                result = conn.execute(update_query, {
                    'plano_id': plano_existente[0],
                    'oque': oque,
                    'por_que': por_que,
                    'onde': onde,
                    'quando': quando,
                    'quem': quem,
                    'como': como,
                    'quanto_custa': data.get('quanto_custa', ''),
                    'comentario': data.get('comentario')
                })
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Plano de ação atualizado com sucesso!',
                    'plano_id': plano_existente[0],
                    'atualizado': True
                })
            
            # Inserir novo plano de ação
            insert_query = text("""
                INSERT INTO planos_acao (
                    analise_id, oque, por_que, onde, quando, 
                    quem, como, quanto_custa, comentario, created_by
                ) VALUES (
                    :analise_id, :oque, :por_que, :onde, :quando,
                    :quem, :como, :quanto_custa, :comentario, :created_by
                ) RETURNING id
            """)
            
            result = conn.execute(insert_query, {
                'analise_id': analise_id,
                'oque': oque,
                'por_que': por_que,
                'onde': onde,
                'quando': quando,
                'quem': quem,
                'como': como,
                'quanto_custa': data.get('quanto_custa', ''),
                'comentario': data.get('comentario'),
                'created_by': usuario_nome
            })
            
            plano_id = result.fetchone()[0]
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Plano de ação criado com sucesso!',
                'plano_id': plano_id,
                'atualizado': False
            })
            
    except Exception as e:
        print(f"❌ Erro ao criar/atualizar plano de ação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@plano_acao_bp.route('/planos-acao/<int:analise_id>', methods=['GET'])
def buscar_plano_acao(analise_id):
    """
    Busca o plano de ação de uma análise específica
    """
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    id, analise_id, oque, por_que, onde, quando,
                    quem, como, quanto_custa, comentario,
                    created_by, created_at, updated_at
                FROM planos_acao
                WHERE analise_id = :analise_id
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = conn.execute(query, {'analise_id': analise_id}).fetchone()
            
            if result:
                return jsonify({
                    'success': True,
                    'plano': {
                        'id': result[0],
                        'analise_id': result[1],
                        'oque': result[2],
                        'por_que': result[3],
                        'onde': result[4],
                        'quando': result[5].isoformat() if result[5] else None,
                        'quem': result[6],
                        'como': result[7],
                        'quanto_custa': result[8],
                        'comentario': result[9],
                        'created_by': result[10],
                        'created_at': result[11].isoformat() if result[11] else None,
                        'updated_at': result[12].isoformat() if result[12] else None
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'plano': None
                })
                
    except Exception as e:
        print(f"❌ Erro ao buscar plano de ação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@plano_acao_bp.route('/planos-acao/<int:plano_id>', methods=['PUT'])
def atualizar_plano_acao(plano_id):
    """
    Atualiza um plano de ação existente
    """
    data = request.json
    
    # Validar campos obrigatórios
    oque = data.get('oque', '').strip()
    por_que = data.get('por_que', '').strip()
    onde = data.get('onde', '').strip()
    quando = data.get('quando')
    quem = data.get('quem', '').strip()
    como = data.get('como', '').strip()
    
    if not oque:
        return jsonify({'success': False, 'error': 'Campo "O que será feito?" é obrigatório'}), 400
    if not por_que:
        return jsonify({'success': False, 'error': 'Campo "Por que será feito?" é obrigatório'}), 400
    if not onde:
        return jsonify({'success': False, 'error': 'Campo "Onde será feito?" é obrigatório'}), 400
    if not quando:
        return jsonify({'success': False, 'error': 'Campo "Quando será feito?" é obrigatório'}), 400
    if not quem:
        return jsonify({'success': False, 'error': 'Campo "Quem fará?" é obrigatório'}), 400
    if not como:
        return jsonify({'success': False, 'error': 'Campo "Como será feito?" é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            update_query = text("""
                UPDATE planos_acao SET
                    oque = :oque,
                    por_que = :por_que,
                    onde = :onde,
                    quando = :quando,
                    quem = :quem,
                    como = :como,
                    quanto_custa = :quanto_custa,
                    comentario = :comentario,
                    updated_at = NOW()
                WHERE id = :plano_id
                RETURNING id
            """)
            
            result = conn.execute(update_query, {
                'plano_id': plano_id,
                'oque': oque,
                'por_que': por_que,
                'onde': onde,
                'quando': quando,
                'quem': quem,
                'como': como,
                'quanto_custa': data.get('quanto_custa', ''),
                'comentario': data.get('comentario')
            })
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Plano de ação não encontrado'}), 404
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Plano de ação atualizado com sucesso!'
            })
            
    except Exception as e:
        print(f"❌ Erro ao atualizar plano de ação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@plano_acao_bp.route('/planos-acao/<int:plano_id>', methods=['DELETE'])
def deletar_plano_acao(plano_id):
    """
    Remove um plano de ação
    """
    try:
        with engine.connect() as conn:
            # Verificar se o plano existe
            check_query = text("SELECT id FROM planos_acao WHERE id = :plano_id")
            existe = conn.execute(check_query, {'plano_id': plano_id}).fetchone()
            
            if not existe:
                return jsonify({'success': False, 'error': 'Plano de ação não encontrado'}), 404
            
            delete_query = text("DELETE FROM planos_acao WHERE id = :plano_id")
            conn.execute(delete_query, {'plano_id': plano_id})
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Plano de ação removido com sucesso!'
            })
            
    except Exception as e:
        print(f"❌ Erro ao deletar plano de ação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500