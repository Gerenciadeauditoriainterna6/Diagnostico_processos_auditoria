def criar_pagina_capa(story, pagesize, titulo_relatorio, subtitulo_relatorio=None, area_nome=None, data_emissao=None):
    """
    Cria uma página de capa para o relatório com centralização vertical.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from reportlab.platypus import Paragraph, Spacer, Image, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    import os
    from pathlib import Path
    
    TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    
    # Estilos para a capa
    titulo_capa_style = ParagraphStyle(
        'TituloCapa',
        parent=normal_style,
        fontSize=14,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0b5b99'),
        spaceAfter=10
    )

    titulo_capa_style2 = ParagraphStyle(
        'TituloCapa2',
        parent=normal_style,
        fontSize=18,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#000000'),
        spaceAfter=5,
        leading=28
    )
    
    subtitulo_capa_style = ParagraphStyle(
        'SubtituloCapa',
        parent=normal_style,
        fontSize=14,
        fontName='Helvetica',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#000000'),
        spaceAfter=20,
        leading=15
    )
    
    info_capa_style = ParagraphStyle(
        'InfoCapa',
        parent=normal_style,
        fontSize=14,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0b5b99'),
        spaceAfter=6
    )

    info_capa_style2 = ParagraphStyle(
        'InfoCapa2',
        parent=normal_style,
        fontSize=11,
        fontName='Helvetica',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#184145'),
        spaceAfter=6
    )
    
    # ⭐ CALCULAR ESPAÇO PARA CENTRALIZAR
    altura_disponivel = pagesize[1] - 2*cm - 2*cm
    
    altura_estimada = 0
    
    root_dir = Path(__file__).parent.parent.parent
    logo_path = os.path.join(root_dir, "static", "assets", "logo_auditoria_recortada_circulo2.png")
    if os.path.exists(logo_path):
        altura_estimada += 4*cm + 20
    else:
        altura_estimada += 20
    
    altura_estimada += 30  # "GERÊNCIA DE AUDITORIA INTERNA"
    altura_estimada += 20  # spacer
    altura_estimada += 30  # "FUSVE"
    altura_estimada += 40  # spacer
    altura_estimada += 40  # título principal
    altura_estimada += 20  # spacer
    
    if subtitulo_relatorio:
        altura_estimada += 30
        altura_estimada += 20
    
    if area_nome:
        altura_estimada += 20
    altura_estimada += 20
    
    espaco_extra = (altura_disponivel - altura_estimada) / 2
    if espaco_extra < 0:
        espaco_extra = 1*cm
    
    # ⭐ SPACER INICIAL (centraliza o conteúdo na página)
    story.append(Spacer(1, espaco_extra))
    
    # Logo
    if os.path.exists(logo_path):
        img = Image(logo_path, width=4*cm, height=4*cm)
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 20))
    
    # Título
    story.append(Paragraph("GERÊNCIA DE AUDITORIA INTERNA", titulo_capa_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("FUSVE", 
                           ParagraphStyle('CustomParagraph', parent=info_capa_style, fontSize=14)))
    story.append(Spacer(1, 40))
    
    # Título principal
    story.append(Paragraph(titulo_relatorio, titulo_capa_style2))
    story.append(Spacer(1, 5))
    
    if subtitulo_relatorio:
        story.append(Paragraph(subtitulo_relatorio, subtitulo_capa_style))
    
    story.append(Spacer(1, 45))
    
    # Informações adicionais
    if area_nome:
        story.append(Paragraph(f"{area_nome}", info_capa_style2))
    
    if data_emissao is None:
        data_emissao = datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    
    story.append(Paragraph(f"Emissão: {data_emissao}", info_capa_style2))
    
    # ⭐⭐⭐ USAR PageBreak() PARA FORÇAR A PRÓXIMA PÁGINA ⭐⭐⭐
    # O PageBreak é necessário para separar a capa do conteúdo
    story.append(PageBreak())