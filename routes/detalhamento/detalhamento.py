from flask import Blueprint, request, jsonify, session, redirect, send_file
from routes.detalhamento.queries import (
    buscar_auditoria_id_do_processo,
    buscar_codigo_processo,
    buscar_proximo_numero_etapa,
    atualizar_etapa,
    inserir_etapa,
    buscar_arquivo_etapa
)
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


@detalhamento_bp.route('/api/etapa/salvar', methods=['POST'])
def api_salvar_etapa():
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
    
    # Processar diagrama
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
    obrigacoes_regulatorias = processar_obrigacoes(data.get('obrigacoes_regulatorias', '[]'))
    
    try:
        if etapa_id:
            # EDIÇÃO
            params = {
                'etapa_id': etapa_id,
                'nome_etapa': data['nome_etapa'],
                'descricao_etapa': data.get('descricao_etapa', ''),
                'como_e_feito': data.get('como_e_feito', ''),
                'objetivo_etapa': data.get('objetivo_etapa', ''),
                'status_etapa': data.get('status_etapa', 'Ativa'),
                'criticidade_etapa': data.get('criticidade_etapa', 'Em aprovação'),
                'politica_interna': data.get('politica_interna', ''),
                'analise_critica': data.get('analise_critica', ''),
                'sugestao_melhoria': data.get('sugestao_melhoria', ''),
                'necessidade_implantacao': data.get('necessidade_implantacao', ''),
                'ganho_previsto': data.get('ganho_previsto', ''),
                'obrigacoes_regulatorias': obrigacoes_regulatorias,
                'executores_etapa': data.get('executores_etapa', ''),
                'manual_em_andamento': data.get('manual_em_andamento', False),
                'auditoria_id': auditoria_id,
                'atualizar_diagrama': bool(data.get('diagrama_base64') or data.get('remover_diagrama')),
                'diagrama_bpmn': diagrama_bytes,
                'diagrama_nome': data.get('diagrama_nome'),
                'diagrama_tipo': data.get('diagrama_tipo'),
                'atualizar_manual': bool(data.get('manual_url') is not None or data.get('remover_manual')),
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
            return jsonify({'success': True, 'etapa_id': etapa_id, 'id': etapa_id})
            
        else:
            # NOVA ETAPA
            codigo_etapa = data.get('codigo_etapa')
            if not codigo_etapa:
                codigo_base = buscar_codigo_processo(processo_id) or str(processo_id)
                proximo = buscar_proximo_numero_etapa(processo_id)
                codigo_etapa = f"{codigo_base}.{proximo}"
            
            novo_id = inserir_etapa({
                'processo_id': processo_id,
                'auditoria_id': auditoria_id,
                'codigo_etapa': codigo_etapa,
                'nome_etapa': data['nome_etapa'],
                'descricao_etapa': data.get('descricao_etapa', ''),
                'como_e_feito': data.get('como_e_feito', ''),
                'objetivo_etapa': data.get('objetivo_etapa', ''),
                'status_etapa': data.get('status_etapa', 'Ativa'),
                'criticidade_etapa': data.get('criticidade_etapa', 'Em aprovação'),
                'politica_interna': data.get('politica_interna', ''),
                'analise_critica': data.get('analise_critica', ''),
                'sugestao_melhoria': data.get('sugestao_melhoria', ''),
                'necessidade_implantacao': data.get('necessidade_implantacao', ''),
                'ganho_previsto': data.get('ganho_previsto', ''),
                'obrigacoes_regulatorias': obrigacoes_regulatorias,
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
            
            return jsonify({'success': True, 'etapa_id': novo_id, 'id': novo_id, 'codigo_etapa': codigo_etapa})
            
    except Exception as e:
        print(f"❌ Erro ao salvar etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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