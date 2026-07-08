# dashboard_novo/endpoints.py

from flask import Blueprint, jsonify, request
from .kpis import NovoDashboardKPIs

novo_dashboard_api = Blueprint('novo_dashboard_api', __name__)

# ====== FILTROS ======

@novo_dashboard_api.route('/api/novo-dashboard/filtros', methods=['GET'])
def get_filtros():
    """Retorna opções para os filtros (anos, áreas)"""
    try:
        dados = NovoDashboardKPIs.gerar_opcoes_filtros()
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@novo_dashboard_api.route('/api/novo-dashboard/auditorias-por-area', methods=['GET'])
def get_auditorias_por_area():
    """Retorna auditorias de uma área específica"""
    area_id = request.args.get('area_id', type=int)
    
    if not area_id:
        return jsonify({"success": False, "error": "area_id é obrigatório"}), 400
    
    try:
        dados = NovoDashboardKPIs.gerar_auditorias_por_area(area_id)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
# ====== CARDS ======

@novo_dashboard_api.route('/api/novo-dashboard/cards', methods=['GET'])
def get_cards():
    """Retorna os 4 cards estratégicos"""
    ano = request.args.get('ano', type=int)
    area_id = request.args.get('area_id', type=int)
    auditoria_id = request.args.get('auditoria_id', type=int)
    
    try:
        dados = NovoDashboardKPIs.gerar_cards(ano, area_id, auditoria_id)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ====== GRÁFICOS ======

@novo_dashboard_api.route('/api/novo-dashboard/situacao-auditorias', methods=['GET'])
def get_situacao_auditorias():
    """Gráfico 1: Situação das Auditorias (Rosca)"""
    ano = request.args.get('ano', type=int)
    area_id = request.args.get('area_id', type=int)
    
    try:
        dados = NovoDashboardKPIs.gerar_situacao_auditorias(ano, area_id)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@novo_dashboard_api.route('/api/novo-dashboard/riscos-magnitude', methods=['GET'])
def get_riscos_magnitude():
    """Gráfico 2: Riscos por Magnitude (Barras)"""
    area_id = request.args.get('area_id', type=int)
    auditoria_id = request.args.get('auditoria_id', type=int)
    
    try:
        dados = NovoDashboardKPIs.gerar_riscos_magnitude(area_id, auditoria_id)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@novo_dashboard_api.route('/api/novo-dashboard/evolucao-mensal', methods=['GET'])
def get_evolucao_mensal():
    """Gráfico 3: Evolução (Mensal ou Anual)"""
    ano = request.args.get('ano', type=int)  # Pode ser None
    area_id = request.args.get('area_id', type=int)
    
    try:
        dados = NovoDashboardKPIs.gerar_evolucao_mensal(ano, area_id)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        print(f"❌ Erro em evolucao-mensal: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@novo_dashboard_api.route('/api/novo-dashboard/riscos-categoria', methods=['GET'])
def get_riscos_categoria():
    """Gráfico 4: Riscos por Categoria (Rosca)"""
    area_id = request.args.get('area_id', type=int)
    auditoria_id = request.args.get('auditoria_id', type=int)
    
    try:
        dados = NovoDashboardKPIs.gerar_riscos_categoria(area_id, auditoria_id)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@novo_dashboard_api.route('/api/novo-dashboard/top-areas', methods=['GET'])
def get_top_areas():
    """Gráfico 5: Top Áreas (Barras)"""
    ano = request.args.get('ano', type=int)
    
    try:
        dados = NovoDashboardKPIs.gerar_top_areas(ano)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        print(f"❌ Erro em top-areas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@novo_dashboard_api.route('/api/novo-dashboard/controles-status', methods=['GET'])
def get_controles_status():
    """Gráfico 6: Controles por Status (Rosca)"""
    area_id = request.args.get('area_id', type=int)
    auditoria_id = request.args.get('auditoria_id', type=int)
    
    try:
        dados = NovoDashboardKPIs.gerar_controles_status(area_id, auditoria_id)
        return jsonify({"success": True, "dados": dados})
    except Exception as e:
        print(f"❌ Erro em controles-status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500