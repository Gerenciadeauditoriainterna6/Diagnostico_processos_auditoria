"""
Módulo de geração de relatórios
sdfadsfasd
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from database import engine
from logic import (listar_areas, listar_processos_da_auditoria_com_riscos,
    listar_riscos_do_processo, listar_etapas_do_processo,
    listar_controles_da_etapa, gerar_pdf_em_memoria, get_estilo_risco
)
import time as time_module

def buscar_processos_pendentes_relatorio():
    """Busca procesos que ainda não tiveram relatório gerencial gerado"""
    query = text("""
        SELECT
            p.id,
            p.codigo_processo,
            p.nome_processo,
            p.objetivo,
            p.status,
            ia.nome_area,
            CASE
                WHEN p.relatorio_gerencial_gerado IS NULL OR p.relatorio_gerencial_gerado = FALSE
                THEN 'Pendente'
                ELSE 'Gerado'
            END as status_relatorio
            FROM processos p
            JOIN informacoes_area ia ON p.id_area = ia.id_area
            WHERE p.status = 'Ativo'
            AND (p.relatorio_gerencial_gerado IS NULL OR p.relatorio_gerencial_gerado = FALSE)
            ORDER BY ia.nome_area, p.codigo_processo
        """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def buscar_processos_por_area(area_id=None):
    """Busca todos os processos de uma área com seus riscos"""
    if area_id:
        query = text("""
            SELECT 
                p.id,
                p.codigo_processo,
                p.nome_processo,
                p.objetivo,
                p.descricao,
                p.etapa_ini,
                p.etapa_fim,
                p.produto,
                p.status,
                ia.nome_area,
                ia.gestor,
                STRING_AGG(DISTINCT r.nome_risco, '; ') as riscos,
                STRING_AGG(DISTINCT r.fator_risco, '; ') as fatores_risco,
                MAX(r.score_risco) as maior_risco
            FROM processos p
            JOIN informacoes_area ia ON p.id_area = ia.id_area
            LEFT JOIN riscos r ON p.id = r.processo_id
            WHERE p.id_area = :area_id AND p.status = 'Ativo'
            GROUP BY p.id, ia.nome_area, ia.gestor
            ORDER BY p.codigo_processo
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"area_id": area_id})
    else:
        query = text("""
            SELECT 
                p.id,
                p.codigo_processo,
                p.nome_processo,
                p.objetivo,
                p.descricao,
                p.etapa_ini,
                p.etapa_fim,
                p.produto,
                p.status,
                ia.nome_area,
                ia.gestor,
                STRING_AGG(DISTINCT r.nome_risco, '; ') as riscos,
                MAX(r.score_risco) as maior_risco
            FROM processos p
            JOIN informacoes_area ia ON p.id_area = ia.id_area
            LEFT JOIN riscos r ON p.id = r.processo_id
            WHERE p.status = 'Ativo'
            GROUP BY p.id, ia.nome_area, ia.gestor
            ORDER BY ia.nome_area, p.codigo_processo
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn)
        
def marcar_relatorio_gerencial_gerado(processo_id):
    """Marca que o relatório gerencial foi gerado para um processo"""
    query = text("""
        UPDATE processos
        SET relatorio_gerencial_gerado = TRUE,
            data_relatorio_gerencial = NOW()
        WHERE id = :processo_id
    """)
    with engine.begin() as conn:
        conn.execute(query, {"processo_id": processo_id})
    return True

def gerar_relatorio_gerencial_area(area_id, area_nome, gestor, orientacao="RETRATO"):
    """Gera relatório gerencial da área (para validação do gestor)
    
    Args:
        area_id: ID da área
        area_nome: Nome da área
        gestor: Nome do gestor
        orientacao: "RETRATO" (padrão) ou "PAISAGEM"
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    import io
    import os
    import math
    
    buffer = io.BytesIO()
    
    # Definir orientação da página
    if orientacao.upper() == "PAISAGEM":
        pagesize = landscape(A4)
        # Margens menores para aproveitar espaço
        topMargin = 1.5*cm
        bottomMargin = 1.5*cm
        leftMargin = 1.0*cm
        rightMargin = 1.0*cm
        # Largura útil da página em paisagem: ~27.5cm (29.7 - 2.2)
        col_widths = [3.0*cm, 8*cm, 12*cm, 3.0*cm]
    else:  # RETRATO
        pagesize = A4
        topMargin = 3*cm
        bottomMargin = 2*cm
        leftMargin = 3*cm
        rightMargin = 2*cm
        # Largura útil da página em retrato: ~18cm (21 - 3)
        col_widths = [2.2*cm, 4.5*cm, 7.5*cm, 2.2*cm]
    
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, 
                           topMargin=topMargin, bottomMargin=bottomMargin,
                           leftMargin=leftMargin, rightMargin=rightMargin)
    
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para o título
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor('#0b5b99')
    )
    
    # Estilo para texto normal com quebra de linha
    normal_style = styles['Normal']
    
    story = []

    # ===== CABEÇALHO COM LOGOS =====
    # Caminho das logos
    logo_fusve_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "logo_fusve.png")
    logo_auditoria_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "logo_auditoria-removebg-preview.png")
    
    # Criar tabela para cabeçalho com duas colunas (logos lado a lado)
    header_data = []

    # Verificar se as logos existem
    tem_logo_esquerda = os.path.exists(logo_fusve_path)
    tem_logo_direita = os.path.exists(logo_auditoria_path)
    if tem_logo_esquerda or tem_logo_direita:
        # Criar lista para as logos
        logos_linha = []

        # Logo esquerda (FUSVE)
        if tem_logo_esquerda:
            img_esquerda = Image(logo_fusve_path, width=4*cm, height=1.5*cm)
            logos_linha.append(img_esquerda)
        else:
            logos_linha.append(Paragraph("", normal_style))

        # Espaço central (titulo)
        logos_linha.append(Paragraph("", normal_style))

        # Logo direita (Auditoria)
        if tem_logo_direita:
            img_direita = Image(logo_auditoria_path, width=5.0*cm, height=1.8*cm)
            logos_linha.append(img_direita)
        else:
            logos_linha.append(Paragraph("", normal_style))
        
        header_data.append(logos_linha)

        # Tabela de cabeçalho
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

    # ===== TÍTULO =====
    story.append(Paragraph("Relatório Gerencial de Auditoria", titulo_style))
    
    # ===== INFORMAÇÕES DA ÁREA =====
    story.append(Paragraph(f"<b>Área:</b> {area_nome}", normal_style))
    story.append(Paragraph(f"<b>Gestor Responsável:</b> {gestor}", normal_style))
    story.append(Paragraph(f"<b>Data de Geração:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
    story.append(Spacer(1, 20))
    
    # ===== BUSCAR PROCESSOS E RISCOS =====
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
        LEFT JOIN riscos r ON p.id = r.processo_id
        WHERE p.id_area = :area_id AND p.status = 'Ativo'
        ORDER BY 
            string_to_array(p.codigo_processo, '.')::int[],
            r.score_risco DESC NULLS LAST
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"area_id": area_id})
    
    if df.empty:
        story.append(Paragraph("Nenhum processo encontrado para esta área.", normal_style))
    else:
        story.append(Paragraph("<b>Processos e Riscos Identificados</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # ===== CONFIGURAÇÃO DA TABELA =====
        data = [[
            Paragraph("<b>Código</b>", normal_style),
            Paragraph("<b>Processo</b>", normal_style),
            Paragraph("<b>Risco Identificado</b>", normal_style),
            Paragraph("<b>Risco Bruto</b>", normal_style)
        ]]
        
        # Adicionar linhas
        for _, row in df.iterrows():
            # Código do processo
            codigo = Paragraph(str(row['codigo_processo']) if row['codigo_processo'] else "N/A", normal_style)
            
            # Nome do processo
            nome_processo = Paragraph(str(row['nome_processo']) if row['nome_processo'] else "Não informado", normal_style)
            
            # Nome do risco ou "Nenhum risco cadastrado"
            if row['risco_id']:
                # Tratar nome do risco (substituir None por string vazia)
                nome_risco = str(row['nome_risco']) if row['nome_risco'] else "Risco não nomeado"
                risco_nome = Paragraph(nome_risco, normal_style)
                
                # Tratar score (pode ser None, NaN, ou número)
                score = row['score_risco']
                
                # Converter NaN para None
                if isinstance(score, float) and math.isnan(score):
                    score = None
                
                # Pegar apenas a cor (ignorar o emoji)
                cor_risco, _ = get_estilo_risco(score)
                
                # Texto do score
                texto_score = str(int(score)) if score is not None else "-"
                
                # Exibir apenas com a cor (sem emoji)
                risco_bruto = Paragraph(f'<font color="{cor_risco}"><b>{texto_score}</b></font>', normal_style)
            else:
                risco_nome = Paragraph("<i>Nenhum risco cadastrado</i>", normal_style)
                risco_bruto = Paragraph("0", normal_style)
            
            data.append([codigo, nome_processo, risco_nome, risco_bruto])
        
        # Criar tabela
        tabela = Table(data, colWidths=col_widths, repeatRows=1)

        # Estilo da tabela
        tabela_style = TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b5b99')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            
            # ===== ALINHAMENTO VERTICAL (apenas para colunas específicas) =====
            # Coluna 0 (Código) - vertical centralizado
            ('VALIGN', (0, 1), (0, -1), 'MIDDLE'),
            # Coluna 3 (Risco Bruto) - vertical centralizado
            ('VALIGN', (3, 1), (3, -1), 'MIDDLE'),
            # Colunas 1 e 2 (Processo e Risco) - vertical TOP (padrão)
            ('VALIGN', (1, 1), (2, -1), 'TOP'),
            
            # ===== ALINHAMENTO HORIZONTAL =====
            # Coluna 0 (Código) - horizontal centralizado
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            # Coluna 3 (Risco Bruto) - horizontal centralizado
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            # Colunas 1 e 2 - horizontal esquerda
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),
        ])

        # Adicionar fundo alternado para as linhas
        for i in range(1, len(data)):
            if i % 2 == 1:
                tabela_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#e8f4f8'))

        tabela.setStyle(tabela_style)
        story.append(tabela)
    
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
    
    # Linha do gestor
    story.append(Paragraph(f"<b>Gestor:</b> {gestor}", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Data:</b> ___/___/_______", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Assinatura:</b> ________________________________", normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def tela_relatorios():
    """Tela de geração de relatórios"""
    st.title("📄 Geração de Relatórios")

    tab1, tab2, tab3 = st.tabs([
        "📊 Relatório Gerencial (Validação)", 
        "📋 Relatório Técnico (Ciência)", 
        "📈 Relatório Consolidado"
    ])

    # ==== TAB 1: RELATÓRIO GERENCIAL ====
    with tab1:
        st.subheader("Relatório para Validação do Gestor")
        st.info("Este relatório consolida todos os processos da área e seus riscos para a validação do gestor.")

        # Listar áreas
        df_areas = listar_areas()
        if df_areas.empty:
            st.warning('Nenhuma área cadastrada.')
        else:
            opcoes_area = {row['nome_area']: row['id_area'] for _, row in df_areas.iterrows()}
            area_selecionada = st.selectbox("Selecione a Área", list(opcoes_area.keys()))
            col_orient1, col_orient2 = st.columns(2)
            with col_orient1:
                orientacao = st.radio(
                    "Orientação do Relatório",
                    ["RETRATO", "PAISAGEM"],
                    horizontal=True,
                    index=0
                )
            id_area = opcoes_area[area_selecionada]

            # Buscar gestor da área
            query_gestor = text("SELECT gestor FROM informacoes_area WHERE id_area = :id_area")
            with engine.connect() as conn:
                gestor = conn.execute(query_gestor, {"id_area": id_area}).scalar() or "Gestor não informado"

            if st.button("Gerar Relatório Gerencial", type="primary", use_container_width=False):
                with st.spinner("Gerando relatório para validação do gestor..."):
                    time_module.sleep(1.15)
                    pdf_bytes = gerar_relatorio_gerencial_area(id_area, area_selecionada, gestor, orientacao)
                    if pdf_bytes:
                        st.session_state['pdf_gerencial'] = pdf_bytes
                        st.success("✅ Relatório gerencial gerado com sucesso!")
                    else:
                        st.error("Erro ao gerar relatório.")
            if 'pdf_gerencial' in st.session_state:
                st.download_button(
                    label="📥 Baixar Relatório Gerencial",
                    data=st.session_state['pdf_gerencial'],
                    file_name=f"relatorio_gerencial_{area_selecionada}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=False
                )
    # ==== TAB 2: RELATÓRIO TÉCNICO ====
    with tab2:
        st.subheader("Relatório Técnico do Processo")
        st.info("Relatório detalhado do processo para ciência da equipe.")

        # Buscar processos pendentes
        if st.button("Atualizar Lista de Processos", key='btn_atualizar_lista_de_processos'):
            st.session_state['df_pendentes'] = buscar_processos_pendentes_relatorio()
        if 'df_pendentes' not in st.session_state:
            st.session_state['df_pendentes'] = buscar_processos_pendentes_relatorio()
        if not st.session_state['df_pendentes'].empty:
            df = st.session_state['df_pendentes']
            st.dataframe(df[['codigo_processo', 'nome_processo', 'nome_area', 'status_relatorio']])

            codigo_selecionado = st.selectbox(
                "Selecione o Processo:",
                df['codigo_processo'].tolist(),
                key="select_processo_tecnico"
            )

            if st.button("Gerar Relatório Técnico", key='btn_gerar_relatorio_tecnico', type="primary"):
                with st.sipnner("Gerando relatório técnico..."):
                    time_module.sleep(1.15)
                    pdf_bytes = gerar_pdf_em_memoria(codigo_selecionado)

                    if pdf_bytes:
                        st.session_state['pdf_tecnico'] = bytes(pdf_bytes)
                        st.success(f"✅ Relatório técnico do processo {codigo_selecionado} gerado com sucesso!")
                    else:
                        st.error("Erro ao gerar relatório.")
            if 'pdf_tecnico' in st.session_state:
                st.download_button(
                    label="📥 Baixar Relatório Técnico",
                    data=st.session_state['pdf_tecnico'],
                    file_name=f"relatorio_tecnico_{codigo_selecionado}.pdf",
                    mime="application/pdf"
                )
            else:
                st.info("Nenhum processo pendente para gerar relatório técnico")
    
    # ==== TAB 3: RELATÓRIO CONSOLIDADO ====
    with tab3:
        st.subheader("Relatório Consolidado da Auditoria")
        st.info("Visão executiva da auditoria com estatísticas e análises.")

        # Selecionar auditoria
        query_auditorias = text("""
            SELECT a.id, a.codigo_auditoria, a.titulo, a.ano, a.trimestre, ia.nome_area
            FROM auditorias a
            JOIN informacoes_area ia ON a.id_area = ia.id_area
            ORDER BY a.ano DESC, a.trimestre DESC
        """)
        with engine.connect() as conn:
            df_auditorias = pd.read_sql(query_auditorias, conn)
        if df_auditorias.empty:
            st.warning("Nenhuma auditoria encontrada.")
        else:
            opcoes_auditoria = {f"{row['codigo_auditoria']} - {row['titulo']}": row['id'] for _, row in df_auditorias.iterrows()}
            auditoria_selecionada = st.selectbox("Selecione a Auditoria:", list(opcoes_auditoria.keys()))
            auditoria_id = opcoes_auditoria[auditoria_selecionada]
            if st.button("Gerar Relatório Consolidado", type="primary", use_container_width=True):
                with st.spinner("Gerando relatório consolidado..."):
                    time_module.sleep(1.15)
                    # Buscar estatísicas da auditoria
                    query_stats = text("""
                        SELECT
                            COUNT(DISTINCT p.id) as total_processos,
                            COUNT(DISTINCT r.id) as total_riscos,
                            COUNT(DISTINCT c.id) as total_controles,
                            COUNT(DISTINCT cs.id) as total_checklists
                        FROM auditoria_processos ap
                        JOIN processos p ON ap.processo_id = p.id
                        LEFT JOIN riscos r ON p.id = r.processo_id
                        LEFT JOIN riscos_etapa re ON p.id = re.etapa_id
                        LEFT JOIN controles_etapa c ON re.id = c.risco_id
                        LEFT JOIN checklist_sessoes cs ON cs.processo_id = p.id AND cs.auditoria_id = ap.auditoria_id
                        WHERE ap.auditoria_id = :auditoria_id
                    """)
                    with engine.connect() as conn:
                        stats = conn.execute(query_stats, {"auditoria_id": auditoria_id}).fetchone()

                    # Gerar relatório consolidado (simplificado)
                    from reportlab.lib.pagesizes import A4
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.styles import getSampleStyleSheet
                    import io

                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=A4)
                    styles = getSampleStyleSheet()
                    story = []

                    story.append(Paragraph(f"Relatório Consolidado de Auditoria", styles['Heading1']))
                    story.append(Spacer(1, 20))
                    story.append(Paragraph(f"<b>Auditoria:</b> {auditoria_selecionada}", styles['Normal']))
                    story.append(Paragraph(f"<b>Data de Geração:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
                    story.append(Spacer(1, 30))
                    
                    story.append(Paragraph("<b>Estatísticas da Auditoria</b>", styles['Heading2']))
                    story.append(Spacer(1, 10))
                    story.append(Paragraph(f"• Total de Processos Auditados: {stats[0] or 0}", styles['Normal']))
                    story.append(Paragraph(f"• Total de Riscos Identificados: {stats[1] or 0}", styles['Normal']))
                    story.append(Paragraph(f"• Total de Controles Mapeados: {stats[2] or 0}", styles['Normal']))
                    story.append(Paragraph(f"• Total de Checklists Realizados: {stats[3] or 0}", styles['Normal']))
                    
                    doc.build(story)
                    buffer.seek(0)
                    pdf_bytes = buffer.getvalue()
                    
                    if pdf_bytes:
                        st.session_state['pdf_consolidado'] = pdf_bytes
                        st.success("✅ Relatório consolidado gerado com sucesso!")
                    else:
                        st.error("Erro ao gerar relatório.")
            
            if 'pdf_consolidado' in st.session_state:
                st.download_button(
                    label="📥 Baixar Relatório Consolidado",
                    data=st.session_state['pdf_consolidado'],
                    file_name=f"relatorio_consolidado_auditoria_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                ) 