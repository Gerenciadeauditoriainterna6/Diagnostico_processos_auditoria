import os
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import text
from database import engine
from datetime import datetime
import streamlit as st
from modules.shared.log_sistema import registrar_log

#local_storage = LocalStorage()
# --- CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOGO = os.path.join(BASE_DIR, "assets", "logo_fusve.png")
CAMINHO_LOGO2 = os.path.join(BASE_DIR, "assets", "logo_auditoria.png")

# Tempo da sessão do usuário
TEMPO_SESSAO_SEGUNDOS = 1800

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
        query_area = text("""
            SELECT nome_area FROM informacoes_area WHERE id_area = :id
        """)
        
        with engine.connect() as conn:
            nome_area = conn.execute(query_area, {"id": dados_auditoria['id_area']}).scalar()

        # Extrai sigla
        sigla = nome_area.split('-')[-1].strip() if '-' in nome_area else nome_area[:3]
        codigo = f"AUD-{sigla}-{dados_auditoria['ano']}-{dados_auditoria['trimestre']}T"

        # Query de inserção (corrigi os nomes das colunas - verifique se estão corretos)
        query = text("""
            INSERT INTO auditorias
            (codigo_auditoria, id_area, titulo, objetivo, escopo, ano, trimestre,
             data_inicio, data_fim, status, responsavel_equipe)
            VALUES
            (:codigo, :id_area, :titulo, :objetivo, :escopo, :ano, :trimestre,
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
            
            # ===== ADICIONAR LOG AQUI =====
            # Prepara os dados que foram inseridos
            dados_inseridos = {
                'id': auditoria_id,
                'codigo_auditoria': codigo,
                'id_area': dados_auditoria['id_area'],
                'titulo': dados_auditoria['titulo'],
                'objetivo': dados_auditoria.get('objetivo', ''),
                'escopo': dados_auditoria.get('escopo', ''),
                'ano': dados_auditoria['ano'],
                'trimestre': dados_auditoria['trimestre'],
                'status': dados_auditoria.get('status', 'Planejamento')
            }
            
            registrar_log(
                tabela='auditorias',
                registro_id=auditoria_id,
                operacao='INSERT',
                dados_anteriores=None,
                dados_novos=dados_inseridos
            )
            # ===== FIM DO LOG =====

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
        # Primeiro, vamos buscar informações para o log (ANTES de inserir)
        with engine.connect() as conn:
            # Buscar dados da auditoria
            auditoria_info = conn.execute(
                text("SELECT codigo_auditoria, titulo FROM auditorias WHERE id = :id"),
                {"id": auditoria_id}
            ).mappings().fetchone()
            
            # Buscar dados do processo
            processo_info = conn.execute(
                text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
                {"id": processo_id}
            ).mappings().fetchone()
        
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
            
            # ===== ADICIONAR LOG AQUI =====
            if result is not None:  # Só registra se realmente inseriu (não existia)
                dados_inseridos = {
                    'auditoria_id': auditoria_id,
                    'auditoria_codigo': auditoria_info['codigo_auditoria'] if auditoria_info else None,
                    'auditoria_titulo': auditoria_info['titulo'] if auditoria_info else None,
                    'processo_id': processo_id,
                    'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                    'processo_nome': processo_info['nome_processo'] if processo_info else None,
                    'motivo_selecao': motivo
                }
                
                registrar_log(
                    tabela='auditoria_processos',
                    registro_id=result,
                    operacao='INSERT',
                    dados_anteriores=None,
                    dados_novos=dados_inseridos
                )
            # ===== FIM DO LOG =====
            
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
            
            # ===== ADICIONAR LOG AQUI =====
            # Prepara os dados que foram inseridos (sem dados sensíveis)
            dados_inseridos = {
                'id': checklist_id,
                'auditoria_id': dados_checklist.get('auditoria_id'),
                'processo_id': dados_checklist.get('processo_id'),
                'pilar': dados_checklist.get('pilar'),
                'pergunta': dados_checklist.get('pergunta')[:100] if dados_checklist.get('pergunta') else None,  # Limita tamanho
                'peso': dados_checklist.get('peso'),
                'resposta': dados_checklist.get('resposta'),
                'pontuacao': dados_checklist.get('pontuacao'),
                'conclusao': dados_checklist.get('conclusao')[:200] if dados_checklist.get('conclusao') else None
            }
            
            registrar_log(
                tabela='checklists_eficacia',
                registro_id=checklist_id,
                operacao='INSERT',
                dados_anteriores=None,
                dados_novos=dados_inseridos
            )
            # ===== FIM DO LOG =====
            
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
        # Primeiro, verificar se já existe uma conclusão para esta auditoria
        with engine.connect() as conn:
            existe = conn.execute(
                text("SELECT id FROM conclusao_auditoria WHERE auditoria_id = :id"),
                {"id": dados_conclusao['auditoria_id']}
            ).scalar()
            
            if existe:
                # Buscar dados ANTIGOS para o log (UPDATE)
                dados_antigos = conn.execute(
                    text("SELECT * FROM conclusao_auditoria WHERE auditoria_id = :id"),
                    {"id": dados_conclusao['auditoria_id']}
                ).mappings().fetchone()
        
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
            
            # ===== ADICIONAR LOG AQUI =====
            # Prepara os dados para o log (sem PDF que pode ser grande)
            dados_novos = {
                'id': conclusao_id,
                'auditoria_id': dados_conclusao['auditoria_id'],
                'resumo_executivo': dados_conclusao.get('resumo_executivo', '')[:200] if dados_conclusao.get('resumo_executivo') else None,
                'pontos_fortes': dados_conclusao.get('pontos_fortes', []),
                'oportunidades_melhoria': dados_conclusao.get('oportunidades_melhoria', []),
                'recomendacoes': dados_conclusao.get('recomendacoes', []),
                'parecer_final': dados_conclusao.get('parecer_final', ''),
                'data_conclusao': str(dados_conclusao.get('data_conclusao')) if dados_conclusao.get('data_conclusao') else None
            }
            
            if existe:
                # É um UPDATE
                registrar_log(
                    tabela='conclusao_auditoria',
                    registro_id=conclusao_id,
                    operacao='UPDATE',
                    dados_anteriores=dict(dados_antigos) if dados_antigos else None,
                    dados_novos=dados_novos
                )
            else:
                # É um INSERT
                registrar_log(
                    tabela='conclusao_auditoria',
                    registro_id=conclusao_id,
                    operacao='INSERT',
                    dados_anteriores=None,
                    dados_novos=dados_novos
                )
            # ===== FIM DO LOG =====
            
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


def listar_categorias():
    """Retorna as categorias de risco pré-definidas"""
    categorias = {
        1: "Risco Financeiro",
        2: "Risco Legal",
        3: "Risco Inerente",
        4: "Risco de TI",
        5: "Risco Reputacional",
        6: "Risco de Integridade",
        7: "Risco Ambiental"
    }
    return categorias

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
        # Buscar informações do processo para o log
        with engine.connect() as conn:
            processo_info = conn.execute(
                text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
                {"id": dados_etapa.get('processo_id')}
            ).mappings().fetchone()
        
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
                RETURNING id
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
                RETURNING id
            """)
        
        with engine.begin() as conn:
            result = conn.execute(query, dados_etapa)
            etapa_id = result.scalar()
            
            # ===== ADICIONAR LOG AQUI =====
            dados_inseridos = {
                'id': etapa_id,
                'processo_id': dados_etapa.get('processo_id'),
                'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                'processo_nome': processo_info['nome_processo'] if processo_info else None,
                'auditoria_id': auditoria_id,
                'codigo_etapa': dados_etapa.get('codigo_etapa'),
                'descricao_etapa': dados_etapa.get('descricao_etapa')[:100] if dados_etapa.get('descricao_etapa') else None,
                'status_etapa': dados_etapa.get('status_etapa'),
                'criticidade_etapa': dados_etapa.get('criticidade_etapa')
            }
            
            registrar_log(
                tabela='etapas_processo',
                registro_id=etapa_id,
                operacao='INSERT',
                dados_anteriores=None,
                dados_novos=dados_inseridos
            )
            # ===== FIM DO LOG =====
            
        return True
    except Exception as e:
        print(f"Erro ao salvar etapa: {e}")
        return False
    
from modules.shared.log_sistema import registrar_log  # Adicione no topo

def atualizar_etapa_no_banco(dados):
    """Atualiza os dados de uma etapa existente"""
    try:
        # Buscar dados ANTIGOS da etapa antes de atualizar
        with engine.connect() as conn:
            dados_antigos = conn.execute(
                text("SELECT * FROM etapas_processo WHERE id = :etapa_id"),
                {"etapa_id": dados['etapa_id']}
            ).mappings().fetchone()
        
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
            RETURNING id
        """)
        
        with engine.begin() as conn:
            result = conn.execute(query, {
                "etapa_id": dados['etapa_id'],
                "desc": dados.get('desc', ''),
                "oque": dados.get('oque', ''),
                "como": dados.get('como', ''),
                "obj": dados.get('obj', ''),
                "status": dados.get('status', 'Ativa'),
                "real": dados.get('real', 'Sim'),
                "crit": dados.get('crit', 'Em Aprovação'),
                "exec": dados.get('exec', ''),
                "link_d": dados.get('link_d', ''),
                "link_m": dados.get('link_m', ''),
                "pol": dados.get('pol', ''),
                "ana": dados.get('ana', ''),
                "sug": dados.get('sug', ''),
                "nec": dados.get('nec', ''),
                "gan": dados.get('gan', ''),
                "obri": dados.get('obri', '')
            })
            
            etapa_id = result.scalar()
            
            # ===== ADICIONAR LOG AQUI =====
            # Preparar dados novos (apenas campos relevantes para o log)
            dados_novos = {
                'id': dados['etapa_id'],
                'descricao_etapa': dados.get('desc', '')[:100],
                'oque_faz': dados.get('oque', '')[:100],
                'como_e_feito': dados.get('como', '')[:100],
                'objetivo_etapa': dados.get('obj', '')[:100],
                'status_etapa': dados.get('status', 'Ativa'),
                'realizado_corretamente': dados.get('real', 'Sim'),
                'criticidade_etapa': dados.get('crit', 'Em Aprovação')
            }
            
            # Preparar dados antigos (apenas campos relevantes)
            dados_antigos_resumidos = {
                'id': dados_antigos['id'],
                'descricao_etapa': dados_antigos.get('descricao_etapa', '')[:100] if dados_antigos else None,
                'oque_faz': dados_antigos.get('oque_faz', '')[:100] if dados_antigos else None,
                'como_e_feito': dados_antigos.get('como_e_feito', '')[:100] if dados_antigos else None,
                'objetivo_etapa': dados_antigos.get('objetivo_etapa', '')[:100] if dados_antigos else None,
                'status_etapa': dados_antigos.get('status_etapa', '') if dados_antigos else None,
                'realizado_corretamente': dados_antigos.get('realizado_corretamente', '') if dados_antigos else None,
                'criticidade_etapa': dados_antigos.get('criticidade_etapa', '') if dados_antigos else None
            }
            
            registrar_log(
                tabela='etapas_processo',
                registro_id=dados['etapa_id'],
                operacao='UPDATE',
                dados_anteriores=dados_antigos_resumidos if dados_antigos else None,
                dados_novos=dados_novos
            )
            # ===== FIM DO LOG =====
            
        return True
    except Exception as e:
        print(f"Erro ao atualizar etapa: {e}")
        return False

def listar_etapas_do_processo(processo_id, auditoria_id=None):
    """Lista todas as etapas de um processo"""
    if auditoria_id:
        query = text("""
            SELECT 
                id, processo_id, codigo_etapa, descricao_etapa, oque_faz,
                como_e_feito, objetivo_etapa, status_etapa, realizado_corretamente,
                criticidade_etapa, politica_interna, analise_critica, sugestao_melhoria,
                necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                diagrama_bpmn, diagrama_nome, diagrama_tipo,
                manual_etapa, manual_nome, manual_tipo
            FROM etapas_processo
            WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id
            ORDER BY codigo_etapa
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={
                "processo_id": processo_id,
                "auditoria_id": auditoria_id
            })
    else:
        query = text("""
            SELECT 
                id, processo_id, codigo_etapa, descricao_etapa, oque_faz,
                como_e_feito, objetivo_etapa, status_etapa, realizado_corretamente,
                criticidade_etapa, politica_interna, analise_critica, sugestao_melhoria,
                necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                diagrama_bpmn, diagrama_nome, diagrama_tipo,
                manual_etapa, manual_nome, manual_tipo
            FROM etapas_processo
            WHERE processo_id = :processo_id
            ORDER BY codigo_etapa
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"processo_id": processo_id})

def obter_proximo_codigo_etapa(processo_id, codigo_processo):
    """Gera o código 1.2.1 baseado no número de etapas existentes."""
    query = text("SELECT COUNT(*) FROM etapas_processo WHERE processo_id = :id")
    with engine.connect() as conn:
        contagem = conn.execute(query, {"id": processo_id}).scalar() or 0
    return f"{codigo_processo}.{contagem + 1}"

def salvar_risco_etapa(dados, auditoria_id=None):
    """Salva risco de etapa, opcionalmente vinculado a uma auditoria"""
    
    # Buscar informações da etapa para o log
    with engine.connect() as conn:
        etapa_info = conn.execute(
            text("""
                SELECT e.codigo_etapa, e.descricao_etapa, p.nome_processo, p.codigo_processo
                FROM etapas_processo e
                JOIN processos p ON e.processo_id = p.id
                WHERE e.id = :id
            """),
            {"id": dados.get('etapa_id')}
        ).mappings().fetchone()
    
    if auditoria_id:
        query = text("""
            INSERT INTO riscos_etapa 
            (etapa_id, auditoria_id, categoria, fator_risco, consequencia, info_adicional, 
             financeiro, ativo, origem, doc_legal, impacto, probabilidade, magnitude, 
             apetite, tratamento)
            VALUES 
            (:etapa_id, :auditoria_id, :cat, :fator, :cons, :info, :fin, :ativo, 
             :ori, :doc, :imp, :prob, :mag, :apet, :trat)
            RETURNING id
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
            RETURNING id
        """)
    
    with engine.begin() as conn:
        result = conn.execute(query, dados)
        risco_id = result.scalar()
        
        # ===== ADICIONAR LOG AQUI =====
        dados_inseridos = {
            'id': risco_id,
            'etapa_id': dados.get('etapa_id'),
            'etapa_codigo': etapa_info['codigo_etapa'] if etapa_info else None,
            'etapa_descricao': etapa_info['descricao_etapa'][:100] if etapa_info and etapa_info.get('descricao_etapa') else None,
            'processo_nome': etapa_info['nome_processo'] if etapa_info else None,
            'processo_codigo': etapa_info['codigo_processo'] if etapa_info else None,
            'auditoria_id': auditoria_id,
            'categoria': dados.get('cat'),
            'fator_risco': dados.get('fator')[:100] if dados.get('fator') else None,
            'consequencia': dados.get('cons')[:100] if dados.get('cons') else None,
            'impacto': dados.get('imp'),
            'probabilidade': dados.get('prob'),
            'magnitude': dados.get('mag')
        }
        
        registrar_log(
            tabela='riscos_etapa',
            registro_id=risco_id,
            operacao='INSERT',
            dados_anteriores=None,
            dados_novos=dados_inseridos
        )
        # ===== FIM DO LOG =====
        
        return True

def listar_riscos_etapa(etapa_id, auditoria_id=None):
    """Lista todos os riscos de uma etapa"""
    if auditoria_id:
        query = text("""
            SELECT 
                id,
                categoria,
                fator_risco,
                consequencia,
                impacto,
                probabilidade,
                magnitude,
                apetite,
                tratamento,
                origem,
                financeiro,
                ativo,
                info_adicional,
                doc_legal
            FROM riscos_etapa
            WHERE etapa_id = :etapa_id AND (auditoria_id = :auditoria_id OR auditoria_id IS NULL)
            ORDER BY magnitude DESC
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={
                "etapa_id": etapa_id,
                "auditoria_id": auditoria_id
            })
    else:
        query = text("""
            SELECT 
                id,
                categoria,
                fator_risco,
                consequencia,
                impacto,
                probabilidade,
                magnitude,
                apetite,
                tratamento,
                origem,
                financeiro,
                ativo,
                info_adicional,
                doc_legal
            FROM riscos_etapa
            WHERE etapa_id = :etapa_id
            ORDER BY magnitude DESC
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"etapa_id": etapa_id})

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
    """Salva novo processo ou atualiza existente, traduzindo categorias para nomes"""
    from logic import listar_categorias, resetar_timer_sessao
    resetar_timer_sessao()
    
    try:
        with engine.begin() as conn:
            id_area_val = st.session_state.get("id_area_selecionado")
            nome_area_val = st.session_state.get("area_selectbox")
            nome_val = st.session_state.get("input_processo", "").strip()

            # === CONCATENAR OBJETIVO ===
            objetivo_raw = st.session_state.get('input_objetivo', '').strip()
            objetivo_com_prefixo = f"Garantir {objetivo_raw}" if objetivo_raw else ''

            # === 1. VERIFICAR SE O PROCESSO JÁ EXISTE ===
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
                
                # Buscar dados ANTIGOS do processo para o log
                dados_antigos_processo = conn.execute(
                    text("SELECT * FROM processos WHERE id = :pid"),
                    {"pid": processo_id}
                ).mappings().fetchone()

                sql_update = text("""
                    UPDATE processos 
                    SET objetivo=:o, descricao=:d, 
                        etapa_ini=:ei, etapa_fim=:ef, produto=:p
                    WHERE id = :pid
                """)

                conn.execute(sql_update, {
                    "pid": processo_id,
                    "o": objetivo_com_prefixo,
                    "d": st.session_state.get('input_descricao', ''),
                    "ei": st.session_state.get('input_etapa_ini', ''),
                    "ef": st.session_state.get('input_etapa_fim', ''),
                    "p": st.session_state.get('input_produto', '')
                })
                
                # Buscar dados NOVOS do processo para o log
                dados_novos_processo = conn.execute(
                    text("SELECT * FROM processos WHERE id = :pid"),
                    {"pid": processo_id}
                ).mappings().fetchone()
                
                # ===== LOG DO UPDATE DO PROCESSO =====
                registrar_log(
                    tabela='processos',
                    registro_id=processo_id,
                    operacao='UPDATE',
                    dados_anteriores=dict(dados_antigos_processo),
                    dados_novos=dict(dados_novos_processo)
                )
                # ===== FIM DO LOG =====

            else:
                # === MODO CRIAÇÃO: Inserir novo processo ===
                codigo_processo = st.session_state.get('codigo_processo_display', '')

                sql_insert = text("""
                    INSERT INTO processos 
                    (id_area, area, codigo_processo, nome_processo, objetivo, 
                    descricao, etapa_ini, etapa_fim, produto, status) 
                    VALUES 
                    (:id_a, :a, :c, :n, :o, :d, :ei, :ef, :p, :st) 
                    RETURNING id
                """)

                params_insert = {
                    "id_a": id_area_val,
                    "a": nome_area_val,
                    "c": codigo_processo,
                    "n": nome_val,
                    "o": objetivo_com_prefixo,
                    "d": st.session_state.get('input_descricao', ''),
                    "ei": st.session_state.get('input_etapa_ini', ''),
                    "ef": st.session_state.get('input_etapa_fim', ''),
                    "p": st.session_state.get('input_produto', ''),
                    "st": "Ativo"
                }

                processo_id = conn.execute(sql_insert, params_insert).scalar()
                st.session_state['processo_existente_id'] = processo_id
                
                # ===== LOG DO INSERT DO PROCESSO =====
                dados_novos_processo = {
                    'id': processo_id,
                    'id_area': id_area_val,
                    'area': nome_area_val,
                    'codigo_processo': codigo_processo,
                    'nome_processo': nome_val,
                    'objetivo': objetivo_com_prefixo,
                    'status': 'Ativo'
                }
                
                registrar_log(
                    tabela='processos',
                    registro_id=processo_id,
                    operacao='INSERT',
                    dados_anteriores=None,
                    dados_novos=dados_novos_processo
                )
                # ===== FIM DO LOG =====

            # ===== 2. RISCOS: REMOVE OS ANTIGOS E INSERE OS NOVOS =====
            # Buscar riscos ANTIGOS antes de deletar (para o log)
            riscos_antigos = conn.execute(
                text("SELECT id, nome_risco, score_risco, categoria FROM riscos WHERE processo_id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchall()
            
            # Registrar DELETE dos riscos antigos (um por um ou em lote)
            for risco_antigo in riscos_antigos:
                registrar_log(
                    tabela='riscos',
                    registro_id=risco_antigo['id'],
                    operacao='DELETE',
                    dados_anteriores=dict(risco_antigo),
                    dados_novos=None
                )
            
            # Executar DELETE
            conn.execute(
                text("DELETE FROM riscos WHERE processo_id = :pid"),
                {"pid": processo_id}
            )

            # Query de Risco
            sql_risco = text("""
                INSERT INTO riscos 
                (processo_id, nome_risco, fator_risco, melhoria, impacto, 
                probabilidade, apetite_risco, motivo_risco, score_risco, categoria) 
                VALUES 
                (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo, :score, :categoria)
                RETURNING id
            """)

            mapa_categorias = listar_categorias()

            for i in range(len(st.session_state['riscos'])):
                nome_risco_raw = st.session_state.get(f"nome_{i}", '').strip()
                nome_risco_com_prefixo = f"Risco pela possibilidade {nome_risco_raw}" if nome_risco_raw else ''
                
                fator_raw = st.session_state.get(f"fator_{i}", '').strip()
                fator_com_prefixo = f"Pelo motivo {fator_raw}" if fator_raw else ''

                imp = st.session_state.get(f"imp_{i}")
                prob = st.session_state.get(f"prob_{i}")
                score = MAPA_RISCO.get((imp, prob), 0)
                
                categorias_ids = st.session_state.get(f"categorias_{i}", [])
                if categorias_ids:
                    nomes_selecionados = [mapa_categorias.get(cid) for cid in categorias_ids if cid in mapa_categorias]
                    categoria_str = ', '.join(nomes_selecionados)
                else:
                    categoria_str = None

                result = conn.execute(sql_risco, {
                    "pid": processo_id,
                    "nome": nome_risco_com_prefixo,
                    "fator": fator_com_prefixo,
                    "melhoria": st.session_state.get(f"melhoria_{i}"),
                    "imp": imp,
                    "prob": prob,
                    "apetite": st.session_state.get(f"apetite_{i}"),
                    "motivo": st.session_state.get(f"motivo_{i}"),
                    "score": score,
                    "categoria": categoria_str
                })
                
                risco_id = result.scalar()
                
                # ===== LOG DO INSERT DO RISCO =====
                dados_novos_risco = {
                    'id': risco_id,
                    'processo_id': processo_id,
                    'nome_risco': nome_risco_com_prefixo,
                    'impacto': imp,
                    'probabilidade': prob,
                    'score_risco': score,
                    'categoria': categoria_str
                }
                
                registrar_log(
                    tabela='riscos',
                    registro_id=risco_id,
                    operacao='INSERT',
                    dados_anteriores=None,
                    dados_novos=dados_novos_risco
                )
                # ===== FIM DO LOG =====

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
    """Retorna cor e emoji baseado no score do risco"""
    # Tratar valores nulos
    if score is None:
        return "#6c757d", "⚪"  # Cinza para sem risco
    elif score >= 12:
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
        RETURNING id
    """)
    
    try:
        with engine.begin() as conn:
            # Buscar informações do risco para o log
            risco_info = conn.execute(
                text("""
                    SELECT r.id, r.nome_risco, r.categoria, p.nome_processo
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE r.id = :id
                """),
                {"id": int(dados.get('risco_id'))}
            ).mappings().fetchone()
            
            result = conn.execute(query, {
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
            
            controle_id = result.scalar()
            
            # ===== ADICIONAR LOG AQUI =====
            dados_inseridos = {
                'id': controle_id,
                'risco_id': int(dados.get('risco_id')),
                'risco_nome': risco_info['nome_risco'][:100] if risco_info and risco_info.get('nome_risco') else None,
                'risco_categoria': risco_info['categoria'] if risco_info else None,
                'processo_nome': risco_info['nome_processo'] if risco_info else None,
                'nome_controle': str(dados.get('nome', ''))[:100],
                'objetivo_controle': str(dados.get('objetivo', ''))[:100],
                'status_controle': str(dados.get('status', '')),
                'natureza': str(dados.get('natureza', ''))
            }
            
            registrar_log(
                tabela='controles_etapa',
                registro_id=controle_id,
                operacao='INSERT',
                dados_anteriores=None,
                dados_novos=dados_inseridos
            )
            # ===== FIM DO LOG =====
            
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
    """
    Verifica se as credenciais existem e estão corretas.
    
    Retorna: (sucesso, id, nome, perfil)
    """
    query = text("""
        SELECT id, login, nome, perfil
        FROM usuarios 
        WHERE login = :u AND senha = :s AND ativo = True
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"u": usuario_digitado, "s": senha_digitada}).fetchone()
            
            # Se encontrou um registro, retorna True
            if result:
                usuario_id = result[0]
                usuario_login = result[1]
                usuario_nome = result[2]
                usuario_perfil = result[3] if result[3] else 'auditor' # Padrão: auditor

                return True, usuario_id, usuario_nome, usuario_perfil
            
            return False, None, None, None
    except Exception as e:
        print(f"Erro ao validar login: {e}")
        return False, None, None, None

def atualizar_status_processo(id_processo, novo_status, coluna):
    """Atualiza link_diagrama ou aprovacao na tabela processos"""
    
    # Validação de segurança: apenas colunas permitidas
    colunas_permitidas = ['link_diagrama', 'aprovacao', 'status', 'relatorio_gerencial_gerado']
    if coluna not in colunas_permitidas:
        print(f"Erro: Coluna '{coluna}' não é permitida para atualização")
        return False
    
    try:
        # Buscar dados ANTIGOS do processo antes de atualizar
        with engine.connect() as conn:
            dados_antigos = conn.execute(
                text("SELECT id, nome_processo, codigo_processo, link_diagrama, aprovacao, status, relatorio_gerencial_gerado FROM processos WHERE id = :id"),
                {"id": id_processo}
            ).mappings().fetchone()
            
            if not dados_antigos:
                print(f"Erro: Processo {id_processo} não encontrado")
                return False
        
        # Query segura com texto puro (sem f-string para valores)
        query = text(f"UPDATE processos SET {coluna} = :valor WHERE id = :id RETURNING id")
        
        with engine.begin() as conn:
            result = conn.execute(query, {"valor": novo_status, "id": id_processo})
            resultado_id = result.scalar()
            
            # ===== ADICIONAR LOG AQUI =====
            dados_novos = {
                'id': id_processo,
                'nome_processo': dados_antigos['nome_processo'],
                'codigo_processo': dados_antigos['codigo_processo'],
                f'{coluna}_anterior': dados_antigos.get(coluna),
                f'{coluna}_novo': novo_status
            }
            
            # Dados antigos resumidos para o log
            dados_antigos_resumidos = {
                'id': id_processo,
                'nome_processo': dados_antigos['nome_processo'],
                'codigo_processo': dados_antigos['codigo_processo'],
                f'{coluna}': dados_antigos.get(coluna)
            }
            
            registrar_log(
                tabela='processos',
                registro_id=id_processo,
                operacao='UPDATE',
                dados_anteriores=dados_antigos_resumidos,
                dados_novos=dados_novos
            )
            # ===== FIM DO LOG =====
        
        return True
        
    except Exception as e:
        print(f"Erro ao atualizar status do processo: {e}")
        return False

def remover_processo_da_auditoria(auditoria_id, processo_id):
    """
    Remove um processo da lista de selecionados da auditoria
    """
    try:
        # Buscar informações ANTES de deletar (para o log)
        with engine.connect() as conn:
            # Buscar dados da relação que será removida
            relacao = conn.execute(
                text("""
                    SELECT ap.id, ap.auditoria_id, ap.processo_id, ap.motivo_selecao,
                           a.codigo_auditoria, a.titulo,
                           p.codigo_processo, p.nome_processo
                    FROM auditoria_processos ap
                    JOIN auditorias a ON a.id = ap.auditoria_id
                    JOIN processos p ON p.id = ap.processo_id
                    WHERE ap.auditoria_id = :auditoria_id 
                    AND ap.processo_id = :processo_id
                """),
                {
                    "auditoria_id": auditoria_id,
                    "processo_id": processo_id
                }
            ).mappings().fetchone()
        
        query = text("""
            DELETE FROM auditoria_processos 
            WHERE auditoria_id = :auditoria_id 
            AND processo_id = :processo_id
            RETURNING id
        """)
        
        with engine.begin() as conn:
            result = conn.execute(query, {
                "auditoria_id": auditoria_id,
                "processo_id": processo_id
            }).fetchone()
            
            # ===== ADICIONAR LOG AQUI =====
            if relacao:
                dados_antigos = {
                    'id': relacao['id'],
                    'auditoria_id': auditoria_id,
                    'auditoria_codigo': relacao['codigo_auditoria'],
                    'auditoria_titulo': relacao['titulo'],
                    'processo_id': processo_id,
                    'processo_codigo': relacao['codigo_processo'],
                    'processo_nome': relacao['nome_processo'],
                    'motivo_selecao': relacao.get('motivo_selecao')
                }
                
                registrar_log(
                    tabela='auditoria_processos',
                    registro_id=relacao['id'],
                    operacao='DELETE',
                    dados_anteriores=dados_antigos,
                    dados_novos=None
                )
            # ===== FIM DO LOG =====
        
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
            
            # ===== LOG DO INSERT DO PROCESSO =====
            dados_novos_processo = {
                'id': processo_id,
                'id_area': id_area_val,
                'area': nome_area_val,
                'codigo_processo': codigo_processo,
                'nome_processo': nome_val,
                'status': 'Ativo',
                'aprovacao': 'Em Aprovação'
            }
            
            registrar_log(
                tabela='processos',
                registro_id=processo_id,
                operacao='INSERT',
                dados_anteriores=None,
                dados_novos=dados_novos_processo
            )
            # ===== FIM DO LOG =====
            
            # ===== SALVAR EXECUTORES =====
            # Buscar executores antigos (se houver)
            executores_antigos = conn.execute(
                text("SELECT funcionario_id FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            ).fetchall()
            
            # Registrar DELETE dos executores antigos
            for exec_antigo in executores_antigos:
                registrar_log(
                    tabela='processo_executores',
                    registro_id=exec_antigo[0],
                    operacao='DELETE',
                    dados_anteriores={'processo_id': processo_id, 'funcionario_id': exec_antigo[0]},
                    dados_novos=None
                )
            
            conn.execute(
                text("DELETE FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            )
            
            executores_ids = st.session_state.get('novo_executores_selecionados', [])
            if executores_ids:
                # Buscar nomes dos funcionários para o log
                funcionarios_info = {}
                for fid in executores_ids:
                    func_info = conn.execute(
                        text("SELECT nome_funcionario FROM funcionarios_area WHERE id = :id"),
                        {"id": fid}
                    ).scalar()
                    funcionarios_info[fid] = func_info
                
                sql_exec = text("""
                    INSERT INTO processo_executores (processo_id, funcionario_id)
                    VALUES (:pid, :fid)
                    RETURNING id
                """)
                
                for fid in executores_ids:
                    result = conn.execute(sql_exec, {"pid": processo_id, "fid": fid})
                    exec_id = result.scalar()
                    
                    # ===== LOG DO INSERT DO EXECUTOR =====
                    dados_novos_executor = {
                        'id': exec_id,
                        'processo_id': processo_id,
                        'funcionario_id': fid,
                        'funcionario_nome': funcionarios_info.get(fid)
                    }
                    
                    registrar_log(
                        tabela='processo_executores',
                        registro_id=exec_id,
                        operacao='INSERT',
                        dados_anteriores=None,
                        dados_novos=dados_novos_executor
                    )
                    # ===== FIM DO LOG =====
            
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
    """Retorna todos os riscos de um processo com sua categoria"""
    query = text("""
        SELECT r.id, r.nome_risco, r.fator_risco, r.melhoria, r.impacto, 
               r.probabilidade, r.apetite_risco, r.motivo_risco, r.score_risco,
               r.categoria
        FROM riscos r
        WHERE r.processo_id = :pid
        ORDER BY r.id
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"pid": processo_id})
        
        # Adicionar função para converter a string de categorias em lista de IDs
        if not df.empty:
            categorias_dict = {
                1: "Risco Financeiro",
                2: "Risco Legal", 
                3: "Risco Inerente",
                4: "Risco de TI",
                5: "Risco Reputacional",
                6: "Risco de Integridade",
                7: "Risco Ambiental"
            }
            
            # Criar dicionário reverso: nome -> id
            nome_para_id = {v: k for k, v in categorias_dict.items()}
            
            def converter_categoria_para_ids(categoria_str):
                if not categoria_str or pd.isna(categoria_str):
                    return []
                # Separar a string por vírgula
                nomes = [nome.strip() for nome in categoria_str.split(',') if nome.strip()]
                # Converter nomes para IDs
                ids = [nome_para_id[nome] for nome in nomes if nome in nome_para_id]
                return ids
            
            # Criar coluna categorias_ids
            df['categorias_ids'] = df['categoria'].apply(converter_categoria_para_ids)
        
        return df

def salvar_area(dados_area):
    try:
        query = text("""
            INSERT INTO informacoes_area 
            (nome_area, objetivo_area, status, email, telefone, gestor, loc_unidade)
            VALUES 
            (:nome, :objetivo, :status, :email, :telefone, :gestor, :loc_unidade)
            RETURNING id_area
        """)
        
        with engine.begin() as conn:
            id_area = conn.execute(query, {
                "nome": dados_area['nome'],
                "loc_unidade": dados_area.get('loc_unidade', ''),
                "objetivo": dados_area.get('objetivo', ''),
                "status": dados_area.get('status', 'Ativo'),
                "email": dados_area.get('email', ''),
                "telefone": dados_area.get('telefone', ''),
                "gestor": dados_area.get('gestor', '')
            }).scalar()
            
            # ====== REGISTRAR LOG ======
            from modules.shared.log_sistema import registrar_log
            registrar_log(
                tabela='informacoes_area',
                registro_id=id_area,
                operacao='INSERT',
                dados_novos=dados_area,
                query_sql="INSERT INTO informacoes_area (nome_area, objetivo_area, status, email, telefone, gestor)"
            )
            # ====== FIM DO LOG ======
            
        return id_area
    except Exception as e:
        print(f"Erro ao salvar área: {e}")
        return None

def listar_areas(apenas_ativas=True):
    """Lista áreas (por padrão, apenas as ativas)"""
    from database import engine
    from sqlalchemy import text
    
    if apenas_ativas:
        query = text("""
            SELECT id_area, nome_area, objetivo_area, status, email, telefone, gestor, loc_unidade
            FROM informacoes_area
            WHERE status = 'Ativo'
            ORDER BY nome_area
        """)
    else:
        query = text("""
            SELECT id_area, nome_area, objetivo_area, status, email, telefone, gestor, loc_unidade
            FROM informacoes_area
            ORDER BY 
                CASE WHEN status = 'Ativo' THEN 0 ELSE 1 END,
                nome_area
        """)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def salvar_funcionarios_area(id_area, funcionarios):
    """Salva múltiplos funcionários para uma área"""
    try:
        with engine.begin() as conn:
            # Buscar nome da área para o log
            area_info = conn.execute(
                text("SELECT nome_area FROM informacoes_area WHERE id_area = :id"),
                {"id": id_area}
            ).scalar()
            
            for func in funcionarios:
                # Verificar se funcionário já existe
                check_query = text("""
                    SELECT id FROM funcionarios_area 
                    WHERE id_area = :id_area AND nome_funcionario = :nome
                """)
                existing = conn.execute(check_query, {
                    "id_area": id_area,
                    "nome": func['nome']
                }).fetchone()
                
                if not existing:
                    insert_query = text("""
                        INSERT INTO funcionarios_area 
                        (id_area, nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa, ativo, created_at, updated_at)
                        VALUES (:id_area, :nome, :cargo, :data_funcao, :data_empresa, TRUE, NOW(), NOW())
                        RETURNING id
                    """)
                    result = conn.execute(insert_query, {
                        "id_area": id_area,
                        "nome": func['nome'],
                        "cargo": func.get('cargo', ''),
                        "data_funcao": func.get('data_inicio_funcao'),
                        "data_empresa": func.get('data_inicio_empresa')
                    })
                    
                    funcionario_id = result.scalar()
                    
                    # ===== ADICIONAR LOG AQUI =====
                    dados_inseridos = {
                        'id': funcionario_id,
                        'id_area': id_area,
                        'nome_area': area_info,
                        'nome_funcionario': func['nome'],
                        'cargo': func.get('cargo', ''),
                        'data_inicio_funcao': str(func.get('data_inicio_funcao')) if func.get('data_inicio_funcao') else None,
                        'data_inicio_empresa': str(func.get('data_inicio_empresa')) if func.get('data_inicio_empresa') else None,
                        'ativo': True
                    }
                    
                    registrar_log(
                        tabela='funcionarios_area',
                        registro_id=funcionario_id,
                        operacao='INSERT',
                        dados_anteriores=None,
                        dados_novos=dados_inseridos
                    )
                    # ===== FIM DO LOG =====
                else:
                    # Funcionário já existe - não faz nada
                    pass
                    
        return True
    except Exception as e:
        print(f"Erro ao salvar funcionários: {e}")
        return False

def listar_funcionarios_area(id_area):
    """Retorna todos os funcionários de uma área com datas"""
    query = text("""
        SELECT 
            id, 
            id_area, 
            nome_funcionario, 
            cargo,
            data_inicio_funcao,
            data_inicio_empresa,
            ativo,
            created_at,
            updated_at
        FROM funcionarios_area
        WHERE id_area = :id_area AND ativo = TRUE
        ORDER BY nome_funcionario
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"id_area": id_area})
    
def listar_funcionarios_area_todos(area_id):
    """Retorna TODOS os funcionários de uma área (ativos e inativos)"""
    from database import engine
    from sqlalchemy import text
    
    query = text("""
        SELECT id, nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa, ativo
        FROM funcionarios_area
        WHERE id_area = :area_id
        ORDER BY nome_funcionario
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"area_id": area_id})

def excluir_funcionario(funcionario_id):
    """Desativa um funcionário (soft delete) - mantém o histórico"""
    from database import engine
    from sqlalchemy import text
    
    print(f"🔍 Desativando funcionário ID: {funcionario_id}")
    
    try:
        # 1. Buscar dados ANTES da desativação (para o log)
        dados_anteriores = buscar_funcionario_por_id(funcionario_id)
        
        if not dados_anteriores:
            print(f"❌ Funcionário com ID {funcionario_id} não encontrado!")
            return False
        
        with engine.connect() as conn:
            # Verificar se o funcionário existe
            check_query = text("SELECT id FROM funcionarios_area WHERE id = :id")
            result_check = conn.execute(check_query, {"id": funcionario_id})
            existe = result_check.fetchone()
            
            if not existe:
                print(f"❌ Funcionário com ID {funcionario_id} não encontrado!")
                return False
            
            # Soft delete: atualizar ativo para false
            update_query = text("UPDATE funcionarios_area SET ativo = false WHERE id = :id")
            result = conn.execute(update_query, {"id": funcionario_id})
            conn.commit()
            
            print(f"✅ Funcionário desativado. Linhas afetadas: {result.rowcount}")

            # 2. Registrar log se a exclusão foi bem-sucedida
            if result.rowcount > 0:
                registrar_log(
                    tabela='funcionarios_area',
                    registro_id=funcionario_id,
                    operacao='DELETE',
                    dados_anteriores=dados_anteriores,
                    query_sql="UPDATE funcionarios_area SET ativo = false"
                )

            return result.rowcount > 0
            
    except Exception as e:
        print(f"❌ Erro ao desativar funcionário: {e}")
        return False

def excluir_area(area_id):
    """Desativa uma área e todos os seus funcionários (soft delete em cascata)"""
    from database import engine
    from sqlalchemy import text
    from modules.shared.log_sistema import registrar_log
    
    print(f"🔍 Desativando área ID: {area_id} e seus funcionários")
    
    try:
        dados_anteriores = buscar_area_por_id(area_id)
        if not dados_anteriores:
            print(f"❌ Área ID {area_id} não encontrada")
            return False
        
        with engine.connect() as conn:
            # Desativar funcionários
            update_funcionarios = text("""
                UPDATE funcionarios_area 
                SET ativo = false 
                WHERE id_area = :id
            """)
            conn.execute(update_funcionarios, {"id": area_id})
            
            # Desativar área
            update_area = text("""
                UPDATE informacoes_area 
                SET status = 'Inativo' 
                WHERE id_area = :id
            """)
            result_area = conn.execute(update_area, {"id": area_id})
            
            conn.commit()
            
            print(f"✅ Área {area_id} desativada com sucesso")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao desativar área: {e}")
        return False


def listar_funcionarios_por_area(id_area):
    """Retorna lista de funcionários com nome e ID (para selects)"""
    query = text("""
        SELECT id, nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa
        FROM funcionarios_area
        WHERE id_area = :id_area AND ativo = TRUE
        ORDER BY nome_funcionario
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"id_area": id_area})
        return [(row[0], row[1]) for row in result]  # id, nome

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

def get_categorias_lista():
    """Retorna apenas a lista de nomes das categorias"""
    return [
        "Risco Financeiro",
        "Risco Legal", 
        "Risco Inerente",
        "Risco de TI",
        "Risco Reputacional",
        "Risco de Integridade",
        "Risco Ambiental"
    ]

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
            
            # === BUSCAR DADOS ANTIGOS DO PROCESSO ===
            dados_antigos_processo = conn.execute(
                text("SELECT * FROM processos WHERE id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchone()
            
            # === CONCATENAR OBJETIVO ===
            objetivo_raw = st.session_state.get('edit_input_objetivo', '').strip()
            if objetivo_raw:
                objetivo_com_prefixo = f"Garantir {objetivo_raw}"
            else:
                objetivo_com_prefixo = ''
            
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
                "o": objetivo_com_prefixo,
                "d": st.session_state.get('edit_input_descricao', ''),
                "ei": st.session_state.get('edit_input_etapa_ini', ''),
                "ef": st.session_state.get('edit_input_etapa_fim', ''),
                "p": st.session_state.get('edit_input_produto', '')
            })
            
            # === LOG DO UPDATE DO PROCESSO ===
            dados_novos_processo = conn.execute(
                text("SELECT * FROM processos WHERE id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchone()
            
            registrar_log(
                tabela='processos',
                registro_id=processo_id,
                operacao='UPDATE',
                dados_anteriores=dict(dados_antigos_processo),
                dados_novos=dict(dados_novos_processo)
            )
            # ===== FIM DO LOG =====
            
            # === ATUALIZAR EXECUTORES ===
            # Buscar executores antigos
            executores_antigos = conn.execute(
                text("SELECT id, funcionario_id FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchall()
            
            # Registrar DELETE dos executores antigos
            for exec_antigo in executores_antigos:
                registrar_log(
                    tabela='processo_executores',
                    registro_id=exec_antigo['id'],
                    operacao='DELETE',
                    dados_anteriores={'processo_id': processo_id, 'funcionario_id': exec_antigo['funcionario_id']},
                    dados_novos=None
                )
            
            conn.execute(
                text("DELETE FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            )
            
            executores_ids = st.session_state.get('edit_executores_selecionados', [])
            if executores_ids:
                # Buscar nomes dos funcionários
                for fid in executores_ids:
                    func_nome = conn.execute(
                        text("SELECT nome_funcionario FROM funcionarios_area WHERE id = :id"),
                        {"id": fid}
                    ).scalar()
                    
                    sql_exec = text("""
                        INSERT INTO processo_executores (processo_id, funcionario_id)
                        VALUES (:pid, :fid)
                        RETURNING id
                    """)
                    result = conn.execute(sql_exec, {"pid": processo_id, "fid": fid})
                    exec_id = result.scalar()
                    
                    # LOG do INSERT do executor
                    registrar_log(
                        tabela='processo_executores',
                        registro_id=exec_id,
                        operacao='INSERT',
                        dados_anteriores=None,
                        dados_novos={
                            'processo_id': processo_id,
                            'funcionario_id': fid,
                            'funcionario_nome': func_nome
                        }
                    )
            
            # === ATUALIZAR RISCOS ===
            # Buscar riscos antigos
            riscos_antigos = conn.execute(
                text("SELECT id, nome_risco, score_risco, categoria FROM riscos WHERE processo_id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchall()
            
            # Registrar DELETE dos riscos antigos
            for risco_antigo in riscos_antigos:
                registrar_log(
                    tabela='riscos',
                    registro_id=risco_antigo['id'],
                    operacao='DELETE',
                    dados_anteriores=dict(risco_antigo),
                    dados_novos=None
                )
            
            conn.execute(text("DELETE FROM riscos WHERE processo_id = :pid"), {"pid": processo_id})
            
            sql_risco = text("""
                INSERT INTO riscos 
                (processo_id, nome_risco, fator_risco, melhoria, impacto, 
                probabilidade, apetite_risco, motivo_risco, score_risco, categoria) 
                VALUES 
                (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo, :score, :categoria)
                RETURNING id
            """)
            
            # Carregar mapa de categorias para conversão
            from logic import listar_categorias
            mapa_categorias = listar_categorias()
            
            for i in range(len(st.session_state.get('edit_riscos', []))):
                # === CONCATENAR NOME DO RISCO ===
                nome_risco_raw = st.session_state.get(f"edit_nome_{i}", '').strip()
                if nome_risco_raw:
                    nome_risco_com_prefixo = f"Risco pela possibilidade {nome_risco_raw}"
                else:
                    nome_risco_com_prefixo = ''
                
                # === CONCATENAR FATOR DO RISCO ===
                fator_raw = st.session_state.get(f"edit_fator_{i}", '').strip()
                if fator_raw:
                    fator_com_prefixo = f"Pelo motivo {fator_raw}"
                else:
                    fator_com_prefixo = ''
                
                imp = st.session_state.get(f"edit_imp_{i}")
                prob = st.session_state.get(f"edit_prob_{i}")
                score = MAPA_RISCO.get((imp, prob), 0)
                
                # === CONVERTER CATEGORIAS (IDs -> NOMES) ===
                categorias_ids = st.session_state.get(f"edit_categorias_{i}", [])
                if categorias_ids:
                    nomes_categorias = [mapa_categorias.get(cid) for cid in categorias_ids if cid in mapa_categorias]
                    categoria_str = ', '.join(nomes_categorias)
                else:
                    categoria_str = None
                
                result = conn.execute(sql_risco, {
                    "pid": processo_id, 
                    "nome": nome_risco_com_prefixo,
                    "fator": fator_com_prefixo,
                    "melhoria": st.session_state.get(f"edit_melhoria_{i}"), 
                    "imp": imp, 
                    "prob": prob, 
                    "apetite": st.session_state.get(f"edit_apetite_{i}"), 
                    "motivo": st.session_state.get(f"edit_motivo_{i}"), 
                    "score": score,
                    "categoria": categoria_str
                })
                
                risco_id = result.scalar()
                
                # LOG do INSERT do novo risco
                registrar_log(
                    tabela='riscos',
                    registro_id=risco_id,
                    operacao='INSERT',
                    dados_anteriores=None,
                    dados_novos={
                        'processo_id': processo_id,
                        'nome_risco': nome_risco_com_prefixo,
                        'impacto': imp,
                        'probabilidade': prob,
                        'score_risco': score,
                        'categoria': categoria_str
                    }
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
            tempo_restante = max(0, TEMPO_SESSAO_SEGUNDOS - tempo_decorrido)
            minutos = int(tempo_restante // 60)
            segundos = int(tempo_restante % 60)
            return f"{minutos:02d}:{segundos:02d}"
    return "00:00"

def salvar_edicao_processo_completa(dados):
    """Salva as alterações de um processo existente e seus riscos"""
    try:
        with engine.begin() as conn:
            processo_id = dados.get('processo_id')
            if not processo_id:
                return False
            
            # === BUSCAR DADOS ANTIGOS DO PROCESSO ===
            dados_antigos_processo = conn.execute(
                text("SELECT * FROM processos WHERE id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchone()
            
            # 1. Preparar Objetivo
            objetivo_raw = dados.get('objetivo', '').strip()
            objetivo_com_prefixo = f"Garantir {objetivo_raw}" if objetivo_raw else ''
            
            # 2. Atualizar dados básicos da tabela PROCESSOS
            sql_update = text("""
                UPDATE processos 
                SET nome_processo=:nome, objetivo=:o, descricao=:d, 
                    etapa_ini=:ei, etapa_fim=:ef, produto=:p
                WHERE id = :pid
            """)
            
            conn.execute(sql_update, {
                "pid": processo_id,
                "nome": dados.get('nome_processo', ''),
                "o": objetivo_com_prefixo,
                "d": dados.get('descricao', ''),
                "ei": dados.get('etapa_ini', ''),
                "ef": dados.get('etapa_fim', ''),
                "p": dados.get('produto', '')
            })
            
            # === LOG DO UPDATE DO PROCESSO ===
            dados_novos_processo = conn.execute(
                text("SELECT * FROM processos WHERE id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchone()
            
            registrar_log(
                tabela='processos',
                registro_id=processo_id,
                operacao='UPDATE',
                dados_anteriores=dict(dados_antigos_processo),
                dados_novos=dict(dados_novos_processo)
            )
            # ===== FIM DO LOG =====
            
            # 3. Atualizar executores (Limpa e reinsere)
            # Buscar executores antigos
            executores_antigos = conn.execute(
                text("SELECT id, funcionario_id FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchall()
            
            # Registrar DELETE dos executores antigos
            for exec_antigo in executores_antigos:
                registrar_log(
                    tabela='processo_executores',
                    registro_id=exec_antigo['id'],
                    operacao='DELETE',
                    dados_anteriores={'processo_id': processo_id, 'funcionario_id': exec_antigo['funcionario_id']},
                    dados_novos=None
                )
            
            conn.execute(
                text("DELETE FROM processo_executores WHERE processo_id = :pid"),
                {"pid": processo_id}
            )
            
            executores_ids = dados.get('executores', [])
            if executores_ids:
                sql_exec = text("INSERT INTO processo_executores (processo_id, funcionario_id) VALUES (:pid, :fid) RETURNING id")
                for fid in executores_ids:
                    # Buscar nome do funcionário
                    func_nome = conn.execute(
                        text("SELECT nome_funcionario FROM funcionarios_area WHERE id = :id"),
                        {"id": fid}
                    ).scalar()
                    
                    result = conn.execute(sql_exec, {"pid": processo_id, "fid": fid})
                    exec_id = result.scalar()
                    
                    # LOG do INSERT do executor
                    registrar_log(
                        tabela='processo_executores',
                        registro_id=exec_id,
                        operacao='INSERT',
                        dados_anteriores=None,
                        dados_novos={
                            'processo_id': processo_id,
                            'funcionario_id': fid,
                            'funcionario_nome': func_nome
                        }
                    )
            
            # 4. Atualizar RISCOS (Limpa e reinsere)
            # Buscar riscos antigos
            riscos_antigos = conn.execute(
                text("SELECT id, nome_risco, score_risco, categoria FROM riscos WHERE processo_id = :pid"),
                {"pid": processo_id}
            ).mappings().fetchall()
            
            # Registrar DELETE dos riscos antigos
            for risco_antigo in riscos_antigos:
                registrar_log(
                    tabela='riscos',
                    registro_id=risco_antigo['id'],
                    operacao='DELETE',
                    dados_anteriores=dict(risco_antigo),
                    dados_novos=None
                )
            
            conn.execute(text("DELETE FROM riscos WHERE processo_id = :pid"), {"pid": processo_id})
            
            sql_risco = text("""
                INSERT INTO riscos 
                (processo_id, nome_risco, fator_risco, melhoria, impacto, 
                 probabilidade, apetite_risco, motivo_risco, score_risco, categoria) 
                VALUES 
                (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo, :score, :cat)
                RETURNING id
            """)
            
            for risco in dados.get('riscos', []):
                mapa_categorias = listar_categorias()
                categorias_selecionadas = risco.get('categorias', [])
                
                if isinstance(categorias_selecionadas, list):
                    nomes_cats = [mapa_categorias.get(cid) for cid in categorias_selecionadas if cid in mapa_categorias]
                    categoria_final = ", ".join(nomes_cats)
                else:
                    categoria_final = mapa_categorias.get(categorias_selecionadas, str(categorias_selecionadas))

                nome_raw = risco.get('nome', '').strip()
                nome_com_prefixo = f"Risco pela possibilidade {nome_raw}" if nome_raw else ''
                
                fator_raw = risco.get('fator', '').strip()
                fator_com_prefixo = f"Pelo motivo {fator_raw}" if fator_raw else ''
                
                imp = risco.get('impacto', 'Médio')
                prob = risco.get('probabilidade', 'Médio')
                score = MAPA_RISCO.get((imp, prob), 0)
                
                result = conn.execute(sql_risco, {
                    "pid": processo_id,
                    "nome": nome_com_prefixo,
                    "fator": fator_com_prefixo,
                    "melhoria": risco.get('melhoria', ''),
                    "imp": imp,
                    "prob": prob,
                    "apetite": risco.get('apetite', ''),
                    "motivo": risco.get('motivo', ''),
                    "score": score,
                    "cat": categoria_final
                })
                
                risco_id = result.scalar()
                
                # LOG do INSERT do novo risco
                registrar_log(
                    tabela='riscos',
                    registro_id=risco_id,
                    operacao='INSERT',
                    dados_anteriores=None,
                    dados_novos={
                        'processo_id': processo_id,
                        'nome_risco': nome_com_prefixo,
                        'impacto': imp,
                        'probabilidade': prob,
                        'score_risco': score,
                        'categoria': categoria_final
                    }
                )
            
        return True
    except Exception as e:
        print(f"Erro ao salvar edição: {e}")
        return False

def listar_respostas_checklist(processo_id, auditoria_id):
    """Lista todas as respostas do checklist para um processo"""
    query = text("""
        SELECT 
            cgp.pergunta,
            cgp.tipo_resposta,
            cr.resposta,
            cr.comentario,
            cr.data_resposta,
            COUNT(ce.id) as num_evidencias
        FROM checklist_sessoes cg
        JOIN checklist_respostas cr ON cr.checklist_id = cg.id
        JOIN checklist_perguntas_padrao cgp ON cgp.id = cr.pergunta_id
        LEFT JOIN checklist_evidencias ce ON ce.resposta_id = cr.id
        WHERE cg.processo_id = :processo_id AND cg.auditoria_id = :auditoria_id
        GROUP BY cgp.id, cr.id
        ORDER BY cgp.ordem
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={
            "processo_id": processo_id,
            "auditoria_id": auditoria_id
        })

def listar_controles_do_processo(processo_id, auditoria_id):
    """Lista todos os controles de todas as etapas de um processo"""
    query = text("""
        SELECT 
            c.id as controle_id,
            c.nome_controle,
            c.natureza,
            c.forma_execucao,
            c.status_controle,
            c.frequencia_evidencia,
            c.responsaveis_tratamento,
            c.risco_avaliacao,
            c.causa_motivo,
            c.objetivo_controle,
            e.id as etapa_id,
            e.codigo_etapa,
            e.descricao_etapa,
            r.fator_risco as risco_fator,
            r.categoria as risco_categoria
        FROM controles_etapa c
        JOIN riscos_etapa r ON c.risco_id = r.id
        JOIN etapas_processo e ON r.etapa_id = e.id
        WHERE e.processo_id = :processo_id 
          AND e.auditoria_id = :auditoria_id
          AND c.status_controle = 'Ativo'
        ORDER BY e.codigo_etapa, c.nome_controle
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={
            "processo_id": processo_id,
            "auditoria_id": auditoria_id
        })

def calcular_tempo(data_inicio):
    """Calcula o tempo decorrido desde uma data até hoje"""
    if not data_inicio:
        return "Não informado"
    
    hoje = datetime.now().date()
    
    # Se for string, converter para date
    if isinstance(data_inicio, str):
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except:
            return "Data inválida"
    
    anos = hoje.year - data_inicio.year
    meses = hoje.month - data_inicio.month
    
    if meses < 0:
        anos -= 1
        meses += 12
    
    # Construir a string de resultado
    resultado = []
    
    if anos > 0:
        if anos == 1:
            resultado.append(f"{anos} ano")
        else:
            resultado.append(f"{anos} anos")
    
    if meses > 0:
        if meses == 1:
            resultado.append(f"{meses} mês")
        else:
            resultado.append(f"{meses} meses")
    
    # Se não houver anos nem meses, retornar mensagem adequada
    if not resultado:
        return "Menos de 1 mês"
    
    return " e ".join(resultado) if len(resultado) > 1 else resultado[0]

def formatar_tempo_funcionario(funcionario):
    """Formata o tempo de função e empresa para exibição"""
    data_funcao = funcionario.get('data_inicio_funcao')
    data_empresa = funcionario.get('data_inicio_empresa')
    tempo_funcao = calcular_tempo(data_funcao) if data_funcao else "Não informado"
    tempo_empresa = calcular_tempo(data_empresa) if data_empresa else "Não informado"

    return tempo_funcao, tempo_empresa

def salvar_diagrama_etapa(etapa_id, arquivo):
    """Salva o diagrama BPMN de uma etapa"""
    if arquivo is not None:
        conteudo = arquivo.read()
        
        # Buscar dados ANTIGOS da etapa antes de atualizar
        with engine.connect() as conn:
            dados_antigos = conn.execute(
                text("""
                    SELECT id, codigo_etapa, descricao_etapa, 
                           diagrama_nome, diagrama_tipo, processo_id
                    FROM etapas_processo 
                    WHERE id = :etapa_id
                """),
                {"etapa_id": etapa_id}
            ).mappings().fetchone()
            
            if not dados_antigos:
                print(f"Erro: Etapa {etapa_id} não encontrada")
                return False
        
        query = text("""
            UPDATE etapas_processo
            SET diagrama_bpmn = :conteudo,
                diagrama_nome = :nome,
                diagrama_tipo = :tipo,
                updated_at = NOW()
            WHERE id = :etapa_id
            RETURNING id
        """)
        
        with engine.begin() as conn:
            result = conn.execute(query, {
                "etapa_id": etapa_id,
                "conteudo": conteudo,
                "nome": arquivo.name,
                "tipo": arquivo.type
            }).scalar()
            
            # ===== ADICIONAR LOG AQUI =====
            # Buscar nome do processo para contexto
            with engine.connect() as conn:
                processo_info = conn.execute(
                    text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
                    {"id": dados_antigos['processo_id']}
                ).mappings().fetchone()
            
            dados_novos = {
                'id': etapa_id,
                'codigo_etapa': dados_antigos['codigo_etapa'],
                'descricao_etapa': dados_antigos['descricao_etapa'][:100] if dados_antigos['descricao_etapa'] else None,
                'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                'processo_nome': processo_info['nome_processo'] if processo_info else None,
                'diagrama_nome_anterior': dados_antigos.get('diagrama_nome'),
                'diagrama_nome_novo': arquivo.name,
                'diagrama_tipo': arquivo.type
            }
            
            dados_antigos_resumidos = {
                'id': etapa_id,
                'codigo_etapa': dados_antigos['codigo_etapa'],
                'descricao_etapa': dados_antigos['descricao_etapa'][:100] if dados_antigos['descricao_etapa'] else None,
                'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                'processo_nome': processo_info['nome_processo'] if processo_info else None,
                'diagrama_nome': dados_antigos.get('diagrama_nome'),
                'diagrama_tipo': dados_antigos.get('diagrama_tipo')
            }
            
            registrar_log(
                tabela='etapas_processo',
                registro_id=etapa_id,
                operacao='UPDATE',
                dados_anteriores=dados_antigos_resumidos,
                dados_novos=dados_novos
            )
            # ===== FIM DO LOG =====
        
        return True
    return False

def salvar_manual_etapa(etapa_id, arquivo):
    """Salva o manual da etapa"""
    if arquivo is not None:
        conteudo = arquivo.read()
        
        # Buscar dados ANTIGOS da etapa antes de atualizar
        with engine.connect() as conn:
            dados_antigos = conn.execute(
                text("""
                    SELECT id, codigo_etapa, descricao_etapa, 
                           manual_nome, manual_tipo, processo_id
                    FROM etapas_processo 
                    WHERE id = :etapa_id
                """),
                {"etapa_id": etapa_id}
            ).mappings().fetchone()
            
            if not dados_antigos:
                print(f"Erro: Etapa {etapa_id} não encontrada")
                return False
        
        query = text("""
            UPDATE etapas_processo 
            SET manual_etapa = :conteudo,
                manual_nome = :nome,
                manual_tipo = :tipo,
                updated_at = NOW()
            WHERE id = :etapa_id
            RETURNING id
        """)
        
        with engine.begin() as conn:
            result = conn.execute(query, {
                "etapa_id": etapa_id,
                "conteudo": conteudo,
                "nome": arquivo.name,
                "tipo": arquivo.type
            }).scalar()
            
            # ===== ADICIONAR LOG AQUI =====
            # Buscar nome do processo para contexto
            with engine.connect() as conn:
                processo_info = conn.execute(
                    text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
                    {"id": dados_antigos['processo_id']}
                ).mappings().fetchone()
            
            dados_novos = {
                'id': etapa_id,
                'codigo_etapa': dados_antigos['codigo_etapa'],
                'descricao_etapa': dados_antigos['descricao_etapa'][:100] if dados_antigos['descricao_etapa'] else None,
                'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                'processo_nome': processo_info['nome_processo'] if processo_info else None,
                'manual_nome_anterior': dados_antigos.get('manual_nome'),
                'manual_nome_novo': arquivo.name,
                'manual_tipo': arquivo.type
            }
            
            dados_antigos_resumidos = {
                'id': etapa_id,
                'codigo_etapa': dados_antigos['codigo_etapa'],
                'descricao_etapa': dados_antigos['descricao_etapa'][:100] if dados_antigos['descricao_etapa'] else None,
                'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                'processo_nome': processo_info['nome_processo'] if processo_info else None,
                'manual_nome': dados_antigos.get('manual_nome'),
                'manual_tipo': dados_antigos.get('manual_tipo')
            }
            
            registrar_log(
                tabela='etapas_processo',
                registro_id=etapa_id,
                operacao='UPDATE',
                dados_anteriores=dados_antigos_resumidos,
                dados_novos=dados_novos
            )
            # ===== FIM DO LOG =====
        
        return True
    return False

def baixar_diagrama_etapa(etapa_id):
    """Recupera o diagrama da etapa para download"""
    query = text("""
        SELECT diagrama_bpmn, diagrama_nome, diagrama_tipo
        FROM etapas_processo
        WHERE id = :etapa_id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"etapa_id": etapa_id}).fetchone()
        if result and result[0]:
            conteudo = result[0]
            if isinstance(conteudo, memoryview):
                conteudo = bytes(conteudo)
            return conteudo, result[1], result[2]
    return None, None, None

def baixar_manual_etapa(etapa_id):
    """Recupera o manual da etapa para download"""
    query = text("""
        SELECT manual_etapa, manual_nome, manual_tipo
        FROM etapas_processo
        WHERE id = :etapa_id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"etapa_id": etapa_id}).fetchone()
        if result and result[0]:
            conteudo = result[0]
            if isinstance(conteudo, memoryview):
                conteudo = bytes(conteudo)
            return conteudo, result[1], result[2]
    return None, None, None

def salvar_funcionario(dados):
    """Salva um novo funcionário no banco de dados"""
    from database import engine
    from sqlalchemy import text
    
    try:
        query = text("""
            INSERT INTO funcionarios_area 
            (id_area, nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa, ativo)
            VALUES 
            (:id_area, :nome, :cargo, :data_inicio_funcao, :data_inicio_empresa, true)
            RETURNING id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {
                "id_area": dados['id_area'],
                "nome": dados['nome'],
                "cargo": dados.get('cargo', ''),
                "data_inicio_funcao": dados.get('data_inicio_funcao'),
                "data_inicio_empresa": dados.get('data_inicio_empresa')
            })
            conn.commit()
            novo_id = result.scalar()

            # ====== REGISTRAR LOG ======
            if novo_id:
                registrar_log(
                    tabela='funcionarios_area',
                    registro_id=novo_id,
                    operacao='INSERT',
                    dados_novos=dados,
                    query_sql='INSERT INTO funcionarios_area (id_area, nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa, ativo)'
                )

            # ====== FIM DO LOG ======

            return novo_id
    except Exception as e:
        print(f"Erro ao salvar funcionário: {e}")
        return None

def buscar_area_por_id(area_id):
    """Buscar uma área pelo ID (retorna dicionário para log)"""
    from database import engine
    from sqlalchemy import text

    query = text("""
        SELECT id_area, nome_area, email, telefone, gestor, objetivo_area, status
        FROM informacoes_area
        WHERE id_area = :id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"id": area_id}).mappings().first()
        return dict(result) if result else None
    

def atualizar_area(area_id, dados):
    """Atualiza uma área existente"""
    from database import engine
    from sqlalchemy import text
    
    try:

        # 1. Buscar dados ANTES da alteração
        dados_anteriores = buscar_area_por_id(area_id)

        if not dados_anteriores:
            print(f"❌ Área ID {area_id} não encontrada para atualização")
            return False
        
        # 2. Executar o UPDATE
        query = text("""
            UPDATE informacoes_area 
            SET nome_area = :nome,
                email = :email,
                telefone = :telefone,
                gestor = :gestor,
                objetivo_area = :objetivo,
                loc_unidade = :loc_unidade
            WHERE id_area = :id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {
                "id": area_id,
                "nome": dados['nome'],
                "email": dados.get('email', ''),
                "telefone": dados.get('telefone', ''),
                "gestor": dados.get('gestor', ''),
                "objetivo": dados.get('objetivo', ''),
                "loc_unidade": dados.get('loc_unidade', '')
            })
            conn.commit()

            # 3. Registrar log se a atualização foi bem-sucedida
            if result.rowcount > 0:
                registrar_log(
                    tabela='informacoes_area',
                    registro_id=area_id,
                    operacao='UPDATE',
                    dados_anteriores=dados_anteriores,
                    dados_novos=dados,
                    query_sql="UPDATE informacoes_area SET nome_area, email, telefone, gestor, objetivo_area"
                )
            return result.rowcount > 0
    except Exception as e:
        print(f"Erro ao atualizar área: {e}")
        return False

def atualizar_funcionario(funcionario_id, dados):
    """Atualiza um funcionário existente"""
    from database import engine
    from sqlalchemy import text
    
    try:
        # 1. Bscar dados ANTES da alteração
        dados_anteriores = buscar_funcionario_por_id(funcionario_id)

        if not dados_anteriores:
            print(f"❌ Funcionário ID {funcionario_id} não encontrado")
            return False
        
        # 2. Executar o UPDATE
        query = text("""
            UPDATE funcionarios_area
            SET nome_funcionario = :nome,
                cargo = :cargo,
                data_inicio_funcao = :data_inicio_funcao,
                data_inicio_empresa = :data_inicio_empresa
            WHERE id = :id
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {
                "id": funcionario_id,
                "nome": dados['nome'],
                "cargo": dados.get('cargo', ''),
                "data_inicio_funcao": dados.get('data_inicio_funcao'),
                "data_inicio_empresa": dados.get('data_inicio_empresa')
            })

            conn.commit()

            # 3. Registrar log se a atualização foi bem-sucedida
            if result.rowcount > 0:
                registrar_log(
                    tabela='funcionarios_area',
                    registro_id=funcionario_id,
                    operacao='UPDATE',
                    dados_anteriores=dados_anteriores,
                    dados_novos=dados,
                    query_sql="UPDATE funcionarios_area SET nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa"
                )

            return result.rowcount > 0 
    except Exception as e:
        print(f"Erro ao atualizar funcionário: {e}")
        return False
    
def buscar_funcionario_por_id(funcionario_id):
    """Busca um funcionario pelo ID"""
    from database import engine
    from sqlalchemy import text

    try:
        query = text("""
            SELECT id, nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa
            FROM funcionarios_area
            WHERE id = :id
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"id": funcionario_id}).mappings().first()
            return dict(result) if result else None
    except Exception as e:
        print(f"Erro ao buscar funcionário: {e}")
        return None
    
def reativar_area(area_id):
    """Reativa uma área (soft delete reverso)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("UPDATE informacoes_area SET status = 'Ativo' WHERE id_area = :id")
            result = conn.execute(query, {"id": area_id})
            conn.commit()
            return result.rowcount > 0
    except Exception as e:
        print(f"Erro ao reativar área: {e}")
        return False

def buscar_processo_por_nome_e_area(nome_processo, id_area, auditoria_id):
    """Verifica se já existe um processo com mesmo nome na área E auditoria"""
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        query = text("""
            SELECT id, codigo_processo 
            FROM processos 
            WHERE nome_processo = :nome 
            AND id_area = :id_area 
            AND auditoria_id = :auditoria_id
            AND status = 'Ativo'
        """)
        result = conn.execute(query, {
            'nome': nome_processo,
            'id_area': id_area,
            'auditoria_id': auditoria_id
        }).fetchone()
        
        if result:
            return {'id': result[0], 'codigo_processo': result[1]}
        return None

def gerar_codigo_processo(id_area):
    """
    Gera o próximo código sequencial para um processo de uma área.
    Busca o MAIOR número existente, independente da ordem de inserção.
    """
    from database import engine
    from sqlalchemy import text
    
    # Solução usando SPLIT_PART (mais legível)
    query = text("""
        SELECT COALESCE(
            MAX(CAST(SPLIT_PART(codigo_processo, '.', 2) AS INTEGER)), 
            0
        ) as max_sequencial
        FROM processos 
        WHERE id_area = :id_area
        AND codigo_processo LIKE '%.%'
        AND codigo_processo ~ '^[0-9]+\.[0-9]+$'
    """)
    
    with engine.connect() as conn:
        resultado = conn.execute(query, {"id_area": id_area}).fetchone()
        max_sequencial = resultado[0] if resultado else 0
        
        novo_numero = max_sequencial + 1
    
    codigo = f"{id_area}.{novo_numero}"
    
    return codigo

def carregar_areas_banco():
    """ Busca áreas no Banco de Dados e retorna um dicionário {nome: id}."""
    query = text("SELECT id_area, nome_area FROM informacoes_area")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Transforma o DataFrame em um dicionário {'Nome da Área': id_area}
    # Zip junta as duas colunas: a primeira vira chave, a segunda vira valor
    return dict(zip(df['nome_area'], df['id_area']))

def calcular_score_risco_etapa(impacto, probabilidade):
    """Calcula o score do risco baseado no impacto e probabilidade"""
    mapa_impacto = {
        'Muito Alto': 5, 'Alto': 4, 'Médio': 3, 'Baixo': 2, 'Muito Baixo': 1
    }
    mapa_prob = {
        'Muito Alta': 5, 'Alta': 4, 'Média': 3, 'Baixa': 2, 'Muito Baixa': 1
    }
    
    imp_val = mapa_impacto.get(impacto, 3)
    prob_val = mapa_prob.get(probabilidade, 3)
    
    return imp_val * prob_val

def gerar_relatorio_gerencial_area(area_id, area_nome, gestor, orientacao="RETRATO", auditoria_id=None):
    """Gera relatório gerencial da área (para validação do gestor)"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    import io
    import os
    import math
    import pandas as pd
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    from logic import get_estilo_risco
    
    buffer = io.BytesIO()
    
    # Definir orientação da página
    if orientacao.upper() == "PAISAGEM":
        pagesize = landscape(A4)
        topMargin = 1.5*cm
        bottomMargin = 2*cm
        leftMargin = 1.0*cm
        rightMargin = 1.0*cm
        col_widths = [3.0*cm, 8*cm, 12*cm, 3.0*cm]
    else:
        pagesize = A4
        topMargin = 1.5*cm
        bottomMargin = 2*cm
        leftMargin = 3*cm
        rightMargin = 2*cm
        col_widths = [2.2*cm, 4.5*cm, 7.5*cm, 2.2*cm]
    
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, 
                           topMargin=topMargin, bottomMargin=bottomMargin,
                           leftMargin=leftMargin, rightMargin=rightMargin)
    
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor('#0b5b99')
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    # ===== CABEÇALHO COM LOGOS (APENAS NA PRIMEIRA PÁGINA) =====
    root_dir = os.path.dirname(os.path.abspath(__file__))
    logo_fusve_path = os.path.join(root_dir, "static", "assets", "logo_fusve.png")
    logo_auditoria_path = os.path.join(root_dir, "static", "assets", "logo_auditoria-removebg-preview.png")
        
    header_data = []
    tem_logo_esquerda = os.path.exists(logo_fusve_path)
    tem_logo_direita = os.path.exists(logo_auditoria_path)
    
    if tem_logo_esquerda or tem_logo_direita:
        logos_linha = []
        if tem_logo_esquerda:
            img_esquerda = Image(logo_fusve_path, width=4*cm, height=1.5*cm)
            logos_linha.append(img_esquerda)
        else:
            logos_linha.append(Paragraph("", normal_style))
        
        logos_linha.append(Paragraph("", normal_style))
        
        if tem_logo_direita:
            img_direita = Image(logo_auditoria_path, width=5.0*cm, height=1.8*cm)
            logos_linha.append(img_direita)
        else:
            logos_linha.append(Paragraph("", normal_style))
        
        header_data.append(logos_linha)
        
        header_table = Table(header_data, colWidths=[4*cm, 8*cm, 4*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
    
    # ===== TÍTULO PRINCIPAL =====
    story.append(Paragraph("Relatório de Diagnóstico da Auditoria", titulo_style))
    
    # Buscar código da auditoria
    codigo_auditoria = ""
    if auditoria_id:
        with engine.connect() as conn:
            query_auditoria = text("SELECT codigo_auditoria FROM auditorias WHERE id = :auditoria_id")
            result_aud = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
            if result_aud:
                codigo_auditoria = result_aud[0]
    
    # Informações
    story.append(Paragraph(f"<b>Auditoria:</b> {codigo_auditoria}", normal_style))
    story.append(Paragraph(f"<b>Área:</b> {area_nome}", normal_style))
    story.append(Paragraph(f"<b>Gestor Responsável:</b> {gestor}", normal_style))
    story.append(Paragraph(f"<b>Data de Geração:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
    story.append(Spacer(1, 20))
    
    # ===== BUSCAR PROCESSOS =====
    query = text("""
        SELECT 
            p.id,
            p.codigo_processo,
            p.nome_processo,
            r.id as risco_id,
            r.nome_risco,
            r.score_risco,
            r.impacto,
            r.probabilidade
        FROM processos p
        INNER JOIN auditoria_processos ap ON p.id = ap.processo_id
        LEFT JOIN riscos r ON p.id = r.processo_id
        WHERE ap.auditoria_id = :auditoria_id 
          AND p.id_area = :area_id 
          AND p.status = 'Ativo'
        ORDER BY 
            string_to_array(p.codigo_processo, '.')::int[],
            r.score_risco DESC NULLS LAST
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"area_id": area_id, "auditoria_id": auditoria_id})
    
    total_riscos = df['risco_id'].notna().sum()
    
    if df.empty:
        story.append(Paragraph("Nenhum processo encontrado para esta área.", normal_style))
    else:
        story.append(Paragraph(f"<b>Quantidade de Riscos identificados:</b> {total_riscos}", normal_style))
        story.append(Spacer(1, 20))
        story.append(Paragraph("<b>Processos e Riscos Identificados</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        data = [[
            Paragraph("<b>Código</b>", normal_style),
            Paragraph("<b>Processo</b>", normal_style),
            Paragraph("<b>Risco Identificado</b>", normal_style),
            Paragraph("<b>Risco Bruto</b>", normal_style)
        ]]
        
        for _, row in df.iterrows():
            codigo = Paragraph(str(row['codigo_processo']) if row['codigo_processo'] else "N/A", normal_style)
            nome_processo = Paragraph(str(row['nome_processo']) if row['nome_processo'] else "Não informado", normal_style)
            
            if row['risco_id']:
                nome_risco = str(row['nome_risco']) if row['nome_risco'] else "Risco não nomeado"
                risco_nome = Paragraph(nome_risco, normal_style)
                
                score = row['score_risco']
                if isinstance(score, float) and math.isnan(score):
                    score = None
                
                cor_risco, _ = get_estilo_risco(score)
                texto_score = str(int(score)) if score is not None else "-"
                risco_bruto = Paragraph(f'<font color="{cor_risco}"><b>{texto_score}</b></font>', normal_style)
            else:
                risco_nome = Paragraph("<i>Nenhum risco cadastrado</i>", normal_style)
                risco_bruto = Paragraph("0", normal_style)
            
            data.append([codigo, nome_processo, risco_nome, risco_bruto])
        
        tabela = Table(data, colWidths=col_widths, repeatRows=1)
        
        tabela_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b5b99')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 1), (0, -1), 'MIDDLE'),
            ('VALIGN', (3, 1), (3, -1), 'MIDDLE'),
            ('VALIGN', (1, 1), (2, -1), 'TOP'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),
        ])
        
        for i in range(1, len(data)):
            if i % 2 == 1:
                tabela_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#e8f4f8'))
        
        tabela.setStyle(tabela_style)
        story.append(tabela)

        # ===== SEÇÃO 2: DETALHAMENTO POR PROCESSO =====
        story.append(PageBreak())
        
        # Título da seção
        story.append(Paragraph("<b>Detalhamento dos Processos</b>", styles['Heading1']))
        story.append(Spacer(1, 15))
        
        # Estilo para box de processo
        processo_box_style = ParagraphStyle(
            'ProcessoBox',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=colors.HexColor('#184145'),
            borderPadding=(8, 12, 8, 12),
            spaceAfter=10,
        )
        
        etapa_header_style = ParagraphStyle(
            'EtapaHeader',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#184145'),
            fontName='Helvetica-Bold',
            spaceBefore=10,
            spaceAfter=5,
        )
        
        sub_header_style = ParagraphStyle(
            'SubHeader',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#0b5b99'),
            fontName='Helvetica-Bold',
            spaceBefore=8,
            spaceAfter=4,
        )
        
        # Linha separadora colorida
        def add_separador(cor=colors.HexColor('#cccccc'), espaco_antes=5, espaco_depois=5):
            story.append(Spacer(1, espaco_antes))
            sep_data = [['']]
            sep_table = Table(sep_data, colWidths=[pagesize[0] - leftMargin - rightMargin])
            sep_table.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, cor),
            ]))
            story.append(sep_table)
            story.append(Spacer(1, espaco_depois))
        
        query_processos = text("""
            SELECT p.id, p.codigo_processo, p.nome_processo, p.objetivo
            FROM processos p
            INNER JOIN auditoria_processos ap ON p.id = ap.processo_id
            WHERE ap.auditoria_id = :auditoria_id 
            AND p.id_area = :area_id 
            AND p.status = 'Ativo'
            GROUP BY p.id, p.codigo_processo, p.nome_processo, p.objetivo
            ORDER BY string_to_array(p.codigo_processo, '.')::int[]
        """)
        
        with engine.connect() as conn:
            processos = conn.execute(query_processos, {
                "area_id": area_id, 
                "auditoria_id": auditoria_id
            }).fetchall()
        
        for idx, proc in enumerate(processos):
            proc_id = proc[0]
            proc_codigo = proc[1]
            proc_nome = proc[2]
            proc_objetivo = proc[3] or 'Não informado'
            
            # Cada processo começa em nova página (exceto o primeiro)
            if idx > 0:
                story.append(PageBreak())
            
            # ===== CABEÇALHO DO PROCESSO (SIMPLES, SEM FUNDO) =====
            story.append(Paragraph(
                f"<b>Processo: {proc_codigo} - {proc_nome}</b>",
                styles['Heading2']
            ))
            story.append(Spacer(1, 5))
            
            # Objetivo do processo
            story.append(Paragraph(f"<b>Objetivo:</b> {proc_objetivo}", normal_style))
            story.append(Spacer(1, 12))
            
            # Buscar etapas
            query_etapas = text("""
                SELECT ep.id, ep.nome_etapa, ep.descricao_etapa, ep.codigo_etapa
                FROM etapas_processo ep
                WHERE ep.processo_id = :processo_id
                ORDER BY ep.id
            """)
            
            with engine.connect() as conn:
                etapas = conn.execute(query_etapas, {"processo_id": proc_id}).fetchall()
            
            if not etapas:
                story.append(Paragraph("<i>Nenhuma etapa cadastrada para este processo.</i>", normal_style))
                continue
            
            story.append(Paragraph("<b>Etapas do Processo:</b>", styles['Heading3']))
            story.append(Spacer(1, 5))
            
            for etapa_idx, etapa in enumerate(etapas):
                etapa_id = etapa[0]
                etapa_nome = etapa[1] or 'Etapa sem nome'
                etapa_desc = etapa[2] or ''
                etapa_codigo = etapa[3] or ''
                
                # Fundo alternado para cada etapa
                bg_cor = colors.HexColor('#f8f9fa') if etapa_idx % 2 == 0 else colors.white
                
                # Box da etapa
                etapa_header = Paragraph(
                    f"<b>Etapa {etapa_codigo}: {etapa_nome}</b>", 
                    etapa_header_style
                )
                
                # Criar uma tabela de 1 coluna para a etapa (efeito de card)
                etapa_conteudo = []
                
                if etapa_desc:
                    etapa_conteudo.append([
                        Paragraph(f"{etapa_desc[:300]}{'...' if len(etapa_desc) > 300 else ''}", normal_style)
                    ])
                
                # Riscos da etapa
                query_riscos_etapa = text("""
                    SELECT re.nome_risco, re.impacto, re.probabilidade, re.fator_risco
                    FROM riscos_etapa re
                    WHERE re.etapa_id = :etapa_id
                    ORDER BY re.id
                """)
                
                with engine.connect() as conn:
                    riscos_etapa = conn.execute(query_riscos_etapa, {"etapa_id": etapa_id}).fetchall()
                
                if riscos_etapa:
                    # Montar tabela de riscos
                    riscos_todas = [[
                        Paragraph("<b>Risco</b>", normal_style),
                        Paragraph("<b>Impacto</b>", normal_style),
                        Paragraph("<b>Prob.</b>", normal_style),
                        Paragraph("<b>Score</b>", normal_style),
                    ]]
                    
                    for r in riscos_etapa:
                        impacto = r[1] or 'Médio'
                        probabilidade = r[2] or 'Médio'
                        score = calcular_score_risco_etapa(impacto, probabilidade)
                        cor_risco, _ = get_estilo_risco(score)
                        
                        riscos_todas.append([
                            Paragraph(str(r[0]) if r[0] else "-", normal_style),
                            Paragraph(impacto, normal_style),
                            Paragraph(probabilidade, normal_style),
                            Paragraph(f'<font color="{cor_risco}"><b>{score}</b></font>', normal_style),
                        ])
                    
                    tabela_riscos = Table(riscos_todas, colWidths=[6*cm, 3*cm, 3*cm, 3*cm])
                    tabela_riscos.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fd6a14')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ]))
                    
                    etapa_conteudo.append([Paragraph("<b>Riscos:</b>", sub_header_style)])
                    etapa_conteudo.append([tabela_riscos])
                else:
                    etapa_conteudo.append([Paragraph("<i>Nenhum risco cadastrado.</i>", normal_style)])
                
                # Controles da etapa
                query_controles_etapa = text("""
                    SELECT ce.nome_controle, ce.como_executado, ce.natureza
                    FROM controles_etapa ce
                    WHERE ce.risco_id IN (
                        SELECT id FROM riscos_etapa WHERE etapa_id = :etapa_id
                    )
                    ORDER BY ce.id
                """)
                
                with engine.connect() as conn:
                    controles_etapa = conn.execute(query_controles_etapa, {"etapa_id": etapa_id}).fetchall()
                
                if controles_etapa:
                    controles_todas = [[
                        Paragraph("<b>Controle</b>", normal_style),
                        Paragraph("<b>Como Executado</b>", normal_style),
                        Paragraph("<b>Natureza</b>", normal_style),
                    ]]
                    
                    for c in controles_etapa:
                        controles_todas.append([
                            Paragraph(str(c[0]) if c[0] else "-", normal_style),
                            Paragraph(str(c[1])[:120] if c[1] else "-", normal_style),
                            Paragraph(str(c[2]) if c[2] else "-", normal_style),
                        ])
                    
                    tabela_controles = Table(controles_todas, colWidths=[4.5*cm, 7*cm, 3.5*cm])
                    tabela_controles.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17a2b8')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ]))
                    
                    etapa_conteudo.append([Paragraph("<b>Controles:</b>", sub_header_style)])
                    etapa_conteudo.append([tabela_controles])
                
                # Montar tabela da etapa
                etapa_table = Table(etapa_conteudo, colWidths=[pagesize[0] - leftMargin - rightMargin])
                etapa_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), bg_cor),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('ROUNDEDCORNERS', [4, 4, 4, 4]),
                ]))
                
                story.append(etapa_header)
                story.append(etapa_table)
                story.append(Spacer(1, 8))
            
            # Separador entre processos (exceto último)
            if idx < len(processos) - 1:
                add_separador(colors.HexColor('#184145'), 10, 5)
    
    story.append(PageBreak())
    
    # ===== PÁGINA DE VALIDAÇÃO DO GESTOR =====
    story.append(Paragraph("<b>Validação do Gestor</b>", styles['Heading1']))
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "Declaro que tomei ciência dos riscos identificados nos processos da minha área "
        "e comprometo-me a tratar as não conformidades apontadas, conforme plano de ação a ser desenvolvido.",
        normal_style
    ))
    story.append(Spacer(1, 50))
    story.append(Paragraph(f"<b>Gestor:</b> {gestor}", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Data:</b> ___/___/_______", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Assinatura:</b> ________________________________", normal_style))
    
    # ===== RODAPÉ EM TODAS AS PÁGINAS =====
    def rodape(canvas, doc):
        canvas.saveState()
        
        # Linha separadora
        canvas.setStrokeColor(colors.HexColor('#cccccc'))
        canvas.line(leftMargin, bottomMargin + 0.3*cm, pagesize[0] - rightMargin, bottomMargin + 0.3*cm)
        
        # Número da página
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawCentredString(pagesize[0]/2, bottomMargin - 0.5*cm, f"Página {doc.page}")
        
        # Data
        data_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        canvas.setFont('Helvetica', 8)
        canvas.drawString(leftMargin, bottomMargin - 0.5*cm, f"Gerado em: {data_str}")
        
        # Área
        area_abreviada = area_nome[:35] + "..." if len(area_nome) > 35 else area_nome
        canvas.drawRightString(pagesize[0] - rightMargin, bottomMargin - 0.5*cm, f"Gerência de Auditoria Interna")
        
        canvas.restoreState()
    
    # Construir o documento com rodapé em todas as páginas
    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
    buffer.seek(0)
    return buffer.getvalue()

def carregar_areas_banco():
    """ Busca áreas no Banco de Dados e retorna um dicionário {nome: id}."""
    query = text("SELECT id_area, nome_area FROM informacoes_area ORDER BY nome_area ASC")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Transforma o DataFrame em um dicionário {'Nome da Área': id_area}
    # Zip junta as duas colunas: a primeira vira chave, a segunda vira valor
    return dict(zip(df['nome_area'], df['id_area']))

import re
import json

def limpar_dados_exibicao(dados):
    """Remove conteúdo de arquivos binários, mantendo metadados"""
    if not dados:
        return dados
    
    texto = str(dados)
    
    # Para cada ocorrência de valor string muito longo (base64)
    # Substitui por metadados
    import re
    
    # Encontra padrões como: "fluxo_bpmn": "iVBORw0KGgo..."
    # e substitui o valor longo por um resumo
    padrao = r'("(?:fluxo_bpmn|diagrama_bpmn|manual_etapa|arquivo_mapeamento|conteudo)":\s*)"([^"]{100,})"'
    texto = re.sub(padrao, r'\1"[ARQUIVO BINÁRIO - \2 bytes]"', texto)
    
    # Fallback: qualquer string com mais de 1000 caracteres
    if len(texto) > 5000:
        texto = texto[:5000] + '...[truncado]'
    
    return texto


def limpar_binario(dados):
    if not dados:
        return dados
    texto = str(dados)
    # Substitui fluxo_bpmn e outros campos binários
    # Padrão para BYTEA: "fluxo_bpmn": "\x89504e..."
    # Padrão para Base64: "fluxo_bpmn": "iVBORw0..."
    texto = re.sub(
        r'"fluxo_bpmn":\s*"[^"]*"',
        '"fluxo_bpmn": "[ARQUIVO BINARIO]"',
        texto
    )
    texto = re.sub(
        r'"diagrama_bpmn":\s*"[^"]*"',
        '"diagrama_bpmn": "[ARQUIVO BINARIO]"',
        texto
    )
    texto = re.sub(
        r'"manual_etapa":\s*"[^"]*"',
        '"manual_etapa": "[ARQUIVO BINARIO]"',
        texto
    )
    texto = re.sub(
        r'"arquivo_mapeamento":\s*"[^"]*"',
        '"arquivo_mapeamento": "[ARQUIVO BINARIO]"',
        texto
    )
    texto = re.sub(
        r'"conteudo":\s*"[^"]*"',
        '"conteudo": "[ARQUIVO BINARIO]"',
        texto
    )
    texto = re.sub(
        r'"arquivo_base64":\s*"[^"]*"',
        '"arquivo_base64": "[ARQUIVO BINARIO]"',
        texto
    )
    return texto

