from reportlab.lib.units import cm
from reportlab.lib import colors
from .variaveis_globais import COR_RODAPE
from datetime import datetime
from utils.formatters import formatar_telefone
from .logos import desenhar_logos

def criar_rodape(canvas, doc, pagesize, total_paginas, titulo_rodape, root_dir=None,
                 email_auditoria=None, telefone_auditoria=None):
    """Cria o rodapé padronizado com logos, email e telefone"""

    from zoneinfo import ZoneInfo

    TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
    
    # ⭐ SE FOR A PRIMEIRA PÁGINA (CAPA), NÃO DESENHA NADA
    if doc.page == 1:
        return  # ⭐ NÃO DESENHA RODAPÉ NA CAPA
    
    canvas.saveState()
    
    altura_rodape = 1.8 * cm
    y_fundo = 0
    
    canvas.setFillColor(colors.HexColor(COR_RODAPE))
    canvas.rect(0, y_fundo, pagesize[0], altura_rodape, fill=1, stroke=0)
    
    # ⭐ LINHA 1: Título e página (AJUSTADO PARA PULAR A CAPA)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#666666'))
    
    # ⭐ doc.page - 1 porque a página 1 é a capa
    numero_pagina = doc.page - 1
    total_paginas_sem_capa = total_paginas - 1

    data_hora_emissao = datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    
    canvas.drawCentredString(
        pagesize[0]/2, 
        2*cm, 
        f"{titulo_rodape} - Página {numero_pagina}/{total_paginas_sem_capa} - Emissão: {data_hora_emissao}"
    )
    
    # ⭐ LINHA 2: Email e Telefone
    if email_auditoria or telefone_auditoria:
        texto_contato = "Gerência de Auditoria Interna - "
        if email_auditoria and email_auditoria != 'Não informado':
            texto_contato += f"E-mail: {email_auditoria}"
        if telefone_auditoria and telefone_auditoria != 'Não informado':
            if texto_contato:
                texto_contato += " | "
            telefone_formatado = formatar_telefone(telefone_auditoria)
            texto_contato += f"Tel: {telefone_formatado}"
        
        if texto_contato:
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(colors.HexColor('#888888'))
            canvas.drawCentredString(
                pagesize[0]/2, 
                1.5*cm, 
                texto_contato
            )
    
    # ⭐ DESENHAR OS LOGOS (APENAS NAS PÁGINAS QUE NÃO SÃO A CAPA)
    desenhar_logos(canvas, pagesize, root_dir)
    
    canvas.restoreState()