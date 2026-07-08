# routes/dashboard_api.py

from flask import Blueprint, jsonify, request
from dashboard_data import DashboardDataGenerator
from dashboard_kpis import DashboardKPIs  # ⬅️ ADICIONE ESTA LINHA!
import random

dashboard_api = Blueprint('dashboard_api', __name__)

@dashboard_api.route('/api/dashboard/kpis-gerais', methods=['GET'])
def get_kpis_gerais():
    """KPIs gerais do sistema"""
    kpis = DashboardKPIs.gerar_kpis_gerais()
    return jsonify({"success": True, "dados": kpis})

@dashboard_api.route('/api/dashboard/kpis-tempo', methods=['GET'])
def get_kpis_tempo():
    """KPIs de tempo"""
    kpis = DashboardKPIs.gerar_kpis_tempo()
    return jsonify({"success": True, "dados": kpis})

@dashboard_api.route('/api/dashboard/kpis-qualidade', methods=['GET'])
def get_kpis_qualidade():
    """KPIs de qualidade"""
    kpis = DashboardKPIs.gerar_kpis_qualidade()
    return jsonify({"success": True, "dados": kpis})

@dashboard_api.route('/api/dashboard/dados-mensais', methods=['GET'])
def get_dados_mensais():
    """Dados mensais para gráficos"""
    dados = DashboardDataGenerator.gerar_dados_mensais_completos()
    return jsonify({"success": True, "dados": dados})

@dashboard_api.route('/api/dashboard/riscos-por-categoria', methods=['GET'])
def get_riscos_por_categoria():
    """Distribuição de riscos por categoria"""
    dados = DashboardDataGenerator.gerar_dados_riscos_por_categoria()
    return jsonify({"success": True, "dados": dados})

@dashboard_api.route('/api/dashboard/top-areas', methods=['GET'])
def get_top_areas():
    """Top 5 áreas com mais processos"""
    dados = DashboardDataGenerator.gerar_top_areas()
    return jsonify({"success": True, "dados": dados})

@dashboard_api.route('/api/dashboard/performance-auditores', methods=['GET'])
def get_performance_auditores():
    """Performance dos auditores"""
    dados = DashboardDataGenerator.gerar_dados_auditores()
    return jsonify({"success": True, "dados": dados})

@dashboard_api.route('/api/dashboard/distribuicao-controles', methods=['GET'])
def get_distribuicao_controles():
    """Distribuição de controles"""
    dados = DashboardKPIs.gerar_distribuicao_controles()
    return jsonify({"success": True, "dados": dados})