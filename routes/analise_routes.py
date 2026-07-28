print("🔵 Arquivo analise_routes.py CARREGADO!")

from flask import Blueprint, request, jsonify, session, redirect, send_file
from services.analise_service import AnaliseService
from database import engine
from sqlalchemy import text
from utils import upload_arquivo_storage, excluir_arquivo_storage, extrair_caminho_da_url
import base64
import uuid
from datetime import datetime
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
                
                # ⭐ CONSTRUIR CAMINHO PARA AUDITOR
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                
                # Limpar nome
                nome_limpo = ''.join(c for c in evidencia_nome if c.isalnum() or c in ' ._-')
                nome_limpo = nome_limpo.replace(' ', '_')
                
                # Caminho: analises_auditor/analise_{id}/{timestamp}_{uuid}_{nome}.pdf
                caminho = f"analises_auditor/analise_{novo_id}/{timestamp}_{unique_id}_{nome_limpo}.pdf"
                
                # ⭐ CHAMAR FUNÇÃO GENÉRICA
                evidencia_url = upload_arquivo_storage(
                    arquivo=evidencia_bytes,
                    caminho_destino=caminho,
                    bucket_name="evidencia_analises_auditor",
                    content_type="application/pdf"
                )
                
                if evidencia_url:
                    AnaliseService.atualizar_evidencia(novo_id, caminho, evidencia_nome)
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
                # ⭐ DECODIFICAR BASE64
                if ',' in evidencia_base64:
                    evidencia_base64 = evidencia_base64.split(',')[1]
                file_bytes = base64.b64decode(evidencia_base64)
                
                # ⭐ CONSTRUIR CAMINHO PARA AUDITADO
                # (ID ainda não existe, mas o service vai gerar)
                # Vamos usar um ID temporário e depois atualizar
                analise_id_temp = int(datetime.now().timestamp())
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                
                # Limpar nome
                nome_limpo = ''.join(c for c in evidencia_nome if c.isalnum() or c in ' ._-')
                nome_limpo = nome_limpo.replace(' ', '_')
                
                # Caminho: analises_auditado/analise_{id}/etapa_{etapa_id}/{timestamp}_{uuid}_{nome}.pdf
                caminho = f"analises_auditado/analise_id_{analise_id_temp}/etapa_id_{payload['etapa_id']}/{timestamp}_{unique_id}_{nome_limpo}.pdf"
                
                # ⭐ CHAMAR FUNÇÃO GENÉRICA
                evidencia_url = upload_arquivo_storage(
                    arquivo=file_bytes,
                    caminho_destino=caminho,
                    bucket_name="evidencia_analises_auditado",
                    content_type="application/pdf"
                )
                
                if evidencia_url:
                    payload['evidencia_url'] = caminho  
                    payload['evidencia_nome'] = evidencia_nome
                    payload['_caminho_evidencia'] = caminho  
                    payload['_analise_id_temp'] = analise_id_temp
                    
            except Exception as e:
                print(f"⚠️ Erro ao processar evidência: {e}")
    
    try:
        novo_id = AnaliseService.criar(payload)
        
        if payload.get('_caminho_evidencia') and payload.get('_analise_id_temp'):
            caminho_antigo = payload['_caminho_evidencia']
            analise_id_temp = payload['_analise_id_temp']
            
            caminho_novo = caminho_antigo.replace(f"analise_{analise_id_temp}", f"analise_{novo_id}")
            
            try:
                from utils import baixar_arquivo_storage, excluir_arquivo_storage
                
                file_bytes = baixar_arquivo_storage(caminho_antigo, "evidencia_analises_auditado")
                if file_bytes:
                    # ⭐ FAZER UPLOAD COM O NOVO CAMINHO
                    nova_url = upload_arquivo_storage(
                        arquivo=file_bytes,
                        caminho_destino=caminho_novo,
                        bucket_name="evidencia_analises_auditado",
                        content_type="application/pdf"
                    )
                    if nova_url:
                        # ⭐ SALVAR APENAS O CAMINHO (NÃO A URL)
                        AnaliseService.atualizar_evidencia(novo_id, caminho_novo, evidencia_nome)  # ← Usar caminho_novo
                        excluir_arquivo_storage(caminho_antigo, "evidencia_analises_auditado")
                        print(f"📎 Evidência renomeada para: {caminho_novo}")
            except Exception as e:
                print(f"⚠️ Erro ao renomear evidência: {e}")
        
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
                        'ganho_previsto', 'observacoes', 'status', 'sugestao_sera_implantada', 'plano_acao_id']
    
    for campo in campos_permitidos:
        if campo in data:
            dados_para_atualizar[campo] = data.get(campo)
    
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
                
                # ⭐ CONSTRUIR CAMINHO PARA AUDITOR
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                
                # Limpar nome
                nome_limpo = ''.join(c for c in evidencia_nome if c.isalnum() or c in ' ._-')
                nome_limpo = nome_limpo.replace(' ', '_')
                
                # Caminho: analises_auditor/analise_{id}/{timestamp}_{uuid}_{nome}.pdf
                caminho = f"analises_auditor/analise_{analise_id}/{timestamp}_{unique_id}_{nome_limpo}.pdf"
                
                # ⭐ CHAMAR FUNÇÃO GENÉRICA
                evidencia_url = upload_arquivo_storage(
                    arquivo=evidencia_bytes,
                    caminho_destino=caminho,
                    bucket_name="evidencia_analises_auditor",
                    content_type="application/pdf"
                )
                
                if evidencia_url:
                    AnaliseService.atualizar_evidencia(analise_id, caminho, evidencia_nome)
                    print(f"📎 Evidência atualizada: {evidencia_nome}")
                    
            except Exception as e:
                print(f"⚠️ Erro ao atualizar evidência: {e}")
        
        
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
                # ⭐ DECODIFICAR BASE64
                if ',' in evidencia_base64:
                    evidencia_base64 = evidencia_base64.split(',')[1]
                file_bytes = base64.b64decode(evidencia_base64)
                
                # ⭐ CONSTRUIR CAMINHO PARA AUDITADO
                # Precisamos buscar a etapa_id da análise
                analise = AnaliseService.buscar_por_id(analise_id)
                etapa_id = analise.get('etapa_id') if analise else None
                
                if not etapa_id:
                    print("⚠️ Etapa não encontrada para a análise")
                    return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                
                # Limpar nome
                nome_limpo = ''.join(c for c in evidencia_nome if c.isalnum() or c in ' ._-')
                nome_limpo = nome_limpo.replace(' ', '_')
                
                # Caminho: analises_auditado/analise_{id}/etapa_{etapa_id}/{timestamp}_{uuid}_{nome}.pdf
                caminho = f"analises_auditado/analise_id_{analise_id}/etapa_id_{etapa_id}/{timestamp}_{unique_id}_{nome_limpo}.pdf"
                
                # ⭐ CHAMAR FUNÇÃO GENÉRICA
                evidencia_url = upload_arquivo_storage(
                    arquivo=file_bytes,
                    caminho_destino=caminho,
                    bucket_name="evidencia_analises_auditado",
                    content_type="application/pdf"
                )
                
                if evidencia_url:
                    AnaliseService.atualizar_evidencia(analise_id, caminho, evidencia_nome)
                    print(f"📎 Evidência atualizada: {evidencia_nome}")
                    
            except Exception as e:
                print(f"⚠️ Erro ao atualizar evidência: {e}")
        
        
        return jsonify({'success': True, 'message': 'Análise atualizada com sucesso'})
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ====== 4. APIs DE DOWNLOAD ======
# ============================================================

@analise_bp.route('/analise-auditado/<int:analise_id>/evidencia', methods=['GET'])
def api_analise_auditado_evidencia(analise_id):
    """Baixa a evidência de uma análise do auditado diretamente do Storage"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        from database import engine
        from sqlalchemy import text
        from flask import send_file
        import io
        import re
        from urllib.parse import unquote
        
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
        
        print(f"📥 URL original: {evidencia_url}")
        
        # ⭐ SE FOR UM CAMINHO PURO (SEM HTTP), USAR DIRETAMENTE
        file_path = None
        if not evidencia_url.startswith('http'):
            file_path = evidencia_url
            print(f"📥 Caminho direto: {file_path}")
        else:
            # ⭐ EXTRAIR O CAMINHO DO ARQUIVO (URL COMPLETA)
            # Método 1: Extrair depois de "evidencia_analises_auditado/"
            if 'evidencia_analises_auditado/' in evidencia_url:
                partes = evidencia_url.split('evidencia_analises_auditado/')
                if len(partes) > 1:
                    file_path = partes[1].split('?')[0]
                    file_path = unquote(file_path)
                    print(f"📥 Caminho extraído (método 1): {file_path}")
            
            # Método 2: Usar regex para /object/...
            if not file_path:
                padrao = r'/object/(?:public|sign|authenticated)/[^/]+/(.+)'
                match = re.search(padrao, evidencia_url)
                if match:
                    file_path = match.group(1).split('?')[0]
                    file_path = unquote(file_path)
                    print(f"📥 Caminho extraído (método 2): {file_path}")
            
            # ⭐ SE O CAMINHO NÃO COMEÇAR COM "analises_auditado/", AJUSTAR
            if file_path and not file_path.startswith('analises_auditado/'):
                if file_path.startswith('analises_auditado'):
                    file_path = file_path.replace('analises_auditado', 'analises_auditado/', 1)
                elif 'evidencia_analises_auditado/' in file_path:
                    file_path = file_path.split('evidencia_analises_auditado/')[-1]
                print(f"📥 Caminho ajustado: {file_path}")
        
        if not file_path:
            return jsonify({'success': False, 'error': 'Não foi possível extrair o caminho do arquivo'}), 400
        
        print(f"📥 Bucket: evidencia_analises_auditado")
        print(f"📥 File path FINAL: {file_path}")
        
        # ⭐ USAR A FUNÇÃO GENÉRICA PARA BAIXAR
        from utils import baixar_arquivo_storage
        
        bucket = "evidencia_analises_auditado"
        file_bytes = baixar_arquivo_storage(file_path, bucket)
        
        if not file_bytes:
            return jsonify({'success': False, 'error': f'Arquivo não encontrado no storage: {file_path}'}), 500
        
        # ⭐ ENVIAR COMO ATTACHMENT (FORÇA O DOWNLOAD)
        return send_file(
            io.BytesIO(file_bytes),
            download_name=evidencia_nome,
            mimetype='application/pdf',
            as_attachment=True
        )
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@analise_bp.route('/analise-auditor/evidencia/<int:evidencia_id>/download')
def baixar_evidencia_analise_auditor(evidencia_id):
    """Baixa a evidência diretamente do Storage (sem abrir no navegador)"""
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        from database import engine
        from sqlalchemy import text
        from flask import send_file
        import io
        
        with engine.connect() as conn:
            query = text("""
                SELECT evidencia_nome 
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': evidencia_id}).fetchone()
            
            if not result:
                return jsonify({'error': 'Evidência não encontrada'}), 404
            
            evidencia_nome = result[0] or 'evidencia.pdf'
        
        # ⭐ CONSTRUIR O CAMINHO CORRETO
        # Caminho: analises_auditor/analise_id_{id}/{nome_arquivo}
        file_path = f"analises_auditor/analise_id_{evidencia_id}/{evidencia_nome}"
        
        print(f"📥 Baixando: {file_path}")
        
        # ⭐ USAR A FUNÇÃO GENÉRICA PARA BAIXAR
        from utils import baixar_arquivo_storage
        
        bucket = "evidencia_analises_auditor"
        file_bytes = baixar_arquivo_storage(file_path, bucket)
        
        if not file_bytes:
            return jsonify({'error': 'Arquivo não encontrado no storage'}), 500
        
        # ⭐ ENVIAR COMO ATTACHMENT (FORÇA O DOWNLOAD)
        return send_file(
            io.BytesIO(file_bytes),
            download_name=evidencia_nome,
            mimetype='application/pdf',
            as_attachment=True  # ⭐ FORÇA O DOWNLOAD EM VEZ DE ABRIR
        )
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
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

@analise_bp.route('/analise-auditor/<int:analise_id>/evidencia', methods=['DELETE'])
def api_remover_evidencia_analise_auditor(analise_id):
    """
    Remove a evidência de uma análise do auditor
    - Remove o arquivo do storage
    - Limpa os campos evidencia_url e evidencia_nome no banco
    """
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        from database import engine
        from sqlalchemy import text
        from utils import excluir_arquivo_storage, extrair_caminho_da_url
        
        with engine.connect() as conn:
            # 1. Buscar a evidência atual
            query = text("""
                SELECT evidencia_url, evidencia_nome
                FROM analises_criticas
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': analise_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            evidencia_url = result[0]
            evidencia_nome = result[1]
            
            if not evidencia_url:
                return jsonify({'success': False, 'error': 'Nenhuma evidência encontrada para remover'}), 404
            
            print(f"🗑️ Removendo evidência da análise {analise_id}: {evidencia_nome}")
            print(f"🗑️ Caminho: {evidencia_url}")
            
            # 2. REMOVER DO STORAGE
            try:
                # Verificar se é URL ou caminho
                if evidencia_url.startswith('http'):
                    caminho, bucket = extrair_caminho_da_url(evidencia_url)
                else:
                    caminho = evidencia_url
                    bucket = "evidencia_analises_auditor"
                
                if caminho:
                    excluir_arquivo_storage(caminho, bucket)
                    print(f"✅ Arquivo removido do storage: {caminho}")
                else:
                    print("⚠️ Não foi possível extrair o caminho do arquivo")
                    
            except Exception as e:
                print(f"⚠️ Erro ao remover do storage: {e}")
                # Continua para limpar o banco mesmo se falhar no storage
            
            # 3. LIMPAR OS CAMPOS NO BANCO
            query_update = text("""
                UPDATE analises_criticas
                SET evidencia_url = NULL,
                    evidencia_nome = NULL,
                    updated_at = NOW()
                WHERE id = :id
            """)
            conn.execute(query_update, {'id': analise_id})
            conn.commit()
            
            print(f"✅ Campos de evidência limpos na análise {analise_id}")
            
            return jsonify({
                'success': True,
                'message': 'Evidência removida com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@analise_bp.route('/analise-auditado/<int:analise_id>/evidencia', methods=['DELETE'])
def api_remover_evidencia_analise_auditado(analise_id):
    """
    Remove a evidência de uma análise do auditado
    - Remove o arquivo do storage
    - Limpa os campos evidencia_url e evidencia_nome no banco
    """
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        from database import engine
        from sqlalchemy import text
        from utils import excluir_arquivo_storage, extrair_caminho_da_url
        
        with engine.connect() as conn:
            # 1. Buscar a evidência atual
            query = text("""
                SELECT evidencia_url, evidencia_nome
                FROM analises_criticas
                WHERE id = :id AND tipo = 'auditado'
            """)
            result = conn.execute(query, {'id': analise_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            evidencia_url = result[0]
            evidencia_nome = result[1]
            
            if not evidencia_url:
                return jsonify({'success': False, 'error': 'Nenhuma evidência encontrada para remover'}), 404
            
            print(f"🗑️ Removendo evidência da análise {analise_id}: {evidencia_nome}")
            print(f"🗑️ Caminho: {evidencia_url}")
            
            # 2. REMOVER DO STORAGE
            try:
                # Verificar se é URL ou caminho
                if evidencia_url.startswith('http'):
                    caminho, bucket = extrair_caminho_da_url(evidencia_url)
                else:
                    caminho = evidencia_url
                    bucket = "evidencia_analises_auditado"
                
                if caminho:
                    excluir_arquivo_storage(caminho, bucket)
                    print(f"✅ Arquivo removido do storage: {caminho}")
                else:
                    print("⚠️ Não foi possível extrair o caminho do arquivo")
                    
            except Exception as e:
                print(f"⚠️ Erro ao remover do storage: {e}")
                # Continua para limpar o banco mesmo se falhar no storage
            
            # 3. LIMPAR OS CAMPOS NO BANCO
            query_update = text("""
                UPDATE analises_criticas
                SET evidencia_url = NULL,
                    evidencia_nome = NULL,
                    updated_at = NOW()
                WHERE id = :id
            """)
            conn.execute(query_update, {'id': analise_id})
            conn.commit()
            
            print(f"✅ Campos de evidência limpos na análise {analise_id}")
            
            return jsonify({
                'success': True,
                'message': 'Evidência removida com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500