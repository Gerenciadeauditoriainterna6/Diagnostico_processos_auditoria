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

# ====== CONSTANTES ======
COR_PRIMARIA = '#0b5b99'
COR_SECUNDARIA = '#184145'
COR_DESTAQUE = '#fd6a14'
COR_FUNDO_TABELA = '#e8f4f8'
COR_RODAPE = '#F0F0F0'

# ====== MAPA DE RISCO PARA CÁLCULO RESIDUAL ======
MAPA_RISCO = {
    ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14, ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
    ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10, ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
    ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6, ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
    ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2, ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
}

def calcular_risco_residual(apetite_impacto, apetite_probabilidade):
    """
    Calcula o risco residual baseado no apetite ao risco
    Retorna o score ou None se não houver dados
    """
    if not apetite_impacto or not apetite_probabilidade:
        return None
    return MAPA_RISCO.get((apetite_impacto, apetite_probabilidade), None)

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
        'subtitulo': subtitulo_style,
        'normal': normal_style,
        'label': label_style,
        'valor': valor_style,
        'cabecalho_tabela': cabecalho_tabela
    }


# ====== FUNÇÃO PARA DESENHAR OS LOGOS ======
def desenhar_logos(canvas, pagesize, root_dir=None):
    """Desenha os três logos no cabeçalho do relatório"""
    if root_dir is None:
        root_dir = os.path.dirname(os.path.abspath(__file__))
    
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
            canvas.drawImage(img, x - largura/2, y - altura/2, 
                           width=largura, height=altura, mask='auto', 
                           preserveAspectRatio=True)
            return True
        except Exception as e:
            print(f"Erro ao desenhar logo {caminho}: {e}")
            return False
    
    espacamento = pagesize[0] / 4
    x1 = espacamento
    x2 = pagesize[0] / 2
    x3 = pagesize[0] - espacamento
    
    desenhar_png(logo1_path, x2, y_logo, 2.5*cm, altura_max_logo)
    desenhar_png(logo2_path, x1, y_logo, 3.5*cm, 3.5*cm)
    desenhar_png(logo3_path, x3, y_logo, 3*cm, 3*cm)

def formatar_telefone(telefone):
    """
    Formata um número de telefone para o padrão (XX) XXXX-XXXX ou (XX) XXXXX-XXXX
    """
    if not telefone:
        return 'Não informado'
    
    # Remove tudo que não é número
    numeros = re.sub(r'\D', '', str(telefone))
    
    if len(numeros) == 0:
        return 'Não informado'
    
    # Se tiver 10 dígitos: (XX) XXXX-XXXX (telefone fixo)
    if len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:10]}"
    # Se tiver 11 dígitos: (XX) XXXXX-XXXX (celular com 9)
    elif len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:11]}"
    # Se tiver 8 dígitos: XXXX-XXXX (sem DDD)
    elif len(numeros) == 8:
        return f"{numeros[:4]}-{numeros[4:8]}"
    # Se tiver 9 dígitos: XXXXX-XXXX (sem DDD, com 9)
    elif len(numeros) == 9:
        return f"{numeros[:5]}-{numeros[5:9]}"
    # Caso contrário, retorna o número original
    else:
        return telefone

def criar_rodape(canvas, doc, pagesize, total_paginas, titulo_rodape, root_dir=None,
                 email_auditoria=None, telefone_auditoria=None):
    """Cria o rodapé padronizado com logos, email e telefone"""
    canvas.saveState()
    
    altura_rodape = 1.8 * cm
    y_fundo = 0
    
    canvas.setFillColor(colors.HexColor(COR_RODAPE))
    canvas.rect(0, y_fundo, pagesize[0], altura_rodape, fill=1, stroke=0)
    
    # ⭐ LINHA 1: Título e página
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#666666'))
    canvas.drawCentredString(
        pagesize[0]/2, 
        2*cm, 
        f"{titulo_rodape} - Página {doc.page}/{total_paginas}"
    )
    
    # ⭐ LINHA 2: Email e Telefone (COM FORMATAÇÃO)
    if email_auditoria or telefone_auditoria:
        texto_contato = ""
        if email_auditoria and email_auditoria != 'Não informado':
            texto_contato += f"E-mail: {email_auditoria}"
        if telefone_auditoria and telefone_auditoria != 'Não informado':
            if texto_contato:
                texto_contato += " | "
            # ⭐ APLICAR FORMATAÇÃO AO TELEFONE
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
    
    # ⭐ DESENHAR OS LOGOS
    desenhar_logos(canvas, pagesize, root_dir)
    
    canvas.restoreState()


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


def buscar_responsaveis_auditoria(auditoria_id):
    """
    Busca os responsáveis pela auditoria na tabela auditorias
    Retorna uma lista de nomes
    """
    from database import engine
    from sqlalchemy import text
    
    if not auditoria_id:
        return []
    
    with engine.connect() as conn:
        query = text("""
            SELECT responsavel_equipe
            FROM auditorias
            WHERE id = :auditoria_id
        """)
        result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
        
        if result and result[0]:
            # responsavel_equipe é um array text[] no PostgreSQL
            return result[0]  # Já retorna como lista
        return []

# ====== FUNÇÃO PARA CRIAR A PÁGINA DE VALIDAÇÃO ======
def criar_pagina_validacao(story, gestor, styles, normal_style, auditoria_id=None):
    """Adiciona a página de validação do gestor ao story com todos os campos de assinatura"""
    
    # ⭐ ESTILO PARA O TÍTULO DE CADA SEÇÃO
    campo_titulo_style = ParagraphStyle(
        'CampoTitulo',
        parent=normal_style,
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=2
    )
    
    # ⭐ ESTILO PARA O NOME (MAIOR E EM NEGRITO)
    nome_style = ParagraphStyle(
        'NomeStyle',
        parent=normal_style,
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145'),
        spaceAfter=2
    )
    
    # ⭐ ESTILO PARA OS RÓTULOS (Data, etc)
    rotulo_style = ParagraphStyle(
        'RotuloStyle',
        parent=normal_style,
        fontSize=9,
        textColor=colors.HexColor('#666666')
    )
    
    # ⭐ ESTILO PARA A LINHA DE ASSINATURA
    assinatura_style = ParagraphStyle(
        'AssinaturaStyle',
        parent=normal_style,
        fontSize=9,
        alignment=1,  # CENTER
        textColor=colors.HexColor('#666666'),
        spaceAfter=2
    )
    
    # ⭐ ESTILO PARA A LINHA DE ASSINATURA (COM BORDA INFERIOR)
    linha_assinatura_style = ParagraphStyle(
        'LinhaAssinatura',
        parent=normal_style,
        fontSize=9,
        alignment=1,
        textColor=colors.HexColor('#999999'),
        spaceAfter=2
    )
    
    # ⭐ Função auxiliar para criar um bloco de assinatura (SEM QUADRADINHO)
    def criar_bloco_assinatura(titulo, nome_padrao=None):
        """Cria um bloco com Nome, Data e Assinatura (sem bordas)"""
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
        
        # Assinatura (linha com borda inferior apenas)
        dados.append([
            Paragraph("___________________________________________", linha_assinatura_style)
        ])
        dados.append([
            Paragraph("<i>Assinatura</i>", ParagraphStyle(
                'AssinaturaLabel',
                parent=normal_style,
                fontSize=8,
                alignment=1,
                textColor=colors.HexColor('#999999')
            ))
        ])
        
        # ⭐ TABELA SEM BORDAS (apenas com espaçamento)
        tabela = Table(dados, colWidths=[14*cm])
        tabela.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # ⭐ SEM BOX e SEM BACKGROUND para remover o quadradinho
        ]))
        
        return tabela
    
    # ⭐ BUSCAR RESPONSÁVEIS DA AUDITORIA
    responsaveis = []
    if auditoria_id:
        responsaveis = buscar_responsaveis_auditoria(auditoria_id)
    
    # ⭐ INÍCIO DA PÁGINA
    story.append(PageBreak())
    
    # Título principal
    story.append(Paragraph("VALIDAÇÃO", styles['titulo']))
    story.append(Spacer(1, 10))
    
    # Texto de declaração
    story.append(Paragraph(
        "Declaro que tomei ciência dos riscos identificados nos processos da minha área "
        "e comprometo-me a tratar as não conformidades apontadas, conforme plano de ação a ser desenvolvido.",
        normal_style
    ))
    story.append(Spacer(1, 20))
    
    # ⭐ ============================================================
    # 1. GESTOR DA ÁREA
    # ⭐ ============================================================
    story.append(Paragraph("GESTOR DA ÁREA", campo_titulo_style))
    story.append(Spacer(1, 5))
    story.append(criar_bloco_assinatura("Gestor", gestor))
    story.append(Spacer(1, 15))
    
    # ⭐ ============================================================
    # 2. RESPONSÁVEIS PELA AUDITORIA (BUSCADOS DO BANCO)
    # ⭐ ============================================================
    story.append(Paragraph("AUDITORES RESPONSÁVEIS PELA AUDITORIA", campo_titulo_style))
    story.append(Spacer(1, 5))
    
    if responsaveis and len(responsaveis) > 0:
        # Exibir os responsáveis da auditoria
        for idx, responsavel in enumerate(responsaveis, 1):
            story.append(criar_bloco_assinatura(f"Auditor", responsavel))
            story.append(Spacer(1, 8))
    else:
        # Se não houver responsáveis cadastrados, exibir campos em branco
        story.append(criar_bloco_assinatura("Auditor 1"))
        story.append(Spacer(1, 8))
        story.append(criar_bloco_assinatura("Auditor 2"))
    
    story.append(Spacer(1, 15))
    
    # ⭐ ============================================================
    # 3. AUDITOR REVISOR
    # ⭐ ============================================================
    story.append(Paragraph("AUDITOR REVISOR", campo_titulo_style))
    story.append(Spacer(1, 5))
    story.append(criar_bloco_assinatura("Revisor"))
    story.append(Spacer(1, 15))
    
    # ⭐ ============================================================
    # 4. GERENTE DE AUDITORIA INTERNA (EM KEEPTOGETHER)
    # ⭐ ============================================================
    # ⭐ Usar um KeepTogether para manter Gerente + Data + Assinatura na mesma página
    gerente_content = []
    
    gerente_content.append(Paragraph("GERENTE DE AUDITORIA INTERNA", campo_titulo_style))
    gerente_content.append(Spacer(1, 5))
    
    # Criar o bloco do gerente
    gerente_dados = []
    
    # Nome (fixo)
    gerente_dados.append([
        Paragraph("<b>Gerente:</b> Teófilo Gaio Boto", nome_style)
    ])
    
    # Data
    gerente_dados.append([
        Paragraph("<b>Data:</b> ____/____/________", rotulo_style)
    ])
    
    # Assinatura
    gerente_dados.append([
        Paragraph("___________________________________________", linha_assinatura_style)
    ])
    gerente_dados.append([
        Paragraph("<i>Assinatura</i>", ParagraphStyle(
            'AssinaturaLabel',
            parent=normal_style,
            fontSize=8,
            alignment=1,
            textColor=colors.HexColor('#999999')
        ))
    ])
    
    tabela_gerente = Table(gerente_dados, colWidths=[14*cm])
    tabela_gerente.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    gerente_content.append(tabela_gerente)
    gerente_content.append(Spacer(1, 10))
    
    # ⭐ Aplicar KeepTogether para manter o conteúdo do gerente junto
    from reportlab.platypus import KeepTogether
    story.append(KeepTogether(gerente_content))
    
    # ⭐ ============================================================
    # OBSERVAÇÃO FINAL (opcional)
    # ⭐ ============================================================
    obs_style = ParagraphStyle(
        'ObsStyle',
        parent=normal_style,
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=1
    )

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

def buscar_dados_gerencia_auditoria():
    """
    Busca os dados da Gerência de Auditoria Interna na tabela informacoes_area
    Retorna o email e telefone da GAI
    """
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT email, telefone 
                FROM informacoes_area 
                WHERE nome_area ILIKE '%Auditoria Interna%' 
                   OR nome_area ILIKE '%GAI%'
                   OR id_area = 99 
                LIMIT 1
            """)
            result = conn.execute(query).fetchone()
            
            if result:
                telefone = result[1] or '(21) 99999-9999'
                # ⭐ APLICAR FORMATAÇÃO
                telefone_formatado = formatar_telefone(telefone)
                return {
                    'email': result[0] or 'auditoria@fusve.com.br',
                    'telefone': telefone_formatado
                }
            else:
                return {
                    'email': 'auditoria@fusve.com.br',
                    'telefone': '(21) 99999-9999'
                }
    except Exception as e:
        print(f"⚠️ Erro ao buscar dados da GAI: {e}")
        return {
            'email': 'auditoria@fusve.com.br',
            'telefone': '(21) 99999-9999'
        }

# ============================================================
# ====== FIM FUNÇÕES AUXILIARES PARA RELATÓRIOS ======
# ============================================================

def gerar_validacao_relatorio_panorama(area_id, area_nome, gestor, cargo, orientacao="RETRATO", auditoria_id=None, processo_id=None):

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
    
    # ===== CONSTRUIR O STORY =====
    story = []
    
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
    logo_auditoria_path = os.path.join(root_dir, "static", "assets", "logo_auditoria_circulo.png")

    header_data = []
    tem_logo = os.path.exists(logo_auditoria_path)

    if tem_logo:
        img_central = Image(logo_auditoria_path, width=2*cm, height=2*cm)
        header_data = [[img_central]]
        header_table = Table(header_data, colWidths=[pagesize[0] - leftMargin - rightMargin])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), -5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
    
    print(f"📄 Após cabeçalho: {len(story)} elementos")

    # ===== 4b. TÍTULO =====
    titulo_style = styles['titulo']
    titulo_style2 = styles['titulo2']
    story.append(Paragraph("Relatório de Validação", titulo_style))
    story.append(Paragraph("Matriz de Panorama", titulo_style2))
    story.append(Spacer(1, 5))

    print(f"📄 Após título: {len(story)} elementos")
    
    # ===== 4c. INFORMAÇÕES DA AUDITORIA E ÁREA =====
    # Buscar código da auditoria
    codigo_auditoria = ""
    data_inicio_auditoria = ""
    if auditoria_id:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            query_auditoria = text("SELECT codigo_auditoria, data_inicio FROM auditorias WHERE id = :auditoria_id")
            result_aud = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
            if result_aud:
                codigo_auditoria = result_aud[0]
                data_inicio_auditoria = result_aud[1]
    
    # Formatar data de início se existir
    if data_inicio_auditoria:
        if isinstance(data_inicio_auditoria, str):
            try:
                data_inicio_auditoria = datetime.strptime(data_inicio_auditoria, '%Y-%m-%d')
            except ValueError:
                pass
        if hasattr(data_inicio_auditoria, 'strftime'):
            data_inicio_auditoria = data_inicio_auditoria.strftime('%d/%m/%Y')
        else:
            data_inicio_auditoria = str(data_inicio_auditoria)
    else:
        data_inicio_auditoria = 'Não informado'
    
    # ⭐ ESTILO PARA AS INFORMAÇÕES
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
    
    data_emissao = datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')
    
    info_data = [
        [Paragraph("<b>Auditoria:</b>", info_label_style), Paragraph(codigo_auditoria or 'N/A', info_valor_style)],
        [Paragraph("<b>Data de Início da Auditoria:</b>", info_label_style), Paragraph(data_inicio_auditoria, info_valor_style)],
        [Paragraph("<b>Data/Hora de Emissão:</b>", info_label_style), Paragraph(data_emissao, info_valor_style)],
    ]
    
    # ⭐ CALCULAR LARGURAS
    largura_label_info = 4.5 * cm
    largura_valor_info = pagesize[0] - leftMargin - rightMargin - largura_label_info - 2*cm
    
    info_table = Table(info_data, colWidths=[largura_label_info, largura_valor_info])
    info_table.setStyle(TableStyle([
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
    story.append(info_table)
    story.append(Spacer(1, 15))

    print(f"📄 Após informações: {len(story)} elementos")

    # ===== 4d. INFORMAÇÕES COMPLETAS DA ÁREA =====
    story.append(Paragraph("Informações da Área", styles['subtitulo']))
    story.append(Spacer(1, 5))
    
    # ⭐ ESTILO COM QUEBRA DE LINHA PARA OS TEXTOS DA ÁREA
    texto_area_style = ParagraphStyle(
        'TextoArea',
        parent=normal_style,
        fontSize=9,
        leading=11,
        wordWrap='CJK'  # ⭐ FORÇA QUEBRA DE LINHA
    )
    
    label_area_style = ParagraphStyle(
        'LabelArea',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145')
    )
    
    info_area_data = [
        [Paragraph("Código da Área:", label_area_style), Paragraph(str(area_id), texto_area_style)],
        [Paragraph("Nome da Área:", label_area_style), Paragraph(area_nome, texto_area_style)],
        [Paragraph("Gestor Responsável:", info_label_style), Paragraph(f"{area_gestor} - {area_cargo}", info_valor_style)],
        [Paragraph("E-mail:", label_area_style), Paragraph(area_email, texto_area_style)],  # ⭐ NOVO
        [Paragraph("Telefone:", label_area_style), Paragraph(area_telefone or 'Não informado', texto_area_style)],
        [Paragraph("Unidade:", label_area_style), Paragraph(area_unidade or 'Não informado', texto_area_style)],
        [Paragraph("Objetivo da Área:", label_area_style), Paragraph(area_objetivo or 'Não informado', texto_area_style)],
        [Paragraph("Superintendente:", label_area_style), Paragraph(area_superintendente or 'Não informado', texto_area_style)],
        [Paragraph("Diretor:", label_area_style), Paragraph(area_diretor or 'Não informado', texto_area_style)],
    ]
    
    # ⭐ CALCULAR LARGURAS DINÂMICAS
    largura_label_area = 4.5 * cm
    largura_valor_area = pagesize[0] - leftMargin - rightMargin - largura_label_area - 2*cm
    
    info_area_table = Table(info_area_data, colWidths=[largura_label_area, largura_valor_area])
    info_area_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
    ]))
    story.append(info_area_table)
    story.append(Spacer(1, 15))

    print(f"📄 Após informações da área: {len(story)} elementos")

    # ===== 4e. FUNCIONÁRIOS DA ÁREA =====
    story.append(Paragraph("Funcionários da Área", styles['subtitulo']))
    story.append(Spacer(1, 5))
    
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
    
    story.append(Spacer(1, 15))

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
        leftIndent=10
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
        
        if proc.get('objetivo'):
            info_processo.append([
                Paragraph("<b>Objetivo do Processo:</b>", card_texto_style),
                Paragraph(proc['objetivo'], texto_processo_style)  # ⭐ SEM TRUNCAMENTO
            ])
        
        if proc.get('descricao'):
            info_processo.append([
                Paragraph("<b>Descrição do Processo:</b>", card_texto_style),
                Paragraph(proc['descricao'], texto_processo_style)  # ⭐ SEM TRUNCAMENTO
            ])
        
        # ⭐ EXECUTOR - SEMPRE MOSTRAR, MESMO SE VAZIO
        executor_valor = proc.get('executor') or 'Não informado'
        info_processo.append([
            Paragraph("<b>Executor(es):</b>", card_texto_style),
            Paragraph(executor_valor, texto_processo_style)
        ])
        
        if proc.get('etapa_ini'):
            info_processo.append([
                Paragraph("<b>Onde Inicia?:</b>", card_texto_style),
                Paragraph(proc['etapa_ini'], texto_processo_style)
            ])
        
        if proc.get('etapa_fim'):
            info_processo.append([
                Paragraph("<b>Onde Termina?:</b>", card_texto_style),
                Paragraph(proc['etapa_fim'], texto_processo_style)
            ])
        
        if proc.get('produto'):
            info_processo.append([
                Paragraph("<b>Qual o Produto Gerado?:</b>", card_texto_style),
                Paragraph(proc['produto'], texto_processo_style)
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
                
                # Coluna 1: Fator de Risco, Categoria, Causas
                if risco.get('fator_risco'):
                    info_risco.append([
                        Paragraph("<b>Fator de Risco:</b>", risco_item_style),
                        Paragraph(risco['fator_risco'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
                    ])
                
                if risco.get('categoria'):
                    info_risco.append([
                        Paragraph("<b>Categoria do Risco:</b>", risco_item_style),
                        Paragraph(risco['categoria'], texto_risco_style)  # ⭐ SEM TRUNCAMENTO
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
    criar_pagina_validacao(story, area_gestor, styles, normal_style, auditoria_id)
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


def gerar_validacao_relatorio_detalhamento(area_id, area_nome, gestor, cargo, orientacao="RETRATO", auditoria_id=None, processo_id=None):
    """
    Gera relatório de validação - Matriz Detalhamento
    Contém: informações da área, funcionários, processos, etapas, riscos e controles
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
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
    
    # ===== CONSTRUIR O STORY =====
    story = []
    
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

    if tem_logo:
        img_central = Image(logo_auditoria_path, width=2*cm, height=2*cm)
        header_data = [[img_central]]
        header_table = Table(header_data, colWidths=[pagesize[0] - leftMargin - rightMargin])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), -5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
    
    # ===== 4b. TÍTULO =====
    titulo_style = styles['titulo']
    titulo_style2 = styles['titulo2']
    story.append(Paragraph("Relatório de Validação", titulo_style))
    story.append(Paragraph("Matriz de Detalhamento", titulo_style2))
    story.append(Spacer(1, 5))
    
    # ===== 4c. INFORMAÇÕES DA AUDITORIA E ÁREA =====
    codigo_auditoria = ""
    data_inicio_auditoria = ""
    if auditoria_id:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            query_auditoria = text("SELECT codigo_auditoria, data_inicio FROM auditorias WHERE id = :auditoria_id")
            result_aud = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
            if result_aud:
                codigo_auditoria = result_aud[0]
                data_inicio_auditoria = result_aud[1]
    
    if data_inicio_auditoria:
        try:
            if isinstance(data_inicio_auditoria, str):
                from datetime import datetime
                data_inicio_auditoria = datetime.strptime(data_inicio_auditoria, '%Y-%m-%d').strftime('%d/%m/%Y')
            elif hasattr(data_inicio_auditoria, 'strftime'):
                data_inicio_auditoria = data_inicio_auditoria.strftime('%d/%m/%Y')
            else:
                data_inicio_auditoria = str(data_inicio_auditoria)
        except:
            data_inicio_auditoria = str(data_inicio_auditoria)
    else:
        data_inicio_auditoria = 'Não informado'
    
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
    
    info_data = [
        [Paragraph("<b>Auditoria:</b>", info_label_style), Paragraph(codigo_auditoria or 'N/A', info_valor_style)],
        [Paragraph("<b>Data de Início da Auditoria:</b>", info_label_style), Paragraph(data_inicio_auditoria, info_valor_style)],
        [Paragraph("<b>Data/Hora de Emissão:</b>", info_label_style), Paragraph(datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M'), info_valor_style)],
    ]
    
    largura_label_info = 4.5 * cm
    largura_valor_info = pagesize[0] - leftMargin - rightMargin - largura_label_info - 2*cm
    
    info_table = Table(info_data, colWidths=[largura_label_info, largura_valor_info])
    info_table.setStyle(TableStyle([
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
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # ===== 4d. INFORMAÇÕES COMPLETAS DA ÁREA =====
    story.append(Paragraph("Informações da Área", styles['subtitulo']))
    story.append(Spacer(1, 5))
    
    texto_area_style = ParagraphStyle(
        'TextoArea',
        parent=normal_style,
        fontSize=9,
        leading=11,
        wordWrap='CJK'
    )
    
    label_area_style = ParagraphStyle(
        'LabelArea',
        parent=normal_style,
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#184145')
    )
    
    info_area_data = [
        [Paragraph("Código da Área:", label_area_style), Paragraph(str(area_id), texto_area_style)],
        [Paragraph("Nome da Área:", label_area_style), Paragraph(area_nome, texto_area_style)],
        [Paragraph("Gestor Responsável:", info_label_style), Paragraph(f"{area_gestor} - {area_cargo}", texto_area_style)],
        [Paragraph("E-mail:", label_area_style), Paragraph(area_email, texto_area_style)],
        [Paragraph("Telefone:", label_area_style), Paragraph(area_telefone or 'Não informado', texto_area_style)],
        [Paragraph("Unidade:", label_area_style), Paragraph(area_unidade or 'Não informado', texto_area_style)],
        [Paragraph("Objetivo da Área:", label_area_style), Paragraph(area_objetivo or 'Não informado', texto_area_style)],
        [Paragraph("Superintendente:", label_area_style), Paragraph(area_superintendente or 'Não informado', texto_area_style)],
        [Paragraph("Diretor:", label_area_style), Paragraph(area_diretor or 'Não informado', texto_area_style)],
    ]
    
    largura_label_area = 4.5 * cm
    largura_valor_area = pagesize[0] - leftMargin - rightMargin - largura_label_area - 2*cm
    
    info_area_table = Table(info_area_data, colWidths=[largura_label_area, largura_valor_area])
    info_area_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
    ]))
    story.append(info_area_table)
    story.append(Spacer(1, 15))
    
    # ===== 4e. FUNCIONÁRIOS DA ÁREA =====
    story.append(Paragraph("Funcionários da Área", styles['subtitulo']))
    story.append(Spacer(1, 5))
    
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
    
    story.append(Spacer(1, 15))
    
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
        leftIndent=10
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
        wordWrap='CJK'
    )
    
    texto_etapa_style = ParagraphStyle(
        'TextoEtapa',
        parent=normal_style,
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        leftIndent=10
    )
    
    texto_processo_style = ParagraphStyle(
        'TextoProcesso',
        parent=normal_style,
        fontSize=8,
        leading=10,
        wordWrap='CJK'
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
            return "🔴"
        elif magnitude >= 8:
            return "🟠"
        elif magnitude >= 4:
            return "🟡"
        else:
            return "🟢"
    
    # Para cada processo
    for proc_idx, proc in enumerate(processos):
        if proc_idx > 0:
            story.append(PageBreak())
        
        codigo = proc.get('codigo_processo', '-')
        nome = proc.get('nome_processo', '-')
        etapas = proc.get('etapas', [])
        
        # ============================================================
        # CABEÇALHO DO PROCESSO
        # ============================================================
        story.append(Paragraph(f"<b>📋 PROCESSO {codigo}: {nome}</b>", card_titulo_style))
        story.append(Spacer(1, 3))
        
        # Informações do processo
        info_processo = []
        
        if proc.get('objetivo'):
            info_processo.append([
                Paragraph("<b>Objetivo:</b>", card_texto_style),
                Paragraph(limitar_texto(proc['objetivo'], 120), texto_processo_style)
            ])
        
        if proc.get('descricao'):
            info_processo.append([
                Paragraph("<b>Descrição:</b>", card_texto_style),
                Paragraph(limitar_texto(proc['descricao'], 120), texto_processo_style)
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
        
        if proc.get('etapa_fim'):
            info_processo.append([
                Paragraph("<b>Fim:</b>", card_texto_style),
                Paragraph(proc['etapa_fim'], texto_processo_style)
            ])
        
        if proc.get('produto'):
            info_processo.append([
                Paragraph("<b>Produto:</b>", card_texto_style),
                Paragraph(proc['produto'], texto_processo_style)
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
        else:
            for etapa_idx, etapa in enumerate(etapas):
                if etapa_idx > 0 and etapa_idx % 3 == 0:
                    story.append(PageBreak())
                
                # ⭐ SEPARADOR ENTRE ETAPAS
                if etapa_idx > 0:
                    story.append(Paragraph("─" * 80, linha_divisoria_style))
                    story.append(Spacer(1, 5))
                
                # ⭐ TÍTULO DA ETAPA
                etapa_codigo = etapa.get('codigo_etapa', '')
                etapa_nome = etapa.get('nome_etapa', 'Etapa sem nome')
                
                story.append(Paragraph(f"<b>📌 Etapa {etapa_codigo}: {etapa_nome}</b>", card_subtitulo_style))
                story.append(Spacer(1, 2))
                
                # Informações da etapa
                info_etapa = []
                
                if etapa.get('descricao_etapa'):
                    info_etapa.append([
                        Paragraph("<b>Descrição:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['descricao_etapa'], 150), texto_etapa_style)
                    ])

                if etapa.get('como_e_feito'):
                    info_etapa.append([
                        Paragraph("<b>Como é feito:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['como_e_feito'], 150), texto_etapa_style)
                    ])

                if etapa.get('objetivo_etapa'):
                    info_etapa.append([
                        Paragraph("<b>Objetivo da Etapa:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['objetivo_etapa'], 150), texto_etapa_style)
                    ])

                if etapa.get('politica_interna'):
                    info_etapa.append([
                        Paragraph("<b>Política Interna:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['politica_interna'], 150), texto_etapa_style)
                    ])

                if etapa.get('obrigacoes_regulatorias'):
                    info_etapa.append([
                        Paragraph("<b>Obrigações Regulatórias:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['obrigacoes_regulatorias'], 150), texto_etapa_style)
                    ])

                if etapa.get('analise_critica'):
                    info_etapa.append([
                        Paragraph("<b>Análise Crítica:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['analise_critica'], 150), texto_etapa_style)
                    ])

                if etapa.get('sugestao_melhoria'):
                    info_etapa.append([
                        Paragraph("<b>Sugestão de Melhoria:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['sugestao_melhoria'], 150), texto_etapa_style)
                    ])

                if etapa.get('necessidade_implantacao'):
                    info_etapa.append([
                        Paragraph("<b>Necessidade para Implantação:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['necessidade_implantacao'], 150), texto_etapa_style)
                    ])

                if etapa.get('ganho_previsto'):
                    info_etapa.append([
                        Paragraph("<b>Ganho Previsto:</b>", card_texto_style),
                        Paragraph(limitar_texto(etapa['ganho_previsto'], 150), texto_etapa_style)
                    ])
                
                # Manual da etapa
                manual_em_andamento = etapa.get('manual_em_andamento', False)
                manual_nome = etapa.get('manual_nome', '')
                
                if manual_em_andamento:
                    status_manual = "📝 Em andamento (aguardando finalização)"
                elif manual_nome:
                    status_manual = f"✅ Concluído - {manual_nome}"
                else:
                    status_manual = "❌ Não anexado"
                
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
                if riscos:
                    story.append(Paragraph("<b>⚠️ Riscos Identificados</b>", secao_titulo_style))
                    story.append(Spacer(1, 3))
                    
                    for risco_idx, risco in enumerate(riscos):
                        # ⭐ SEPARADOR ENTRE RISCOS
                        if risco_idx > 0:
                            story.append(Paragraph("•" * 70, linha_divisoria_style))
                            story.append(Spacer(1, 3))
                        
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
                                Paragraph(limitar_texto(risco['categoria'], 100), texto_risco_style)
                            ])

                        if risco.get('fator_risco'):
                            info_risco.append([
                                Paragraph("<b>Fator de Risco:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['fator_risco'], 120), texto_risco_style)
                            ])

                        if risco.get('consequencia'):
                            info_risco.append([
                                Paragraph("<b>Consequência:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['consequencia'], 120), texto_risco_style)
                            ])

                        if risco.get('causas'):
                            info_risco.append([
                                Paragraph("<b>Categoria de Causa:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['causas'], 120), texto_risco_style)
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
                                Paragraph(limitar_texto(risco['motivo_classificacao'], 100), texto_risco_style)
                            ])

                        if risco.get('tratamento'):
                            info_risco.append([
                                Paragraph("<b>Tratamento:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['tratamento'], 100), texto_risco_style)
                            ])

                        if risco.get('desc_tratamento'):
                            info_risco.append([
                                Paragraph("<b>Descrição do Tratamento:</b>", card_texto_style),
                                Paragraph(limitar_texto(risco['desc_tratamento'], 100), texto_risco_style)
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
                        if controles:
                            # ⭐ TÍTULO DOS CONTROLES
                            story.append(Paragraph("<b>📋 Controles para este risco</b>", subsecao_titulo_style))
                            story.append(Spacer(1, 2))
                            
                            for controle_idx, controle in enumerate(controles):
                                # ⭐ DESTAQUE PARA CADA CONTROLE
                                if controle_idx > 0:
                                    story.append(Spacer(1, 2))
                                
                                texto_controle = []
                                texto_controle.append(f"<b>Controle {controle_idx + 1}:</b> {controle.get('nome_controle', 'Controle não nomeado')}")
                                
                                if risco.get('fator_risco'):
                                    texto_controle.append(f"  • <b>Fator de Risco:</b> {limitar_texto(risco['fator_risco'], 80)}")
                                
                                if controle.get('objetivo_controle'):
                                    texto_controle.append(f"  • <b>Objetivo:</b> {limitar_texto(controle['objetivo_controle'], 80)}")
                                
                                if controle.get('forma_execucao'):
                                    texto_controle.append(f"  • <b>Forma de Execução:</b> {controle['forma_execucao']}")
                                
                                if controle.get('como_executado'):
                                    texto_controle.append(f"  • <b>Como Executado:</b> {limitar_texto(controle['como_executado'], 80)}")
                                
                                if controle.get('natureza'):
                                    texto_controle.append(f"  • <b>Natureza:</b> {controle['natureza']}")
                                
                                if controle.get('periodicidade_execucao'):
                                    texto_controle.append(f"  • <b>Periodicidade:</b> {controle['periodicidade_execucao']}")
                                
                                if controle.get('evidencia_realizacao'):
                                    texto_controle.append(f"  • <b>Evidência:</b> {limitar_texto(controle['evidencia_realizacao'], 80)}")
                                
                                if controle.get('frequencia_evidencia'):
                                    texto_controle.append(f"  • <b>Frequência da Evidência:</b> {controle['frequencia_evidencia']}")
                                
                                if controle.get('local_evidencia'):
                                    texto_controle.append(f"  • <b>Local da Evidência:</b> {controle['local_evidencia']}")
                                
                                if controle.get('lgpd'):
                                    texto_controle.append(f"  • <b>LGPD:</b> {controle['lgpd']}")
                                
                                if controle.get('status_controle'):
                                    status_texto = controle['status_controle']
                                    if 'Ativo' in status_texto or 'ativo' in status_texto:
                                        status_texto = f"✅ {status_texto}"
                                    elif 'Inativo' in status_texto or 'inativo' in status_texto:
                                        status_texto = f"❌ {status_texto}"
                                    elif 'Em andamento' in status_texto or 'em andamento' in status_texto:
                                        status_texto = f"🔄 {status_texto}"
                                    texto_controle.append(f"  • <b>Status:</b> {status_texto}")
                                
                                if controle.get('responsaveis_tratamento'):
                                    texto_controle.append(f"  • <b>Responsável:</b> {controle['responsaveis_tratamento']}")
                                
                                story.append(Paragraph("<br/>".join(texto_controle), texto_controle_style))
                        else:
                            story.append(Paragraph("<i>Nenhum controle cadastrado para este risco.</i>", normal_style))
                        
                        story.append(Spacer(1, 5))
                else:
                    story.append(Paragraph("<i>Nenhum risco cadastrado para esta etapa.</i>", normal_style))
        
        story.append(Spacer(1, 10))
    
    # ===== 4g. PÁGINA DE VALIDAÇÃO DO GESTOR =====
    criar_pagina_validacao(story, area_gestor, styles, normal_style, auditoria_id)

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
                AND (e.status_etapa = 'Ativa' OR e.status_etapa IS NULL)
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
                    r.probabilidade_aceitavel
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
                    'apetite_impacto': risco[13],      # ⭐ impacto_aceitavel
                    'apetite_probabilidade': risco[14], # ⭐ probabilidade_aceitavel
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


def gerar_relatorio_gerencial_area(area_id, area_nome, gestor, cargo, orientacao="RETRATO", auditoria_id=None, processo_id=None):
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
    from zoneinfo import ZoneInfo
    from logic import get_estilo_risco
    from PyPDF2 import PdfReader
    from PIL import Image as PILImage
    from reportlab.lib.utils import ImageReader
    import copy
    
    buffer = io.BytesIO()

    TZ_BRASILIA = ZoneInfo('America/Sao_Paulo')
    
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
    
    # ===== CONSTRUIR O STORY (conteúdo do relatório) =====
    story = []
    
    # ===== CABEÇALHO COM LOGOS =====
    root_dir = os.path.dirname(os.path.abspath(__file__))
    logo_auditoria_path = os.path.join(root_dir, "static", "assets", "logo_auditoria_circulo.png")

    header_data = []
    tem_logo = os.path.exists(logo_auditoria_path)

    if tem_logo:
        img_central = Image(logo_auditoria_path, width=2*cm, height=2*cm)
        header_data = [[img_central]]
        header_table = Table(header_data, colWidths=[16*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), -5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))

    # ===== TÍTULO =====
    if processo_id:
        titulo = f"Relatório de Validação - Processo {processo_id}"
    else:
        titulo = "Relatório de Validação (Matrizes Panorama e Detalhamento)"
    story.append(Paragraph(titulo, titulo_style))
    
    # Buscar código da auditoria
    codigo_auditoria = ""
    if auditoria_id:
        with engine.connect() as conn:
            query_auditoria = text("SELECT codigo_auditoria FROM auditorias WHERE id = :auditoria_id")
            result_aud = conn.execute(query_auditoria, {'auditoria_id': auditoria_id}).fetchone()
            if result_aud:
                codigo_auditoria = result_aud[0]
    
    # Informações
    story.append(Paragraph(f"Auditoria: {codigo_auditoria}", normal_style))
    story.append(Paragraph(f"Área: {area_nome}", normal_style))
    story.append(Paragraph(f"Gestor Responsável e Cargo: {gestor} - {cargo}", normal_style))
    story.append(Paragraph(f"Data/Hora de Emissão: {datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')}", normal_style))
    story.append(Spacer(1, 20))
    
    # ===== BUSCAR PROCESSOS =====
    if processo_id:
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
            WHERE p.auditoria_id = :auditoria_id 
              AND p.id_area = :area_id 
              AND p.status = 'Ativo'
              AND p.id = :processo_id
            ORDER BY 
                string_to_array(p.codigo_processo, '.')::int[],
                r.score_risco DESC NULLS LAST
        """)
        params = {"area_id": area_id, "auditoria_id": auditoria_id, "processo_id": processo_id}
    else:
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
            WHERE p.auditoria_id = :auditoria_id 
              AND p.id_area = :area_id 
              AND p.status = 'Ativo'
            ORDER BY 
                string_to_array(p.codigo_processo, '.')::int[],
                r.score_risco DESC NULLS LAST
        """)
        params = {"area_id": area_id, "auditoria_id": auditoria_id}
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)
    
    if df.empty:
        raise Exception("Nenhum processo encontrado para os critérios selecionados.")
    
    total_riscos = df['risco_id'].notna().sum()
    
    if processo_id:
        story.append(Paragraph(f"Processo selecionado: {df.iloc[0]['codigo_processo']} - {df.iloc[0]['nome_processo']}", normal_style))
        story.append(Spacer(1, 10))
    
    story.append(Paragraph(f"Quantidade de Riscos identificados: {total_riscos}", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Processos e Riscos Identificados", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    data = [[
        Paragraph("Código", normal_style),
        Paragraph("Processo", normal_style),
        Paragraph("Risco Identificado", normal_style),
        Paragraph("Risco Bruto", normal_style)
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
            risco_bruto = Paragraph(f'<font color="{cor_risco}">{texto_score}</font>', normal_style)
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
    story.append(Paragraph("Detalhamento dos Processos", styles['Heading1']))
    story.append(Spacer(1, 15))
    
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
    
    def add_separador(cor=colors.HexColor('#cccccc'), espaco_antes=5, espaco_depois=5):
        story.append(Spacer(1, espaco_antes))
        sep_data = [['']]
        sep_table = Table(sep_data, colWidths=[pagesize[0] - leftMargin - rightMargin])
        sep_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, cor),
        ]))
        story.append(sep_table)
        story.append(Spacer(1, espaco_depois))
    
    if processo_id:
        query_processos = text("""
            SELECT p.id, p.codigo_processo, p.nome_processo, p.objetivo,
                p.descricao, p.etapa_ini, p.etapa_fim, p.produto
            FROM processos p
            WHERE p.auditoria_id = :auditoria_id 
            AND p.id_area = :area_id 
            AND p.status = 'Ativo'
            AND p.id = :processo_id
            GROUP BY p.id, p.codigo_processo, p.nome_processo, p.objetivo,
                    p.descricao, p.etapa_ini, p.etapa_fim, p.produto
            ORDER BY string_to_array(p.codigo_processo, '.')::int[]
        """)
        params_processos = {"area_id": area_id, "auditoria_id": auditoria_id, "processo_id": processo_id}
    else:
        query_processos = text("""
            SELECT p.id, p.codigo_processo, p.nome_processo, p.objetivo,
                p.descricao, p.etapa_ini, p.etapa_fim, p.produto
            FROM processos p
            WHERE p.auditoria_id = :auditoria_id 
            AND p.id_area = :area_id 
            AND p.status = 'Ativo'
            GROUP BY p.id, p.codigo_processo, p.nome_processo, p.objetivo,
                    p.descricao, p.etapa_ini, p.etapa_fim, p.produto
            ORDER BY string_to_array(p.codigo_processo, '.')::int[]
        """)
        params_processos = {"area_id": area_id, "auditoria_id": auditoria_id}
    
    with engine.connect() as conn:
        processos = conn.execute(query_processos, params_processos).fetchall()
    
    for idx, proc in enumerate(processos):
        proc_id = proc[0]
        proc_codigo = proc[1]
        proc_nome = proc[2]
        proc_objetivo = proc[3] or 'Não informado'
        proc_descricao = proc[4] or ''
        proc_etapa_ini = proc[5] or ''
        proc_etapa_fim = proc[6] or ''
        proc_produto = proc[7] or ''
        
        if idx > 0:
            story.append(PageBreak())
        
        story.append(Paragraph(
            f"Processo: {proc_codigo} - {proc_nome}",
            styles['Heading2']
        ))
        story.append(Spacer(1, 5))

        # Buscar executores
        query_executores = text("""
            SELECT f.nome_funcionario, f.cargo
            FROM processo_executores pe
            JOIN funcionarios_area f ON pe.funcionario_id = f.id
            WHERE pe.processo_id = :processo_id
            ORDER BY f.nome_funcionario
        """)

        with engine.connect() as conn:
            executores = conn.execute(query_executores, {"processo_id": proc_id}).fetchall()
        executores_text = ', '.join([f"{e[0]} ({e[1]})" if e[1] else e[0] for e in executores]) if executores else 'Não informado'
        
        info_data = [
            [Paragraph("Objetivo:", normal_style), Paragraph(proc_objetivo, normal_style)],
            [Paragraph("O que é o processo?:", normal_style), Paragraph(proc_descricao or 'Não informado', normal_style)],
            [Paragraph("Onde começa?:", normal_style), Paragraph(proc_etapa_ini or 'Não informado', normal_style)],
            [Paragraph("Produto final:", normal_style), Paragraph(proc_produto or 'Não informado', normal_style)],
            [Paragraph("Para onde envia?:", normal_style), Paragraph(proc_etapa_fim or 'Não informado', normal_style)],
            [Paragraph("Executores:", normal_style), Paragraph(executores_text, normal_style)]
        ]

        info_table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])

        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(info_table_style)
        story.append(info_table)
        story.append(Spacer(1, 10))
        
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
        
        story.append(Paragraph("Etapas do Processo:", styles['Heading3']))
        story.append(Spacer(1, 5))
        
        for etapa_idx, etapa in enumerate(etapas):
            etapa_id = etapa[0]
            etapa_nome = etapa[1] or 'Etapa sem nome'
            etapa_desc = etapa[2] or ''
            etapa_codigo = etapa[3] or ''
            
            bg_cor = colors.HexColor('#f8f9fa') if etapa_idx % 2 == 0 else colors.white
            
            etapa_header = Paragraph(
                f"Etapa {etapa_codigo}: {etapa_nome}", 
                etapa_header_style
            )
            
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
                riscos_todas = [[
                    Paragraph("Risco", normal_style),
                    Paragraph("Impacto", normal_style),
                    Paragraph("Prob.", normal_style),
                    Paragraph("Score", normal_style),
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
                        Paragraph(f'<font color="{cor_risco}">{score}</font>', normal_style),
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
                
                etapa_conteudo.append([Paragraph("Riscos:", sub_header_style)])
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
                    Paragraph("Controle", normal_style),
                    Paragraph("Como Executado", normal_style),
                    Paragraph("Natureza", normal_style),
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
                
                etapa_conteudo.append([Paragraph("Controles:", sub_header_style)])
                etapa_conteudo.append([tabela_controles])
            
            # Montar tabela da etapa
            etapa_table = Table(etapa_conteudo, colWidths=[pagesize[0] - leftMargin - rightMargin - 20])
            etapa_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_cor),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROUNDEDCORNERS', [4, 4, 4, 4]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(etapa_header)
            story.append(etapa_table)
            story.append(Spacer(1, 8))
        
        if idx < len(processos) - 1:
            add_separador(colors.HexColor('#184145'), 10, 5)
    
    story.append(PageBreak())
    
    # ===== PÁGINA DE VALIDAÇÃO DO GESTOR =====
    story.append(Paragraph("Validação do Gestor", styles['Heading1']))
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "Declaro que tomei ciência dos riscos identificados nos processos da minha área "
        "e comprometo-me a tratar as não conformidades apontadas, conforme plano de ação a ser desenvolvido.",
        normal_style
    ))
    story.append(Spacer(1, 50))
    story.append(Paragraph(f"Gestor: {gestor}", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Data: ___/___/_______", normal_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Assinatura: ________________________________", normal_style))

    # ============================================================
    # ⭐ AQUI ESTÁ A SOLUÇÃO DEFINITIVA ⭐
    # ============================================================
    
    # ⭐ FUNÇÃO PARA DESENHAR LOGOS
    def desenhar_logos(canvas):
        root_dir = os.path.dirname(os.path.abspath(__file__))
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

    # ⭐ PASSO 1: FAZER UMA CÓPIA DO STORY
    story_copy = copy.deepcopy(story)
    
    # ⭐ PASSO 2: GERAR PDF TEMPORÁRIO PARA CONTAR PÁGINAS (USANDO A CÓPIA)
    def rodape_contador(canvas, doc):
        canvas.saveState()
        altura_rodape = 1.8 * cm
        y_fundo = 0
        canvas.setFillColor(colors.HexColor('#F0F0F0'))
        canvas.rect(0, y_fundo, pagesize[0], altura_rodape, fill=1, stroke=0)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        if processo_id and 'proc_codigo' in locals():
            canvas.drawCentredString(pagesize[0]/2, 2*cm, f"Relatório Gerencial - Processo {proc_codigo} - Página {doc.page}")
        else:
            canvas.drawCentredString(pagesize[0]/2, 2*cm, f"Relatório Gerencial - Área: {area_nome[:50]} - Página {doc.page}")
        desenhar_logos(canvas)
        canvas.restoreState()

    buffer_temp = io.BytesIO()
    doc_temp = SimpleDocTemplate(buffer_temp, pagesize=pagesize,
                                topMargin=topMargin, bottomMargin=bottomMargin,
                                leftMargin=leftMargin, rightMargin=rightMargin)
    
    doc_temp.build(story_copy, onFirstPage=rodape_contador, onLaterPages=rodape_contador)
    
    # ⭐ PASSO 3: CONTAR AS PÁGINAS
    buffer_temp.seek(0)
    pdf_reader = PdfReader(buffer_temp)
    total_paginas = len(pdf_reader.pages)
    
    # ⭐ PASSO 4: GERAR O PDF FINAL COM O TOTAL (USANDO O STORY ORIGINAL)
    def rodape_final(canvas, doc):
        canvas.saveState()
        
        altura_rodape = 1.8 * cm
        y_fundo = 0
        
        canvas.setFillColor(colors.HexColor('#F0F0F0'))
        canvas.rect(0, y_fundo, pagesize[0], altura_rodape, fill=1, stroke=0)
        
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        
        if processo_id and 'proc_codigo' in locals():
            canvas.drawCentredString(pagesize[0]/2, 2*cm, 
                f"Relatório Gerencial - Processo {proc_codigo} - Página {doc.page}/{total_paginas}")
        else:
            canvas.drawCentredString(pagesize[0]/2, 2*cm, 
                f"Relatório Gerencial - Área: {area_nome[:50]} - Página {doc.page}/{total_paginas}")
        
        desenhar_logos(canvas)
        canvas.restoreState()
    
    # ⭐ CONSTRUIR O DOCUMENTO FINAL
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, 
                           topMargin=topMargin, bottomMargin=bottomMargin,
                           leftMargin=leftMargin, rightMargin=rightMargin)
    
    doc.build(story, onFirstPage=rodape_final, onLaterPages=rodape_final)
    buffer.seek(0)
    return buffer.getvalue()

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

def gerar_relatorio_parecer_auditoria(area_id, area_nome, gestor, cargo, auditoria_id, processo_id, 
                                     usuario_nome='Auditor', orientacao="RETRATO", incluir_abr=False):  # ⭐ ADICIONAR AQUI
    """
    Gera relatório de Parecer da Auditoria para um processo específico
    Inclui análises do auditado (etapas) e análises do auditor (checklists)
    
    Parâmetros:
    - incluir_abr: Se True, inclui a seção ABR - Auditoria Baseada em Risco (apenas admin)
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    import io
    import os
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    buffer = io.BytesIO()

    TZ_BRASILIA = ZoneInfo('America/Sao_Paulo')
    
    # Definir orientação
    if orientacao.upper() == "PAISAGEM":
        pagesize = landscape(A4)
    else:
        pagesize = A4
    
    doc = SimpleDocTemplate(buffer, pagesize=pagesize,
                           topMargin=1.5*cm, bottomMargin=2*cm,
                           leftMargin=2*cm, rightMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    # Estilos
    titulo_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=16, alignment=1, spaceAfter=20,
        textColor=colors.HexColor('#0b5b99')
    )

    paragraph_style = ParagraphStyle(
        'CustomParagraph', parent=styles['Normal'],
        fontSize=10, alignment=1, spaceAfter=10,
        textColor=colors.HexColor('#0b5b99')
    )
    
    secao_style = ParagraphStyle(
        'SecaoStyle', parent=styles['Heading2'],
        fontSize=14, spaceAfter=10, spaceBefore=15,
        textColor=colors.HexColor('#184145')
    )
    
    subsecao_style = ParagraphStyle(
        'SubSecaoStyle', parent=styles['Heading3'],
        fontSize=12, spaceAfter=8, spaceBefore=10,
        textColor=colors.HexColor('#0b5b99')
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 9
    
    story = []
    
    # ===== CABEÇALHO COM LOGO CENTRALIZADO =====
    root_dir = os.path.dirname(os.path.abspath(__file__))
    logo_auditoria_path = os.path.join(root_dir, "static", "assets", "logo_auditoria_circulo.png")

    header_data = []
    tem_logo = os.path.exists(logo_auditoria_path)

    if tem_logo:
        img_central = Image(logo_auditoria_path, width=2*cm, height=2*cm)
        
        header_data = [[img_central]]
        
        header_table = Table(header_data, colWidths=[16*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), -5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
    
    story.append(Paragraph("MAPA", titulo_style))
    story.append(Spacer(0, -20))
    story.append(Paragraph("Mapeamento, Auditoria e Processos Avaliados", paragraph_style))
    story.append(Spacer(1, 2))
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
        titulo_auditoria = auditoria_info[1]
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
            SELECT id, nome_etapa, codigo_etapa, descricao_etapa
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
            
            # Buscar análises do auditado
            query_analises_auditado = text("""
                SELECT 
                    ac.id,
                    ac.categoria,
                    ac.analise_critica,
                    ac.sugestao_melhoria,
                    ac.sugestao_sera_implantada,
                    ac.plano_acao,
                    ac.responsavel_implantacao,
                    ac.data_inicio_prevista,
                    ac.data_conclusao_prevista,
                    ac.efetivamente_implantada,
                    ac.data_implantacao_efetiva
                FROM analises_criticas ac
                WHERE ac.etapa_id = :etapa_id AND ac.tipo = 'auditado'
                ORDER BY ac.categoria
            """)
            analises_auditado_raw = conn.execute(query_analises_auditado, {"etapa_id": etapa_id}).fetchall()
            
            analises_auditado_list = []
            for a in analises_auditado_raw:
                # Buscar histórico de andamento
                query_historico = text("""
                    SELECT status, comentario, created_by, created_at
                    FROM analises_historico_andamento
                    WHERE analise_id = :analise_id
                    ORDER BY created_at ASC
                """)
                historico_raw = conn.execute(query_historico, {"analise_id": a[0]}).fetchall()
                
                historico_list = []
                for h in historico_raw:
                    historico_list.append({
                        'data': h[3].strftime('%d/%m/%Y') if h[3] else '',
                        'status': h[0] or '',
                        'comentario': h[1] or '',
                        'created_by': h[2] or ''
                    })
                
                # Buscar follow-ups
                query_followups = text("""
                    SELECT etapa, data_prevista, data_realizada, status, comentario
                    FROM analises_follow_up
                    WHERE analise_id = :analise_id
                    ORDER BY data_prevista ASC
                """)
                followups_raw = conn.execute(query_followups, {"analise_id": a[0]}).fetchall()
                
                followups_list = []
                for f in followups_raw:
                    followups_list.append({
                        'etapa': f[0] or '',
                        'data_prevista': f[1].strftime('%d/%m/%Y') if f[1] else '',
                        'data_realizada': f[2].strftime('%d/%m/%Y') if f[2] else '',
                        'status': f[3] or 'Pendente',
                        'comentario': f[4] or ''
                    })
                
                analises_auditado_list.append({
                    'id': a[0],
                    'categoria': a[1],
                    'analise_critica': a[2] or '',
                    'sugestao_melhoria': a[3] or '',
                    'sugestao_sera_implantada': a[4],
                    'plano_acao': a[5] or '',
                    'responsavel_implantacao': a[6] or '',
                    'data_inicio_prevista': a[7].strftime('%d/%m/%Y') if a[7] else None,
                    'data_conclusao_prevista': a[8].strftime('%d/%m/%Y') if a[8] else None,
                    'efetivamente_implantada': a[9] if a[9] is not None else None,
                    'data_implantacao_efetiva': a[10].strftime('%d/%m/%Y') if a[10] else None,
                    'historico': historico_list,
                    'followups': followups_list
                })
            
            etapas.append({
                'id': etapa_id,
                'nome': etapa_nome,
                'codigo': etapa_codigo,
                'descricao': etapa_desc,
                'analises_auditado': analises_auditado_list,
            })
        
        # ===== 2. BUSCAR ANÁLISES DO AUDITOR PARA O PROCESSO =====
        query_analises_auditor = text("""
            SELECT 
                ac.id,
                ac.analise_critica,
                ac.sugestao_melhoria,
                ac.sugestao_sera_implantada,
                ac.plano_acao,
                ac.responsavel_implantacao,
                ac.data_inicio_prevista,
                ac.data_conclusao_prevista,
                ac.efetivamente_implantada,
                ac.data_implantacao_efetiva,
                ac.created_at
            FROM analises_criticas ac
            WHERE ac.processo_id = :processo_id 
            AND ac.tipo = 'auditor'
            ORDER BY ac.created_at ASC
        """)
        analises_auditor_raw = conn.execute(query_analises_auditor, {"processo_id": proc_id}).fetchall()
        
        analises_auditor_list = []
        for a in analises_auditor_raw:
            analise_id = a[0]
            
            # Buscar histórico de andamento
            query_historico = text("""
                SELECT status, comentario, created_by, created_at
                FROM analises_historico_andamento
                WHERE analise_id = :analise_id
                ORDER BY created_at ASC
            """)
            historico_raw = conn.execute(query_historico, {"analise_id": analise_id}).fetchall()
            
            historico_list = []
            for h in historico_raw:
                historico_list.append({
                    'data': h[3].strftime('%d/%m/%Y') if h[3] else '',
                    'status': h[0] or '',
                    'comentario': h[1] or '',
                    'created_by': h[2] or ''
                })
            
            # Buscar follow-ups
            query_followups = text("""
                SELECT etapa, data_prevista, data_realizada, status, comentario
                FROM analises_follow_up
                WHERE analise_id = :analise_id
                ORDER BY data_prevista ASC
            """)
            followups_raw = conn.execute(query_followups, {"analise_id": analise_id}).fetchall()
            
            followups_list = []
            for f in followups_raw:
                followups_list.append({
                    'etapa': f[0] or '',
                    'data_prevista': f[1].strftime('%d/%m/%Y') if f[1] else '',
                    'data_realizada': f[2].strftime('%d/%m/%Y') if f[2] else '',
                    'status': f[3] or 'Pendente',
                    'comentario': f[4] or ''
                })
            
            analises_auditor_list.append({
                'id': analise_id,
                'analise_critica': a[1] or '',
                'sugestao_melhoria': a[2] or '',
                'sugestao_sera_implantada': a[3],
                'plano_acao': a[4] or '',
                'responsavel_implantacao': a[5] or '',
                'data_inicio_prevista': a[6].strftime('%d/%m/%Y') if a[6] else None,
                'data_conclusao_prevista': a[7].strftime('%d/%m/%Y') if a[7] else None,
                'efetivamente_implantada': a[8] if a[8] is not None else None,
                'data_implantacao_efetiva': a[9].strftime('%d/%m/%Y') if a[9] else None,
                'data_criacao': a[10].strftime('%d/%m/%Y') if a[10] else '',
                'historico': historico_list,
                'followups': followups_list
            })
        
        # ===== 3. BUSCAR MATRIZES DE CHECKLIST (GOVERNANÇA, RISCOS, CONTROLES) =====
        checklist_tipos = ['governanca', 'riscos', 'controles']
        checklist_data = {}
        
        # ⭐ DEFINIR O NÚMERO DE PERGUNTAS PARA CADA TIPO
        perguntas_por_tipo = {
            'governanca': 13,
            'riscos': 12,
            'controles': 12
        }
        
        for tipo in checklist_tipos:
            tabela = f'checklist_{tipo}_respostas'
            num_perguntas = perguntas_por_tipo.get(tipo, 12)
            
            # ⭐ CONSTRUIR A LISTA DE COLUNAS DINAMICAMENTE
            colunas_respostas = ', '.join([f'p{i}_resposta' for i in range(1, num_perguntas + 1)])
            colunas_comentarios = ', '.join([f'p{i}_comentario' for i in range(1, num_perguntas + 1)])
            
            query_checklist = text(f"""
                SELECT 
                    id,
                    status,
                    observacoes_gerais,
                    {colunas_respostas},
                    {colunas_comentarios}
                FROM {tabela}
                WHERE processo_id = :processo_id
                ORDER BY id DESC
                LIMIT 1
            """)
            
            try:
                checklist_result = conn.execute(query_checklist, {"processo_id": proc_id}).fetchone()
                
                if checklist_result:
                    respostas = []
                    for i in range(1, num_perguntas + 1):
                        # Índices: 0=id, 1=status, 2=observacoes
                        # Depois vêm as respostas (num_perguntas colunas)
                        # Depois os comentários (num_perguntas colunas)
                        idx_resposta = 3 + (i - 1)
                        idx_comentario = 3 + num_perguntas + (i - 1)
                        
                        resposta_valor = checklist_result[idx_resposta] if idx_resposta < len(checklist_result) else ''
                        comentario_valor = checklist_result[idx_comentario] if idx_comentario < len(checklist_result) else ''
                        
                        respostas.append({
                            'resposta': resposta_valor or '',
                            'comentario': comentario_valor or ''
                        })
                    
                    checklist_data[tipo] = {
                        'id': checklist_result[0],
                        'status': checklist_result[1] or 'Não iniciado',
                        'observacoes_gerais': checklist_result[2] or '',
                        'respostas': respostas
                    }
                else:
                    checklist_data[tipo] = None
            except Exception as e:
                print(f"Erro ao buscar checklist {tipo}: {e}")
                checklist_data[tipo] = None
    
    # ===== FUNÇÃO PARA DESENHAR TARJA =====
    def cabecalho_com_tarja(canvas, doc):
        canvas.saveState()
        
        status_config = {
            'Inconclusiva': {'cor': (0.86, 0.08, 0.24), 'texto': 'AUDITORIA INCONCLUSIVA'},
            'Em Atraso': {'cor': (0.86, 0.08, 0.24), 'texto': 'AUDITORIA EM ATRASO'},
            'Follow-up': {'cor': (0.99, 0.49, 0.08), 'texto': 'AUDITORIA EM FOLLOW-UP'},
            'Eficácia Validada': {'cor': (0.16, 0.63, 0.27), 'texto': 'AUDITORIA COM EFICÁCIA VALIDADA'},
            'Em Execução': {'cor': (0.09, 0.63, 0.76), 'texto': 'AUDITORIA EM EXECUÇÃO'}
        }
        
        if status in status_config:
            config = status_config[status]
            canvas.setFillColorRGB(config['cor'][0], config['cor'][1], config['cor'][2], 1)
            canvas.rect(0, pagesize[1] - 1.2*cm, pagesize[0], 0.8*cm, fill=1, stroke=0)
            canvas.setFont('Helvetica-Bold', 12)
            canvas.setFillColorRGB(1, 1, 1)
            canvas.drawCentredString(pagesize[0] / 2, pagesize[1] - 0.9*cm, config['texto'])
        
        canvas.restoreState()
    
    status_colors = {
        'Em Execução': colors.HexColor('#17a2b8'),      
        'Eficácia Validada': colors.HexColor('#28a745'), 
        'Follow-up': colors.HexColor("#fded14"),         
        'Em Atraso': colors.HexColor("#dc7235"),         
        'Inconclusiva': colors.HexColor("#ff0000")       
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

    # ===== CONTAR FOLLOW-UPS ATIVOS NO PROCESSO =====
    total_followups_pendentes = 0
    total_followups_em_andamento = 0
    total_melhorias_em_implantacao = 0
    
    # Contar follow-ups pendentes nas análises do auditor
    for analise in analises_auditor_list:
        if analise.get('sugestao_sera_implantada') == True:
            if analise.get('efetivamente_implantada') == False:
                total_melhorias_em_implantacao += 1
            if analise.get('followups'):
                for fu in analise['followups']:
                    if fu['status'] == 'Pendente':
                        total_followups_pendentes += 1
                    elif fu['status'] in ['Aderente', 'Nao aderente', 'Parcialmente aderente']:
                        total_followups_em_andamento += 1
    
    # Contar follow-ups pendentes nas análises do auditado
    for etapa in etapas:
        for analise in etapa['analises_auditado']:
            if analise.get('sugestao_sera_implantada') == True:
                if analise.get('efetivamente_implantada') == False:
                    total_melhorias_em_implantacao += 1
                if analise.get('followups'):
                    for fu in analise['followups']:
                        if fu['status'] == 'Pendente':
                            total_followups_pendentes += 1
                        elif fu['status'] in ['Aderente', 'Nao aderente', 'Parcialmente aderente']:
                            total_followups_em_andamento += 1
    
    # Criar mensagem de alerta
    alerta_followup = ""
    if total_followups_pendentes > 0:
        alerta_followup = f'<font color="#dc5a10"><b>ATENÇÃO: {total_followups_pendentes} follow-up(s) pendente(s) aguardando registro!</b></font>'
    elif total_melhorias_em_implantacao > 0:
        alerta_followup = f'<font color="#ffc107"><b>{total_melhorias_em_implantacao} melhoria(s) em processo de implantação</b></font>'
    elif total_followups_em_andamento > 0:
        alerta_followup = f'<font color="#28a745"><b>{total_followups_em_andamento} follow-up(s) já registrados</b></font>'
    
    info_data = [
        ["Código:", Paragraph(codigo_auditoria or '', cell_style)],
        ["Título:", Paragraph(titulo_auditoria or '', cell_style)],
        ["Área:", Paragraph(area_nome or '', cell_style)],
        ["Gestor:", Paragraph(gestor or '', cell_style)],
        ["Cargo:", Paragraph(cargo or '', cell_style)],
        ["Cronograma Previsto:", Paragraph(f"{data_inicio.strftime('%d/%m/%Y') if data_inicio else '-'} a {data_fim.strftime('%d/%m/%Y') if data_fim else '-'}", cell_style)],
        ["Status da Auditoria:", Paragraph(f"{status_text}{status_atraso_html}", cell_style_2)],
    ]
    
    # ⭐ ADICIONAR ALERTA DE FOLLOW-UP ⭐
    if alerta_followup:
        info_data.append(["", ""])
        info_data.append(["Status dos Follow-ups:", Paragraph(alerta_followup, cell_style_2)])
    
    info_data.append(["", ""])
    info_data.append(["Processo Auditado:", Paragraph(f"{proc_codigo} - {proc_nome}", cell_style)])
    info_data.append(["Data/Hora Emissão:", Paragraph(datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M'), cell_style)])
    
    info_table = Table(info_data, colWidths=[4*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
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
    
    # ===== FUNÇÃO AUXILIAR PARA EXIBIR HISTÓRICO =====
    def adicionar_historico(historico):
        if historico and len(historico) > 0:
            story.append(Paragraph("<b>Histórico de Andamento:</b>", normal_style))
            story.append(Spacer(1, 3))
            
            hist_data = [["Data", "Status", "Comentário", "Registrado por"]]
            for h in historico:
                hist_data.append([
                    Paragraph(h['data'], normal_style),
                    Paragraph(h['status'], normal_style),
                    Paragraph(h['comentario'][:60] + ('...' if len(h['comentario']) > 60 else ''), normal_style),
                    Paragraph(h['created_by'], normal_style)
                ])
            
            tabela_hist = Table(hist_data, colWidths=[2.5*cm, 3*cm, 8*cm, 3.5*cm], repeatRows=1)
            tabela_hist.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.09, 0.25, 0.27, alpha=0.60)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(tabela_hist)
    
    # ===== FUNÇÃO AUXILIAR PARA EXIBIR FOLLOW-UPS =====
    def adicionar_followups(followups):
        if followups and len(followups) > 0:
            story.append(Spacer(1, 5))
            story.append(Paragraph("<b>Follow-ups Pós-Implantação:</b>", normal_style))
            story.append(Spacer(1, 3))
            
            fu_data = [["Etapa", "Data Prevista", "Data Realizada", "Status", "Comentário"]]
            for fu in followups:
                etapa_texto = fu['etapa']
                if '30' in etapa_texto:
                    etapa_texto = '30 dias após implantação'
                elif '60' in etapa_texto:
                    etapa_texto = '60 dias após implantação'
                elif '90' in etapa_texto:
                    etapa_texto = '90 dias após implantação'
                
                status_texto = fu['status']
                if fu['status'] == 'Pendente':
                    status_texto = 'Pendente'
                elif fu['status'] == 'Aderente':
                    status_texto = 'Aderente'
                elif fu['status'] == 'Nao aderente':
                    status_texto = 'Não aderente'
                elif fu['status'] == 'Parcialmente aderente':
                    status_texto = 'Parcialmente aderente'
                
                fu_data.append([
                    Paragraph(etapa_texto, normal_style),
                    Paragraph(fu['data_prevista'], normal_style),
                    Paragraph(fu['data_realizada'] or '-', normal_style),
                    Paragraph(status_texto, normal_style),
                    Paragraph(fu['comentario'][:50] or '-', normal_style)
                ])
            
            tabela_fu = Table(fu_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 3.5*cm, 5*cm], repeatRows=1)
            tabela_fu.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b5b99')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(tabela_fu)

    # ===== PERGUNTAS DOS CHECKLISTS =====
    perguntas_governanca = [
        "O fluxo das etapas e seus objetivos são de fato realizados? Verificando se o que foi feito até agora, segue o padrão relatado no mapeamento? Solicite execuções feitas e compare com o mapeamento. Está cumprindo o que diz fazer?",
        "O fluxo das etapas e seus objetivos são de fato realizados? Fazendo simulações, compare com o mapeamento. Está cumprindo o que diz fazer?",
        "Existem procedimentos operacionais padronizados (POPs) documentados e atualizados para os processos-chave da área?",
        "Os proprietários dos processos e as responsabilidades por resultados e riscos são claramente definidos, conhecidos e aceitos na área?",
        "As decisões operacionais são tomadas no nível hierárquico correto (evitando escalonamentos desnecessários ou decisões tomadas por pessoas sem alçada)?",
        "A gestão da área realiza monitoramento contínuo dos processos?",
        "Os dados e relatórios operacionais reportados à gestão são confiáveis, precisos e utilizados para a tomada de decisão?",
        "Os indicadores de desempenho (KPIs) da área estão alinhados com os objetivos estratégicos da empresa?",
        "Os problemas operacionais e as não conformidades são comunicados à gestão superior no tempo adequado?",
        "A área realiza revisões periódicas do seu próprio desempenho, identificando e implementando melhorias nos processos?",
        "Os recursos (pessoas, tecnologia) alocados para a área são suficientes e adequados para o cumprimento dos objetivos operacionais?",
        "A área demonstra comprometimento ético no dia a dia, aderindo a políticas e reportando desvios sem medo de retaliação?",
        "O Auditado validou por email se existe mapeamento de processos feito pela área escritório de processos?"
    ]

    perguntas_riscos = [
        "Validar se os Riscos e Fator de Riscos estão coerentes com o Objetivo da etapa.",
        "Verificar se os riscos estão atualizados e sendo monitorados pelo gestor de primeira linha.",
        "A área realiza mapeamento de riscos dos seus processos operacionais regularmente (ex: anualmente ou após mudanças significativas)?",
        "Os riscos chave (ex: erro humano, falha de sistema, fraude) estão claramente identificados e documentados pela própria área?",
        "A análise de riscos inclui a avaliação da probabilidade de ocorrência e do impacto financeiro/reputacional/operacional?",
        "Existe um plano de ação formalizado para mitigar os riscos classificados como Alto ou Crítico?",
        "Os controles internos da área foram especificamente desenhados para reduzir os riscos identificados (e não apenas herdados de outros processos)?",
        "A área possui e testa planos de contingência/continuidade de negócios (plano B) para a não interrupção de processos que possuem maiores riscos?",
        "A área monitora indicadores-chave de risco (KRIs) que sinalizam o aumento da exposição aos riscos operacionais?",
                "Os eventos de perda ou incidentes operacionais são registrados, analisados e utilizados para ajustar a avaliação de risco da área?",
        "O Gerente da Área (Primeira Linha de Defesa) revisa e confirma o status dos principais riscos operacionais da sua área periodicamente?",
        "O Auditado validou por email se existe mapeamento de RISCO feito pela área Gerência de riscos e Compliance?"
    ]

    perguntas_controles = [
        "Testar se a Ação dos Controles de fato mitigam os Fatores de Riscos informados na matriz de riscos. Verificando se o que foi feito até agora, segue o padrão relatado no mapeamento? Solicite execuções feitas e compare com o mapeamento. Está cumprindo o que diz fazer?",
        "Testar se a Ação dos Controles de fato mitigam os Fatores de Riscos informados na matriz de riscos. Fazendo simulações, comparando com o mapeamento. Está cumprindo o que diz fazer?",
        "Os controles são preventivos (impedem o erro) sempre que possível, ao invés de apenas detectivos (identificam o erro após a ocorrência)?",
        "Existe segregação de funções adequada dentro dos processos operacionais (ex: quem aprova não é quem executa, quem registra não é quem concilia)?",
        "Os controles automáticos (configurações do sistema) são revisados e testados após atualizações ou mudanças no sistema?",
        "O passo do controle (ex: revisão, aprovação, conciliação) é realizado na frequência exigida e sem exceções não autorizadas?",
        "O responsável pelo controle deixa evidência clara (assinatura, log do sistema, captura de tela) de que o controle foi executado e revisado?",
        "Os controles-chave são executados por pessoas com o conhecimento e a autoridade necessários para tal?",
        "As falhas ou exceções encontradas nos controles são escaladas imediatamente para tratamento e correção?",
        "A área rastreia e monitora as ações corretivas implementadas para remediar as deficiências de controle identificadas?",
        "As reconciliações (ex: contábeis, estoques) são realizadas, e os itens pendentes são investigados e resolvidos prontamente?",
        "O Auditado validou por email se existe mapeamento de CONTROLE feito pela área Gerência de riscos e Compliance?"
    ]
    
    # ===== FUNÇÃO AUXILIAR PARA EXIBIR ANÁLISE COMPLETA =====
    def adicionar_analise(analise, titulo):
        story.append(Paragraph(titulo or 'Sem título', subsecao_style))  # ⭐ Adicionar or ''
        story.append(Spacer(1, 5))
        
        # Análise Crítica
        if analise.get('analise_critica'):
            story.append(Paragraph("<b>Análise Crítica:</b>", normal_style))
            story.append(Paragraph(analise['analise_critica'] or '', normal_style))  # ⭐ Adicionar or ''
            story.append(Spacer(1, 5))
        
        # Sugestão de Melhoria
        if analise.get('sugestao_melhoria'):
            story.append(Paragraph("<b>Sugestão de Melhoria:</b>", normal_style))
            story.append(Paragraph(analise['sugestao_melhoria'] or '', normal_style))  # ⭐ Adicionar or ''
            story.append(Spacer(1, 5))

        # Decisão sobre implantação
        if analise.get('sugestao_sera_implantada') == True:
            story.append(Paragraph("<b>Esta melhoria será implantada</b>", normal_style))
            story.append(Spacer(1, 3))
            
            # Plano de Ação
            adicionar_plano_acao(analise)
            story.append(Spacer(1, 5))
            
            # Histórico de Andamento
            if analise.get('historico') and len(analise['historico']) > 0:
                adicionar_historico(analise['historico'])
                story.append(Spacer(1, 5))
            
            # Follow-ups (apenas se já implantada)
            if analise.get('efetivamente_implantada') == True and analise.get('followups') and len(analise['followups']) > 0:
                adicionar_followups(analise['followups'])
                
        elif analise.get('sugestao_sera_implantada') == False:
            story.append(Paragraph("<b>Esta melhoria não será implantada</b>", normal_style))
        else:
            story.append(Paragraph("<b>Aguardando decisão sobre implantação</b>", normal_style))
        
        story.append(Spacer(1, 8))
    
    # ===== FUNÇÃO PARA EXIBIR CHECKLIST (FORMATO LISTA) =====
    def adicionar_checklist_simples(checklist, titulo, perguntas):
        """Adiciona as respostas do checklist ao relatório em formato de lista"""
        story.append(PageBreak())
        story.append(Paragraph(titulo, secao_style))
        story.append(Spacer(1, 5))
        
        if not checklist:
            story.append(Paragraph(
                f"<i>Nenhuma resposta encontrada para {titulo}.</i>", 
                normal_style
            ))
            story.append(Spacer(1, 10))
            return
        
        # Status
        status_text = checklist.get('status', 'Não iniciado')
        story.append(Paragraph(f"<b>Status:</b> {status_text}", normal_style))
        story.append(Spacer(1, 8))
        
        # ⭐ EXIBIR PERGUNTAS E RESPOSTAS EM LISTA
        respostas = checklist.get('respostas', [])
        
        # Criar estilo para perguntas com indentação
        pergunta_style = ParagraphStyle(
            'PerguntaStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=10,
            spaceAfter=4
        )
        
        resposta_style = ParagraphStyle(
            'RespostaStyle',
            parent=normal_style,
            fontSize=9,
            leading=12,
            leftIndent=30,
            spaceAfter=10,
            textColor=colors.HexColor('#0b5b99')
        )
        
        contador = 0
        for idx, r in enumerate(respostas, 1):
            if r.get('resposta'):
                contador += 1
                pergunta_texto = perguntas[idx - 1] if idx - 1 < len(perguntas) else f"Pergunta {idx}"
                
                # Número da pergunta
                story.append(Paragraph(
                    f"<b>{contador}.</b> {pergunta_texto}", 
                    pergunta_style
                ))
                
                # Resposta com destaque
                resposta = str(r.get('resposta'))
                story.append(Paragraph(
                    f"<b>Resposta:</b> {resposta}", 
                    resposta_style
                ))
        
        if contador == 0:
            story.append(Paragraph("<i>Nenhuma resposta registrada.</i>", normal_style))
        
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
            alignment=0,
            spaceAfter=8,
            leftIndent=10
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
    story.append(Paragraph("1. ANÁLISES DO AUDITADO", secao_style))
    story.append(Paragraph("Análises realizadas pelo auditado durante o detalhamento das etapas", normal_style))
    story.append(Spacer(1, 10))
    
    if not etapas:
        story.append(Paragraph("<i>Nenhuma etapa cadastrada para este processo.</i>", normal_style))
    else:
        for etapa_idx, etapa in enumerate(etapas):
            story.append(Paragraph(f"Etapa {etapa['codigo']}: {etapa['nome']}", subsecao_style))
            story.append(Spacer(1, 3))
            
            if etapa['descricao']:
                story.append(Paragraph(f"<i>{etapa['descricao'][:200]}{'...' if len(etapa['descricao']) > 200 else ''}</i>", normal_style))
                story.append(Spacer(1, 5))
            
            if etapa['analises_auditado']:
                for a in etapa['analises_auditado']:
                    nome_categoria = {
                        'governanca': 'Governança',
                        'riscos': 'Riscos',
                        'controles': 'Controles'
                    }.get(a['categoria'], a['categoria'].upper())
                    
                    adicionar_analise(a, f"{nome_categoria}")
            else:
                story.append(Paragraph("<i>Nenhuma análise cadastrada para esta etapa.</i>", normal_style))
            
            # ⭐ Separador entre etapas (com linha cinza)
            if etapa_idx < len(etapas) - 1:
                story.append(Spacer(1, 5))
                story.append(Paragraph("<hr color='#CCCCCC'/>", normal_style))
                story.append(Spacer(1, 5))

    # ===== SEÇÃO 1.5: MATRIZES DE CHECKLIST =====
    adicionar_checklist_simples(
        checklist_data.get('governanca'), 
        "Matriz de Governança - Respostas",
        perguntas_governanca
    )
    
    adicionar_checklist_simples(
        checklist_data.get('riscos'), 
        "Matriz de Riscos - Respostas",
        perguntas_riscos
    )
    
    adicionar_checklist_simples(
        checklist_data.get('controles'), 
        "Matriz de Controles - Respostas",
        perguntas_controles
    )
    
    # ===== SEÇÃO 2: ANÁLISES DO AUDITOR =====
    story.append(PageBreak())
    story.append(Paragraph("2. ANÁLISES DO AUDITOR", secao_style))
    story.append(Paragraph("Análises realizadas pelo auditor durante a Matriz de Eficácia", normal_style))
    story.append(Spacer(1, 10))
    
    if not analises_auditor_list:
        story.append(Paragraph("<i>Nenhuma análise do auditor cadastrada para este processo.</i>", normal_style))
    else:
        for idx, analise in enumerate(analises_auditor_list, 1):
            adicionar_analise(analise, f"2.{idx} Análise do Auditor - {analise.get('data_criacao', '')}")
            
            # ⭐ Separador entre análises (com linha cinza e mais espaçamento)
            if idx < len(analises_auditor_list):
                story.append(Spacer(1, 10))
                story.append(Paragraph("<hr color='#CCCCCC'/>", normal_style))
                story.append(Spacer(1, 10))
    
    # ===== SEÇÃO 2.5: RESUMO DAS MELHORIAS E FOLLOW-UPS =====
    if total_melhorias_em_implantacao > 0 or total_followups_pendentes > 0:
        story.append(PageBreak())
        story.append(Paragraph("2.5. RESUMO DO ACOMPANHAMENTO", secao_style))
        story.append(Spacer(1, 10))
        
        # Box de resumo
        resumo_data = []
        
        if total_melhorias_em_implantacao > 0:
            resumo_data.append([
                Paragraph("Em implantação:", normal_style),
                Paragraph(f"{total_melhorias_em_implantacao} melhoria(s) em andamento", normal_style)
            ])
        
        if total_followups_pendentes > 0:
            resumo_data.append([
                Paragraph("Pendentes:", normal_style),
                Paragraph(f"{total_followups_pendentes} follow-up(s) aguardando registro", normal_style)
            ])
        
        if total_followups_em_andamento > 0:
            resumo_data.append([
                Paragraph("Realizados:", normal_style),
                Paragraph(f"{total_followups_em_andamento} follow-up(s) já registrados", normal_style)
            ])
        
        if resumo_data:
            # Criar tabela resumo com fundo colorido
            resumo_table = Table(resumo_data, colWidths=[5*cm, 11*cm])
            resumo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.97, 1.0, alpha=0.80)),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(resumo_table)
            story.append(Spacer(1, 15))
    
    story.append(PageBreak())
    
    
    # ===== ASSINATURAS =====
    assinatura_data = [
        ["Auditor Responsável pela emissão:", usuario_nome or 'Auditor'],
        ["Data:", datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y')],
        ["Assinatura:", "_________________________"],
        ["", ""],
        ["Auditor Revisor:", "_________________________"],
        ["Data:", "___/___/_______"],
        ["Assinatura:", "_________________________"],
        ["", ""],
        ["Responsável pelas informações:", "_________________________"],
        ["Data:", "___/___/_______"],
        ["Assinatura:", "_________________________"],
        ["", ""],
        ["Ciência do Gestor:", ""],
        ["Gestor:", gestor or 'Não informado'],
        ["Data:", "___/___/_______"],
        ["Assinatura:", "_________________________"],
    ]
    
    tabela_assinaturas = Table(assinatura_data, colWidths=[5.5*cm, 10*cm])
    tabela_assinaturas.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E0E0E0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(tabela_assinaturas)

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
        root_dir = os.path.dirname(os.path.abspath(__file__))
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
    def rodape_final(canvas, doc):
        canvas.saveState()
        
        altura_rodape = 1.8 * cm
        y_fundo = 0
        
        canvas.setFillColor(colors.HexColor('#F0F0F0'))
        canvas.rect(0, y_fundo, pagesize[0], altura_rodape, fill=1, stroke=0)
        
        # ⭐ LINHA 1: Título e página
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawCentredString(pagesize[0]/2, 2*cm, 
            f"Parecer do Processo {proc_codigo} - {area_nome} - Página {doc.page}/{total_paginas}")
        
        # ⭐ LINHA 2: Email e Telefone da GAI
        texto_contato = f"E-mail: {email_gai} | Tel: {telefone_gai}"
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#888888'))
        canvas.drawCentredString(pagesize[0]/2, 1.5*cm, texto_contato)
        
        # ⭐ DESENHAR OS LOGOS
        desenhar_logos_parecer(canvas)
        canvas.restoreState()
    
    # ⭐ CONSTRUIR O DOCUMENTO FINAL
    doc = SimpleDocTemplate(buffer, pagesize=pagesize,
                           topMargin=1.5*cm, bottomMargin=2*cm,
                           leftMargin=2*cm, rightMargin=2*cm)
    
    doc.build(story, 
          onFirstPage=lambda c, d: [cabecalho_com_tarja(c, d), rodape_final(c, d)],
          onLaterPages=lambda c, d: [cabecalho_com_tarja(c, d), rodape_final(c, d)])
    buffer.seek(0)
    return buffer.getvalue()