from flask import Blueprint, request, jsonify, session, redirect, send_file
from routes.detalhamento.queries import (
    buscar_auditoria_id_do_processo,
    buscar_codigo_processo,
    buscar_proximo_numero_etapa,
    atualizar_etapa,
    inserir_etapa,
    buscar_arquivo_etapa
)
from utils.storage_utils import excluir_arquivo_storage
import base64, json, io

detalhamento_bp = Blueprint('detalhamento', __name__)


def processar_obrigacoes(obrigacoes_regulatorias):
    """Processa e limpa obrigações regulatórias"""
    if isinstance(obrigacoes_regulatorias, str):
        obrigacoes = json.loads(obrigacoes_regulatorias) if obrigacoes_regulatorias else []
    else:
        obrigacoes = obrigacoes_regulatorias or []
    
    for obrigacao in obrigacoes:
        for campo in ['arquivo_base64', '_upload_file', '_file_data', '_index']:
            obrigacao.pop(campo, None)
        obrigacao.setdefault('titulo', 'INEXISTENTE')
        obrigacao.setdefault('descricao_completa', 'INEXISTENTE')
        obrigacao.setdefault('arquivo_url', '')
        obrigacao.setdefault('arquivo_nome', '')
        obrigacao.setdefault('arquivo_tamanho', 0)
        obrigacao.setdefault('prazo', '')
        obrigacao.setdefault('obrigatorio', False)
        obrigacao.setdefault('orgao_regulador', '')
        obrigacao.setdefault('documento_necessario', '')
    
    return json.dumps(obrigacoes, ensure_ascii=False)


@detalhamento_bp.route('/api/etapa/<int:etapa_id>/download/<tipo>')
def api_download_arquivo(etapa_id, tipo):
    try:
        arquivo = buscar_arquivo_etapa(etapa_id, tipo)
        
        if not arquivo:
            return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
        
        if tipo == 'manual':
            if not arquivo.get('url'):
                return jsonify({'success': False, 'error': 'Nenhum manual'}), 404
            return redirect(arquivo['url'])
        else:
            if not arquivo.get('bytes'):
                return jsonify({'success': False, 'error': 'Nenhum arquivo'}), 404
            return send_file(
                io.BytesIO(arquivo['bytes']),
                download_name=arquivo.get('nome') or 'arquivo',
                as_attachment=True
            )
            
    except Exception as e:
        print(f"❌ Erro ao baixar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@detalhamento_bp.route('/api/etapa/salvar', methods=['POST'])
def api_salvar_etapa():
    """Salva uma nova etapa ou atualiza existente"""
    from routes.detalhamento.queries import inserir_etapa, atualizar_etapa, buscar_codigo_processo, buscar_proximo_numero_etapa, buscar_auditoria_id_do_processo
    import base64, json
    
    data = request.json
    etapa_id = data.get('id')
    processo_id = data.get('processo_id')
    auditoria_id = data.get('auditoria_id')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    if not data.get('nome_etapa'):
        return jsonify({'success': False, 'error': 'Nome da etapa é obrigatório'}), 400
    
    # Buscar auditoria_id se não veio
    if not auditoria_id:
        auditoria_id = buscar_auditoria_id_do_processo(processo_id)
    
    # Processar diagrama (Base64 → bytes)
    diagrama_bytes = None
    if data.get('diagrama_base64'):
        b64 = data['diagrama_base64'].split(',')[1] if ',' in data['diagrama_base64'] else data['diagrama_base64']
        diagrama_bytes = base64.b64decode(b64)
    
    # Processar mapeamento
    arquivo_mapeamento_bytes = None
    if data.get('arquivo_mapeamento_base64'):
        b64 = data['arquivo_mapeamento_base64'].split(',')[1] if ',' in data['arquivo_mapeamento_base64'] else data['arquivo_mapeamento_base64']
        arquivo_mapeamento_bytes = base64.b64decode(b64)
    
    # Processar obrigações
    obrigacoes_str = data.get('obrigacoes_regulatorias', '[]')
    if isinstance(obrigacoes_str, list):
        obrigacoes_str = json.dumps(obrigacoes_str)
    
    try:
        if etapa_id:
            # EDIÇÃO
            params = {
                'etapa_id': etapa_id, 'nome_etapa': data['nome_etapa'],
                'descricao_etapa': data.get('descricao_etapa', ''),
                'como_e_feito': data.get('como_e_feito', ''),
                'objetivo_etapa': data.get('objetivo_etapa', ''),
                'status_etapa': data.get('status_etapa', 'ATIVA'),
                'politica_interna': data.get('politica_interna', ''),
                'obrigacoes_regulatorias': obrigacoes_str,
                'executores_etapa': data.get('executores_etapa', ''),
                'manual_em_andamento': data.get('manual_em_andamento', False),
                'auditoria_id': auditoria_id,
                'atualizar_diagrama': bool(data.get('diagrama_base64') or data.get('remover_diagrama')),
                'diagrama_bpmn': diagrama_bytes,
                'diagrama_nome': data.get('diagrama_nome'),
                'diagrama_tipo': data.get('diagrama_tipo'),
                'atualizar_manual': bool('manual_url' in data or data.get('remover_manual')),
                'manual_nome': data.get('manual_nome'),
                'manual_url': data.get('manual_url'),
                'atualizar_mapeamento': bool(data.get('arquivo_mapeamento_base64') or data.get('remover_arquivo_mapeamento')),
                'arquivo_mapeamento': arquivo_mapeamento_bytes,
                'arquivo_mapeamento_nome': data.get('arquivo_mapeamento_nome'),
                'arquivo_mapeamento_tipo': data.get('arquivo_mapeamento_tipo'),
            }
            
            if data.get('remover_diagrama'):
                params.update({'diagrama_bpmn': None, 'diagrama_nome': None, 'diagrama_tipo': None})
            if data.get('remover_manual'):
                params.update({'manual_nome': None, 'manual_url': None})
            
            atualizar_etapa(etapa_id, params)
            return jsonify({'success': True, 'etapa_id': etapa_id})
        else:
            # NOVA ETAPA
            codigo_etapa = data.get('codigo_etapa')
            if not codigo_etapa:
                codigo_base = buscar_codigo_processo(processo_id) or str(processo_id)
                proximo = buscar_proximo_numero_etapa(processo_id)
                codigo_etapa = f"{codigo_base}.{proximo}"
            
            novo_id = inserir_etapa({
                'processo_id': processo_id, 'auditoria_id': auditoria_id,
                'codigo_etapa': codigo_etapa, 'nome_etapa': data['nome_etapa'],
                'descricao_etapa': data.get('descricao_etapa', ''),
                'como_e_feito': data.get('como_e_feito', ''),
                'objetivo_etapa': data.get('objetivo_etapa', ''),
                'status_etapa': data.get('status_etapa', 'ATIVA'),
                'politica_interna': data.get('politica_interna', ''),
                'obrigacoes_regulatorias': obrigacoes_str,
                'executores_etapa': data.get('executores_etapa', ''),
                'diagrama_bpmn': diagrama_bytes,
                'diagrama_nome': data.get('diagrama_nome'),
                'diagrama_tipo': data.get('diagrama_tipo'),
                'manual_nome': data.get('manual_nome'),
                'manual_url': data.get('manual_url'),
                'arquivo_mapeamento': arquivo_mapeamento_bytes,
                'arquivo_mapeamento_nome': data.get('arquivo_mapeamento_nome'),
                'arquivo_mapeamento_tipo': data.get('arquivo_mapeamento_tipo'),
                'manual_em_andamento': data.get('manual_em_andamento', False),
            })
            return jsonify({'success': True, 'etapa_id': novo_id, 'codigo_etapa': codigo_etapa})
            
    except Exception as e:
        print(f"❌ Erro ao salvar etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@detalhamento_bp.route('/api/etapa/<int:etapa_id>/excluir', methods=['DELETE'])
def api_excluir_etapa(etapa_id):
    from routes.detalhamento.queries import excluir_etapa
    try:
        excluir_etapa(etapa_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@detalhamento_bp.route('/api/etapa/<int:etapa_id>')
def api_etapa_detalhes(etapa_id):
    from routes.detalhamento.queries import buscar_etapa_por_id
    etapa = buscar_etapa_por_id(etapa_id)
    if etapa:
        return jsonify({'success': True, 'etapa': etapa})
    return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404


@detalhamento_bp.route('/api/etapa/gerar-codigo')
def api_gerar_codigo_etapa():
    from routes.detalhamento.queries import gerar_codigo_etapa
    processo_id = request.args.get('processo_id')
    if not processo_id:
        return jsonify({'error': 'processo_id é obrigatório'}), 400
    codigo = gerar_codigo_etapa(processo_id)
    if codigo:
        return jsonify({'success': True, 'codigo_etapa': codigo})
    return jsonify({'error': 'Processo não encontrado'}), 404


@detalhamento_bp.route('/api/etapa/<int:etapa_id>/download-manual')
def api_download_manual(etapa_id):
    from routes.detalhamento.queries import buscar_manual_etapa
    from flask import redirect
    manual = buscar_manual_etapa(etapa_id)
    if manual and manual.get('url'):
        return redirect(manual['url'])
    return jsonify({'success': False, 'error': 'Nenhum manual'}), 404


@detalhamento_bp.route('/api/etapa/<int:etapa_id>/remover-manual', methods=['DELETE'])
def api_remover_manual(etapa_id):
    from routes.detalhamento.queries import remover_manual_etapa
    from utils.storage_utils import excluir_arquivo_storage
    from urllib.parse import urlparse, unquote
    import re
    
    data = request.json
    arquivo_url = data.get('arquivo_url') if data else None
    
    if not arquivo_url:
        return jsonify({'success': False, 'error': 'URL não fornecida'}), 400
    
    print(f"🔍 URL recebida: {arquivo_url}")
    
    # ⭐ Extrair caminho manualmente da URL assinada
    # Exemplo: /storage/v1/object/sign/detalhamento_etapas/manuais/etapa_id_56/arquivo.pdf?token=...
    caminho = None
    bucket = 'detalhamento_etapas'
    
    parsed = urlparse(arquivo_url)
    path = unquote(parsed.path)
    
    # Procurar pelo padrão: /sign/ ou /public/ ou /authenticated/
    match = re.search(r'/(?:sign|public|authenticated)/([^/]+)/(.+)', path)
    if match:
        bucket = match.group(1)
        caminho = match.group(2)
        # Remover parâmetros de consulta (token)
        caminho = caminho.split('?')[0]
    
    print(f"🔍 Caminho extraído: {caminho}")
    print(f"🔍 Bucket: {bucket}")
    
    if caminho:
        excluir_arquivo_storage(caminho, bucket)
    else:
        print("⚠️ Não foi possível extrair o caminho da URL")
    
    remover_manual_etapa(etapa_id)
    return jsonify({'success': True})

@detalhamento_bp.route('/api/upload/detalhamento', methods=['POST'])
def api_upload_detalhamento():
    """Upload de arquivos para o bucket detalhamento_etapas"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    try:
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Nome vazio'}), 400
        
        tipo = request.form.get('tipo', 'obrigacao')
        etapa_id = request.form.get('etapa_id', 'temp')
        
        # Validar tipo
        if arquivo.content_type not in ['application/pdf']:
            return jsonify({'success': False, 'error': 'Apenas PDF'}), 400
        
        # Validar tamanho (10MB)
        arquivo.seek(0, 2)
        tamanho = arquivo.tell()
        arquivo.seek(0)
        if tamanho > 10 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Máx 10MB'}), 400
        
        # Gerar nome único
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        nome_limpo = ''.join(c for c in arquivo.filename if c.isalnum() or c in ' ._-').replace(' ', '_')
        
        pasta = 'manuais' if tipo == 'manual' else 'obrigacoes'
        caminho = f"{pasta}/etapa_id_{etapa_id}/{timestamp}_{unique_id}_{nome_limpo}"
        
        from utils.storage_utils import upload_arquivo_storage
        url_arquivo = upload_arquivo_storage(arquivo, caminho, "detalhamento_etapas", "application/pdf")
        
        if url_arquivo:
            return jsonify({'success': True, 'url': url_arquivo, 'nome_arquivo': arquivo.filename, 'tamanho': tamanho})
        
        return jsonify({'success': False, 'error': 'Erro no upload'}), 500
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@detalhamento_bp.route('/api/arquivo/url-assinada', methods=['POST'])
def api_obter_url_assinada():
    from utils.storage_utils import obter_url_assinada
    from urllib.parse import urlparse, unquote
    import re
    
    data = request.json
    caminho_recebido = data.get('caminho')
    bucket = data.get('bucket', 'detalhamento_etapas')
    
    if not caminho_recebido:
        return jsonify({'success': False, 'error': 'Caminho é obrigatório'}), 400
    
    # ⭐ Se for uma URL completa, extrair só o caminho
    if caminho_recebido.startswith('http'):
        parsed = urlparse(caminho_recebido)
        path = unquote(parsed.path)
        match = re.search(r'/(?:sign|public|authenticated)/([^/]+)/(.+)', path)
        if match:
            bucket = match.group(1)
            caminho_recebido = match.group(2).split('?')[0]
    
    print(f"🔍 Gerando URL para: bucket={bucket}, caminho={caminho_recebido}")
    
    url = obter_url_assinada(caminho_recebido, bucket, expires_in=31536000)
    
    if url:
        return jsonify({'success': True, 'url': url})
    return jsonify({'success': False, 'error': 'Erro ao gerar URL'}), 500

@detalhamento_bp.route('/api/analise/<int:analise_id>/evidencia')
def api_analise_evidencia(analise_id):
    """Download da evidência da análise"""
    from database import engine
    from sqlalchemy import text
    from utils.storage_utils import obter_url_assinada
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT evidencia_url, evidencia_nome FROM analises_criticas WHERE id = :aid
        """), {'aid': analise_id}).fetchone()
        
        if result and result[0]:
            url = obter_url_assinada(result[0], 'evidencia_analises_auditado')
            if url:
                from flask import redirect
                return redirect(url)
    
    return jsonify({'success': False, 'error': 'Evidência não encontrada'}), 404

@detalhamento_bp.route('/api/obrigacao/remover-arquivo', methods=['POST'])
def api_obrigacao_remover_arquivo():
    """Remove arquivo da obrigação do Storage"""
    from utils.storage_utils import excluir_arquivo_storage
    from urllib.parse import urlparse, unquote
    import re
    
    data = request.json
    arquivo_url = data.get('arquivo_url')
    
    if not arquivo_url:
        return jsonify({'success': False, 'error': 'URL não fornecida'}), 400
    
    print(f"🔍 Removendo arquivo de obrigação: {arquivo_url}")
    
    # Extrair caminho da URL
    caminho = None
    bucket = 'detalhamento_etapas'
    
    if arquivo_url.startswith('http'):
        parsed = urlparse(arquivo_url)
        path = unquote(parsed.path)
        match = re.search(r'/(?:sign|public|authenticated)/([^/]+)/(.+)', path)
        if match:
            bucket = match.group(1)
            caminho = match.group(2).split('?')[0]
    else:
        caminho = arquivo_url
    
    print(f"🗑️ Removendo: bucket={bucket}, caminho={caminho}")
    
    if caminho:
        excluir_arquivo_storage(caminho, bucket)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Caminho inválido'}), 400

@detalhamento_bp.route('/api/arquivo/excluir', methods=['POST'])
def api_arquivo_excluir():
    """Exclui um arquivo do Storage"""
    from utils.storage_utils import excluir_arquivo_storage
    from urllib.parse import urlparse, unquote
    import re
    
    data = request.json
    arquivo_url = data.get('arquivo_url')
    bucket = data.get('bucket', 'detalhamento_etapas')
    
    if not arquivo_url:
        return jsonify({'success': False, 'error': 'URL não fornecida'}), 400
    
    caminho = None
    
    if arquivo_url.startswith('http'):
        parsed = urlparse(arquivo_url)
        path = unquote(parsed.path)
        match = re.search(r'/(?:sign|public|authenticated)/([^/]+)/(.+)', path)
        if match:
            bucket = match.group(1)
            caminho = match.group(2).split('?')[0]
    else:
        caminho = arquivo_url
    
    print(f"🗑️ Excluindo: bucket={bucket}, caminho={caminho}")
    
    if caminho:
        excluir_arquivo_storage(caminho, bucket)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Caminho inválido'}), 400

@detalhamento_bp.route('/api/obrigacao/excluir', methods=['DELETE'])
def api_excluir_obrigacao():
    """Exclui uma obrigação regulatória da etapa"""
    from database import engine
    from sqlalchemy import text
    import json
    from utils.storage_utils import excluir_arquivo_storage
    from urllib.parse import urlparse, unquote
    import re
    
    try:
        data = request.json
        etapa_id = data.get('etapa_id')
        indice_obrigacao = data.get('indice')
        arquivo_url = data.get('arquivo_url')
        
        if not etapa_id:
            return jsonify({'success': False, 'error': 'ID da etapa é obrigatório'}), 400
        if indice_obrigacao is None:
            return jsonify({'success': False, 'error': 'Índice da obrigação é obrigatório'}), 400
        
        print(f"🗑️ Excluindo obrigação {indice_obrigacao} da etapa {etapa_id}")
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT obrigacoes_regulatorias FROM etapas_processo WHERE id = :eid
            """), {'eid': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            obrigacoes = json.loads(result[0]) if result[0] else []
            
            if indice_obrigacao >= len(obrigacoes):
                return jsonify({'success': False, 'error': 'Obrigação não encontrada'}), 404
            
            obrigacao_removida = obrigacoes.pop(indice_obrigacao)
            
            # Excluir arquivo do storage
            url_para_excluir = arquivo_url or obrigacao_removida.get('arquivo_url')
            if url_para_excluir and url_para_excluir.strip():
                caminho = None
                bucket = 'detalhamento_etapas'
                
                if url_para_excluir.startswith('http'):
                    parsed = urlparse(url_para_excluir)
                    path = unquote(parsed.path)
                    match = re.search(r'/(?:sign|public|authenticated)/([^/]+)/(.+)', path)
                    if match:
                        bucket = match.group(1)
                        caminho = match.group(2).split('?')[0]
                else:
                    caminho = url_para_excluir
                
                if caminho:
                    print(f"📎 Excluindo arquivo: {caminho}")
                    excluir_arquivo_storage(caminho, bucket)
            
            # Atualizar banco
            conn.execute(text("""
                UPDATE etapas_processo SET obrigacoes_regulatorias = :obrig, updated_at = NOW()
                WHERE id = :eid
            """), {'obrig': json.dumps(obrigacoes, ensure_ascii=False), 'eid': etapa_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Obrigação excluída', 'total_restantes': len(obrigacoes)})
            
    except Exception as e:
        print(f"❌ Erro ao excluir obrigação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500