# ROTAS DA TELA DO DIAGNOSTICO
##############################

from flask import session, request, jsonify, Blueprint
from routes.diagnostico.queries import (
    buscar_auditorias_por_area, buscar_processos_por_area, 
    buscar_riscos_por_processo, buscar_score_maximo_e_qtd_riscos_por_processo,
    buscar_funcionarios_por_area
    )
import uuid

# Criamos o blueprint
diagnostico_bp = Blueprint('diagnostico', __name__)


# ============================================================
# ROTA: Carregar auditorias de uma área
# ============================================================

@diagnostico_bp.route('/api/auditorias-por-area')
def api_auditorias_por_area():
    area_id = request.args.get('area_id')
    if not area_id:
        return jsonify({'error': 'area_id é obrigatório'}), 400
    
    auditorias = buscar_auditorias_por_area(area_id)
    return jsonify({'auditorias': auditorias})


# ============================================================
# ROTA: Carregar processos de uma área/auditoria
# ============================================================
@diagnostico_bp.route('/api/processos-por-area')
def api_processos_por_area():
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    area_id = request.args.get('area_id')
    auditoria_id = request.args.get('auditoria_id')
    
    if not area_id:
        return jsonify({'success': False, 'error': 'area_id é obrigatório'}), 400
    
    try:
        area_id = int(area_id)
        auditoria_id = int(auditoria_id) if auditoria_id and auditoria_id.strip() else None
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'IDs devem ser números inteiros'}), 400
    
    try:
        processos = buscar_processos_por_area(area_id, auditoria_id)
        return jsonify({'success': True, 'processos': processos})
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ROTA: Carregar os riscos do processo e seu score
# ============================================================
@diagnostico_bp.route('/api/processo/<int:processo_id>/riscos')
def api_processo_riscos(processo_id):
    """Retorna os riscos de um processo"""
    try:
        riscos = buscar_riscos_por_processo(processo_id)
        return jsonify({'success': True, 'riscos': riscos})
    except Exception as e:
        print(f"❌ Erro ao buscar riscos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ROTA: Carregar os funcionários da área
# ============================================================
@diagnostico_bp.route('/api/area/<int:area_id>/funcionarios-para-select')
def api_area_funcionarios_para_select(area_id):
    """Retorna funcionários da área"""
    
    funcionarios = buscar_funcionarios_por_area(area_id)
    return jsonify({'funcionarios': funcionarios})

# ============================================================
# ROTA: Retorna o último numero sequencial de uma area
# ============================================================
@diagnostico_bp.route('/api/processo/ultimo-sequencial')
def api_ultimo_sequencial():
    area_id = request.args.get('id_area')
    if not area_id:
        return jsonify({'error': 'id_area é obrigatório'}), 400
    
    from routes.diagnostico.queries import buscar_ultimo_sequencial
    ultimo = buscar_ultimo_sequencial(area_id)
    
    return jsonify({'ultimo_sequencial': ultimo})

# ============================================================
# ROTA: Salva as informações básicas do processo na etapa 2 do wizard
# ============================================================
@diagnostico_bp.route('/api/processo/salvar-basicos', methods=['POST'])
def api_salvar_processos_basicos():
    """Salva MÚLTIPLOS processos básicos de uma vez"""
    from routes.diagnostico.queries import salvar_processo_basico, salvar_executores_processo
    
    data = request.json
    processos = data.get('processos', [])
    
    if not processos:
        return jsonify({'success': False, 'error': 'Nenhum processo para salvar'}), 400
    
    ids_salvos = []
    
    try:
        for proc in processos:
            nome = proc.get('nome', '').strip().upper()
            codigo = proc.get('codigo', '').strip()
            funcionarios_ids = proc.get('funcionarios_ids', [])  # ← PLURAL!
            entrevistado = proc.get('entrevistado', '')
            area_id = proc.get('area_id')
            auditoria_id = proc.get('auditoria_id')
            processo_id = proc.get('id')
            
            if not nome or not area_id or not auditoria_id:
                continue
            
            # Salva o processo
            processo_id = salvar_processo_basico(nome, codigo, area_id, auditoria_id, entrevistado, processo_id)
            
            # Salva os executores (VÁRIOS)
            salvar_executores_processo(processo_id, funcionarios_ids)
            
            ids_salvos.append(processo_id)
        
        return jsonify({
            'success': True,
            'ids': ids_salvos,
            'quantidade': len(ids_salvos)
        })
        
    except Exception as e:
        print(f"❌ Erro ao salvar processos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ROTA: Salva os detalhes do processo na etapa 3 do wizard
# ============================================================
@diagnostico_bp.route('/api/processo/salvar-detalhes', methods=['POST'])
def api_salvar_processo_detalhes():
    """Salva os detalhes do processo"""
    from routes.diagnostico.queries import salvar_detalhes_processo
    
    data = request.json
    processo_id = data.get('processo_id')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    
    try:
        salvar_detalhes_processo(
            processo_id=processo_id,
            descricao=data.get('descricao', ''),
            etapa_ini=data.get('etapa_ini', ''),
            etapa_fim=data.get('etapa_fim', ''),
            produto=data.get('produto', ''),
            objetivo=data.get('objetivo', '')
        )
        
        return jsonify({'success': True, 'message': 'Detalhes salvos com sucesso'})
        
    except Exception as e:
        print(f"❌ Erro ao salvar detalhes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================================================
# ROTA: Retorna os processos em Ids específicos
# ============================================================
@diagnostico_bp.route('/api/processos-por-ids')
def api_processos_por_ids():
    """Retorna processos por IDs específicos"""
    ids_str = request.args.get('ids', '')
    
    if not ids_str:
        return jsonify({'success': False, 'error': 'ids é obrigatório'}), 400
    
    try:
        ids = [int(id.strip()) for id in ids_str.split(',')]
    except ValueError:
        return jsonify({'success': False, 'error': 'IDs inválidos'}), 400
    
    from routes.diagnostico.queries import buscar_processos_por_ids
    
    processos = buscar_processos_por_ids(ids)
    return jsonify({'success': True, 'processos': processos})

# ============================================================
# ROTA: Exclui um risco específico
# ============================================================

@diagnostico_bp.route('/api/risco/<int:risco_id>/excluir', methods=['DELETE'])
def api_excluir_risco(risco_id):
    """Exclui um risco"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM riscos WHERE id = :id"), {'id': risco_id})
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================================================
# ROTA: Busca os dados do processo
# ============================================================
@diagnostico_bp.route('/api/processo/<int:processo_id>/dados')
def api_processo_dados(processo_id):
    from routes.diagnostico.queries import buscar_processo_completo
    
    dados = buscar_processo_completo(processo_id)
    
    if dados:
        return jsonify({'success': True, **dados})
    return jsonify({'success': False, 'error': 'Processo não encontrado'}), 404


# ============================================================
# ROTA: Busca os executores de um processo
# ============================================================
@diagnostico_bp.route('/api/processo/<int:processo_id>/executores')
def api_processo_executores(processo_id):
    from routes.diagnostico.queries import buscar_executores_processo
    
    executores = buscar_executores_processo(processo_id)
    return jsonify({'success': True, 'executores': executores})

# ============================================================
# ROTA: Listar anexos do storage nos processos
# ============================================================
@diagnostico_bp.route('/api/processo/<int:processo_id>/anexos', methods=['GET'])
def api_listar_anexos(processo_id):
    from routes.diagnostico.queries import listar_anexos_processo
    anexos = listar_anexos_processo(processo_id)
    return jsonify({'success': True, 'anexos': anexos})


# ============================================================
# ROTA: Upload dos anexos
# ============================================================
@diagnostico_bp.route('/api/processo/<int:processo_id>/anexos', methods=['POST'])
def api_upload_anexo(processo_id):
    from utils.storage_utils import upload_arquivo_storage
    from routes.diagnostico.queries import salvar_anexo
    
    if 'arquivo' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
    
    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        return jsonify({'success': False, 'error': 'Arquivo vazio'}), 400
    
    # Validar tamanho (10MB)
    arquivo.seek(0, 2)
    tamanho = arquivo.tell()
    arquivo.seek(0)
    
    if tamanho > 10 * 1024 * 1024:
        return jsonify({'success': False, 'error': 'Arquivo excede 10MB'}), 400
    
    # Gerar nome único
    extensao = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''
    nome_unico = f"{uuid.uuid4()}.{extensao}" if extensao else str(uuid.uuid4())
    
    # Caminho no storage
    caminho = f"processo_{processo_id}/{nome_unico}"
    
    # Upload
    url = upload_arquivo_storage(arquivo, caminho, 'fluxo_processo', arquivo.content_type)
    
    if url:
        # Salvar no banco
        anexo_id = salvar_anexo(
            processo_id=processo_id,
            nome_arquivo=nome_unico,
            nome_original=arquivo.filename,
            caminho_storage=caminho,
            tipo_mime=arquivo.content_type,
            tamanho_bytes=tamanho
        )
        return jsonify({'success': True, 'anexo_id': anexo_id, 'url': url})
    
    return jsonify({'success': False, 'error': 'Erro no upload'}), 500

# ============================================================
# ROTA: Excuir anexos
# ============================================================
@diagnostico_bp.route('/api/anexo/<int:anexo_id>', methods=['DELETE'])
def api_excluir_anexo(anexo_id):
    from utils.storage_utils import excluir_arquivo_storage
    from routes.diagnostico.queries import excluir_anexo
    
    caminho = excluir_anexo(anexo_id)
    
    if caminho:
        excluir_arquivo_storage(caminho, 'fluxo_processo')
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Anexo não encontrado'}), 404

# ============================================================
# ROTA: Buscar URL assinada
# ============================================================
@diagnostico_bp.route('/api/anexo/<int:anexo_id>/url')
def api_anexo_url(anexo_id):
    from routes.diagnostico.queries import listar_anexos_processo
    from utils.storage_utils import obter_url_assinada
    
    # Buscar todos os anexos (não temos busca por ID único)
    # Vamos criar uma query específica
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT caminho_storage FROM processo_anexos WHERE id = :id
        """), {'id': anexo_id}).fetchone()
        
        if result:
            url = obter_url_assinada(result[0], 'fluxo_processo')
            return jsonify({'success': True, 'url': url})
    
    return jsonify({'success': False, 'error': 'Anexo não encontrado'}), 404