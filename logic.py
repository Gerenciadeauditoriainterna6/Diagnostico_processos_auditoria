import os
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import text
from database import engine
from datetime import datetime
import streamlit as st

# --- CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOGO = os.path.join(BASE_DIR, "assets", "logo_fusve.png")
CAMINHO_LOGO2 = os.path.join(BASE_DIR, "assets", "logo_auditoria.png")

#MAPPING_AREAS = {"Gerência de Gente e gestão - GGG": 1, "Gerência de Finanças": 2,"Gerência de TI": 3}

def resetar_timer_sessao():
    """Reseta o timestamp da sessão para a hora atual"""
    if st.session_state.get('autenticado'):
        st.session_state['login_timestamp'] = datetime.now()

# =====================================================
# NOVAS FUNÇÕES PARA AUDITORIAS TRIMESTRAIS
# =====================================================

def criar_nova_auditoria(dados_auditoria):
    """
    Cria uma nova auditoria no banco de dados.
    dados_auditoria deve conter: id_area, titulo, objetivo, escopo, ano, trimestre
    """
    try:
        # Gera o código automático: AUD-SIGLA-ANO-TRIM
        # Primeiro busca a sigla da área
        query_area = text(
            """
            SELECT nome_area FROM informacoes_area WHERE id_area = :id
        """)
        with engine.connect() as conn:
            nome_area = conn.execute(query_area, {"id": dados_auditoria['id_area']}).scalar()

        # Extrai sigla (Ex: "Gerência de Gente e Gestão - GGG" -> "GGG")
        sigla = nome_area.split('-')[-1].strip() if '-' in nome_area else nome_area[:3]
        codigo = f"AUD-{sigla}-{dados_auditoria['ano']}-{dados_auditoria['trimestre']}T"

        query = text(
            """
            INSERT INTO auditorias
            (codigo_auditorias, id_area, titulo, objetivo, scopo, ano, timestre,
            data_inicio, data_fim, status, responsavel_equipe)
            VALUES
            (:codigo, :id_area, :titutlo, :objetivo, :escopo, :ano, :trimestre,
            :data_inicio, :data_fim, :status, :responsavel)
            RETURNING id
        """)

        with engine.begin() as conn:
            auditoria_id = conn.execute(query, {
                "codigo": codigo,
                "id_area": dados_auditoria['id_area'],
                "titulo": dados_auditoria['titulo'],
                "objetivo": dados_auditoria.get('objetivo', ''),
                "escopo": dados_auditoria.get('escopo', ''),
                "ano": dados_auditoria['ano'],
                "trimestre": dados_auditoria['trimestre'],
                "data_inicio": dados_auditoria.get('data_inicio'),
                "data_fim": dados_auditoria.get('data_fim'),
                "status": dados_auditoria.get('status', 'Planejamento'),
                "responsavel": dados_auditoria.get('responsavel_equipe', [])
            }).scalar()

        return auditoria_id, codigo
    except Exception as e:
        print(f"Erro ao criar auditoria: {e}")
        return None, None

def listar_auditorias_por_ano(ano=None):
    """
    Retorna todas as auditorias, opcionalmente filtradas por ano
    """

    if ano:
        query = text(
            """
            SELECT a.*, i.nome_area
            FROM auditorias a
            JOIN informacoes_area i ON a.id_area = i.id_area
            WHERE a.ano = :ano
            ORDER BY a.ano DESC, a.trimestre
        """)
        params = {"ano": ano}
    else:
        query = text("""
            SELECT a.*, i.nome_area 
            FROM auditorias a
            JOIN informacoes_area i ON a.id_area = i.id_area
            ORDER BY a.ano DESC, a.trimestre
        """)
        params = {}

    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)

def buscar_auditoria_por_id(auditoria_id):
    """
    Busca detalhes completos de uma auditoria específica
    """
    query = text("""
        SELECT a.*, i.nome_area, i.gestor
        FROM auditorias a
        JOIN informacoes_area i ON a.id_area = i.id_area
        WHERE a.id = :id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"id": auditoria_id}).mappings().first()
        return dict(result) if result else None

def vincular_processo_a_auditoria(auditoria_id, processo_id, motivo=""):
    """
    Vincula um processo a uma auditoria (seleciona para ser auditado)
    """
    try:
        query = text("""
            INSERT INTO auditoria_processos (auditoria_id, processo_id, motivo_selecao)
            VALUES (:auditoria_id, :processo_id, :motivo)
            ON CONFLICT (auditoria_id, processo_id) DO NOTHING
            RETURNING id
        """)
        
        with engine.begin() as conn:
            result = conn.execute(query, {
                "auditoria_id": auditoria_id,
                "processo_id": processo_id,
                "motivo": motivo
            }).scalar()
            
        return result is not None
    except Exception as e:
        print(f"Erro ao vincular processo: {e}")
        return False
    
def listar_processos_da_auditoria(auditoria_id):
    """
    Retorna todos os processos vinculados a uma auditoria
    """
    query = text("""
        SELECT ap.*, p.codigo_processo, p.nome_processo, p.area,
               COUNT(r.id) as total_riscos,
               MAX(r.score_risco) as maior_risco
        FROM auditoria_processos ap
        JOIN processos p ON ap.processo_id = p.id
        LEFT JOIN riscos r ON p.id = r.processo_id
        WHERE ap.auditoria_id = :id
        GROUP BY ap.id, p.codigo_processo, p.nome_processo, p.area
        ORDER BY p.codigo_processo
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"id": auditoria_id})

def salvar_checklist_eficacia(dados_checklist):
    """
    Salva uma resposta de checklist
    dados_checklist deve conter: auditoria_id, processo_id, pilar, pergunta, 
                                  peso, resposta, pontuacao, evidencia, conclusao
    """
    try:
        query = text("""
            INSERT INTO checklists_eficacia 
            (auditoria_id, processo_id, pilar, pergunta, peso, 
             resposta, pontuacao, evidencia, conclusao)
            VALUES 
            (:auditoria_id, :processo_id, :pilar, :pergunta, :peso,
             :resposta, :pontuacao, :evidencia, :conclusao)
            RETURNING id
        """)
        
        with engine.begin() as conn:
            checklist_id = conn.execute(query, dados_checklist).scalar()
            
        return checklist_id
    except Exception as e:
        print(f"Erro ao salvar checklist: {e}")
        return None

def listar_checklists_da_auditoria(auditoria_id, processo_id=None, pilar=None):
    """
    Lista checklists de uma auditoria, com filtros opcionais
    """
    query = text("""
        SELECT c.*, p.codigo_processo, p.nome_processo
        FROM checklists_eficacia c
        JOIN processos p ON c.processo_id = p.id
        WHERE c.auditoria_id = :auditoria_id
        AND (:processo_id IS NULL OR c.processo_id = :processo_id)
        AND (:pilar IS NULL OR c.pilar = :pilar)
        ORDER BY c.pilar, c.id
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={
            "auditoria_id": auditoria_id,
            "processo_id": processo_id,
            "pilar": pilar
        })

def calcular_maturidade_por_pilar(auditoria_id, pilar):
    """
    Calcula a média de pontuação para um pilar específico
    """
    query = text("""
        SELECT AVG(pontuacao) as media, COUNT(*) as total_perguntas
        FROM checklists_eficacia
        WHERE auditoria_id = :auditoria_id
        AND pilar = :pilar
        AND pontuacao IS NOT NULL
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {
            "auditoria_id": auditoria_id,
            "pilar": pilar
        }).mappings().first()
        
        if result and result['media']:
            return round(result['media'], 2), result['total_perguntas']
        return 0, 0

def salvar_conclusao_auditoria(dados_conclusao):
    """
    Salva o parecer final da auditoria
    dados_conclusao deve conter: auditoria_id, resumo_executivo, pontos_fortes,
                                  oportunidades_melhoria, recomendacoes, parecer_final
    """
    try:
        query = text("""
            INSERT INTO conclusao_auditoria 
            (auditoria_id, resumo_executivo, pontos_fortes, oportunidades_melhoria,
             recomendacoes, parecer_final, data_conclusao, pdf_relatorio)
            VALUES 
            (:auditoria_id, :resumo, :pontos_fortes, :oportunidades,
             :recomendacoes, :parecer, :data_conclusao, :pdf)
            ON CONFLICT (auditoria_id) DO UPDATE SET
                resumo_executivo = EXCLUDED.resumo_executivo,
                pontos_fortes = EXCLUDED.pontos_fortes,
                oportunidades_melhoria = EXCLUDED.oportunidades_melhoria,
                recomendacoes = EXCLUDED.recomendacoes,
                parecer_final = EXCLUDED.parecer_final,
                data_conclusao = EXCLUDED.data_conclusao,
                pdf_relatorio = EXCLUDED.pdf_relatorio
            RETURNING id
        """)
        
        with engine.begin() as conn:
            conclusao_id = conn.execute(query, {
                "auditoria_id": dados_conclusao['auditoria_id'],
                "resumo": dados_conclusao.get('resumo_executivo', ''),
                "pontos_fortes": dados_conclusao.get('pontos_fortes', []),
                "oportunidades": dados_conclusao.get('oportunidades_melhoria', []),
                "recomendacoes": dados_conclusao.get('recomendacoes', []),
                "parecer": dados_conclusao.get('parecer_final', ''),
                "data_conclusao": dados_conclusao.get('data_conclusao'),
                "pdf": dados_conclusao.get('pdf_relatorio')
            }).scalar()
            
        return conclusao_id
    except Exception as e:
        print(f"Erro ao salvar conclusão: {e}")
        return None
    
def buscar_conclusao_auditoria(auditoria_id):
    """
    Busca a conclusão de uma auditoria específica
    """
    query = text("SELECT * FROM conclusao_auditoria WHERE auditoria_id = :id")
    with engine.connect() as conn:
        result = conn.execute(query, {"id": auditoria_id}).mappings().first()
        return dict(result) if result else None

def get_resumo_trimestre(ano, trimestre):
    """
    Retorna um resumo consolidado do trimestre para dashboard
    """
    query = text("""
        SELECT 
            a.id,
            a.codigo_auditoria,
            i.nome_area,
            a.status,
            COUNT(DISTINCT ap.processo_id) as total_processos,
            COUNT(DISTINCT c.id) as total_checklists,
            AVG(c.pontuacao) as media_geral
        FROM auditorias a
        JOIN informacoes_area i ON a.id_area = i.id_area
        LEFT JOIN auditoria_processos ap ON a.id = ap.auditoria_id
        LEFT JOIN checklists_eficacia c ON a.id = c.auditoria_id
        WHERE a.ano = :ano AND a.trimestre = :trimestre
        GROUP BY a.id, i.nome_area
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"ano": ano, "trimestre": trimestre})

def listar_processos_da_auditoria_com_riscos(auditoria_id):
    """
    Retorna os processos vinculados a uma auditoria com informações de riscos
    """
    query = text("""
        SELECT 
            ap.*,
            p.codigo_processo,
            p.nome_processo,
            p.area,
            COUNT(r.id) as total_riscos,
            MAX(r.score_risco) as maior_risco,
            STRING_AGG(DISTINCT r.impacto || ' - ' || r.probabilidade, '; ') as riscos_resumo
        FROM auditoria_processos ap
        JOIN processos p ON ap.processo_id = p.id
        LEFT JOIN riscos r ON p.id = r.processo_id
        WHERE ap.auditoria_id = :auditoria_id
        GROUP BY ap.id, p.codigo_processo, p.nome_processo, p.area
        ORDER BY maior_risco DESC NULLS LAST, p.codigo_processo
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"auditoria_id": auditoria_id})

def get_cores_por_score(score):
    """Retorna cor e emoji baseado no score do risco"""
    if score is None:
        return "#6c757d", "⚪"  # Cinza para sem risco
    elif score >= 12:
        return "#dc3545", "🔴"  # Vermelho - Muito Alto
    elif score >= 8:
        return "#fd7e14", "🟠"  # Laranja - Alto
    elif score >= 4:
        return "#ffc107", "🟡"  # Amarelo - Médio
    else:
        return "#28a745", "🟢"  # Verde - Baixo

def listar_processos_disponiveis_para_auditoria(auditoria_id, id_area):
    """
    Lista processos da área que AINDA NÃO estão vinculados a esta auditoria.
    Retorna DataFrame com id, codigo_processo, nome_processo, maior_risco, total_riscos
    """
    query = text("""
        SELECT 
            p.id,
            p.codigo_processo,
            p.nome_processo,
            COALESCE(MAX(r.score_risco), 0) as maior_risco,
            COUNT(r.id) as total_riscos,
            STRING_AGG(DISTINCT r.impacto || ' - ' || r.probabilidade, '; ') as riscos_resumo
        FROM processos p
        LEFT JOIN riscos r ON p.id = r.processo_id
        WHERE p.id_area = :id_area
        AND p.id NOT IN (
            SELECT processo_id 
            FROM auditoria_processos 
            WHERE auditoria_id = :auditoria_id
        )
        GROUP BY p.id
        ORDER BY maior_risco DESC, p.codigo_processo
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={
                "auditoria_id": auditoria_id,
                "id_area": id_area
            })
            return df
    except Exception as e:
        print(f"Erro ao listar processos disponíveis: {e}")
        return pd.DataFrame()

# =====================================================
# NOVAS FUNÇÕES PARA AUDITORIAS TRIMESTRAIS
# =====================================================

def buscar_processo_por_codigo(codigo):
    """Busca todos os detalhes de um processo e o nome do gestor da área."""
    query = text("""
            SELECT p.*, i.nome_area, i.gestor AS responsavel_area
            FROM processos p
            JOIN informacoes_area i ON p.id_area = i.id_area
            WHERE p.codigo_processo = :c
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"c": str(codigo)}).mappings().first()
        return dict(result) if result else None

def salvar_etapa_no_banco(dados_etapa, auditoria_id=None):
    """Salva os dados de uma etapa no banco de dados, opcionalmente vinculada a uma auditoria."""
    try:
        if auditoria_id:
            query = text("""
                INSERT INTO etapas_processo (
                    processo_id, auditoria_id, codigo_etapa, descricao_etapa, oque_faz, 
                    status_etapa, como_e_feito, objetivo_etapa, realizado_corretamente, 
                    link_diagrama_etapa, politica_interna, analise_critica,
                    sugestao_melhoria, necessidade_implantacao, ganho_previsto, 
                    obrigacoes_regulatorias, criticidade_etapa, manual_processo_link
                ) VALUES (
                    :p_id, :auditoria_id, :cod, :desc, :oque, :status, :como, :obj, 
                    :real, :link_d, :pol, :ana, :sug, :nec, :gan, :obri, :crit, :man
                )
            """)
            dados_etapa['auditoria_id'] = auditoria_id
        else:
            query = text("""
                INSERT INTO etapas_processo (
                    processo_id, codigo_etapa, descricao_etapa, oque_faz, status_etapa, 
                    como_e_feito, objetivo_etapa, realizado_corretamente, link_diagrama_etapa, 
                    politica_interna, analise_critica, sugestao_melhoria, necessidade_implantacao, 
                    ganho_previsto, obrigacoes_regulatorias, criticidade_etapa, manual_processo_link
                ) VALUES (
                    :p_id, :cod, :desc, :oque, :status, :como, :obj, :real, :link_d, 
                    :pol, :ana, :sug, :nec, :gan, :obri, :crit, :man
                )
            """)
        
        with engine.begin() as conn:
            conn.execute(query, dados_etapa)
            
        return True
    except Exception as e:
        print(f"Erro ao salvar etapa: {e}")
        return False
    
def atualizar_etapa_no_banco(dados):
    """Atualiza os dados de uma etapa existente"""
    try:
        query = text("""
            UPDATE etapas_processo SET
                descricao_etapa = :desc,
                oque_faz = :oque,
                como_e_feito = :como,
                objetivo_etapa = :obj,
                status_etapa = :status,
                realizado_corretamente = :real,
                criticidade_etapa = :crit,
                executor = :exec,
                link_diagrama_etapa = :link_d,
                manual_processo_link = :link_m,
                politica_interna = :pol,
                analise_critica = :ana,
                sugestao_melhoria = :sug,
                necessidade_implantacao = :nec,
                ganho_previsto = :gan,
                obrigacoes_regulatorias = :obri,
                updated_at = NOW()
            WHERE id = :etapa_id
        """)
        
        with engine.begin() as conn:
            conn.execute(query, {
                "etapa_id": dados['etapa_id'],
                "desc": dados['desc'],
                "oque": dados['oque'],
                "como": dados['como'],
                "obj": dados['obj'],
                "status": dados['status'],
                "real": dados['real'],
                "crit": dados['crit'],
                "exec": dados['exec'],
                "link_d": dados['link_d'],
                "link_m": dados['link_m'],
                "pol": dados['pol'],
                "ana": dados['ana'],
                "sug": dados['sug'],
                "nec": dados['nec'],
                "gan": dados['gan'],
                "obri": dados['obri']
            })
            
        return True
    except Exception as e:
        print(f"Erro ao atualizar etapa: {e}")
        return False

def listar_etapas_do_processo(processo_id, auditoria_id=None):
    """
    Retorna todas as etapas de um processo.
    Se auditoria_id for fornecido, filtra por auditoria.
    """
    if auditoria_id:
        query = text("""
            SELECT * FROM etapas_processo 
            WHERE processo_id = :id AND auditoria_id = :auditoria_id 
            ORDER BY codigo_etapa
        """)
        params = {"id": processo_id, "auditoria_id": auditoria_id}
    else:
        query = text("SELECT * FROM etapas_processo WHERE processo_id = :id ORDER BY codigo_etapa")
        params = {"id": processo_id}
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)

def obter_proximo_codigo_etapa(processo_id, codigo_processo):
    """Gera o código 1.2.1 baseado no número de etapas existentes."""
    query = text("SELECT COUNT(*) FROM etapas_processo WHERE processo_id = :id")
    with engine.connect() as conn:
        contagem = conn.execute(query, {"id": processo_id}).scalar() or 0
    return f"{codigo_processo}.{contagem + 1}"
  
def carregar_areas_banco():
    """ Busca áreas no Banco de Dados e retorna um dicionário {nome: id}."""
    query = text("SELECT id_area, nome_area FROM informacoes_area")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Transforma o DataFrame em um dicionário {'Nome da Área': id_area}
    # Zip junta as duas colunas: a primeira vira chave, a segunda vira valor
    return dict(zip(df['nome_area'], df['id_area']))

def salvar_risco_etapa(dados, auditoria_id=None):
    """Salva risco de etapa, opcionalmente vinculado a uma auditoria"""
    if auditoria_id:
        query = text("""
            INSERT INTO riscos_etapa 
            (etapa_id, auditoria_id, categoria, fator_risco, consequencia, info_adicional, 
             financeiro, ativo, origem, doc_legal, impacto, probabilidade, magnitude, 
             apetite, tratamento)
            VALUES 
            (:etapa_id, :auditoria_id, :cat, :fator, :cons, :info, :fin, :ativo, 
             :ori, :doc, :imp, :prob, :mag, :apet, :trat)
        """)
        dados['auditoria_id'] = auditoria_id
    else:
        query = text("""
            INSERT INTO riscos_etapa 
            (etapa_id, categoria, fator_risco, consequencia, info_adicional, financeiro, 
             ativo, origem, doc_legal, impacto, probabilidade, magnitude, apetite, tratamento)
            VALUES 
            (:etapa_id, :cat, :fator, :cons, :info, :fin, :ativo, :ori, :doc, 
             :imp, :prob, :mag, :apet, :trat)
        """)
    
    with engine.begin() as conn:
        conn.execute(query, dados)
        return True

def listar_riscos_etapa(etapa_id, auditoria_id=None):
    """Lista riscos de uma etapa, opcionalmente filtrados por auditoria"""
    if auditoria_id:
        query = text("SELECT * FROM riscos_etapa WHERE etapa_id = :e_id AND auditoria_id = :auditoria_id")
        params = {"e_id": etapa_id, "auditoria_id": auditoria_id}
    else:
        query = text("SELECT * FROM riscos_etapa WHERE etapa_id = :e_id")
        params = {"e_id": etapa_id}
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)

def buscar_todos_processos():
    query = text("""
            SELECT 
                p.area,
                p.codigo_processo,
                p.nome_processo,
                i.gestor,
                p.aprovacao
            FROM processos p
            JOIN informacoes_area i ON p.area = i.nome_area
            ORDER BY
                string_to_array(p.codigo_processo, '.')::int[]    
                """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

MAPA_RISCO = {
    ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14, ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
    ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10, ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
    ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6, ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
    ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2, ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
}

# --- CLASSE DO PDF ---
class PDF(FPDF):
    def header(self):
        y_posicao = 10
        altura_fixa = 12 # Altura em mm

        # Logo FUSVE (Esquerda - Fixo em 10mm)
        if os.path.exists(CAMINHO_LOGO):
            self.image(CAMINHO_LOGO, 10, y_posicao, h=altura_fixa)
            
        # Logo Auditoria (Direita - Cálculo Automático)
        if os.path.exists(CAMINHO_LOGO2):
            # Para descobrir a largura, o FPDF permite calcular ou estimar.
            # Se você quer a logo à direita, force o X para um valor alto,
            # mas vamos garantir que ele não corte:
            
            largura_logo_auditoria = 40 # Defina o tamanho que você deseja para ela
            posicao_x_direita = 210 - 10 - largura_logo_auditoria
            
            self.image(CAMINHO_LOGO2, posicao_x_direita, y_posicao, w=largura_logo_auditoria, h=altura_fixa)

        # Textos Centralizados
        self.set_y(12)
        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, "RELATÓRIO DE VALIDAÇÃO DO PROCESSO", border=False, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font('helvetica', "", 10)
        self.cell(0, 5, "Diagnóstico de Auditoria Interna - FUSVE", border=False, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Linha e espaçamento
        self.set_y(45)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_x(170)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

# --- LÓGICA DE BANCO DE DADOS ---
def obter_proximo_codigo(id_area):
    query = text("SELECT COUNT(*) FROM processos WHERE id_area = :id")
    with engine.connect() as conn:
        contagem = conn.execute(query, {"id": id_area}).scalar() or 0
    return f"{id_area}.{contagem + 1}"

def processar_codigo_inteligente():
    """Gera o código do processo e verifica se já existe para carregar dados"""
    resetar_timer_sessao()
    
    id_area = st.session_state.get("id_area_selecionado") 
    nome = st.session_state.get("input_processo", "").strip()
    
    if not id_area or not nome:
        st.session_state['codigo_processo_display'] = ""
        return
    
    # Verificar se já existe um processo com este nome na mesma área
    query_check = text("""
        SELECT id, codigo_processo, objetivo, executor, descricao, 
               etapa_ini, etapa_fim, produto
        FROM processos 
        WHERE id_area = :id_area AND nome_processo = :nome
    """)
    
    with engine.connect() as conn:
        resultado = conn.execute(query_check, {
            "id_area": id_area, 
            "nome": nome
        }).mappings().first()
    
    if resultado:
        # Processo já existe - carregar todos os dados
        st.session_state['novo_processo_existente_id'] = resultado['id']
        st.session_state['codigo_processo_display'] = resultado['codigo_processo']
        
        # NÃO carregar os detalhamentos para não enganar o usuário
        # NÃO setar info_basicas_salvas = True

        # Mostrar aviso claro para o usuário
        st.warning(f"⚠️ O processo '{nome}' já existe na área selecionada. "
                   f"Por favor, utilize a aba '✏️ Editar Processo Existente' para modificá-lo.")
        
        # Limpar campos que poderiam dar a impressão de que é um novo processo
        st.session_state['input_objetivo'] = ""
        st.session_state['input_descricao'] = ""
        st.session_state['input_etapa_ini'] = ""
        st.session_state['input_etapa_fim'] = ""
        st.session_state['input_produto'] = ""
        
        return
        
    else:

        # Processo novo - gerar código baseado no último código da área
        ultimo_codigo_query = text("""
            SELECT codigo_processo 
            FROM processos 
            WHERE id_area = :id_area
            ORDER BY 
                CAST(split_part(codigo_processo, '.', 1) AS INTEGER),
                CAST(split_part(codigo_processo, '.', 2) AS INTEGER) DESC
            LIMIT 1
        """)
        
        with engine.connect() as conn:
            ultimo = conn.execute(ultimo_codigo_query, {"id_area": id_area}).scalar()
        
        if ultimo:
            partes = ultimo.split('.')
            if len(partes) >= 2:
                ultimo_numero = int(partes[1])
                novo_numero = ultimo_numero + 1
                codigo = f"{id_area}.{novo_numero}"
            else:
                codigo = f"{id_area}.1"
        else:
            codigo = f"{id_area}.1"
        
        st.session_state['codigo_processo_display'] = codigo
        # Limpar dados de edição anterior
        if 'processo_existente_id' in st.session_state:
            st.session_state.pop('processo_existente_id', None)
        # Limpar campos de detalhamento (opcional)
        st.session_state['input_objetivo'] = ""
        st.session_state['input_descricao'] = ""
        st.session_state['input_etapa_ini'] = ""
        st.session_state['input_etapa_fim'] = ""
        st.session_state['input_produto'] = ""
        st.session_state['info_basicas_salvas'] = False

def normalizar_valor_risco(valor):
    """
    Converte valores de risco para o formato correto:
    'MUITO ALTO' → 'Muito Alto'
    'ALTO' → 'Alto'
    'MÉDIO' → 'Médio'
    'BAIXO' → 'Baixo'
    """
    if not valor:
        return "Baixo"
    
    valor_str = str(valor).strip().upper()
    
    if valor_str == 'MUITO ALTO':
        return "Muito Alto"
    elif valor_str == 'ALTO':
        return "Alto"
    elif valor_str == 'MÉDIO' or valor_str == 'MEDIO':
        return "Médio"
    elif valor_str == 'BAIXO':
        return "Baixo"
    else:
        # Se não for nenhum dos padrões, tenta encontrar no texto
        if 'MUITO ALTO' in valor_str:
            return "Muito Alto"
        elif 'ALTO' in valor_str:
            return "Alto"
        elif 'MÉDIO' in valor_str or 'MEDIO' in valor_str:
            return "Médio"
        else:
            return "Baixo"


def salvar_no_banco():
    resetar_timer_sessao()
    try:
        with engine.begin() as conn:
            id_area_val = st.session_state.get("id_area_selecionado")
            nome_area_val = st.session_state.get("area_selectbox")
            nome_val = st.session_state.get("input_processo", "").strip()

            # === PRIMEIRO: VERIFICAR SE O PROCESSO JÁ EXISTE ===
            check_query = text("""
                SELECT id FROM processos 
                WHERE id_area = :id_area AND nome_processo = :nome
            """)
            existing = conn.execute(check_query, {
                "id_area": id_area_val,
                "nome": nome_val
            }).fetchone()

            if existing:
                # === MODO EDIÇÃO: Atualizar processo existente ===
                processo_id = existing[0]
                st.session_state['processo_existente_id'] = processo_id

                sql_update = text("""
                    UPDATE processos 
                    SET objetivo=:o, descricao=:d, 
                        etapa_ini=:ei, etapa_fim=:ef, produto=:p
                    WHERE id = :pid
                """)

                conn.execute(sql_update, {
                    "pid": processo_id,
                    "o": st.session_state.get('input_objetivo', ''),
                    "d": st.session_state.get('input_descricao', ''),
                    "ei": st.session_state.get('input_etapa_ini', ''),
                    "ef": st.session_state.get('input_etapa_fim', ''),
                    "p": st.session_state.get('input_produto', '')
                })

            else:
                # === MODO CRIAÇÃO: Inserir novo processo ===
                codigo_processo = st.session_state.get('codigo_processo_display', '')

                sql_insert = text("""
                    INSERT INTO processos 
                    (id_area, area, codigo_processo, nome_processo, objetivo, 
                     descricao, etapa_ini, etapa_fim, produto, status, categoria) 
                    VALUES 
                    (:id_a, :a, :c, :n, :o, :d, :ei, :ef, :p, :st, :cat) 
                    RETURNING id
                """)

                params_insert = {
                    "id_a": id_area_val,
                    "a": nome_area_val,
                    "c": codigo_processo,
                    "n": nome_val,
                    "o": st.session_state.get('input_objetivo', ''),
                    "d": st.session_state.get('input_descricao', ''),
                    "ei": st.session_state.get('input_etapa_ini', ''),
                    "ef": st.session_state.get('input_etapa_fim', ''),
                    "p": st.session_state.get('input_produto', ''),
                    "st": "Ativo",
                    "cat": "Geral"
                }

                processo_id = conn.execute(sql_insert, params_insert).scalar()
                st.session_state['processo_existente_id'] = processo_id

            # ===== RISCOS: REMOVE OS ANTIGOS E INSERE OS NOVOS =====
            conn.execute(
                text("DELETE FROM riscos WHERE processo_id = :pid"),
                {"pid": processo_id}
            )

            sql_risco = text("""
                INSERT INTO riscos 
                (processo_id, nome_risco, fator_risco, melhoria, impacto, 
                 probabilidade, apetite_risco, motivo_risco, score_risco) 
                VALUES 
                (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo, :score)
                RETURNING id
            """)

            for i in range(len(st.session_state['riscos'])):
                imp = st.session_state.get(f"imp_{i}")
                prob = st.session_state.get(f"prob_{i}")
                score = MAPA_RISCO.get((imp, prob), 0)

                result = conn.execute(sql_risco, {
                    "pid": processo_id,
                    "nome": st.session_state.get(f"nome_{i}"),
                    "fator": st.session_state.get(f"fator_{i}"),
                    "melhoria": st.session_state.get(f"melhoria_{i}"),
                    "imp": imp,
                    "prob": prob,
                    "apetite": st.session_state.get(f"apetite_{i}"),
                    "motivo": st.session_state.get(f"motivo_{i}"),
                    "score": score
                })

                risco_id = result.scalar()

                # === SALVAR CATEGORIAS DO RISCO ===
                categorias_ids = st.session_state.get(f"categorias_{i}", [])
                if categorias_ids:
                    for cat_id in categorias_ids:
                        conn.execute(
                            text("INSERT INTO risco_categorias (risco_id, categoria_id) VALUES (:rid, :cid)"),
                            {"rid": risco_id, "cid": cat_id}
                        )

            st.session_state['ultimo_processo_id'] = processo_id

        return True

    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def buscar_processos_pendentes():
    query = text("""
        SELECT DISTINCT 
            p.id, 
            p.codigo_processo, 
            i.nome_area, 
            p.nome_processo,
            string_to_array(p.codigo_processo, '.')::int[] AS ordem_logica -- Incluído aqui
        FROM processos p
        JOIN riscos r ON p.id = r.processo_id
        JOIN informacoes_area i ON p.id_area = i.id_area
        WHERE r.relatorio_gerado != 'Sim' OR r.relatorio_gerado IS NULL
        ORDER BY 
            ordem_logica -- Agora usamos o apelido que está no SELECT
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def buscar_dados_do_processo(codigo_processo):
    # Usamos o JOIN para buscar o nome da área baseado no ID
    query = text("""
        SELECT 
            i.nome_area AS "AREA", 
            p.nome_processo AS "PROCESSO", 
            p.objetivo AS "OBJETIVO",
            p.descricao AS "DESCRIÇÃO DO PROCESSO", 
            p.executor AS "QUEM EXECUTA?",
            p.produto AS "PRODUTO DO PROCESSO", 
            p.etapa_ini AS "ETAPA INICIAL",
            p.etapa_fim AS "ETAPA FINAL", 
            r.nome_risco AS "RISCO",
            r.fator_risco AS "FATOR DE RISCO", 
            r.melhoria AS "O QUE PODERIA MELHORAR?",
            r.impacto AS "IMPACTO", 
            r.probabilidade AS "PROBABILIDADE",
            r.score_risco AS "RISCO BRUTO"
        FROM processos p
        JOIN riscos r ON p.id = r.processo_id
        JOIN informacoes_area i ON p.id_area = i.id_area
        WHERE p.codigo_processo = :codigo
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"codigo": codigo_processo})

def draw_table_header(pdf, headers, widths):
    pdf.set_fill_color(200, 220, 255) # Cor de fundo azul claro
    pdf.set_font('helvetica', "B", 6)
    
    line_h = 5
    padding = 1
    
    # 1. Pré-processa os cabeçalhos (quebra as linhas se necessário)
    wrapped_headers = [wrap_text_lines(pdf, h, w - 2*padding) for h, w in zip(headers, widths)]
    
    # 2. Calcula a altura necessária para o cabeçalho (baseado na linha mais longa)
    max_lines = max(len(col) for col in wrapped_headers)
    header_height = max_lines * line_h + 2 # + 2 de respiro
    
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    
    # 3. Desenha cada célula do cabeçalho
    for i, (lines, w) in enumerate(zip(wrapped_headers, widths)):
        x_col = x_start + sum(widths[:i])
        
        # Desenha o fundo e a borda
        pdf.rect(x_col, y_start, w, header_height, style='F') # 'F' preenche
        pdf.rect(x_col, y_start, w, header_height)            # Desenha borda
        
        # Centraliza o texto verticalmente dentro do cabeçalho
        # Se max_lines for maior que a qtd de linhas desta célula, centralizamos visualmente
        offset_y = (header_height - (len(lines) * line_h)) / 2
        
        for j, line in enumerate(lines):
            pdf.set_xy(x_col + padding, y_start + offset_y + (j * line_h))
            pdf.cell(w - 2*padding, line_h, line, align="C")
            
    # 4. Posiciona o cursor para começar a tabela exatamente abaixo do cabeçalho
    pdf.set_xy(x_start, y_start + header_height)

# --- 1. A FUNÇÃO DE AJUDA ---
def wrap_text_lines(pdf_obj, text, width):
    """Calcula a quebra de texto por largura."""
    paragraphs = str(text).splitlines() or ['']
    out_lines = []
    for para in paragraphs:
        words = para.split()
        if not words:
            out_lines.append('')
            continue
        cur = ''
        for w in words:
            test = (cur + ' ' + w).strip()
            if pdf_obj.get_string_width(test) <= width:
                cur = test
            else:
                if cur:
                    out_lines.append(cur)
                part = ''
                for ch in w:
                    if pdf_obj.get_string_width(part + ch) <= width:
                        part += ch
                    else:
                        if part:
                            out_lines.append(part)
                        part = ch
                cur = part
        if cur:
            out_lines.append(cur)
    return out_lines

# --- 2. A FUNÇÃO QUE DESENHA A LINHA ---
def draw_table_row(pdf, data, widths, headers):
    line_h = 5
    padding = 2
    
    # Agora ela encontra a função wrap_text_lines acima!
    wrapped = []
    for i, item in enumerate(data):
        wrapped.append(wrap_text_lines(pdf, str(item), widths[i] - 2*padding))
    
    max_lines = max(len(col) for col in wrapped)
    altura_linha = max_lines * line_h
    
    # Verifica quebra de página
    if pdf.get_y() + altura_linha > (pdf.h - pdf.b_margin):
        pdf.add_page()
        # Certifique-se de que sua função draw_table_header está definida neste mesmo arquivo ou importada
        draw_table_header(pdf, headers, widths) 
    
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    
    for i, (w, lines_list) in enumerate(zip(widths, wrapped)):
        x_col = x_start + sum(widths[:i])
        pdf.rect(x_col, y_start, w, altura_linha)
        
        for j, line in enumerate(lines_list):
            pdf.set_xy(x_col + padding, y_start + (j * line_h) + padding/2)
            pdf.cell(w - 2*padding, line_h, line, border=0, align="L")
            
    pdf.set_xy(x_start, y_start + altura_linha)

def gerar_pdf_em_memoria(id_proc):
    df_processo = buscar_dados_do_processo(id_proc)
    if df_processo.empty: return None

    pdf = PDF()
    pdf.add_page()
    primeira_linha = df_processo.iloc[0]

    # --- Cabeçalho e Detalhes ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, f"ID DO PROCESSO: {id_proc}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.cell(0, 8, f"ÁREA: {primeira_linha['AREA']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(30, 8, "PROCESSO:", border=False)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, str(primeira_linha['PROCESSO']), border=0, align="L")
    
    pdf.ln(2)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "OBJETIVO DO PROCESSO:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(0, 6, str(primeira_linha['OBJETIVO']))

    pdf.ln(2)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "DESCRIÇÃO DETALHADA:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(0, 6, str(primeira_linha['DESCRIÇÃO DO PROCESSO']))
    
    pdf.ln(5)

    # --- Tabela ---
    headers = ["RISCO", "FATOR DE RISCO", "O QUE PODERIA MELHORAR?", "IMPACTO", "PROBABILIDADE", "RISCO BRUTO"]
    widths = [50, 40, 40, 15, 15, 20]

    draw_table_header(pdf, headers, widths)

    for _, linha in df_processo.iterrows():
        data = [
            linha['RISCO'],
            linha['FATOR DE RISCO'],
            linha['O QUE PODERIA MELHORAR?'],
            linha['IMPACTO'],
            linha['PROBABILIDADE'],
            int(linha['RISCO BRUTO'])
        ]
        draw_table_row(pdf, data, widths, headers)
    
    # --- Seção de Assinaturas (Ao final da página) ---
    posicao_ancora = 240
    
    # Se a tabela não chegou no final, pula para a âncora
    if pdf.get_y() < posicao_ancora:
        pdf.set_y(posicao_ancora)
    
    # 1. Desenha a Data
    data_hoje = datetime.now()
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    data_formatada = f"Vassouras, {data_hoje.day} de {meses[data_hoje.month - 1]} de {data_hoje.year}."
    
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, data_formatada, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # 2. Desenha as assinaturas
    y_assinatura = pdf.get_y() + 10
    pdf.line(20, y_assinatura, 90, y_assinatura)
    pdf.line(110, y_assinatura, 180, y_assinatura)
    
    pdf.set_y(y_assinatura + 2)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(90, 5, "Gerência", align="C")
    pdf.cell(90, 5, "Superintendência", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # --- IMPORTANTE: O Retorno ---
    return pdf.output(dest='S')

def get_estilo_risco(score):
    if score >= 12:
        return "#ff0000", "🔴" 
    elif score >= 8:
        return "#f0ad4e", "🟠" 
    elif score >= 4:
        return "#f7ed94", "🟡" 
    else:
        return "#5cb85c", "🟢"

def salvar_controle_no_banco(dados):
    query = text("""
        INSERT INTO controles_etapa (
            risco_id, risco_avaliacao, nome_controle, como_executado, 
            objetivo_controle, periodicidade_execucao, evidencia_realizacao, 
            forma_execucao, natureza, status_controle, data_atualizacao, 
            frequencia_evidencia, responsaveis_tratamento, causa_motivo
        ) VALUES (
            :risco_id, :aval, :nome, :como, 
            :obj, :periodo, :evid, 
            :forma, :natureza, :status, :data_atu, 
            :freq, :resp, :causa
        )
    """)
    
    try:
        # Importante: converter para os tipos corretos antes de enviar
        with engine.begin() as conn:
            conn.execute(query, {
                "risco_id": int(dados.get('risco_id')),
                "aval": str(dados.get('avaliacao', '')),
                "nome": str(dados.get('nome', '')),
                "como": str(dados.get('como_executado', '')),
                "obj": str(dados.get('objetivo', '')),
                "periodo": str(dados.get('periodicidade', '')),
                "evid": str(dados.get('evidencia', '')), 
                "forma": str(dados.get('forma', '')),
                "natureza": str(dados.get('natureza', '')),
                "status": str(dados.get('status', '')),
                "data_atu": dados.get('data_atualizacao'),
                "freq": str(dados.get('frequencia', '')),
                "resp": str(dados.get('responsavel', '')),
                "causa": str(dados.get('causa_motivo', ''))
            })
        return True
    except Exception as e:
        print(f"❌ Erro detalhado no banco: {e}") 
        return False

def listar_controles_da_etapa(etapa_id, auditoria_id=None):
    query = text("""
        SELECT 
            c.*, 
            r.fator_risco as risco_pai
        FROM controles_etapa c
        JOIN riscos_etapa r ON c.risco_id = r.id
        WHERE r.etapa_id = :etapa_id
        AND (:auditoria_id IS NULL OR r.auditoria_id = :auditoria_id)
    """)
    try:
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={
                "etapa_id": etapa_id,
                "auditoria_id": auditoria_id
            })
    except Exception as e:
        print(f"Erro ao listar controles_etapa: {e}")
        return pd.DataFrame()


def validar_login_no_banco(usuario_digitado, senha_digitada):
    """Verifica se as credenciais existem e estão corretas."""
    query = text("""
        SELECT login, senha 
        FROM usuarios 
        WHERE login = :u AND senha = :s AND ativo = True
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"u": usuario_digitado, "s": senha_digitada}).fetchone()
            
            # Se encontrou um registro, retorna True
            if result:
                return True
            return False
    except Exception as e:
        print(f"Erro ao validar login: {e}")
        return False

def atualizar_status_processo(id_processo, novo_status, coluna):
    """Atualiza link_diagrama ou aprovacao na tabela processos"""
    query = text(f"UPDATE processos SET {coluna} = :valor WHERE id = :id")
    with engine.connect() as conn:
        conn.execute(query, {"valor": novo_status, "id": id_processo})
        conn.commit()

def remover_processo_da_auditoria(auditoria_id, processo_id):
    """
    Remove um processo da lista de selecionados da auditoria
    """
    try:
        query = text("""
            DELETE FROM auditoria_processos 
            WHERE auditoria_id = :auditoria_id 
            AND processo_id = :processo_id
        """)
        
        with engine.begin() as conn:
            conn.execute(query, {
                "auditoria_id": auditoria_id,
                "processo_id": processo_id
            })
        
        return True
    except Exception as e:
        print(f"Erro ao remover processo: {e}")
        return False

def validar_basicos():
    """Valida nome do processo e pelo menos um executor selecionado"""
    
    if not st.session_state.get("input_processo", "").strip():
        st.error("❌ O campo 'Nome do Processo' é obrigatório.")
        return False
    
    if not st.session_state.get('novo_executores_selecionados'):
        st.error("❌ Selecione pelo menos um funcionário para executar o processo.")
        return False
    
    return True

def salvar_informacoes_basicas():
    """Salva as informações básicas do processo
    Retorna: (bool, str) - (sucesso, codigo_do_processo)
    """
    resetar_timer_sessao()
    try:
        with engine.begin() as conn:
            id_area_val = st.session_state.get("id_area_selecionado")
            nome_area_val = st.session_state.get("area_selectbox")
            nome_val = st.session_state.get("input_processo", "").strip()
            
            # VERIFICAR SE O PROCESSO JÁ EXISTE
            check_query = text("""
                SELECT id, codigo_processo FROM processos 
                WHERE id_area = :id_area AND nome_processo = :nome
            """)
            existing = conn.execute(check_query, {
                "id_area": id_area_val,
                "nome": nome_val
            }).mappings().fetchone()
            
            if existing:
                # Processo já existe
                processo_id = existing['id']
                st.session_state['processo_existente_id'] = processo_id
                st.info(f"Processo já existe.")
                return True, existing['codigo_processo']
            
            # GERAR CÓDIGO DO PROCESSO
            ultimo_codigo_query = text("""
                SELECT codigo_processo 
                FROM processos 
                WHERE id_area = :id_area
                ORDER BY 
                    CAST(split_part(codigo_processo, '.', 1) AS INTEGER),
                    CAST(split_part(codigo_processo, '.', 2) AS INTEGER) DESC
                LIMIT 1
            """)
            
            ultimo = conn.execute(ultimo_codigo_query, {"id_area": id_area_val}).scalar()
            
            if ultimo:
                partes = ultimo.split('.')
                if len(partes) >= 2:
                    ultimo_numero = int(partes[1])
                    novo_numero = ultimo_numero + 1
                    codigo_processo = f"{id_area_val}.{novo_numero}"
                else:
                    codigo_processo = f"{id_area_val}.1"
            else:
                codigo_processo = f"{id_area_val}.1"
            
            # Inserir novo processo
            sql_insert = text("""
                INSERT INTO processos 
                (id_area, area, codigo_processo, nome_processo, status, aprovacao) 
                VALUES 
                (:id_a, :a, :c, :n, :st, :aprov) 
                RETURNING id
            """)
            
            params = {
                "id_a": id_area_val,
                "a": nome_area_val,
                "c": codigo_processo,
                "n": nome_val,
                "st": "Ativo",
                "aprov": "Em Aprovação"
            }
            processo_id = conn.execute(sql_insert, params).scalar()
            st.session_state['processo_existente_id'] = processo_id
            
            # ===== SALVAR EXECUTORES =====
            conn.execute(
                text("DELETE FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            )
            
            executores_ids = st.session_state.get('novo_executores_selecionados', [])
            if executores_ids:
                sql_exec = text("""
                    INSERT INTO processo_executores (processo_id, funcionario_id)
                    VALUES (:pid, :fid)
                """)
                for fid in executores_ids:
                    conn.execute(sql_exec, {"pid": processo_id, "fid": fid})
            
            # Vincular à auditoria
            if 'auditoria_diagnostico' in st.session_state:
                auditoria_id = st.session_state['auditoria_diagnostico']
                vincular_processo_a_auditoria(
                    auditoria_id=auditoria_id,
                    processo_id=processo_id,
                    motivo="Processo identificado durante diagnóstico da área"
                )
            
            st.session_state['ultimo_processo_id'] = processo_id
            
            return True, codigo_processo
            
    except Exception as e:
        st.error(f"Erro ao salvar informações básicas: {e}")
        return False, None
    
def listar_riscos_do_processo(processo_id):
    """Retorna todos os riscos de um processo com suas categorias"""
    query = text("""
        SELECT r.id, r.nome_risco, r.fator_risco, r.melhoria, r.impacto, 
               r.probabilidade, r.apetite_risco, r.motivo_risco, r.score_risco,
               ARRAY_AGG(c.id) as categorias_ids,
               ARRAY_AGG(c.nome) as categorias_nomes
        FROM riscos r
        LEFT JOIN risco_categorias rc ON r.id = rc.risco_id
        LEFT JOIN categorias_risco c ON rc.categoria_id = c.id
        WHERE r.processo_id = :pid
        GROUP BY r.id
        ORDER BY r.id
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"pid": processo_id})

def salvar_area(dados_area):
    """Salva uma nova área no banco de dados"""
    try:
        query = text("""
            INSERT INTO informacoes_area 
            (nome_area, objetivo_area, status, email, telefone, gestor)
            VALUES 
            (:nome, :objetivo, :status, :email, :telefone, :gestor)
            RETURNING id_area
        """)
        
        with engine.begin() as conn:
            id_area = conn.execute(query, {
                "nome": dados_area['nome'],
                "objetivo": dados_area.get('objetivo', ''),
                "status": dados_area.get('status', 'Ativo'),
                "email": dados_area.get('email', ''),
                "telefone": dados_area.get('telefone', ''),
                "gestor": dados_area.get('gestor', '')
            }).scalar()
            
        return id_area
    except Exception as e:
        print(f"Erro ao salvar área: {e}")
        return None

def listar_areas():
    """Retorna todas as áreas cadastradas"""
    query = text("""
        SELECT id_area, nome_area, objetivo_area, status, email, telefone, gestor
        FROM informacoes_area
        ORDER BY nome_area
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def salvar_funcionarios_area(id_area, lista_funcionarios):
    """Salva a lista de funcionários de uma área"""
    try:
        with engine.begin() as conn:
            # Remove funcionários antigos
            conn.execute(
                text("DELETE FROM funcionarios_area WHERE id_area = :id_area"),
                {"id_area": id_area}
            )
            
            # Insere novos funcionários
            if lista_funcionarios:
                sql_insert = text("""
                    INSERT INTO funcionarios_area 
                    (id_area, nome_funcionario, cargo, tempo_funcao, tempo_empresa, ativo)
                    VALUES 
                    (:id_area, :nome, :cargo, :tempo_funcao, :tempo_empresa, :ativo)
                """)
                
                for func in lista_funcionarios:
                    if func.get('nome', '').strip():
                        conn.execute(sql_insert, {
                            "id_area": id_area,
                            "nome": func['nome'].strip(),
                            "cargo": func.get('cargo', '').strip(),
                            "tempo_funcao": func.get('tempo_funcao', '').strip(),
                            "tempo_empresa": func.get('tempo_empresa', '').strip(),
                            "ativo": func.get('ativo', True)
                        })
            return True
    except Exception as e:
        print(f"Erro ao salvar funcionários: {e}")
        return False

def listar_funcionarios_area(id_area):
    """Retorna os funcionários de uma área"""
    query = text("""
        SELECT id, nome_funcionario, cargo, tempo_funcao, tempo_empresa, ativo
        FROM funcionarios_area
        WHERE id_area = :id_area AND ativo = TRUE
        ORDER BY nome_funcionario
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"id_area": id_area})

def listar_funcionarios_por_area(id_area):
    """Retorna lista de funcionários de uma área para usar em selectbox"""
    query = text("""
        SELECT id, nome_funcionario, cargo
        FROM funcionarios_area
        WHERE id_area = :id_area AND ativo = TRUE
        ORDER BY nome_funcionario
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"id_area": id_area})
        if df.empty:
            return []
        return [(row['id'], f"{row['nome_funcionario']} ({row['cargo']})") 
                for _, row in df.iterrows()]

def listar_executores_processo(processo_id):
    """Retorna os IDs dos funcionários que executam um processo"""
    query = text("""
        SELECT funcionario_id
        FROM processo_executores
        WHERE processo_id = :pid
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"pid": processo_id})
        return df['funcionario_id'].tolist() if not df.empty else []

def buscar_funcionario_por_id(funcionario_id):
    """Busca dados de um funcionário pelo ID"""
    query = text("""
        SELECT id, nome_funcionario, cargo
        FROM funcionarios_area
        WHERE id = :fid
    """)
    with engine.connect() as conn:
        return conn.execute(query, {"fid": funcionario_id}).mappings().first()

def listar_executores_processo_com_nomes(processo_id):
    """Retorna os nomes dos funcionários que executam um processo"""
    query = text("""
        SELECT f.nome_funcionario, f.cargo
        FROM processo_executores pe
        JOIN funcionarios_area f ON pe.funcionario_id = f.id
        WHERE pe.processo_id = :pid
        ORDER BY f.nome_funcionario
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"pid": processo_id})
        if df.empty:
            return []
        return [f"{row['nome_funcionario']} ({row['cargo']})" 
                for _, row in df.iterrows()]

def listar_categorias():
    """Retorna todas as categorias disponíveis"""
    query = text(
        """SELECT id, nome
           FROM categorias_risco ORDER BY id 
        """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        return dict(zip(df['id'], df['nome']))

def salvar_categorias_risco(risco_id, categorias_ids):
    """Salva as categorias de um risco"""
    try:
        with engine.connect() as conn:
            # Remove categorias antigas
            conn.execute(
                text("""
                    DELETE FROM risco_categorias WHERE risco_id = :rid
                    """),
                    {'id': risco_id}
            )

            # Insere novas categorias
            if categorias_ids:
                for cat_id in categorias_ids:
                    conn.execute(
                        text(
                            """INSERT INTO risco_categorias (risco_id, categoria_id)
                                VALUES (:rid, :cid)
                            """), {'rid': risco_id, "cid": cat_id}
                    )
            return True
    except Exception as e:
        print(f"Erro ao salvar categorias: {e}")
        return False

def listar_categorias_do_risco(risco_id):
    """Retorna os IDs das categorias de um risco"""
    query = text(
        """SELECT categoria_id
            FROM risco_categorias
            WHERE risco_id = :rid
        """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={'rid': risco_id})
        return df['categoria_id'].tolist() if not df.empty else []
    
def carregar_riscos_processo_para_edicao(processo_id):
    """Carrega os riscos do processo para a session_state de edição"""
    import streamlit as st
    
    # ===== LIMPEZA AGRESSIVA =====
    # Remover todas as keys de edição de riscos
    keys_to_remove = []
    for key in list(st.session_state.keys()):
        if key.startswith('edit_nome_') or key.startswith('edit_fator_') or \
           key.startswith('edit_melhoria_') or key.startswith('edit_apetite_') or \
           key.startswith('edit_imp_') or key.startswith('edit_prob_') or \
           key.startswith('edit_motivo_') or key.startswith('edit_categorias_'):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        st.session_state.pop(key, None)
    
    # ===== CARREGAR NOVOS RISCOS =====
    df_riscos = listar_riscos_do_processo(processo_id)
    
    # CRUCIAL: Se não há riscos, criar lista VAZIA, não [{}]
    if not df_riscos.empty:
        st.session_state['edit_riscos'] = []
        
        for idx, (_, row) in enumerate(df_riscos.iterrows()):
            st.session_state['edit_riscos'].append({})
            st.session_state[f'edit_nome_{idx}'] = row['nome_risco'] or ""
            st.session_state[f'edit_fator_{idx}'] = row['fator_risco'] or ""
            st.session_state[f'edit_melhoria_{idx}'] = row['melhoria'] or ""
            st.session_state[f'edit_apetite_{idx}'] = row['apetite_risco'] or ""
            st.session_state[f'edit_motivo_{idx}'] = row['motivo_risco'] or ""
            st.session_state[f'edit_categorias_{idx}'] = row['categorias_ids'] if row['categorias_ids'] else []
            st.session_state[f'edit_imp_{idx}'] = normalizar_valor_risco(row['impacto'])
            st.session_state[f'edit_prob_{idx}'] = normalizar_valor_risco(row['probabilidade'])
    else:
        # ===== MUDANÇA CRÍTICA: LISTA VAZIA, NÃO [{}] =====
        st.session_state['edit_riscos'] = []  # ← LISTA VAZIA
    
    # DEBUG
    print(f"🔍 Carregados {len(st.session_state['edit_riscos'])} riscos para o processo {processo_id}")

def salvar_edicao_processo():
    """Salva as alterações de um processo existente"""
    resetar_timer_sessao()
    try:
        with engine.begin() as conn:
            processo_id = st.session_state.get('edit_processo_existente_id')
            if not processo_id:
                st.error("Processo não identificado.")
                return False
            
            # Atualizar dados básicos
            sql_update = text("""
                UPDATE processos 
                SET nome_processo=:nome, objetivo=:o, descricao=:d, 
                    etapa_ini=:ei, etapa_fim=:ef, produto=:p
                WHERE id = :pid
            """)
            
            conn.execute(sql_update, {
                "pid": processo_id,
                "nome": st.session_state.get('edit_input_processo', ''),
                "o": st.session_state.get('edit_input_objetivo', ''),
                "d": st.session_state.get('edit_input_descricao', ''),
                "ei": st.session_state.get('edit_input_etapa_ini', ''),
                "ef": st.session_state.get('edit_input_etapa_fim', ''),
                "p": st.session_state.get('edit_input_produto', '')
            })
            
            # Atualizar executores
            conn.execute(
                text("DELETE FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            )
            
            executores_ids = st.session_state.get('edit_executores_selecionados', [])
            if executores_ids:
                sql_exec = text("INSERT INTO processo_executores (processo_id, funcionario_id) VALUES (:pid, :fid)")
                for fid in executores_ids:
                    conn.execute(sql_exec, {"pid": processo_id, "fid": fid})
            
            # Atualizar riscos (remover antigos e inserir novos)
            conn.execute(text("DELETE FROM riscos WHERE processo_id = :pid"), {"pid": processo_id})
            
            sql_risco = text("""
                INSERT INTO riscos 
                (processo_id, nome_risco, fator_risco, melhoria, impacto, probabilidade, 
                 apetite_risco, motivo_risco, score_risco) 
                VALUES (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo, :score)
                RETURNING id
            """)
            
            for i in range(len(st.session_state.get('edit_riscos', []))):
                imp = st.session_state.get(f"edit_imp_{i}")
                prob = st.session_state.get(f"edit_prob_{i}")
                score = MAPA_RISCO.get((imp, prob), 0)
                
                result = conn.execute(sql_risco, {
                    "pid": processo_id, 
                    "nome": st.session_state.get(f"edit_nome_{i}"), 
                    "fator": st.session_state.get(f"edit_fator_{i}"), 
                    "melhoria": st.session_state.get(f"edit_melhoria_{i}"), 
                    "imp": imp, 
                    "prob": prob, 
                    "apetite": st.session_state.get(f"edit_apetite_{i}"), 
                    "motivo": st.session_state.get(f"edit_motivo_{i}"), 
                    "score": score
                })
                
                risco_id = result.scalar()
                
                categorias_ids = st.session_state.get(f"edit_categorias_{i}", [])
                if categorias_ids:
                    for cat_id in categorias_ids:
                        conn.execute(
                            text("INSERT INTO risco_categorias (risco_id, categoria_id) VALUES (:rid, :cid)"),
                            {"rid": risco_id, "cid": cat_id}
                        )
            
        return True
    except Exception as e:
        st.error(f"Erro ao salvar edição: {e}")
        return False
    
def tempo_restante_sessao():
    """Retorna o tempo restante em minutos e segundos"""
    if st.session_state.get('autenticado'):
        login_time = st.session_state.get('login_timestamp')
        if login_time:
            tempo_decorrido = (datetime.now() - login_time).total_seconds()
            tempo_restante = max(0, 1800 - tempo_decorrido)
            minutos = int(tempo_restante // 60)
            segundos = int(tempo_restante % 60)
            return f"{minutos:02d}:{segundos:02d}"
    return "00:00"