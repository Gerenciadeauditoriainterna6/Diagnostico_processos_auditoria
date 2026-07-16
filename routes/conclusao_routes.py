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
    from flask import session
    
    auditoria_id = request.args.get('auditoria_id')
    area_id = request.args.get('area_id')
    
    if not auditoria_id or not area_id:
        return jsonify({'success': False, 'error': 'Parâmetros incompletos'}), 400
    
    # ⭐ PEGAR PERFIL DO USUÁRIO DA SESSÃO
    usuario_logado = session.get('usuario_nome', '')
    perfil = session.get('usuario_perfil', '')
    is_admin = perfil in ['administrador', 'admin', 'Administrador']
    
    print(f"🔍 Histórico - Usuário: {usuario_logado}, Perfil: {perfil}, is_admin: {is_admin}")
    
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
            
            # ⭐ RETORNAR TAMBÉM O PERFIL DO USUÁRIO
            return jsonify({
                'success': True,
                'conclusoes': conclusoes,
                'is_admin': is_admin,
                'usuario_logado': usuario_logado
            })
                
    except Exception as e:
        print(f"❌ Erro ao buscar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        conclusao_id = data.get('conclusao_id')
        usuario_filtro = data.get('usuario')
        conclusao_texto = data.get('conclusao')
        
        print(f"📥 conclusao_id: {conclusao_id}")
        print(f"📥 usuario_filtro: {usuario_filtro}")
        
        # Validações
        if not area_id:
            return jsonify({'error': 'Área não informada'}), 400
        
        if not auditoria_id:
            return jsonify({'error': 'Auditoria não informada'}), 400
        
        usuario_logado = session.get('usuario_nome', 'Usuário')
        perfil = session.get('usuario_perfil', '')
        is_admin = perfil in ['administrador', 'admin', 'Administrador']
        
        print(f"👤 Usuário logado: {usuario_logado}, admin: {is_admin}")
        
        # ============================================================
        # 1. BUSCAR A CONCLUSÃO
        # ============================================================
        with engine.connect() as conn:
            if conclusao_id:
                query = text("""
                    SELECT id, usuario_nome, conclusao, created_at
                    FROM conclusoes_auditoria
                    WHERE id = :conclusao_id
                """)
                result = conn.execute(query, {'conclusao_id': conclusao_id}).fetchone()
                
                if not result:
                    return jsonify({'error': 'Conclusão não encontrada'}), 404
                
                # ⭐ Verificar permissão
                if not is_admin and result[1] != usuario_logado:
                    return jsonify({'error': 'Você não tem permissão para baixar esta conclusão'}), 403
                
                usuario_conclusao = result[1]
                texto_conclusao = result[2]
                data_criacao = result[3]
                
                # ⭐ DETERMINAR SE O USUÁRIO LOGADO É O AUTOR
                is_owner = (usuario_conclusao == usuario_logado)
                
            elif usuario_filtro and is_admin:
                query = text("""
                    SELECT id, usuario_nome, conclusao, created_at
                    FROM conclusoes_auditoria
                    WHERE auditoria_id = :auditoria_id 
                    AND area_id = :area_id 
                    AND usuario_nome = :usuario_filtro
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = conn.execute(query, {
                    'auditoria_id': auditoria_id,
                    'area_id': area_id,
                    'usuario_filtro': usuario_filtro
                }).fetchone()
                
                if not result:
                    return jsonify({'error': f'Nenhuma conclusão encontrada para {usuario_filtro}'}), 404
                
                usuario_conclusao = result[1]
                texto_conclusao = result[2]
                data_criacao = result[3]
                
                # ⭐ ADMIN BAIXANDO CONCLUSÃO DE OUTRO
                is_owner = False
                
            else:
                query = text("""
                    SELECT id, usuario_nome, conclusao, created_at
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
                    'usuario_nome': usuario_logado
                }).fetchone()
                
                if not result and conclusao_texto:
                    usuario_conclusao = usuario_logado
                    texto_conclusao = conclusao_texto
                    is_owner = True
                elif not result:
                    return jsonify({'error': 'Nenhuma conclusão encontrada para este usuário'}), 404
                else:
                    usuario_conclusao = result[1]
                    texto_conclusao = result[2]
                    data_criacao = result[3]
                    is_owner = True  # ⭐ É O PRÓPRIO USUÁRIO
            
            print(f"📌 is_owner: {is_owner} (usuário logado: {usuario_logado}, autor: {usuario_conclusao})")
            
            # Buscar dados da área
            query_area = text("""
                SELECT nome_area, gestor, cargo, loc_unidade
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area_info:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0] or 'Área não identificada'
            gestor = area_info[1] or 'Não informado'
            cargo = area_info[2] or 'Não informado'
            unidade = area_info[3] or ''
            
            # Buscar dados da auditoria
            query_auditoria = text("""
                SELECT codigo_auditoria, titulo
                FROM auditorias
                WHERE id = :auditoria_id
            """)
            auditoria_info = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
            
            codigo_auditoria = auditoria_info[0] if auditoria_info else 'N/A'
            titulo_auditoria = auditoria_info[1] if auditoria_info else 'Auditoria'
        
        # ============================================================
        # 2. GERAR O PDF
        # ============================================================
        print(f"📄 Gerando PDF para {usuario_conclusao} (is_owner={is_owner})")
        
        pdf_bytes = gerar_pdf_conclusao(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            unidade=unidade,
            codigo_auditoria=codigo_auditoria,
            titulo_auditoria=titulo_auditoria,
            conclusao=texto_conclusao,
            orientacao=orientacao,
            usuario_nome=usuario_logado,
            usuario_conclusao=usuario_conclusao,
            is_owner=is_owner  # ⭐ PASSA O FLAG
        )
        
        print(f"✅ PDF gerado! Tamanho: {len(pdf_bytes)} bytes")
        
        # Nome do arquivo
        TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
        data_atual = datetime.now(TZ_BRASILIA).strftime('%Y%m%d_%H%M')
        
        # ⭐ NOME DO ARQUIVO COM INDICAÇÃO DE VALIDADE
        if is_owner:
            nome_arquivo = f"relatorio_conclusao_{usuario_conclusao.replace(' ', '_')}_assinado_{data_atual}.pdf"
        else:
            nome_arquivo = f"relatorio_conclusao_{usuario_conclusao.replace(' ', '_')}_sem_validade_{data_atual}.pdf"
        
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