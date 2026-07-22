print("🔵 Arquivo analise_routes.py CARREGADO!")

from flask import Blueprint, request, jsonify, session, redirect, send_file
from services.analise_service import AnaliseService
from utils.storage_utils import upload_evidencia_storage  # ⭐ IMPORTAR FUNÇÃO DE UPLOAD
from database import engine
from sqlalchemy import text
import base64
import io
from urllib.parse import urlparse, unquote
import re
from . import analise_bp

# ============================================================
# ====== 1. APIs DE LISTAGEM (GET) ======
# ============================================================

@analise_bp.route('/analises-criticas-por-processo', methods=['GET'])
def api_analises_criticas_por_processo():
    """Retorna as análises críticas do auditado para um processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    try:
        analises = AnaliseService.listar_por_processo(
            processo_id=int(processo_id),
            tipo='auditado'
        )
        return jsonify({'success': True, 'analises': analises})
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analise_bp.route('/analises-auditor/por-processo', methods=['GET'])
def api_analises_auditor_por_processo():
    """Retorna as análises do auditor para um processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    try:
        analises = AnaliseService.listar_por_processo(
            processo_id=int(processo_id),
            tipo='auditor'
        )
        return jsonify({'success': True, 'analises': analises})
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ====== 2. APIs DE CRIAÇÃO (POST) ======
# ============================================================

@analise_bp.route('/analise-auditor/salvar', methods=['POST'])
def api_analise_auditor_salvar():
    """Salva uma nova análise do auditor com evidência"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # ⭐ EXTRAIR DADOS (suporta FormData e JSON)
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form
        evidencia_file = request.files.get('evidencia')
    else:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        evidencia_file = None
    
    # Validar campos obrigatórios
    if not data.get('processo_id'):
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    if not data.get('analise_critica'):
        return jsonify({'success': False, 'error': 'Análise Crítica é obrigatória'}), 400
    
    # ⭐ MONTAR PAYLOAD
    payload = {
        'processo_id': int(data.get('processo_id')),
        'analise_critica': data.get('analise_critica', ''),
        'sugestao_melhoria': data.get('sugestao_melhoria', ''),
        'necessidade_implantacao': data.get('necessidade_implantacao', ''),
        'ganho_previsto': data.get('ganho_previsto', ''),
        'observacoes': data.get('observacoes', ''),
        'tipo': 'auditor',
        'categoria': 'geral',
        'status': 'ativo',
        'created_by': session.get('usuario_nome', 'Sistema')
    }
    
    # Processar sugestao_sera_implantada
    sugestao_str = data.get('sugestao_sera_implantada')
    if sugestao_str == 'true':
        payload['sugestao_sera_implantada'] = True
    elif sugestao_str == 'false':
        payload['sugestao_sera_implantada'] = False
    else:
        payload['sugestao_sera_implantada'] = None
    
    # Plano de ação (se houver)
    if payload.get('sugestao_sera_implantada') is True:
        payload['plano_acao'] = data.get('plano_acao', '')
        payload['responsavel_implantacao'] = data.get('responsavel_implantacao', '')
        payload['data_inicio_prevista'] = data.get('data_inicio_prevista')
        payload['data_conclusao_prevista'] = data.get('data_conclusao_prevista')
    
    try:
        # ⭐ 1. SALVAR ANÁLISE USANDO O SERVICE
        novo_id = AnaliseService.criar(payload)
        
        # ⭐ 2. PROCESSAR EVIDÊNCIA (se houver)
        evidencia_url = None
        evidencia_nome = data.get('evidencia_nome')
        
        if evidencia_file and evidencia_nome:
            try:
                # Ler arquivo
                if hasattr(evidencia_file, 'read'):
                    evidencia_file.seek(0)
                    evidencia_bytes = evidencia_file.read()
                else:
                    evidencia_file.seek(0)
                    evidencia_bytes = evidencia_file.read()
                
                # Converter para base64
                evidencia_base64 = base64.b64encode(evidencia_bytes).decode('utf-8')
                
                # ⭐ CHAMAR UPLOAD
                evidencia_url = upload_evidencia_storage(
                    novo_id, 
                    evidencia_base64, 
                    evidencia_nome
                )
                
                if evidencia_url:
                    AnaliseService.atualizar_evidencia(novo_id, evidencia_url, evidencia_nome)
                    print(f"📎 Evidência salva: {evidencia_nome}")
                    
            except Exception as e:
                print(f"⚠️ Erro ao salvar evidência: {e}")
        
        return jsonify({
            'success': True,
            'id': novo_id,
            'message': 'Análise salva com sucesso',
            'evidencia_url': evidencia_url
        })
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analise_bp.route('/analise-auditado/salvar', methods=['POST'])
def api_analise_auditado_salvar():
    """Salva uma nova análise do auditado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
    
    # Validar campos obrigatórios
    if not data.get('processo_id'):
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    if not data.get('etapa_id'):
        return jsonify({'success': False, 'error': 'etapa_id é obrigatório'}), 400
    if not data.get('categoria'):
        return jsonify({'success': False, 'error': 'categoria é obrigatória'}), 400
    if not data.get('analise_critica'):
        return jsonify({'success': False, 'error': 'Análise Crítica é obrigatória'}), 400
    
    # ⭐ MONTAR PAYLOAD
    payload = {
        'processo_id': int(data.get('processo_id')),
        'etapa_id': int(data.get('etapa_id')),
        'categoria': data.get('categoria'),
        'analise_critica': data.get('analise_critica', ''),
        'sugestao_melhoria': data.get('sugestao_melhoria', ''),
        'necessidade_implantacao': data.get('necessidade_implantacao', ''),
        'ganho_previsto': data.get('ganho_previsto', ''),
        'observacoes': data.get('observacoes', ''),
        'tipo': 'auditado',
        'status': 'ativo',
        'created_by': session.get('usuario_nome', 'Sistema')
    }
    
    # Processar sugestao_sera_implantada
    sugestao_str = data.get('sugestao_sera_implantada')
    if sugestao_str == 'true':
        payload['sugestao_sera_implantada'] = True
    elif sugestao_str == 'false':
        payload['sugestao_sera_implantada'] = False
    else:
        payload['sugestao_sera_implantada'] = None
    
    # Plano de ação (se houver)
    if payload.get('sugestao_sera_implantada') is True:
        payload['plano_acao'] = data.get('plano_acao', '')
        payload['responsavel_implantacao'] = data.get('responsavel_implantacao', '')
        payload['data_inicio_prevista'] = data.get('data_inicio_prevista')
        payload['data_conclusao_prevista'] = data.get('data_conclusao_prevista')
        
        # Processar evidência base64 (se veio)
        evidencia_base64 = data.get('evidencia_base64')
        evidencia_nome = data.get('evidencia_nome')
        
        if evidencia_base64 and evidencia_nome:
            try:
                evidencia_url = upload_evidencia_storage(
                    None,  # ID será gerado depois
                    evidencia_base64,
                    evidencia_nome
                )
                payload['evidencia_url'] = evidencia_url
                payload['evidencia_nome'] = evidencia_nome
            except Exception as e:
                print(f"⚠️ Erro ao processar evidência: {e}")
    
    try:
        novo_id = AnaliseService.criar(payload)
        return jsonify({
            'success': True,
            'id': novo_id,
            'message': 'Análise salva com sucesso'
        })
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ====== 3. APIs DE ATUALIZAÇÃO (PUT) ======
# ============================================================

@analise_bp.route('/analise-auditor/<int:analise_id>', methods=['PUT'])
def api_analise_auditor_atualizar(analise_id):
    """Atualiza uma análise do auditor existente"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # ⭐ EXTRAIR DADOS (suporta FormData e JSON)
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form
        evidencia_file = request.files.get('evidencia')
    else:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        evidencia_file = None
    
    # ⭐ EXTRAIR CAMPOS PARA UPDATE
    dados_para_atualizar = {}
    campos_permitidos = ['analise_critica', 'sugestao_melhoria', 'necessidade_implantacao',
                        'ganho_previsto', 'observacoes', 'status', 'sugestao_sera_implantada', 'plano_acao_id']  # ⭐ ADICIONADO
    
    for campo in campos_permitidos:
        if campo in data:
            dados_para_atualizar[campo] = data.get(campo)
    
    # ⭐ LOG PARA VER O QUE ESTÁ CHEGANDO
    print("=" * 50)
    print("📥 Dados para atualizar:")
    print(f"  sugestao_sera_implantada: {dados_para_atualizar.get('sugestao_sera_implantada')}")
    print(f"  tipo: {type(dados_para_atualizar.get('sugestao_sera_implantada'))}")
    print("=" * 50)
    
    if not dados_para_atualizar:
        return jsonify({'success': False, 'error': 'Nenhum campo válido para atualizar'}), 400
    
    try:
        # ⭐ 1. ATUALIZAR ANÁLISE USANDO O SERVICE
        sucesso = AnaliseService.atualizar(analise_id, dados_para_atualizar)
        
        if not sucesso:
            return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
        
        # ⭐ 2. PROCESSAR EVIDÊNCIA (se houver)
        evidencia_nome = data.get('evidencia_nome')
        if evidencia_file and evidencia_nome:
            try:
                # Ler arquivo
                if hasattr(evidencia_file, 'read'):
                    evidencia_file.seek(0)
                    evidencia_bytes = evidencia_file.read()
                else:
                    evidencia_file.seek(0)
                    evidencia_bytes = evidencia_file.read()
                
                evidencia_base64 = base64.b64encode(evidencia_bytes).decode('utf-8')
                evidencia_url = upload_evidencia_storage(analise_id, evidencia_base64, evidencia_nome)
                
                if evidencia_url:
                    AnaliseService.atualizar_evidencia(analise_id, evidencia_url, evidencia_nome)
                    print(f"📎 Evidência atualizada: {evidencia_nome}")
                    
            except Exception as e:
                print(f"⚠️ Erro ao atualizar evidência: {e}")
        
        # ⭐ 3. REMOVER EVIDÊNCIA (se solicitado)
        if data.get('remover_evidencia') == 'true':
            AnaliseService.atualizar_evidencia(analise_id, None, None)
            print(f"🗑️ Evidência removida da análise {analise_id}")
        
        return jsonify({'success': True, 'message': 'Análise atualizada com sucesso'})
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analise_bp.route('/analise-auditado/<int:analise_id>', methods=['PUT'])
def api_analise_auditado_atualizar(analise_id):
    """Atualiza uma análise do auditado existente"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
    
    # ⭐ EXTRAIR CAMPOS PARA UPDATE
    dados_para_atualizar = {}
    campos_permitidos = ['analise_critica', 'sugestao_melhoria', 'necessidade_implantacao',
                        'ganho_previsto', 'observacoes', 'status']
    
    for campo in campos_permitidos:
        if campo in data:
            dados_para_atualizar[campo] = data.get(campo)
    
    # Processar sugestao_sera_implantada
    sugestao_str = data.get('sugestao_sera_implantada')
    if sugestao_str == 'true':
        dados_para_atualizar['sugestao_sera_implantada'] = True
    elif sugestao_str == 'false':
        dados_para_atualizar['sugestao_sera_implantada'] = False
    else:
        dados_para_atualizar['sugestao_sera_implantada'] = None
    
    if not dados_para_atualizar:
        return jsonify({'success': False, 'error': 'Nenhum campo válido para atualizar'}), 400
    
    try:
        sucesso = AnaliseService.atualizar(analise_id, dados_para_atualizar)
        
        if not sucesso:
            return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
        
        # ⭐ Processar evidência em base64 (se veio)
        evidencia_base64 = data.get('evidencia_base64')
        evidencia_nome = data.get('evidencia_nome')
        
        if evidencia_base64 and evidencia_nome:
            try:
                evidencia_url = upload_evidencia_storage(analise_id, evidencia_base64, evidencia_nome)
                if evidencia_url:
                    AnaliseService.atualizar_evidencia(analise_id, evidencia_url, evidencia_nome)
                    print(f"📎 Evidência atualizada: {evidencia_nome}")
            except Exception as e:
                print(f"⚠️ Erro ao atualizar evidência: {e}")
        
        # ⭐ Remover evidência (se solicitado)
        if data.get('remover_evidencia') == 'true':
            AnaliseService.atualizar_evidencia(analise_id, None, None)
            print(f"🗑️ Evidência removida da análise {analise_id}")
        
        return jsonify({'success': True, 'message': 'Análise atualizada com sucesso'})
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ====== 4. APIs DE DOWNLOAD ======
# ============================================================

@analise_bp.route('/analise-auditado/<int:analise_id>/evidencia', methods=['GET'])
def api_analise_auditado_evidencia(analise_id):
    """Baixa a evidência de uma análise do auditado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT evidencia_url, evidencia_nome
                FROM analises_criticas
                WHERE id = :id AND tipo = 'auditado'
            """)
            result = conn.execute(query, {'id': analise_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Evidência não encontrada'}), 404
            
            evidencia_url = result[0]
            evidencia_nome = result[1] or 'evidencia.pdf'
            
            # Extrair caminho para regenerar assinatura
            parsed = urlparse(evidencia_url)
            path_parts = parsed.path.split('/')
            
            caminho = None
            for i, part in enumerate(path_parts):
                if part == 'evidencia_analises_auditado' and i + 1 < len(path_parts):
                    caminho = '/'.join(path_parts[i+1:])
                    if '?' in caminho:
                        caminho = caminho.split('?')[0]
                    break
            
            if caminho:
                from supabase_client import SupabaseClient
                supabase = SupabaseClient.get_instance()
                
                url_assinada = supabase.storage.from_('evidencia_analises_auditado').create_signed_url(
                    path=caminho,
                    expires_in=604800
                )
                
                update_query = text("""
                    UPDATE analises_criticas 
                    SET evidencia_url = :evidencia_url
                    WHERE id = :id
                """)
                conn.execute(update_query, {
                    'evidencia_url': url_assinada['signedURL'],
                    'id': analise_id
                })
                conn.commit()
                
                return redirect(url_assinada['signedURL'])
            
            return redirect(evidencia_url)
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analise_bp.route('/analise-auditor/evidencia/<int:evidencia_id>/download')
def baixar_evidencia_analise_auditor(evidencia_id):
    """Baixa a evidência do Storage"""
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT evidencia_url, evidencia_nome 
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': evidencia_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'error': 'Evidência não encontrada'}), 404
            
            evidencia_url = result[0]
            evidencia_nome = result[1] or 'evidencia.pdf'
        
        # Extrair caminho
        match = re.search(r'/sign/[^/]+/(.+)', evidencia_url)
        if not match:
            return jsonify({'error': 'Não foi possível extrair o caminho do arquivo'}), 400
        
        file_path = match.group(1).split('?')[0]
        file_path = unquote(file_path)
        
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        response = supabase.storage.from_('evidencia_analises_auditor').download(file_path)
        
        if response:
            return send_file(
                io.BytesIO(response),
                download_name=evidencia_nome,
                mimetype='application/pdf',
                as_attachment=True
            )
        else:
            return jsonify({'error': 'Erro ao baixar arquivo'}), 500
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'error': str(e)}), 500


@analise_bp.route('/analise-auditor/<int:analise_id>/anexo')
def api_analise_auditor_anexo(analise_id):
    """Baixa o anexo PDF de uma análise do auditor"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            
            cursor.execute("""
                SELECT anexo_base64, anexo_nome 
                FROM analises_criticas 
                WHERE id = %s AND tipo = 'auditor'
            """, (analise_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row or not row[0]:
                return jsonify({'error': 'Arquivo não encontrado'}), 404
            
            anexo_bytes = row[0]
            anexo_nome = row[1] or f'anexo_analise_{analise_id}.pdf'
            
            if len(anexo_bytes) < 100:
                return jsonify({'error': 'Arquivo muito pequeno (corrompido)'}), 400
            
            return send_file(
                io.BytesIO(anexo_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=anexo_nome
            )
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'error': str(e)}), 500


@analise_bp.route('/analise-auditado/<int:analise_id>/anexo')
def api_analise_auditado_anexo(analise_id):
    """Baixa o anexo PDF de uma análise do auditado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT anexo_base64, anexo_nome 
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditado'
            """), {'id': analise_id})
            row = result.fetchone()
            
            if not row or not row[0]:
                return jsonify({'error': 'Arquivo não encontrado'}), 404
            
            anexo_bytes = bytes(row[0]) if hasattr(row[0], '__iter__') else row[0]
            anexo_nome = row[1] or f'anexo_auditado_{analise_id}.pdf'
            
            return send_file(
                io.BytesIO(anexo_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=anexo_nome
            )
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# ====== 5. API DE CONFIRMAÇÃO DE IMPLANTAÇÃO ======
# ============================================================

@analise_bp.route('/analise-auditor/<int:analise_id>/confirmar-implantacao', methods=['PUT'])
def api_confirmar_implantacao_auditor(analise_id):
    """Confirma a implantação de uma análise do auditor"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
    
    plano_de_acao_implantado = data.get('plano_de_acao_implantado')
    data_execucao_plano_acao = data.get('data_execucao_plano_acao')
    comentario = data.get('comentario_implantacao')
    
    if data_execucao_plano_acao is None:
        return jsonify({'success': False, 'error': 'Data de implantação é obrigatória'}), 400
    
    try:
        sucesso = AnaliseService.confirmar_implantacao(
            analise_id,
            plano_de_acao_implantado,
            data_execucao_plano_acao,
            comentario
        )
        
        if sucesso:
            return jsonify({'success': True, 'message': 'Implantação confirmada com sucesso'})
        else:
            return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analise_bp.route('/analise-auditado/<int:analise_id>/confirmar-implantacao', methods=['PUT'])
def api_confirmar_implantacao_auditado(analise_id):
    """Confirma a implantação de uma análise do auditado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
    
    plano_de_acao_implantado = data.get('plano_de_acao_implantado')
    data_execucao_plano_acao = data.get('data_execucao_plano_acao')
    comentario = data.get('comentario_implantacao')
    
    if data_execucao_plano_acao is None:
        return jsonify({'success': False, 'error': 'Data de implantação é obrigatória'}), 400
    
    try:
        sucesso = AnaliseService.confirmar_implantacao(
            analise_id,
            plano_de_acao_implantado,
            data_execucao_plano_acao,
            comentario
        )
        
        if sucesso:
            return jsonify({'success': True, 'message': 'Implantação confirmada com sucesso'})
        else:
            return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500