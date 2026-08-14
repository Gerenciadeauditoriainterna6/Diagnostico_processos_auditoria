from utils.relatorios.variaveis_globais import TEXTOS_VALIDACAO
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import cm
from utils.relatorios.informacoes import buscar_responsaveis_auditoria

# ====== FUNÇÃO PARA CRIAR A PÁGINA DE VALIDAÇÃO ======
def criar_pagina_validacao(story, gestor, styles, normal_style, auditoria_id=None, 
                           tipo_relatorio='padrao', entrevistado=None):
    """
    Adiciona a página de validação do gestor ao story com todos os campos de assinatura
    """

    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    # ⭐ BUSCAR O TEXTO CORRETO PARA O TIPO DE RELATÓRIO
    config = TEXTOS_VALIDACAO.get(tipo_relatorio, TEXTOS_VALIDACAO['padrao'])
    titulo_validacao = config['titulo']
    texto_declaracao = config['texto']

    if 'titulo' not in styles:
        styles.add(ParagraphStyle(
            'titulo',
            parent=styles['Normal'],
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            textColor=colors.HexColor('#184145'),
            spaceAfter=12
        ))
    
    # ⭐ ESTILOS REDUZIDOS
    campo_titulo_style = ParagraphStyle(
        'CampoTitulo',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=1
    )
    
    nome_style = ParagraphStyle(
        'NomeStyle',
        parent=normal_style,
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=1
    )
    
    rotulo_style = ParagraphStyle(
        'RotuloStyle',
        parent=normal_style,
        fontSize=8,
        textColor=colors.HexColor('#666666')
    )
    
    linha_assinatura_style = ParagraphStyle(
        'LinhaAssinatura',
        parent=normal_style,
        fontSize=8,
        alignment=1,
        textColor=colors.HexColor('#999999'),
        spaceAfter=1
    )

    texto_declaracao_style = ParagraphStyle(
        'TextoDeclaracao',
        parent=normal_style,
        fontSize=9,
        leading=12,
        alignment=4,
        spaceAfter=10
    )
    
    # ⭐ Função auxiliar para criar um bloco de assinatura (VERSÃO COMPACTA)
    def criar_bloco_assinatura(titulo, nome_padrao=None):
        """Cria um bloco com Nome, Data e Assinatura (sem bordas) - VERSÃO COMPACTA"""
        dados = []
        
        # Nome (com ou sem valor padrão)
        if nome_padrao:
            dados.append([
                Paragraph(f"<b>{titulo}:</b> {nome_padrao}", nome_style)
            ])
        else:
            dados.append([
                Paragraph(f"<b>{titulo}:</b> _________________________", nome_style)
            ])
        
        # Data
        dados.append([
            Paragraph("<b>Data:</b> ____/____/________", rotulo_style)
        ])
        
        # Assinatura
        dados.append([
            Paragraph("___________________________________________", linha_assinatura_style)
        ])
        dados.append([
            Paragraph("<i>Assinatura</i>", ParagraphStyle(
                'AssinaturaLabel',
                parent=normal_style,
                fontSize=7,
                alignment=1,
                textColor=colors.HexColor('#999999')
            ))
        ])
        
        tabela = Table(dados, colWidths=[14*cm])
        tabela.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        return tabela
    
    # ⭐ BUSCAR RESPONSÁVEIS DA AUDITORIA
    responsaveis = []
    if auditoria_id:
        responsaveis = buscar_responsaveis_auditoria(auditoria_id)
    
    # ⭐ INÍCIO DA PÁGINA
    story.append(PageBreak())
    
    # Título principal
    story.append(Paragraph(titulo_validacao, styles['titulo']))
    story.append(Spacer(1, 5))
    
    # Texto de declaração
    story.append(Paragraph(texto_declaracao, texto_declaracao_style))
    story.append(Spacer(1, 10))
    
    # ⭐ ============================================================
    # GESTOR DA ÁREA
    # ⭐ ============================================================
    story.append(Paragraph("GESTOR DA ÁREA", campo_titulo_style))
    story.append(Spacer(1, 2))
    story.append(criar_bloco_assinatura("Gestor", gestor))
    story.append(Spacer(1, 8))

    # ⭐ ============================================================
    # ENTREVISTADO (REUTILIZANDO A FUNÇÃO)
    # ⭐ ============================================================
    story.append(Paragraph("ENTREVISTADO", campo_titulo_style))
    story.append(Spacer(1, 2))
    
    if entrevistado and entrevistado.strip():
        # ⭐ REUTILIZA A MESMA FUNÇÃO!
        story.append(criar_bloco_assinatura("Entrevistado", entrevistado))
    else:
        # ⭐ TAMBÉM REUTILIZA, MAS COM NOME VAZIO
        story.append(criar_bloco_assinatura("Entrevistado"))
    
    story.append(Spacer(1, 8))
    
    # ⭐ ============================================================
    # RESPONSÁVEIS PELA AUDITORIA
    # ⭐ ============================================================
    story.append(Paragraph("AUDITORES RESPONSÁVEIS PELA AUDITORIA", campo_titulo_style))
    story.append(Spacer(1, 2))
    
    if responsaveis and len(responsaveis) > 0:
        for idx, responsavel in enumerate(responsaveis, 1):
            story.append(criar_bloco_assinatura(f"Auditor", responsavel))
            story.append(Spacer(1, 4))
    else:
        story.append(criar_bloco_assinatura("Auditor"))
        story.append(Spacer(1, 4))
        story.append(criar_bloco_assinatura("Auditor"))
    
    story.append(Spacer(1, 8))
    
    # ⭐ ============================================================
    # AUDITOR REVISOR
    # ⭐ ============================================================
    story.append(Paragraph("AUDITOR REVISOR", campo_titulo_style))
    story.append(Spacer(1, 2))
    story.append(criar_bloco_assinatura("Revisor"))
    story.append(Spacer(1, 8))
    
    # ⭐ ============================================================
    # GERENTE DE AUDITORIA INTERNA
    # ⭐ ============================================================
    gerente_content = []
    
    gerente_content.append(Paragraph("GERENTE DE AUDITORIA INTERNA", campo_titulo_style))
    gerente_content.append(Spacer(1, 2))
    
    gerente_dados = []
    gerente_dados.append([
        Paragraph("TEÓFILO GAIO BOTO", nome_style)
    ])
    gerente_dados.append([
        Paragraph("<b>Data:</b> ____/____/________", rotulo_style)
    ])
    gerente_dados.append([
        Paragraph("___________________________________________", linha_assinatura_style)
    ])
    gerente_dados.append([
        Paragraph("<i>Assinatura</i>", ParagraphStyle(
            'AssinaturaLabel',
            parent=normal_style,
            fontSize=7,
            alignment=1,
            textColor=colors.HexColor('#999999')
        ))
    ])
    
    tabela_gerente = Table(gerente_dados, colWidths=[14*cm])
    tabela_gerente.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    gerente_content.append(tabela_gerente)
    
    from reportlab.platypus import KeepTogether
    story.append(KeepTogether(gerente_content))