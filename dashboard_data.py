# dashboard_data.py

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

class DashboardDataGenerator:
    """Gerador de dados para gráficos"""
    
    @staticmethod
    def gerar_dados_mensais_completos() -> List[Dict]:
        """Gera dados mensais completos (12 meses)"""
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        
        dados = []
        for i, mes in enumerate(meses):
            # Tendência de crescimento
            fator = 1 + (i * 0.08)
            dados.append({
                "mes": mes,
                "auditorias_iniciadas": int(random.randint(3, 8) * fator),
                "auditorias_concluidas": int(random.randint(2, 6) * fator),
                "riscos_identificados": int(random.randint(15, 40) * fator),
                "processos_auditados": int(random.randint(8, 20) * fator)
            })
        
        return dados
    
    @staticmethod
    def gerar_dados_riscos_por_categoria() -> Dict:
        """Gera distribuição de riscos por categoria"""
        categorias = [
            "Risco Operacional",
            "Risco Financeiro", 
            "Risco de Compliance",
            "Risco de TI/Segurança",
            "Risco Reputacional",
            "Risco Estratégico"
        ]
        
        return {
            "categorias": categorias,
            "quantidades": [random.randint(20, 100) for _ in categorias],
            "cores": ['#dc3545', '#fd7e14', '#ffc107', '#17a2b8', '#6f42c1', '#28a745']
        }
    
    @staticmethod
    def gerar_top_areas() -> List[Dict]:
        """Gera top 5 áreas com mais processos"""
        areas = [
            "Financeiro", "Comercial", "Recursos Humanos", "Tecnologia da Informação",
            "Jurídico", "Operações", "Logística", "Marketing", "Compras", "Engenharia"
        ]
        
        dados = []
        for area in random.sample(areas, 5):
            dados.append({
                "area": area,
                "processos": random.randint(15, 50),
                "riscos": random.randint(10, 40),
                "controles": random.randint(8, 30)
            })
        
        return sorted(dados, key=lambda x: x['processos'], reverse=True)
    
    @staticmethod
    def gerar_dados_auditores() -> List[Dict]:
        """Gera dados de performance dos auditores"""
        nomes = [
            "Chaiane Mattos", "Maicon Gomes", "Bárbara Fadel", 
            "Willian Ferreira", "Teófilo Boto"
        ]
        
        dados = []
        for nome in random.sample(nomes, random.randint(5, 8)):
            dados.append({
                "nome": nome,
                "auditorias": random.randint(3, 15),
                "processos": random.randint(10, 40),
                "riscos": random.randint(20, 60),
                "eficiencia": round(random.uniform(65, 98), 1)
            })
        
        return sorted(dados, key=lambda x: x['auditorias'], reverse=True)