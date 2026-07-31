# ROTAS DA TELA DO DIAGNOSTICO
##############################

from flask import session, request, jsonify, Blueprint
from routes.diagnostico.queries import buscar_auditorias_por_area, buscar_processos_por_area, buscar_riscos_por_processo, buscar_score_maximo_e_qtd_riscos_por_processo

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