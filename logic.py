import os
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import text
from database import engine
from datetime import datetime
from flask import session, request
import re
import json

# ===== MIGRAÇÃO PARA FLASK =====
# Streamlit removido - sistema agora usa Flask
# import streamlit as st  # REMOVIDO

# Placeholder para evitar erros (as funções Streamlit não serão chamadas no Flask)
class _DummyStreamlit:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

st = _DummyStreamlit()
# ===== FIM DA MIGRAÇÃO =====

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

def contar_paginas_e_gerar_pdf(story, pagesize, topMargin, bottomMargin, leftMargin, rightMargin, 
                                rodape_func, cabecalho_func=None):
    """
    Conta as páginas de um story e gera o PDF com o total correto no rodapé.
    Retorna o PDF em bytes.
    """
    from reportlab.platypus import SimpleDocTemplate
    import io
    
    # Primeira passada: contar páginas
    buffer_temp = io.BytesIO()
    doc_temp = SimpleDocTemplate(buffer_temp, pagesize=pagesize,
                                topMargin=topMargin, bottomMargin=bottomMargin,
                                leftMargin=leftMargin, rightMargin=rightMargin)
    
    page_counter = {'count': 0}
    
    def rodape_temp(canvas, doc):
        page_counter['count'] += 1
    
    doc_temp.build(story, onFirstPage=rodape_temp, onLaterPages=rodape_temp)
    total_paginas = page_counter['count']
    
    # Segunda passada: gerar o PDF final com o total
    buffer_final = io.BytesIO()
    doc_final = SimpleDocTemplate(buffer_final, pagesize=pagesize,
                                 topMargin=topMargin, bottomMargin=bottomMargin,
                                 leftMargin=leftMargin, rightMargin=rightMargin)
    
    # Criar um novo rodapé que recebe o total
    def rodape_com_total(canvas, doc):
        # Chamar a função de rodapé original com o total
        rodape_func(canvas, doc, total_paginas)
    
    if cabecalho_func:
        doc_final.build(story, 
                       onFirstPage=lambda c, d: [cabecalho_func(c, d), rodape_com_total(c, d)],
                       onLaterPages=lambda c, d: [cabecalho_func(c, d), rodape_com_total(c, d)])
    else:
        doc_final.build(story, onFirstPage=rodape_com_total, onLaterPages=rodape_com_total)
    
    buffer_final.seek(0)
    return buffer_final.getvalue()

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
    story.append(Paragraph(f"Gestor Responsável: {gestor} - {cargo}", normal_style))
    story.append(Paragraph(f"Data de Geração: {datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y %H:%M')}", normal_style))
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
    
    # ===== SEÇÃO 3: CONCLUSÃO E RECOMENDAÇÕES =====
    story.append(PageBreak())
    story.append(Paragraph("3. CONCLUSÃO E RECOMENDAÇÕES", secao_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Com base nas análises realizadas para o processo {proc_codigo or 'N/A'} - {proc_nome or 'N/A'}, "
        "este parecer consolida as principais observações e recomendações.",
        normal_style
    ))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph("Conclusão Final do Auditor:", secao_style))
    story.append(Spacer(1, 8))
    
    for i in range(6):
        story.append(Paragraph("________________________________________________________________________________", normal_style))
        story.append(Spacer(1, 5))
    
    story.append(Spacer(1, 5))
    
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

    # ⭐ FAZER UMA CÓPIA DO STORY PARA A PRIMEIRA PASSADA
    story_copy = copy.deepcopy(story)
    
    # ⭐ PRIMEIRA PASSADA: GERAR PDF TEMPORÁRIO PARA CONTAR PÁGINAS
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
        
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        
        canvas.drawCentredString(pagesize[0]/2, 2*cm, 
            f"Parecer do Processo {proc_codigo} - Página {doc.page}/{total_paginas}")
        
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