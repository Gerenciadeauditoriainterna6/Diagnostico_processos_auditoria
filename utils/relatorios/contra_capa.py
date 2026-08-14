def contra_capa_relatorio(story, styles, normal_style, pagesize, leftMargin, rightMargin,
                                   auditoria_id=None, processo_id=None, area_id=None, area_nome=None,
                                   gestor=None, cargo=None, titulo_auditoria=None):
    """
    Adiciona as informações padronizadas para todos os relatórios.
    """
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    
    TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
    
    # ⭐ ESTILOS
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
    
    info_valor_style_2 = ParagraphStyle(
        'InfoValor2',
        parent=normal_style,
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#333333'),
        wordWrap='CJK'
    )
    
    # ⭐ CALCULAR LARGURAS
    largura_label = 4.5 * cm
    largura_valor = pagesize[0] - leftMargin - rightMargin - largura_label - 1*cm
    
    # ============================================================
    # 1. BUSCAR DADOS DA AUDITORIA
    # ============================================================
    codigo_auditoria = ""
    titulo_auditoria = ""
    data_inicio_auditoria = ""
    data_fim_auditoria = ""
    status_auditoria = ""
    
    if auditoria_id:
        with engine.connect() as conn:
            query = text("""
                SELECT codigo_auditoria, titulo, data_inicio, data_fim, status
                FROM auditorias WHERE id = :auditoria_id
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            if result:
                codigo_auditoria = result[0] or ''
                titulo_auditoria = result[1] or ''
                data_inicio_auditoria = result[2]
                data_fim_auditoria = result[3]
                status_auditoria = result[4] or 'Não informado'
    
    # Formatar datas
    if data_inicio_auditoria:
        if hasattr(data_inicio_auditoria, 'strftime'):
            data_inicio_auditoria = data_inicio_auditoria.strftime('%d/%m/%Y')
        else:
            data_inicio_auditoria = str(data_inicio_auditoria)
    else:
        data_inicio_auditoria = 'Não informado'
    
    if data_fim_auditoria:
        if hasattr(data_fim_auditoria, 'strftime'):
            data_fim_auditoria = data_fim_auditoria.strftime('%d/%m/%Y')
        else:
            data_fim_auditoria = str(data_fim_auditoria)
    else:
        data_fim_auditoria = 'Não informado'
    
    cronograma = f"{data_inicio_auditoria} a {data_fim_auditoria}"
    
    # ⭐ COR DO STATUS
    status_text = status_auditoria or 'Não informado'
    status_colors = {
        'EM EXECUÇÃO': '#17a2b8',
        'EFICÁCIA VALIDADA': '#28a745',
        'FOLLOW-UP': '#ffc107',
        'INCONCLUSIVA': '#dc3545'
    }
    cor_status = status_colors.get(status_text, '#666666')
    status_html = f'<font color="{cor_status}"><b>{status_text}</b></font>'
    
    # ============================================================
    # 2. BUSCAR PROCESSO
    # ============================================================
    proc_codigo = ""
    proc_nome = ""
    if processo_id:
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT codigo_processo, nome_processo FROM processos WHERE id = :processo_id
                """)
                result = conn.execute(query, {'processo_id': processo_id}).fetchone()
                if result:
                    proc_codigo = result[0] or ''
                    proc_nome = result[1] or ''
        except Exception:
            pass
    
    # ============================================================
    # 3. BUSCAR ENTREVISTADO
    # ============================================================
    entrevistado = ""
    if processo_id:
        try:
            with engine.connect() as conn:
                query = text("SELECT entrevistado FROM processos WHERE id = :processo_id")
                result = conn.execute(query, {'processo_id': processo_id}).fetchone()
                if result and result[0]:
                    entrevistado = result[0]
        except Exception:
            pass
    
    # ============================================================
    # 4. BUSCAR DADOS DA ÁREA (se não veio)
    # ============================================================
    area_codigo = str(area_id) if area_id else ""
    area_nome_exibicao = area_nome or ""
    area_unidade = ""
    area_objetivo = ""
    area_superintendente = ""
    area_diretor = ""
    area_email = ""
    area_telefone = ""
    
    if area_id:
        with engine.connect() as conn:
            query = text("""
                SELECT nome_area, loc_unidade, objetivo_area, superintendente, diretor, email, telefone
                FROM informacoes_area WHERE id_area = :area_id
            """)
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            if result:
                area_nome_exibicao = result[0] or area_nome_exibicao
                area_unidade = result[1] or ''
                area_objetivo = result[2] or ''
                area_superintendente = result[3] or ''
                area_diretor = result[4] or ''
                area_email = result[5] or ''
                area_telefone = result[6] or ''
    
    # ============================================================
    # 5. DATA/HORA DE EMISSÃO
    # ============================================================
    data_emissao = datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    
    # ============================================================
    # 6. MONTAR TABELA COMPLETA
    # ============================================================
    dados = []
    
    # --- SEÇÃO 1: DADOS DA AUDITORIA ---

    # --- PROCESSO AUDITADO (se houver) ---
    if processo_id and proc_codigo and proc_nome:
        dados.append([
            Paragraph("<b>Processo Auditado:</b>", info_label_style),
            Paragraph(f"{proc_codigo} - {proc_nome}", info_valor_style_2)
        ])
        
    dados.append([
        Paragraph("<b>Código da Auditoria:</b>", info_label_style),
        Paragraph(codigo_auditoria or 'N/A', info_valor_style)
    ])
    
    dados.append([
        Paragraph("<b>Título:</b>", info_label_style),
        Paragraph(titulo_auditoria or 'N/A', info_valor_style_2)
    ])

    dados.append([
        Paragraph("<b>Código da Área:</b>", info_label_style),
        Paragraph(area_codigo or 'N/A', info_valor_style)
    ])
    
    dados.append([
        Paragraph("<b>Área:</b>", info_label_style),
        Paragraph(area_nome_exibicao or 'N/A', info_valor_style_2)
    ])
    
    dados.append([
        Paragraph("<b>Gestor:</b>", info_label_style),
        Paragraph(gestor or 'Não informado', info_valor_style)
    ])
    
    dados.append([
        Paragraph("<b>Cargo:</b>", info_label_style),
        Paragraph(cargo or 'Não informado', info_valor_style)
    ])
    
    
    if area_unidade:
        dados.append([
            Paragraph("<b>Unidade:</b>", info_label_style),
            Paragraph(area_unidade, info_valor_style)
        ])
    
    if area_email:
        dados.append([
            Paragraph("<b>E-mail:</b>", info_label_style),
            Paragraph(area_email, info_valor_style)
        ])
    
    if area_telefone:
        dados.append([
            Paragraph("<b>Telefone:</b>", info_label_style),
            Paragraph(area_telefone or 'Não informado', info_valor_style)
        ])
    
    if area_objetivo:
        dados.append([
            Paragraph("<b>Objetivo da Área:</b>", info_label_style),
            Paragraph(area_objetivo, info_valor_style_2)
        ])
    
    if area_superintendente:
        dados.append([
            Paragraph("<b>Superintendente:</b>", info_label_style),
            Paragraph(area_superintendente, info_valor_style)
        ])
    
    if area_diretor:
        dados.append([
            Paragraph("<b>Diretor:</b>", info_label_style),
            Paragraph(area_diretor, info_valor_style)
        ])

    
    # --- SEÇÃO 2: CRONOGRAMA E STATUS ---
    dados.append([
        Paragraph("<b>Cronograma Previsto:</b>", info_label_style),
        Paragraph(cronograma, info_valor_style)
    ])
    
    dados.append([
        Paragraph("<b>Status da Auditoria:</b>", info_label_style),
        Paragraph(status_html, info_valor_style)
    ])
    
    
    # --- ENTREVISTADO (se houver) ---
    if entrevistado:
        dados.append([
            Paragraph("<b>Entrevistado:</b>", info_label_style),
            Paragraph(entrevistado, info_valor_style)
        ])
    
    # --- DATA/HORA EMISSÃO ---
    dados.append([
        Paragraph("<b>Data/Hora Emissão:</b>", info_label_style),
        Paragraph(data_emissao, info_valor_style)
    ])
    
    # ============================================================
    # 7. CRIAR TABELA
    # ============================================================
    tabela = Table(dados, colWidths=[largura_label, largura_valor])
    tabela.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#DDDDDD')),
    ]))
    
    story.append(tabela)
    story.append(Spacer(1, 15))