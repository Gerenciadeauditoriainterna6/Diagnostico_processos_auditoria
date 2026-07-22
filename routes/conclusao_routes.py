from flask import request, jsonify, session
from database import engine
from sqlalchemy import text
from . import conclusao_bp
import json
from utils.verificar_responsavel_auditoria import verificar_responsavel_auditoria, verificar_administrador

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
    Salva ou atualiza a conclusão da auditoria (APENAS UMA POR AUDITORIA)
    """
    from database import engine
    from sqlalchemy import text
    from flask import session
    import json
    
    data = request.json
    auditoria_id = data.get('auditoria_id')
    area_id = data.get('area_id')
    
    if not auditoria_id or not area_id:
        return jsonify({'success': False, 'error': 'Auditoria e área são obrigatórios'}), 400
    
    usuario_nome = session.get('usuario_nome', '')
    
    # ⭐ VERIFICAR SE O USUÁRIO É RESPONSÁVEL OU ADMIN
    if not verificar_responsavel_auditoria(auditoria_id, usuario_nome):
        return jsonify({
            'success': False, 
            'error': 'Apenas administradores ou responsáveis pela auditoria podem salvar a conclusão'
        }), 403
    
    conclusao = data.get('conclusao', '').strip()
    forca = data.get('forca', '').strip()
    fraqueza = data.get('fraqueza', '').strip()
    oportunidades = data.get('oportunidades', '').strip()
    ameacas = data.get('ameacas', '').strip()
    
    # ⭐ PELO MENOS UM CAMPO DEVE ESTAR PREENCHIDO
    if not any([conclusao, forca, fraqueza, oportunidades, ameacas]):
        return jsonify({
            'success': False, 
            'error': 'Preencha pelo menos um campo da conclusão'
        }), 400
    
    try:
        with engine.connect() as conn:
            # ⭐ VERIFICAR SE JÁ EXISTE UMA CONCLUSÃO PARA ESTA AUDITORIA
            check_query = text("""
                SELECT id FROM conclusoes_auditoria 
                WHERE auditoria_id = :auditoria_id 
                AND area_id = :area_id
            """)
            existing = conn.execute(check_query, {
                'auditoria_id': auditoria_id,
                'area_id': area_id
            }).fetchone()
            
            if existing:
                # ⭐ ATUALIZAR A CONCLUSÃO EXISTENTE
                update_query = text("""
                    UPDATE conclusoes_auditoria 
                    SET conclusao = jsonb_build_object(
                        'conclusao', :conclusao,
                        'forca', :forca,
                        'fraqueza', :fraqueza,
                        'oportunidades', :oportunidades,
                        'ameacas', :ameacas
                    ),
                    usuario_nome = :usuario_nome,  -- ⭐ QUEM EDITOU POR ÚLTIMO
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """)
                conn.execute(update_query, {
                    'id': existing[0],
                    'conclusao': conclusao,
                    'forca': forca,
                    'fraqueza': fraqueza,
                    'oportunidades': oportunidades,
                    'ameacas': ameacas,
                    'usuario_nome': usuario_nome
                })
                mensagem = 'Conclusão atualizada com sucesso!'
                acao = 'atualizada'
                
            else:
                # ⭐ CRIAR A PRIMEIRA CONCLUSÃO
                insert_query = text("""
                    INSERT INTO conclusoes_auditoria (
                        auditoria_id, area_id, usuario_nome, conclusao
                    ) VALUES (
                        :auditoria_id, :area_id, :usuario_nome, 
                        jsonb_build_object(
                            'conclusao', :conclusao,
                            'forca', :forca,
                            'fraqueza', :fraqueza,
                            'oportunidades', :oportunidades,
                            'ameacas', :ameacas
                        )
                    )
                """)
                conn.execute(insert_query, {
                    'auditoria_id': auditoria_id,
                    'area_id': area_id,
                    'usuario_nome': usuario_nome,
                    'conclusao': conclusao,
                    'forca': forca,
                    'fraqueza': fraqueza,
                    'oportunidades': oportunidades,
                    'ameacas': ameacas
                })
                mensagem = 'Conclusão salva com sucesso!'
                acao = 'salva'
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': mensagem,
                'acao': acao
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar conclusão: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@conclusao_bp.route('/conclusoes/buscar', methods=['GET'])
def api_buscar_conclusao():
    """
    Busca a conclusão da auditoria (APENAS UMA POR AUDITORIA)
    """
    auditoria_id = request.args.get('auditoria_id')
    area_id = request.args.get('area_id')
    
    if not auditoria_id or not area_id:
        return jsonify({'success': False, 'error': 'Auditoria e área são obrigatórios'}), 400
    
    usuario_nome = session.get('usuario_nome', '')
    
    # ⭐ VERIFICAR SE O USUÁRIO É RESPONSÁVEL OU ADMIN
    if not verificar_responsavel_auditoria(auditoria_id, usuario_nome):
        return jsonify({
            'success': False, 
            'error': 'Apenas administradores ou responsáveis pela auditoria podem visualizar a conclusão'
        }), 403
    
    try:
        with engine.connect() as conn:
            # ⭐ BUSCAR A ÚNICA CONCLUSÃO DA AUDITORIA
            query = text("""
                SELECT id, usuario_nome, conclusao, created_at, updated_at
                FROM conclusoes_auditoria
                WHERE auditoria_id = :auditoria_id 
                AND area_id = :area_id
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'area_id': area_id
            }).fetchone()
            
            if not result:
                return jsonify({'success': True, 'conclusao': None})
            
            conclusao_id = result[0]
            usuario_nome_db = result[1]
            conclusao_data = result[2]
            created_at = result[3]
            updated_at = result[4]
            
            # ⭐ PARSE DO JSON
            if isinstance(conclusao_data, str):
                try:
                    conclusao_data = json.loads(conclusao_data)
                except:
                    conclusao_data = {'conclusao': conclusao_data}
            elif not isinstance(conclusao_data, dict):
                conclusao_data = {'conclusao': str(conclusao_data)}
            
            # ⭐ GARANTIR TODOS OS CAMPOS
            conclusao_data.setdefault('conclusao', '')
            conclusao_data.setdefault('forca', '')
            conclusao_data.setdefault('fraqueza', '')
            conclusao_data.setdefault('oportunidades', '')
            conclusao_data.setdefault('ameacas', '')
            
            return jsonify({
                'success': True,
                'conclusao': {
                    'id': conclusao_id,
                    'usuario_nome': usuario_nome_db,
                    'texto': conclusao_data,
                    'created_at': created_at.strftime('%d/%m/%Y %H:%M') if created_at else '',
                    'updated_at': updated_at.strftime('%d/%m/%Y %H:%M') if updated_at else ''
                }
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar conclusão: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@conclusao_bp.route('/conclusoes/historico', methods=['GET'])
def api_historico_conclusoes():
    """
    Busca o histórico de edições da conclusão da auditoria
    """
    auditoria_id = request.args.get('auditoria_id')
    area_id = request.args.get('area_id')
    
    if not auditoria_id or not area_id:
        return jsonify({'success': False, 'error': 'Auditoria e área são obrigatórios'}), 400
    
    usuario_nome = session.get('usuario_nome', '')
    
    # ⭐ VERIFICAR SE O USUÁRIO É RESPONSÁVEL OU ADMIN
    if not verificar_responsavel_auditoria(auditoria_id, usuario_nome):
        return jsonify({
            'success': False, 
            'error': 'Apenas administradores ou responsáveis pela auditoria podem ver o histórico'
        }), 403
    
    try:
        with engine.connect() as conn:
            # ⭐ BUSCAR A CONCLUSÃO (COM HISTÓRICO)
            # Como não temos uma tabela de histórico separada, vamos mostrar a conclusão atual
            query = text("""
                SELECT id, usuario_nome, conclusao, created_at, updated_at
                FROM conclusoes_auditoria
                WHERE auditoria_id = :auditoria_id 
                AND area_id = :area_id
                ORDER BY updated_at DESC
            """)
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'area_id': area_id
            }).fetchall()
            
            conclusoes = []
            for row in result:
                conclusao_data = row[2]
                if isinstance(conclusao_data, str):
                    try:
                        conclusao_data = json.loads(conclusao_data)
                    except:
                        conclusao_data = {'conclusao': conclusao_data}
                elif not isinstance(conclusao_data, dict):
                    conclusao_data = {'conclusao': str(conclusao_data)}
                
                conclusoes.append({
                    'id': row[0],
                    'usuario_nome': row[1],
                    'conclusao': conclusao_data,
                    'created_at': row[3].strftime('%d/%m/%Y %H:%M') if row[3] else '',
                    'updated_at': row[4].strftime('%d/%m/%Y %H:%M') if row[4] else ''
                })
            
            return jsonify({
                'success': True,
                'conclusoes': conclusoes,
                'usuario_logado': usuario_nome,
                'is_admin': verificar_administrador(usuario_nome)
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@conclusao_bp.route('/relatorios/gerar-conclusao', methods=['POST'])
def gerar_relatorio_conclusao():
    """
    Gera o relatório de conclusão em PDF com suporte a SWOT
    """
    from flask import session, make_response
    from logic import gerar_pdf_conclusao
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import traceback
    import json
    
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
        
        if not area_id or not auditoria_id:
            return jsonify({'error': 'Área e auditoria são obrigatórios'}), 400
        
        usuario_nome = session.get('usuario_nome', '')
        
        # ⭐ VERIFICAR SE O USUÁRIO É RESPONSÁVEL
        if not verificar_responsavel_auditoria(auditoria_id, usuario_nome):
            return jsonify({'error': 'Apenas responsáveis pela auditoria podem baixar o relatório'}), 403
        
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
                conclusao_data = result[2]
                data_criacao = result[3]
                
                # ⭐ PARSE DO JSON
                if isinstance(conclusao_data, str):
                    try:
                        conclusao_data = json.loads(conclusao_data)
                    except:
                        conclusao_data = {'conclusao': conclusao_data}
                elif not isinstance(conclusao_data, dict):
                    conclusao_data = {'conclusao': str(conclusao_data)}
                
                # ⭐ GARANTIR TODOS OS CAMPOS
                conclusao_data.setdefault('conclusao', '')
                conclusao_data.setdefault('forca', '')
                conclusao_data.setdefault('fraqueza', '')
                conclusao_data.setdefault('oportunidades', '')
                conclusao_data.setdefault('ameacas', '')
                
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
                conclusao_data = result[2]
                data_criacao = result[3]
                
                if isinstance(conclusao_data, str):
                    try:
                        conclusao_data = json.loads(conclusao_data)
                    except:
                        conclusao_data = {'conclusao': conclusao_data}
                elif not isinstance(conclusao_data, dict):
                    conclusao_data = {'conclusao': str(conclusao_data)}
                
                conclusao_data.setdefault('conclusao', '')
                conclusao_data.setdefault('forca', '')
                conclusao_data.setdefault('fraqueza', '')
                conclusao_data.setdefault('oportunidades', '')
                conclusao_data.setdefault('ameacas', '')
                
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
                    conclusao_data = {
                        'conclusao': conclusao_texto,
                        'forca': '',
                        'fraqueza': '',
                        'oportunidades': '',
                        'ameacas': ''
                    }
                    is_owner = True
                elif not result:
                    return jsonify({'error': 'Nenhuma conclusão encontrada para este usuário'}), 404
                else:
                    usuario_conclusao = result[1]
                    conclusao_data = result[2]
                    data_criacao = result[3]
                    
                    if isinstance(conclusao_data, str):
                        try:
                            conclusao_data = json.loads(conclusao_data)
                        except:
                            conclusao_data = {'conclusao': conclusao_data}
                    elif not isinstance(conclusao_data, dict):
                        conclusao_data = {'conclusao': str(conclusao_data)}
                    
                    conclusao_data.setdefault('conclusao', '')
                    conclusao_data.setdefault('forca', '')
                    conclusao_data.setdefault('fraqueza', '')
                    conclusao_data.setdefault('oportunidades', '')
                    conclusao_data.setdefault('ameacas', '')
                    
                    is_owner = True
            
            print(f"📌 is_owner: {is_owner} (usuário logado: {usuario_logado}, autor: {usuario_conclusao})")
            print(f"📊 Dados da conclusão: {conclusao_data}")
            
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
            conclusao_data=conclusao_data,  # ⭐ PASSA O DICT COMPLETO
            orientacao=orientacao,
            usuario_nome=usuario_logado,
        )
        
        print(f"✅ PDF gerado! Tamanho: {len(pdf_bytes)} bytes")
        
        # Nome do arquivo
        TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
        data_atual = datetime.now(TZ_BRASILIA).strftime('%Y%m%d_%H%M')
        
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