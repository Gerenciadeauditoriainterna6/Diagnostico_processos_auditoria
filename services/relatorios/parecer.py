from utils.relatorios.capa import criar_pagina_capa
from utils.relatorios.contra_capa import contra_capa_relatorio
from utils.relatorios.validacao import criar_pagina_validacao
from utils.relatorios.informacoes import buscar_dados_gerencia_auditoria
from utils.relatorios.rodape import criar_rodape
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import io
import os
from database import engine
from sqlalchemy import text
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json

def gerar_relatorio_parecer_auditoria(area_id, area_nome, gestor, cargo, auditoria_id, processo_id,
                                     usuario_nome='Auditor', orientacao="RETRATO", incluir_abr=False, titulo_auditoria=None, incluir_checklists=True):
    """
    Gera relatório de Parecer da Auditoria para um processo específico
    Inclui análises do auditado (etapas) e análises do auditor (checklists)
    
    Parâmetros:
    - incluir_abr: Se True, inclui a seção ABR - Auditoria Baseada em Risco (apenas admin)
    - titulo_auditoria: Título da auditoria
    """
    
    
    buffer = io.BytesIO()
    TZ_BRASILIA = ZoneInfo('America/Sao_Paulo')
    
    # Definir orientação
    if orientacao.upper() == "PAISAGEM":
        pagesize = landscape(A4)
        topMargin = 1.5*cm
        bottomMargin = 2*cm
        leftMargin = 1.0*cm
        rightMargin = 1.0*cm
    else:
        pagesize = A4
        topMargin = 1.5*cm
        bottomMargin = 2*cm
        leftMargin = 1.2*cm
        rightMargin = 1.2*cm
    
    # ⭐ 1. PRIMEIRO: DEFINIR OS ESTILOS BÁSICOS
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontSize = 9
    normal_style.fontName = 'Helvetica'
    
    # ⭐ 2. DEPOIS: DEFINIR OS ESTILOS QUE DEPENDEM DO normal_style
    info_label_style = ParagraphStyle(
        'InfoLabel',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145')
    )
    
    info_valor_style = ParagraphStyle(
        'InfoValor',
        parent=normal_style,
        fontSize=9,
        textColor=colors.HexColor('#333333')
    )
    
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=20,
        textColor=colors.HexColor('#000000')
    )

    titulo_style0 = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=20,
        textColor=colors.HexColor('#0b5b99')
    )
    
    paragraph_style = ParagraphStyle(
        'CustomParagraph',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        spaceAfter=10,
        textColor=colors.HexColor('#0b5b99')
    )
    
    secao_style = ParagraphStyle(
        'SecaoStyle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=5,
        alignment=TA_CENTER,
        spaceBefore=15,
        textColor=colors.HexColor('#184145'),
        underline=True,
        underlineColor=colors.HexColor('#184145'),
        underlineWidth=1.5,  # ⭐ Mais fino para ficar elegante
        underlineOffset=2
    )
    
    subsecao_style = ParagraphStyle(
        'SubSecaoStyle',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=10,
        textColor=colors.HexColor('#0b5b99')
    )

    card_texto_style = ParagraphStyle(
        'CardTexto',
        parent=normal_style,
        fontSize=8,
        leading=10,
        leftIndent=0,
        alignment=TA_JUSTIFY
    )

    card_subtitulo_style = ParagraphStyle(
            'CardTexto',
            parent=normal_style,
            fontSize=12,
            leading=10,
            leftIndent=0,
            alignment=TA_JUSTIFY
        )

    card_texto_style_secao3 = ParagraphStyle(
        'CardTexto',
        parent=normal_style,
        fontSize=10,
        leading=10,
        leftIndent=10,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    card_subtitulo_style_center = ParagraphStyle(
            'CardTexto',
            parent=normal_style,
            fontSize=12,
            leading=10,
            leftIndent=10,
            alignment=TA_CENTER,
            spaceAfter=12
        )
    
    # ⭐ 3. ESTILOS PARA A TABELA DE CÉLULAS
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=normal_style,
        fontSize=9,
        leading=12,
        wordWrap='CJK'
    )
    
    cell_style_2 = ParagraphStyle(
        'CellStyle2',
        parent=normal_style,
        fontSize=9,
        leading=12,
        wordWrap='CJK'
    )

    # ===== PERGUNTAS DOS CHECKLISTS =====
    perguntas_governanca = [
        "1. O FLUXO DAS ETAPAS E SEUS OBJETIVOS SÃO DE FATO REALIZADOS?",
        "1.1 VERIFICANDO SE O QUE FOI FEITO ATÉ AGORA, SEGUE O PADRÃO RELATADO NO MAPEAMENTO?",
        "1.2 SOLICITE EXECUÇÕES FEITAS E COMPARE COM O MAPEAMENTO. ESTÁ CUMPRINDO O QUE DIZ FAZER?",
        "2. O FLUXO DAS ETAPAS E SEUS OBJETIVOS SÃO DE FATO REALIZADOS? FAZENDO SIMULAÇÕES, COMPARE COM O MAPEAMENTO. ESTÁ CUMPRINDO O QUE DIZ FAZER?",
        "3. EXISTEM PROCEDIMENTOS OPERACIONAIS PADRONIZADOS (POPS) DOCUMENTADOS E ATUALIZADOS PARA OS PROCESSOS-CHAVE DA ÁREA?",
        "4. OS PROPRIETÁRIOS DOS PROCESSOS E AS RESPONSABILIDADES POR RESULTADOS E RISCOS SÃO CLARAMENTE DEFINIDOS, CONHECIDOS E ACEITOS NA ÁREA?",
        "5. AS DECISÕES OPERACIONAIS SÃO TOMADAS NO NÍVEL HIERÁRQUICO CORRETO (EVITANDO ESCALONAMENTOS DESNECESSÁRIOS OU DECISÕES TOMADAS POR PESSOAS SEM ALÇADA)?",
        "6. A GESTÃO DA ÁREA REALIZA MONITORAMENTO CONTÍNUO DOS PROCESSOS?",
        "7. OS DADOS E RELATÓRIOS OPERACIONAIS REPORTADOS À GESTÃO SÃO CONFIÁVEIS, PRECISOS E UTILIZADOS PARA A TOMADA DE DECISÃO?",
        "8. OS INDICADORES DE DESEMPENHO (KPIS) DA ÁREA ESTÃO ALINHADOS COM OS OBJETIVOS ESTRATÉGICOS DA EMPRESA?",
        "9. OS PROBLEMAS OPERACIONAIS E AS NÃO CONFORMIDADES SÃO COMUNICADOS À GESTÃO SUPERIOR NO TEMPO ADEQUADO?",
        "10. A ÁREA REALIZA REVISÕES PERIÓDICAS DO SEU PRÓPRIO DESEMPENHO, IDENTIFICANDO E IMPLEMENTANDO MELHORIAS NOS PROCESSOS?",
        "11. OS RECURSOS (PESSOAS, TECNOLOGIA) ALOCADOS PARA A ÁREA SÃO SUFICIENTES E ADEQUADOS PARA O CUMPRIMENTO DOS OBJETIVOS OPERACIONAIS?",
        "12. A ÁREA DEMONSTRA COMPROMETIMENTO ÉTICO NO DIA A DIA, ADERINDO A POLÍTICAS E REPORTANDO DESVIOS SEM MEDO DE RETALIAÇÃO?",
        "13. O AUDITADO VALIDOU POR EMAIL SE EXISTE MAPEAMENTO DE PROCESSOS FEITO PELA ÁREA ESCRITÓRIO DE PROCESSOS?"
    ]

    perguntas_riscos = [
        "1. VALIDAR SE OS RISCOS E FATOR DE RISCOS ESTÃO COERENTES COM O OBJETIVO DA ETAPA.",
        "2. VERIFICAR SE OS RISCOS ESTÃO ATUALIZADOS E SENDO MONITORADOS PELO GESTOR DE PRIMEIRA LINHA.",
        "3. A ÁREA REALIZA MAPEAMENTO DE RISCOS DOS SEUS PROCESSOS OPERACIONAIS REGULARMENTE (EX: ANUALMENTE OU APÓS MUDANÇAS SIGNIFICATIVAS)?",
        "4. OS RISCOS CHAVE (EX: ERRO HUMANO, FALHA DE SISTEMA, FRAUDE) ESTÃO CLARAMENTE IDENTIFICADOS E DOCUMENTADOS PELA PRÓPRIA ÁREA?",
        "5. A ANÁLISE DE RISCOS INCLUI A AVALIAÇÃO DA PROBABILIDADE DE OCORRÊNCIA E DO IMPACTO FINANCEIRO/REPUTACIONAL/OPERACIONAL?",
        "6. EXISTE UM PLANO DE AÇÃO FORMALIZADO PARA MITIGAR OS RISCOS CLASSIFICADOS COMO ALTO OU CRÍTICO?",
        "7. OS CONTROLES INTERNOS DA ÁREA FORAM ESPECIFICAMENTE DESENHADOS PARA REDUZIR OS RISCOS IDENTIFICADOS (E NÃO APENAS HERDADOS DE OUTROS PROCESSOS)?",
        "8. A ÁREA POSSUI E TESTA PLANOS DE CONTINGÊNCIA/CONTINUIDADE DE NEGÓCIOS (PLANO B) PARA A NÃO INTERRUPÇÃO DE PROCESSOS QUE POSSUEM MAIORES RISCOS?",
        "9. A ÁREA MONITORA INDICADORES-CHAVE DE RISCO (KRIS) QUE SINALIZAM O AUMENTO DA EXPOSIÇÃO AOS RISCOS OPERACIONAIS?",
        "10. OS EVENTOS DE PERDA OU INCIDENTES OPERACIONAIS SÃO REGISTRADOS, ANALISADOS E UTILIZADOS PARA AJUSTAR A AVALIAÇÃO DE RISCO DA ÁREA?",
        "11. O GERENTE DA ÁREA (PRIMEIRA LINHA DE DEFESA) REVISA E CONFIRMA O STATUS DOS PRINCIPAIS RISCOS OPERACIONAIS DA SUA ÁREA PERIODICAMENTE?",
        "12. O AUDITADO VALIDOU POR EMAIL SE EXISTE MAPEAMENTO DE RISCO FEITO PELA ÁREA GERÊNCIA DE RISCOS E COMPLIANCE?"
    ]

    perguntas_controles = [
        "1. TESTAR SE A AÇÃO DOS CONTROLES DE FATO MITIGAM OS FATORES DE RISCOS INFORMADOS NA MATRIZ DE RISCOS. VERIFICANDO SE O QUE FOI FEITO ATÉ AGORA, SEGUE O PADRÃO RELATADO NO MAPEAMENTO? SOLICITE EXECUÇÕES FEITAS E COMPARE COM O MAPEAMENTO. ESTÁ CUMPRINDO O QUE DIZ FAZER?",
        "2. TESTAR SE A AÇÃO DOS CONTROLES DE FATO MITIGAM OS FATORES DE RISCOS INFORMADOS NA MATRIZ DE RISCOS. FAZENDO SIMULAÇÕES, COMPARANDO COM O MAPEAMENTO. ESTÁ CUMPRINDO O QUE DIZ FAZER?",
        "3. OS CONTROLES SÃO PREVENTIVOS (IMPEDEM O ERRO) SEMPRE QUE POSSÍVEL, AO INVÉS DE APENAS DETECTIVOS (IDENTIFICAM O ERRO APÓS A OCORRÊNCIA)?",
        "4. EXISTE SEGREGAÇÃO DE FUNÇÕES ADEQUADA DENTRO DOS PROCESSOS OPERACIONAIS (EX: QUEM APROVA NÃO É QUEM EXECUTA, QUEM REGISTRA NÃO É QUEM CONCILIA)?",
        "5. OS CONTROLES AUTOMÁTICOS (CONFIGURAÇÕES DO SISTEMA) SÃO REVISADOS E TESTADOS APÓS ATUALIZAÇÕES OU MUDANÇAS NO SISTEMA?",
        "6. O PASSO DO CONTROLE (EX: REVISÃO, APROVAÇÃO, CONCILIAÇÃO) É REALIZADO NA FREQUÊNCIA EXIGIDA E SEM EXCEÇÕES NÃO AUTORIZADAS?",
        "7. O RESPONSÁVEL PELO CONTROLE DEIXA EVIDÊNCIA CLARA (ASSINATURA, LOG DO SISTEMA, CAPTURA DE TELA) DE QUE O CONTROLE FOI EXECUTADO E REVISADO?",
        "8. OS CONTROLES-CHAVE SÃO EXECUTADOS POR PESSOAS COM O CONHECIMENTO E A AUTORIDADE NECESSÁRIOS PARA TAL?",
        "9. AS FALHAS OU EXCEÇÕES ENCONTRADAS NOS CONTROLES SÃO ESCALADAS IMEDIATAMENTE PARA TRATAMENTO E CORREÇÃO?",
        "10. A ÁREA RASTREIA E MONITORA AS AÇÕES CORRETIVAS IMPLEMENTADAS PARA REMEDIAR AS DEFICIÊNCIAS DE CONTROLE IDENTIFICADAS?",
        "11. AS RECONCILIAÇÕES (EX: CONTÁBEIS, ESTOQUES) SÃO REALIZADAS, E OS ITENS PENDENTES SÃO INVESTIGADOS E RESOLVIDOS PRONTAMENTE?",
        "12. O AUDITADO VALIDOU POR EMAIL SE EXISTE MAPEAMENTO DE CONTROLE FEITO PELA ÁREA GERÊNCIA DE RISCOS E COMPLIANCE?"
    ]
    
    story = []

    titulo_final = titulo_auditoria

    if titulo_final is None:
        # Se não veio como parâmetro, buscar do banco
        try:
            with engine.connect() as conn:
                query_titulo = text("SELECT titulo FROM auditorias WHERE id = :auditoria_id")
                result = conn.execute(query_titulo, {'auditoria_id': auditoria_id}).fetchone()
                if result:
                    titulo_final = result[0]
                else:
                    titulo_final = 'Auditoria'
        except Exception as e:
            print(f"⚠️ Erro ao buscar título: {e}")
            titulo_final = 'Auditoria'

    criar_pagina_capa(
        story=story,
        pagesize=pagesize,
        titulo_relatorio="PARECER DA AUDITORIA INTERNA",
        subtitulo_relatorio=f"{titulo_final}",
        area_nome=area_nome,
        data_emissao=datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    )
    
    # ===== CABEÇALHO COM LOGO CENTRALIZADO =====
    root_dir = Path(__file__).parent.parent.parent
    logo_auditoria_path = os.path.join(root_dir, "static", "assets", "logo_auditoria_circulo.png")

    header_data = []
    tem_logo = os.path.exists(logo_auditoria_path)

    # ===== TÍTULO =====
    story.append(Paragraph("PARECER DA AUDITORIA INTERNA", titulo_style))
    story.append(Spacer(1, 5))
    
    # ===== BUSCAR TODOS OS DADOS =====
    with engine.connect() as conn:
        # Buscar dados da auditoria
        query_auditoria = text("""
            SELECT codigo_auditoria, titulo, data_inicio, data_fim, status, trimestre, ano, fundamentos
            FROM auditorias WHERE id = :auditoria_id
        """)
        auditoria_info = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
        
        if not auditoria_info:
            raise Exception(f"Auditoria não encontrada")
        
        codigo_auditoria = auditoria_info[0]
        data_inicio = auditoria_info[2]
        data_fim = auditoria_info[3]
        status = auditoria_info[4]
        trimestre = auditoria_info[5]
        ano = auditoria_info[6]
        fundamentos = auditoria_info[7] if len(auditoria_info) > 7 and auditoria_info[7] else ''

        # Buscar processo específico
        query_processo = text("""
            SELECT p.id, p.codigo_processo, p.nome_processo
            FROM processos p
            WHERE p.id = :processo_id 
              AND p.auditoria_id = :auditoria_id 
              AND p.id_area = :area_id 
              AND p.status = 'Ativo'
        """)
        
        processo = conn.execute(query_processo, {
            "processo_id": processo_id,
            "area_id": area_id, 
            "auditoria_id": auditoria_id
        }).fetchone()
        
        if not processo:
            raise Exception(f"Processo {processo_id} não encontrado")
        
        proc_id = processo[0]
        proc_codigo = processo[1]
        proc_nome = processo[2]
        
        # ===== 1. BUSCAR ETAPAS E ANÁLISES DO AUDITADO =====
        query_etapas = text("""
            SELECT id, nome_etapa, codigo_etapa, descricao_etapa, objetivo_etapa
            FROM etapas_processo 
            WHERE processo_id = :processo_id 
            ORDER BY codigo_etapa
        """)
        etapas_raw = conn.execute(query_etapas, {"processo_id": proc_id}).fetchall()
        
        etapas = []
        for etapa in etapas_raw:
            etapa_id = etapa[0]
            etapa_nome = etapa[1]
            etapa_codigo = etapa[2] or ''
            etapa_desc = etapa[3] or ''
            etapa_obj = etapa[4] or ''
            
            # Buscar análises do auditado
            query_analises_auditado = text("""
                SELECT 
                    ac.id,
                    ac.categoria,
                    ac.analise_critica,
                    ac.sugestao_melhoria,
                    ac.sugestao_sera_implantada,
                    ac.plano_de_acao_implantado,
                    ac.data_execucao_plano_acao,
                    ac.necessidade_implantacao,
                    ac.ganho_previsto,
                    ac.evidencia_nome,
                    ac.evidencia_url
                FROM analises_criticas ac
                WHERE ac.etapa_id = :etapa_id AND ac.tipo = 'auditado'
                ORDER BY ac.categoria
            """)
            analises_auditado_raw = conn.execute(query_analises_auditado, {"etapa_id": etapa_id}).fetchall()
            
            analises_auditado_list = []
            for a in analises_auditado_raw:                
                
                analises_auditado_list.append({
                    'id': a._mapping['id'],
                    'categoria': a._mapping['categoria'],
                    'analise_critica': a._mapping['analise_critica'] or '',
                    'sugestao_melhoria': a._mapping['sugestao_melhoria'] or '',
                    'sugestao_sera_implantada': a._mapping['sugestao_sera_implantada'],
                    'plano_de_acao_implantado': a._mapping['plano_de_acao_implantado'],
                    'data_execucao_plano_acao': a._mapping['data_execucao_plano_acao'].strftime('%d/%m/%Y') if a._mapping['data_execucao_plano_acao'] else None,
                    'necessidade_implantacao': a._mapping['necessidade_implantacao'] or '',
                    'ganho_previsto': a._mapping['ganho_previsto'] or '',
                    'evidencia_nome': a._mapping['evidencia_nome'] or '',
                    'evidencia_url': a._mapping['evidencia_url'] or ''
                })

            # ⭐ NOVO: Buscar riscos da etapa com parecer
            query_riscos_etapa = text("""
                SELECT 
                    re.id,
                    re.nome_risco,
                    re.parecer_auditor
                FROM riscos_etapa re
                WHERE re.etapa_id = :etapa_id
                AND (re.ativo IS NULL OR re.ativo = true)
                ORDER BY re.id
            """)
            riscos_etapa_raw = conn.execute(query_riscos_etapa, {"etapa_id": etapa_id}).fetchall()

            for r in riscos_etapa_raw:
                risco_id = r._mapping['id']
                
                # ⭐ Buscar controles deste risco
                query_controles = text("""
                    SELECT 
                        ce.id,
                        ce.nome_controle
                    FROM controles_etapa ce
                    WHERE ce.risco_id = :risco_id
                    ORDER BY ce.id
                """)
                controles_raw = conn.execute(query_controles, {"risco_id": risco_id}).fetchall()
                
                controles_list = []
                for c in controles_raw:
                    controles_list.append({
                        'id': c._mapping['id'],
                        'nome_controle': c._mapping['nome_controle'] or ''
                    })

            
            riscos_etapa_list = []
            for r in riscos_etapa_raw:
                riscos_etapa_list.append({
                    'id': r._mapping['id'],
                    'nome_risco': r._mapping['nome_risco'] or '',
                    'parecer_auditor': r._mapping['parecer_auditor'] or '',
                    'controles': controles_list
                })
            
            etapas.append({
                'id': etapa_id,
                'nome': etapa_nome,
                'codigo': etapa_codigo,
                'descricao': etapa_desc,
                'objetivo': etapa_obj,
                'analises_auditado': analises_auditado_list,
                'riscos_etapa': riscos_etapa_list,
            })
        
        # ===== 2. BUSCAR ANÁLISES DO AUDITOR PARA O PROCESSO =====
        query_analises_auditor = text("""
            SELECT 
                ac.id,
                ac.analise_critica,
                ac.sugestao_melhoria,
                ac.sugestao_sera_implantada,
                ac.plano_de_acao_implantado,
                ac.data_execucao_plano_acao,
                ac.created_at,
                ac.necessidade_implantacao,
                ac.ganho_previsto,
                ac.evidencia_nome,
                ac.evidencia_url,
                ac.riscos_controles
            FROM analises_criticas ac
            WHERE ac.processo_id = :processo_id 
            AND ac.tipo = 'auditor'
            ORDER BY ac.created_at ASC
        """)

        # ⭐ EXECUTA A QUERY E POPULA A LISTA
        analises_auditor_raw = conn.execute(query_analises_auditor, {"processo_id": proc_id}).fetchall()

        analises_auditor_list = []
        for a in analises_auditor_raw:
            riscos_raw = a._mapping.get('riscos_controles')

            if isinstance(riscos_raw, list):
                riscos_controles = riscos_raw
            elif isinstance(riscos_raw, str) and riscos_raw:
                try:
                    riscos_controles = json.loads(riscos_raw)
                except:
                    riscos_controles = []
            else:
                riscos_controles = []

            analises_auditor_list.append({
                'id': a._mapping['id'],
                'analise_critica': a._mapping['analise_critica'] or '',
                'sugestao_melhoria': a._mapping['sugestao_melhoria'] or '',
                'sugestao_sera_implantada': a._mapping['sugestao_sera_implantada'],
                'plano_de_acao_implantado': a._mapping['plano_de_acao_implantado'],
                'data_execucao_plano_acao': a._mapping['data_execucao_plano_acao'].strftime('%d/%m/%Y') if a._mapping['data_execucao_plano_acao'] else None,
                'data_criacao': a._mapping['created_at'].strftime('%d/%m/%Y') if a._mapping['created_at'] else '',
                'necessidade_implantacao': a._mapping['necessidade_implantacao'] or '',
                'ganho_previsto': a._mapping['ganho_previsto'] or '',
                'evidencia_nome': a._mapping['evidencia_nome'] or '',
                'evidencia_url': a._mapping['evidencia_url'] or '',
                'riscos_controles': riscos_controles
            })
            
        # ===== 3. BUSCAR MATRIZES DE CHECKLIST (GOVERNANÇA, RISCOS, CONTROLES) =====
        checklist_tipos = ['governanca', 'riscos', 'controles']
        checklist_data = {}

        # ⭐ Mapeamento das perguntas por tipo
        perguntas_por_tipo = {
            'governanca': perguntas_governanca,
            'riscos': perguntas_riscos,
            'controles': perguntas_controles
        }

        for tipo in checklist_tipos:
            # ⭐ BUSCAR O CABEÇALHO DO CHECKLIST
            query_checklist_cabecalho = text("""
                SELECT 
                    id,
                    status,
                    observacoes_gerais
                FROM checklists
                WHERE processo_id = :processo_id 
                AND tipo = :tipo
                ORDER BY id DESC
                LIMIT 1
            """)
            
            checklist_cabecalho = conn.execute(query_checklist_cabecalho, {
                "processo_id": proc_id,
                "tipo": tipo
            }).fetchone()
            
            if checklist_cabecalho:
                checklist_id = checklist_cabecalho[0]
                checklist_status = checklist_cabecalho[1] or 'Não iniciado'
                observacoes = checklist_cabecalho[2] or ''
                
                # ⭐ BUSCAR AS RESPOSTAS NA ORDEM CORRETA
                # Para governança, as respostas podem ter ordens: "1", "1.1", "1.2", "2", "3", ...
                query_respostas = text("""
                    SELECT 
                        pergunta_ordem,
                        resposta,
                        comentario
                    FROM checklist_respostas
                    WHERE checklist_id = :checklist_id
                    ORDER BY 
                        -- Ordenar: primeiro o número principal, depois o subitem
                        CAST(SPLIT_PART(pergunta_ordem, '.', 1) AS INTEGER),
                        CASE 
                            WHEN SPLIT_PART(pergunta_ordem, '.', 2) = '' THEN 0
                            ELSE CAST(SPLIT_PART(pergunta_ordem, '.', 2) AS INTEGER)
                        END
                """)
                
                respostas_raw = conn.execute(query_respostas, {
                    "checklist_id": checklist_id
                }).fetchall()
                
                # ⭐ CONSTRUIR DICIONÁRIO DE RESPOSTAS POR ORDEM
                respostas_dict = {}
                for row in respostas_raw:
                    ordem = row[0]  # "1", "1.1", "1.2", "2", etc.
                    resposta = row[1] or ''
                    comentario = row[2] or ''
                    respostas_dict[ordem] = {
                        'resposta': resposta,
                        'comentario': comentario
                    }
                
                # ⭐ CRIAR LISTA DE RESPOSTAS NA MESMA ORDEM DAS PERGUNTAS
                perguntas = perguntas_por_tipo.get(tipo, [])
                respostas_ordenadas = []
                
                for pergunta in perguntas:
                    # Extrair o número da pergunta (se houver)
                    # Ex: "1.1 Verificando..." -> "1.1"
                    # Ex: "O fluxo das etapas..." -> "1" (primeira pergunta)
                    ordem = None
                    
                    # Verificar se a pergunta começa com número (ex: "1.1", "2", etc.)
                    import re
                    match = re.match(r'^(\d+(?:\.\d+)?)', pergunta)
                    if match:
                        ordem = match.group(1)  # "1", "1.1", etc.
                    else:
                        # Se não tem número, é uma pergunta principal sequencial
                        # Vamos contar quantas perguntas principais já foram processadas
                        pass
                    
                    # Buscar a resposta correspondente
                    if ordem and ordem in respostas_dict:
                        respostas_ordenadas.append(respostas_dict[ordem])
                    else:
                        # Se não encontrou por ordem, tentar encontrar pela posição
                        # Para perguntas sem numeração (ex: "O fluxo das etapas...")
                        # Elas correspondem à ordem "1", "2", "3"...
                        posicao = len([p for p in perguntas[:perguntas.index(pergunta)] if not re.match(r'^\d', p)]) + 1
                        if str(posicao) in respostas_dict:
                            respostas_ordenadas.append(respostas_dict[str(posicao)])
                        else:
                            # Se não encontrou, adiciona vazio
                            respostas_ordenadas.append({
                                'resposta': '',
                                'comentario': ''
                            })
                
                checklist_data[tipo] = {
                    'id': checklist_id,
                    'status': checklist_status,
                    'observacoes_gerais': observacoes,
                    'respostas': respostas_ordenadas
                }
            else:
                checklist_data[tipo] = None
       
    
    # ===== FUNÇÃO PARA DESENHAR TARJA =====
    def cabecalho_com_tarja(canvas, doc):
        canvas.saveState()
        
        # Limpa espaços e quebras de linha
        status_limpo = status.strip() if status else ''
        
        status_config = {
            'INCONCLUSIVA': {'cor': (0.86, 0.08, 0.24), 'texto': 'AUDITORIA INCONCLUSIVA'},
            'FOLLOW-UP': {'cor': (0.99, 0.49, 0.08), 'texto': 'AUDITORIA EM FOLLOW-UP'},
            'EFICÁCIA VALIDADA': {'cor': (0.16, 0.63, 0.27), 'texto': 'AUDITORIA COM EFICÁCIA VALIDADA'},
            'EM EXECUÇÃO': {'cor': (0.09, 0.63, 0.76), 'texto': 'AUDITORIA EM EXECUÇÃO'}
        }
        
        # Usa o status limpo para buscar a configuração; se não existir, usa uma tarja cinza genérica
        config = status_config.get(status_limpo, {
            'cor': (0.5, 0.5, 0.5),
            'texto': f'AUDITORIA - {status_limpo.upper()}'
        })
        
        canvas.setFillColorRGB(config['cor'][0], config['cor'][1], config['cor'][2], 1)
        canvas.rect(0, pagesize[1] - 1.2*cm, pagesize[0], 0.8*cm, fill=1, stroke=0)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColorRGB(1, 1, 1)
        canvas.drawCentredString(pagesize[0] / 2, pagesize[1] - 0.9*cm, config['texto'])
        
        canvas.restoreState()
    
    status_colors = {
        'EM EXECUÇÃO': colors.HexColor('#17a2b8'),      
        'EFICÁCIA VALIDADA': colors.HexColor('#28a745'), 
        'FOLLOW-UP': colors.HexColor("#fded14"),                  
        'INCONCLUSIVA': colors.HexColor("#ff0000")       
    }
    
    status_color = status_colors.get(status, colors.black)
    status_text = f'<font color="#{status_color.hexval()[2:]}"><b>{status}</b></font>'
    
    # ===== VERIFICAR ATRASO DA AUDITORIA =====
    hoje = datetime.now(TZ_BRASILIA).date()
    status_atraso_html = ""
    
    if data_fim and data_fim < hoje:
        status_atraso_html = '<font color="#dc3545"><b> - Em Atraso</b></font>'
    
    # Estilo para células da tabela
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=normal_style,
        fontSize=9,
        leading=12,
        wordWrap='CJK'
    )
    
    cell_style_2 = ParagraphStyle(
        'CellStyle2',
        parent=normal_style,
        fontSize=9,
        leading=12,
        wordWrap='CJK'
    )
    
    # ===== INFORMAÇÕES DO RELATÓRIO =====
    # ⭐ Usar a função padronizada
    contra_capa_relatorio(
        story=story,
        styles=styles,
        normal_style=normal_style,
        pagesize=pagesize,
        leftMargin=2*cm,
        rightMargin=2*cm,
        auditoria_id=auditoria_id,
        processo_id=processo_id,
        area_id=area_id,
        area_nome=area_nome,
        gestor=gestor,
        cargo=cargo,
        titulo_auditoria=titulo_final
    )
    
    # ===== FUNÇÃO AUXILIAR PARA EXIBIR PLANO DE AÇÃO =====
    def adicionar_plano_acao(analise):
        dados_plano = []
        if analise.get('responsavel_implantacao'):
            dados_plano.append([Paragraph("<b>Responsável:</b>", normal_style), Paragraph(analise['responsavel_implantacao'], normal_style)])
        if analise.get('data_inicio_prevista'):
            dados_plano.append([Paragraph("<b>Início Previsto:</b>", normal_style), Paragraph(analise['data_inicio_prevista'], normal_style)])
        if analise.get('data_conclusao_prevista'):
            dados_plano.append([Paragraph("<b>Conclusão Prevista:</b>", normal_style), Paragraph(analise['data_conclusao_prevista'], normal_style)])
        
        if dados_plano:
            story.append(Paragraph("<b>Plano de Ação:</b>", normal_style))
            if analise.get('plano_acao'):
                story.append(Paragraph(analise['plano_acao'], normal_style))
                story.append(Spacer(1, 3))
            
            tabela_plano = Table(dados_plano, colWidths=[4*cm, 11*cm])
            tabela_plano.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.91, 0.96, 0.91, alpha=0.60)),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(tabela_plano)
    
    # ===== FUNÇÃO AUXILIAR PARA EXIBIR ANÁLISE COMPLETA =====
    def adicionar_analise_auditado(analise, titulo):
        
        # Análise Crítica
        if analise.get('analise_critica'):
            story.append(Paragraph("<b>PONTO DE AUDITORIA</b>", card_texto_style))
            story.append(Paragraph(analise['analise_critica'] or '', normal_style))  # ⭐ Adicionar or ''
            story.append(Spacer(1, 10))
        
        # Sugestão de Melhoria
        if analise.get('sugestao_melhoria'):
            story.append(Paragraph("<b>SUGESTÃO DE MELHORIA</b>", card_texto_style))
            story.append(Paragraph(analise['sugestao_melhoria'] or '', normal_style))  # ⭐ Adicionar or ''
            story.append(Spacer(1, 10))

        # Necessidade para implantacao
        if analise.get('necessidade_implantacao'):
            story.append(Paragraph("<b>NECESSIDADE PARA IMPLANTAÇÃO</b>", card_texto_style))
            story.append(Paragraph(analise['necessidade_implantacao'] or '', normal_style))
            story.append(Spacer(1, 10))

        # Ganho Previso
        if analise.get('ganho_previsto'):
            story.append(Paragraph("<b>GANHO PREVISTO</b>", card_texto_style))
            story.append(Paragraph(analise['ganho_previsto'] or '', normal_style))
            story.append(Spacer(1, 10))

        # Decisão sobre implantação
        if analise.get('sugestao_sera_implantada') == True:
            story.append(Paragraph("<b><font color=#00ff60>*ESTA SUGESTÃO DE MELHORIA SERÁ IMPLANTADA</font></b>", normal_style))
            story.append(Spacer(1, 3))
            
            # Plano de Ação
            adicionar_plano_acao(analise)
            story.append(Spacer(1, 5))
                
        elif analise.get('sugestao_sera_implantada') == False:
            story.append(Paragraph("<b><font color=#ff0000>*ESTA SUGESTÃO DE MELHORIA NÃO SERÁ IMPLANTADA</font></b>", normal_style))
        else:
            pass
        
        story.append(Spacer(1, 8))

    
    # ===== FUNÇÃO AUXILIAR PARA EXIBIR ANÁLISE COMPLETA =====
    def adicionar_analise(analise, titulo):
        
        # Análise Crítica
        if analise.get('analise_critica'):
            story.append(Paragraph("<b>PONTO DE AUDITORIA</b>", card_texto_style_secao3))
            story.append(Paragraph(analise['analise_critica'] or '', normal_style))  # ⭐ Adicionar or ''
            story.append(Spacer(1, 10))
        
        # Sugestão de Melhoria
        if analise.get('sugestao_melhoria'):
            story.append(Paragraph("<b>SUGESTÃO DE MELHORIA</b>", card_texto_style_secao3))
            story.append(Paragraph(analise['sugestao_melhoria'] or '', normal_style))  # ⭐ Adicionar or ''
            story.append(Spacer(1, 10))

        # Necessidade para implantacao
        if analise.get('necessidade_implantacao'):
            story.append(Paragraph("<b>NECESSIDADE PARA IMPLANTAÇÃO</b>", card_texto_style_secao3))
            story.append(Paragraph(analise['necessidade_implantacao'] or '', normal_style))
            story.append(Spacer(1, 10))

        # Ganho Previso
        if analise.get('ganho_previsto'):
            story.append(Paragraph("<b>GANHO PREVISTO</b>", card_texto_style_secao3))
            story.append(Paragraph(analise['ganho_previsto'] or '', normal_style))
            story.append(Spacer(1, 10))

        # Decisão sobre implantação
        if analise.get('sugestao_sera_implantada') == True:
            story.append(Paragraph("<b><font color=#00ff60>*ESTA SUGESTÃO DE MELHORIA SERÁ IMPLANTADA</font></b></b>", normal_style))
            story.append(Spacer(1, 3))
            
            # Plano de Ação
            adicionar_plano_acao(analise)
            story.append(Spacer(1, 5))
            
        elif analise.get('sugestao_sera_implantada') == False:
            story.append(Paragraph("<b><font color=#ff0000>*ESTA SUGESTÃO DE MELHORIA NÃO SERÁ IMPLANTADA</font></b>", normal_style))
        else:
            pass
        
        # ⭐ NOVO: Riscos e Controles
        riscos_controles = analise.get('riscos_controles', [])

        if riscos_controles:
            story.append(Paragraph("<b>3.1 RISCOS IDENTIFICADOS E CONTROLES SUGERIDOS</b>", secao_style))
            
            for risco in riscos_controles:
                # Pega o nome do risco (pode ser dict ou string)
                if isinstance(risco, dict):
                    nome_risco = risco.get('risco', '')
                    controles = risco.get('controles', [])
                else:
                    nome_risco = str(risco)
                    controles = []
                
                story.append(Paragraph(f"<b>RISCO:</b> {nome_risco}", normal_style))
                
                if controles:
                    for controle in controles:
                        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>CONTROLE:</b> {controle}", normal_style))
                else:
                    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<i>Nenhum controle sugerido ou informado</i>", normal_style))
                
                story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("<b>RISCOS IDENTIFICADOS E CONTROLES SUGERIDOS</b>", card_texto_style_secao3))
            story.append(Paragraph("<i>Nenhum risco identificado ou não informado. Nenhum controle sugerido ou informado.</i>", normal_style))

        story.append(Spacer(1, 10))
    
    # ===== FUNÇÃO PARA EXIBIR CHECKLIST (FORMATO LISTA) =====
    def adicionar_checklist_simples(checklist, titulo, perguntas):
        """Adiciona as respostas do checklist ao relatório em formato de lista"""
        
        # ⭐ DEFINIR CORES POR TIPO DE MATRIZ
        cores_por_titulo = {
            'MATRIZ DE GOVERNANÇA': '#0b5b99',
            'MATRIZ DE RISCOS': '#fd6a14',
            'MATRIZ DE CONTROLES': '#17a2b8'
        }
        
        # ⭐ Buscar a cor e ícone correspondentes (case-insensitive)
        cor_titulo = '#184145'  # cor padrão
        
        for chave, cor in cores_por_titulo.items():
            if chave.upper() in titulo.upper():
                cor_titulo = cor
                break
        
        # ⭐ ESTILO DO TÍTULO COM A COR CORRESPONDENTE
        titulo_checklist_style = ParagraphStyle(
            'TituloChecklistStyle',
            parent=normal_style,
            fontSize=11,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(cor_titulo),
            spaceAfter=8,
            spaceBefore=8,
            alignment=TA_CENTER
        )
        
        # ⭐ TÍTULO COM ÍCONE E COR
        story.append(Paragraph(
            f"{titulo}",
            titulo_checklist_style
        ))
        story.append(Spacer(1, 3))
        
        # ⭐ LINHA DIVISÓRIA COM A COR DO TÍTULO
        story.append(HRFlowable(
            width="100%", 
            thickness=1.5, 
            color=colors.HexColor(cor_titulo), 
            spaceBefore=3, 
            spaceAfter=8
        ))
        
        if not checklist:
            story.append(Paragraph(
                f"<i>Nenhuma resposta encontrada para {titulo}.</i>", 
                normal_style
            ))
            story.append(Spacer(1, 10))
            return
        
        # Status
        status_text = checklist.get('status', 'Não iniciado')
        status_color = {
            'Não iniciado': '#6c757d',
            'Em andamento': '#17a2b8',
            'Concluído': '#28a745'
        }.get(status_text, '#000000')
        
        story.append(Paragraph(
            f"<b>Status:</b> <font color='{status_color}'>{status_text}</font>", 
            normal_style
        ))
        story.append(Spacer(1, 8))
        
        # Observações gerais (se houver)
        if checklist.get('observacoes_gerais'):
            story.append(Paragraph("<b>Observações Gerais:</b>", normal_style))
            story.append(Paragraph(checklist['observacoes_gerais'], normal_style))
            story.append(Spacer(1, 10))
        
        # ⭐ EXIBIR PERGUNTAS E RESPOSTAS EM LISTA
        respostas = checklist.get('respostas', [])
        
        # Criar estilos com diferentes níveis de indentação
        pergunta_style = ParagraphStyle(
            'PerguntaStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=5,
            spaceAfter=3,
            fontName='Helvetica-Bold',
            alignment=TA_JUSTIFY
        )
        
        subpergunta_style = ParagraphStyle(
            'SubPerguntaStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=20,
            spaceAfter=3,
            alignment=TA_JUSTIFY
        )
        
        resposta_style = ParagraphStyle(
            'RespostaStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=15,
            spaceAfter=3,
            textColor=colors.HexColor(cor_titulo),  # ⭐ USA A COR DO TÍTULO
            alignment=TA_JUSTIFY
        )
        
        subresposta_style = ParagraphStyle(
            'SubRespostaStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=35,
            spaceAfter=3,
            textColor=colors.HexColor(cor_titulo),  # ⭐ USA A COR DO TÍTULO
            alignment=TA_JUSTIFY
        )
        
        comentario_style = ParagraphStyle(
            'ComentarioStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=15,
            spaceAfter=8,
            textColor=colors.HexColor("#6c757d"),
            alignment=TA_JUSTIFY
        )
        
        subcomentario_style = ParagraphStyle(
            'SubComentarioStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=35,
            spaceAfter=8,
            textColor=colors.HexColor('#6c757d'),
            alignment=TA_JUSTIFY
        )
        
        # ⭐ PERCORRER TODAS AS PERGUNTAS
        import re
        
        for idx, pergunta_texto in enumerate(perguntas):
            if idx >= len(respostas):
                break
                
            resposta = respostas[idx]
            resposta_texto = resposta.get('resposta', '')
            comentario_texto = resposta.get('comentario', '')
            
            # Determinar se é subpergunta (começa com número e ponto: "1.1", "1.2", etc.)
            is_subpergunta = bool(re.match(r'^\d+\.\d+', pergunta_texto))
            
            # ⭐ Separador entre perguntas principais
            if not is_subpergunta and idx > 0:
                story.append(Spacer(1, 5))
                story.append(HRFlowable(
                    width="100%", 
                    thickness=0.5, 
                    color=colors.HexColor("#E0E0E0"), 
                    spaceBefore=5, 
                    spaceAfter=5
                ))
                story.append(Spacer(1, 5))
            
            if is_subpergunta:
                # ⭐ SUBPERGUNTA
                story.append(Paragraph(
                    pergunta_texto,
                    subpergunta_style
                ))
                
                if resposta_texto:
                    story.append(Paragraph(
                        f"<b>RESPOSTA:</b> {resposta_texto}",
                        subresposta_style
                    ))
                else:
                    story.append(Paragraph(
                        "<i>SEM RESPOSTA</i>",
                        subresposta_style
                    ))
                
                if comentario_texto:
                    story.append(Paragraph(
                        f"<b>COMENTÁRIO:</b> {comentario_texto}",
                        subcomentario_style
                    ))
                
                story.append(Spacer(1, 5))
            else:
                # ⭐ PERGUNTA PRINCIPAL
                story.append(Paragraph(
                    pergunta_texto,
                    pergunta_style
                ))
                
                if resposta_texto:
                    story.append(Paragraph(
                        f"<b>RESPOSTA:</b> {resposta_texto}",
                        resposta_style
                    ))
                else:
                    story.append(Paragraph(
                        "<i>SEM RESPOSTA</i>",
                        resposta_style
                    ))
                
                if comentario_texto:
                    story.append(Paragraph(
                        f"<b>COMENTÁRIO:</b> {comentario_texto}",
                        comentario_style
                    ))
        
        story.append(Spacer(1, 10))
    
    # ===== SEÇÃO DE FUNDAMENTOS DA AUDITORIA (CONDICIONAL) =====
    # ⭐ MODIFICADO PARA SER CONDICIONAL
    if incluir_abr and fundamentos and len(fundamentos) > 0:
        story.append(Paragraph("ABR - AUDITORIA BASEADA EM RISCO", secao_style))
        story.append(Spacer(1, 5))
        
        fundamentos_style = ParagraphStyle(
            'FundamentosStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            spaceAfter=8,
            leftIndent=10,
            alignment=TA_JUSTIFY
        )
        
        for idx, fund in enumerate(fundamentos, 1):
            titulo = fund.get('titulo', '')
            pontos = fund.get('pontos', [])
            
            if titulo:
                story.append(Paragraph(f"<b>{idx}. {titulo}</b>", fundamentos_style))
                story.append(Spacer(1, 3))
            
            for ponto in pontos:
                if ponto and ponto.strip():
                    story.append(Paragraph(f"• {ponto}", fundamentos_style))
                    story.append(Spacer(1, 2))
            
            story.append(Spacer(1, 5))
        
        story.append(Spacer(1, 10))
    
    # ===== SEÇÃO 1: ANÁLISES DO AUDITADO (POR ETAPA) =====
    story.append(Paragraph("1. ANÁLISES E PARECER DO AUDITADO", secao_style))
    story.append(Paragraph("Análises realizadas pelo auditado durante o detalhamento das etapas", normal_style))
    story.append(Spacer(1, 10))
    
    if not etapas:
        story.append(Paragraph("<i>Nenhuma etapa cadastrada para este processo.</i>", normal_style))
    else:
        for etapa_idx, etapa in enumerate(etapas):
            story.append(Paragraph(f"Etapa {etapa['codigo']}: {etapa['nome']}", subsecao_style))
            story.append(Spacer(1, 3))
            
            
            if etapa['analises_auditado']:
                num_analises = len(etapa['analises_auditado'])
                for i, a in enumerate(etapa['analises_auditado']):
                    nome_categoria = {
                        'governanca': 'Governança',
                        'riscos': 'Riscos',
                        'controles': 'Controles'
                    }.get(a['categoria'], a['categoria'].upper())
                    
                    adicionar_analise_auditado(a, f"{nome_categoria}")
                    
                    # ⭐ ADICIONAR SEPARADOR ENTRE ANÁLISES DO AUDITADO (exceto após a última)
                    if i < num_analises - 1:
                        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC"), spaceBefore=5, spaceAfter=5))
                       
            else:
                story.append(Paragraph("<i>Nenhuma análise cadastrada para esta etapa.</i>", normal_style))

            # ⭐ NOVO: Riscos da Etapa com Parecer
            if etapa.get('riscos_etapa'):
                story.append(Spacer(1, 2))
                story.append(Paragraph("<b>RISCOS MAPEADOS E PARECER DO AUDITOR</b>", card_subtitulo_style))
                story.append(Spacer(1, 20))
                
                for risco in etapa['riscos_etapa']:
                    story.append(Paragraph(f"<b>RISCO:</b> {risco['nome_risco']}", normal_style))

                    # ⭐ MOSTRAR CONTROLES
                    if risco.get('controles'):
                        for controle in risco['controles']:
                            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>CONTROLE:</b> {controle['nome_controle']}", normal_style))
                    else:
                        story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<i>Nenhum controle informado</i>", normal_style))
                    
                    if risco['parecer_auditor']:
                        story.append(Spacer(1, 6))
                        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>PARECER:</b> {risco['parecer_auditor']}", normal_style))
                        story.append(Spacer(1, 6))
                    else:
                        story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i>Sem parecer do auditor</i>", normal_style))
                    
                    story.append(Spacer(1, 5))
            else:
                story.append(Paragraph("<i>Nenhum risco mapeado para esta etapa.</i>", normal_style))

            # ⭐ Separador entre etapas (com linha cinza)
            if etapa_idx < len(etapas) - 1:
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC"), spaceBefore=5, spaceAfter=5))

    if incluir_checklists:
        # ===== SEÇÃO 2: CHECKLISTS =====
        story.append(PageBreak())
        story.append(Paragraph("2. MATRIZES DE EFICÁCIA", secao_style))
        story.append(Spacer(1, 2))

        # ===== SEÇÃO 2.1: MATRIZES DE CHECKLIST =====
        adicionar_checklist_simples(
            checklist_data.get('governanca'), 
            "MATRIZ DE GOVERNANÇA - RESPOSTAS",
            perguntas_governanca
        )
        story.append(PageBreak())
        
        adicionar_checklist_simples(
            checklist_data.get('riscos'), 
            "MATRIZ DE RISCOS - RESPOSTAS",
            perguntas_riscos
        )
        story.append(PageBreak())
        
        
        adicionar_checklist_simples(
            checklist_data.get('controles'), 
            "MATRIZ DE CONTROLES - RESPOSTAS",
            perguntas_controles
        )
    

    # ====== SEÇÃO 3 ANÁLISES DO AUDITOR ======

    story.append(PageBreak())
    story.append(Paragraph("3. ANÁLISES E PARECER DO AUDITOR", secao_style))
    story.append(Spacer(1, 10)) 

    if not analises_auditor_list:
        story.append(Paragraph("<i>Nenhuma análise do auditor cadastrada para este processo.</i>", normal_style))
    else:
        for idx, analise in enumerate(analises_auditor_list, 1):
            adicionar_analise(analise, f"2.{idx} Análise do Auditor - {analise.get('data_criacao', '')}")
            
            # ⭐ Separador entre análises do auditor (com linha cinza e mais espaçamento)
            if idx < len(analises_auditor_list):
                story.append(Spacer(1, 10))   # mantenha um espaço extra se desejar
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC"), spaceBefore=0, spaceAfter=0))
                story.append(Spacer(1, 10))    
    
    styles.add(ParagraphStyle('titulo', parent=titulo_style))

    
    # ===== ASSINATURAS =====
    criar_pagina_validacao(
        story=story,
        gestor=gestor,
        styles=styles,                # já obtido via getSampleStyleSheet()
        normal_style=normal_style,
        auditoria_id=auditoria_id,
        tipo_relatorio='parecer',     # ou o nome que você usa para o parecer
        entrevistado=None             # ajuste se houver um entrevistado específico
    )

    # ============================================================
    # ⭐ RODAPÉ COM TOTAL DE PÁGINAS (USANDO PyPDF2)
    # ============================================================
    from reportlab.lib.utils import ImageReader
    from PIL import Image as PILImage
    import copy
    from PyPDF2 import PdfReader

    # ⭐ BUSCAR DADOS DA GAI PARA O RODAPÉ
    dados_gai = buscar_dados_gerencia_auditoria()
    email_gai = dados_gai['email']
    telefone_gai = dados_gai['telefone']
    
    # Função para desenhar as logos
    def desenhar_logos_parecer(canvas):
        root_dir = Path(__file__).parent.parent.parent
        logo1_path = os.path.join(root_dir, "static", "assets", "logo_fusve.png")
        logo2_path = os.path.join(root_dir, "static", "assets", "logo_auditoria-removebg-preview.png")
        logo3_path = os.path.join(root_dir, "static", "assets", "logo_iia.png")
        
        y_logo = 0.8 * cm
        altura_max_logo = 5 * cm
        
        def desenhar_png(caminho, x, y, largura_max, altura_max):
            if not os.path.exists(caminho):
                return False
            try:
                pil_img = PILImage.open(caminho)
                if pil_img.mode != 'RGBA':
                    pil_img = pil_img.convert('RGBA')
                img_width, img_height = pil_img.size
                proporcao = img_width / img_height
                largura = min(largura_max, 5*cm)
                altura = largura / proporcao
                if altura > altura_max:
                    altura = altura_max
                    largura = altura * proporcao
                buffer_temp = io.BytesIO()
                pil_img.save(buffer_temp, format='PNG')
                buffer_temp.seek(0)
                img = ImageReader(buffer_temp)
                canvas.drawImage(img, x - largura/2, y - altura/2, width=largura, height=altura, mask='auto', preserveAspectRatio=True)
                return True
            except Exception as e:
                print(f"Erro ao desenhar logo: {e}")
                return False
        
        espacamento = pagesize[0] / 4
        x1 = espacamento
        x2 = pagesize[0] / 2
        x3 = pagesize[0] - espacamento
        largura_max = 2.5 * cm
        
        desenhar_png(logo1_path, x2, y_logo, largura_max, altura_max_logo)
        desenhar_png(logo2_path, x1, y_logo, 3.5 * cm, 3.5 * cm)
        desenhar_png(logo3_path, x3, y_logo, 3 * cm, 3 * cm)

    # FAZER UMA CÓPIA DO STORY PARA A PRIMEIRA PASSADA
    story_copy = copy.deepcopy(story)
    
    # PRIMEIRA PASSADA: GERAR PDF TEMPORÁRIO PARA CONTAR PÁGINAS
    buffer_temp = io.BytesIO()
    doc_temp = SimpleDocTemplate(buffer_temp, pagesize=pagesize,
                                topMargin=1.5*cm, bottomMargin=2*cm,
                                leftMargin=2*cm, rightMargin=2*cm)
    
    # Rodapé temporário para contagem
    def rodape_contador(canvas, doc):
        canvas.saveState()
        altura_rodape = 1.8 * cm
        y_fundo = 0
        canvas.setFillColor(colors.HexColor('#F0F0F0'))
        canvas.rect(0, y_fundo, pagesize[0], altura_rodape, fill=1, stroke=0)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawCentredString(pagesize[0]/2, 2*cm, f"Parecer do Processo {proc_codigo} - Página {doc.page}")
        desenhar_logos_parecer(canvas)
        canvas.restoreState()
    
    # Tarja temporária (vazia para não interferir na contagem)
    def tarja_temp(canvas, doc):
        pass
    
    doc_temp.build(story_copy, 
                   onFirstPage=lambda c, d: [tarja_temp(c, d), rodape_contador(c, d)],
                   onLaterPages=lambda c, d: [tarja_temp(c, d), rodape_contador(c, d)])
    
    # ⭐ CONTAR AS PÁGINAS USANDO PyPDF2
    buffer_temp.seek(0)
    pdf_reader = PdfReader(buffer_temp)
    total_paginas = len(pdf_reader.pages)
    
    # ⭐ SEGUNDA PASSADA: GERAR O PDF FINAL COM O TOTAL

    # ===== BUSCAR DADOS DA GERÊNCIA DE AUDITORIA INTERNA (FIXOS) =====
    dados_gai = buscar_dados_gerencia_auditoria()
    email_gai = dados_gai['email']
    telefone_gai = dados_gai['telefone']
    root_dir = Path(__file__).parent.parent.parent
    
    # ============================================================
    # ⭐ RODAPÉ USANDO A FUNÇÃO PADRONIZADA
    # ============================================================
    def rodape_parecer(canvas, doc, total_paginas):
        """Rodapé específico do relatório Parecer"""
        titulo_rodape = f"Parecer do Processo {proc_codigo} - {area_nome[:50]}"
        criar_rodape(canvas, doc, pagesize, total_paginas, titulo_rodape,
                     root_dir=root_dir,
                     email_auditoria=email_gai,
                     telefone_auditoria=telefone_gai)
    
    # ============================================================
    # ⭐ FUNÇÃO PARA CONTAR PÁGINAS E GERAR O PDF
    # ============================================================
    
    # ⭐ 1. FAZER UMA CÓPIA DO STORY PARA A PRIMEIRA PASSADA
    story_copy = copy.deepcopy(story)
    
    # ⭐ 2. PRIMEIRA PASSADA: GERAR PDF TEMPORÁRIO PARA CONTAR PÁGINAS
    buffer_temp = io.BytesIO()
    doc_temp = SimpleDocTemplate(buffer_temp, pagesize=pagesize,
                                topMargin=topMargin, bottomMargin=bottomMargin,
                                leftMargin=leftMargin, rightMargin=rightMargin)
    
    def rodape_temp(canvas, doc):
        # ⭐ NÃO DESENHA RODAPÉ NA CAPA (página 1)
        if doc.page == 1:
            return
        # ⭐ PARA AS DEMAIS PÁGINAS, USA O RODAPÉ NORMAL (SEM CONTAGEM)
        criar_rodape(canvas, doc, pagesize, 0, f"Parecer do Processo {proc_codigo} - {area_nome[:50]}",
                     root_dir=root_dir,
                     email_auditoria=email_gai,
                     telefone_auditoria=telefone_gai)
    
    def cabecalho_temp(canvas, doc):
        if doc.page > 1:  # ⭐ PULA O CABEÇALHO NA CAPA
            cabecalho_com_tarja(canvas, doc)
    
    doc_temp.build(story_copy, 
                   onFirstPage=lambda c, d: [cabecalho_temp(c, d), rodape_temp(c, d)],
                   onLaterPages=lambda c, d: [cabecalho_temp(c, d), rodape_temp(c, d)])
    
    # ⭐ 3. CONTAR AS PÁGINAS
    buffer_temp.seek(0)
    pdf_reader = PdfReader(buffer_temp)
    total_paginas = len(pdf_reader.pages)
    
    # ⭐ 4. SEGUNDA PASSADA: GERAR O PDF FINAL COM O TOTAL
    doc_final = SimpleDocTemplate(buffer, pagesize=pagesize,
                                 topMargin=topMargin, bottomMargin=bottomMargin,
                                 leftMargin=leftMargin, rightMargin=rightMargin)
    
    def rodape_final(canvas, doc):
        if doc.page == 1:  # ⭐ PULA A CAPA
            return
        # ⭐ PASSA O TOTAL DE PÁGINAS PARA O RODAPÉ
        rodape_parecer(canvas, doc, total_paginas)
    
    def cabecalho_final(canvas, doc):
        if doc.page > 1:  # ⭐ PULA O CABEÇALHO NA CAPA
            cabecalho_com_tarja(canvas, doc)
    
    doc_final.build(story, 
                    onFirstPage=lambda c, d: [cabecalho_final(c, d), rodape_final(c, d)],
                    onLaterPages=lambda c, d: [cabecalho_final(c, d), rodape_final(c, d)])
    
    buffer.seek(0)
    return buffer.getvalue()