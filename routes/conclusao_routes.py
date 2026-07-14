from flask import request, jsonify, session
from database import engine
from sqlalchemy import text
from . import conclusao_bp

# ⭐ PRINT PARA CONFIRMAR QUE O ARQUIVO FOI CARREGADO
print("🔵 Arquivo conclusao_routes.py CARREGADO!")

# ⭐ PRINT PARA VER AS ROTAS REGISTRADAS
print(f"🔵 Blueprint conclusao_bp registrado com prefixo: {conclusao_bp.url_prefix}")

# ============================================================
# ====== API PARA CONCLUSÕES DE AUDITORIA ======
# ============================================================

@conclusao_bp.route('/conclusoes/salvar', methods=['POST'])
def api_salvar_conclusao():
    """
    Salva ou atualiza uma conclusão de auditoria
    - Se já existe conclusão do mesmo usuário para esta auditoria/área, atualiza
    - Senão, cria uma nova
    """
    from database import engine
    from sqlalchemy import text
    from flask import session
    
    data = request.json
    auditoria_id = data.get('auditoria_id')
    area_id = data.get('area_id')
    conclusao = data.get('conclusao', '').strip()
    
    # ⭐ Validações
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'Auditoria é obrigatória'}), 400
    
    if not area_id:
        return jsonify({'success': False, 'error': 'Área é obrigatória'}), 400
    
    if not conclusao:
        return jsonify({'success': False, 'error': 'Conclusão não pode estar vazia'}), 400
    
    # ⭐ Pegar nome do usuário da sessão
    usuario_nome = session.get('usuario_nome', 'Usuário')
    
    try:
        with engine.connect() as conn:
            # ⭐ Verificar se já existe conclusão deste usuário
            check_query = text("""
                SELECT id FROM conclusoes_auditoria 
                WHERE auditoria_id = :auditoria_id 
                AND area_id = :area_id 
                AND usuario_nome = :usuario_nome
            """)
            
            existing = conn.execute(check_query, {
                'auditoria_id': auditoria_id,
                'area_id': area_id,
                'usuario_nome': usuario_nome
            }).fetchone()
            
            if existing:
                # ⭐ Atualizar conclusão existente
                update_query = text("""
                    UPDATE conclusoes_auditoria 
                    SET conclusao = :conclusao, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """)
                conn.execute(update_query, {
                    'id': existing[0],
                    'conclusao': conclusao
                })
                mensagem = 'Conclusão atualizada com sucesso!'
                acao = 'atualizada'
            else:
                # ⭐ Inserir nova conclusão
                insert_query = text("""
                    INSERT INTO conclusoes_auditoria (
                        auditoria_id, area_id, usuario_nome, conclusao
                    ) VALUES (
                        :auditoria_id, :area_id, :usuario_nome, :conclusao
                    )
                """)
                conn.execute(insert_query, {
                    'auditoria_id': auditoria_id,
                    'area_id': area_id,
                    'usuario_nome': usuario_nome,
                    'conclusao': conclusao
                })
                mensagem = 'Conclusão salva com sucesso!'
                acao = 'salva'
            
            conn.commit()
            
            print(f"📝 Conclusão {acao} para auditoria {auditoria_id}, área {area_id} por {usuario_nome}")
            return jsonify({
                'success': True, 
                'message': mensagem,
                'acao': acao
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar conclusão: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@conclusao_bp.route('/conclusoes/buscar', methods=['GET'])
def api_buscar_conclusao():
    """
    Busca a conclusão do usuário atual para uma auditoria/área específica
    """
    from database import engine
    from sqlalchemy import text
    from flask import session
    
    auditoria_id = request.args.get('auditoria_id')
    area_id = request.args.get('area_id')
    
    if not auditoria_id or not area_id:
        return jsonify({'success': False, 'error': 'Parâmetros incompletos'}), 400
    
    usuario_nome = session.get('usuario_nome', 'Usuário')
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, conclusao, created_at, updated_at
                FROM conclusoes_auditoria
                WHERE auditoria_id = :auditoria_id 
                AND area_id = :area_id 
                AND usuario_nome = :usuario_nome
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'area_id': area_id,
                'usuario_nome': usuario_nome
            }).fetchone()
            
            if result:
                return jsonify({
                    'success': True,
                    'conclusao': {
                        'id': result[0],
                        'texto': result[1],
                        'created_at': result[2].strftime('%d/%m/%Y %H:%M') if result[2] else None,
                        'updated_at': result[3].strftime('%d/%m/%Y %H:%M') if result[3] else None
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'conclusao': None
                })
                
    except Exception as e:
        print(f"❌ Erro ao buscar conclusão: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@conclusao_bp.route('/conclusoes/historico', methods=['GET'])
def api_historico_conclusoes():
    """
    Busca TODAS as conclusões de uma auditoria/área (todos os usuários)
    """
    from database import engine
    from sqlalchemy import text
    
    auditoria_id = request.args.get('auditoria_id')
    area_id = request.args.get('area_id')
    
    if not auditoria_id or not area_id:
        return jsonify({'success': False, 'error': 'Parâmetros incompletos'}), 400
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, usuario_nome, conclusao, created_at, updated_at
                FROM conclusoes_auditoria
                WHERE auditoria_id = :auditoria_id AND area_id = :area_id
                ORDER BY created_at DESC
            """)
            
            results = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'area_id': area_id
            }).fetchall()
            
            conclusoes = []
            for row in results:
                conclusoes.append({
                    'id': row[0],
                    'usuario_nome': row[1],
                    'conclusao': row[2],
                    'created_at': row[3].strftime('%d/%m/%Y %H:%M') if row[3] else None,
                    'updated_at': row[4].strftime('%d/%m/%Y %H:%M') if row[4] else None
                })
            
            return jsonify({
                'success': True,
                'conclusoes': conclusoes
            })
                
    except Exception as e:
        print(f"❌ Erro ao buscar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# routes/conclusao_routes.py
# Adicione esta nova rota no final do arquivo

@conclusao_bp.route('/relatorios/gerar-conclusao', methods=['POST'])
def gerar_relatorio_conclusao():
    """
    Gera o relatório de conclusão em PDF
    """
    from flask import session, make_response
    from logic import gerar_pdf_conclusao
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import traceback
    
    print("=" * 50)
    print("🔵 ROTA /relatorios/gerar-conclusao FOI CHAMADA!")
    
    try:
        data = request.json
        print(f"📥 Dados recebidos: {data}")
        
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        orientacao = data.get('orientacao', 'RETRATO')
        conclusao = data.get('conclusao', '').strip()
        
        print(f"📥 area_id: {area_id}, auditoria_id: {auditoria_id}")
        print(f"📥 orientacao: {orientacao}")
        print(f"📥 conclusao: {conclusao[:50]}...")
        
        # Validações
        if not area_id:
            print("❌ area_id não informado")
            return jsonify({'error': 'Área não informada'}), 400
        
        if not auditoria_id:
            print("❌ auditoria_id não informado")
            return jsonify({'error': 'Auditoria não informada'}), 400
        
        if not conclusao:
            print("❌ conclusão vazia")
            return jsonify({'error': 'Conclusão não pode estar vazia'}), 400
        
        # Buscar dados da área
        print("🔍 Buscando dados da área...")
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor, cargo, loc_unidade
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area_info:
                print("❌ Área não encontrada")
                return jsonify({'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0] or 'Área não identificada'
            gestor = area_info[1] or 'Não informado'
            cargo = area_info[2] or 'Não informado'
            unidade = area_info[3] or ''
            
            print(f"✅ Área encontrada: {area_nome}")
            print(f"   Gestor: {gestor}")
            print(f"   Cargo: {cargo}")
            print(f"   Unidade: {unidade}")
            
            # Buscar dados da auditoria
            print("🔍 Buscando dados da auditoria...")
            query_auditoria = text("""
                SELECT codigo_auditoria, titulo, trimestre, ano
                FROM auditorias
                WHERE id = :auditoria_id
            """)
            auditoria_info = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
            
            if not auditoria_info:
                print("⚠️ Auditoria não encontrada, usando valores padrão")
                codigo_auditoria = 'N/A'
                titulo_auditoria = 'Auditoria'
            else:
                codigo_auditoria = auditoria_info[0] or 'N/A'
                titulo_auditoria = auditoria_info[1] or 'Auditoria'
            
            print(f"✅ Auditoria: {codigo_auditoria} - {titulo_auditoria}")
        
        # Pegar nome do usuário da sessão
        usuario_nome = session.get('usuario_nome', 'Usuário')
        print(f"👤 Usuário: {usuario_nome}")
        
        # Gerar o PDF
        print("📄 Chamando gerar_pdf_conclusao...")
        pdf_bytes = gerar_pdf_conclusao(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            unidade=unidade,
            codigo_auditoria=codigo_auditoria,
            titulo_auditoria=titulo_auditoria,
            conclusao=conclusao,
            orientacao=orientacao,
            usuario_nome=usuario_nome
        )
        print(f"✅ PDF gerado! Tamanho: {len(pdf_bytes)} bytes")
        
        # Nome do arquivo
        TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
        data_atual = datetime.now(TZ_BRASILIA).strftime('%Y%m%d_%H%M')
        nome_arquivo = f"relatorio_conclusao_{area_nome.replace(' ', '_')}_{data_atual}.pdf"
        print(f"📁 Nome do arquivo: {nome_arquivo}")
        
        # Retornar o PDF
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        print("✅ Resposta criada com sucesso!")
        print("=" * 50)
        return response
        
    except Exception as e:
        print(f"❌❌❌ ERRO NA ROTA: {e}")
        print(traceback.format_exc())
        print("=" * 50)
        return jsonify({'error': str(e)}), 500