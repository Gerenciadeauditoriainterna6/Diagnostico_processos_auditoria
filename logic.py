import os
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import text
from database import engine
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import session, request
import re
import json
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
import copy
from PyPDF2 import PdfReader

from utils.relatorios.capa import criar_pagina_capa
from utils.relatorios.variaveis_globais import COR_PRIMARIA, COR_SECUNDARIA, COR_FUNDO_TABELA
from utils.relatorios.contra_capa import contra_capa_relatorio
from utils.relatorios.validacao import criar_pagina_validacao
from utils.relatorios.informacoes import buscar_dados_gerencia_auditoria, buscar_responsaveis_auditoria
from utils.relatorios.rodape import criar_rodape

# ===== MIGRAÇÃO PARA FLASK =====
# Streamlit removido - sistema agora usa Flask
# import streamlit as st  # REMOVIDO

# Placeholder para evitar erros (as funções Streamlit não serão chamadas no Flask)
class _DummyStreamlit:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

st = _DummyStreamlit()
# ===== FIM DA MIGRAÇÃO =====



# ⭐ FUNÇÃO PARA LIMITAR TEXTO (MESMA DO PANORAMA)
def limitar_texto(texto, limite=80):
    """Limita o texto a um número máximo de caracteres e força quebra de linha"""
    if not texto:
        return ''
    # Remover quebras de linha extras
    texto = ' '.join(texto.split())
    if len(texto) <= limite:
        return texto
    # Tentar quebrar no último espaço antes do limite
    espaco = texto.rfind(' ', 0, limite)
    if espaco > 0:
        return texto[:espaco] + '...'
    return texto[:limite] + '...'

def get_estilos_relatorio():
    """
    Retorna um dicionário com todos os estilos padronizados para os relatórios
    """
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    
    # ⭐ ESTILO BASE
    estilo_normal = ParagraphStyle(
        'Normal',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    # ⭐ TÍTULOS PRINCIPAIS
    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=estilo_normal,
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor('#184145'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    estilo_titulo2 = ParagraphStyle(
        'Titulo2',
        parent=estilo_normal,
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#0b5b99'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=estilo_normal,
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#184145'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    # ⭐ CARDS E SEÇÕES
    estilo_card_titulo = ParagraphStyle(
        'CardTitulo',
        parent=estilo_normal,
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor('#184145'),
        spaceAfter=5
    )
    
    estilo_card_subtitulo = ParagraphStyle(
        'CardSubtitulo',
        parent=estilo_normal,
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#0b5b99'),
        spaceAfter=3
    )
    
    estilo_card_texto = ParagraphStyle(
        'CardTexto',
        parent=estilo_normal,
        fontSize=8,
        leading=10,
        leftIndent=10
    )
    
    # ⭐ TEXTOS COM QUEBRA DE LINHA
    estilo_texto_processo = ParagraphStyle(
        'TextoProcesso',
        parent=estilo_normal,
        fontSize=8,
        leading=10,
        wordWrap='CJK'
    )
    
    estilo_texto_risco = ParagraphStyle(
        'TextoRisco',
        parent=estilo_normal,
        fontSize=8,
        leading=10,
        wordWrap='CJK'
    )
    
    estilo_texto_controle = ParagraphStyle(
        'TextoControle',
        parent=estilo_normal,
        fontSize=7.5,
        leading=9,
        wordWrap='CJK'
    )
    
    estilo_texto_etapa = ParagraphStyle(
        'TextoEtapa',
        parent=estilo_normal,
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        leftIndent=10
    )
    
    # ⭐ INFORMAÇÕES (LABEL E VALOR)
    estilo_info_label = ParagraphStyle(
        'InfoLabel',
        parent=estilo_normal,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145')
    )
    
    estilo_info_valor = ParagraphStyle(
        'InfoValor',
        parent=estilo_normal,
        fontSize=9,
        textColor=colors.HexColor('#333333')
    )
    
    # ⭐ ÁREA (LABEL E VALOR)
    estilo_label_area = ParagraphStyle(
        'LabelArea',
        parent=estilo_normal,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145')
    )
    
    estilo_texto_area = ParagraphStyle(
        'TextoArea',
        parent=estilo_normal,
        fontSize=9,
        leading=11,
        wordWrap='CJK'
    )
    
    # ⭐ SEÇÕES E DIVISÓRIAS
    estilo_secao_titulo = ParagraphStyle(
        'SecaoTitulo',
        parent=estilo_normal,
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=5,
        spaceBefore=10
    )
    
    estilo_linha_divisoria = ParagraphStyle(
        'LinhaDivisoria',
        parent=estilo_normal,
        fontSize=1,
        textColor=colors.HexColor('#CCCCCC'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    # ⭐ RISCO TÍTULO E ITEM
    estilo_risco_titulo = ParagraphStyle(
        'RiscoTitulo',
        parent=estilo_normal,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        leftIndent=15,
        spaceAfter=2
    )
    
    estilo_risco_item = ParagraphStyle(
        'RiscoItem',
        parent=estilo_normal,
        fontSize=8,
        leading=10,
        leftIndent=30
    )
    
    # ⭐ VALIDAÇÃO
    estilo_titulo_validacao = ParagraphStyle(
        'TituloValidacao',
        parent=estilo_subtitulo,
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=15
    )
    
    estilo_campo_titulo = ParagraphStyle(
        'CampoTitulo',
        parent=estilo_normal,
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=2
    )
    
    estilo_nome = ParagraphStyle(
        'NomeStyle',
        parent=estilo_normal,
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=2
    )
    
    estilo_rotulo = ParagraphStyle(
        'RotuloStyle',
        parent=estilo_normal,
        fontSize=9,
        textColor=colors.HexColor('#666666')
    )
    
    estilo_assinatura = ParagraphStyle(
        'AssinaturaStyle',
        parent=estilo_normal,
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#666666'),
        spaceAfter=2
    )
    
    # ⭐ RETORNAR DICIONÁRIO COM TODOS OS ESTILOS
    return {
        'normal': estilo_normal,
        'titulo': estilo_titulo,
        'titulo2': estilo_titulo2,
        'subtitulo': estilo_subtitulo,
        'card_titulo': estilo_card_titulo,
        'card_subtitulo': estilo_card_subtitulo,
        'card_texto': estilo_card_texto,
        'texto_processo': estilo_texto_processo,
        'texto_risco': estilo_texto_risco,
        'texto_controle': estilo_texto_controle,
        'texto_etapa': estilo_texto_etapa,
        'info_label': estilo_info_label,
        'info_valor': estilo_info_valor,
        'label_area': estilo_label_area,
        'texto_area': estilo_texto_area,
        'secao_titulo': estilo_secao_titulo,
        'linha_divisoria': estilo_linha_divisoria,
        'risco_titulo': estilo_risco_titulo,
        'risco_item': estilo_risco_item,
        'titulo_validacao': estilo_titulo_validacao,
        'campo_titulo': estilo_campo_titulo,
        'nome': estilo_nome,
        'rotulo': estilo_rotulo,
        'assinatura': estilo_assinatura
    }

def registrar_log(tabela, registro_id, operacao, dados_anteriores=None, dados_novos=None, query_sql=None):
    """
    Registra uma ação do usuário na tabela de log (adaptado para Flask)
    """
    try:
        with engine.begin() as conn:
            # Pega informações do usuário logado (agora do Flask session)
            usuario_id = session.get('usuario_id', None)
            usuario_nome = session.get('usuario_nome', session.get('usuario_logado', 'Sistema'))

            # Pega o IP do cliente (Flask request)
            ip_origem = request.remote_addr if request else '0.0.0.0'

            # Converte dicionários para JSON (STRING)
            dados_anteriores_json = json.dumps(dados_anteriores, default=str) if dados_anteriores else None
            dados_novos_json = json.dumps(dados_novos, default=str) if dados_novos else None

            conn.execute(text("""
                INSERT INTO log_auditoria
                    (tabela_afetada, registro_id, operacao, dados_anteriores, dados_novos,
                     usuario_id, usuario_nome, ip_origem, query_sql, data_hora)
                VALUES
                    (:tabela, :registro_id, :operacao, :dados_anteriores, :dados_novos,
                     :usuario_id, :usuario_nome, :ip_origem, :query_sql, :data_hora)
            """), {
                'tabela': tabela,
                'registro_id': registro_id,
                'operacao': operacao,
                'dados_anteriores': dados_anteriores_json,
                'dados_novos': dados_novos_json,
                'usuario_id': usuario_id,
                'usuario_nome': usuario_nome,
                'ip_origem': ip_origem,
                'query_sql': query_sql,
                'data_hora': datetime.now()
            })

            print(f"✅ Log registrado: {tabela} - {operacao} - ID: {registro_id}")
            return True
    except Exception as e:
        print(f"❌ Erro ao registrar log: {e}")
        import traceback
        traceback.print_exc()
        return False

# --- CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOGO = os.path.join(BASE_DIR, "assets", "logo_fusve.png")
CAMINHO_LOGO2 = os.path.join(BASE_DIR, "assets", "logo_auditoria.png")

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

def validar_login_no_banco(usuario_digitado, senha_digitada):
    from datetime import datetime, timedelta
    from werkzeug.security import check_password_hash
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, login, nome, perfil, senha, ativo, 
                       tentativas_login, bloqueado_ate, forcar_troca_senha, senha_temporaria
                FROM usuarios 
                WHERE login = :u
            """)
            result = conn.execute(query, {"u": usuario_digitado}).fetchone()
            
            if not result:
                return (False, None, None, None, 0, False, 0, False)
            
            usuario_id = result[0]
            usuario_login = result[1]
            usuario_nome = result[2]
            usuario_perfil = result[3] if result[3] else 'auditor'
            senha_hash = result[4]
            ativo = result[5]
            tentativas = result[6] or 0
            bloqueado_ate = result[7]
            forcar_troca = result[8] or False
            senha_temporaria = result[9]
            
            # Verifica bloqueio temporário
            if bloqueado_ate and datetime.now() < bloqueado_ate:
                minutos_restantes = int((bloqueado_ate - datetime.now()).total_seconds() / 60) + 1
                return (False, None, None, None, 0, True, minutos_restantes, False)
            
            # Verifica se está ativo
            if not ativo:
                return (False, None, None, None, 0, False, 0, False)
            
            # ⭐ PRIORIDADE 1: Verificar se é senha temporária (recuperação)
            if forcar_troca and senha_temporaria and senha_digitada == senha_temporaria:
                # Login com senha temporária - força trocar senha
                # Reseta tentativas e bloqueio
                conn.execute(text("""
                    UPDATE usuarios 
                    SET tentativas_login = 0, bloqueado_ate = NULL 
                    WHERE id = :id
                """), {'id': usuario_id})
                conn.commit()
                return (True, usuario_id, usuario_nome, usuario_perfil, 0, False, 0, True)  # precisa_trocar = True
            
            # ⭐ PRIORIDADE 2: Verificar senha normal (hash)
            if check_password_hash(senha_hash, senha_digitada):
                # Resetar tentativas
                conn.execute(text("""
                    UPDATE usuarios 
                    SET tentativas_login = 0, bloqueado_ate = NULL 
                    WHERE id = :id
                """), {'id': usuario_id})
                conn.commit()
                
                # Se tinha solicitação de recuperação, limpar
                if forcar_troca:
                    conn.execute(text("""
                        UPDATE usuarios 
                        SET forcar_troca_senha = FALSE, 
                            senha_temporaria = NULL, 
                            solicitou_recuperacao = FALSE 
                        WHERE id = :id
                    """), {'id': usuario_id})
                    conn.commit()
                
                return (True, usuario_id, usuario_nome, usuario_perfil, 0, False, 0, False)
            
            # Falha: incrementar tentativas
            tentativas += 1
            bloqueado = False
            minutos_restantes = 0
            
            if tentativas >= 3:
                bloqueado_ate = datetime.now() + timedelta(minutes=5)
                bloqueado = True
                minutos_restantes = 5
            
            conn.execute(text("""
                UPDATE usuarios 
                SET tentativas_login = :tentativas, bloqueado_ate = :bloqueado_ate 
                WHERE id = :id
            """), {'tentativas': tentativas, 'bloqueado_ate': bloqueado_ate if bloqueado else None, 'id': usuario_id})
            conn.commit()
            
            tentativas_restantes = max(0, 3 - tentativas)
            return (False, None, None, None, tentativas_restantes, bloqueado, minutos_restantes, False)
            
    except Exception as e:
        print(f"Erro ao validar login: {e}")
        return (False, None, None, None, 0, False, 0, False)

def salvar_area(dados_area):
    try:
        query = text("""
            INSERT INTO informacoes_area (
                nome_area, objetivo_area, status, email, telefone, gestor, loc_unidade,
                superintendente, diretor  -- ⭐ ADICIONADOS
            ) VALUES (
                :nome, :objetivo, :status, :email, :telefone, :gestor, :loc_unidade,
                :superintendente, :diretor  -- ⭐ ADICIONADOS
            )
            RETURNING id_area
        """)
        
        with engine.begin() as conn:
            id_area = conn.execute(query, {
                "nome": dados_area.get('nome', ''),
                "loc_unidade": dados_area.get('loc_unidade', ''),
                "objetivo": dados_area.get('objetivo', ''),
                "status": dados_area.get('status', 'Ativo'),
                "email": dados_area.get('email', ''),
                "telefone": dados_area.get('telefone', ''),
                "gestor": dados_area.get('gestor', ''),
                "superintendente": dados_area.get('superintendente', ''),  # ⭐ NOVO
                "diretor": dados_area.get('diretor', '')                   # ⭐ NOVO
            }).scalar()
            
            # ====== REGISTRAR LOG ======
            registrar_log(
                tabela='informacoes_area',
                registro_id=id_area,
                operacao='INSERT',
                dados_novos=dados_area,
                query_sql="INSERT INTO informacoes_area (nome_area, objetivo_area, status, email, telefone, gestor, superintendente, diretor)"
            )
            # ====== FIM DO LOG ======
            
        return id_area
    except Exception as e:
        print(f"❌ Erro ao salvar área: {e}")
        return None

def listar_areas(apenas_ativas=True):
    """Lista áreas (por padrão, apenas as ativas)"""
    from database import engine
    from sqlalchemy import text
    import pandas as pd
    
    if apenas_ativas:
        query = text("""
            SELECT id_area, nome_area, objetivo_area, status, email, telefone, gestor, loc_unidade,
                   superintendente, diretor  -- ⭐ ADICIONADOS
            FROM informacoes_area
            WHERE status = 'Ativo'
            ORDER BY nome_area
        """)
    else:
        query = text("""
            SELECT id_area, nome_area, objetivo_area, status, email, telefone, gestor, loc_unidade,
                   superintendente, diretor  -- ⭐ ADICIONADOS
            FROM informacoes_area
            ORDER BY 
                CASE WHEN status = 'Ativo' THEN 0 ELSE 1 END,
                nome_area
        """)
    
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

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

def buscar_area_por_id(area_id):
    """Buscar uma área pelo ID (retorna dicionário para log)"""
    from database import engine
    from sqlalchemy import text

    query = text("""
        SELECT id_area, nome_area, email, telefone, gestor, 
               superintendente, diretor, objetivo_area, status,
               loc_unidade
        FROM informacoes_area
        WHERE id_area = :id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"id": area_id}).mappings().first()
        return dict(result) if result else None

def excluir_area(area_id):
    """Desativa uma área e todos os seus funcionários (soft delete em cascata)"""
    from database import engine
    from sqlalchemy import text
    
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
        
        # 2. Executar o UPDATE com TODOS os campos
        query = text("""
            UPDATE informacoes_area 
            SET nome_area = :nome,
                email = :email,
                telefone = :telefone,
                gestor = :gestor,
                objetivo_area = :objetivo,
                loc_unidade = :loc_unidade,
                superintendente = :superintendente,  -- ⭐ NOVO
                diretor = :diretor                   -- ⭐ NOVO
            WHERE id_area = :id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {
                "id": area_id,
                "nome": dados.get('nome', ''),
                "email": dados.get('email', ''),
                "telefone": dados.get('telefone', ''),
                "gestor": dados.get('gestor', ''),
                "objetivo": dados.get('objetivo', ''),
                "loc_unidade": dados.get('loc_unidade', ''),
                "superintendente": dados.get('superintendente', ''),  # ⭐ NOVO
                "diretor": dados.get('diretor', '')                   # ⭐ NOVO
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
                    query_sql="UPDATE informacoes_area SET nome_area, email, telefone, gestor, objetivo_area, loc_unidade, superintendente, diretor"
                )
            return result.rowcount > 0
            
    except Exception as e:
        print(f"Erro ao atualizar área: {e}")
        import traceback
        traceback.print_exc()
        return False

def atualizar_funcionario(funcionario_id, dados):
    """Atualiza um funcionário e sincroniza com o cargo do gestor se for o caso"""
    from database import engine
    from sqlalchemy import text
    
    try:
        # 1. Buscar dados ANTES da alteração
        query_busca = text("""
            SELECT id, nome_funcionario, cargo, id_area 
            FROM funcionarios_area 
            WHERE id = :id
        """)
        
        with engine.connect() as conn:
            funcionario_atual = conn.execute(query_busca, {'id': funcionario_id}).fetchone()
            
            if not funcionario_atual:
                print(f"❌ Funcionário ID {funcionario_id} não encontrado")
                return False
            
            nome_antigo = funcionario_atual[1]
            cargo_antigo = funcionario_atual[2]
            area_id = funcionario_atual[3]
            
            # ⭐ 2. Verificar se o funcionário é o GESTOR da área
            query_verificar_gestor = text("""
                SELECT id_area, gestor, cargo 
                FROM informacoes_area 
                WHERE id_area = :area_id 
                AND UPPER(gestor) = UPPER(:nome_gestor)
            """)
            
            gestor_area = conn.execute(query_verificar_gestor, {
                'area_id': area_id,
                'nome_gestor': nome_antigo
            }).fetchone()
            
            # 3. Atualizar o funcionário
            novo_nome = dados.get('nome', nome_antigo).upper().strip()
            novo_cargo = dados.get('cargo', cargo_antigo).upper().strip()
            
            query_update_func = text("""
                UPDATE funcionarios_area 
                SET nome_funcionario = :nome,
                    cargo = :cargo,
                    data_inicio_funcao = :data_inicio_funcao,
                    data_inicio_empresa = :data_inicio_empresa
                WHERE id = :id
            """)
            
            conn.execute(query_update_func, {
                'id': funcionario_id,
                'nome': novo_nome,
                'cargo': novo_cargo,
                'data_inicio_funcao': dados.get('data_inicio_funcao', None),
                'data_inicio_empresa': dados.get('data_inicio_empresa', None)
            })
            
            # ⭐ 4. Se o funcionário é o GESTOR, atualizar o cargo na tabela informacoes_area
            if gestor_area:
                query_update_gestor = text("""
                    UPDATE informacoes_area 
                    SET cargo = :cargo
                    WHERE id_area = :area_id 
                    AND UPPER(gestor) = UPPER(:gestor)
                """)
                
                conn.execute(query_update_gestor, {
                    'area_id': area_id,
                    'gestor': nome_antigo,
                    'cargo': novo_cargo
                })
                
                print(f"✅ Cargo do gestor '{nome_antigo}' atualizado para '{novo_cargo}' na tabela informacoes_area")
            
            conn.commit()
            
            # 5. Registrar log
            from logic import registrar_log
            registrar_log(
                tabela='funcionarios_area',
                registro_id=funcionario_id,
                operacao='UPDATE',
                dados_anteriores={
                    'nome': nome_antigo,
                    'cargo': cargo_antigo,
                    'id_area': area_id
                },
                dados_novos={
                    'nome': novo_nome,
                    'cargo': novo_cargo,
                    'id_area': area_id
                },
                query_sql="UPDATE funcionarios_area SET nome_funcionario, cargo, data_inicio_funcao, data_inicio_empresa"
            )
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao atualizar funcionário: {e}")
        import traceback
        traceback.print_exc()
        return False
    
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

def gerar_codigo_processo(id_area, auditoria_id):
    """
    Gera o próximo código sequencial para um processo de uma área.
    O código é sequencial por área, independente da auditoria.
    Formato: {id_area}.{sequencial} (ex: 4.1, 4.2, 4.3...)
    """
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar o maior número sequencial
            query = text("""
                SELECT COALESCE(
                    MAX(CAST(SUBSTRING(codigo_processo FROM '^[0-9]+\\.([0-9]+)$') AS INTEGER)), 
                    0
                ) as max_sequencial
                FROM processos 
                WHERE id_area = :id_area 
                  AND codigo_processo ~ '^[0-9]+\\.[0-9]+$'
            """)
            
            resultado = conn.execute(query, {
                "id_area": id_area
            }).fetchone()
            
            max_sequencial = resultado[0] if resultado and resultado[0] else 0
            novo_numero = max_sequencial + 1
            
            codigo = f"{id_area}.{novo_numero}"
            
            print(f"✅ Código gerado: {codigo} (área: {id_area}, último: {max_sequencial}, próximo: {novo_numero})")
            return codigo
            
    except Exception as e:
        print(f"❌ Erro ao gerar código: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"{id_area}.1"

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


# ============================================================
# ====== FUNÇÕES AUXILIARES PARA RELATÓRIOS ======
# ============================================================



# ====== MAPA DE RISCO PARA CÁLCULO RESIDUAL ======
MAPA_RISCO = {
    ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14, ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
    ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10, ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
    ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6, ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
    ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2, ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
}

def calcular_risco_residual(impacto_aceitavel, probabilidade_aceitavel):
    """
    Calcula o risco residual baseado no impacto aceitável e probabilidade aceitável
    """
    # ⭐ Mapa de risco para calcular o score residual
    MAPA_RISCO_RESIDUAL = {
        ("MUITO ALTO", "MUITO ALTO"): 15,
        ("ALTO", "MUITO ALTO"): 14,
        ("MÉDIO", "MUITO ALTO"): 13,
        ("BAIXO", "MUITO ALTO"): 12,
        ("MUITO ALTO", "ALTO"): 11,
        ("ALTO", "ALTO"): 10,
        ("MÉDIO", "ALTO"): 9,
        ("BAIXO", "ALTO"): 8,
        ("MUITO ALTO", "MÉDIO"): 7,
        ("ALTO", "MÉDIO"): 6,
        ("MÉDIO", "MÉDIO"): 5,
        ("BAIXO", "MÉDIO"): 4,
        ("MUITO ALTO", "BAIXO"): 3,
        ("ALTO", "BAIXO"): 2,
        ("MÉDIO", "BAIXO"): 1,
        ("BAIXO", "BAIXO"): 0
    }
    
    # ⭐ Se ambos forem None, retorna None
    if impacto_aceitavel is None and probabilidade_aceitavel is None:
        return None
    
    # ⭐ Se um for None, usa "Médio" como padrão
    if impacto_aceitavel is None:
        impacto_aceitavel = "MÉDIO"
    if probabilidade_aceitavel is None:
        probabilidade_aceitavel = "MÉDIO"
    
    # ⭐ Converter para maiúsculas e remover espaços extras
    impacto_upper = impacto_aceitavel.strip().upper()
    probabilidade_upper = probabilidade_aceitavel.strip().upper()
    
    # ⭐ Buscar no mapa
    chave = (impacto_upper, probabilidade_upper)
    score = MAPA_RISCO_RESIDUAL.get(chave)
    
    # ⭐ Se não encontrar, retorna None
    if score is None:
        print(f"⚠️ Combinação não encontrada para risco residual: {impacto_upper} x {probabilidade_upper}")
        return None
    
    return score

# ====== ESTILOS PADRÃO ======
def get_estilos_padrao():
    """Retorna os estilos padrão para uso nos relatórios"""
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=5,
        textColor=colors.HexColor(COR_PRIMARIA)
    )

    titulo_style2 = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor(COR_PRIMARIA)
    )

    titulo_style0 = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=5,
        textColor=colors.HexColor('#000000')
    )
    
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=13,
        alignment=1,
        spaceAfter=15,
        textColor=colors.HexColor(COR_SECUNDARIA)
    )
    
    normal_style = styles['Normal']
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Bold'
    )
    
    valor_style = ParagraphStyle(
        'ValorStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#184145')
    )
    
    cabecalho_tabela = ParagraphStyle(
        'CabecalhoTabela',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=1
    )
    
    return {
        'titulo': titulo_style,
        'titulo2': titulo_style2,
        'titulo0': titulo_style0,
        'subtitulo': subtitulo_style,
        'normal': normal_style,
        'label': label_style,
        'valor': valor_style,
        'cabecalho_tabela': cabecalho_tabela
    }




# ====== FUNÇÃO PARA CRIAR TABELA ESTILIZADA ======
def criar_tabela_estilizada(dados, col_widths, cabecalho_cor=COR_PRIMARIA, 
                            fonte_tamanho=8):
    """Cria uma tabela com o estilo padrão"""
    tabela = Table(dados, colWidths=col_widths, repeatRows=1)
    
    estilo = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(cabecalho_cor)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), fonte_tamanho),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    
    for i in range(1, len(dados)):
        if i % 2 == 1:
            estilo.add('BACKGROUND', (0, i), (-1, i), colors.HexColor(COR_FUNDO_TABELA))
    
    tabela.setStyle(estilo)
    return tabela








def criar_pagina_validacao_conclusao(story, gestor, styles, normal_style, auditoria_id=None, 
                                     responsaveis=None, tipo_relatorio='conclusao'):
    """
    Adiciona a página de validação do relatório de conclusão com campos de assinatura
    """
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import KeepTogether
    
    # ⭐ TEXTO ESPECÍFICO PARA O RELATÓRIO DE CONCLUSÃO
    titulo_validacao = "VALIDACÃO DA CONCLUSÃO DA AUDITORIA"
    texto_declaracao = """
    
    """
    
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
    
    # ⭐ ESTILOS
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
        alignment=TA_CENTER,
        textColor=colors.HexColor('#999999'),
        spaceAfter=1
    )
    
    texto_declaracao_style = ParagraphStyle(
        'TextoDeclaracao',
        parent=normal_style,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    # ⭐ Função auxiliar para criar um bloco de assinatura
    def criar_bloco_assinatura(titulo, nome_padrao=None):
        """Cria um bloco com Nome, Data e Assinatura"""
        dados = []
        
        if nome_padrao:
            dados.append([
                Paragraph(f"<b>{titulo}:</b> {nome_padrao}", nome_style)
            ])
        else:
            dados.append([
                Paragraph(f"<b>{titulo}:</b> _________________________", nome_style)
            ])
        
        dados.append([
            Paragraph("<b>Data:</b> ____/____/________", rotulo_style)
        ])
        
        dados.append([
            Paragraph("___________________________________________", linha_assinatura_style)
        ])
        dados.append([
            Paragraph("<i>Assinatura</i>", ParagraphStyle(
                'AssinaturaLabel',
                parent=normal_style,
                fontSize=7,
                alignment=TA_CENTER,
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
    
    # ⭐ INÍCIO DA PÁGINA
    story.append(PageBreak())
    
    # Título principal
    story.append(Paragraph(titulo_validacao, styles['titulo']))
    story.append(Spacer(1, 5))
    
    # Texto de declaração
    story.append(Paragraph(texto_declaracao, texto_declaracao_style))
    story.append(Spacer(1, 10))
        
    # ============================================================
    # 2. RESPONSÁVEIS PELA AUDITORIA (da equipe)
    # ============================================================
    story.append(Paragraph("AUDITORES RESPONSÁVEIS PELA AUDITORIA", campo_titulo_style))
    story.append(Spacer(1, 2))
    
    if responsaveis and len(responsaveis) > 0:
        for idx, responsavel in enumerate(responsaveis, 1):
            story.append(criar_bloco_assinatura(f"Auditor", responsavel))
            story.append(Spacer(1, 4))
    else:
        # ⭐ Se não houver responsáveis, mostrar campos em branco
        story.append(criar_bloco_assinatura("Auditor"))
        story.append(Spacer(1, 4))
        story.append(criar_bloco_assinatura("Auditor"))
    
    story.append(Spacer(1, 8))
    
    # ============================================================
    # 3. GERENTE DE AUDITORIA INTERNA
    # ============================================================
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
            alignment=TA_CENTER,
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
    
    story.append(KeepTogether(gerente_content))

def contar_paginas_e_gerar_pdf(story, pagesize, topMargin, bottomMargin, leftMargin, rightMargin, 
                                rodape_func, cabecalho_func=None):
    """
    Conta as páginas de um story e gera o PDF com o total correto no rodapé.
    Retorna o PDF em bytes.
    """
    from reportlab.platypus import SimpleDocTemplate
    import io
    import copy
    
    print(f"📄 contar_paginas_e_gerar_pdf: story recebido com {len(story)} elementos")
    
    story_copy = copy.deepcopy(story)
    print(f"📄 story_copy criado com {len(story_copy)} elementos")
    
    try:
        # Primeira passada: contar páginas
        buffer_temp = io.BytesIO()
        doc_temp = SimpleDocTemplate(buffer_temp, pagesize=pagesize,
                                    topMargin=topMargin, bottomMargin=bottomMargin,
                                    leftMargin=leftMargin, rightMargin=rightMargin)
        
        page_counter = {'count': 0}
        
        def rodape_temp(canvas, doc):
            page_counter['count'] += 1
        
        print("📄 Construindo PDF temporário para contagem...")
        doc_temp.build(story_copy, onFirstPage=rodape_temp, onLaterPages=rodape_temp)
        total_paginas = page_counter['count']
        print(f"📄 Total de páginas: {total_paginas}")
        
        if total_paginas == 0:
            print("⚠️ ATENÇÃO: Nenhuma página foi contada!")
            total_paginas = 1
        
        # ⭐ RECRIAR A CÓPIA PARA A SEGUNDA PASSADA
        story_copy2 = copy.deepcopy(story)
        print(f"📄 story_copy2 criado com {len(story_copy2)} elementos")
        
        # Segunda passada: gerar o PDF final com o total
        buffer_final = io.BytesIO()
        doc_final = SimpleDocTemplate(buffer_final, pagesize=pagesize,
                                     topMargin=topMargin, bottomMargin=bottomMargin,
                                     leftMargin=leftMargin, rightMargin=rightMargin)
        
        def rodape_com_total(canvas, doc):
            # ⭐ A FUNÇÃO DE RODAPÉ JÁ TEM OS DADOS FIXOS DA GAI
            rodape_func(canvas, doc, total_paginas)
        
        print("📄 Gerando PDF final...")
        if cabecalho_func:
            doc_final.build(story_copy2, 
                           onFirstPage=lambda c, d: [cabecalho_func(c, d), rodape_com_total(c, d)],
                           onLaterPages=lambda c, d: [cabecalho_func(c, d), rodape_com_total(c, d)])
        else:
            doc_final.build(story_copy2, onFirstPage=rodape_com_total, onLaterPages=rodape_com_total)
        
        buffer_final.seek(0)
        pdf_bytes = buffer_final.getvalue()
        print(f"📄 PDF final gerado: {len(pdf_bytes)} bytes")
        
        if len(pdf_bytes) < 1000:
            print("⚠️ ATENÇÃO: PDF muito pequeno!")
            buffer_alt = io.BytesIO()
            doc_alt = SimpleDocTemplate(buffer_alt, pagesize=pagesize,
                                       topMargin=topMargin, bottomMargin=bottomMargin,
                                       leftMargin=leftMargin, rightMargin=rightMargin)
            doc_alt.build(story_copy2)
            buffer_alt.seek(0)
            pdf_bytes_alt = buffer_alt.getvalue()
            print(f"📄 PDF alternativo gerado: {len(pdf_bytes_alt)} bytes")
            if len(pdf_bytes_alt) > len(pdf_bytes):
                print("✅ PDF alternativo é maior! Usando ele.")
                return pdf_bytes_alt
        
        return pdf_bytes
        
    except Exception as e:
        print(f"❌ ERRO AO GERAR PDF: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    except Exception as e:
        print(f"❌ ERRO AO GERAR PDF: {e}")
        import traceback
        traceback.print_exc()
        raise

def buscar_processos_riscos_por_area(area_id, auditoria_id=None, processo_id=None):
    """
    Busca processos e seus riscos para uma área/auditoria
    Retorna lista de dicionários com processos e riscos
    """
    from database import engine
    from sqlalchemy import text
    import pandas as pd
    
    print(f"🔍 Buscando processos - area_id: {area_id}, auditoria_id: {auditoria_id}, processo_id: {processo_id}")
    
    if processo_id:
        query = text("""
            SELECT 
                p.id as processo_id,
                p.codigo_processo,
                p.nome_processo,
                p.objetivo,
                p.descricao,
                p.etapa_ini,
                p.etapa_fim,
                p.produto,
                -- ⭐ AGREGAR OS EXECUTORES DA TABELA processo_executores
                (
                    SELECT STRING_AGG(f.nome_funcionario, ', ' ORDER BY f.nome_funcionario)
                    FROM processo_executores pe
                    JOIN funcionarios_area f ON pe.funcionario_id = f.id
                    WHERE pe.processo_id = p.id
                ) AS executores,
                r.id as risco_id,
                r.nome_risco,
                r.fator_risco,
                r.categoria,
                r.causas,
                r.melhoria,
                r.impacto,
                r.probabilidade,
                r.motivo_risco,
                r.apetite_impacto,
                r.apetite_probabilidade,
                r.score_risco,
                r.tratamento_risco,
                r.descricao_tratamento,
                r.prazo_implantacao
            FROM processos p
            LEFT JOIN riscos r ON p.id = r.processo_id
            WHERE p.id_area = :area_id
                AND p.status = 'Ativo'
                AND p.id = :processo_id
            ORDER BY p.codigo_processo, r.nome_risco
        """)
        params = {"area_id": area_id, "processo_id": processo_id}
    else:
        query = text("""
            SELECT 
                p.id as processo_id,
                p.codigo_processo,
                p.nome_processo,
                p.objetivo,
                p.descricao,
                p.etapa_ini,
                p.etapa_fim,
                p.produto,
                -- ⭐ AGREGAR OS EXECUTORES DA TABELA processo_executores
                (
                    SELECT STRING_AGG(f.nome_funcionario, ', ' ORDER BY f.nome_funcionario)
                    FROM processo_executores pe
                    JOIN funcionarios_area f ON pe.funcionario_id = f.id
                    WHERE pe.processo_id = p.id
                ) AS executores,
                r.id as risco_id,
                r.nome_risco,
                r.fator_risco,
                r.categoria,
                r.causas,
                r.melhoria,
                r.impacto,
                r.probabilidade,
                r.motivo_risco,
                r.apetite_impacto,
                r.apetite_probabilidade,
                r.score_risco,
                r.tratamento_risco,
                r.descricao_tratamento,
                r.prazo_implantacao
            FROM processos p
            LEFT JOIN riscos r ON p.id = r.processo_id
            WHERE p.id_area = :area_id
                AND p.status = 'Ativo'
                AND p.auditoria_id = :auditoria_id
            ORDER BY p.codigo_processo, r.nome_risco
        """)
        params = {"area_id": area_id, "auditoria_id": auditoria_id}
    
    print(f"🔍 Executando query com params: {params}")
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)
    
    print(f"📊 Query retornou {len(df)} linhas")
    
    if df.empty:
        print("❌ Nenhum dado encontrado!")
        return []
    
    # Mostrar primeiras linhas para debug
    print(f"📋 Colunas: {df.columns.tolist()}")
    print(f"📋 Primeiras linhas:\n{df.head()}")
    
    # Organizar dados por processo
    processos_dict = {}
    for _, row in df.iterrows():
        proc_id = row['processo_id']
        if proc_id not in processos_dict:
            processos_dict[proc_id] = {
                'processo_id': proc_id,
                'codigo_processo': row['codigo_processo'],
                'nome_processo': row['nome_processo'],
                'objetivo': row['objetivo'],
                'executor': row.get('executores', ''),  # ⭐ USAR O CAMPO AGREGADO
                'descricao': row['descricao'],
                'etapa_ini': row['etapa_ini'],
                'etapa_fim': row['etapa_fim'],
                'produto': row['produto'],
                'riscos': []
            }
        
        if pd.notna(row['risco_id']):
            risco = {
                'risco_id': row['risco_id'],
                'nome_risco': row['nome_risco'],
                'fator_risco': row['fator_risco'],
                'categoria': row['categoria'],
                'causas': row['causas'],
                'melhoria': row['melhoria'],
                'impacto': row['impacto'],
                'probabilidade': row['probabilidade'],
                'motivo_risco': row['motivo_risco'],
                'apetite_impacto': row['apetite_impacto'],
                'apetite_probabilidade': row['apetite_probabilidade'],
                'score_risco': row['score_risco'],
                'tratamento_risco': row['tratamento_risco'],
                'descricao_tratamento': row['descricao_tratamento'],
                'prazo_implantacao': row['prazo_implantacao'],
                'risco_residual': calcular_risco_residual(
                    row['apetite_impacto'], 
                    row['apetite_probabilidade']
                )
            }
            processos_dict[proc_id]['riscos'].append(risco)
    
    # ⭐ CORREÇÃO: Para processos sem executores, definir valor padrão
    for proc_id, proc_data in processos_dict.items():
        if not proc_data.get('executor') or proc_data['executor'] is None:
            proc_data['executor'] = 'Não informado'
    
    print(f"✅ Retornando {len(processos_dict)} processos")
    return list(processos_dict.values())



# ============================================================
# ====== FIM FUNÇÕES AUXILIARES PARA RELATÓRIOS ======
# ============================================================

def gerar_validacao_relatorio_panorama(area_id, area_nome, gestor, cargo, orientacao="RETRATO", auditoria_id=None, processo_id=None, titulo_auditoria=None):

    """
    Gera relatório de validação - Matriz Panorama
    Contém: informações da área, funcionários, processos e riscos
    """

    from datetime import datetime
    from zoneinfo import ZoneInfo
    import io
    import os
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

    print(f"🔍 Iniciando geração do relatório Panorama...")
    print(f"   area_id: {area_id}")
    print(f"   area_nome: {area_nome}")
    print(f"   auditoria_id: {auditoria_id}")
    print(f"   processo_id: {processo_id}")

    buffer = io.BytesIO()
    TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")

    # Definir orientação da página
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
    
    # Estilos
    styles = get_estilos_padrao()
    normal_style = styles['normal']

    paragraph_style = ParagraphStyle(
        'CustomParagraph',
        parent=normal_style,
        fontSize=10,
        alignment=1,  # CENTRO
        spaceAfter=10,
        textColor=colors.HexColor('#0b5b99')
    )

    titulo_final = titulo_auditoria  # Começa com o que veio como parâmetro
    
    if titulo_final is None and auditoria_id:
        # Se não veio como parâmetro, buscar do banco
        try:
            from database import engine
            from sqlalchemy import text
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
    elif titulo_final is None:
        titulo_final = 'Auditoria'
    
    # ===== CONSTRUIR O STORY =====
    story = []

    criar_pagina_capa(
        story=story,
        pagesize=pagesize,
        titulo_relatorio='RELATÓRIO DE VALIDAÇÃO<br/>MATRIZ DE PANORAMA',
        subtitulo_relatorio=f'{titulo_final}',
        area_nome=area_nome,
        data_emissao=datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    )
    
    # ===== 1. BUSCAR DADOS DA ÁREA =====
    dados_area = buscar_area_por_id(area_id)
    if not dados_area:
        raise Exception(f"Área {area_id} não encontrada")
    
    area_nome = dados_area.get('nome_area', area_nome)
    area_unidade = dados_area.get('loc_unidade', 'Não informado')
    area_objetivo = dados_area.get('objetivo_area', 'Não informado')
    area_superintendente = dados_area.get('superintendente', 'Não informado')
    area_diretor = dados_area.get('diretor', 'Não informado')
    area_gestor = dados_area.get('gestor', gestor)
    area_cargo = dados_area.get('cargo', cargo)
    area_email = dados_area.get('email', 'Não informado')
    area_telefone = dados_area.get('telefone', 'Não informado')
    
    # ===== 2. BUSCAR FUNCIONÁRIOS DA ÁREA =====
    funcionarios_df = listar_funcionarios_area_todos(area_id)
    
    # ===== 3. BUSCAR PROCESSOS E RISCOS =====
    processos_riscos = buscar_processos_riscos_por_area(area_id, auditoria_id, processo_id)
    
    if not processos_riscos:
        raise Exception("Nenhum processo encontrado para os critérios selecionados.")
    
     # ===== 4. MONTAR O RELATÓRIO =====
    
    # ===== 4a. CABEÇALHO COM LOGOS =====
    root_dir = os.path.dirname(os.path.abspath(__file__))
    logo_auditoria_path = os.path.join(root_dir, "static", "assets", "logo_auditoria_recortada_circulo2.png")

    header_data = []
    tem_logo = os.path.exists(logo_auditoria_path)

    # if tem_logo:
    #     img_central = Image(logo_auditoria_path, width=2*cm, height=2*cm)
    #     header_data = [[img_central]]
    #     header_table = Table(header_data, colWidths=[pagesize[0] - leftMargin - rightMargin])
    #     header_table.setStyle(TableStyle([
    #         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    #         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    #         ('BOTTOMPADDING', (0, 0), (-1, -1), -5),
    #     ]))
    #     story.append(header_table)
    #     story.append(Spacer(1, 10))
    
    print(f"📄 Após cabeçalho: {len(story)} elementos")

    # ===== 4b. TÍTULO =====
    titulo_style = styles['titulo']
    titulo_style2 = styles['titulo2']
    titulo_style0 = styles['titulo0']

    # # ⭐ CABEÇALHO MAPA
    # story.append(Paragraph("MAPA", titulo_style))
    # story.append(Spacer(0, 0))
    # story.append(Paragraph("Mapeamento, Auditoria e Processos Avaliados", paragraph_style))
    # story.append(Spacer(1, 2))

    # ⭐ TÍTULO PRINCIPAL
    story.append(Paragraph("Relatório de Validação", titulo_style0))
    story.append(Paragraph("Matriz de Panorama", titulo_style0))
    story.append(Spacer(1, 5))

    print(f"📄 Após título: {len(story)} elementos")
    
    # Substitua as seções 4c e 4d por:
    contra_capa_relatorio(
        story=story,
        styles=styles,
        normal_style=normal_style,
        pagesize=pagesize,
        leftMargin=leftMargin,
        rightMargin=rightMargin,
        auditoria_id=auditoria_id,
        processo_id=processo_id,
        area_id=area_id,
        area_nome=area_nome,
        gestor=area_gestor,
        cargo=area_cargo,
        titulo_auditoria=titulo_final
    )

    # ===== 4e. FUNCIONÁRIOS DA ÁREA =====
    story.append(Paragraph("Funcionários da Área", styles['subtitulo']))
    story.append(Spacer(1, 2))
    
    if not funcionarios_df.empty:
        # Converter DataFrame para lista de dicionários
        funcionarios = funcionarios_df.to_dict('records')
        func_data = [["Nome", "Cargo"]]
        for f in funcionarios:
            func_data.append([
                Paragraph(f.get('nome_funcionario', '-'), normal_style),
                Paragraph(f.get('cargo', '-'), normal_style)
            ])
        
        func_table = criar_tabela_estilizada(func_data, [8*cm, 8*cm])
        story.append(func_table)
    else:
        story.append(Paragraph("<i>Nenhum funcionário cadastrado para esta área.</i>", normal_style))
    
    story.append(PageBreak())

    print(f"📄 Após funcionários: {len(story)} elementos")

    # ===== 4f. PROCESSOS E RISCOS (CARDS POR PROCESSO) =====
    story.append(Paragraph("Processos e Riscos Identificados", styles['subtitulo']))
    story.append(Spacer(1, 5))
    
    # Contar total de riscos
    total_riscos = sum(len(p.get('riscos', [])) for p in processos_riscos)
    story.append(Paragraph(f"Total de Processos: {len(processos_riscos)} | Total de Riscos: {total_riscos}", normal_style))
    story.append(Spacer(1, 10))
    
    # ⭐ CALCULAR A LARGURA DISPONÍVEL PARA O CARD
    largura_disponivel = pagesize[0] - leftMargin - rightMargin - 2*cm  # 2cm de padding interno
    
    # Estilos
    card_titulo_style = ParagraphStyle(
        'CardTitulo',
        parent=normal_style,
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=5
    )
    
    card_subtitulo_style = ParagraphStyle(
        'CardSubtitulo',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0b5b99'),
        spaceAfter=3
    )
    
    card_texto_style = ParagraphStyle(
        'CardTexto',
        parent=normal_style,
        fontSize=8,
        leading=10,
        leftIndent=10,
        alignment=TA_JUSTIFY
    )

    card_texto_style = ParagraphStyle(
        'CardTexto',
        parent=normal_style,
        fontSize=8,
        leading=10,
        leftIndent=10
    )
    
    # ⭐ ADICIONAR ESTES DOIS ESTILOS
    risco_titulo_style = ParagraphStyle(
        'RiscoTitulo',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        leftIndent=15,
        spaceAfter=2
    )
    
    risco_item_style = ParagraphStyle(
        'RiscoItem',
        parent=normal_style,
        fontSize=8,
        leading=10,
        leftIndent=30
    )
    
    normal_style_pequeno = ParagraphStyle(
        'NormalPequeno',
        parent=normal_style,
        fontSize=7,
        leading=9
    )
    
    # Função para obter emoji do risco
    def get_emoji_risco(score):
        if score is None:
            return ""
        elif score >= 12:
            return ""
        elif score >= 8:
            return ""
        elif score >= 4:
            return ""
        else:
            return ""
    
    # Para cada processo
    for idx, proc in enumerate(processos_riscos):
        # Quebra de página a cada 3 processos
        if idx > 0 and idx % 3 == 0:
            story.append(PageBreak())
        
        codigo = proc.get('codigo_processo', '-')
        nome = proc.get('nome_processo', '-')
        riscos = proc.get('riscos', [])
        
        # ⭐ CONTEÚDO DO CARD (uma lista de elementos)
        conteudo_card = []
        
        # Cabeçalho do processo
        conteudo_card.append(
            Paragraph(f"<b>Processo {codigo}: {nome}</b>", card_titulo_style)
        )
        conteudo_card.append(Spacer(1, 3))
        
        # ⭐ INFORMAÇÕES DO PROCESSO (UMA TABELA COM LARGURA AJUSTADA)
        info_processo = []
        
        # Criar estilo com wordWrap para quebra de linha
        texto_processo_style = ParagraphStyle(
            'TextoProcesso',
            parent=normal_style,
            fontSize=8,
            leading=10,
            wordWrap='CJK'  # ⭐ FORÇA QUEBRA DE LINHA
        )

        # ⭐ EXECUTOR - SEMPRE MOSTRAR, MESMO SE VAZIO
        executor_valor = proc.get('executor') or 'Não informado'
        info_processo.append([
            Paragraph("<b>Quem executa o Processo?</b>", card_texto_style),
            Paragraph(executor_valor, texto_processo_style)
        ])

        if proc.get('descricao'):
            info_processo.append([
                Paragraph("<b>O que é o Processo?</b>", card_texto_style),
                Paragraph(proc['descricao'], texto_processo_style)  # ⭐ SEM TRUNCAMENTO
            ])

        if proc.get('etapa_ini'):
            info_processo.append([
                Paragraph("<b>Onde  começa o Processo?</b>", card_texto_style),
                Paragraph(proc['etapa_ini'], texto_processo_style)
            ])

        if proc.get('produto'):
            info_processo.append([
                Paragraph("<b>Qual o produto final desse Processo?</b>", card_texto_style),
                Paragraph(proc['produto'], texto_processo_style)
            ])

        if proc.get('etapa_fim'):
            info_processo.append([
                Paragraph("<b>Depois de acabado, para onde envia?</b>", card_texto_style),
                Paragraph(proc['etapa_fim'], texto_processo_style)
            ])
        
        if proc.get('objetivo'):
            info_processo.append([
                Paragraph("<b>Qual o objetivo do Processo? E por que faz?:</b>", card_texto_style),
                Paragraph(proc['objetivo'], texto_processo_style)  
            ])
      
        if info_processo:
            # ⭐ LARGURA AJUSTADA PARA O CARD
            largura_label = 3.0 * cm
            largura_valor = largura_disponivel - largura_label - 1*cm
            
            info_table = Table(info_processo, colWidths=[largura_label, largura_valor])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#DDDDDD')),
            ]))
            conteudo_card.append(info_table)
            conteudo_card.append(Spacer(1, 5))
        
                # ⭐ RISCOS DO PROCESSO (CARDS INDIVIDUAIS)
        if riscos:
            conteudo_card.append(Paragraph(f"<b>Riscos ({len(riscos)})</b>", card_subtitulo_style))
            conteudo_card.append(Spacer(1, 3))
            
            # Para cada risco, criar um card interno
            for risco_idx, risco in enumerate(riscos):
                # Card do risco com borda colorida
                risco_conteudo = []
                
                # Cabeçalho do risco com emoji e nome
                score = risco.get('score_risco')
                emoji = get_emoji_risco(score)
                nome_risco = risco.get('nome_risco', 'Risco não nomeado')
                
                risco_conteudo.append(
                    Paragraph(f"{emoji} <b>Risco {risco_idx + 1}: {nome_risco}</b>", risco_titulo_style)
                )
                risco_conteudo.append(Spacer(1, 2))
                
                # Informações do risco em grade (2 colunas)
                info_risco = []
                
                # Criar estilo com wordWrap para quebra de linha
                texto_risco_style = ParagraphStyle(
                    'TextoRisco',
                    parent=normal_style,
                    fontSize=8,
                    leading=10,
                    wordWrap='CJK'  # ⭐ FORÇA QUEBRA DE LINHA
                )

                if risco.get('categoria'):
                    info_risco.append([
                        Paragraph("<b>Categoria do Risco:</b>", risco_item_style),
                        Paragraph(risco['categoria'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                # Coluna: Fator de Risco, Categoria, Causas
                if risco.get('fator_risco'):
                    info_risco.append([
                        Paragraph("<b>Fator de Risco:</b>", risco_item_style),
                        Paragraph(risco['fator_risco'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                
                if risco.get('causas'):
                    info_risco.append([
                        Paragraph("<b>Categoria de Causa:</b>", risco_item_style),
                        Paragraph(risco['causas'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                if risco.get('melhoria'):
                    info_risco.append([
                        Paragraph("<b>O que mais incomoda no processo e que deveria melhorar?:</b>", risco_item_style),
                        Paragraph(risco['melhoria'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                # Coluna 2: Impacto, Probabilidade, Motivo
                if risco.get('impacto'):
                    info_risco.append([
                        Paragraph("<b>Impacto:</b>", risco_item_style),
                        Paragraph(risco['impacto'], texto_risco_style)
                    ])
                
                if risco.get('probabilidade'):
                    info_risco.append([
                        Paragraph("<b>Probabilidade:</b>", risco_item_style),
                        Paragraph(risco['probabilidade'], texto_risco_style)
                    ])
                
                if risco.get('motivo_risco'):
                    info_risco.append([
                        Paragraph("<b>Motivo da Classificação da Probabilidade:</b>", risco_item_style),
                        Paragraph(risco['motivo_risco'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                # Apetite ao Risco
                if risco.get('apetite_impacto') or risco.get('apetite_probabilidade'):
                    apetite_texto = f"Impacto: {risco.get('apetite_impacto', '-')} | Probabilidade: {risco.get('apetite_probabilidade', '-')}"
                    info_risco.append([
                        Paragraph("<b>Apetite ao Risco:</b>", risco_item_style),
                        Paragraph(apetite_texto, texto_risco_style)
                    ])
                
                # Scores
                texto_score = str(int(score)) if score is not None else "-"
                residual = risco.get('risco_residual')
                texto_residual = str(int(residual)) if residual is not None else "-"
                
                info_risco.append([
                    Paragraph("<b>Magnitude do Risco (Risco Bruto):</b>", risco_item_style),
                    Paragraph(f"{emoji} {texto_score}", texto_risco_style)
                ])
                
                info_risco.append([
                    Paragraph("<b>Risco Residual:</b>", risco_item_style),
                    Paragraph(texto_residual, texto_risco_style)
                ])
                
                # Tratamento
                if risco.get('tratamento_risco'):
                    info_risco.append([
                        Paragraph("<b>Como Tratar o Risco?:</b>", risco_item_style),
                        Paragraph(risco['tratamento_risco'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                if risco.get('descricao_tratamento'):
                    info_risco.append([
                        Paragraph("<b>Descrição do Tratamento:</b>", risco_item_style),
                        Paragraph(risco['descricao_tratamento'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                if risco.get('prazo_implantacao'):
                    info_risco.append([
                        Paragraph("<b>Prazo para Implementação da Descrição do Tratamento:</b>", risco_item_style),
                        Paragraph(risco['prazo_implantacao'], texto_risco_style)
                    ])
                
                # Criar tabela 2 colunas para as informações do risco
                if info_risco:
                    # Calcular larguras dinamicamente
                    largura_label_risco = 4.0 * cm  # Largura fixa para os labels
                    largura_valor_risco = largura_disponivel - 2*cm - largura_label_risco - 1*cm
                    
                    # Garantir que a largura do valor não fique negativa
                    if largura_valor_risco < 4*cm:
                        largura_valor_risco = 4*cm
                        largura_label_risco = largura_disponivel - 2*cm - largura_valor_risco - 1*cm
                        if largura_label_risco < 3*cm:
                            largura_label_risco = 3*cm
                    
                    info_risco_table = Table(info_risco, colWidths=[largura_label_risco, largura_valor_risco])
                    info_risco_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFF8F0')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#EEEEEE')),
                    ]))
                    risco_conteudo.append(info_risco_table)
                
                # Criar o card do risco com borda colorida
                largura_risco_card = largura_disponivel - 2*cm
                
                # Garantir largura mínima
                if largura_risco_card < 10*cm:
                    largura_risco_card = 10*cm
                
                risco_card = Table([[item] for item in risco_conteudo], colWidths=[largura_risco_card])
                
                # Cor da borda baseada no score
                if score is None:
                    cor_borda = '#CCCCCC'
                elif score >= 12:
                    cor_borda = '#dc3545'  # Vermelho
                elif score >= 8:
                    cor_borda = '#fd7e14'  # Laranja
                elif score >= 4:
                    cor_borda = '#ffc107'  # Amarelo
                else:
                    cor_borda = '#28a745'  # Verde
                
                risco_card.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.99, 0.97, 0.95, alpha=0.40)),
                    ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor(cor_borda)),
                    ('ROUNDEDCORNERS', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                conteudo_card.append(risco_card)
                conteudo_card.append(Spacer(1, 5))
        else:
            conteudo_card.append(Paragraph("<i>Nenhum risco cadastrado para este processo.</i>", normal_style))
        
        # ⭐ CRIAR O CARD COM TODOS OS ELEMENTOS

        card_conteudo = []
        for item in conteudo_card:
            if isinstance(item, Spacer):
                card_conteudo.append([item])
            else:
                card_conteudo.append([item])
        
        # ⭐ LARGURA DINÂMICA DO CARD
        largura_card_principal = largura_disponivel
        
        card_table = Table(card_conteudo, colWidths=[largura_card_principal])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.97, 0.97, 0.97, alpha=0.60)),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ('ROUNDEDCORNERS', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(card_table)
        story.append(Spacer(1, 10))

    print(f"📄 Após processos e riscos: {len(story)} elementos")

    # ===== 4g. PÁGINA DE VALIDAÇÃO DO GESTOR =====
    entrevistado = None
    if processo_id:
        try:
            with engine.connect() as conn:
                query_entrevistado = text("""
                    SELECT entrevistado FROM processos WHERE id = :processo_id
                """)
                result = conn.execute(query_entrevistado, {"processo_id": processo_id}).fetchone()
                if result and result[0]:
                    entrevistado = result[0]
        except Exception as e:
            print(f"⚠️ Erro ao buscar entrevistado: {e}")

    criar_pagina_validacao(
        story=story,
        gestor=area_gestor,
        styles=styles,
        normal_style=normal_style,
        auditoria_id=auditoria_id,
        tipo_relatorio='panorama',
        entrevistado=entrevistado  # ⭐ PASSA O ENTREVISTADO
    )
    print(f"📄 Após validação: {len(story)} elementos")
    
    # ⭐ VERIFICAR SE O STORY TEM CONTEÚDO ANTES DE GERAR O PDF
    print(f"📄 Story FINAL tem {len(story)} elementos")
    if story:
        print("✅ Story NÃO está vazio!")
        print(f"   Primeiro elemento: {type(story[0]).__name__}")
        print(f"   Último elemento: {type(story[-1]).__name__}")
    else:
        print("❌ Story está vazio! Verifique o código.")
        raise Exception("Story vazio - nenhum conteúdo foi adicionado ao relatório")
    
    # ===== BUSCAR DADOS DA GERÊNCIA DE AUDITORIA INTERNA (FIXOS) =====
    dados_gai = buscar_dados_gerencia_auditoria()
    email_gai = dados_gai['email']
    telefone_gai = dados_gai['telefone']
    
    # ===== 5. GERAR O PDF =====
    def rodape_panorama(canvas, doc, total_paginas):
        """Rodapé específico do relatório Panorama"""
        titulo_rodape = f"Relatório de Validação Matriz de Panorama - {area_nome[:50]}"
        criar_rodape(canvas, doc, pagesize, total_paginas, titulo_rodape, 
                     email_auditoria=email_gai,      # ⬅️ Email da GAI (fixo)
                     telefone_auditoria=telefone_gai) # ⬅️ Telefone da GAI (fixo)
    
    pdf_bytes = contar_paginas_e_gerar_pdf(
        story=story,
        pagesize=pagesize,
        topMargin=topMargin,
        bottomMargin=bottomMargin,
        leftMargin=leftMargin,
        rightMargin=rightMargin,
        rodape_func=rodape_panorama,
        cabecalho_func=None
    )
    
    print(f"📄 PDF gerado! Tamanho: {len(pdf_bytes)} bytes")
    
    # # ⭐ SALVAR O PDF PARA INSPEÇÃO (APENAS PARA TESTE)
    # with open("teste_panorama.pdf", "wb") as f:
    #     f.write(pdf_bytes)
    # print("📄 PDF salvo como 'teste_panorama.pdf'")
    
    return pdf_bytes

# ============================================================
# ====== RELATÓRIO DE VALIDAÇÃO - DETALHAMENTO ======
# ============================================================


def gerar_validacao_relatorio_detalhamento(area_id, area_nome, gestor, cargo, orientacao="RETRATO", auditoria_id=None, processo_id=None, titulo_auditoria=None):
    """
    Gera relatório de validação - Matriz Detalhamento
    Contém: informações da área, funcionários, processos, etapas, riscos e controles
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
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
    import pandas as pd
    
    print(f"🔍 Iniciando geração do relatório Detalhamento...")
    print(f"   area_id: {area_id}")
    print(f"   area_nome: {area_nome}")
    print(f"   auditoria_id: {auditoria_id}")
    print(f"   processo_id: {processo_id}")
    
    buffer = io.BytesIO()
    TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
    
    # Definir orientação da página
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
    
    # ⭐ 1. PRIMEIRO: DEFINIR normal_style
    styles = get_estilos_padrao()
    normal_style = styles['normal']

    paragraph_style = ParagraphStyle(
        'CustomParagraph',
        parent=normal_style,
        fontSize=10,
        alignment=1,  # CENTRO
        spaceAfter=10,
        textColor=colors.HexColor('#0b5b99')
    )
    
    # ⭐ 2. DEPOIS: DEFINIR OS ESTILOS QUE DEPENDEM DE normal_style
    
    # ⭐ ESTILO PARA TÍTULOS DE SEÇÃO
    secao_titulo_style = ParagraphStyle(
        'SecaoTitulo',
        parent=normal_style,
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=5,
        spaceBefore=10
    )

    # ⭐ ESTILO PARA LINHA DIVISÓRIA
    linha_divisoria_style = ParagraphStyle(
        'LinhaDivisoria',
        parent=normal_style,
        fontSize=1,
        textColor=colors.HexColor('#CCCCCC'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    # ⭐ ESTILO PARA SUBSEÇÃO (RISCOS, CONTROLES)
    subsecao_titulo_style = ParagraphStyle(
        'SubsecaoTitulo',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0b5b99'),
        spaceAfter=3,
        spaceBefore=5,
        leftIndent=10
    )
    
    # ⭐ ESTILO PARA ITENS (CONTROLES)
    item_style = ParagraphStyle(
        'ItemStyle',
        parent=normal_style,
        fontSize=8,
        leading=10,
        leftIndent=20
    )

    titulo_final = titulo_auditoria  # Começa com o que veio como parâmetro
    
    if titulo_final is None and auditoria_id:
        # Se não veio como parâmetro, buscar do banco
        try:
            from database import engine
            from sqlalchemy import text
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
    elif titulo_final is None:
        titulo_final = 'Auditoria'

    
    # ===== CONSTRUIR O STORY =====
    story = []

    criar_pagina_capa(
        story=story,
        pagesize=pagesize,
        titulo_relatorio="RELATÓRIO DE VALIDAÇÃO<br/>MATRIZ DE DETALHAMENTO",
        subtitulo_relatorio=f"{titulo_final}",
        area_nome=area_nome,
        data_emissao=datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    )
    
    # ===== 1. BUSCAR DADOS DA ÁREA =====
    dados_area = buscar_area_por_id(area_id)
    if not dados_area:
        raise Exception(f"Área {area_id} não encontrada")
    
    area_nome = dados_area.get('nome_area', area_nome)
    area_unidade = dados_area.get('loc_unidade', 'Não informado')
    area_objetivo = dados_area.get('objetivo_area', 'Não informado')
    area_superintendente = dados_area.get('superintendente', 'Não informado')
    area_diretor = dados_area.get('diretor', 'Não informado')
    area_gestor = dados_area.get('gestor', gestor)
    area_cargo = dados_area.get('cargo', cargo)
    area_email = dados_area.get('email', 'Não informado')
    area_telefone = dados_area.get('telefone', 'Não informado')
    
    # ===== 2. BUSCAR FUNCIONÁRIOS DA ÁREA =====
    funcionarios_df = listar_funcionarios_area_todos(area_id)
    
    # ===== 3. BUSCAR PROCESSOS =====
    processos = buscar_processos_detalhamento(area_id, auditoria_id, processo_id)
    
    if not processos:
        raise Exception("Nenhum processo encontrado para os critérios selecionados.")
    
    # ===== 4. MONTAR O RELATÓRIO =====
    
    # ===== 4a. CABEÇALHO COM LOGOS =====
    root_dir = os.path.dirname(os.path.abspath(__file__))
    logo_auditoria_path = os.path.join(root_dir, "static", "assets", "logo_auditoria_circulo.png")

    header_data = []
    tem_logo = os.path.exists(logo_auditoria_path)

    # if tem_logo:
    #     img_central = Image(logo_auditoria_path, width=2*cm, height=2*cm)
    #     header_data = [[img_central]]
    #     header_table = Table(header_data, colWidths=[pagesize[0] - leftMargin - rightMargin])
    #     header_table.setStyle(TableStyle([
    #         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    #         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    #         ('BOTTOMPADDING', (0, 0), (-1, -1), -5),
    #     ]))
    #     story.append(header_table)
    #     story.append(Spacer(1, 10))
    
    # ===== 4b. TÍTULO =====
    titulo_style = styles['titulo']
    titulo_style2 = styles['titulo2']
    titulo_style0 = styles['titulo0']

    # # ⭐ CABEÇALHO MAPA
    # story.append(Paragraph("MAPA", titulo_style))
    # story.append(Spacer(0, 0))
    # story.append(Paragraph("Mapeamento, Auditoria e Processos Avaliados", paragraph_style))
    # story.append(Spacer(1, 2))

    # ⭐ TÍTULO PRINCIPAL
    story.append(Paragraph("Relatório de Validação", titulo_style0))
    story.append(Paragraph("Matriz de Detalhamento", titulo_style0))
    story.append(Spacer(1, 5))
    
    contra_capa_relatorio(
        story=story,
        styles=styles,
        normal_style=normal_style,
        pagesize=pagesize,
        leftMargin=leftMargin,
        rightMargin=rightMargin,
        auditoria_id=auditoria_id,
        processo_id=processo_id,
        area_id=area_id,
        area_nome=area_nome,
        gestor=gestor,
        cargo=cargo,
        titulo_auditoria=titulo_final
    )
    
    # ===== 4e. FUNCIONÁRIOS DA ÁREA =====
    story.append(Paragraph("Funcionários da Área", styles['subtitulo']))
    story.append(Spacer(1, 2))
    
    if not funcionarios_df.empty:
        funcionarios = funcionarios_df.to_dict('records')
        func_data = [["Nome", "Cargo"]]
        for f in funcionarios:
            func_data.append([
                Paragraph(f.get('nome_funcionario', '-'), normal_style),
                Paragraph(f.get('cargo', '-'), normal_style)
            ])
        
        func_table = criar_tabela_estilizada(func_data, [8*cm, 8*cm])
        story.append(func_table)
    else:
        story.append(Paragraph("<i>Nenhum funcionário cadastrado para esta área.</i>", normal_style))
    
    story.append(PageBreak())
    
    # ===== 4f. PROCESSOS COM DETALHAMENTO =====
    story.append(Paragraph("Detalhamento dos Processos", styles['subtitulo']))
    story.append(Spacer(1, 5))
    
    largura_disponivel = pagesize[0] - leftMargin - rightMargin - 2*cm
    
    # ⭐ ESTILOS PARA O RELATÓRIO DE DETALHAMENTO
    card_titulo_style = ParagraphStyle(
        'CardTitulo',
        parent=normal_style,
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=5
    )
    
    card_subtitulo_style = ParagraphStyle(
        'CardSubtitulo',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0b5b99'),
        spaceAfter=3
    )
    
    card_texto_style = ParagraphStyle(
        'CardTexto',
        parent=normal_style,
        fontSize=8,
        leading=10,
        leftIndent=10,
        alignment=TA_JUSTIFY
    )
    
    texto_risco_style = ParagraphStyle(
        'TextoRisco',
        parent=normal_style,
        fontSize=8,
        leading=10,
        wordWrap='CJK'
    )
    
    texto_controle_style = ParagraphStyle(
        'TextoControle',
        parent=normal_style,
        fontSize=7.5,
        leading=9,
        wordWrap='CJK',
        alignment=TA_JUSTIFY
    )
    
    texto_etapa_style = ParagraphStyle(
        'TextoEtapa',
        parent=normal_style,
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        alignment=TA_JUSTIFY,
        leftIndent=10
    )
    
    texto_processo_style = ParagraphStyle(
        'TextoProcesso',
        parent=normal_style,
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        alignment= TA_JUSTIFY
    )
    
    # Função para limitar texto
    def limitar_texto(texto, limite=80):
        if not texto:
            return ''
        texto = ' '.join(texto.split())
        if len(texto) <= limite:
            return texto
        espaco = texto.rfind(' ', 0, limite)
        if espaco > 0:
            return texto[:espaco] + '...'
        return texto[:limite] + '...'
    
    # Função para obter emoji do risco
    def get_emoji_risco(magnitude):
        if magnitude is None:
            return ""
        elif magnitude >= 12:
            return ""
        elif magnitude >= 8:
            return ""
        elif magnitude >= 4:
            return ""
        else:
            return ""
    
    # Para cada processo
    
    for proc_idx, proc in enumerate(processos):
        if proc_idx > 0:
            story.append(PageBreak())
        
        # ⭐ CORREÇÃO: Acessar os campos corretamente (agora são dicionários, não objetos)
        codigo = proc.get('codigo_processo', '-')
        nome = proc.get('nome_processo', '-')
        etapas = proc.get('etapas', [])
        
        print(f"📋 Processo: {codigo} - {nome}")
        print(f"   Etapas encontradas: {len(etapas)}")
        
        # ============================================================
        # CABEÇALHO DO PROCESSO
        # ============================================================
        story.append(Paragraph(f"<b>PROCESSO {codigo}: {nome}</b>", card_titulo_style))
        story.append(Spacer(1, 3))
        
        # Informações do processo
        info_processo = []
        
        if proc.get('objetivo'):
            info_processo.append([
                Paragraph("<b>Objetivo:</b>", card_texto_style),
                Paragraph(limitar_texto(proc['objetivo'], 10000), texto_processo_style)
            ])
        
        if proc.get('descricao'):
            info_processo.append([
                Paragraph("<b>Descrição:</b>", card_texto_style),
                Paragraph(limitar_texto(proc['descricao'], 10000), texto_processo_style)
            ])
        
        executor_valor = proc.get('executor') or 'Não informado'
        info_processo.append([
            Paragraph("<b>Executor(es):</b>", card_texto_style),
            Paragraph(executor_valor, texto_processo_style)
        ])
        
        if proc.get('etapa_ini'):
            info_processo.append([
                Paragraph("<b>Início:</b>", card_texto_style),
                Paragraph(proc['etapa_ini'], texto_processo_style)
            ])
        
        if proc.get('produto'):
            info_processo.append([
                Paragraph("<b>Produto:</b>", card_texto_style),
                Paragraph(proc['produto'], texto_processo_style)
            ])
        
        if proc.get('etapa_fim'):
            info_processo.append([
                Paragraph("<b>Fim:</b>", card_texto_style),
                Paragraph(proc['etapa_fim'], texto_processo_style)
            ])
        
        
        if info_processo:
            largura_label = 3.0 * cm
            largura_valor = largura_disponivel - largura_label - 1*cm
            
            info_table = Table(info_processo, colWidths=[largura_label, largura_valor])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#DDDDDD')),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 8))
        
        # ============================================================
        # ETAPAS DO PROCESSO
        # ============================================================
        if not etapas:
            story.append(Paragraph("<i>Nenhuma etapa cadastrada para este processo.</i>", normal_style))
            print(f"Nenhuma etapa para o processo {codigo}")
        else:
            for etapa_idx, etapa in enumerate(etapas):
                # ⭐ CORREÇÃO: Acessar os campos do dicionário
                etapa_codigo = etapa.get('codigo_etapa', '')
                etapa_nome = etapa.get('nome_etapa', 'Etapa sem nome')
                
                print(f"   Etapa {etapa_codigo}: {etapa_nome}")
                
                # ⭐ SEPARADOR ENTRE ETAPAS
                if etapa_idx > 0:
                    story.append(Paragraph("─" * 80, linha_divisoria_style))
                    story.append(Spacer(1, 5))
                
                # ⭐ TÍTULO DA ETAPA
                etapa_codigo = etapa.get('codigo_etapa', '')
                etapa_nome = etapa.get('nome_etapa', 'Etapa sem nome')
                
                story.append(Paragraph(f"<b>Etapa {etapa_codigo}: {etapa_nome}</b>", card_subtitulo_style))
                story.append(Spacer(1, 2))
                
                # Informações da etapa
                info_etapa = []
                
                if etapa.get('descricao_etapa'):
                    info_etapa.append([
                        Paragraph("<b>Descrição:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['descricao_etapa'], 10000), texto_etapa_style)
                    ])

                if etapa.get('como_e_feito'):
                    info_etapa.append([
                        Paragraph("<b>Como é feito:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['como_e_feito'], 10000), texto_etapa_style)
                    ])

                if etapa.get('objetivo_etapa'):
                    info_etapa.append([
                        Paragraph("<b>Objetivo da Etapa:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['objetivo_etapa'], 10000), texto_etapa_style)
                    ])

                if etapa.get('politica_interna'):
                    info_etapa.append([
                        Paragraph("<b>Política Interna:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['politica_interna'], 10000), texto_etapa_style)
                    ])

                # Dentro do loop de etapas, modifique:
                if etapa.get('obrigacoes_regulatorias'):
                    try:
                        dados_obrigacoes = etapa['obrigacoes_regulatorias']
                        if isinstance(dados_obrigacoes, str):
                            dados_obrigacoes = json.loads(dados_obrigacoes)
                        
                        # Extrai apenas os títulos
                        if isinstance(dados_obrigacoes, list):
                            titulos = [item.get('titulo', 'Sem título') for item in dados_obrigacoes if isinstance(item, dict)]
                            texto_obrigacoes = " • ".join(titulos) if titulos else "Nenhuma obrigação cadastrada"
                        else:
                            texto_obrigacoes = str(dados_obrigacoes)
                    except:
                        texto_obrigacoes = str(etapa['obrigacoes_regulatorias'])
                    
                    info_etapa.append([
                        Paragraph("<b>Obrigações Regulatórias:</b>", card_texto_style),
                        Paragraph(texto_obrigacoes, texto_etapa_style)
                    ])

                if etapa.get('analise_critica'):
                    info_etapa.append([
                        Paragraph("<b>PONTO DE AUDITORIA:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['analise_critica'], 10000), texto_etapa_style)
                    ])

                if etapa.get('sugestao_melhoria'):
                    info_etapa.append([
                        Paragraph("<b>SUGESTÃO DE MELHORIA:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['sugestao_melhoria'], 10000), texto_etapa_style)
                    ])

                if etapa.get('necessidade_implantacao'):
                    info_etapa.append([
                        Paragraph("<b>NECESSIDADE PARA IMPLANTAÇÃO:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['necessidade_implantacao'], 10000), texto_etapa_style)
                    ])

                if etapa.get('ganho_previsto'):
                    info_etapa.append([
                        Paragraph("<b>GANHO PREVISTO:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['ganho_previsto'], 10000), texto_etapa_style)
                    ])
                
                # Manual da etapa
                manual_em_andamento = etapa.get('manual_em_andamento', False)
                manual_nome = etapa.get('manual_nome', '')
                
                if manual_em_andamento:
                    status_manual = "EM ANDAMENTO (AGUARDANDO FINALIZAÇÃO)"
                elif manual_nome:
                    status_manual = f"CONCLUÍDO - {manual_nome}"
                else:
                    status_manual = "NÃO ANEXADO"
                
                info_etapa.append([
                    Paragraph("<b>Manual:</b>", card_texto_style),
                    Paragraph(status_manual, texto_etapa_style)
                ])
                
                if info_etapa:
                    largura_label_etapa = 4.0 * cm
                    largura_valor_etapa = largura_disponivel - 2*cm - largura_label_etapa - 1*cm
                    
                    if largura_valor_etapa < 4*cm:
                        largura_valor_etapa = 4*cm
                        largura_label_etapa = largura_disponivel - 2*cm - largura_valor_etapa - 1*cm
                        if largura_label_etapa < 3*cm:
                            largura_label_etapa = 3*cm
                    
                    info_etapa_table = Table(info_etapa, colWidths=[largura_label_etapa, largura_valor_etapa])
                    info_etapa_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#DDDDDD')),
                    ]))
                    story.append(info_etapa_table)
                    story.append(Spacer(1, 5))
                
                # ============================================================
                # RISCOS DA ETAPA
                # ============================================================
                riscos = etapa.get('riscos', [])
                print(f"      Riscos encontrados: {len(riscos)}")
                
                if riscos:
                    story.append(Paragraph("<b>Riscos Identificados</b>", secao_titulo_style))
                    story.append(Spacer(1, 3))
                    
                    for risco_idx, risco in enumerate(riscos):
                        # ⭐ CORREÇÃO: Acessar os campos do dicionário
                        magnitude = risco.get('magnitude')
                        nome_risco = risco.get('nome_risco', 'Risco não nomeado')
                        
                        print(f"         Risco {risco_idx + 1}: {nome_risco}")
                        
                        magnitude = risco.get('magnitude')
                        emoji = get_emoji_risco(magnitude)
                        nome_risco = risco.get('nome_risco', 'Risco não nomeado')
                        
                        # # Limitar nome do risco
                        # if len(nome_risco) > 80:
                        #     nome_risco = nome_risco[:77] + '...'
                        
                        story.append(Paragraph(f"{emoji} <b>Risco {risco_idx + 1}:</b> {nome_risco}", card_subtitulo_style))
                        story.append(Spacer(1, 2))
                        
                        info_risco = []
                        
                        if risco.get('categoria'):
                            info_risco.append([
                                Paragraph("<b>Categoria:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['categoria'], 10000), texto_risco_style)
                            ])

                        if risco.get('fator_risco'):
                            info_risco.append([
                                Paragraph("<b>Fator de Risco:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['fator_risco'], 10000), texto_risco_style)
                            ])

                        if risco.get('consequencia'):
                            info_risco.append([
                                Paragraph("<b>Consequência:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['consequencia'], 10000), texto_risco_style)
                            ])
                        
                        # ⭐ NOVOS CAMPOS AQUI (entre consequencia e desc_tratamento)
                        if risco.get('info_adicional'):
                            info_risco.append([
                                Paragraph("<b>Informações Adicionais:</b>", card_texto_style),
                                Paragraph(limitar_texto(str(risco['info_adicional']), 10000), texto_risco_style)
                            ])

                        if risco.get('financeiro') is not None:  # Verifica se não é None
                            valor_financeiro = risco['financeiro']
                            # Converte booleano para "Sim" ou "Não"
                            if isinstance(valor_financeiro, bool):
                                valor_financeiro = "SIM" if valor_financeiro else "NÃO"
                            info_risco.append([
                                Paragraph("<b>Impacta Financeiramente?:</b>", card_texto_style),
                                Paragraph(str(valor_financeiro), texto_risco_style)
                            ])

                        if risco.get('ativo') is not None:  # Verifica se não é None
                            valor_ativo = risco['ativo']
                            # Converte booleano para "Sim" ou "Não"
                            if isinstance(valor_ativo, bool):
                                valor_ativo = "SIM" if valor_ativo else "NÃO"
                            info_risco.append([
                                Paragraph("<b>Risco está ativo?:</b>", card_texto_style),
                                Paragraph(str(valor_ativo), texto_risco_style)
                            ])

                        if risco.get('origem'):
                            info_risco.append([
                                Paragraph("<b>Origem:</b>", card_texto_style),
                                Paragraph(str(risco['origem']), texto_risco_style)
                            ])

                        if risco.get('causas'):
                            info_risco.append([
                                Paragraph("<b>Categoria de Causa:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['causas'], 10000), texto_risco_style)
                            ])

                        if risco.get('impacto'):
                            info_risco.append([
                                Paragraph("<b>Impacto:</b>", card_texto_style),
                                Paragraph(risco['impacto'], texto_risco_style)
                            ])

                        if risco.get('probabilidade'):
                            info_risco.append([
                                Paragraph("<b>Probabilidade:</b>", card_texto_style),
                                Paragraph(risco['probabilidade'], texto_risco_style)
                            ])

                        if risco.get('magnitude') is not None:
                            info_risco.append([
                                Paragraph("<b>Magnitude (Risco Bruto):</b>", card_texto_style),
                                Paragraph(str(risco['magnitude']), texto_risco_style)
                            ])
                        
                        # Risco Residual
                        apetite_impacto = risco.get('apetite_impacto')
                        apetite_probabilidade = risco.get('apetite_probabilidade')
                        risco_residual = calcular_risco_residual(apetite_impacto, apetite_probabilidade)

                        if risco_residual is not None:
                            info_risco.append([
                                Paragraph("<b>Risco Residual:</b>", card_texto_style),
                                Paragraph(str(risco_residual), texto_risco_style)
                            ])
                        else:
                            info_risco.append([
                                Paragraph("<b>Risco Residual:</b>", card_texto_style),
                                Paragraph("Não informado", texto_risco_style)
                            ])

                        if risco.get('motivo_classificacao'):
                            info_risco.append([
                                Paragraph("<b>Motivo da Classificação:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['motivo_classificacao'], 10000), texto_risco_style)
                            ])

                        if risco.get('tratamento'):
                            info_risco.append([
                                Paragraph("<b>Tratamento:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['tratamento'], 10000), texto_risco_style)
                            ])

                        if risco.get('desc_tratamento'):
                            info_risco.append([
                                Paragraph("<b>Descrição do Tratamento:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['desc_tratamento'], 10000), texto_risco_style)
                            ])

                        if risco.get('prazo_implantacao'):
                            info_risco.append([
                                Paragraph("<b>Prazo para Implementação:</b>", card_texto_style),
                                Paragraph(risco['prazo_implantacao'], texto_risco_style)
                            ])
                        
                        if info_risco:
                            largura_label_risco = 3.5 * cm
                            largura_valor_risco = largura_disponivel - 2*cm - largura_label_risco - 1*cm
                            
                            if largura_valor_risco < 4*cm:
                                largura_valor_risco = 4*cm
                                largura_label_risco = largura_disponivel - 2*cm - largura_valor_risco - 1*cm
                                if largura_label_risco < 3*cm:
                                    largura_label_risco = 3*cm
                            
                            info_risco_table = Table(info_risco, colWidths=[largura_label_risco, largura_valor_risco])
                            info_risco_table.setStyle(TableStyle([
                                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFF8F0')),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('TOPPADDING', (0, 0), (-1, -1), 2),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#EEEEEE')),
                            ]))
                            story.append(info_risco_table)
                            story.append(Spacer(1, 3))
                        
                        # ============================================================
                        # CONTROLES DO RISCO
                        # ============================================================
                        controles = risco.get('controles', [])
                        print(f"            Controles encontrados: {len(controles)}")
                        
                        if controles:
                            story.append(Paragraph("<b>Controles para este risco</b>", subsecao_titulo_style))
                            story.append(Spacer(1, 2))
                            
                            for controle_idx, controle in enumerate(controles):
                                # ⭐ CORREÇÃO: Acessar os campos do dicionário
                                nome_controle = controle.get('nome_controle', 'Controle não nomeado')
                                print(f"               Controle {controle_idx + 1}: {nome_controle}")
                                
                                texto_controle = []
                                texto_controle.append(f"<b>Controle {controle_idx + 1}:</b> {controle.get('nome_controle', 'Controle não nomeado')}")
                                
                                if risco.get('fator_risco'):
                                    texto_controle.append(f"  • <b>Fator de Risco:</b> {limitar_texto(risco['fator_risco'], 10000)}")
                                
                                if controle.get('objetivo_controle'):
                                    texto_controle.append(f"  • <b>Objetivo:</b> {limitar_texto(controle['objetivo_controle'], 10000)}")
                                
                                if controle.get('forma_execucao'):
                                    texto_controle.append(f"  • <b>Forma de Execução:</b> {controle['forma_execucao']}")
                                
                                if controle.get('como_executado'):
                                    texto_controle.append(f"  • <b>Como Executado:</b> {limitar_texto(controle['como_executado'], 10000)}")
                                
                                if controle.get('natureza'):
                                    texto_controle.append(f"  • <b>Natureza:</b> {controle['natureza']}")
                                
                                if controle.get('periodicidade_execucao'):
                                    texto_controle.append(f"  • <b>Periodicidade:</b> {controle['periodicidade_execucao']}")
                                
                                if controle.get('evidencia_realizacao'):
                                    texto_controle.append(f"  • <b>Evidência:</b> {limitar_texto(controle['evidencia_realizacao'], 10000)}")
                                
                                if controle.get('frequencia_evidencia'):
                                    texto_controle.append(f"  • <b>Frequência da Evidência:</b> {controle['frequencia_evidencia']}")
                                
                                if controle.get('local_evidencia'):
                                    texto_controle.append(f"  • <b>Local da Evidência:</b> {controle['local_evidencia']}")
                                
                                if controle.get('lgpd'):
                                    texto_controle.append(f"  • <b>LGPD:</b> {controle['lgpd']}")
                                
                                if controle.get('status_controle'):
                                    status_texto = controle['status_controle']
                                    if 'Ativo' in status_texto or 'ativo' in status_texto:
                                        status_texto = f"{status_texto}"
                                    elif 'Inativo' in status_texto or 'inativo' in status_texto:
                                        status_texto = f"{status_texto}"
                                    elif 'Em andamento' in status_texto or 'em andamento' in status_texto:
                                        status_texto = f"{status_texto}"
                                    texto_controle.append(f"  • <b>Status:</b> {status_texto}")
                                
                                if controle.get('responsaveis_tratamento'):
                                    texto_controle.append(f"  • <b>Responsável:</b> {controle['responsaveis_tratamento']}")
                                
                                story.append(Paragraph("<br/>".join(texto_controle), texto_controle_style))
                        else:
                            story.append(Paragraph("<i>Nenhum controle cadastrado para este risco.</i>", normal_style))
                        
                        story.append(Spacer(1, 10))
                else:
                    story.append(Paragraph("<i>Nenhum risco cadastrado para esta etapa.</i>", normal_style))
        
        story.append(Spacer(1, 15))
    
    # ===== 4g. PÁGINA DE VALIDAÇÃO DO GESTOR =====
    entrevistado = None
    if processo_id:
        try:
            from database import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                query_entrevistado = text("""
                    SELECT entrevistado FROM processos WHERE id = :processo_id
                """)
                result = conn.execute(query_entrevistado, {"processo_id": processo_id}).fetchone()
                if result and result[0]:
                    entrevistado = result[0]
        except Exception as e:
            print(f"Erro ao buscar entrevistado: {e}")

    criar_pagina_validacao(
        story=story,
        gestor=gestor,
        styles=styles,
        normal_style=normal_style,
        auditoria_id=auditoria_id,
        tipo_relatorio='detalhamento',
        entrevistado=entrevistado  # ⭐ PASSA O ENTREVISTADO
    )

    # ===== BUSCAR DADOS DA GERÊNCIA DE AUDITORIA INTERNA (FIXOS) =====
    dados_gai = buscar_dados_gerencia_auditoria()
    email_gai = dados_gai['email']
    telefone_gai = dados_gai['telefone']
    
    # ===== 5. GERAR O PDF =====
    def rodape_detalhamento(canvas, doc, total_paginas):
        """Rodapé específico do relatório Detalhamento"""
        titulo_rodape = f"Relatório de Validação Matriz de Detalhamento - {area_nome[:50]}"
        criar_rodape(canvas, doc, pagesize, total_paginas, titulo_rodape,
                     email_auditoria=email_gai,      # ⬅️ Email da GAI (fixo)
                     telefone_auditoria=telefone_gai) # ⬅️ Telefone da GAI (fixo)
    
    pdf_bytes = contar_paginas_e_gerar_pdf(
        story=story,
        pagesize=pagesize,
        topMargin=topMargin,
        bottomMargin=bottomMargin,
        leftMargin=leftMargin,
        rightMargin=rightMargin,
        rodape_func=rodape_detalhamento,
        cabecalho_func=None
    )
    
    print(f"📄 PDF do Detalhamento gerado! Tamanho: {len(pdf_bytes)} bytes")
    
    return pdf_bytes


def buscar_processos_detalhamento(area_id, auditoria_id=None, processo_id=None):
    """
    Busca processos com suas etapas, riscos e controles para o relatório de Detalhamento
    Inclui os executores da tabela processo_executores e os campos de apetite ao risco
    """
    from database import engine
    from sqlalchemy import text
    
    print(f"🔍 Buscando processos para Detalhamento")
    print(f"   area_id: {area_id}")
    print(f"   auditoria_id: {auditoria_id}")
    print(f"   processo_id: {processo_id}")
    
    # ⭐ 1. BUSCAR PROCESSOS COM EXECUTORES AGREGADOS
    if processo_id:
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
                (
                    SELECT STRING_AGG(f.nome_funcionario, ', ' ORDER BY f.nome_funcionario)
                    FROM processo_executores pe
                    JOIN funcionarios_area f ON pe.funcionario_id = f.id
                    WHERE pe.processo_id = p.id
                ) AS executores
            FROM processos p
            WHERE p.id_area = :area_id
                AND p.id = :processo_id
                AND p.status = 'Ativo'
            ORDER BY p.codigo_processo
        """)
        params = {"area_id": area_id, "processo_id": processo_id}
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
                (
                    SELECT STRING_AGG(f.nome_funcionario, ', ' ORDER BY f.nome_funcionario)
                    FROM processo_executores pe
                    JOIN funcionarios_area f ON pe.funcionario_id = f.id
                    WHERE pe.processo_id = p.id
                ) AS executores
            FROM processos p
            WHERE p.id_area = :area_id
                AND p.auditoria_id = :auditoria_id
                AND p.status = 'Ativo'
            ORDER BY p.codigo_processo
        """)
        params = {"area_id": area_id, "auditoria_id": auditoria_id}
    
    with engine.connect() as conn:
        processos = conn.execute(query, params).fetchall()
    
    print(f"📊 Processos encontrados: {len(processos)}")
    
    if not processos:
        print("❌ Nenhum processo encontrado!")
        return []
    
    # ⭐ 2. Para CADA processo, buscar etapas
    resultados = []
    
    for proc in processos:
        proc_id = proc[0]
        proc_codigo = proc[1]
        proc_nome = proc[2]
        proc_executores = proc[8] or 'Não informado'
        
        print(f"   🔍 Buscando etapas para processo: {proc_codigo} (ID: {proc_id})")
        
        # ⭐ Buscar etapas com TODOS OS CAMPOS
        query_etapas = text("""
            SELECT 
                e.id,
                e.codigo_etapa,
                e.nome_etapa,
                e.descricao_etapa,
                e.objetivo_etapa,
                e.como_e_feito,
                e.analise_critica,
                e.sugestao_melhoria,
                e.necessidade_implantacao,
                e.ganho_previsto,
                e.politica_interna,
                e.obrigacoes_regulatorias,
                e.status_etapa,
                e.criticidade_etapa,
                e.manual_em_andamento,
                e.manual_nome,
                e.diagrama_nome,
                e.arquivo_mapeamento_nome
            FROM etapas_processo e
            WHERE e.processo_id = :processo_id
                AND (e.status_etapa = 'ATIVA' OR e.status_etapa IS NULL)
            ORDER BY e.codigo_etapa
        """)
        
        with engine.connect() as conn:
            etapas = conn.execute(query_etapas, {"processo_id": proc_id}).fetchall()
        
        print(f"      Etapas encontradas: {len(etapas)}")
        
        etapas_lista = []
        
        for etapa in etapas:
            etapa_id = etapa[0]
            
            # ⭐ Buscar riscos da etapa (COM OS CAMPOS DE APETITE - NOMES CORRETOS)
            query_riscos = text("""
                SELECT 
                    r.id,
                    r.nome_risco,
                    r.categoria,
                    r.fator_risco,
                    r.consequencia,
                    r.causas,
                    r.impacto,
                    r.probabilidade,
                    r.magnitude,
                    r.motivo_classificacao,
                    r.tratamento,
                    r.desc_tratamento,
                    r.prazo_implantacao,
                    r.impacto_aceitavel,
                    r.probabilidade_aceitavel,
                    r.info_adicional,
                    r.financeiro,
                    r.ativo,
                    r.origem
                FROM riscos_etapa r
                WHERE r.etapa_id = :etapa_id
                ORDER BY r.id
            """)
            
            with engine.connect() as conn:
                riscos = conn.execute(query_riscos, {"etapa_id": etapa_id}).fetchall()
            
            print(f"         Riscos encontrados: {len(riscos)}")
            
            riscos_lista = []
            
            for risco in riscos:
                risco_id = risco[0]
                
                # ⭐ Buscar controles do risco com TODOS OS CAMPOS
                query_controles = text("""
                    SELECT 
                        c.id,
                        c.nome_controle,
                        c.como_executado,
                        c.objetivo_controle,
                        c.natureza,
                        c.periodicidade_execucao,
                        c.evidencia_realizacao,
                        c.responsaveis_tratamento,
                        c.forma_execucao,
                        c.lgpd,
                        c.frequencia_evidencia,
                        c.local_evidencia,
                        c.status_controle
                    FROM controles_etapa c
                    WHERE c.risco_id = :risco_id
                    ORDER BY c.id
                """)
                
                with engine.connect() as conn:
                    controles = conn.execute(query_controles, {"risco_id": risco_id}).fetchall()
                
                controles_lista = []
                for controle in controles:
                    controles_lista.append({
                        'controle_id': controle[0],
                        'nome_controle': controle[1],
                        'como_executado': controle[2],
                        'objetivo_controle': controle[3],
                        'natureza': controle[4],
                        'periodicidade_execucao': controle[5],
                        'evidencia_realizacao': controle[6],
                        'responsaveis_tratamento': controle[7],
                        'forma_execucao': controle[8],
                        'lgpd': controle[9],
                        'frequencia_evidencia': controle[10],
                        'local_evidencia': controle[11],
                        'status_controle': controle[12]
                    })
                
                # ⭐ MONTAR DICIONÁRIO DO RISCO COM TODOS OS CAMPOS
                riscos_lista.append({
                    'risco_id': risco_id,
                    'nome_risco': risco[1],
                    'categoria': risco[2],
                    'fator_risco': risco[3],
                    'consequencia': risco[4],
                    'causas': risco[5],
                    'impacto': risco[6],
                    'probabilidade': risco[7],
                    'magnitude': risco[8],
                    'motivo_classificacao': risco[9],
                    'tratamento': risco[10],
                    'desc_tratamento': risco[11],
                    'prazo_implantacao': risco[12],
                    'apetite_impacto': risco[13],      
                    'apetite_probabilidade': risco[14], 
                    'info_adicional': risco[15],
                    'financeiro': risco[16],
                    'ativo': risco[17],
                    'origem': risco[18],
                    'controles': controles_lista
                })
            
            etapas_lista.append({
                'etapa_id': etapa_id,
                'codigo_etapa': etapa[1],
                'nome_etapa': etapa[2],
                'descricao_etapa': etapa[3],
                'objetivo_etapa': etapa[4],
                'como_e_feito': etapa[5],
                'analise_critica': etapa[6],
                'sugestao_melhoria': etapa[7],
                'necessidade_implantacao': etapa[8],
                'ganho_previsto': etapa[9],
                'politica_interna': etapa[10],
                'obrigacoes_regulatorias': etapa[11],
                'status_etapa': etapa[12],
                'criticidade_etapa': etapa[13],
                'manual_em_andamento': etapa[14],
                'manual_nome': etapa[15],
                'diagrama_nome': etapa[16],
                'arquivo_mapeamento_nome': etapa[17],
                'riscos': riscos_lista
            })
        
        resultados.append({
            'processo_id': proc_id,
            'codigo_processo': proc_codigo,
            'nome_processo': proc_nome,
            'objetivo': proc[3],
            'executor': proc_executores,
            'descricao': proc[4],
            'etapa_ini': proc[5],
            'etapa_fim': proc[6],
            'produto': proc[7],
            'etapas': etapas_lista
        })
    
    print(f"✅ Retornando {len(resultados)} processos para Detalhamento")
    return resultados


def carregar_areas_banco():
    """ Busca áreas no Banco de Dados e retorna um dicionário {nome: id}."""
    query = text("""
        SELECT id_area, nome_area, loc_unidade
        FROM informacoes_area
        ORDER BY nome_area ASC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    def formatar_nome(row):
        nome = row['nome_area']
        unidade = row['loc_unidade']
        if unidade and unidade.strip():
            return f"{nome} - {unidade}"
        return nome
    
    df['nome_completo'] = df.apply(formatar_nome, axis=1)

    return dict(zip(df['nome_completo'], df['id_area']))

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



def gerar_pdf_conclusao(area_id, area_nome, gestor, cargo, unidade, 
                        codigo_auditoria, titulo_auditoria, conclusao_data, 
                        orientacao="RETRATO", usuario_nome="Usuário"):
    """
    Gera o relatório de conclusão em PDF com suporte a SWOT
    
    Parâmetros:
    - conclusao_data: Pode ser uma string (texto) ou um dicionário com os campos da SWOT
    - usuario_nome: Nome do usuário que está baixando o relatório (vai na assinatura)
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    import io
    import os
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from PyPDF2 import PdfReader
    import copy
    import json
    
    buffer = io.BytesIO()
    TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Buscar dados da GAI
    dados_gai = buscar_dados_gerencia_auditoria()
    email_gai = dados_gai['email']
    telefone_gai = dados_gai['telefone']
    
    # ⭐ EXTRAIR DADOS DA CONCLUSÃO (pode ser string ou dict)
    if isinstance(conclusao_data, dict):
        texto_conclusao = conclusao_data.get('conclusao', '')
        forca = conclusao_data.get('forca', '')
        fraqueza = conclusao_data.get('fraqueza', '')
        oportunidades = conclusao_data.get('oportunidades', '')
        ameacas = conclusao_data.get('ameacas', '')
    else:
        texto_conclusao = str(conclusao_data) if conclusao_data else ''
        forca = fraqueza = oportunidades = ameacas = ''
    
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
    
    story = []
    
    # ⭐ CAPA
    criar_pagina_capa(
        story=story,
        pagesize=pagesize,
        titulo_relatorio="RELATÓRIO DE CONCLUSÃO DA AUDITORIA",
        subtitulo_relatorio=f"{titulo_auditoria}",
        area_nome=area_nome,
        data_emissao=datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    )
    
    # ⭐ PÁGINA DE CONCLUSÃO
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    
    # Estilos
    titulo_secao_style = ParagraphStyle(
        'TituloSecao',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#0b5b99')
    )
    
    conclusao_style = ParagraphStyle(
        'ConclusaoStyle',
        parent=normal_style,
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=15,
        leftIndent=20,
        rightIndent=20
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=normal_style,
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=8
    )
    
    # ⭐ ESTILO PARA SWOT
    swot_titulo_style = ParagraphStyle(
        'SwotTitulo',
        parent=normal_style,
        fontSize=12,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor('#184145')
    )
    
    swot_label_style = ParagraphStyle(
        'SwotLabel',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        spaceAfter=3,
        textColor=colors.HexColor('#184145'),
        alignment=TA_CENTER
    )
    
    swot_texto_style = ParagraphStyle(
        'SwotTexto',
        parent=normal_style,
        fontSize=9,
        leading=12,
        alignment=TA_JUSTIFY,  # ⭐ Centralizado
        leftIndent=0,         # ⭐ Remove indentação
        rightIndent=0,
        spaceAfter=8
    )
    
    assinatura_style = ParagraphStyle(
        'AssinaturaStyle',
        parent=normal_style,
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    # Título
    story.append(Paragraph("CONCLUSÃO DA AUDITORIA", titulo_secao_style))
    story.append(Spacer(1, 10))
    
    # Informações
    story.append(Paragraph(f"<b>Auditoria:</b> {codigo_auditoria} - {titulo_auditoria}", info_style))
    story.append(Paragraph(f"<b>Área:</b> {area_nome}", info_style))
    if unidade:
        story.append(Paragraph(f"<b>Unidade:</b> {unidade}", info_style))
    story.append(Paragraph(f"<b>Gestor:</b> {gestor} - {cargo}", info_style))
    
    # ⭐ Quem escreveu a conclusão (vem do banco)
    # Buscar o autor da conclusão do banco
    autor_conclusao = usuario_nome  # Por padrão, usa o usuário atual
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT usuario_nome FROM conclusoes_auditoria
                WHERE auditoria_id = :auditoria_id AND area_id = :area_id
            """)
            result = conn.execute(query, {
                'auditoria_id': codigo_auditoria,  # Precisa do ID da auditoria
                'area_id': area_id
            }).fetchone()
            if result:
                autor_conclusao = result[0]
    except:
        pass
    
    story.append(Paragraph(f"<b>Data/Hora Emissão:</b> {datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')}", info_style))
    story.append(Spacer(1, 20))
    
    # Linha divisória
    story.append(Paragraph("<hr/>", normal_style))
    story.append(Spacer(1, 15))
    
    # ⭐ REMOVIDO O AVISO DE VALIDADE - SEMPRE ASSINA
    
    # ⭐ CONCLUSÃO GERAL
    if texto_conclusao:
        story.append(Paragraph("<b>CONCLUSÃO:</b>", info_style))
        story.append(Spacer(1, 5))
        story.append(Paragraph(texto_conclusao, conclusao_style))
        story.append(Spacer(1, 20))
    
    # ⭐ ANÁLISE SWOT
    story.append(PageBreak())
    tem_swot = any([forca, fraqueza, oportunidades, ameacas])
    if tem_swot:
        story.append(Paragraph("<b>ANÁLISE SWOT</b>", swot_titulo_style))
        story.append(Spacer(1, 5))
        
        # ⭐ CRIAR TABELA SWOT (2x2)
        dados_swot = []
        
        # Forças
        forca_texto = forca if forca else 'Não informado'
        dados_swot.append([
            Paragraph('<b><font color="#28a745">FORÇAS</font></b>', swot_label_style),
            Paragraph(forca_texto, swot_texto_style)
        ])
        
        # Fraquezas
        fraqueza_texto = fraqueza if fraqueza else 'Não informado'
        dados_swot.append([
            Paragraph('<b><font color="#dc3545">FRAQUEZAS</font></b>', swot_label_style),
            Paragraph(fraqueza_texto, swot_texto_style)
        ])
        
        # Oportunidades
        oportunidades_texto = oportunidades if oportunidades else 'Não informado'
        dados_swot.append([
            Paragraph('<b><font color="#ffc107">OPORTUNIDADES</font></b>', swot_label_style),
            Paragraph(oportunidades_texto, swot_texto_style)
        ])
        
        # Ameaças
        ameacas_texto = ameacas if ameacas else 'Não informado'
        dados_swot.append([
            Paragraph('<b><font color="#fd6a14">AMEAÇAS</font></b>', swot_label_style),
            Paragraph(ameacas_texto, swot_texto_style)
        ])
        
        # ⭐ CRIAR TABELA
        tabela_swot = Table(dados_swot, colWidths=[3.5*cm, 12*cm])
        tabela_swot.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),      # ⭐ Centraliza horizontalmente
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),     # ⭐ Centraliza verticalmente
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ]))
        
        story.append(tabela_swot)
        story.append(Spacer(1, 15))
    
    # ⭐ SE NÃO HOUVER NEM CONCLUSÃO NEM SWOT
    if not texto_conclusao and not tem_swot:
        story.append(Paragraph(
            "<i>Nenhuma conclusão foi registrada para esta auditoria.</i>",
            conclusao_style
        ))
        story.append(Spacer(1, 20))
    
   

    # ============================================================
    # ⭐ PÁGINA DE VALIDAÇÃO COM ASSINATURAS
    # ============================================================

    # Buscar responsáveis da auditoria
    responsaveis = []
    try:
        with engine.connect() as conn:
            query_resp = text("""
                SELECT responsavel_equipe FROM auditorias WHERE codigo_auditoria = :codigo
            """)
            # ⭐ USAR codigo_auditoria como código
            result = conn.execute(query_resp, {'codigo': codigo_auditoria}).fetchone()
            
            if result and result[0]:
                responsaveis = result[0]
                print(f"📋 Responsáveis: {responsaveis}")
    except Exception as e:
        print(f"⚠️ Erro ao buscar responsáveis: {e}")

    # ⭐ CHAMAR A FUNÇÃO DE VALIDAÇÃO
    criar_pagina_validacao_conclusao(
        story=story,
        gestor=gestor,
        styles=styles,
        normal_style=normal_style,
        auditoria_id=codigo_auditoria,
        responsaveis=responsaveis,
        tipo_relatorio='conclusao'
    )
    
    # ============================================================
    # ⭐ RODAPÉ USANDO A FUNÇÃO PADRONIZADA
    # ============================================================
    def rodape_conclusao(canvas, doc, total_paginas):
        """Rodapé específico do relatório de conclusão"""
        titulo_rodape = f"Relatório de Conclusão - {area_nome[:50]}"
        criar_rodape(canvas, doc, pagesize, total_paginas, titulo_rodape,
                     root_dir=root_dir,
                     email_auditoria=email_gai,
                     telefone_auditoria=telefone_gai)
    
    # ============================================================
    # ⭐ GERAR O PDF COM CONTAGEM DE PÁGINAS
    # ============================================================
    
    # ⭐ 1. FAZER UMA CÓPIA DO STORY PARA A PRIMEIRA PASSADA
    story_copy = copy.deepcopy(story)
    
    # ⭐ 2. PRIMEIRA PASSADA: GERAR PDF TEMPORÁRIO PARA CONTAR PÁGINAS
    buffer_temp = io.BytesIO()
    doc_temp = SimpleDocTemplate(buffer_temp, pagesize=pagesize,
                                topMargin=topMargin, bottomMargin=bottomMargin,
                                leftMargin=leftMargin, rightMargin=rightMargin)
    
    def rodape_temp(canvas, doc):
        if doc.page == 1:
            return
        criar_rodape(canvas, doc, pagesize, 0, f"Relatório de Conclusão - {area_nome[:50]}",
                     root_dir=root_dir,
                     email_auditoria=email_gai,
                     telefone_auditoria=telefone_gai)
    
    doc_temp.build(story_copy, onFirstPage=rodape_temp, onLaterPages=rodape_temp)
    
    # ⭐ 3. CONTAR AS PÁGINAS
    buffer_temp.seek(0)
    pdf_reader = PdfReader(buffer_temp)
    total_paginas = len(pdf_reader.pages)
    
    # ⭐ 4. SEGUNDA PASSADA: GERAR O PDF FINAL COM O TOTAL
    doc_final = SimpleDocTemplate(buffer, pagesize=pagesize,
                                 topMargin=topMargin, bottomMargin=bottomMargin,
                                 leftMargin=leftMargin, rightMargin=rightMargin)
    
    def rodape_final(canvas, doc):
        if doc.page == 1:
            return
        rodape_conclusao(canvas, doc, total_paginas)
    
    doc_final.build(story, onFirstPage=rodape_final, onLaterPages=rodape_final)
    
    buffer.seek(0)
    return buffer.getvalue()

def gerar_relatorio_followups(area_id, area_nome, gestor, cargo, auditoria_id, processo_id,
                               orientacao="RETRATO", titulo_auditoria=None):
    """
    Gera relatório de Follow-ups das sugestões de melhoria
    Organizado por etapas do processo
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.utils import ImageReader
    from PIL import Image as PILImage
    import copy
    from PyPDF2 import PdfReader
    
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
    
    # Estilos
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontSize = 9
    normal_style.fontName = 'Helvetica'
    
    # Estilos personalizados
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#000000')
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
        underlineWidth=1.5,
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
    
    story = []
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # ===== BUSCAR TÍTULO DA AUDITORIA =====
    titulo_final = titulo_auditoria
    if titulo_final is None:
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
    
    # ===== CAPA =====
    criar_pagina_capa(
        story=story,
        pagesize=pagesize,
        titulo_relatorio="RELATÓRIO DE FOLLOW-UPS",
        subtitulo_relatorio=f"{titulo_final}",
        area_nome=area_nome,
        data_emissao=datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    )
    
    # ===== TÍTULO =====
    story.append(Paragraph("RELATÓRIO DE FOLLOW-UPS", titulo_style))
    story.append(Spacer(1, 5))
    
    # ===== BUSCAR DADOS =====
    with engine.connect() as conn:
        # Buscar dados da auditoria
        query_auditoria = text("""
            SELECT codigo_auditoria, titulo, status
            FROM auditorias WHERE id = :auditoria_id
        """)
        auditoria_info = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
        
        if not auditoria_info:
            raise Exception(f"Auditoria não encontrada")
        
        codigo_auditoria = auditoria_info[0]
        status = auditoria_info[2]
        
        # Buscar processo específico (se fornecido)
        if processo_id:
            query_processo = text("""
                SELECT id, codigo_processo, nome_processo
                FROM processos
                WHERE id = :processo_id AND auditoria_id = :auditoria_id AND status = 'Ativo'
            """)
            processo = conn.execute(query_processo, {
                "processo_id": processo_id,
                "auditoria_id": auditoria_id
            }).fetchone()
            
            if not processo:
                raise Exception(f"Processo {processo_id} não encontrado")
            
            proc_id = processo[0]
            proc_codigo = processo[1]
            proc_nome = processo[2]
            
            # Buscar apenas as etapas deste processo
            query_etapas = text("""
                SELECT id, nome_etapa, codigo_etapa, descricao_etapa, objetivo_etapa
                FROM etapas_processo 
                WHERE processo_id = :processo_id 
                ORDER BY codigo_etapa
            """)
            etapas_raw = conn.execute(query_etapas, {"processo_id": proc_id}).fetchall()
        else:
            # Buscar todos os processos da auditoria
            query_processos = text("""
                SELECT id, codigo_processo, nome_processo
                FROM processos
                WHERE auditoria_id = :auditoria_id AND status = 'Ativo'
                ORDER BY codigo_processo
            """)
            processos = conn.execute(query_processos, {"auditoria_id": auditoria_id}).fetchall()
            
            if not processos:
                raise Exception(f"Nenhum processo encontrado para esta auditoria")
            
            # Buscar etapas de todos os processos
            proc_ids = [p[0] for p in processos]
            query_etapas = text("""
                SELECT id, nome_etapa, codigo_etapa, descricao_etapa, objetivo_etapa, processo_id
                FROM etapas_processo 
                WHERE processo_id IN :processo_ids
                ORDER BY processo_id, codigo_etapa
            """)
            etapas_raw = conn.execute(query_etapas, {"processo_ids": tuple(proc_ids)}).fetchall()
        
        # ===== AGRUPAR ETAPAS =====
        etapas = []
        for etapa in etapas_raw:
            if processo_id:
                etapa_id = etapa[0]
                etapa_nome = etapa[1]
                etapa_codigo = etapa[2] or ''
                etapa_desc = etapa[3] or ''
                etapa_obj = etapa[4] or ''
            else:
                etapa_id = etapa[0]
                etapa_nome = etapa[1]
                etapa_codigo = etapa[2] or ''
                etapa_desc = etapa[3] or ''
                etapa_obj = etapa[4] or ''
                proc_id_etapa = etapa[5]
            
            # Buscar análises com sugestao_sera_implantada = TRUE
            query_analises = text("""
                SELECT 
                    ac.id,
                    ac.analise_critica,
                    ac.sugestao_melhoria,
                    ac.sugestao_sera_implantada,
                    ac.plano_de_acao_implantado,
                    ac.data_execucao_plano_acao,
                    ac.necessidade_implantacao,
                    ac.ganho_previsto,
                    ac.categoria,
                    p.codigo_processo,
                    p.nome_processo,
                    pa.oque,                    
                    pa.por_que,                 
                    pa.onde,                    
                    pa.quando,                  
                    pa.quem,                    
                    pa.como,                    
                    pa.quanto_custa,           
                    pa.comentario               
                FROM analises_criticas ac
                LEFT JOIN processos p ON ac.processo_id = p.id
                LEFT JOIN planos_acao pa ON ac.id = pa.analise_id   
                WHERE ac.etapa_id = :etapa_id 
                AND ac.sugestao_sera_implantada = true
                AND ac.processo_id = :processo_id
                ORDER BY ac.categoria, ac.id
            """)
            
            analises_params = {"etapa_id": etapa_id, "processo_id": proc_id if processo_id else proc_id_etapa}
            analises_raw = conn.execute(query_analises, analises_params).fetchall()
            
            analises_list = []
            for a in analises_raw:
                # Buscar follow-ups
                query_followups = text("""
                    SELECT etapa, data_prevista, data_realizada, status, comentario, responsavel
                    FROM analises_follow_up
                    WHERE analise_id = :analise_id
                    ORDER BY data_prevista ASC
                """)
                followups_raw = conn.execute(query_followups, {"analise_id": a[0]}).fetchall()
                
                followups_list = []
                for f in followups_raw:
                    followups_list.append({
                        'etapa': f[0] or '',
                        'data_prevista': f[1].strftime('%d/%m/%Y') if f[1] else '-',
                        'data_realizada': f[2].strftime('%d/%m/%Y') if f[2] else '-',
                        'status': f[3] or 'Pendente',
                        'comentario': f[4] or '',
                        'responsavel': f[5] or ''
                    })
                
                analises_list.append({
                    'id': a[0],
                    'analise_critica': a[1] or '',
                    'sugestao_melhoria': a[2] or '',
                    'sugestao_sera_implantada': a[3],
                    'plano_de_acao_implantado': a[4],
                    'data_execucao_plano_acao': a[5].strftime('%d/%m/%Y') if a[5] else None,
                    'necessidade_implantacao': a[6] or '',
                    'ganho_previsto': a[7] or '',
                    'categoria': a[8] or '',
                    'codigo_processo': a[9] or '',
                    'nome_processo': a[10] or '',
                    # ⭐ PLANO DE AÇÃO 5W2H
                    'plano_acao': {
                        'oque': a[11] or '',
                        'por_que': a[12] or '',
                        'onde': a[13] or '',
                        'quando': a[14].strftime('%d/%m/%Y') if a[14] else None,
                        'quem': a[15] or '',
                        'como': a[16] or '',
                        'quanto_custa': a[17] or '',
                        'comentario': a[18] or ''
                    } if a[11] else None,  # ⭐ Se tiver 'oque', mostra o plano
                    'followups': followups_list
                })
            
            # Só adicionar a etapa se tiver análises
            if analises_list:
                etapas.append({
                    'id': etapa_id,
                    'nome': etapa_nome,
                    'codigo': etapa_codigo,
                    'descricao': etapa_desc,
                    'objetivo': etapa_obj,
                    'analises': analises_list
                })
    
    # ===== INFORMAÇÕES DO RELATÓRIO =====
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
    
    # ===== SE NÃO HOUVER ANÁLISES =====
    if not etapas:
        story.append(Paragraph(
            "<b>Nenhuma sugestão de melhoria com follow-ups encontrada para este processo.</b>",
            normal_style
        ))
        story.append(Spacer(1, 10))
    else:
        # ===== RESUMO ESTATÍSTICO =====
        total_analises = sum(len(e['analises']) for e in etapas)
        total_followups = sum(len(a['followups']) for e in etapas for a in e['analises'])
        total_pendentes = sum(1 for e in etapas for a in e['analises'] for fu in a['followups'] if fu['status'] == 'Pendente')
        total_aderentes = sum(1 for e in etapas for a in e['analises'] for fu in a['followups'] if fu['status'] == 'Aderente')
        total_nao_aderentes = sum(1 for e in etapas for a in e['analises'] for fu in a['followups'] if fu['status'] == 'Nao aderente')
        total_parcial = sum(1 for e in etapas for a in e['analises'] for fu in a['followups'] if fu['status'] == 'Parcialmente aderente')
        
        story.append(Paragraph("1. RESUMO DOS FOLLOW-UPS", secao_style))
        story.append(Spacer(1, 5))
        
        resumo_data = [
            ["Métrica", "Quantidade"],
            ["Total de análises com sugestões implantadas", str(total_analises)],
            ["Total de follow-ups", str(total_followups)],
            ["Pendentes", str(total_pendentes)],
            ["Aderentes", str(total_aderentes)],
            ["Não aderentes", str(total_nao_aderentes)],
            ["Parcialmente aderentes", str(total_parcial)]
        ]
        
        resumo_table = Table(resumo_data, colWidths=[8*cm, 8*cm])
        resumo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#184145')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.98, 0.98, 0.98, alpha=0.80)),
        ]))
        story.append(resumo_table)
        story.append(Spacer(1, 15))
        
        # ===== DETALHES POR ETAPA =====
        story.append(PageBreak())
        story.append(Paragraph("2. DETALHES DOS FOLLOW-UPS POR ETAPA", secao_style))
        story.append(Spacer(1, 5))
        
        for etapa_idx, etapa in enumerate(etapas, 1):
            # Título da etapa
            story.append(Paragraph(
                f"Etapa {etapa['codigo']}: {etapa['nome']}",
                subsecao_style
            ))
            
            if etapa['descricao']:
                story.append(Paragraph(
                    f"<b>Descrição:</b> {etapa['descricao']}",
                    normal_style
                ))
                story.append(Spacer(1, 3))
            
            if etapa['objetivo']:
                story.append(Paragraph(
                    f"<b>Objetivo:</b> {etapa['objetivo']}",
                    normal_style
                ))
                story.append(Spacer(1, 5))
            
            # Análises da etapa
            for analise_idx, analise in enumerate(etapa['analises'], 1):
                # Cabeçalho da análise
                categoria_nome = {
                    'governanca': 'Governança',
                    'riscos': 'Riscos',
                    'controles': 'Controles'
                }.get(analise['categoria'], analise['categoria'] or 'Análise')
                
                story.append(Paragraph(
                    f"<b>{etapa_idx}.{analise_idx} - {categoria_nome}</b>",
                    normal_style
                ))
                
                # Análise Crítica
                if analise['analise_critica']:
                    story.append(Paragraph(
                        f"<b>PONTO DE AUDITORIA:</b> {analise['analise_critica']}",
                        normal_style
                    ))
                
                # Sugestão de Melhoria
                if analise['sugestao_melhoria']:
                    story.append(Paragraph(
                        f"<b>Sugestão de Melhoria:</b> {analise['sugestao_melhoria']}",
                        normal_style
                    ))
                
                # ⭐ PLANO DE AÇÃO 5W2H (se existir)
                if analise.get('plano_acao') and analise['plano_acao'].get('oque'):
                    plano = analise['plano_acao']
                    story.append(Paragraph(
                        "<b>PLANO DE AÇÃO 5W2H:</b>",
                        normal_style
                    ))
                    
                    # Tabela do plano de ação
                    plano_data = [
                        ["O que?", plano.get('oque', '-')],
                        ["Por que?", plano.get('por_que', '-')],
                        ["Onde?", plano.get('onde', '-')],
                        ["Quando?", plano.get('quando', '-')],
                        ["Quem?", plano.get('quem', '-')],
                        ["Como?", plano.get('como', '-')],
                        ["Quanto custa?", plano.get('quanto_custa', '-')],
                        ["Comentário:", plano.get('comentario', '-')]
                    ]
                    
                    plano_table = Table(plano_data, colWidths=[3*cm, 11*cm])
                    plano_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E9')),
                        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    story.append(plano_table)
                    story.append(Spacer(1, 5))
                
                # Status da implantação
                if analise['plano_de_acao_implantado']:
                    status_texto = '<font color="#28a745"><b>Implantado</b></font>'
                else:
                    status_texto = '<font color="#ffc107"><b>Em andamento</b></font>'
                
                story.append(Paragraph(
                    f"<b>Status da implantação:</b> {status_texto}",
                    normal_style
                ))
                
                if analise['data_execucao_plano_acao']:
                    story.append(Paragraph(
                        f"<b>Data da implantação:</b> {analise['data_execucao_plano_acao']}",
                        normal_style
                    ))
                
                story.append(Spacer(1, 5))
                
                # Follow-ups
                if analise['followups']:
                    fu_data = [["Etapa", "Data Prevista", "Data Realizada", "Status", "Comentário"]]
                    for fu in analise['followups']:
                        etapa_texto = {
                            'FOLLOW_UP_30': '30 dias',
                            'FOLLOW_UP_60': '60 dias',
                            'FOLLOW_UP_90': '90 dias'
                        }.get(fu['etapa'], fu['etapa'])
                        
                        status_color = {
                            'Pendente': '#ff6000',
                            'Aderente': '#28a745',
                            'Nao aderente': '#dc3545',
                            'Parcialmente aderente': '#ffc107'
                        }.get(fu['status'], '#000000')
                        
                        status_text = f'<font color="{status_color}"><b>{fu["status"]}</b></font>'
                        
                        fu_data.append([
                            Paragraph(etapa_texto, normal_style),
                            Paragraph(fu['data_prevista'] or '-', normal_style),
                            Paragraph(fu['data_realizada'] or '-', normal_style),
                            Paragraph(status_text, normal_style),
                            Paragraph(fu['comentario'][:50] or '-', normal_style)
                        ])
                    
                    fu_table = Table(fu_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 3*cm, 5.5*cm], repeatRows=1)
                    fu_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b5b99')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ]))
                    story.append(fu_table)
                else:
                    story.append(Paragraph(
                        "<i>Nenhum follow-up registrado.</i>",
                        normal_style
                    ))
                
                story.append(Spacer(1, 8))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E0E0E0"), spaceBefore=3, spaceAfter=3))
            
            # Separador entre etapas
            if etapa_idx < len(etapas):
                story.append(Spacer(1, 10))
    
    # ===== ASSINATURAS =====
    criar_pagina_validacao(
        story=story,
        gestor=gestor,
        styles=styles,
        normal_style=normal_style,
        auditoria_id=auditoria_id,
        tipo_relatorio='followup',
        entrevistado=None
    )
    
    # ===== RODAPÉ =====
    # Buscar dados da GAI
    dados_gai = buscar_dados_gerencia_auditoria()
    email_gai = dados_gai['email']
    telefone_gai = dados_gai['telefone']
    
    # Função para desenhar logos
    def desenhar_logos_followup(canvas):
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
    
    # Rodapé
    def rodape_followup(canvas, doc, total_paginas):
        titulo_rodape = f"Relatório de Follow-ups - {area_nome[:50]}"
        if processo_id and 'proc_codigo' in locals():
            titulo_rodape = f"Relatório de Follow-ups - Processo {proc_codigo} - {area_nome[:40]}"
        criar_rodape(canvas, doc, pagesize, total_paginas, titulo_rodape,
                     root_dir=root_dir,
                     email_auditoria=email_gai,
                     telefone_auditoria=telefone_gai)
    
    # Primeira passada para contar páginas
    story_copy = copy.deepcopy(story)
    buffer_temp = io.BytesIO()
    doc_temp = SimpleDocTemplate(buffer_temp, pagesize=pagesize,
                                 topMargin=topMargin, bottomMargin=bottomMargin,
                                 leftMargin=leftMargin, rightMargin=rightMargin)
    
    def rodape_temp(canvas, doc):
        if doc.page == 1:
            return
        titulo_temp = f"Relatório de Follow-ups - {area_nome[:40]}"
        criar_rodape(canvas, doc, pagesize, 0, titulo_temp,
                     root_dir=root_dir,
                     email_auditoria=email_gai,
                     telefone_auditoria=telefone_gai)
    
    doc_temp.build(story_copy, onFirstPage=lambda c, d: rodape_temp(c, d),
                   onLaterPages=lambda c, d: rodape_temp(c, d))
    
    buffer_temp.seek(0)
    pdf_reader = PdfReader(buffer_temp)
    total_paginas = len(pdf_reader.pages)
    
    # Segunda passada - PDF final
    doc_final = SimpleDocTemplate(buffer, pagesize=pagesize,
                                  topMargin=topMargin, bottomMargin=bottomMargin,
                                  leftMargin=leftMargin, rightMargin=rightMargin)
    
    def rodape_final(canvas, doc):
        if doc.page == 1:
            return
        rodape_followup(canvas, doc, total_paginas)
    
    doc_final.build(story, onFirstPage=lambda c, d: rodape_final(c, d),
                    onLaterPages=lambda c, d: rodape_final(c, d))
    
    buffer.seek(0)
    return buffer.getvalue()