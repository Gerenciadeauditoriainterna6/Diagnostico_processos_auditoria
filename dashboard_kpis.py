# dashboard_kpis.py

import random
from typing import Dict, Any

class DashboardKPIs:
    """Gerador de KPIs fictícios"""
    
    @staticmethod
    def gerar_kpis_gerais() -> Dict[str, Any]:
        return {
            "total_auditorias": random.randint(30, 50),
            "auditorias_concluidas": random.randint(12, 22),
            "auditorias_em_andamento": random.randint(6, 14),
            "auditorias_planejadas": random.randint(8, 16),
            "total_processos": random.randint(150, 300),
            "total_riscos": random.randint(400, 800),
            "riscos_criticos": random.randint(20, 50),
            "riscos_altos": random.randint(60, 120),
            "total_controles": random.randint(200, 500),
            "controles_eficazes": random.randint(150, 350),
            "processos_detalhados": random.randint(80, 150),
            "taxa_conclusao_geral": round(random.uniform(65, 95), 1),
            "eficiencia_equipe": round(random.uniform(70, 98), 1)
        }
    
    @staticmethod
    def gerar_kpis_tempo() -> Dict[str, Any]:
        return {
            "tempo_medio_auditoria": round(random.uniform(30, 90), 1),
            "auditorias_no_prazo": random.randint(15, 30),
            "auditorias_atrasadas": random.randint(2, 8),
            "taxa_conclusao": round(random.uniform(65, 95), 1),
            "dias_uteis_media": random.randint(20, 60),
            "eficiencia_equipe": round(random.uniform(70, 98), 1)
        }
    
    @staticmethod
    def gerar_kpis_qualidade() -> Dict[str, Any]:
        return {
            "indice_conformidade": round(random.uniform(75, 98), 1),
            "recomendacoes_emitidas": random.randint(80, 200),
            "recomendacoes_aceitas": random.randint(60, 150),
            "taxa_aceitacao": round(random.uniform(70, 95), 1),
            "nao_conformidades": random.randint(30, 80),
            "grau_risco_medio": round(random.uniform(4, 8), 1)
        }
    
    @staticmethod
    def gerar_distribuicao_controles() -> Dict[str, Any]:
        """Distribuição de controles"""
        total = random.randint(200, 500)
        eficazes = int(total * random.uniform(0.6, 0.85))
        ineficazes = int((total - eficazes) * random.uniform(0.3, 0.6))
        pendentes = total - eficazes - ineficazes
        
        return {
            "eficazes": eficazes,
            "ineficazes": ineficazes,
            "pendentes": pendentes,
            "total": total,
            "cores": ['#28a745', '#dc3545', '#ffc107']
        }