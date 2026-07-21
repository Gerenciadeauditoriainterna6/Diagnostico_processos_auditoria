# routes/relatorios.py

from flask import Blueprint, jsonify, request, session, make_response
from database import engine
from sqlalchemy import text
from datetime import datetime
from zoneinfo import ZoneInfo
from logic import gerar_relatorio_followups
import io
import os

# Importar as funções de relatório
# (vamos criar essas funções no mesmo arquivo ou importar de outro lugar)

relatorios_bp = Blueprint('relatorios', __name__, url_prefix='/api/relatorios')

TZ_BRASILIA = ZoneInfo('America/Sao_Paulo')


# ============================================================
# ROTA: GERAR RELATÓRIO DE FOLLOW-UPS
# ============================================================

@relatorios_bp.route('/gerar-followup', methods=['POST'])
def gerar_relatorio_followup():
    """Gera relatório de follow-ups das sugestões de melhoria"""
    try:
        data = request.json
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        processo_id = data.get('processo_id')
        orientacao = data.get('orientacao', 'RETRATO')
        
        if not area_id or not auditoria_id:
            return jsonify({'error': 'Área e auditoria são obrigatórios'}), 400
        
        # ⭐ TODAS AS QUERIES DENTRO DE UM ÚNICO BLOCO
        with engine.connect() as conn:
            # Query 1: Buscar área
            query_area = text("""
                SELECT nome_area, loc_unidade, gestor, cargo 
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            area = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            area_nome = f"{area[0]} - {area[1]}" if area[1] else area[0]
            gestor = area[2] or 'Não informado'
            cargo = area[3] or 'Gestor'
            
            # Query 2: Buscar título da auditoria (MESMA CONEXÃO)
            query_titulo = text("SELECT titulo FROM auditorias WHERE id = :auditoria_id")
            titulo_result = conn.execute(query_titulo, {'auditoria_id': auditoria_id}).fetchone()
            titulo_auditoria = titulo_result[0] if titulo_result else 'Auditoria'
        
        # ⭐ CHAMAR A FUNÇÃO DO logic.py (FORA DO BLOCO, pois ela tem suas próprias queries)
        from logic import gerar_relatorio_followups
        
        pdf_bytes = gerar_relatorio_followups(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            auditoria_id=auditoria_id,
            processo_id=processo_id,
            orientacao=orientacao,
            titulo_auditoria=titulo_auditoria
        )
        
        # Nome do arquivo
        if processo_id:
            nome_arquivo = f"relatorio_followup_processo_{processo_id}.pdf"
        else:
            nome_arquivo = f"relatorio_followup_auditoria_{auditoria_id}.pdf"
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f"attachment; filename={nome_arquivo}"
        return response
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório de follow-up: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================
# ROTA: BUSCAR PROCESSOS POR AUDITORIA
# ============================================================

@relatorios_bp.route('/processos-por-auditoria', methods=['GET'])
def get_processos_por_auditoria():
    """Busca processos de uma auditoria para o select"""
    try:
        auditoria_id = request.args.get('auditoria_id')
        
        if not auditoria_id:
            return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
        
        with engine.connect() as conn:
            query = text("""
                SELECT id, codigo_processo, nome_processo
                FROM processos
                WHERE auditoria_id = :auditoria_id AND status = 'Ativo'
                ORDER BY codigo_processo
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            processos = []
            for row in result:
                processos.append({
                    'id': row[0],
                    'codigo_processo': row[1],
                    'nome_processo': row[2]
                })
            
            return jsonify({'success': True, 'processos': processos})
            
    except Exception as e:
        print(f"❌ Erro ao buscar processos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


