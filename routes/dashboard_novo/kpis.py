# dashboard_novo/kpis.py

from database import engine
from sqlalchemy import text
from typing import Dict, Any, Optional, List
import random
from config.cores import CORES

class NovoDashboardKPIs:
    """KPIs do novo dashboard usando SQL PURO"""
    
    # ==========================================
    # FILTROS
    # ==========================================
    
    @staticmethod
    def gerar_opcoes_filtros() -> Dict[str, Any]:
        """Busca opções reais do banco de dados"""
        
        with engine.connect() as conn:
            # Anos
            anos_result = conn.execute(text("""
                SELECT DISTINCT ano 
                FROM auditorias 
                WHERE ano IS NOT NULL
                ORDER BY ano DESC
            """)).fetchall()
            anos = [row[0] for row in anos_result] if anos_result else []
            
            # Áreas
            areas_result = conn.execute(text("""
                SELECT id_area, nome_area 
                FROM informacoes_area 
                WHERE status = 'Ativo'
                ORDER BY id_area
            """)).fetchall()
            areas = [
                {"id": row[0], "nome": row[1]} 
                for row in areas_result
            ] if areas_result else []
            
            if not anos:
                anos = [2026, 2025, 2024]
            if not areas:
                areas = [
                    {"id": 1, "nome": "Financeiro"},
                    {"id": 2, "nome": "Comercial"},
                ]
            
            return {"anos": anos, "areas": areas}
    
    @staticmethod
    def gerar_auditorias_por_area(area_id: int) -> Dict[str, Any]:
        """Busca auditorias de uma área específica"""
        if not area_id:
            return {"auditorias": []}
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    id,
                    codigo_auditoria,
                    titulo,
                    ano,
                    trimestre
                FROM auditorias 
                WHERE id_area = :area_id
                ORDER BY ano DESC, trimestre DESC
            """), {"area_id": area_id}).fetchall()
            
            auditorias = []
            for row in result:
                auditorias.append({
                    "id": row[0],
                    "codigo": row[1] or f"AUD-{row[3]}{row[4]:02d}",
                    "titulo": row[2] or f"Auditoria {row[0]}",
                    "ano": row[3],
                    "trimestre": row[4]
                })
            
            return {"auditorias": auditorias}
    
    # ==========================================
    # CARDS (4)
    # ==========================================
    
    # dashboard_novo/kpis.py

    @staticmethod
    def gerar_cards(
        ano: Optional[int] = None,
        area_id: Optional[int] = None,
        auditoria_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Gera os 4 cards estratégicos do dashboard"""
        
        with engine.connect() as conn:
            
            # ==========================================
            # 1. Total de Auditorias
            # ==========================================
            sql_total = """
                SELECT COUNT(*) 
                FROM auditorias a
                WHERE 1=1
            """
            params_total = {}
        
            if ano is not None:
                sql_total += " AND a.ano = :ano"
                params_total['ano'] = ano
            
            total_auditorias = conn.execute(text(sql_total), params_total).fetchone()[0] or 0
            
            # ==========================================
            # 2. Auditorias em Andamento
            # ==========================================
            sql_andamento = """
                SELECT COUNT(*) 
                FROM auditorias a
                WHERE 1=1
            """
            params_andamento = {}
            
            if ano is not None:
                sql_andamento += " AND a.ano = :ano"
                params_andamento['ano'] = ano
            if area_id is not None:
                sql_andamento += " AND a.id_area = :area_id"
                params_andamento['area_id'] = area_id
            if auditoria_id is not None:
                sql_andamento += " AND a.id = :auditoria_id"
                params_andamento['auditoria_id'] = auditoria_id
            
            sql_andamento += " AND a.status = 'EM EXECUÇÃO'"
            em_andamento = conn.execute(text(sql_andamento), params_andamento).fetchone()[0] or 0
            
            # ==========================================
            # 3. Auditorias Concluídas
            # ==========================================
            sql_concluidas = """
                SELECT COUNT(*) 
                FROM auditorias a
                WHERE 1=1
            """
            params_concluidas = {}
            
            if ano is not None:
                sql_concluidas += " AND a.ano = :ano"
                params_concluidas['ano'] = ano
            if area_id is not None:
                sql_concluidas += " AND a.id_area = :area_id"
                params_concluidas['area_id'] = area_id
            if auditoria_id is not None:
                sql_concluidas += " AND a.id = :auditoria_id"
                params_concluidas['auditoria_id'] = auditoria_id
            
            sql_concluidas += " AND a.status = 'CONCLUÍDA'"
            concluidas = conn.execute(text(sql_concluidas), params_concluidas).fetchone()[0] or 0
            
            # ==========================================
            # 4. Auditorias Inconclusivas
            # ==========================================
            sql_inconclusivas = """
                SELECT COUNT(*) 
                FROM auditorias a
                WHERE 1=1
            """
            params_inconclusivas = {}
            
            if ano is not None:
                sql_inconclusivas += " AND a.ano = :ano"
                params_inconclusivas['ano'] = ano
            if area_id is not None:
                sql_inconclusivas += " AND a.id_area = :area_id"
                params_inconclusivas['area_id'] = area_id
            if auditoria_id is not None:
                sql_inconclusivas += " AND a.id = :auditoria_id"
                params_inconclusivas['auditoria_id'] = auditoria_id
            
            sql_inconclusivas += " AND a.status = 'INCONCLUSIVA'"
            inconclusivas = conn.execute(text(sql_inconclusivas), params_inconclusivas).fetchone()[0] or 0
            
            # ==========================================
            # 5. Riscos Identificados (TODOS os riscos da tabela riscos)
            # ==========================================
            sql_riscos = """
                SELECT COUNT(*) 
                FROM riscos r
                JOIN processos p ON r.processo_id = p.id
                JOIN auditorias a ON p.auditoria_id = a.id
                WHERE 1=1
            """
            params_riscos = {}
            
            if ano is not None:
                sql_riscos += " AND a.ano = :ano"
                params_riscos['ano'] = ano
            if area_id is not None:
                sql_riscos += " AND a.id_area = :area_id"
                params_riscos['area_id'] = area_id
            if auditoria_id is not None:
                sql_riscos += " AND a.id = :auditoria_id"
                params_riscos['auditoria_id'] = auditoria_id
            
            riscos_identificados = conn.execute(text(sql_riscos), params_riscos).fetchone()[0] or 0
            
            # ==========================================
            # 6. Processos Mapeados (Ativos)
            # ==========================================
            sql_processos = """
                SELECT COUNT(*) 
                FROM processos p
                WHERE p.status = 'Ativo'
            """
            params_processos = {}
            
            if ano is not None:
                sql_processos += " AND EXISTS (SELECT 1 FROM auditorias a WHERE a.id = p.auditoria_id AND a.ano = :ano)"
                params_processos['ano'] = ano
            if area_id is not None:
                sql_processos += " AND p.id_area = :area_id"
                params_processos['area_id'] = area_id
            if auditoria_id is not None:
                sql_processos += " AND p.auditoria_id = :auditoria_id"
                params_processos['auditoria_id'] = auditoria_id
            
            processos_mapeados = conn.execute(text(sql_processos), params_processos).fetchone()[0] or 0
            
            # ==========================================
            # 7. Total de Controles (com status preenchido)
            # ==========================================
            sql_controles = """
                SELECT COUNT(*)
                FROM controles_etapa ce
                WHERE ce.status_controle IS NOT NULL
                AND ce.status_controle != ''
            """
            params_controles = {}
            
            if ano is not None:
                sql_controles += " AND a.ano = :ano"
                params_controles['ano'] = ano
            
            if area_id is not None:
                sql_controles += " AND p.id_area = :area_id"
                params_controles['area_id'] = area_id
            
            if auditoria_id is not None:
                sql_controles += " AND p.auditoria_id = :auditoria_id"
                params_controles['auditoria_id'] = auditoria_id
            
            total_controles = conn.execute(text(sql_controles), params_controles).fetchone()[0] or 0
        
        return {
            "total_auditorias": total_auditorias,
            "auditorias_em_andamento": em_andamento,
            "auditorias_concluidas": concluidas,
            "auditorias_inconclusivas": inconclusivas,
            "riscos_identificados": riscos_identificados,
            "processos_mapeados": processos_mapeados,
            "total_controles": total_controles
        }
    
            

    @staticmethod
    def gerar_situacao_auditorias(
        ano: Optional[int] = None,
        area_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Dados para o gráfico de situação das auditorias (Rosca)"""
        
        with engine.connect() as conn:
            sql = """
                SELECT 
                    status,
                    COUNT(*) as quantidade
                FROM auditorias a
                WHERE 1=1
            """
            params = {}
            
            if ano is not None:
                sql += " AND a.ano = :ano"
                params['ano'] = ano
            if area_id is not None:
                sql += " AND a.id_area = :area_id"
                params['area_id'] = area_id
            
            sql += " GROUP BY status"
            
            result = conn.execute(text(sql), params).fetchall()
            
            print(f"🔍 Status do banco: {result}")
        
        # ⭐ Mapeamento dos status reais
        status_map = {
            "EM EXECUÇÃO": "em_execucao",
            "INCONCLUSIVA": "inconclusiva",
            "EFICÁCIA VALIDADA": "eficacia_validada",
            "FOLLOW-UP": "follow_up"
        }
        
        # Inicializar todos os contadores
        dados = {
            "em_execucao": 0,
            "inconclusiva": 0,
            "eficacia_validada": 0,
            "follow_up": 0
        }
        
        for row in result:
            status = row[0] or ''
            qtd = row[1] or 0
            
            if status in status_map:
                dados[status_map[status]] = qtd
                print(f"✅ Status '{status}' → {qtd}")
            else:
                print(f"⚠️ Status não mapeado: '{status}'")
        
        # ⭐ Preparar dados para o gráfico (apenas status que existem)
        labels = []
        valores = []
        cores = []
        
        # Mapeamento de cores por status
        cores_status = {
            "em_execucao": CORES['status_execucao'],
            "inconclusiva": CORES['status_inconclusivo'],
            "eficacia_validada": CORES['status_eficacia_validada'],
            "follow_up": CORES['status_followup']
        }

        
        # Nomes amigáveis para exibição
        nomes_status = {
            "em_execucao": "Em Execução",
            "inconclusiva": "Inconclusiva",
            "eficacia_validada": "Eficácia Validada",
            "follow_up": "Follow-up"
        }
        
        # Adicionar apenas status que têm dados > 0
        for chave, valor in dados.items():
            if valor > 0:
                labels.append(nomes_status.get(chave, chave))
                valores.append(valor)
                cores.append(cores_status.get(chave, "#6c757d"))
        
        # ⭐ Se não houver dados, mostrar mensagem
        if not valores:
            labels = ["Sem dados"]
            valores = [1]
            cores = ["#e0e0e0"]
        
        return {
            "labels": labels,
            "valores": valores,
            "cores": cores
        }
    

    @staticmethod
    def gerar_riscos_magnitude(
        area_id: Optional[int] = None,
        auditoria_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Dados para o gráfico de riscos por magnitude (Barras)
        Busca da tabela riscos (processos)
        """
        
        with engine.connect() as conn:
            sql = """
                SELECT 
                    r.score_risco,
                    COUNT(*) as quantidade
                FROM riscos r
                JOIN processos p ON r.processo_id = p.id
                JOIN auditorias a ON p.auditoria_id = a.id
                WHERE 1=1
            """
            params = {}
            
            if area_id is not None:
                sql += " AND a.id_area = :area_id"
                params['area_id'] = area_id
            if auditoria_id is not None:
                sql += " AND a.id = :auditoria_id"
                params['auditoria_id'] = auditoria_id
            
            sql += " GROUP BY r.score_risco"
            sql += " ORDER BY r.score_risco"
            
            result = conn.execute(text(sql), params).fetchall()
            
            print(f"🔍 Riscos magnitude (tabela riscos) - resultado: {result}")
        
        # Inicializar contadores
        dados = {
            "baixo": 0,    # 0-3
            "medio": 0,    # 4-7
            "alto": 0,     # 8-11
            "muito_alto": 0   # 12+
        }
        
        for row in result:
            score = row[0] or 0
            qtd = row[1] or 0
            
            if score <= 3:
                dados["baixo"] += qtd
            elif score <= 7:
                dados["medio"] += qtd
            elif score <= 11:
                dados["alto"] += qtd
            else:
                dados["muito_alto"] += qtd
        
        # Preparar dados para o gráfico
        labels = ["Baixo (0-3)", "Médio (4-7)", "Alto (8-11)", "Muito Alto (12+)"]
        valores = [dados["baixo"], dados["medio"], dados["alto"], dados["muito_alto"]]
        cores = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
        
        return {
            "labels": labels,
            "valores": valores,
            "cores": cores
        }
    

    @staticmethod
    def gerar_evolucao_mensal(
        ano: Optional[int] = None,
        area_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Dados para o gráfico de evolução (Mensal ou Anual)
        
        - Se apenas 1 ano disponível: mostra evolução por mês
        - Se mais de 1 ano disponível: mostra evolução por ano
        """
        
        with engine.connect() as conn:
            
            # ⭐ PASSO 1: Descobrir quantos anos existem no filtro
            sql_anos = """
                SELECT DISTINCT EXTRACT(YEAR FROM data_inicio) as ano
                FROM auditorias a
                WHERE data_inicio IS NOT NULL
            """
            params_anos = {}
            
            if area_id is not None:
                sql_anos += " AND a.id_area = :area_id"
                params_anos['area_id'] = area_id
            
            sql_anos += " ORDER BY ano"
            
            result_anos = conn.execute(text(sql_anos), params_anos).fetchall()
            anos_disponiveis = [int(row[0]) for row in result_anos]
            
            print(f"🔍 Anos disponíveis: {anos_disponiveis}")
            
            # ⭐ Se não houver dados, retornar vazio
            if not anos_disponiveis:
                return {
                    "tipo": "vazio",
                    "dados": [],
                    "titulo": "Sem dados disponíveis",
                    "label_y": "Quantidade"
                    
                }
            
            # ⭐ PASSO 2: Decidir se mostra mensal ou anual
            # Se o filtro de ano está definido OU só tem 1 ano disponível
            if ano is not None or len(anos_disponiveis) == 1:
                # Mostrar por MÊS
                ano_para_mostrar = ano if ano is not None else anos_disponiveis[0]
                
                meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                
                sql = """
                    SELECT 
                        EXTRACT(MONTH FROM data_inicio) as mes,
                        COUNT(*) as total
                    FROM auditorias a
                    WHERE data_inicio IS NOT NULL
                    AND EXTRACT(YEAR FROM data_inicio) = :ano
                """
                params = {'ano': ano_para_mostrar}
                
                if area_id is not None:
                    sql += " AND a.id_area = :area_id"
                    params['area_id'] = area_id
                
                sql += " GROUP BY EXTRACT(MONTH FROM data_inicio)"
                sql += " ORDER BY mes"
                
                result = conn.execute(text(sql), params).fetchall()
                print(f"🔍 Evolução mensal para {ano_para_mostrar}: {result}")
                
                # Inicializar todos os meses com zero
                dados_meses = {i: 0 for i in range(1, 13)}
                for row in result:
                    mes = int(row[0])
                    dados_meses[mes] = row[1] or 0
                
                # Preparar dados para o gráfico
                dados = []
                for i, mes in enumerate(meses):
                    dados.append({
                        "label": mes,
                        "valor": dados_meses[i + 1]
                    })
                
                return {
                    "tipo": "mensal",
                    "ano": ano_para_mostrar,
                    "dados": dados,
                    "titulo": f"Auditorias Iniciadas em {ano_para_mostrar}",
                    "label_x": "Mês",
                    "label_y": "Quantidade de Auditorias",
                    "cor_linha": CORES['primary_blue'],
                    "cor_area": CORES['blue_lightest']
                }
            
            # ⭐ PASSO 3: Mais de 1 ano → Mostrar por ANO
            else:
                sql = """
                    SELECT 
                        EXTRACT(YEAR FROM data_inicio) as ano,
                        COUNT(*) as total
                    FROM auditorias a
                    WHERE data_inicio IS NOT NULL
                """
                params = {}
                
                if area_id is not None:
                    sql += " AND a.id_area = :area_id"
                    params['area_id'] = area_id
                
                sql += " GROUP BY EXTRACT(YEAR FROM data_inicio)"
                sql += " ORDER BY ano"
                
                result = conn.execute(text(sql), params).fetchall()
                print(f"🔍 Evolução anual: {result}")
                
                # Preparar dados para o gráfico
                dados = []
                for row in result:
                    ano_val = int(row[0])
                    dados.append({
                        "label": str(ano_val),
                        "valor": row[1] or 0
                    })
                
                return {
                    "tipo": "anual",
                    "dados": dados,
                    "titulo": "Evolução Anual de Auditorias",
                    "label_x": "Ano",
                    "label_y": "Quantidade de Auditorias",
                    "cor_linha": CORES['primary_blue'],
                    "cor_area": CORES['blue_lightest']
                }
            

    @staticmethod
    def gerar_riscos_categoria(
        area_id: Optional[int] = None,
        auditoria_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Dados para o gráfico de riscos por categoria (Rosca)
        Busca da tabela riscos (processos)
        TRATAMENTO: Categorias separadas por vírgula
        """
        
        with engine.connect() as conn:
            sql = """
                SELECT 
                    r.categoria
                FROM riscos r
                JOIN processos p ON r.processo_id = p.id
                JOIN auditorias a ON p.auditoria_id = a.id
                WHERE r.categoria IS NOT NULL AND r.categoria != ''
            """
            params = {}
            
            if area_id is not None:
                sql += " AND a.id_area = :area_id"
                params['area_id'] = area_id
            if auditoria_id is not None:
                sql += " AND a.id = :auditoria_id"
                params['auditoria_id'] = auditoria_id
            
            result = conn.execute(text(sql), params).fetchall()
            
            print(f"🔍 Riscos por categoria (raw): {result}")
        
        # ⭐ Processar categorias (separadas por vírgula)
        contagem_categorias = {}
        
        for row in result:
            categoria_raw = row[0] or ''
            
            # ⭐ Dividir por vírgula e limpar espaços
            categorias = [cat.strip() for cat in categoria_raw.split(',') if cat.strip()]
            
            for categoria in categorias:
                contagem_categorias[categoria] = contagem_categorias.get(categoria, 0) + 1
        
        print(f"🔍 Contagem de categorias: {contagem_categorias}")
        
        # ⭐ Mapeamento de cores por categoria
        cores_categoria = {
            "RISCO FINANCEIRO": CORES['primary_dark'],
            "RISCO DE TI": CORES['primary_blue'],
            "RISCO INERENTE": CORES['primary_lighter'],
            "Risco DE INTEGRIDADE": CORES['primary_lightest'],
            "RISCO AMBIENTAL": CORES['blue_light'],
            "RISCO REPUTACIONAL": CORES['blue_lighter'],
        }
        
        # Se não houver categorias
        if not contagem_categorias:
            return {
                "labels": ["Sem dados"],
                "valores": [1],
                "cores": ["#e0e0e0"]
            }
        
        # ⭐ Ordenar por quantidade (decrescente)
        categorias_ordenadas = sorted(
            contagem_categorias.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # ⭐ Pegar apenas as 6 principais (para não poluir o gráfico)
        top_categorias = categorias_ordenadas[:6]
        
        labels = []
        valores = []
        cores = []
        
        for categoria, qtd in top_categorias:
            labels.append(categoria)
            valores.append(qtd)
            cores.append(cores_categoria.get(categoria, "#6c757d"))
        
        # ⭐ Adicionar "Outros" se houver mais categorias
        if len(categorias_ordenadas) > 6:
            total_outros = sum(qtd for _, qtd in categorias_ordenadas[6:])
            labels.append("Outros")
            valores.append(total_outros)
            cores.append("#adb5bd")
        
        return {
            "labels": labels,
            "valores": valores,
            "cores": cores
        }
    

    @staticmethod
    def gerar_top_areas(
        ano: Optional[int] = None
    ) -> Dict[str, Any]:
        """Dados para o gráfico de Top Áreas (Barras)
        
        Filtros: APENAS ANO
        Área e Auditoria NÃO filtram este gráfico
        """
        
        with engine.connect() as conn:
            sql = """
                SELECT 
                    ia.nome_area,
                    COUNT(DISTINCT p.id) as total_processos
                FROM informacoes_area ia
                JOIN processos p ON ia.id_area = p.id_area
                JOIN auditorias a ON p.auditoria_id = a.id
                WHERE p.status = 'Ativo'
            """
            params = {}
            
            # ⭐ APENAS O ANO FILTRA
            if ano is not None:
                sql += " AND a.ano = :ano"
                params['ano'] = ano
            
            sql += " GROUP BY ia.nome_area"
            sql += " ORDER BY total_processos DESC"
            sql += " LIMIT 5"
            
            result = conn.execute(text(sql), params).fetchall()
            
            print(f"🔍 Top áreas - resultado: {result}")
        
        # Se não houver resultados
        if not result:
            return {
                "labels": ["Sem dados"],
                "valores": [0],
                "cores": ["#e0e0e0"]
            }
        
        # ⭐ Função para extrair a sigla (ex: "Gerência Financeira/Setor Contas a Pagar - GFI" → "GFI")
        def extrair_sigla(nome_completo):
            if not nome_completo:
                return "Sem nome"
            # Buscar o que vem depois de " - "
            if ' - ' in nome_completo:
                return nome_completo.split(' - ')[-1].strip()
            # Se não tiver " - ", usar as primeiras letras das palavras
            palavras = nome_completo.split()
            sigla = ''.join([p[0].upper() for p in palavras if p and p[0].isalpha()])
            return sigla[:6] if sigla else nome_completo[:10]  # Limitar a 6 caracteres
        
        # ⭐ Cores para as áreas
        cores = [CORES['primary_dark'], CORES['primary_blue'], CORES['primary_light'], CORES['primary_lighter'], CORES['primary_lightest'], CORES['blue_light'], CORES['blue_lighter'], CORES['blue_lightest']]
        
        labels = []
        valores = []
        cores_usadas = []
        nomes_completos = []  # Para tooltip
        
        for i, row in enumerate(result):
            nome_completo = row[0] or "Área sem nome"
            total = row[1] or 0
            
            sigla = extrair_sigla(nome_completo)
            
            labels.append(sigla)
            valores.append(total)
            cores_usadas.append(cores[i % len(cores)])
            nomes_completos.append(nome_completo)
        
        return {
            "labels": labels,
            "valores": valores,
            "cores": cores_usadas,
            "nomes_completos": nomes_completos  # Para tooltip
        }
    

    @staticmethod
    def gerar_controles_status(
        area_id: Optional[int] = None,
        auditoria_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Dados para o gráfico de controles por natureza (Rosca)
        
        Filtros: Área e Auditoria
        Naturezas: Preditivo, Preventivo, Corretivo
        """
        
        with engine.connect() as conn:
            sql = """
                SELECT 
                    ce.natureza,
                    COUNT(*) as quantidade
                FROM controles_etapa ce
                WHERE ce.status_controle IS NOT NULL
                AND ce.natureza IS NOT NULL
                AND ce.natureza != ''

            """
            params = {}
            

            sql += " GROUP BY ce.natureza"
            
            result = conn.execute(text(sql), params).fetchall()
            
            print(f"🔍 Controles por natureza - resultado: {result}")
        
        # ⭐ Mapeamento das naturezas
        natureza_map = {
            "PREDITIVO": "preditivo",
            "PREVENTIVO": "preventivo",
            "CORRETIVO": "corretivo",
            # Variações comuns
            "Preditiva": "preditivo",
            "Preventiva": "preventivo",
            "Corretiva": "corretivo",
        }
        
        # Inicializar contadores
        dados = {
            "preditivo": 0,
            "preventivo": 0,
            "corretivo": 0
        }
        
        for row in result:
            natureza = row[0] or ''
            qtd = row[1] or 0
            
            # Limpar espaços e normalizar
            natureza_clean = natureza.strip()
            
            if natureza_clean in natureza_map:
                dados[natureza_map[natureza_clean]] += qtd
                print(f"✅ Natureza '{natureza_clean}' → {qtd}")
            else:
                print(f"⚠️ Natureza não mapeada: '{natureza_clean}'")
        
        # ⭐ Se não houver dados
        if sum(dados.values()) == 0:
            return {
                "labels": ["Sem dados"],
                "valores": [1],
                "cores": ["#e0e0e0"]
            }
        
        # Preparar dados para o gráfico
        labels = []
        valores = []
        cores = []
        
        # ⭐ Ordem: Preditivo, Preventivo, Corretivo
        ordem = [
            ("preditivo", "Preditivo", "#17a2b8"),   # Azul
            ("preventivo", "Preventivo", "#28a745"), # Verde
            ("corretivo", "Corretivo", "#dc3545")    # Vermelho
        ]
        
        for chave, label, cor in ordem:
            if dados[chave] > 0:
                labels.append(label)
                valores.append(dados[chave])
                cores.append(cor)
        
        return {
            "labels": labels,
            "valores": valores,
            "cores": cores
        }