"""
Arquivo principal para aplicação Flask
Sistema MAPA - FUSVE
"""

import os
from datetime import datetime, timedelta, date
import json
import io
from supabase import create_client
import base64
import uuid

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, flash, make_response
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from database import (
    engine, 
    SessionLocal,
    Checklist,
    ChecklistResposta,
    ChecklistEvidencia,
    criar_tabelas
)

from utils import (
    upload_arquivo_storage,
    baixar_arquivo_storage,
    excluir_arquivo_storage,
    obter_url_assinada,
    extrair_caminho_da_url
)

from logic import (validar_login_no_banco, listar_areas,
                   listar_funcionarios_area, gerar_validacao_relatorio_detalhamento, gerar_validacao_relatorio_panorama)

from services.relatorios.parecer import gerar_relatorio_parecer_auditoria

# ============================================================
# CARREGAR CONFIGURAÇÕES
# ============================================================

# Carrega .env apenas em desenvolvimento (local)
# No Render, as variáveis já estão no ambiente
if not os.environ.get('RENDER'):
    load_dotenv()

# ============================================================
# IMPORTAR FUNÇÕES AUXILIARES
# ============================================================

from logic import validar_login_no_banco

# ============================================================
# FUNÇÕES DE UTILIDADE
# ============================================================

def atualizar_obrigacao_com_arquivo(etapa_id, indice_obrigacao, arquivo_url, arquivo_nome, arquivo_tamanho):
    """
    Atualiza a obrigação com a URL do arquivo
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            # Buscar as obrigações atuais
            query = text("""
                SELECT obrigacoes_regulatorias 
                FROM etapas_processo 
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result or not result[0]:
                print(f"❌ Nenhuma obrigação encontrada para etapa {etapa_id}")
                return False
            
            # Parsear o JSON
            try:
                obrigacoes = json.loads(result[0])
            except json.JSONDecodeError as e:
                print(f"❌ Erro ao parsear JSON: {e}")
                return False
            
            # Verificar se o índice existe
            if indice_obrigacao >= len(obrigacoes):
                print(f"❌ Índice {indice_obrigacao} não encontrado (total: {len(obrigacoes)})")
                return False
            
            # Atualizar o arquivo na obrigação
            obrigacoes[indice_obrigacao]['arquivo_url'] = arquivo_url
            obrigacoes[indice_obrigacao]['arquivo_nome'] = arquivo_nome
            obrigacoes[indice_obrigacao]['arquivo_tamanho'] = arquivo_tamanho
            
            # Salvar de volta
            update_query = text("""
                UPDATE etapas_processo 
                SET obrigacoes_regulatorias = :obrigacoes::text
                WHERE id = :etapa_id
            """)
            
            conn.execute(update_query, {
                'obrigacoes': json.dumps(obrigacoes, ensure_ascii=False),
                'etapa_id': etapa_id
            })
            conn.commit()
            
            print(f"✅ Obrigação {indice_obrigacao} atualizada com arquivo: {arquivo_nome}")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao atualizar obrigação: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def baixar_arquivo_obrigacao(etapa_id, indice_obrigacao):
    """
    Retorna a URL assinada do arquivo da obrigação
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            # Buscar as obrigações
            query = text("""
                SELECT obrigacoes_regulatorias 
                FROM etapas_processo 
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result or not result[0]:
                return None
            
            obrigacoes = json.loads(result[0])
            
            if indice_obrigacao >= len(obrigacoes):
                return None
            
            obrigacao = obrigacoes[indice_obrigacao]
            arquivo_url = obrigacao.get('arquivo_url', '')
            
            if not arquivo_url:
                return None
            
            # Retornar a URL assinada (já está na obrigação)
            return arquivo_url
            
    except Exception as e:
        print(f"❌ Erro ao buscar arquivo: {e}")
        return None

def calcular_tempo(data_inicio):
    """Calcula tempo decorrido desde a data de início até hoje"""
    if not data_inicio:
        return "Não informado"
    
    if isinstance(data_inicio, str):
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except:
            return "Data inválida"
    
    hoje = date.today()
    anos = hoje.year - data_inicio.year
    meses = hoje.month - data_inicio.month
    
    if meses < 0:
        anos -= 1
        meses += 12
    
    if anos == 0 and meses == 0:
        return "Menos de 1 mês"
    elif anos == 0:
        return f"{meses} {'mês' if meses == 1 else 'meses'}"
    elif meses == 0:
        return f"{anos} {'ano' if anos == 1 else 'anos'}"
    else:
        return f"{anos} {'ano' if anos == 1 else 'anos'} e {meses} {'mês' if meses == 1 else 'meses'}"

# ============================================================
# CRIAÇÃO DA APLICAÇÃO FLASK
# ============================================================

from dashboard_api import dashboard_api
from routes.dashboard_novo.endpoints import novo_dashboard_api
from routes.followups import followups_bp
from routes.relatorios import relatorios_bp
from routes.diagnostico.diagnostico import diagnostico_bp
from routes.detalhamento.detalhamento import detalhamento_bp
from routes import register_blueprints


app = Flask(__name__, static_folder='static')

app.register_blueprint(diagnostico_bp)
app.register_blueprint(dashboard_api)
app.register_blueprint(novo_dashboard_api)
app.register_blueprint(followups_bp)
app.register_blueprint(relatorios_bp)
app.register_blueprint(detalhamento_bp)

register_blueprints(app)

# ⭐⭐⭐ CONFIGURAÇÕES DE SESSÃO ⭐⭐⭐
app.secret_key = os.getenv('SECRET_KEY', 'chave-padrao')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=int(os.getenv('SESSION_TIMEOUT_SECONDS', 1800)))
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ============================================================
# MIDDLEWARE PARA AUDITORIA
# ============================================================

from flask import request, g
from database import engine
from sqlalchemy import text

@app.before_request
def configurar_auditoria():
    """
    Configura variáveis no PostgreSQL para auditoria E RENOVA A SESSÃO
    """

    if request.endpoint in ['login', 'static', 'ping', 'cadastro']:
        return

    # ⭐⭐⭐ NOVO: RENOVAR SESSÃO A CADA REQUISIÇÃO ⭐⭐⭐
    if session.get('autenticado'):
        # Renova o tempo de vida da sessão
        session.permanent = True
        # Atualiza o timestamp da última atividade (para debug)
        session['_last_activity'] = datetime.now().isoformat()
        # Verifica se a sessão tem tempo definido
        if session.permanent:
            # Pega o tempo de expiração
            sessao_expira_em = app.permanent_session_lifetime
            tempo_restante = sessao_expira_em.total_seconds() / 60  # em minutos
            
            print(f"🟢 USUÁRIO: {session.get('usuario_nome')}")
            print(f"🟢 SESSÃO EXPIRA EM: {tempo_restante:.0f} minutos")
            print(f"🟢 ÚLTIMA ATIVIDADE: {session.get('_last_activity')}")
        # A sessão é automaticamente salva pelo Flask
        # O timeout conta a partir da última requisição
    else:
        # Se não estiver autenticado, não faz nada
        return
    
    # ⭐ CÓDIGO EXISTENTE DE AUDITORIA (mantido)
    # Só configura se o usuário estiver autenticado
    if not session.get('autenticado'):
        return
    
    # Pega os dados do usuário da sessão
    usuario_id = session.get('usuario_id')
    usuario_nome = session.get('usuario_nome')
    
    # Se não tiver, usa padrão
    if not usuario_id:
        usuario_id = 0
    if not usuario_nome:
        usuario_nome = 'Sistema'
    
    # Pega o IP real do cliente
    ip_origem = request.headers.get('X-Forwarded-For')
    if ip_origem:
        ip_origem = ip_origem.split(',')[0].strip()
    else:
        ip_origem = request.remote_addr or '127.0.0.1'
    
    # Guarda na sessão do Flask
    g.usuario_id = usuario_id
    g.usuario_nome = usuario_nome
    g.ip_origem = ip_origem
    
    # ✅ ABORDAGEM OTIMIZADA: Só chama o PostgreSQL se houver mudança real
    # Isso reduz o número de queries no banco
    try:
        with engine.connect() as conn:
            # Usa uma query mais leve - apenas SET, sem SELECT
            conn.execute(
                text("SELECT set_app_user(:uid, :uname, :ip)"),
                {'uid': usuario_id, 'uname': usuario_nome, 'ip': ip_origem}
            )
            conn.commit()
    except Exception as e:
        print(f"⚠️ [AUDITORIA] Erro: {e}")

from config.cores import CORES

@app.context_processor
def inject_cores():
    """Disponibiliza CORES para TODOS os templates HTML"""
    return {'CORES': CORES}

@app.route('/static/css/theme.css')
def gerar_css_tema():
    """
    Gera UM ÚNICO ARQUIVO CSS com TODAS as cores
    Você NUNCA precisa atualizar isso!
    """
    css = ":root {\n"
    for nome, cor in CORES.items():
        # primary_dark → --primary-dark
        nome_css = nome.replace('_', '-')
        css += f"    --{nome_css}: {cor};\n"
    css += "}"
    
    response = make_response(css)
    response.headers['Content-Type'] = 'text/css'
    return response

@app.before_request
def verificar_inatividade():
    if request.endpoint in ['login', 'static', 'ping', 'cadastro']:
        return
    
    if not session.get('autenticado'):
        return
    
    ultima_atividade = session.get('_last_activity')
    if ultima_atividade:
        try:
            ultimo_timestamp = datetime.fromisoformat(ultima_atividade)
            tempo_decorrido = (datetime.now() - ultimo_timestamp).total_seconds()
            
            if tempo_decorrido > 1800:
                session.clear()
                
                # ⭐ SE FOR REQUISIÇÃO AJAX → RETORNA 401
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Sessão expirada por inatividade'}), 401
                
                # ⭐ SE FOR REQUISIÇÃO NORMAL → REDIRECIONA PARA O LOGIN
                return redirect(url_for('login'))
        except:
            pass



@app.route('/api/obrigacao/upload', methods=['POST'])
def api_upload_obrigacao():
    """Faz upload do arquivo de uma obrigação regulatória"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    etapa_id = data.get('etapa_id')
    indice = data.get('indice')
    arquivo_base64 = data.get('arquivo_base64')
    nome_arquivo = data.get('nome_arquivo')
    
    # Validações
    if not etapa_id:
        return jsonify({'success': False, 'error': 'etapa_id é obrigatório'}), 400
    
    if indice is None:
        return jsonify({'success': False, 'error': 'indice é obrigatório'}), 400
    
    if not arquivo_base64:
        return jsonify({'success': False, 'error': 'arquivo_base64 é obrigatório'}), 400
    
    if not nome_arquivo:
        return jsonify({'success': False, 'error': 'nome_arquivo é obrigatório'}), 400
    
    # Validar tamanho (10MB)
    import base64
    try:
        # Calcular tamanho aproximado
        if ',' in arquivo_base64:
            arquivo_base64_clean = arquivo_base64.split(',')[1]
        else:
            arquivo_base64_clean = arquivo_base64
        
        tamanho_bytes = len(arquivo_base64_clean) * 3 / 4  # Aproximado
        if tamanho_bytes > 10 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Arquivo muito grande. Máximo 10MB'}), 400
    except:
        pass
    
    try:
        from logic import upload_obrigacao_storage, atualizar_obrigacao_com_arquivo
        
        # Fazer upload
        arquivo_url = upload_obrigacao_storage(
            etapa_id, 
            indice, 
            arquivo_base64, 
            nome_arquivo
        )
        
        if not arquivo_url:
            return jsonify({'success': False, 'error': 'Erro ao fazer upload do arquivo'}), 500
        
        # Atualizar a obrigação com a URL
        sucesso = atualizar_obrigacao_com_arquivo(
            etapa_id, 
            indice, 
            arquivo_url, 
            nome_arquivo,
            int(tamanho_bytes) if 'tamanho_bytes' in locals() else 0
        )
        
        if not sucesso:
            return jsonify({'success': False, 'error': 'Erro ao atualizar obrigação'}), 500
        
        return jsonify({
            'success': True,
            'arquivo_url': arquivo_url,
            'arquivo_nome': nome_arquivo,
            'message': 'Arquivo anexado com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def excluir_obrigacao_completa(etapa_id, indice_obrigacao, arquivo_url=None):
    """
    Exclui uma obrigação regulatória completa:
    - Remove do banco de dados
    - Remove o arquivo do storage (se existir)
    
    Args:
        etapa_id (int): ID da etapa
        indice_obrigacao (int): Índice da obrigação no array JSON
        arquivo_url (str, optional): URL do arquivo para excluir
    
    Returns:
        dict: Resultado da operação
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        print(f"🗑️ Excluindo obrigação {indice_obrigacao} da etapa {etapa_id}")
        
        with engine.connect() as conn:
            # Buscar a etapa atual
            query_busca = text("""
                SELECT obrigacoes_regulatorias FROM etapas_processo WHERE id = :etapa_id
            """)
            result = conn.execute(query_busca, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return {'success': False, 'error': 'Etapa não encontrada'}
            
            # Parse do JSON
            obrigacoes_str = result[0]
            if obrigacoes_str:
                obrigacoes = json.loads(obrigacoes_str)
            else:
                obrigacoes = []
            
            # Verificar se o índice existe
            if indice_obrigacao >= len(obrigacoes):
                return {'success': False, 'error': 'Obrigação não encontrada'}
            
            # Remover a obrigação do array
            obrigacao_removida = obrigacoes.pop(indice_obrigacao)
            
            # 🔥 Se tiver URL, excluir do storage
            url_para_excluir = None
            
            # Prioridade 1: URL passada como parâmetro
            if arquivo_url and arquivo_url.strip() != '':
                url_para_excluir = arquivo_url
            # Prioridade 2: URL da obrigação removida
            elif obrigacao_removida and obrigacao_removida.get('arquivo_url'):
                url_para_excluir = obrigacao_removida.get('arquivo_url')
            
            if url_para_excluir and url_para_excluir.strip() != '':
                print(f"📎 Excluindo arquivo do storage: {url_para_excluir}")
                excluir_arquivo_storage(url_para_excluir)
            else:
                print("ℹ️ Nenhum arquivo para excluir do storage")
            
            # Atualizar o campo no banco
            obrigacoes_json = json.dumps(obrigacoes, ensure_ascii=False)
            
            query_update = text("""
                UPDATE etapas_processo 
                SET obrigacoes_regulatorias = :obrigacoes, updated_at = NOW()
                WHERE id = :etapa_id
            """)
            conn.execute(query_update, {
                'obrigacoes': obrigacoes_json,
                'etapa_id': etapa_id
            })
            conn.commit()
            
            print(f"✅ Obrigação {indice_obrigacao} excluída com sucesso")
            
            return {
                'success': True,
                'message': 'Obrigação excluída com sucesso',
                'total_restantes': len(obrigacoes)
            }
            
    except Exception as e:
        print(f"❌ Erro ao excluir obrigação: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

@app.route('/api/obrigacao/remover-arquivo', methods=['POST'])
def api_obrigacao_remover_arquivo():
    """
    Remove apenas o arquivo de uma obrigação (mantém a obrigação)
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        data = request.json
        etapa_id = data.get('etapa_id')
        indice_obrigacao = data.get('indice')
        arquivo_url = data.get('arquivo_url')
        
        if not etapa_id:
            return jsonify({'success': False, 'error': 'ID da etapa é obrigatório'}), 400
        
        if indice_obrigacao is None:
            return jsonify({'success': False, 'error': 'Índice da obrigação é obrigatório'}), 400
        
        print(f"🗑️ Removendo arquivo da obrigação {indice_obrigacao} da etapa {etapa_id}")
        print(f"📎 URL do arquivo: {arquivo_url}")
        
        with engine.connect() as conn:
            # Buscar a etapa atual
            query_busca = text("""
                SELECT obrigacoes_regulatorias FROM etapas_processo WHERE id = :etapa_id
            """)
            result = conn.execute(query_busca, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            # Parse do JSON
            obrigacoes_str = result[0]
            if obrigacoes_str:
                obrigacoes = json.loads(obrigacoes_str)
            else:
                obrigacoes = []
            
            # Verificar se o índice existe
            if indice_obrigacao >= len(obrigacoes):
                return jsonify({'success': False, 'error': 'Obrigação não encontrada'}), 404
            
            # 🔥 Se tiver URL, excluir do storage
            if arquivo_url and arquivo_url.strip() != '':
                print(f"📎 Excluindo arquivo do storage: {arquivo_url}")
                
                try:
                    # ⭐ EXTRAIR CAMINHO E BUCKET DA URL
                    caminho, bucket = extrair_caminho_da_url(arquivo_url)
                    
                    if caminho and bucket:
                        print(f"📎 Caminho extraído: {caminho}")
                        print(f"📎 Bucket extraído: {bucket}")
                        
                        # ⭐ EXCLUIR USANDO A FUNÇÃO GENÉRICA
                        sucesso = excluir_arquivo_storage(caminho, bucket)
                        
                        if not sucesso:
                            print("⚠️ Falha ao excluir arquivo do storage, mas continuando...")
                    else:
                        print(f"⚠️ Não foi possível extrair caminho da URL: {arquivo_url}")
                        
                except Exception as e:
                    print(f"⚠️ Erro ao excluir do storage: {e}")
                    # Continua mesmo se falhar para remover do banco
            else:
                print("⚠️ Nenhuma URL fornecida para excluir")
                return jsonify({'success': False, 'error': 'URL do arquivo não fornecida'}), 400
            
            # 🔥 Limpar os campos de arquivo na obrigação
            obrigacoes[indice_obrigacao]['arquivo_url'] = ''
            obrigacoes[indice_obrigacao]['arquivo_nome'] = ''
            obrigacoes[indice_obrigacao]['arquivo_tamanho'] = 0
            
            # Atualizar o campo no banco
            obrigacoes_json = json.dumps(obrigacoes, ensure_ascii=False)
            
            query_update = text("""
                UPDATE etapas_processo 
                SET obrigacoes_regulatorias = :obrigacoes, updated_at = NOW()
                WHERE id = :etapa_id
            """)
            conn.execute(query_update, {
                'obrigacoes': obrigacoes_json,
                'etapa_id': etapa_id
            })
            conn.commit()
            
            print(f"✅ Arquivo removido com sucesso da obrigação {indice_obrigacao}")
            
            return jsonify({
                'success': True,
                'message': 'Arquivo removido com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover arquivo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
# ============================================================

@app.route('/cadastro', methods=["GET", "POST"])
def cadastro():
    """Tela de cadastro de novos usuários"""
    if request.method == 'GET':
        return render_template('cadastro.html')

    # POST - processar cadastro
    data = request.json
    login = data.get('login')
    nome = data.get('nome')
    senha = data.get('senha')

    if not login or not nome or not senha:
        return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'}), 400
    
    from database import engine
    from sqlalchemy import text
    from werkzeug.security import generate_password_hash

    try:
        with engine.connect() as conn:
            # Verifica se email já existe
            check_query = text("SELECT id FROM usuarios WHERE login = :login")
            existing = conn.execute(check_query, {'login': login}).fetchone()

            if existing:
                return jsonify({'success': False, 'error': 'E-mail já cadastrado. Faça login ou recupere sua senha.'}), 400

            # Hash da senha
            senha_hash = generate_password_hash(senha)

            # Inserir novo usuário (ativo = false, perfil 'auditor', area = 'Gerência de Auditoria Interna')
            insert_query = text("""
                INSERT INTO usuarios (login, senha, nome, area, ativo, perfil)
                VALUES (:login, :senha, :nome, :area, :ativo, :perfil)
            """)

            conn.execute(insert_query, {
                'login': login,
                'senha': senha_hash,
                'nome': nome,
                'area': 'Gerência de Auditoria Interna',
                'ativo': False,
                'perfil': 'auditor'
            })
            conn.commit()

            return jsonify({'success': True, 'message': 'Cadastro realizado! Aguarde aprovação do administrador.'})
        
    except Exception as e:
        print(f"❌ Erro ao cadastrar usuário: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/login', methods=["GET", "POST"])
def login():
    if session.get('autenticado'):
        return redirect(url_for('home'))
    
    if request.method == 'GET':
        return render_template('login.html', mostrar_botao_esqueci=False)
    
    data = request.json
    usuario = data.get('usuario')
    senha = data.get('senha')
    
    resultado = validar_login_no_banco(usuario, senha)
    
    # Desempacota (agora pode ter 8 valores)
    if len(resultado) == 8:
        sucesso, usuario_id, usuario_nome, usuario_perfil, tentativas_restantes, bloqueado, minutos_restantes, precisa_trocar = resultado
    else:
        sucesso, usuario_id, usuario_nome, usuario_perfil, tentativas_restantes, bloqueado, minutos_restantes = resultado
        precisa_trocar = False
    
    if sucesso:
        if precisa_trocar:
            # Login com senha temporária - força troca
            session['trocar_senha'] = True
            session['usuario_id_temp'] = usuario_id
            session['usuario_nome_temp'] = usuario_nome
            return jsonify({'success': True, 'trocar_senha': True, 'redirect': url_for('trocar_senha')})
        
        # Login normal
        session['autenticado'] = True
        session['usuario_logado'] = usuario
        session['usuario_nome'] = usuario_nome
        session['usuario_id'] = usuario_id
        session['usuario_perfil'] = usuario_perfil
        session.permanent = True
        return jsonify({'success': True, 'redirect': url_for('home')})
    
    if bloqueado:
        return jsonify({
            'success': False, 
            'bloqueado': True, 
            'minutos': minutos_restantes,
            'error': f'Conta bloqueada por {minutos_restantes} minutos.'
        })
    
    if tentativas_restantes > 0:
        mostrar_esqueci = tentativas_restantes <= 1
        return jsonify({
            'success': False, 
            'tentativas_restantes': tentativas_restantes,
            'error': f'Usuário ou senha incorretos. Você tem mais {tentativas_restantes} tentativa(s).',
            'mostrar_esqueci': mostrar_esqueci
        })
    
    return jsonify({'success': False, 'error': 'Usuário ou senha incorretos'})

@app.route('/trocar-senha', methods=['GET', 'POST'])
def trocar_senha():
    """Página para forçar troca de senha"""
    if not session.get('trocar_senha'):
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('trocar_senha.html', nome=session.get('usuario_nome_temp', 'Usuário'))
    
    # POST - processar nova senha
    from database import engine
    from sqlalchemy import text
    from werkzeug.security import generate_password_hash
    
    data = request.json
    nova_senha = data.get('nova_senha')
    confirmar_senha = data.get('confirmar_senha')
    
    if not nova_senha or not confirmar_senha:
        return jsonify({'success': False, 'message': 'Preencha todos os campos'}), 400
    
    if nova_senha != confirmar_senha:
        return jsonify({'success': False, 'message': 'As senhas não coincidem'}), 400
    
    if len(nova_senha) < 6:
        return jsonify({'success': False, 'message': 'A senha deve ter no mínimo 6 caracteres'}), 400
    
    try:
        usuario_id = session.get('usuario_id_temp')
        nova_senha_hash = generate_password_hash(nova_senha)
        
        print(f"🔍 DEBUG - Usuário ID: {usuario_id}")
        
        with engine.connect() as conn:
            # Verificar estado ANTES
            before = conn.execute(text("SELECT solicitou_recuperacao, forcar_troca_senha, senha_temporaria FROM usuarios WHERE id = :id"), {'id': usuario_id}).fetchone()
            print(f"🔍 ANTES: solicitou_recuperacao={before[0]}, forcar_troca_senha={before[1]}, senha_temporaria={before[2]}")
            
            # ⭐ ATUALIZAR todos os campos de recuperação
            update = text("""
                UPDATE usuarios 
                SET senha = :senha, 
                    forcar_troca_senha = FALSE, 
                    senha_temporaria = NULL,
                    solicitou_recuperacao = FALSE,
                    tentativas_login = 0,
                    bloqueado_ate = NULL
                WHERE id = :id
            """)
            result = conn.execute(update, {
                'senha': nova_senha_hash, 
                'id': usuario_id
            })
            conn.commit()
            print(f"🔍 Linhas afetadas: {result.rowcount}")
            
            # Verificar estado DEPOIS
            after = conn.execute(text("SELECT solicitou_recuperacao, forcar_troca_senha, senha_temporaria FROM usuarios WHERE id = :id"), {'id': usuario_id}).fetchone()
            print(f"🔍 DEPOIS: solicitou_recuperacao={after[0]}, forcar_troca_senha={after[1]}, senha_temporaria={after[2]}")
        
        # Limpa sessão temporária
        session.pop('trocar_senha', None)
        session.pop('usuario_id_temp', None)
        session.pop('usuario_nome_temp', None)
        
        return jsonify({'success': True, 'message': 'Senha alterada com sucesso! Faça login.'})
        
    except Exception as e:
        print(f"Erro ao trocar senha: {e}")
        return jsonify({'success': False, 'message': 'Erro ao processar solicitação'}), 500

@app.route('/logout')
def logout():
    """Remove os dados da sessão e desloga o usuário"""
    session.clear()
    return redirect(url_for('login'))



@app.route('/admin/usuario/<int:usuario_id>/resetar-senha', methods=['POST'])
def admin_resetar_senha(usuario_id):
    # Verifica se é ADMIN
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    from werkzeug.security import generate_password_hash
    
    senha_temp = f"temp{usuario_id}{datetime.now().strftime('%d%m')}"
    senha_hash = generate_password_hash(senha_temp)
    
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE usuarios 
            SET senha = :senha, 
                forcar_troca_senha = TRUE,
                senha_temporaria = :temp
            WHERE id = :id
        """), {'senha': senha_hash, 'temp': senha_temp, 'id': usuario_id})
        conn.commit()
    
    return jsonify({'success': True, 'senha_temporaria': senha_temp})

@app.route('/solicitar-recuperacao', methods=['POST'])
def solicitar_recuperacao():
    """Usuário solicita recuperação de senha"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'E-mail é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Verifica se email existe
            user = conn.execute(text("SELECT id FROM usuarios WHERE login = :email"), {'email': email}).fetchone()
            
            if not user:
                # Por segurança, não informamos que o email não existe
                return jsonify({'success': True, 'message': 'Solicitação enviada ao administrador.'})
            
            # Marca que o usuário solicitou recuperação
            conn.execute(text("""
                UPDATE usuarios 
                SET solicitou_recuperacao = TRUE 
                WHERE id = :id
            """), {'id': user[0]})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Solicitação enviada ao administrador.'})
            
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'success': False, 'message': 'Erro ao processar solicitação'}), 500

@app.route('/ping')
def ping():
    """Health check para o UptimeRobot"""
    return "OK", 200

# ============================================================
# ROTAS PRINCIPAIS (PÁGINAS)
# ============================================================

@app.route('/')
def index():
    """Redireciona para login ou home"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return redirect(url_for('home'))  # Agora redireciona para /home

@app.route('/home')
def home():
    """Redireciona para a home"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/plano-anual')
def plano_anual():
    """Página do Plano Anual de Auditoria"""
    from database import engine
    from sqlalchemy import text
    import os
    
    # Buscar anos disponíveis dos PDFs
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'pdfs', 'plano_anual')
    anos_disponiveis = []
    
    if os.path.exists(pdf_dir):
        for arquivo in os.listdir(pdf_dir):
            if arquivo.startswith('plano_anual_') and arquivo.endswith('.pdf'):
                try:
                    ano = arquivo.replace('plano_anual_', '').replace('.pdf', '')
                    if ano.isdigit():
                        anos_disponiveis.append(int(ano))
                except:
                    pass
    
    # Ordenar anos do mais recente para o mais antigo
    anos_disponiveis = sorted(set(anos_disponiveis), reverse=True)
    
    # Se não encontrou PDFs, buscar anos do banco de dados
    if not anos_disponiveis:
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT DISTINCT ano FROM auditorias ORDER BY ano DESC"))
                anos_disponiveis = [row[0] for row in result if row[0]]
        except:
            pass
    
    return render_template('plano_anual.html', anos_disponiveis=anos_disponiveis)

@app.route('/auditorias-emergenciais')
def auditorias_emergenciais():
    """Página de Auditorias Emergenciais"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id_area, nome_area 
                FROM informacoes_area 
                ORDER BY nome_area
            """))
            areas = {row.nome_area: row.id_area for row in result}
        
        return render_template('auditorias_emergenciais.html', areas=areas)
    except Exception as e:
        print(f"❌ Erro ao carregar página de auditorias emergenciais: {e}")
        return render_template('auditorias_emergenciais.html', areas={})

@app.route('/dashboard')
def dashboard():
    """Dashboard principal - apenas administradores podem acessar"""
    
    # 1. Verificar se o usuário está logado
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    # 2. Verifica se o usuário é administrador
    usuario_perfil = session.get('usuario_perfil')
    if usuario_perfil not in ['administrador', 'admin']:
        # Se não for admin, redireciona para home com mensagem de erro
        flash('Acesso negado. Apenas administradores podem visualizar o dashboard', 'error')
        return redirect(url_for('home'))
    
    # 3. Se for admin, mostra a página
    return render_template('dashboard.html')

# ⭐ NOVO ENDPOINT: /dashboardteste
@app.route('/dashboardteste')
def dashboard_teste():
    # Pode passar um parâmetro para o template
    modo_teste = request.args.get('modo', 'completo')
    return render_template('dashboard_teste.html', modo_teste=modo_teste)

@app.route('/auditorias')
def auditorias():
    """Página de cadastro de auditorias"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    # Verificar se é administrador (opcional)
    if session.get('usuario_perfil') not in ['administrador', 'admin', 'auditor']:
        flash('Acesso negado. Apenas administradores e auditores podem acessar.', 'error')
        return redirect(url_for('home'))
    
    return render_template('auditorias.html')

# ============================================================
# API - PLANO ANUNAL
# ============================================================

@app.route('/api/fundamentos-por-ano')
def api_fundamentos_por_ano():
    """Retorna todas as auditorias não emergenciais de um ano com seus fundamentos"""
    from database import engine
    from sqlalchemy import text
    import json
    
    ano = request.args.get('ano')
    if not ano:
        return jsonify({'success': False, 'error': 'Ano é obrigatório'}), 400
    
    try:
        query = text("""
            SELECT 
                a.id,
                a.codigo_auditoria,
                a.titulo,
                a.ano,
                a.trimestre,
                a.fundamentos,
                ar.nome_area as area_nome
            FROM auditorias a
            LEFT JOIN informacoes_area ar ON a.id_area = ar.id_area
            WHERE a.ano = :ano 
                AND (a.emergencial = false OR a.emergencial IS NULL)
            ORDER BY a.trimestre ASC, a.codigo_auditoria ASC
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"ano": ano})
            auditorias = []
            
            for row in result:
                aud = dict(row._mapping)
                
                # Parse dos fundamentos (se for string JSON)
                if aud.get('fundamentos'):
                    if isinstance(aud['fundamentos'], str):
                        try:
                            aud['fundamentos'] = json.loads(aud['fundamentos'])
                        except:
                            aud['fundamentos'] = []
                    elif not isinstance(aud['fundamentos'], list):
                        aud['fundamentos'] = []
                else:
                    aud['fundamentos'] = []
                
                auditorias.append(aud)
        
        return jsonify({
            'success': True,
            'auditorias': auditorias,
            'total': len(auditorias)
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar fundamentos por ano: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'auditorias': [],
            'total': 0
        }), 500

@app.route('/api/plano-anual-pdf')
def api_plano_anual_pdf():
    """Retorna o PDF do plano anual ou da auditoria emergencial"""
    import os
    from flask import send_file
    
    ano = request.args.get('ano')
    tipo = request.args.get('tipo', 'plano')
    
    # ====== AUDITORIAS EMERGENCIAIS ======
    if tipo == 'emergencial':
        codigo = request.args.get('codigo')
        if not codigo:
            return jsonify({'error': 'Código é obrigatório'}), 400
        
        # Buscar na pasta static/emergenciais/
        pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'emergenciais')
        arquivo_pdf = os.path.join(pdf_dir, f"{codigo}.pdf")
        
        # Se não encontrar, tentar buscar qualquer arquivo que comece com o código
        if not os.path.exists(arquivo_pdf) and os.path.exists(pdf_dir):
            for arquivo in os.listdir(pdf_dir):
                if arquivo.startswith(codigo) and arquivo.endswith('.pdf'):
                    arquivo_pdf = os.path.join(pdf_dir, arquivo)
                    break
        
        if os.path.exists(arquivo_pdf):
            return send_file(arquivo_pdf, as_attachment=True, download_name=os.path.basename(arquivo_pdf))
        else:
            return jsonify({'error': f'Arquivo PDF não encontrado para a auditoria {codigo}'}), 404
    
    # ====== PLANO ANUAL ======
    if not ano:
        return jsonify({'error': 'Ano é obrigatório'}), 400
    
    # ⭐ Buscar direto na pasta static (estrutura simplificada)
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'planejada')
    
    # Buscar arquivo plano_anual_{ano}.pdf
    arquivo_pdf = os.path.join(pdf_dir, f"plano_anual_{ano}.pdf")
    
    # Se não encontrar, tentar buscar qualquer arquivo que termine com o ano
    if not os.path.exists(arquivo_pdf):
        for arquivo in os.listdir(pdf_dir):
            if arquivo.endswith(f"_{ano}.pdf") or arquivo.endswith(f"-{ano}.pdf"):
                arquivo_pdf = os.path.join(pdf_dir, arquivo)
                break
    
    if os.path.exists(arquivo_pdf):
        return send_file(arquivo_pdf, as_attachment=True, download_name=os.path.basename(arquivo_pdf))
    else:
        return jsonify({'error': f'Arquivo PDF do Plano Anual para {ano} não encontrado'}), 404

@app.route('/api/auditoria/<int:auditoria_id>/fundamentos', methods=['GET'])
def api_buscar_fundamentos_auditoria(auditoria_id):
    """Busca a lista de fundamentos da auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT fundamentos
                FROM auditorias
                WHERE id = :auditoria_id
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            fundamentos_raw = result[0]
            
            # ⭐ LOG PARA DEBUG ⭐
            print(f"🔍 fundamentos_raw: {fundamentos_raw}")
            print(f"🔍 tipo: {type(fundamentos_raw)}")
            
            # ⭐ TRATAMENTO CORRETO ⭐
            if fundamentos_raw is None:
                fundamentos = []
            elif isinstance(fundamentos_raw, str):
                if fundamentos_raw == '':
                    fundamentos = []
                else:
                    try:
                        fundamentos = json.loads(fundamentos_raw)
                    except json.JSONDecodeError as e:
                        print(f"❌ Erro ao fazer parse do JSON: {e}")
                        fundamentos = []
            elif isinstance(fundamentos_raw, list):
                fundamentos = fundamentos_raw
            else:
                fundamentos = []
            
            print(f"🔍 fundamentos retornados: {fundamentos}")
            print(f"🔍 tipo retornado: {type(fundamentos)}")
            
            return jsonify({
                'success': True,
                'fundamentos': fundamentos
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar fundamentos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auditoria/<int:auditoria_id>/fundamentos', methods=['POST', 'PUT'])
def api_salvar_fundamentos_auditoria(auditoria_id):
    """Salva a lista de fundamentos da auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        dados = request.json
        fundamentos = dados.get('fundamentos', [])
        
        # Converter para JSON string
        if isinstance(fundamentos, (list, dict)):
            fundamentos_json = json.dumps(fundamentos)
        else:
            fundamentos_json = fundamentos
        
        with engine.connect() as conn:
            query = text("""
                UPDATE auditorias 
                SET fundamentos = :fundamentos,
                    updated_at = NOW()
                WHERE id = :auditoria_id
            """)
            
            result = conn.execute(query, {
                'fundamentos': fundamentos_json,
                'auditoria_id': auditoria_id
            })
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            return jsonify({'success': True})
            
    except Exception as e:
        print(f"❌ Erro ao salvar fundamentos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================================================
# FIM API PLANO ANUNAL
# ============================================================

@app.route('/diagnostico')
def diagnostico():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    
    return render_template('diagnostico/diagnostico.html', areas=areas, usuario_perfil=usuario_perfil)

@app.route('/detalhamento')
def detalhamento():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    
    return render_template('/detalhamento/detalhamento.html', areas=areas, usuario_perfil=usuario_perfil)

@app.route('/visao-geral')
def visao_geral():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('visao_geral.html')

@app.route('/checklists')
def checklists():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('checklists.html')

@app.route('/relatorios')
def relatorios():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    # ⭐ Passar variáveis da sessão para o template
    return render_template(
        'relatorios.html',
        usuario_perfil=session.get('usuario_perfil', ''),
        usuario_nome=session.get('usuario_nome', '')
    )

@app.route('/areas')
def areas():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    return render_template('areas.html', usuario_perfil=usuario_perfil)

@app.route('/log-alteracoes')
def log_alteracoes():
    """
    Página de visualização do histórico de alterações
    Apenas administradores podem acessar
    """

    # 1. Verificar se o usuário está logado
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    # 2. Verifica se o usuário é adminsitrador
    usuario_perfil = session.get('usuario_perfil')
    if usuario_perfil not in ['administrador', 'admin']:
        # Se nã for admin, redireciona para home com mensagem de erro
        # Usando o sistema de toast que já temos
        flash('Acesso negado. Apenas administradores podem visualizar o histórico de alterações', 'error')
        return redirect(url_for('home'))
    
    # 3. Se for admin, mostra a página
    return render_template('log_alteracoes.html')
    
    



@app.route('/api/processo/<int:processo_id>/etapas')
def api_processo_etapas(processo_id):
    """Retorna todas as etapas de um processo"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # ⭐ ADICIONAR manual_em_andamento NO SELECT
            query = text("""
                SELECT ep.id, ep.codigo_etapa, ep.nome_etapa, ep.descricao_etapa,
                    ep.como_e_feito, ep.objetivo_etapa, ep.status_etapa, ep.criticidade_etapa,
                    ep.politica_interna, ep.analise_critica, ep.sugestao_melhoria,
                    ep.necessidade_implantacao, ep.ganho_previsto, ep.obrigacoes_regulatorias,
                    ep.executores_etapa,
                    ep.manual_nome, ep.created_at, ep.auditoria_id,
                    -- ⭐ NOVO CAMPO
                    ep.manual_em_andamento,
                    EXISTS(
                        SELECT 1 FROM analises_criticas ac 
                        WHERE ac.etapa_id = ep.id AND ac.tipo = 'auditado'
                    ) as tem_analise_auditado,
                    EXISTS(
                        SELECT 1 FROM analises_criticas ac 
                        WHERE ac.etapa_id = ep.id AND ac.tipo = 'auditor'
                    ) as tem_analise_auditor
                FROM etapas_processo ep
                WHERE ep.processo_id = :processo_id
                ORDER BY ep.codigo_etapa
            """)
            
            result = conn.execute(query, {'processo_id': processo_id}).fetchall()

            etapas = []
            for row in result:
                etapas.append({
                    'id': row[0],
                    'codigo_etapa': row[1] or '',
                    'nome_etapa': row[2] or '',
                    'descricao_etapa': row[3] or '',
                    'como_e_feito': row[4] or '',
                    'objetivo_etapa': row[5] or '',
                    'status_etapa': row[6] or 'Ativa',
                    'criticidade_etapa': row[7] or 'Em aprovação',
                    'politica_interna': row[8] or '',
                    'analise_critica': row[9] or '',
                    'sugestao_melhoria': row[10] or '',
                    'necessidade_implantacao': row[11] or '',
                    'ganho_previsto': row[12] or '',
                    'obrigacoes_regulatorias': row[13] or '',
                    'executores_etapa': row[14] or '',
                    'manual_nome': row[15] or '',                    
                    'created_at': row[16].isoformat() if row[16] else '',
                    'auditoria_id': row[17] if len(row) > 17 else None,
                    # ⭐ NOVO CAMPO
                    'manual_em_andamento': row[18] if len(row) > 18 else False,
                    'tem_analise_auditado': row[19] if len(row) > 19 else False,
                    'tem_analise_auditor': row[20] if len(row) > 20 else False,
                })
            
            return jsonify({'success': True, 'etapas': etapas})
        
    except Exception as e:
        print(f"❌ Erro ao buscar etapas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/detalhamento_etapas')
def detalhamento_etapas():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    return render_template('detalhamento/detalhamento_etapas.html')

   
@app.route('/api/controle-etapa/<int:controle_id>', methods=['DELETE'])
def api_controle_etapa_excluir(controle_id):
    """Remove um controle (soft delete)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Como sua tabela não tem coluna 'ativo', vamos deletar mesmo
            # Se quiser manter soft delete, teria que adicionar a coluna 'ativo'
            query = text("DELETE FROM controles_etapa WHERE id = :controle_id")
            conn.execute(query, {'controle_id': controle_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Controle excluído com sucesso'})
    except Exception as e:
        print(f"❌ Erro ao excluir controle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================================================
# ROTAS DE API (BACKEND)
# ============================================================

@app.route('/api/auditorias-emergenciais')
def api_auditorias_emergenciais():
    """Retorna apenas as auditorias emergenciais"""
    from database import engine
    from sqlalchemy import text
    
    area_id = request.args.get('area_id')
    
    # Construir a query base
    query = text("""
        SELECT 
            a.id, 
            a.codigo_auditoria, 
            a.titulo, 
            a.trimestre, 
            a.ano, 
            a.status, 
            a.unidade,
            a.data_inicio,
            a.data_fim,
            a.emergencial,
            ar.nome_area as area_nome
        FROM auditorias a
        LEFT JOIN informacoes_area ar ON a.id_area = ar.id_area
        WHERE a.emergencial = true
    """)
    
    # Adicionar filtro por área se fornecido
    if area_id:
        query = text("""
            SELECT 
                a.id, 
                a.codigo_auditoria, 
                a.titulo, 
                a.trimestre, 
                a.ano, 
                a.status, 
                a.unidade,
                a.data_inicio,
                a.data_fim,
                a.emergencial,
                ar.nome_area as area_nome
            FROM auditorias a
            LEFT JOIN informacoes_area ar ON a.id_area = ar.id_area
            WHERE a.emergencial = true AND a.id_area = :area_id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"area_id": area_id})
            auditorias = [dict(row._mapping) for row in result]
    else:
        with engine.connect() as conn:
            result = conn.execute(query)
            auditorias = [dict(row._mapping) for row in result]
    
    return jsonify({
        'success': True,
        'auditorias': auditorias,
        'total': len(auditorias)
    })

@app.route('/api/auditoria-emergencial-pdf')
def api_auditoria_emergencial_pdf():
    """Retorna o PDF da auditoria emergencial"""
    import os
    from flask import send_file
    
    codigo = request.args.get('codigo')
    if not codigo:
        return jsonify({'error': 'Código da auditoria é obrigatório'}), 400
    
    # Caminho onde os PDFs das auditorias emergenciais estão armazenados
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'pdfs', 'emergenciais')
    
    # Buscar arquivo com o nome exato do código
    arquivo_pdf = os.path.join(pdf_dir, f"{codigo}.pdf")
    
    if os.path.exists(arquivo_pdf):
        return send_file(arquivo_pdf, as_attachment=True, download_name=f"{codigo}.pdf")
    else:
        return jsonify({'error': 'Arquivo PDF não encontrado'}), 404

@app.route('/api/auditoria/<int:auditoria_id>/responsavel')
def api_auditoria_responsavel(auditoria_id):
    """Verifica se o usuário logado é responsável pela auditoria ou é administrador"""
    from database import engine
    from sqlalchemy import text

    usuario_nome = session.get('usuario_nome')
    usuario_perfil = session.get('usuario_perfil')

    if not usuario_nome:
        return jsonify({'autorizado': False, 'error': 'Usuário não logado'}), 401
    
    # ADMINISTRADOR tem acesso total
    if usuario_perfil == 'administrador' or usuario_perfil == 'admin':
        return jsonify({
            'autorizado': True,
            'usuario': usuario_nome,
            'perfil': usuario_perfil,
            'motivo': 'Administrador tem acesso total'
        })
    
    query = text("""
        SELECT responsavel_equipe FROM auditorias WHERE id = :id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'id': auditoria_id}).fetchone()

        if not result:
            return jsonify({'autorizado': False, 'error': 'Auditoria não encontrada'}), 404
        
        responsaveis = result[0] or []

        autorizado = usuario_nome in responsaveis if responsaveis else False

        return jsonify({
            'autorizado': autorizado,
            'usuario': usuario_nome,
            'perfil': usuario_perfil,
            'responsaveis': responsaveis
        })

@app.route('/api/auditoria/<int:auditoria_id>/upload-evidencia', methods=['POST'])
def api_upload_evidencia(auditoria_id):
    """Faz upload de uma evidência para o Supabase Storage"""
    import os
    from datetime import datetime
    import json
    
    try:
        # Verificar se o arquivo foi enviado
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Nome do arquivo vazio'}), 400
        
        # Buscar código da auditoria
        from database import engine
        from sqlalchemy import text
        
        query = text("SELECT codigo_auditoria FROM auditorias WHERE id = :auditoria_id")
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            if not row:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            codigo_auditoria = row.codigo_auditoria
        
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        # Gerar nome único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_original = arquivo.filename
        extensao = nome_original.rsplit('.', 1)[-1] if '.' in nome_original else ''
        nome_arquivo = f"{codigo_auditoria}_{timestamp}.{extensao}" if extensao else f"{codigo_auditoria}_{timestamp}"
        
        # Caminho no Storage
        caminho_storage = f"auditorias/emergenciais/{codigo_auditoria}/{nome_arquivo}"
        
        # Ler o arquivo
        arquivo_bytes = arquivo.read()
        
        # Upload usando o bucket 'evidencias_auditorias'
        bucket_name = 'evidencias_auditorias'
        supabase.storage.from_(bucket_name).upload(
            path=caminho_storage,
            file=arquivo_bytes,
            file_options={"content-type": arquivo.content_type}
        )
        
        # Gerar URL assinada
        url_assinada = supabase.storage.from_(bucket_name).create_signed_url(
            path=caminho_storage,
            expires_in=604800  # 7 dias
        )
        
        # Buscar evidências existentes
        query = text("SELECT evidencias FROM auditorias WHERE id = :auditoria_id")
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            if row and row.evidencias:
                if isinstance(row.evidencias, str):
                    evidencias = json.loads(row.evidencias)
                else:
                    evidencias = row.evidencias or []
            else:
                evidencias = []
        
        # Adicionar nova evidência
        nova_evidencia = {
            'nome': nome_original,
            'url': caminho_storage,
            'url_signed': url_assinada['signedURL'] if isinstance(url_assinada, dict) else url_assinada,
            'tamanho': len(arquivo_bytes),
            'tipo': arquivo.content_type,
            'data_upload': datetime.now().isoformat()
        }
        evidencias.append(nova_evidencia)
        
        # Salvar no banco
        evidencias_json = json.dumps(evidencias)
        query = text("""
            UPDATE auditorias 
            SET evidencias = :evidencias
            WHERE id = :auditoria_id
        """)
        
        with engine.connect() as conn:
            conn.execute(query, {
                "evidencias": evidencias_json,
                "auditoria_id": auditoria_id
            })
            conn.commit()
        
        return jsonify({
            'success': True,
            'evidencia': nova_evidencia,
            'message': 'Arquivo enviado com sucesso'
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auditoria/<int:auditoria_id>/evidencia', methods=['DELETE'])
def api_remover_evidencia(auditoria_id):
    """Remove uma evidência da auditoria e do Storage"""
    from database import engine
    from sqlalchemy import text
    import json
    import os
    
    try:
        data = request.json
        caminho = data.get('caminho')
        
        if not caminho:
            return jsonify({'success': False, 'error': 'Caminho do arquivo é obrigatório'}), 400
        
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket_name = 'evidencias_auditorias'
        
        # Buscar evidências existentes
        query = text("SELECT evidencias FROM auditorias WHERE id = :auditoria_id")
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            if row and row.evidencias:
                if isinstance(row.evidencias, str):
                    evidencias = json.loads(row.evidencias)
                else:
                    evidencias = row.evidencias or []
            else:
                evidencias = []
        
        # Remover a evidência da lista
        evidencias = [e for e in evidencias if e.get('url') != caminho]
        
        # Remover do Storage
        supabase.storage.from_(bucket_name).remove([caminho])
        
        # Salvar no banco
        evidencias_json = json.dumps(evidencias)
        query = text("""
            UPDATE auditorias 
            SET evidencias = :evidencias
            WHERE id = :auditoria_id
        """)
        
        with engine.connect() as conn:
            conn.execute(query, {
                "evidencias": evidencias_json,
                "auditoria_id": auditoria_id
            })
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Evidência removida com sucesso'
        })
        
    except Exception as e:
        print(f"❌ Erro ao remover evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auditoria/<int:auditoria_id>/evidencias')
def api_get_evidencias(auditoria_id):
    """Retorna a lista de evidências de uma auditoria"""
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        query = text("""
            SELECT evidencias 
            FROM auditorias 
            WHERE id = :auditoria_id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            
            if row and row.evidencias:
                if isinstance(row.evidencias, str):
                    evidencias = json.loads(row.evidencias)
                else:
                    evidencias = row.evidencias
            else:
                evidencias = []
        
        # ⭐ RENOVAR URLS ASSINADAS (se necessário)
        if evidencias:
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            bucket_name = 'evidencias_auditorias'
            
            for ev in evidencias:
                if ev.get('url'):
                    try:
                        url_assinada = supabase.storage.from_(bucket_name).create_signed_url(
                            ev['url'],
                            expires_in=604800  # 7 dias
                        )
                        if isinstance(url_assinada, dict) and 'signedURL' in url_assinada:
                            ev['url_signed'] = url_assinada['signedURL']
                        else:
                            ev['url_signed'] = url_assinada
                    except:
                        pass
        
        return jsonify({
            'success': True,
            'evidencias': evidencias
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar evidências: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'evidencias': []
        }), 500

# ============================================================
# MATRIZ DE ACHADOS (COMENTÁRIOS COM ANEXOS)
# ============================================================

@app.route('/api/auditoria/<int:auditoria_id>/achados', methods=['GET'])
def api_get_achados(auditoria_id):
    """Lista todos os achados (comentários) de uma auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    a.id,
                    a.texto,
                    a.data_criacao,
                    a.data_edicao,
                    a.anexos,
                    a.usuario_id,
                    u.nome as usuario_nome
                FROM matriz_achados a
                JOIN usuarios u ON a.usuario_id = u.id
                WHERE a.auditoria_id = :auditoria_id
                ORDER BY a.data_criacao DESC
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            achados = []
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            for row in result:
                # Parse dos anexos (JSON)
                anexos = []
                if row[4]:
                    if isinstance(row[4], str):
                        anexos = json.loads(row[4])
                    else:
                        anexos = row[4] or []
                
                # Gerar URLs assinadas para cada anexo
                if anexos:
                    for anexo in anexos:
                        try:
                            caminho = anexo.get('caminho')
                            if caminho:
                                signed_url = supabase.storage.from_('matriz_achados_anexos').create_signed_url(
                                    path=caminho,
                                    expires_in=86400  # 24 horas
                                )
                                anexo['url'] = signed_url['signedURL'] if isinstance(signed_url, dict) else signed_url
                        except Exception as e:
                            print(f"⚠️ Erro ao gerar URL assinada: {e}")
                            anexo['url'] = None
                
                achados.append({
                    'id': row[0],
                    'texto': row[1],
                    'data_criacao': row[2].isoformat() if row[2] else None,
                    'data_edicao': row[3].isoformat() if row[3] else None,
                    'anexos': anexos,
                    'usuario_id': row[5],
                    'usuario_nome': row[6] or 'Usuário',
                    'pode_editar': row[5] == session.get('usuario_id') or session.get('usuario_perfil') in ['administrador', 'admin']
                })
            
            return jsonify({'success': True, 'achados': achados})
            
    except Exception as e:
        print(f"❌ Erro ao buscar achados: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auditoria/<int:auditoria_id>/achados', methods=['POST'])
def api_adicionar_achado(auditoria_id):
    """Adiciona um novo achado (comentário) com anexos"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import base64
    import json
    from datetime import datetime
    
    try:
        data = request.get_json()
        texto = data.get('texto', '').strip()
        anexos = data.get('anexos', [])
        
        if not texto:
            return jsonify({'success': False, 'error': 'Texto do achado é obrigatório'}), 400
        
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        # Validar limite de anexos
        if len(anexos) > 5:
            return jsonify({'success': False, 'error': 'Máximo de 5 anexos por achado'}), 400
        
        with engine.connect() as conn:
            # 1. INSERIR ACHADO
            query = text("""
                INSERT INTO matriz_achados (auditoria_id, usuario_id, texto, data_criacao, anexos)
                VALUES (:auditoria_id, :usuario_id, :texto, NOW(), '[]'::jsonb)
                RETURNING id
            """)
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'usuario_id': usuario_id,
                'texto': texto
            })
            achado_id = result.fetchone()[0]
            
            # 2. PROCESSAR ANEXOS (UPLOAD PARA STORAGE)
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            anexos_salvos = []
            
            for anexo in anexos:
                nome_arquivo = anexo.get('nome')
                tipo_arquivo = anexo.get('tipo', 'application/octet-stream')
                tamanho = anexo.get('tamanho', 0)
                base64_data = anexo.get('base64')
                
                if not base64_data or not nome_arquivo:
                    continue
                
                # Decodificar Base64
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                arquivo_bytes = base64.b64decode(base64_data)
                
                # Validar tamanho (10MB)
                if len(arquivo_bytes) > 10 * 1024 * 1024:
                    continue
                
                # Gerar caminho único no Storage
                timestamp = int(datetime.now().timestamp())
                caminho_storage = f"matriz_achados_auditoria/auditoria_id_{auditoria_id}/achado_id_{achado_id}/{timestamp}_{nome_arquivo}"
                
                # Upload para o Storage
                try:
                    supabase.storage.from_('matriz_achados_anexos').upload(
                        path=caminho_storage,
                        file=arquivo_bytes,
                        file_options={"content-type": tipo_arquivo}
                    )
                    
                    anexos_salvos.append({
                        'nome': nome_arquivo,
                        'caminho': caminho_storage,
                        'tipo': tipo_arquivo,
                        'tamanho': tamanho,
                        'data_upload': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"⚠️ Erro no upload do anexo {nome_arquivo}: {e}")
            
            # 3. ATUALIZAR O CAMPO ANEXOS COM OS DADOS SALVOS
            if anexos_salvos:
                anexos_json = json.dumps(anexos_salvos)
                query_update = text("""
                    UPDATE matriz_achados 
                    SET anexos = CAST(:anexos AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                """)
                conn.execute(query_update, {
                    'anexos': anexos_json,
                    'id': achado_id
                })
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'achado_id': achado_id,
                'message': 'Achado adicionado com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao adicionar achado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/achado/<int:achado_id>', methods=['PUT'])
def api_editar_achado(achado_id):
    """Edita um achado existente (texto e anexos)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import base64
    import json
    from datetime import datetime
    
    try:
        data = request.get_json()
        texto = data.get('texto', '').strip()
        novos_anexos = data.get('anexos', [])
        
        if not texto:
            return jsonify({'success': False, 'error': 'Texto do achado é obrigatório'}), 400
        
        usuario_id = session.get('usuario_id')
        is_admin = session.get('usuario_perfil') in ['administrador', 'admin']
        
        with engine.connect() as conn:
            # 1. VERIFICAR PERMISSÃO
            query_check = text("""
                SELECT usuario_id, anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result_check = conn.execute(query_check, {'achado_id': achado_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            autor_id = result_check[0]
            anexos_existentes = []
            if result_check[1]:
                if isinstance(result_check[1], str):
                    anexos_existentes = json.loads(result_check[1])
                else:
                    anexos_existentes = result_check[1] or []
            
            # Verificar se é o autor ou admin
            if autor_id != usuario_id and not is_admin:
                return jsonify({'success': False, 'error': 'Sem permissão para editar este achado'}), 403
            
            # 2. ATUALIZAR TEXTO
            query_update = text("""
                UPDATE matriz_achados 
                SET texto = :texto,
                    data_edicao = NOW(),
                    updated_at = NOW()
                WHERE id = :id
            """)
            conn.execute(query_update, {
                'texto': texto,
                'id': achado_id
            })
            
            # 3. PROCESSAR NOVOS ANEXOS
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            anexos_salvos = anexos_existentes.copy()
            
            for anexo in novos_anexos:
                nome_arquivo = anexo.get('nome')
                tipo_arquivo = anexo.get('tipo', 'application/octet-stream')
                tamanho = anexo.get('tamanho', 0)
                base64_data = anexo.get('base64')
                
                if not base64_data or not nome_arquivo:
                    continue
                
                # Decodificar Base64
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                arquivo_bytes = base64.b64decode(base64_data)
                
                # Validar tamanho (10MB)
                if len(arquivo_bytes) > 10 * 1024 * 1024:
                    continue
                
                # Gerar caminho único no Storage

                timestamp = int(datetime.now().timestamp())
                query_auditoria = text("""
                    SELECT auditoria_id 
                    FROM matriz_achados 
                    WHERE id = :achado_id
                """)
                result_auditoria = conn.execute(query_auditoria, {'achado_id': achado_id}).fetchone()
                auditoria_id = result_auditoria[0]

                # Depois usar o mesmo padrão do POST
                caminho_storage = f"matriz_achados_auditoria/auditoria_id_{auditoria_id}/achado_id_{achado_id}/{timestamp}_{nome_arquivo}"
                
                # Upload para o Storage
                try:
                    supabase.storage.from_('matriz_achados_anexos').upload(
                        path=caminho_storage,
                        file=arquivo_bytes,
                        file_options={"content-type": tipo_arquivo}
                    )
                    
                    anexos_salvos.append({
                        'nome': nome_arquivo,
                        'caminho': caminho_storage,
                        'tipo': tipo_arquivo,
                        'tamanho': tamanho,
                        'data_upload': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"⚠️ Erro no upload do anexo {nome_arquivo}: {e}")
            
            # 4. ATUALIZAR CAMPO ANEXOS
            if anexos_salvos:
                anexos_json = json.dumps(anexos_salvos)
                query_update_anexos = text("""
                    UPDATE matriz_achados 
                    SET anexos = CAST(:anexos AS jsonb)
                    WHERE id = :id
                """)
                conn.execute(query_update_anexos, {
                    'anexos': anexos_json,
                    'id': achado_id
                })
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Achado atualizado com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao editar achado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/achado/<int:achado_id>', methods=['DELETE'])
def api_excluir_achado(achado_id):
    """Exclui um achado e seus anexos do Storage"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import json
    
    try:
        usuario_id = session.get('usuario_id')
        usuario_perfil = session.get('usuario_perfil')
        is_admin = usuario_perfil in ['administrador', 'admin']
        
        with engine.connect() as conn:
            # 1. VERIFICAR PERMISSÃO
            query_check = text("""
                SELECT usuario_id, anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result_check = conn.execute(query_check, {'achado_id': achado_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            autor_id = result_check[0]
            anexos_json = result_check[1]
            
            # Verificar se é o autor ou admin
            if autor_id != usuario_id and not is_admin:
                return jsonify({'success': False, 'error': 'Sem permissão para excluir este achado'}), 403
            
            # 2. REMOVER ANEXOS DO STORAGE
            anexos = []
            if anexos_json:
                if isinstance(anexos_json, str):
                    anexos = json.loads(anexos_json)
                else:
                    anexos = anexos_json or []
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            if anexos:
                try:
                    caminhos = [a.get('caminho') for a in anexos if a.get('caminho')]
                    if caminhos:
                        supabase.storage.from_('matriz_achados_anexos').remove(caminhos)
                        print(f"🗑️ Removidos {len(caminhos)} arquivos do Storage")
                except Exception as e:
                    print(f"⚠️ Erro ao remover arquivos do Storage: {e}")
            
            # 3. REMOVER DO BANCO
            query_delete = text("DELETE FROM matriz_achados WHERE id = :achado_id")
            conn.execute(query_delete, {'achado_id': achado_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Achado excluído com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir achado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/achado/<int:achado_id>/anexo/<int:anexo_index>', methods=['DELETE'])
def api_remover_anexo(achado_id, anexo_index):
    """Remove um anexo específico de um achado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import json
    
    try:
        usuario_id = session.get('usuario_id')
        is_admin = session.get('usuario_perfil') in ['administrador', 'admin']
        
        with engine.connect() as conn:
            # 1. VERIFICAR PERMISSÃO
            query_check = text("""
                SELECT usuario_id, anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result_check = conn.execute(query_check, {'achado_id': achado_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            autor_id = result_check[0]
            
            # Verificar se é o autor ou admin
            if autor_id != usuario_id and not is_admin:
                return jsonify({'success': False, 'error': 'Sem permissão'}), 403
            
            # 2. BUSCAR ANEXOS
            anexos = []
            if result_check[1]:
                if isinstance(result_check[1], str):
                    anexos = json.loads(result_check[1])
                else:
                    anexos = result_check[1] or []
            
            if anexo_index >= len(anexos):
                return jsonify({'success': False, 'error': 'Anexo não encontrado'}), 404
            
            anexo_removido = anexos[anexo_index]
            caminho_storage = anexo_removido.get('caminho')
            
            # 3. REMOVER DO STORAGE
            if caminho_storage:
                # ⭐ USAR O SINGLETON
                from supabase_client import SupabaseClient
                supabase = SupabaseClient.get_instance()
                
                try:
                    supabase.storage.from_('matriz_achados_anexos').remove([caminho_storage])
                    print(f"🗑️ Arquivo removido do Storage: {caminho_storage}")
                except Exception as e:
                    print(f"⚠️ Erro ao remover do Storage: {e}")
            
            # 4. REMOVER DO JSON
            anexos.pop(anexo_index)
            anexos_json = json.dumps(anexos)
            
            query_update = text("""
                UPDATE matriz_achados 
                SET anexos = CAST(:anexos AS jsonb),
                    updated_at = NOW()
                WHERE id = :id
            """)
            conn.execute(query_update, {
                'anexos': anexos_json,
                'id': achado_id
            })
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Anexo removido com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover anexo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/achado/anexo/<int:achado_id>/<int:anexo_index>/download', methods=['GET'])
def api_download_anexo_achado(achado_id, anexo_index):
    """Baixa um anexo de um achado pelo índice no JSON"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result = conn.execute(query, {'achado_id': achado_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            anexos = []
            if result[0]:
                if isinstance(result[0], str):
                    anexos = json.loads(result[0])
                else:
                    anexos = result[0] or []
            
            if anexo_index >= len(anexos):
                return jsonify({'success': False, 'error': 'Anexo não encontrado'}), 404
            
            anexo = anexos[anexo_index]
            caminho_storage = anexo.get('caminho')
            nome_arquivo = anexo.get('nome')
            
            if not caminho_storage:
                return jsonify({'success': False, 'error': 'Caminho do arquivo não encontrado'}), 404
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            url_assinada = supabase.storage.from_('matriz_achados_anexos').create_signed_url(
                path=caminho_storage,
                expires_in=3600  # 1 hora
            )
            
            signed_url = url_assinada['signedURL'] if isinstance(url_assinada, dict) else url_assinada
            
            return jsonify({
                'success': True,
                'url': signed_url,
                'nome_arquivo': nome_arquivo
            })
            
    except Exception as e:
        print(f"❌ Erro ao baixar anexo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# FIM - MATRIZ DE ACHADOS (COMENTÁRIOS COM ANEXOS)
# ============================================================

@app.route('/api/evidencia/<path:caminho>')
def api_baixar_evidencia(caminho):
    """Baixa uma evidência do Supabase Storage"""
    try:
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket_name = 'evidencias_auditorias'
        
        # Gerar URL assinada (1 hora)
        url_assinada = supabase.storage.from_(bucket_name).create_signed_url(
            path=caminho,
            expires_in=3600
        )
        
        # Extrair a URL do dicionário
        if isinstance(url_assinada, dict) and 'signedURL' in url_assinada:
            url = url_assinada['signedURL']
        else:
            url = url_assinada
        
        return jsonify({
            'success': True,
            'url': url
        })
        
    except Exception as e:
        print(f"❌ Erro ao baixar evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# API - DIAGNÓSTICO DOS PROCESSOS
# ============================================================
@app.route('/api/processo/verificar')
def api_verificar_processo():
    """Verifica se um processo com o mesmo nome já existe na área E auditoria"""
    # 👇 CONVERTER PARA MAIÚSCULAS
    nome_processo = request.args.get('nome', '').upper().strip()
    id_area = request.args.get('id_area')
    auditoria_id = request.args.get('auditoria_id')

    if not nome_processo or not id_area or not auditoria_id:
        return jsonify({'existe': False})
    
    from logic import buscar_processo_por_nome_e_area
    processo = buscar_processo_por_nome_e_area(nome_processo, id_area, auditoria_id)

    if processo:
        return jsonify({
            'existe': True,
            'processo_id': processo['id'],
            'codigo': processo['codigo_processo']
        })
    return jsonify({'existe': False})

@app.route('/api/processo/gerar-codigo')
def api_gerar_codigo_processo():
    """Gera o próximo código sequencial para uma área em uma auditoria específica"""
    from logic import gerar_codigo_processo
    
    id_area = request.args.get('id_area')
    auditoria_id = request.args.get('auditoria_id')  # ← NOVO
    
    if not id_area or not auditoria_id:
        return jsonify({'error': 'id_area e auditoria_id são obrigatórios'}), 400
    
    try:
        id_area = int(id_area)
        auditoria_id = int(auditoria_id)
    except ValueError:
        return jsonify({'error': 'id_area e auditoria_id devem ser números'}), 400
    
    codigo = gerar_codigo_processo(id_area, auditoria_id)  # ← MODIFICAR
    
    return jsonify({'codigo': codigo})


@app.route('/api/area/<int:area_id>/upload-organograma', methods=['POST'])
def api_upload_organograma(area_id):
    """Faz upload do organograma para o Supabase Storage - qualquer usuário autenticado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import base64
    
    data = request.json
    arquivo_base64 = data.get('arquivo_base64')
    nome_arquivo = data.get('nome_arquivo')
    tipo_arquivo = data.get('tipo_arquivo')
    
    if not arquivo_base64:
        return jsonify({'success': False, 'error': 'Arquivo é obrigatório'}), 400
    
    try:
        # 1. Decodificar Base64
        if ',' in arquivo_base64:
            arquivo_base64 = arquivo_base64.split(',')[1]
        arquivo_bytes = base64.b64decode(arquivo_base64)
        
        # 2. Validar tamanho (5MB)
        if len(arquivo_bytes) > 5 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Arquivo muito grande. Máximo 5MB'}), 400
        
        # 3. Conectar ao Supabase - USAR SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        # 4. Gerar caminho único
        extensao = nome_arquivo.split('.')[-1].lower()
        caminho = f"area_{area_id}/organograma.{extensao}"
        
        # 5. Fazer upload
        print(f"📎 Fazendo upload do organograma: {caminho}")
        supabase.storage.from_('organogramas').upload(
            path=caminho,
            file=arquivo_bytes,
            file_options={"content-type": tipo_arquivo}
        )
        
        # 6. Obter URL pública
        public_url = supabase.storage.from_('organogramas').get_public_url(caminho)
        
        # 7. Salvar no banco
        with engine.connect() as conn:
            query = text("""
                UPDATE informacoes_area 
                SET organograma_url = :url,
                    organograma_nome = :nome
                WHERE id_area = :area_id
            """)
            conn.execute(query, {
                'url': public_url,
                'nome': nome_arquivo,
                'area_id': area_id
            })
            conn.commit()
        
        print(f"✅ Organograma salvo com sucesso para área {area_id}")
        
        return jsonify({
            'success': True,
            'url': public_url,
            'nome': nome_arquivo,
            'message': 'Organograma salvo com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro no upload do organograma: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/area/<int:area_id>/organograma', methods=['GET'])
def api_buscar_organograma(area_id):
    """Busca o organograma da área"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT organograma_url, organograma_nome
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({
                    'success': True,
                    'tem_organograma': False
                })
            
            return jsonify({
                'success': True,
                'tem_organograma': True,
                'url': result[0],
                'nome': result[1] or 'Organograma'
            })
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/area/<int:area_id>/organograma', methods=['DELETE'])
def api_remover_organograma(area_id):
    """Remove o organograma da área - qualquer usuário autenticado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar URL atual
            query = text("SELECT organograma_url FROM informacoes_area WHERE id_area = :area_id")
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if result and result[0]:
                # ⭐ USAR O SINGLETON
                from supabase_client import SupabaseClient
                supabase = SupabaseClient.get_instance()
                
                # Extrair caminho da URL
                if '/organogramas/' in result[0]:
                    caminho = result[0].split('/organogramas/')[-1]
                    try:
                        supabase.storage.from_('organogramas').remove([caminho])
                        print(f"✅ Arquivo removido do storage: {caminho}")
                    except Exception as e:
                        print(f"⚠️ Erro ao remover do storage: {e}")
            
            # Limpar banco
            query = text("""
                UPDATE informacoes_area 
                SET organograma_url = NULL,
                    organograma_nome = NULL
                WHERE id_area = :area_id
            """)
            conn.execute(query, {'area_id': area_id})
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Organograma removido com sucesso!'})
        
    except Exception as e:
        print(f"❌ Erro ao remover organograma: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/api/processo/<int:processo_id>/desativar', methods=['PUT'])
def api_desativar_processo(processo_id):
    """Desativa um processo (soft delete)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET status = 'Inativo'
                WHERE id = :processo_id
            """)
            conn.execute(query, {'processo_id': processo_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Processo desativado'})
            
    except Exception as e:
        print(f"❌ Erro ao desativar processo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/riscos')
def api_processo_riscos(processo_id):
    """Retorna os riscos de um processo"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    id, nome_risco, fator_risco, melhoria,
                    impacto, probabilidade, motivo_risco,
                    categoria, causas,
                    tratamento_risco, descricao_tratamento, prazo_implantacao,
                    score_risco, apetite_impacto, apetite_probabilidade
                FROM riscos
                WHERE processo_id = :processo_id
            """)
            result = conn.execute(query, {'processo_id': processo_id}).fetchall()
            
            riscos = []
            for row in result:               
                # Converter strings para listas
                categorias_str = row[7] if len(row) > 8 else ''
                causas_str = row[7] if len(row) > 9 else ''
                
                categorias = categorias_str.split(',') if categorias_str else []
                causas_list = causas_str.split(',') if causas_str else []
                
                # Formatar data
                prazo = row[11] if len(row) > 11 and row[11] else ''
                
                risco = {
                    'id': row[0],
                    'nome_risco': row[1] if len(row) > 1 and row[1] else '',
                    'fator_risco': row[2] if len(row) > 2 and row[2] else '',
                    'melhoria': row[3] if len(row) > 3 and row[3] else '',
                    'impacto': row[4] if len(row) > 4 and row[4] else 'Médio',
                    'probabilidade': row[5] if len(row) > 5 and row[5] else 'Médio',
                    'motivo_risco': row[6] if len(row) > 6 and row[6] else '',
                    'categorias': [c.strip() for c in categorias if c.strip()],
                    'categoria_causa': [c.strip() for c in causas_list if c.strip()],
                    'score_risco': row[12] if len(row) > 12 and row[12] else 0,
                    # ⭐ CAMPOS DE TRATAMENTO CORRIGIDOS ⭐
                    'como_tratar': row[9] if len(row) > 9 and row[9] else '',
                    'desc_tratamento': row[10] if len(row) > 10 and row[10] else '',
                    'prazo_implantacao': prazo,
                    'apetite_impacto': row[13] if len(row) > 13 and row[13] else 'Médio',
                    'apetite_probabilidade': row[14] if len(row) > 14 and row[14] else 'Médio'
                }
                
                riscos.append(risco)
            
            # Log para debug no servidor
            print(f"✅ Buscou {len(riscos)} riscos para o processo {processo_id}")
            if riscos:
                print(f"📊 Primeiro risco - como_tratar: '{riscos[0].get('como_tratar', 'N/A')}'")
                print(f"📊 Primeiro risco - desc_tratamento: '{riscos[0].get('desc_tratamento', 'N/A')}'")
            
            return jsonify({'success': True, 'riscos': riscos})
            
    except Exception as e:
        print(f"❌ Erro ao buscar riscos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    

    
@app.route('/api/processos-por-auditoria')
def api_processos_por_auditoria():
    """Retorna todos os processos de uma auditoria"""
    from database import engine
    from sqlalchemy import text

    auditoria_id = request.args.get('auditoria_id')
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            # ⭐ AGORA É DIRETO - SEM JOIN!
            query = text("""
                SELECT p.id, p.codigo_processo, p.nome_processo, p.objetivo
                FROM processos p
                WHERE p.auditoria_id = :auditoria_id
                    AND p.status = 'Ativo'
                ORDER BY 
                    CAST(SUBSTRING(p.codigo_processo FROM '^[0-9]+') AS INTEGER),
                    CAST(SUBSTRING(p.codigo_processo FROM '[0-9]+$') AS INTEGER)
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id})
            processos = [dict(row._mapping) for row in result]

            return jsonify({'success': True, 'processos': processos})
    
    except Exception as e:
        print(f"❌ Erro ao buscar processos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
                           

# ============================================================
# API - ÁREAS E FUNCIONÁRIOS
# ============================================================

@app.route('/api/areas')
def api_areas():
    """Retorna todas as áreas (ativas e inativas)"""
    
    
    # Passar apenas_ativas=False para buscar TODAS as áreas
    df = listar_areas(apenas_ativas=False)
    
    if df.empty:
        return jsonify([])
    
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/totais')
def api_totais():
    """Retorna totais de áreas e funcionários"""
    
    df_areas = listar_areas()
    total_areas = len(df_areas) if not df_areas.empty else 0
    
    total_funcionarios = 0
    if not df_areas.empty:
        for _, area in df_areas.iterrows():
            df_func = listar_funcionarios_area(area['id_area'])
            if not df_func.empty:
                total_funcionarios += len(df_func)
    
    return jsonify({
        'areas': total_areas,
        'funcionarios': total_funcionarios,
        'total_geral': total_areas + total_funcionarios
    })

@app.route('/api/area/<int:area_id>')
def api_area_detalhes(area_id):
    """Retorna detalhes de uma área específica (com organograma)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ BUSCAR DIRETAMENTE COM OS CAMPOS DO ORGANOGRAMA
            query = text("""
                SELECT id_area, nome_area, loc_unidade, email, telefone, gestor,
                       superintendente, diretor, objetivo_area, status,
                       organograma_url, organograma_nome
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if not result:
                return jsonify({}), 404
            
            # Converter para dicionário
            area_dict = {
                'id_area': result[0],
                'nome_area': result[1],
                'loc_unidade': result[2],
                'email': result[3],
                'telefone': result[4],
                'gestor': result[5],
                'superintendente': result[6] or '',
                'diretor': result[7] or '',
                'objetivo_area': result[8] or '',
                'status': result[9],
                'organograma_url': result[10] or '',  # ⭐
                'organograma_nome': result[11] or '', # ⭐
                'unidade': result[2]  # Para compatibilidade
            }
            
            return jsonify(area_dict)
            
    except Exception as e:
        print(f"❌ Erro ao buscar área: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/area/<int:area_id>/funcionarios')
def api_area_funcionarios(area_id):
    """Retorna todos os funcionários de uma área com tempo calculado"""
    
    df = listar_funcionarios_area(area_id)
    
    if df.empty:
        return jsonify([])
    
    funcionarios = df.to_dict(orient='records')
    
    for func in funcionarios:
        func['tempo_funcao'] = calcular_tempo(func.get('data_inicio_funcao'))
        func['tempo_empresa'] = calcular_tempo(func.get('data_inicio_empresa'))
    
    return jsonify(funcionarios)

@app.route('/api/area/<int:area_id>', methods=['DELETE'])
def api_excluir_area(area_id):
    """Desativa uma área (soft delete) - qualquer usuário autenticado"""
    from logic import excluir_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    resultado = excluir_area(area_id)
    print(f"🔍 Resultado de excluir_area({area_id}): {resultado}")
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao desativar área'}), 400

@app.route('/api/area/<int:area_id>/organograma-url', methods=['GET'])
def api_organograma_url(area_id):
    """Retorna URL assinada para o organograma (validade 5 minutos)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT organograma_url, organograma_nome
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Organograma não encontrado'}), 404
            
            url_completa = result[0]
            nome = result[1] or 'organograma'
            
            # Extrair o caminho da URL pública
            if '/organogramas/' in url_completa:
                caminho = url_completa.split('/organogramas/')[-1]
            else:
                caminho = url_completa
            
            print(f"📎 Caminho extraído: {caminho}")
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            # Gerar URL assinada (expira em 300 segundos = 5 minutos)
            url_assinada = supabase.storage.from_('organogramas').create_signed_url(
                path=caminho,
                expires_in=300
            )
            
            return jsonify({
                'success': True,
                'url': url_assinada['signedURL'],
                'nome': nome
            })
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/salvar-area', methods=['POST'])
def api_salvar_area():
    from logic import salvar_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json
    
    if not dados.get('nome'):
        return jsonify({'success': False, 'error': 'Nome da área é obrigatório'}), 400
    
    if not dados.get('gestor'):
        return jsonify({'success': False, 'error': 'Gestor é obrigatório'}), 400
    
    resultado = salvar_area(dados)
    
    if resultado:
        return jsonify({'success': True, 'id': resultado})
    return jsonify({'success': False, 'error': 'Falha ao salvar área'}), 400

@app.route('/api/area/<int:area_id>', methods=['PUT'])
def api_atualizar_area(area_id):
    from logic import atualizar_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json
    dados['superintendente'] = dados.get('superintendente', '')
    dados['diretor'] = dados.get('diretor', '')

    resultado = atualizar_area(area_id, dados)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao atualizar área'}), 400

@app.route('/api/area/<int:area_id>/reativar', methods=['PUT'])
def api_reativar_area(area_id):
    """Reativa uma área - qualquer usuário autenticado"""
    from logic import reativar_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    resultado = reativar_area(area_id)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao reativar área'}), 400

@app.route('/api/area/<int:area_id>/todos-funcionarios')
def api_area_todos_funcionarios(area_id):
    """Retorna TODOS os funcionários de uma área (ativos e inativos) com tempo calculado"""
    from logic import listar_funcionarios_area_todos
    
    df = listar_funcionarios_area_todos(area_id)
    
    if df.empty:
        return jsonify([])
    
    funcionarios = df.to_dict(orient='records')
    
    # Adicionar tempo calculado para cada funcionário
    for func in funcionarios:
        func['tempo_funcao'] = calcular_tempo(func.get('data_inicio_funcao'))
        func['tempo_empresa'] = calcular_tempo(func.get('data_inicio_empresa'))
    
    return jsonify(funcionarios)

@app.route('/api/funcionario/<int:funcionario_id>', methods=['DELETE'])
def api_excluir_funcionario(funcionario_id):
    """Exclui um funcionário - qualquer usuário autenticado"""
    from logic import excluir_funcionario
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    resultado = excluir_funcionario(funcionario_id)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao excluir funcionário'}), 400

@app.route('/api/funcionario/<int:funcionario_id>', methods=['PUT'])
def api_atualizar_funcionario(funcionario_id):
    """Atualiza um funcionário - qualquer usuário autenticado"""
    from logic import atualizar_funcionario

    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json
    
    # ⭐ VALIDAÇÃO BÁSICA
    if not dados.get('nome'):
        return jsonify({'success': False, 'error': 'Nome do funcionário é obrigatório'}), 400
    
    resultado = atualizar_funcionario(funcionario_id, dados)

    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao atualizar funcionário'}), 400

@app.route('/api/funcionario/<int:funcionario_id>')
def api_funcionario_detalhes(funcionario_id):
    """Retorna os dados de um funcionário específico"""
    from logic import buscar_funcionario_por_id

    funcionario = buscar_funcionario_por_id(funcionario_id)

    if funcionario:
        return jsonify(funcionario)
    return jsonify({}), 404

@app.route('/api/salvar-funcionario', methods=['POST'])
def api_salvar_funcionario():
    """Salva um novo funcionário - qualquer usuário autenticado"""
    from logic import salvar_funcionario

    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json

    if not dados.get('nome'):
        return jsonify({'success': False, 'error': 'Nome do funcionário é obrigatório'}), 400
    
    if not dados.get('id_area'):
        return jsonify({'success': False, 'error': 'Área é obrigatória'}), 400
    
    resultado = salvar_funcionario(dados)
    
    if resultado:
        return jsonify({'success': True, 'id': resultado})
    return jsonify({'success': False, 'error': 'Falha ao salvar funcionário'}), 400

# ============================================================
# DETALHAMENTO DOS PROCESSOS
# ============================================================

@app.route('/detalhamento_controles')
def detalhamento_controles():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    
    return render_template('detalhamento_controles.html', areas=areas)

@app.route('/matriz_achados')
def matriz_achados():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    
    return render_template('matriz_achados.html', areas=areas)






@app.route('/api/risco/<int:risco_id>/controles')
def api_risco_controles(risco_id):
    """Retorna todos os controles associados a um risco"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_controle, como_executado, objetivo_controle,
                       periodicidade_execucao, evidencia_realizacao, forma_execucao,
                       natureza, status_controle, responsaveis_tratamento,
                       risco_avaliacao, causa_motivo, frequencia_evidencia, 
                       local_evidencia, lgpd, created_at, updated_at
                FROM controles_etapa
                WHERE risco_id = :risco_id
                ORDER BY id
            """)
            
            result = conn.execute(query, {'risco_id': risco_id}).fetchall()
            
            controles = []
            for row in result:
                controles.append({
                    'id': row[0],
                    'nome_controle': row[1] or '',
                    'como_executado': row[2] or '',
                    'objetivo_controle': row[3] or '',
                    'periodicidade_execucao': row[4] or '',
                    'evidencia_realizacao': row[5] or '',
                    'forma_execucao': row[6] or '',
                    'natureza': row[7] or '',
                    'status_controle': row[8] or '',
                    'responsaveis_tratamento': row[9] or '',
                    'risco_avaliacao': row[10] or '',
                    'causa_motivo': row[11] or '',
                    'frequencia_evidencia': row[12] or '',
                    'local_evidencia': row[13] or '',
                    'lgpd': row[14] or '',
                    'created_at': row[15].isoformat() if row[15] else '',
                    'updated_at': row[16].strftime('%Y-%m-%d') if row[16] else ''
                })
            
            return jsonify({'success': True, 'controles': controles})
            
    except Exception as e:
        print(f"❌ Erro ao buscar controles do risco: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/controles/count')
def api_etapa_controles_count(etapa_id):
    """Retorna a quantidade de controles de uma etapa"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) FROM controles_etapa ce
                WHERE ce.risco_id IN (
                    -- Riscos da etapa (riscos_etapa)
                    SELECT re.id 
                    FROM riscos_etapa re 
                    WHERE re.etapa_id = :etapa_id AND re.ativo = true
                    
                    UNION
                    
                    -- Riscos do processo vinculados (tabela riscos)
                    SELECT CAST(unnest(string_to_array(ep.riscos_processo_ids, ', ')) AS bigint)
                    FROM etapas_processo ep
                    WHERE ep.id = :etapa_id
                    AND ep.riscos_processo_ids IS NOT NULL
                    AND ep.riscos_processo_ids != ''
                )
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            return jsonify({'success': True, 'total': result[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/risco/<int:risco_id>/controles/count')
def api_risco_controles_count(risco_id):
    """Retorna a quantidade de controles de um risco específico"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) as total
                FROM controles_etapa
                WHERE risco_id = :risco_id
            """)
            result = conn.execute(query, {'risco_id': risco_id}).fetchone()
            
            return jsonify({
                'success': True,
                'total': result[0] or 0
            })
            
    except Exception as e:
        print(f"❌ Erro ao contar controles do risco {risco_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# COMUNICAÇÃO DOS RESULTADOS
# ============================================================

@app.route('/api/checklist/analises-por-auditoria')
def api_checklist_analises_por_auditoria():
    """Retorna as análises críticas de todas as etapas dos processos de uma auditoria, filtradas por categoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    categoria = request.args.get('categoria', 'governanca')
    
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    ac.id, ac.tipo, ac.categoria,
                    ac.analise_critica, ac.sugestao_melhoria,
                    ac.necessidade_implantacao, ac.ganho_previsto,
                    ep.codigo_etapa, ep.nome_etapa,
                    p.codigo_processo, p.nome_processo
                FROM analises_criticas ac
                JOIN etapas_processo ep ON ac.etapa_id = ep.id
                JOIN processos p ON ep.processo_id = p.id
                WHERE p.auditoria_id = :auditoria_id   -- ← AGORA É DIRETO!
                AND ac.categoria = :categoria
                ORDER BY p.codigo_processo, ep.codigo_etapa, ac.tipo
            """)
            
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'categoria': categoria
            }).fetchall()
            
            analises = []
            for row in result:
                analises.append({
                    'id': row[0],
                    'tipo': row[1],
                    'categoria': row[2],
                    'analise_critica': row[3] or '',
                    'sugestao_melhoria': row[4] or '',
                    'necessidade_implantacao': row[5] or '',
                    'ganho_previsto': row[6] or '',
                    'codigo_etapa': row[7] or '',
                    'nome_etapa': row[8] or '',
                    'codigo_processo': row[9] or '',
                    'nome_processo': row[10] or ''
                })
            
            return jsonify({'success': True, 'analises': analises})
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/carregar', methods=['GET'])
def api_checklist_carregar():
    """Carrega as respostas de um checklist para um processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    tipo = request.args.get('tipo')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    if not tipo or tipo not in ['governanca', 'riscos', 'controles']:
        return jsonify({'success': False, 'error': 'tipo inválido'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ 1. BUSCAR O CHECKLIST
            query_checklist = text("""
                SELECT id, status, observacoes_gerais
                FROM checklists
                WHERE processo_id = :processo_id AND tipo = :tipo
            """)
            
            checklist = conn.execute(query_checklist, {
                'processo_id': processo_id,
                'tipo': tipo
            }).fetchone()
            
            num_perguntas = {
                'governanca': 13,
                'riscos': 12,
                'controles': 12
            }.get(tipo, 12)
            
            if not checklist:
                respostas_vazias = []
                for i in range(1, num_perguntas + 1):
                    respostas_vazias.append({
                        'id': None,  # ← ID DA RESPOSTA (None)
                        'ordem': i,
                        'resposta': '',
                        'comentario': '',
                        'evidencias': []
                    })
                
                return jsonify({
                    'success': True,
                    'id': None,
                    'status': 'Não iniciado',
                    'observacoes_gerais': '',
                    'respostas': respostas_vazias
                })
            
            checklist_id = checklist[0]
            status = checklist[1] or 'Não iniciado'
            observacoes = checklist[2] or ''
            
            # ⭐ 2. BUSCAR AS RESPOSTAS
            query_respostas = text("""
                SELECT id, pergunta_ordem, resposta, comentario
                FROM checklist_respostas
                WHERE checklist_id = :checklist_id
                ORDER BY pergunta_ordem
            """)

            respostas_db = conn.execute(query_respostas, {
                'checklist_id': checklist_id
            }).fetchall()

            # ⭐ 3. CRIAR MAPA DE RESPOSTAS POR ORDEM COM O ID CORRETO
            respostas_map = {}
            for r in respostas_db:
                # ⭐ CONVERTER PARA STRING (já que pergunta_ordem é VARCHAR)
                chave = str(r[1])
                respostas_map[chave] = {
                    'id': r[0],
                    'ordem': r[1],
                    'resposta': r[2] or '',
                    'comentario': r[3] or ''
                }

            # ⭐ LOG PARA DEBUG
            print(f"🔍 Respostas encontradas: {len(respostas_db)}")
            print(f"🔍 Mapa de respostas: {respostas_map}")

            # ⭐ 4. MONTAR RESPOSTAS NA ORDEM CORRETA
            respostas = []

            if tipo == 'governanca':
                # Definição das ordens do frontend
                ordens_frontend = ['1', '1.1', '1.2', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13']
                
                # Mapeamento: frontend_ordem -> banco_pergunta_ordem
                mapeamento_banco = {
                    '1': '1',
                    '1.1': '1.1',
                    '1.2': '1.2',
                    '2': '2',
                    '3': '3',
                    '4': '4',
                    '5': '5',
                    '6': '6',
                    '7': '7',
                    '8': '8',
                    '9': '9',
                    '10': '10',
                    '11': '11',
                    '12': '12',
                    '13': '13'   # ← AGORA CORRETO!
                }
                
                for ordem_frontend in ordens_frontend:
                    ordem_banco = mapeamento_banco.get(ordem_frontend, ordem_frontend)
                    resposta_data = respostas_map.get(ordem_banco, {
                        'id': None,
                        'ordem': ordem_frontend,
                        'resposta': '',
                        'comentario': ''
                    })
                    
                    # Buscar evidências
                    evidencias = []
                    if resposta_data['id']:
                        query_evidencias = text("""
                            SELECT id, nome_arquivo, tamanho_bytes
                            FROM checklist_evidencias
                            WHERE resposta_id = :resposta_id
                        """)
                        ev_result = conn.execute(query_evidencias, {
                            'resposta_id': resposta_data['id']
                        }).fetchall()
                        
                        for ev in ev_result:
                            evidencias.append({
                                'id': ev[0],
                                'nome': ev[1],
                                'tamanho': ev[2]
                            })
                    
                    respostas.append({
                        'id': resposta_data['id'],
                        'ordem': ordem_frontend,
                        'resposta': resposta_data['resposta'],
                        'comentario': resposta_data['comentario'],
                        'evidencias': evidencias
                    })

            else:
                # Para riscos e controles, ordem normal
                for i in range(1, num_perguntas + 1):
                    ordem = str(i)
                    resposta_data = respostas_map.get(ordem, {
                        'id': None,
                        'ordem': ordem,
                        'resposta': '',
                        'comentario': ''
                    })
                    
                    # Buscar evidências
                    evidencias = []
                    if resposta_data['id']:
                        query_evidencias = text("""
                            SELECT id, nome_arquivo, tamanho_bytes
                            FROM checklist_evidencias
                            WHERE resposta_id = :resposta_id
                        """)
                        ev_result = conn.execute(query_evidencias, {
                            'resposta_id': resposta_data['id']
                        }).fetchall()
                        
                        for ev in ev_result:
                            evidencias.append({
                                'id': ev[0],
                                'nome': ev[1],
                                'tamanho': ev[2]
                            })
                    
                    respostas.append({
                        'id': resposta_data['id'],
                        'ordem': ordem,
                        'resposta': resposta_data['resposta'],
                        'comentario': resposta_data['comentario'],
                        'evidencias': evidencias
                    })

            # ⭐ LOG PARA DEBUG
            print(f"📤 Respostas sendo enviadas: {[{'id': r['id'], 'ordem': r['ordem']} for r in respostas]}")
            
            return jsonify({
                'success': True,
                'id': checklist_id,
                'status': status,
                'observacoes_gerais': observacoes,
                'respostas': respostas  # ← CADA UMA COM SEU ID
            })
            
    except Exception as e:
        print(f"❌ Erro ao carregar checklist: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/salvar', methods=['POST'])
def api_checklist_salvar():
    """Salva as respostas de um checklist (UPSERT)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    processo_id = data.get('processo_id')
    tipo = data.get('tipo')
    respostas = data.get('respostas', [])
    concluir = data.get('concluir', False)
    observacoes_gerais = data.get('observacoes_gerais', '')
    
    if not processo_id or not tipo:
        return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # 1. BUSCAR OU CRIAR O CHECKLIST
            query_checklist = text("""
                SELECT id FROM checklists
                WHERE processo_id = :processo_id AND tipo = :tipo
            """)
            checklist = conn.execute(query_checklist, {
                'processo_id': processo_id,
                'tipo': tipo
            }).fetchone()
            
            if not checklist:
                query_insert = text("""
                    INSERT INTO checklists (processo_id, tipo, status, observacoes_gerais)
                    VALUES (:processo_id, :tipo, 'Não iniciado', :observacoes_gerais)
                    RETURNING id
                """)
                result = conn.execute(query_insert, {
                    'processo_id': processo_id,
                    'tipo': tipo,
                    'observacoes_gerais': observacoes_gerais
                })
                conn.commit()
                checklist_id = result.fetchone()[0]
                print(f"📝 Checklist criado: id={checklist_id}")
            else:
                checklist_id = checklist[0]
                print(f"📝 Checklist encontrado: id={checklist_id}")
                # Atualizar observações gerais
                query_update = text("""
                    UPDATE checklists SET observacoes_gerais = :observacoes_gerais
                    WHERE id = :checklist_id
                """)
                conn.execute(query_update, {
                    'observacoes_gerais': observacoes_gerais,
                    'checklist_id': checklist_id
                })
                conn.commit()
            
            # ⭐ 2. UPSERT - INSERIR OU ATUALIZAR RESPOSTAS (SEM DELETAR)
            respostas_ids = {}
            
            for resp in respostas:
                pergunta_ordem = resp.get('ordem')
                resposta_valor = resp.get('resposta', '')
                comentario_valor = resp.get('comentario', '')
                
                print(f"📝 Upsert resposta: pergunta={pergunta_ordem}, resposta='{resposta_valor}'")
                
                # ⭐⭐ USAR ON CONFLICT PARA ATUALIZAR EM VEZ DE DELETAR ⭐⭐
                query_upsert = text("""
                    INSERT INTO checklist_respostas (checklist_id, pergunta_ordem, resposta, comentario)
                    VALUES (:checklist_id, :pergunta_ordem, :resposta, :comentario)
                    ON CONFLICT (checklist_id, pergunta_ordem) 
                    DO UPDATE SET 
                        resposta = EXCLUDED.resposta,
                        comentario = EXCLUDED.comentario,
                        updated_at = NOW()
                    RETURNING id
                """)
                
                result = conn.execute(query_upsert, {
                    'checklist_id': checklist_id,
                    'pergunta_ordem': pergunta_ordem,
                    'resposta': resposta_valor,
                    'comentario': comentario_valor
                })
                conn.commit()
                
                resposta_id = result.fetchone()[0]
                respostas_ids[str(pergunta_ordem)] = resposta_id
                print(f"✅ Resposta salva: pergunta {pergunta_ordem} → id {resposta_id} (mantido)")
            
            # 4. ATUALIZAR STATUS DO CHECKLIST
            novo_status = 'Concluído' if concluir else 'Em andamento'
            query_status = text("""
                UPDATE checklists SET status = :status, updated_at = NOW()
                WHERE id = :checklist_id
            """)
            conn.execute(query_status, {
                'status': novo_status,
                'checklist_id': checklist_id
            })
            conn.commit()
            
            print(f"📤 respostas_ids sendo retornados: {respostas_ids}")
            
            return jsonify({
                'success': True,
                'id': checklist_id,
                'respostas_ids': respostas_ids,
                'message': 'Respostas salvas com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar checklist: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/checklist/progresso')
def api_checklist_progresso():
    """Retorna o progresso dos checklists para um processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    # Configuração dos checklists
    CONFIG = {
        'governanca': {'total': 13},
        'riscos': {'total': 12},
        'controles': {'total': 12}
    }
    
    resultado = {}
    
    try:
        with engine.connect() as conn:
            for tipo, config in CONFIG.items():
                total = config['total']
                
                # Buscar o checklist
                query_checklist = text("""
                    SELECT id, status
                    FROM checklists
                    WHERE processo_id = :processo_id AND tipo = :tipo
                """)
                
                checklist = conn.execute(query_checklist, {
                    'processo_id': processo_id,
                    'tipo': tipo
                }).fetchone()
                
                if not checklist:
                    resultado[tipo] = {
                        'total': total,
                        'respondidas': 0,
                        'status': 'Não iniciado'
                    }
                else:
                    checklist_id = checklist[0]
                    status = checklist[1] or 'Em andamento'
                    
                    # ⭐⭐⭐ CONTAR APENAS PERGUNTAS PRINCIPAIS ⭐⭐⭐
                    # Para governança: contar perguntas 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
                    # Ignorar 1.1 e 1.2
                    
                    if tipo == 'governanca':
                        # ⭐ Lista das perguntas principais (excluindo subitens)
                        query_respondidas = text("""
                            SELECT COUNT(*) 
                            FROM checklist_respostas 
                            WHERE checklist_id = :checklist_id 
                            AND resposta IS NOT NULL 
                            AND resposta != ''
                            AND pergunta_ordem IN ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13')
                        """)
                    else:
                        # Para riscos e controles, todas as perguntas são principais
                        query_respondidas = text("""
                            SELECT COUNT(*) 
                            FROM checklist_respostas 
                            WHERE checklist_id = :checklist_id 
                            AND resposta IS NOT NULL 
                            AND resposta != ''
                        """)
                    
                    result = conn.execute(query_respondidas, {
                        'checklist_id': checklist_id
                    })
                    
                    respondidas = result.fetchone()[0]
                    
                    resultado[tipo] = {
                        'total': total,
                        'respondidas': respondidas,
                        'status': status
                    }
            
            return jsonify({
                'success': True,
                'progresso': resultado
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar progresso: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/checklist/evidencia/<int:evidencia_id>/download', methods=['GET'])
def baixar_evidencia_checklist_route(evidencia_id):
    """Baixa uma evidência do checklist do Supabase Storage"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    from flask import send_file
    import io
    
    try:
        # 1. BUSCAR EVIDÊNCIA NO BANCO
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_arquivo, caminho_arquivo, tamanho_bytes, content_type
                FROM checklist_evidencias
                WHERE id = :evidencia_id
            """)
            
            result = conn.execute(query, {'evidencia_id': evidencia_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Evidência não encontrada'}), 404
            
            evidencia_id = result[0]
            nome_arquivo = result[1]
            caminho_arquivo = result[2]
            tamanho_bytes = result[3]
            content_type = result[4] or 'application/pdf'
        
        print(f"📥 Baixando evidência: id={evidencia_id}, nome={nome_arquivo}")
        print(f"📥 Caminho salvo no banco: {caminho_arquivo}")
        
        # 2. VERIFICAR SE É URL OU CAMINHO
        if caminho_arquivo.startswith('https://'):
            # Já é uma URL - redirecionar
            from flask import redirect
            print(f"📥 É uma URL, redirecionando...")
            return redirect(caminho_arquivo)
        
        # 3. ⭐ USAR A FUNÇÃO GENÉRICA PARA BAIXAR
        print(f"📥 É um caminho, baixando do storage...")
        file_bytes = baixar_arquivo_storage(caminho_arquivo, "matriz_eficacia")
        
        if file_bytes:
            print(f"✅ Arquivo baixado! Tamanho: {len(file_bytes)} bytes")
            return send_file(
                io.BytesIO(file_bytes),
                download_name=nome_arquivo,
                mimetype=content_type,
                as_attachment=True
            )
        
        # 4. ⭐ TENTAR GERAR URL ASSINADA (fallback)
        print(f"📥 Tentando gerar URL assinada...")
        signed_url = obter_url_assinada(caminho_arquivo, "matriz_eficacia", 3600)
        if signed_url:
            from flask import redirect
            print(f"✅ URL assinada gerada, redirecionando...")
            return redirect(signed_url)
        
        return jsonify({'success': False, 'error': 'Erro ao baixar evidência'}), 500
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/evidencia/<int:evidencia_id>', methods=['DELETE'])
def remover_evidencia_checklist_route(evidencia_id):
    """Remove uma evidência do checklist (banco + storage)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        # 1. BUSCAR EVIDÊNCIA NO BANCO
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_arquivo, caminho_arquivo
                FROM checklist_evidencias
                WHERE id = :evidencia_id
            """)
            
            result = conn.execute(query, {'evidencia_id': evidencia_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Evidência não encontrada'}), 404
            
            evidencia_id = result[0]
            nome_arquivo = result[1]
            caminho_arquivo = result[2]
            
            print(f"🗑️ Removendo evidência: id={evidencia_id}, nome={nome_arquivo}")
            print(f"🗑️ Caminho salvo no banco: {caminho_arquivo}")
            
            # 2. ⭐ REMOVER DO STORAGE USANDO A FUNÇÃO GENÉRICA
            if caminho_arquivo:
                try:
                    # Verificar se é URL ou caminho direto
                    if caminho_arquivo.startswith('https://'):
                        # É uma URL - extrair caminho e bucket
                        from utils import extrair_caminho_da_url
                        caminho, bucket = extrair_caminho_da_url(caminho_arquivo)
                        if caminho and bucket:
                            print(f"📎 Extraído - caminho: {caminho}, bucket: {bucket}")
                            excluir_arquivo_storage(caminho, bucket)
                        else:
                            print(f"⚠️ Não foi possível extrair caminho da URL: {caminho_arquivo}")
                    else:
                        # É um caminho direto - usar diretamente
                        print(f"📎 Caminho direto: {caminho_arquivo}")
                        excluir_arquivo_storage(caminho_arquivo, "matriz_eficacia")
                except Exception as e:
                    print(f"⚠️ Erro ao remover do storage: {e}")
                    # Continua mesmo se falhar para remover do banco
            
            # 3. REMOVER DO BANCO
            query_delete = text("""
                DELETE FROM checklist_evidencias
                WHERE id = :evidencia_id
            """)
            
            conn.execute(query_delete, {'evidencia_id': evidencia_id})
            conn.commit()
            
            print(f"✅ Evidência removida com sucesso! ID: {evidencia_id}")
            
            return jsonify({
                'success': True,
                'message': 'Evidência removida com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/evidencia/salvar', methods=['POST'])
def salvar_evidencia_checklist_route():
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import base64
    import uuid
    from datetime import datetime
    
    try:
        data = request.json
        resposta_id = data.get('resposta_id')
        evidencia_base64 = data.get('evidencia_base64')
        evidencia_nome = data.get('evidencia_nome')
        
        if not resposta_id or not evidencia_base64 or not evidencia_nome:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        if not evidencia_nome.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Apenas arquivos PDF são permitidos'}), 400
        
        with engine.connect() as conn:
            # Buscar dados da resposta
            query_resposta = text("""
                SELECT id, checklist_id, pergunta_ordem
                FROM checklist_respostas
                WHERE id = :resposta_id
            """)
            resposta = conn.execute(query_resposta, {'resposta_id': resposta_id}).fetchone()
            
            if not resposta:
                return jsonify({'success': False, 'error': 'Resposta não encontrada'}), 404
            
            checklist_id = resposta[1]
            pergunta_ordem = resposta[2]
            
            # ⭐ DECODIFICAR BASE64
            if ',' in evidencia_base64:
                evidencia_base64 = evidencia_base64.split(',')[1]
            file_bytes = base64.b64decode(evidencia_base64)
            
            # ⭐ GERAR NOME ÚNICO
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            
            # ⭐ LIMPAR NOME
            nome_limpo = ''.join(c for c in evidencia_nome if c.isalnum() or c in ' ._-')
            nome_limpo = nome_limpo.replace(' ', '_')
            
            # ⭐ CONSTRUIR CAMINHO
            # Estrutura: checklists/{checklist_id}/pergunta_{ordem}/{timestamp}_{uuid}_{nome}.pdf
            caminho = f"checklists/checklist_id_{checklist_id}/pergunta_{pergunta_ordem}/{timestamp}_{unique_id}_{nome_limpo}"
            
            # ⭐ CHAMAR FUNÇÃO GENÉRICA
            url_retornada = upload_arquivo_storage(
                arquivo=file_bytes,
                caminho_destino=caminho,
                bucket_name="matriz_eficacia",
                content_type="application/pdf"
            )
            
            # ⭐ IMPORTANTE: Para checklist, precisamos do CAMINHO, não da URL
            # A função retorna a URL assinada, mas o banco espera o caminho
            # Então usamos o caminho que construímos
            if url_retornada:
                # Upload foi bem-sucedido, salvar o caminho no banco
                caminho_para_salvar = caminho
                print(f"📎 Evidência salva: {caminho_para_salvar}")
            else:
                return jsonify({'success': False, 'error': 'Erro ao fazer upload da evidência'}), 500
            
            # Calcular tamanho
            tamanho_aproximado = 0
            if evidencia_base64:
                base64_data = evidencia_base64
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                tamanho_aproximado = int(len(base64_data) * 0.75)
            
            # Salvar no banco
            query_insert = text("""
                INSERT INTO checklist_evidencias (resposta_id, nome_arquivo, caminho_arquivo, tamanho_bytes, content_type)
                VALUES (:resposta_id, :nome_arquivo, :caminho_arquivo, :tamanho_bytes, :content_type)
                RETURNING id
            """)
            
            result = conn.execute(query_insert, {
                'resposta_id': resposta_id,
                'nome_arquivo': evidencia_nome,
                'caminho_arquivo': caminho_para_salvar,
                'tamanho_bytes': tamanho_aproximado,
                'content_type': 'application/pdf'
            })
            conn.commit()
            
            evidencia_id = result.fetchone()[0]
            
            return jsonify({
                'success': True,
                'evidencia': {
                    'id': evidencia_id,
                    'nome': evidencia_nome,
                    'caminho': caminho_para_salvar,
                    'tamanho': tamanho_aproximado
                }
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/checklist/evidencias/<int:resposta_id>', methods=['GET'])
def listar_evidencias_checklist(resposta_id):
    """Lista as evidências de uma resposta específica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ VERIFICAR SE A RESPOSTA EXISTE
            query_resposta = text("""
                SELECT id FROM checklist_respostas WHERE id = :resposta_id
            """)
            resposta = conn.execute(query_resposta, {'resposta_id': resposta_id}).fetchone()
            
            if not resposta:
                return jsonify({
                    'success': True,
                    'evidencias': [],
                    'message': f'Resposta {resposta_id} não encontrada'
                })
            
            # ⭐ BUSCAR EVIDÊNCIAS
            query_evidencias = text("""
                SELECT id, nome_arquivo, caminho_arquivo, tamanho_bytes, uploaded_at
                FROM checklist_evidencias
                WHERE resposta_id = :resposta_id
                ORDER BY uploaded_at DESC
            """)
            
            result = conn.execute(query_evidencias, {'resposta_id': resposta_id}).fetchall()
            
            evidencias = []
            for row in result:
                evidencias.append({
                    'id': row[0],
                    'nome': row[1],
                    'caminho': row[2],
                    'tamanho': row[3],
                    'data': row[4].isoformat() if row[4] else None
                })
            
            return jsonify({
                'success': True,
                'evidencias': evidencias
            })
            
    except Exception as e:
        print(f"❌ Erro ao listar evidências: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# GERAÇÃO DE RELATÓRIOS
# ============================================================

@app.route('/api/relatorios/areas')
def api_relatorios_areas():
    """Retorna todas as áreas ativas para os relatórios"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # ⭐ ADICIONAR loc_unidade NO SELECT
            query = text("""
                SELECT id_area, nome_area, gestor, loc_unidade
                FROM informacoes_area
                WHERE status = 'Ativo'
                ORDER BY nome_area
            """)

            result = conn.execute(query).fetchall()

            areas = []

            for row in result:
                id_area = row[0]
                nome_area = row[1]
                gestor = row[2] or 'Não informado'
                unidade = row[3] if len(row) > 3 and row[3] else ''  # ⭐ PEGAR UNIDADE
                
                # ⭐ FORMATAR NOME COM UNIDADE
                if unidade and unidade.strip():
                    nome_exibicao = f"{nome_area} - {unidade}"
                else:
                    nome_exibicao = nome_area

                areas.append({
                    'id': id_area,
                    'nome': nome_exibicao,  # ← NOME FORMATADO
                    'nome_original': nome_area,  # ← OPCIONAL (para referência)
                    'gestor': gestor,
                    'unidade': unidade  # ← UNIDADE SEPARADA (opcional)
                })

            return jsonify({'success': True, 'areas': areas})

    except Exception as e:
        print(f"❌ Erro ao buscar áreas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorios/auditorias-por-area')
def api_relatorios_auditorias_por_area():
    """Retorna as auditorias de uma área específica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    area_id = request.args.get('area_id')
    if not area_id:
        return jsonify({'success': False, 'error': 'area_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, codigo_auditoria, titulo, ano, trimestre, unidade
                FROM auditorias
                WHERE id_area = :area_id
                ORDER BY ano DESC, trimestre DESC
            """)

            result = conn.execute(query, {'area_id': area_id}).fetchall()

            auditorias = []
            for row in result:
                auditorias.append({
                    'id': row[0],
                    'codigo_auditoria': row[1],
                    'titulo': row[2],
                    'ano': row[3],
                    'trimestre': row[4],
                    'unidade': row[5] or ''
                })

            return jsonify({'success': True, 'auditorias': auditorias})
    
    except Exception as e:
        print(f"❌ Erro ao buscar auditorias: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorios/gerar-panorama', methods=['POST'])

def api_gerar_relatorio_panorama():
    """Gera relatório de validação - Matriz Panorama"""
    from logic import gerar_validacao_relatorio_panorama
    from flask import send_file, request, jsonify
    import io
    from database import engine
    from sqlalchemy import text
    
    try:
        data = request.get_json()
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        processo_id = data.get('processo_id')  # Pode ser None
        orientacao = data.get('orientacao', 'RETRATO')
        
        if not area_id or not auditoria_id:
            return jsonify({'error': 'Área e auditoria são obrigatórios'}), 400
        
        # Buscar informações da área
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor, cargo 
                FROM informacoes_area 
                WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {"area_id": area_id}).fetchone()
            
            if not area_info:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0]
            gestor = area_info[1] or 'Não informado'
            cargo = area_info[2] or 'Não informado'
        
        # Gerar o relatório
        pdf_bytes = gerar_validacao_relatorio_panorama(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            orientacao=orientacao,
            auditoria_id=auditoria_id,
            processo_id=processo_id
        )
        
        # Nome do arquivo
        if processo_id:
            nome_arquivo = f"relatorio_panorama_processo_{processo_id}.pdf"
        else:
            nome_arquivo = f"relatorio_panorama_auditoria_{auditoria_id}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/relatorios/gerar-detalhamento', methods=['POST'])

def api_gerar_relatorio_detalhamento():
    """Gera relatório de validação - Matriz Detalhamento"""
    from logic import gerar_validacao_relatorio_detalhamento
    from flask import send_file, request, jsonify
    import io
    from database import engine
    from sqlalchemy import text
    
    try:
        data = request.get_json()
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        processo_id = data.get('processo_id')  # Pode ser None
        orientacao = data.get('orientacao', 'RETRATO')
        
        if not area_id or not auditoria_id:
            return jsonify({'error': 'Área e auditoria são obrigatórios'}), 400
        
        # Buscar informações da área
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor, cargo 
                FROM informacoes_area 
                WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {"area_id": area_id}).fetchone()
            
            if not area_info:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0]
            gestor = area_info[1] or 'Não informado'
            cargo = area_info[2] or 'Não informado'
        
        # Gerar o relatório
        pdf_bytes = gerar_validacao_relatorio_detalhamento(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            orientacao=orientacao,
            auditoria_id=auditoria_id,
            processo_id=processo_id
        )
        
        # Nome do arquivo
        if processo_id:
            nome_arquivo = f"relatorio_detalhamento_processo_{processo_id}.pdf"
        else:
            nome_arquivo = f"relatorio_detalhamento_auditoria_{auditoria_id}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/relatorios/gerar-parecer', methods=['POST'])
def gerar_parecer():

    from flask import Flask, jsonify, request, session, make_response
    """Endpoint para gerar o parecer da auditoria"""
    try:
        # Verificar autenticação
        if 'usuario_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        data = request.get_json()
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        processo_id = data.get('processo_id')
        orientacao = data.get('orientacao', 'RETRATO')
        incluir_abr = data.get('incluir_abr', False)
        incluir_checklists = data.get('incluir_checklists', True)
        
        # Verificar permissão para ABR
        perfil = session.get('usuario_perfil', 'usuario')
        if incluir_abr and perfil not in ['administrador', 'admin']:
            return jsonify({'error': 'Apenas administradores podem incluir a seção ABR'}), 403
        
        # Buscar dados necessários
        with engine.connect() as conn:
            # Buscar informações da área
            query_area = text("SELECT id_area, nome_area FROM informacoes_area WHERE id_area = :area_id")
            area = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            # Buscar gestor
            query_gestor = text("""
                SELECT gestor, cargo
                FROM informacoes_area 
                WHERE id_area = :area_id
            """)
            gestor_info = conn.execute(query_gestor, {'area_id': area_id}).fetchone()
            
            gestor = gestor_info[0] if gestor_info else 'Não informado'
            cargo = gestor_info[1] if gestor_info and len(gestor_info) > 1 else 'Não informado'
            
            usuario_nome = session.get('usuario_nome', 'Auditor')
        
        # ⭐ PASSAR O PARÂMETRO incluir_abr PARA A FUNÇÃO
        pdf_bytes = gerar_relatorio_parecer_auditoria(
            area_id=area_id,
            area_nome=area[1],
            gestor=gestor,
            cargo=cargo,
            auditoria_id=auditoria_id,
            processo_id=processo_id,
            usuario_nome=usuario_nome,
            orientacao=orientacao,
            incluir_abr=incluir_abr,
            incluir_checklists=incluir_checklists
        )
        
        # Criar resposta com o PDF
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="parecer_auditoria_processo_{processo_id}.pdf"'
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/relatorios/download')
def api_relatorios_download():
    """Faz o download do relatório PDF gerado"""

    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    
    pdf_bytes = session.get('relatorio_pdf')
    nome_arquivo = session.get('relatorio_nome', 'relatorio.pdf')

    if not pdf_bytes:
        return jsonify({'error': 'Nenhum relatório gerado'}), 404
    
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=nome_arquivo
    )

@app.route('/api/relatorios/processos-por-auditoria')
def api_relatorios_processos_por_auditoria():
    """Retorna os processos de uma auditoria específica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, codigo_processo, nome_processo
                FROM processos
                WHERE auditoria_id = :auditoria_id AND status = 'Ativo'
                ORDER BY string_to_array(codigo_processo, '.')::int[]
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            processos = [{'id': row[0], 'codigo_processo': row[1], 'nome_processo': row[2]} for row in result]
            
            return jsonify({'success': True, 'processos': processos})
            
    except Exception as e:
        print(f"❌ Erro ao buscar processos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ROTA DE TESTE PARA AUDITORIA (remover depois)
# ============================================================

@app.route('/debug-auditoria')
def debug_auditoria():
    """🔍 Rota de teste para verificar se a auditoria está configurada"""
    if not session.get('autenticado'):
        return jsonify({'erro': 'Faça login primeiro'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Tenta ler as variáveis que configuramos
            resultado = conn.execute(text("""
                SELECT 
                    current_setting('app.usuario_id', true) as usuario_id,
                    current_setting('app.usuario_nome', true) as usuario_nome,
                    current_setting('app.ip_origem', true) as ip_origem
            """))
            row = resultado.fetchone()
            
            return jsonify({
                'sucesso': True,
                'usuario_id': row[0],
                'usuario_nome': row[1],
                'ip_origem': row[2],
                'explicacao': '✅ Se você vê seus dados, a auditoria está pronta!'
            })
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'explicacao': '⚠️ As variáveis ainda não foram configuradas para esta conexão'
        }), 500
    

@app.route('/debug-sessao')
def debug_sessao():
    """🔍 Verifica o que tem na sessão do Flask"""
    if not session.get('autenticado'):
        return jsonify({'erro': 'Não logado'}), 401
    
    return jsonify({
        'autenticado': session.get('autenticado'),
        'usuario_id': session.get('usuario_id'),
        'usuario_nome': session.get('usuario_nome'),
        'usuario_logado': session.get('usuario_logado'),
        'usuario_perfil': session.get('usuario_perfil'),
        'login_timestamp': session.get('login_timestamp')
    })

# ============================================================
# LOG DE ALTERACOES
# ============================================================

@app.route('/api/logs')
def api_logs():
    """
    API que retorna os logs da tabela log_auditoria com paginação
    Apenas administradores podem acessar
    """
    
    # 1. Verificar autenticação
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # 2. Verificar se é administrador
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    # 3. Importar dependências
    from database import engine
    from sqlalchemy import text
    
    # 4. Pegar parâmetros da URL
    pagina = request.args.get('pagina', 1, type=int)
    limite = request.args.get('limite', 20, type=int)
    tabela = request.args.get('tabela', '')
    operacao = request.args.get('operacao', '')
    usuario = request.args.get('usuario', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    
    # Calcular offset (deslocamento) para paginação
    # Exemplo: página 1, limite 20 → offset 0 (registros 1-20)
    #          página 2, limite 20 → offset 20 (registros 21-40)
    offset = (pagina - 1) * limite
    
    # 5. Construir a query BASE (para contar total)
    base_query = """
        FROM log_auditoria
        WHERE 1=1
    """
    
    # 6. Construir a query de SELECT (para buscar os dados)
    select_query = """
        SELECT 
            id,
            tabela_afetada,
            registro_id,
            operacao,
            usuario_nome,
            ip_origem,
            data_hora,
            dados_anteriores,
            dados_novos
    """
    
    # 7. Parâmetros compartilhados entre as queries
    params = {}
    
    # 8. Adicionar filtros (mesmo para COUNT e SELECT)
    if tabela:
        base_query += " AND tabela_afetada = :tabela"
        select_query += base_query  # Adiciona o WHERE à SELECT também
        params['tabela'] = tabela
    else:
        select_query += base_query
    
    # Recriar base_query para o COUNT (porque já foi usada)
    count_query = "SELECT COUNT(*) " + base_query
    
    # Ajustar select_query para incluir o ORDER BY e LIMIT
    select_query += " ORDER BY id DESC LIMIT :limite OFFSET :offset"
    params['limite'] = limite
    params['offset'] = offset
    
    # Adicionar filtros individualmente (para não duplicar)
    if operacao:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND operacao = :operacao")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND operacao = :operacao")
        params['operacao'] = operacao
    
    if usuario:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND usuario_nome ILIKE :usuario")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND usuario_nome ILIKE :usuario")
        params['usuario'] = f'%{usuario}%'
    
    if data_inicio:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora >= :data_inicio")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora >= :data_inicio")
        params['data_inicio'] = data_inicio
    
    if data_fim:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora <= :data_fim")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora <= :data_fim")
        params['data_fim'] = data_fim + ' 23:59:59'  # Inclui todo o dia
    
    try:
        with engine.connect() as conn:
            # 9. Primeiro, buscar o TOTAL de registros (para paginação)
            total_result = conn.execute(text(count_query), params)
            total_registros = total_result.fetchone()[0]
            
            # 10. Calcular total de páginas
            total_paginas = (total_registros + limite - 1) // limite if total_registros > 0 else 1
            
            # 11. Buscar os registros da página atual
            result = conn.execute(text(select_query), params)
            
            # 12. Converter os resultados para lista de dicionários
            import re

            logs = []
            for row in result:
                logs.append({
                    'id': row[0],
                    'tabela_afetada': row[1],
                    'registro_id': row[2],
                    'operacao': row[3],
                    'usuario_nome': row[4] or 'Sistema',
                    'ip_origem': row[5] or '-',
                    'data_hora': row[6].strftime('%d/%m/%Y %H:%M:%S') if row[6] else '',
                    'dados_anteriores': row[7],
                    'dados_novos': row[8]
                })
            
            return jsonify({
                'success': True,
                'logs': logs,
                'total_registros': total_registros,
                'total_paginas': total_paginas,
                'pagina_atual': pagina,
                'limite': limite
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tabelas')
def api_tabelas():
    """
    Retorna a lista de todas as tabelas do banco (exceto log_auditoria)
    Apenas administradores podem acessar
    """
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar todas as tabelas do schema public
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    AND table_name != 'log_auditoria'
                ORDER BY table_name
            """)
            result = conn.execute(query)
            tabelas = [row[0] for row in result]
            
            return jsonify({'success': True, 'tabelas': tabelas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/usuarios')
def api_usuarios():
    """
    Retorna a lista de usuários para o filtro de logs
    Apenas administradores podem acessar
    """
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome, login
                FROM usuarios
                                WHERE ativo = true
                ORDER BY nome
            """)
            result = conn.execute(query)
            usuarios = [{'id': row[0], 'nome': row[1], 'login': row[2]} for row in result]
            
            return jsonify({'success': True, 'usuarios': usuarios})
    except Exception as e:
        print(f"❌ Erro ao buscar usuários: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - ANÁLISES CRÍTICAS
# ============================================================

@app.route('/api/etapa/<int:etapa_id>/analises', methods=['GET'])
def api_etapa_analises(etapa_id):
    """Retorna todas as análises críticas de uma etapa com evidências"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa_id, tipo, categoria,
                       analise_critica, sugestao_melhoria,
                       necessidade_implantacao, ganho_previsto,
                       evidencia_url, evidencia_nome,  -- ⭐ NOVO
                       created_at, updated_at
                FROM analises_criticas
                WHERE etapa_id = :etapa_id
                ORDER BY tipo, categoria
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchall()
            
            analises = []
            for row in result:
                analise = {
                    'id': row[0],
                    'etapa_id': row[1],
                    'tipo': row[2],
                    'categoria': row[3],
                    'analise_critica': row[4] or '',
                    'sugestao_melhoria': row[5] or '',
                    'necessidade_implantacao': row[6] or '',
                    'ganho_previsto': row[7] or '',
                    'evidencia_url': row[8],      # ⭐ NOVO
                    'evidencia_nome': row[9],     # ⭐ NOVO
                    'created_at': row[10].isoformat() if row[10] else '',
                    'updated_at': row[11].strftime('%Y-%m-%d %H:%M') if row[11] else ''
                }
                analises.append(analise)
            
            return jsonify({'success': True, 'analises': analises})
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise-auditor/<int:analise_id>', methods=['DELETE'])
def api_analise_auditor_excluir(analise_id):
    """Exclui uma análise do auditor"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ✅ CORRETO: usar a tabela analises_criticas
            query = text("""
                DELETE FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': analise_id})
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            return jsonify({'success': True, 'message': 'Análise excluída com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir análise do auditor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    
# @app.route('/api/analise-auditor/<int:analise_id>/confirmar-implantacao', methods=['PUT'])
# def api_analise_auditor_confirmar_implantacao(analise_id):
#     """Confirma se a melhoria foi efetivamente implantada e CRIA FOLLOW-UPS automáticos"""
#     if not session.get('autenticado'):
#         return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
#     data = request.json
#     plano_de_acao_implantado = data.get('plano_de_acao_implantado')
#     data_execucao_plano_acao = data.get('data_execucao_plano_acao')

    
#     if plano_de_acao_implantado and not data_execucao_plano_acao:
#         return jsonify({'success': False, 'error': 'Data de implantação é obrigatória'}), 400
    
#     from database import engine
#     from sqlalchemy import text
#     from datetime import datetime, timedelta
    
#     try:
#         with engine.connect() as conn:
#             # Buscar dados atuais da análise (usando 'tipo', não 'tipo')
#             result = conn.execute(text("""
#                 SELECT sugestao_sera_implantada, processo_id
#                 FROM analises_criticas 
#                 WHERE id = :id AND tipo = 'auditor'
#             """), {'id': analise_id})
#             analise = result.fetchone()
            
#             if not analise:
#                 return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
#             # Atualizar a análise
#             conn.execute(text("""
#                 UPDATE analises_criticas 
#                 SET plano_de_acao_implantado = :plano_de_acao_implantado,
#                     data_execucao_plano_acao = :data_execucao_plano_acao,
#                     updated_at = NOW()
#                 WHERE id = :id
#             """), {
#                 'id': analise_id,
#                 'plano_de_acao_implantado': plano_de_acao_implantado,
#                 'data_execucao_plano_acao': data_execucao_plano_acao
#             })
            
#             # Se foi implantada, criar follow-ups automáticos
#             if plano_de_acao_implantado:
#                 data_base = datetime.strptime(data_execucao_plano_acao, '%Y-%m-%d')
                
#                 follow_ups = [
#                     {'etapa': 'FOLLOW_UP_30', 'dias': 30},
#                     {'etapa': 'FOLLOW_UP_60', 'dias': 60},
#                     {'etapa': 'FOLLOW_UP_90', 'dias': 90}
#                 ]
                
#                 for fu in follow_ups:
#                     data_prevista = data_base + timedelta(days=fu['dias'])
                    
#                     # Verificar se já existe follow-up
#                     check = conn.execute(text("""
#                         SELECT id FROM analises_follow_up 
#                         WHERE analise_id = :analise_id AND etapa = :etapa
#                     """), {'analise_id': analise_id, 'etapa': fu['etapa']}).fetchone()
                    
#                     if not check:
#                         conn.execute(text("""
#                             INSERT INTO analises_follow_up (
#                                 analise_id, etapa, data_prevista, status, created_by, created_at
#                             ) VALUES (
#                                 :analise_id, :etapa, :data_prevista, 'Pendente', :created_by, NOW()
#                             )
#                         """), {
#                             'analise_id': analise_id,
#                             'etapa': fu['etapa'],
#                             'data_prevista': data_prevista.date(),
#                             'created_by': session.get('usuario_nome', 'Sistema')
#                         })
#                         print(f"✅ Follow-up {fu['etapa']} criado para {data_prevista.date()}")
                
#                 # Registrar no histórico de andamento (se a tabela existir)
#                 try:
#                     conn.execute(text("""
#                         INSERT INTO analises_historico_andamento (
#                             analise_id, status, comentario, created_by, created_at
#                         ) VALUES (
#                             :analise_id, 'Concluido', :comentario, :created_by, NOW()
#                         )
#                     """), {
#                         'analise_id': analise_id,
#                         'comentario': f'✅ Melhoria implantada em {data_execucao_plano_acao}. Follow-ups criados para 30, 60 e 90 dias.',
#                         'created_by': session.get('usuario_nome', 'Sistema')
#                     })
#                 except Exception as e:
#                     print(f"⚠️ Histórico: {e}")
            
#             conn.commit()
            
#             return jsonify({'success': True, 'message': 'Implantação confirmada e follow-ups criados'})
            
#     except Exception as e:
#         print(f"❌ Erro ao confirmar implantação: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-auditor/<int:analise_id>/evidencias')
def listar_evidencias_analise(analise_id):
    """Lista as evidências de uma análise (para debug)"""
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        from database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            query = text("""
                SELECT id, evidencia_url, evidencia_nome, created_at
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': analise_id})
            row = result.fetchone()
            
            if not row:
                return jsonify({'error': 'Análise não encontrada'}), 404
            
            return jsonify({
                'success': True,
                'analise_id': row[0],
                'evidencia_url': row[1],
                'evidencia_nome': row[2],
                'created_at': row[3]
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/melhorias/ativas', methods=['GET'])
def api_melhorias_ativas():
    """Lista melhorias que estão em acompanhamento (mesmo após auditoria finalizada)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    apenas_pendentes = request.args.get('apenas_pendentes', 'true').lower() == 'true'
    
    from database import engine
    from sqlalchemy import text
    from datetime import date
    
    try:
        with engine.connect() as conn:
            hoje = date.today()
            
            # Query corrigida: usa 'tipo' em vez de 'tipo'
            query = """
                SELECT 
                    a.id,
                    a.tipo,
                    a.sugestao_melhoria,
                    a.responsavel_implantacao,
                    a.data_conclusao_prevista,
                    a.data_execucao_plano_acao,
                    a.plano_de_acao_implantado,
                    p.codigo_processo,
                    p.nome_processo
                FROM analises_criticas a
                JOIN processos p ON a.processo_id = p.id
                WHERE a.sugestao_sera_implantada = true
                  AND (a.plano_de_acao_implantado = false OR a.plano_de_acao_implantado IS NULL)
            """
            
            params = {}
            
            if auditoria_id:
                query += " AND p.auditoria_id = :auditoria_id"
                params['auditoria_id'] = auditoria_id
            
            if apenas_pendentes:
                query += " AND (a.data_conclusao_prevista < :hoje OR a.data_conclusao_prevista IS NULL)"
                params['hoje'] = hoje
            
            query += " ORDER BY a.data_conclusao_prevista ASC NULLS LAST"
            
            result = conn.execute(text(query), params).fetchall()
            
            melhorias = []
            for row in result:
                prazo_vencido = False
                if row[4] and not row[6]:  # data_conclusao_prevista existe e não está implantada
                    prazo_vencido = row[4] < hoje
                
                melhorias.append({
                    'id': row[0],
                    'tipo': row[1],
                    'sugestao_melhoria': row[2] or '',
                    'responsavel': row[3] or '',
                    'data_conclusao_prevista': row[4].isoformat() if row[4] else None,
                    'data_implantacao': row[5].isoformat() if row[5] else None,
                    'plano_de_acao_implantado': row[6] or False,
                    'prazo_vencido': prazo_vencido,
                    'processo': f"{row[7]} - {row[8]}" if row[7] else row[8] or ''
                })
            
            return jsonify({'success': True, 'melhorias': melhorias})
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise/salvar', methods=['POST'])
def api_analise_salvar():
    """Salva ou atualiza uma análise crítica com evidência"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('id')
    etapa_id = data.get('etapa_id')
    tipo = data.get('tipo', 'auditado')
    categoria = data.get('categoria', 'governanca')
    analise_critica = data.get('analise_critica', '')
    sugestao_melhoria = data.get('sugestao_melhoria', '')
    necessidade_implantacao = data.get('necessidade_implantacao', '')
    ganho_previsto = data.get('ganho_previsto', '')
    
    # Campos de evidência
    evidencia_base64 = data.get('evidencia_base64')
    evidencia_nome = data.get('evidencia_nome')
    remover_evidencia = data.get('remover_evidencia', False)
    
    if not etapa_id:
        return jsonify({'success': False, 'error': 'etapa_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    import base64
    import uuid
    
    try:
        with engine.connect() as conn:
            # Buscar o processo_id da etapa
            query_processo = text("""
                SELECT processo_id FROM etapas_processo WHERE id = :etapa_id
            """)
            result_processo = conn.execute(query_processo, {'etapa_id': etapa_id}).fetchone()
            processo_id = result_processo[0] if result_processo else None
            
            print(f"🔍 Etapa {etapa_id} pertence ao processo {processo_id}")
            
            evidencia_url_final = None
            evidencia_nome_final = None
            
            if remover_evidencia:
                print(f"🗑️ Removendo evidência da análise {analise_id or 'nova'}")
                
                if analise_id:
                    query_evidencia = text("""
                        SELECT evidencia_url FROM analises_criticas WHERE id = :id
                    """)
                    result_evidencia = conn.execute(query_evidencia, {'id': analise_id}).fetchone()
                    if result_evidencia and result_evidencia[0]:
                        url_antiga = result_evidencia[0]
                        print(f"📎 Removendo evidência antiga: {url_antiga}")
                        
                        # Extrair caminho e bucket da URL
                        caminho, bucket = extrair_caminho_da_url(url_antiga)
                        if caminho and bucket:
                            excluir_arquivo_storage(caminho, bucket)
                
                evidencia_url_final = None
                evidencia_nome_final = None
                
            elif evidencia_base64 and evidencia_nome:
                try:
                    # Determinar o ID para o caminho
                    if analise_id:
                        query_check = text("""
                            SELECT id FROM analises_criticas WHERE id = :id
                        """)
                        result_check = conn.execute(query_check, {'id': analise_id}).fetchone()
                        if result_check:
                            analise_id_para_path = analise_id
                        else:
                            analise_id_para_path = int(datetime.now().timestamp())
                    else:
                        analise_id_para_path = int(datetime.now().timestamp())
                    
                    # Decodificar base64
                    if ',' in evidencia_base64:
                        evidencia_base64 = evidencia_base64.split(',')[1]
                    file_bytes = base64.b64decode(evidencia_base64)

                    # Definir bucket baseado no tipo
                    bucket = "evidencia_analises_auditor" if tipo == 'auditor' else "evidencia_analises_auditado"

                    # Gerar nome único
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_id = str(uuid.uuid4())[:8]

                    # Limpar nome
                    nome_limpo = ''.join(c for c in evidencia_nome if c.isalnum() or c in ' ._-')
                    nome_limpo = nome_limpo.replace(' ', '_')

                    # Definir caminho baseado no tipo
                    if tipo == 'auditado':
                        # Auditado: inclui a etapa no caminho
                        caminho = f"analises_{tipo}/analise_id_{analise_id_para_path}/etapa_{etapa_id}/{timestamp}_{unique_id}_{nome_limpo}.pdf"
                    else:
                        # Auditor: sem etapa no caminho
                        caminho = f"analises_{tipo}/analise_id_{analise_id_para_path}/{timestamp}_{unique_id}_{nome_limpo}.pdf"

                    # Chamar função genérica
                    url_assinada = upload_arquivo_storage(
                        arquivo=file_bytes,
                        caminho_destino=caminho,
                        bucket_name=bucket,
                        content_type="application/pdf"
                    )
                    
                    if url_assinada:
                        evidencia_url_final = caminho
                        evidencia_nome_final = evidencia_nome
                        print(f"📎 Evidência salva no Storage: {evidencia_url_final}")
                    else:
                        print("⚠️ Falha ao salvar evidência no Storage")
                        
                except Exception as e:
                    print(f"⚠️ Erro ao salvar evidência no Storage: {e}")
            
            # Buscar evidência existente se não houver nova e não for remoção
            if not evidencia_base64 and not remover_evidencia and analise_id:
                query_existente = text("""
                    SELECT evidencia_url, evidencia_nome 
                    FROM analises_criticas 
                    WHERE id = :id
                """)
                result_existente = conn.execute(query_existente, {'id': analise_id}).fetchone()
                if result_existente and result_existente[0]:
                    evidencia_url_final = result_existente[0]
                    evidencia_nome_final = result_existente[1]
            
            if analise_id:
                # Atualizar
                query = text("""
                    UPDATE analises_criticas
                    SET tipo = :tipo,
                        categoria = :categoria,
                        analise_critica = :analise_critica,
                        sugestao_melhoria = :sugestao_melhoria,
                        necessidade_implantacao = :necessidade_implantacao,
                        ganho_previsto = :ganho_previsto,
                        evidencia_url = :evidencia_url,
                        evidencia_nome = :evidencia_nome,
                        updated_at = NOW()
                    WHERE id = :id
                """)
                conn.execute(query, {
                    'id': analise_id,
                    'tipo': tipo,
                    'categoria': categoria,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'evidencia_url': evidencia_url_final,
                    'evidencia_nome': evidencia_nome_final
                })
                print(f"✏️ Análise {analise_id} atualizada")
            else:
                # Inserir nova
                query = text("""
                    INSERT INTO analises_criticas
                    (etapa_id, processo_id, tipo, categoria, 
                     analise_critica, sugestao_melhoria, 
                     necessidade_implantacao, ganho_previsto,
                     evidencia_url, evidencia_nome)
                    VALUES (:etapa_id, :processo_id, :tipo, :categoria,
                            :analise_critica, :sugestao_melhoria,
                            :necessidade_implantacao, :ganho_previsto,
                            :evidencia_url, :evidencia_nome)
                    RETURNING id
                """)
                result = conn.execute(query, {
                    'etapa_id': etapa_id,
                    'processo_id': processo_id,
                    'tipo': tipo,
                    'categoria': categoria,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'evidencia_url': evidencia_url_final,
                    'evidencia_nome': evidencia_nome_final
                })
                analise_id = result.fetchone()[0]
                print(f"✅ Nova análise criada! ID: {analise_id}")
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'id': analise_id,
                'message': 'Análise salva com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar análise: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise/<int:analise_id>', methods=['DELETE'])
def api_analise_excluir(analise_id):
    """Exclui uma análise crítica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM analises_criticas WHERE id = :id")
            conn.execute(query, {'id': analise_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Análise excluída'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir análise: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-follow-ups/criar', methods=['POST'])
def api_analise_follow_ups_criar():
    """Cria follow-ups automáticos para uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('analise_id')
    follow_ups = data.get('follow_ups', [])
    
    if not analise_id:
        return jsonify({'success': False, 'error': 'analise_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            for fu in follow_ups:
                query = text("""
                    INSERT INTO analises_follow_up (
                        analise_id, etapa, data_prevista, status, 
                        comentario, created_at, updated_at
                    ) VALUES (
                        :analise_id, :etapa, :data_prevista, 'Pendente',
                        'Aguardando registro', NOW(), NOW()
                    )
                """)
                conn.execute(query, {
                    'analise_id': analise_id,
                    'etapa': fu.get('etapa'),
                    'data_prevista': fu.get('data_prevista')
                })
            conn.commit()
            
            return jsonify({'success': True, 'message': f'{len(follow_ups)} follow-ups criados'})
            
    except Exception as e:
        print(f"❌ Erro ao criar follow-ups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/api/analise-auditado/<int:analise_id>/confirmar-implantacao', methods=['PUT'])
def api_analise_auditado_confirmar_implantacao(analise_id):
    """Confirma implantação de uma análise do auditado e cria follow-ups"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    plano_de_acao_implantado = data.get('plano_de_acao_implantado')
    data_execucao_plano_acao = data.get('data_execucao_plano_acao')
    
    if plano_de_acao_implantado and not data_execucao_plano_acao:
        return jsonify({'success': False, 'error': 'Data de implantação é obrigatória'}), 400
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime, timedelta
    
    try:
        with engine.connect() as conn:
            # Verificar se existe e é do tipo 'auditado'
            result = conn.execute(text("""
                SELECT id FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditado'
            """), {'id': analise_id})
            if not result.fetchone():
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            # Atualizar
            conn.execute(text("""
                UPDATE analises_criticas 
                SET plano_de_acao_implantado = :plano_de_acao_implantado,
                    data_execucao_plano_acao = :data_execucao_plano_acao,
                    updated_at = NOW()
                WHERE id = :id
            """), {
                'id': analise_id,
                'plano_de_acao_implantado': plano_de_acao_implantado,
                'data_execucao_plano_acao': data_execucao_plano_acao
            })
            
            # Criar follow-ups se implantada
            if plano_de_acao_implantado:
                data_base = datetime.strptime(data_execucao_plano_acao, '%Y-%m-%d')
                
                follow_ups = [
                    {'etapa': 'FOLLOW_UP_30', 'dias': 30},
                    {'etapa': 'FOLLOW_UP_60', 'dias': 60},
                    {'etapa': 'FOLLOW_UP_90', 'dias': 90}
                ]
                
                for fu in follow_ups:
                    data_prevista = data_base + timedelta(days=fu['dias'])
                    
                    check = conn.execute(text("""
                        SELECT id FROM analises_follow_up 
                        WHERE analise_id = :analise_id AND etapa = :etapa
                    """), {'analise_id': analise_id, 'etapa': fu['etapa']}).fetchone()
                    
                    if not check:
                        conn.execute(text("""
                            INSERT INTO analises_follow_up (
                                analise_id, etapa, data_prevista, status, created_by, created_at
                            ) VALUES (
                                :analise_id, :etapa, :data_prevista, 'Pendente', :created_by, NOW()
                            )
                        """), {
                            'analise_id': analise_id,
                            'etapa': fu['etapa'],
                            'data_prevista': data_prevista.date(),
                            'created_by': session.get('usuario_nome', 'Sistema')
                        })
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Implantação confirmada e follow-ups criados'})
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - HISTÓRICO DE ANDAMENTO
# ============================================================

# @app.route('/api/analise-historico/<int:analise_id>', methods=['GET'])
# def api_analise_historico_buscar(analise_id):
#     """Busca o histórico de andamento de uma análise"""
#     if not session.get('autenticado'):
#         return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
#     from database import engine
#     from sqlalchemy import text
    
#     try:
#         with engine.connect() as conn:
#             query = text("""
#                 SELECT id, status, comentario, created_by, created_at
#                 FROM analises_historico_andamento
#                 WHERE analise_id = :analise_id
#                 ORDER BY created_at DESC
#             """)
#             result = conn.execute(query, {'analise_id': analise_id}).fetchall()
            
#             historico = []
#             for row in result:
#                 historico.append({
#                     'id': row[0],
#                     'status': row[1],
#                     'comentario': row[2] or '',
#                     'created_by': row[3] or '',
#                     'data_registro': row[4].isoformat() if row[4] else None
#                 })
            
#             return jsonify({'success': True, 'historico': historico})
            
#     except Exception as e:
#         print(f"❌ Erro ao buscar histórico: {e}")
#         return jsonify({'success': False, 'error': str(e)}), 500


# @app.route('/api/analise-historico/salvar', methods=['POST'])
# def api_analise_historico_salvar():
#     """Salva um registro de andamento"""
#     if not session.get('autenticado'):
#         return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
#     data = request.json
#     analise_id = data.get('analise_id')
#     status = data.get('status')
#     comentario = data.get('comentario')
#     usuario_nome = session.get('usuario_nome', 'Sistema')
    
#     if not analise_id:
#         return jsonify({'success': False, 'error': 'analise_id é obrigatório'}), 400
    
#     from database import engine
#     from sqlalchemy import text
#     from datetime import datetime
    
#     try:
#         with engine.connect() as conn:
#             query = text("""
#                 INSERT INTO analises_historico_andamento (
#                     analise_id, status, comentario, created_by, created_at
#                 ) VALUES (
#                     :analise_id, :status, :comentario, :created_by, NOW()
#                 )
#             """)
#             conn.execute(query, {
#                 'analise_id': analise_id,
#                 'status': status,
#                 'comentario': comentario,
#                 'created_by': usuario_nome
#             })
#             conn.commit()
            
#             return jsonify({'success': True, 'message': 'Andamento registrado'})
            
#     except Exception as e:
#         print(f"❌ Erro ao salvar histórico: {e}")
#         return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise-follow-ups/<int:analise_id>', methods=['GET'])
def api_analise_follow_ups_buscar(analise_id):
    """Busca os follow-ups de uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa, data_prevista, data_realizada, status, comentario, responsavel
                FROM analises_follow_up
                WHERE analise_id = :analise_id
                ORDER BY data_prevista ASC
            """)
            result = conn.execute(query, {'analise_id': analise_id}).fetchall()
            
            follow_ups = []
            for row in result:
                follow_ups.append({
                    'id': row[0],
                    'etapa': row[1],
                    'data_prevista': row[2].isoformat() if row[2] else None,
                    'data_realizada': row[3].isoformat() if row[3] else None,
                    'status': row[4] or 'Pendente',
                    'comentario': row[5] or '',
                    'responsavel': row[6] or ''
                })
            
            return jsonify({'success': True, 'follow_ups': follow_ups})
            
    except Exception as e:
        print(f"❌ Erro ao buscar follow-ups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise-follow-up/<int:follow_up_id>', methods=['PUT'])
def api_analise_follow_up_atualizar(follow_up_id):
    """Atualiza um follow-up (registra resultado)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    status = data.get('status')
    comentario = data.get('comentario')
    usuario_nome = session.get('usuario_nome', 'Sistema')
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE analises_follow_up 
                SET status = :status,
                    comentario = :comentario,
                    data_realizada = NOW(),
                    responsavel = :responsavel,
                    updated_at = NOW()
                WHERE id = :id
            """)
            result = conn.execute(query, {
                'id': follow_up_id,
                'status': status,
                'comentario': comentario,
                'responsavel': usuario_nome
            })
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Follow-up não encontrado'}), 404
            
            return jsonify({'success': True, 'message': 'Follow-up registrado'})
            
    except Exception as e:
        print(f"❌ Erro ao atualizar follow-up: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - ANOTAÇÕES DO AUDITOR
# ============================================================

@app.route('/api/anotacoes', methods=['GET'])
def api_anotacoes_listar():
    """Retorna todas as anotações do usuário logado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, titulo, conteudo, created_at, updated_at
                FROM anotacoes_auditor
                WHERE usuario_id = :usuario_id
                ORDER BY updated_at DESC
            """)
            result = conn.execute(query, {'usuario_id': usuario_id}).fetchall()
            
            anotacoes = []
            for row in result:
                anotacoes.append({
                    'id': row[0],
                    'titulo': row[1] or 'Sem título',
                    'conteudo': row[2] or '',
                    'created_at': row[3].strftime('%d/%m/%Y %H:%M') if row[3] else '',
                    'updated_at': row[4].strftime('%d/%m/%Y %H:%M') if row[4] else ''
                })
            
            return jsonify({'success': True, 'anotacoes': anotacoes})
            
    except Exception as e:
        print(f"❌ Erro ao buscar anotações: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/anotacoes/salvar', methods=['POST'])
def api_anotacoes_salvar():
    """Salva ou atualiza uma anotação"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    data = request.json
    
    anotacao_id = data.get('id')
    titulo = data.get('titulo', 'Sem título')
    conteudo = data.get('conteudo', '')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            if anotacao_id:
                # Atualizar
                query = text("""
                    UPDATE anotacoes_auditor
                    SET titulo = :titulo, conteudo = :conteudo, updated_at = NOW()
                    WHERE id = :id AND usuario_id = :usuario_id
                """)
                conn.execute(query, {
                    'id': anotacao_id,
                    'titulo': titulo,
                    'conteudo': conteudo,
                    'usuario_id': usuario_id
                })
            else:
                # Nova
                query = text("""
                    INSERT INTO anotacoes_auditor (usuario_id, titulo, conteudo)
                    VALUES (:usuario_id, :titulo, :conteudo)
                    RETURNING id
                """)
                result = conn.execute(query, {
                    'usuario_id': usuario_id,
                    'titulo': titulo,
                    'conteudo': conteudo
                })
                anotacao_id = result.fetchone()[0]
            
            conn.commit()
            
            return jsonify({'success': True, 'id': anotacao_id, 'message': 'Anotação salva!'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar anotação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/anotacoes/<int:anotacao_id>', methods=['DELETE'])
def api_anotacoes_excluir(anotacao_id):
    """Exclui uma anotação"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                DELETE FROM anotacoes_auditor
                WHERE id = :id AND usuario_id = :usuario_id
            """)
            conn.execute(query, {'id': anotacao_id, 'usuario_id': usuario_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Anotação excluída'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir anotação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - DASHBOARD
# ============================================================

@app.route('/api/dashboard/riscos-etapa-magnitude')
def api_dashboard_riscos_etapa_magnitude():
    """Retorna quantidade de riscos de ETAPA por faixa de magnitude
    Suporta filtros por auditoria_id (única) ou auditoria_ids (múltiplas)
    """
    from database import engine
    from sqlalchemy import text
    
    try:
        auditoria_ids = request.args.get('auditoria_ids', '')
        auditoria_id = request.args.get('auditoria_id', '')
        
        with engine.connect() as conn:
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT 
                        SUM(CASE WHEN magnitude <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN magnitude >= 4 AND magnitude <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN magnitude >= 8 AND magnitude <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN magnitude >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos_etapa
                    WHERE ativo = true
                    AND auditoria_id IN ({placeholders})
                """)
                result = conn.execute(query, params).fetchone()
            
            # CASO 2: Uma auditoria específica
            elif auditoria_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN magnitude <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN magnitude >= 4 AND magnitude <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN magnitude >= 8 AND magnitude <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN magnitude >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos_etapa
                    WHERE ativo = true
                    AND auditoria_id = :auditoria_id
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            # CASO 3: Nenhum filtro - todos os riscos de etapa ativos
            else:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN magnitude <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN magnitude >= 4 AND magnitude <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN magnitude >= 8 AND magnitude <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN magnitude >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos_etapa
                    WHERE ativo = true
                """)
                result = conn.execute(query).fetchone()
            
            return jsonify({
                'success': True,
                'baixo': result[0] or 0,
                'medio': result[1] or 0,
                'alto': result[2] or 0,
                'critico': result[3] or 0
            })
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/riscos-etapa-magnitude: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================
# ===== API - AUDITORIAS =====
# ============================

@app.route('/api/usuarios-para-select')
def api_usuarios_para_select():
    """Retorna lista de usuários ativos para seleção"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome, login, perfil
                FROM usuarios
                WHERE ativo = true
                ORDER BY nome
            """)
            result = conn.execute(query).fetchall()
            
            usuarios = [{'id': row[0], 'nome': row[1], 'login': row[2], 'perfil': row[3]} for row in result]
            
            return jsonify(usuarios)
            
    except Exception as e:
        print(f"❌ Erro ao buscar usuários: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auditorias')
def api_auditorias_listar():
    """Retorna todas as auditorias cadastradas"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    a.id,
                    a.codigo_auditoria,
                    a.id_area,
                    a.titulo,
                    a.ano,
                    a.trimestre,
                    a.data_inicio,
                    a.data_fim,
                    a.status,
                    a.responsavel_equipe,
                    a.unidade,
                    a.emergencial,
                    i.nome_area
                FROM auditorias a
                LEFT JOIN informacoes_area i ON a.id_area = i.id_area
                ORDER BY a.ano DESC, a.trimestre DESC
            """)
            result = conn.execute(query).fetchall()
            
            auditorias = []
            for row in result:
                # ⭐ RESPONSAVEL_EQUIPE está no índice 9 (décimo campo do SELECT)
                responsaveis_raw = row[9]
                
                # Converter ARRAY do PostgreSQL para lista Python
                if responsaveis_raw is None:
                    responsaveis_lista = []
                elif isinstance(responsaveis_raw, list):
                    responsaveis_lista = responsaveis_raw
                else:
                    responsaveis_lista = []
                
                auditorias.append({
                    'id': row[0],
                    'codigo_auditoria': row[1],
                    'id_area': row[2],
                    'titulo': row[3],
                    'ano': row[4],
                    'trimestre': row[5],
                    'data_inicio': row[6].strftime('%Y-%m-%d') if row[6] else None,
                    'data_fim': row[7].strftime('%Y-%m-%d') if row[7] else None,
                    'status': row[8],
                    'responsavel_equipe': responsaveis_lista,
                    'unidade': row[10] if len(row) > 10 else None,
                    'emergecial': row[11] if len(row) > 11 else None,
                    'nome_area': row[12] if len(row) > 12 else None
                })
            
            return jsonify(auditorias)
            
    except Exception as e:
        print(f"❌ Erro ao listar auditorias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auditorias/salvar', methods=['POST'])
def api_auditorias_salvar():
    """Salva uma nova auditoria ou atualiza existente"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                INSERT INTO auditorias (
                    codigo_auditoria, id_area, titulo, ano, trimestre, 
                    data_inicio, data_fim, status, unidade, responsavel_equipe,
                    emergencial   -- <-- ADICIONE AQUI
                ) VALUES (
                    :codigo, :id_area, :titulo, :ano, :trimestre,
                    :data_inicio, :data_fim, :status, :unidade, :responsaveis,
                    :emergencial   -- <-- E AQUI
                )
            """)

            conn.execute(query, {
                'codigo': data.get('codigo_auditoria'),
                'id_area': data.get('id_area'),
                'titulo': data.get('titulo'),
                'ano': data.get('ano'),
                'trimestre': data.get('trimestre'),
                'data_inicio': data.get('data_inicio'),
                'data_fim': data.get('data_fim'),
                'status': data.get('status', 'Planejamento'),
                'unidade': data.get('unidade'),
                'responsaveis': data.get('responsavel_equipe', []),
                'emergencial': data.get('emergencial', False)   # <-- ADICIONE
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Auditoria salva com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auditorias/<int:auditoria_id>', methods=['DELETE'])
def api_auditorias_excluir(auditoria_id):
    """Exclui uma auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM auditorias WHERE id = :id")
            conn.execute(query, {'id': auditoria_id})
            conn.commit()
            
            return jsonify({'success': True})
            
    except Exception as e:
        print(f"❌ Erro ao excluir auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/auditorias/<int:auditoria_id>', methods=['PUT'])
def api_auditorias_atualizar(auditoria_id):
    """Atualiza uma auditoria existente (com validação de permissão)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    usuario_nome = session.get('usuario_nome')
    usuario_perfil = session.get('usuario_perfil')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar a auditoria para verificar permissão
            query_check = text("SELECT responsavel_equipe FROM auditorias WHERE id = :id")
            result_check = conn.execute(query_check, {'id': auditoria_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            responsaveis = result_check[0] or []
            
            # Verificar permissão: administrador OU responsável
            if usuario_perfil not in ['administrador', 'admin'] and usuario_nome not in responsaveis:
                return jsonify({'success': False, 'error': 'Você não tem permissão para editar esta auditoria'}), 403
            
            # Se a auditoria está cancelada, não permite editar
            query_status = text("SELECT status FROM auditorias WHERE id = :id")
            status_result = conn.execute(query_status, {'id': auditoria_id}).fetchone()
            
            if status_result and status_result[0] == 'Cancelada':
                return jsonify({'success': False, 'error': 'Auditorias canceladas não podem ser editadas'}), 403
            
            # Atualizar
            query = text("""
                UPDATE auditorias 
                SET 
                    codigo_auditoria = :codigo,
                    id_area = :id_area,
                    titulo = :titulo,
                    ano = :ano,
                    trimestre = :trimestre,
                    data_inicio = :data_inicio,
                    data_fim = :data_fim,
                    status = :status,
                    unidade = :unidade,
                    responsavel_equipe = :responsaveis,
                    emergencial = :emergencial   -- <-- ADICIONE
                WHERE id = :id
            """)

            conn.execute(query, {
                'id': auditoria_id,
                'codigo': data.get('codigo_auditoria'),
                'id_area': data.get('id_area'),
                'titulo': data.get('titulo'),
                'ano': data.get('ano'),
                'trimestre': data.get('trimestre'),
                'data_inicio': data.get('data_inicio'),
                'data_fim': data.get('data_fim'),
                'status': data.get('status', 'Planejamento'),
                'unidade': data.get('unidade'),
                'responsaveis': data.get('responsavel_equipe', []),
                'emergencial': data.get('emergencial', False)   # <-- ADICIONE
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Auditoria atualizada com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao atualizar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auditorias/<int:auditoria_id>')
def api_auditorias_buscar(auditoria_id):
    """Retorna uma auditoria específica para edição"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    id, 
                    codigo_auditoria, 
                    id_area, 
                    titulo, 
                    ano, 
                    trimestre, 
                    data_inicio, 
                    data_fim, 
                    status, 
                    responsavel_equipe, 
                    unidade,
                    emergencial
                FROM auditorias 
                WHERE id = :id
            """)
            result = conn.execute(query, {'id': auditoria_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            # ⭐ DEBUG: Imprimir todos os campos
            print(f"🔍 RESULT COMPLETO: {result}")
            print(f"🔍 QUANTIDADE DE CAMPOS: {len(result)}")
            print(f"🔍 ÍNDICE 0 (id): {result[0]}")
            print(f"🔍 ÍNDICE 11 (emergencial): {result[11] if len(result) > 11 else 'NÃO EXISTE'}")
            
            # responsavel_equipe está no índice 9
            responsaveis = result[9] if result[9] else []
            if not isinstance(responsaveis, list):
                responsaveis = []
            
            auditoria = {
                'id': result[0],
                'codigo_auditoria': result[1],
                'id_area': result[2],
                'titulo': result[3],
                'ano': result[4],
                'trimestre': result[5],
                'data_inicio': result[6].strftime('%Y-%m-%d') if result[6] else None,
                'data_fim': result[7].strftime('%Y-%m-%d') if result[7] else None,
                'status': result[8],
                'responsavel_equipe': responsaveis,
                'unidade': result[10] if len(result) > 10 else None,
                'emergencial': result[11] if len(result) > 11 and result[11] is not None else False
            }
            
            print(f"🔍 AUDITORIA DICT: {auditoria}")
            
            return jsonify({'success': True, 'auditoria': auditoria})
            
    except Exception as e:
        print(f"❌ Erro ao buscar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auditorias/<int:auditoria_id>/cancelar', methods=['PUT'])
def api_auditorias_cancelar(auditoria_id):
    """Cancela uma auditoria (soft delete) - apenas administrador"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # Verificar se é administrador
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Apenas administradores podem cancelar auditorias'}), 403
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE auditorias 
                SET status = 'CANCELADA', updated_at = NOW()
                WHERE id = :id AND status != 'CANCELADA'
            """)
            result = conn.execute(query, {'id': auditoria_id})
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada ou já cancelada'}), 404
            
            return jsonify({'success': True, 'message': 'Auditoria cancelada com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao cancelar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================
# ===== FIM API - AUDITORIAS =====
# ============================

@app.route('/api/auditorias/situacao')
def api_auditorias_situacao():
    """Retorna situação das auditorias com todos os status existentes"""
    from database import engine
    from sqlalchemy import text
    
    try:
        area_id = request.args.get('area_id')
        
        with engine.connect() as conn:
            if area_id:
                query = text("""
                    SELECT status, COUNT(*) as total
                    FROM auditorias
                    WHERE id_area = :area_id
                    GROUP BY status
                    ORDER BY 
                        CASE status
                            WHEN 'Planejamento' THEN 1
                            WHEN 'Em Execução' THEN 2
                            WHEN 'Concluída' THEN 3
                            WHEN 'Concluída Avaliação' THEN 4
                            WHEN 'Concluída com Follow-Up' THEN 5
                            WHEN 'Em Atraso' THEN 6
                            WHEN 'Inconclusiva' THEN 7
                            ELSE 8
                        END
                """)
                result = conn.execute(query, {'area_id': area_id}).fetchall()
            else:
                query = text("""
                    SELECT status, COUNT(*) as total
                    FROM auditorias
                    GROUP BY status
                    ORDER BY 
                        CASE status
                            WHEN 'Planejamento' THEN 1
                            WHEN 'Em Execução' THEN 2
                            WHEN 'Concluída' THEN 3
                            WHEN 'Concluída Avaliação' THEN 4
                            WHEN 'Concluída com Follow-Up' THEN 5
                            WHEN 'Em Atraso' THEN 6
                            WHEN 'Inconclusiva' THEN 7
                            ELSE 8
                        END
                """)
                result = conn.execute(query).fetchall()
            
            # Mapeamento de cores e ícones para cada status
            cores_status = {
                'Planejamento': '#ffc107',           # Amarelo
                'Em Execução': '#17a2b8',             # Azul
                'Concluída': '#28a745',               # Verde
                'Concluída Avaliação': '#20c997',     # Verde menta
                'Concluída com Follow-Up': '#34ce57', # Verde claro
                'Em Atraso': '#dc3545',               # Vermelho
                'Inconclusiva': '#6c757d'             # Cinza
            }
            
            # Nomes amigáveis para exibição
            nomes_status = {
                'Planejamento': 'Planejamento',
                'Em Execução': 'Em Execução',
                'Concluída': 'Concluída',
                'Concluída Avaliação': 'Concluída (Avaliação)',
                'Concluída com Follow-Up': 'Concluída (Follow-Up)',
                'Em Atraso': 'Em Atraso',
                'Inconclusiva': 'Inconclusiva'
            }
            
            labels = []
            dados = []
            cores = []
            
            for row in result:
                status = row[0]
                total = row[1]
                labels.append(nomes_status.get(status, status))
                dados.append(total)
                cores.append(cores_status.get(status, '#6c757d'))
            
            # Se não houver dados, retorna vazio
            if not dados:
                return jsonify({
                    'success': True,
                    'labels': ['Nenhuma auditoria'],
                    'dados': [1],
                    'cores': ['#e0e0e0']
                })
            
            return jsonify({
                'success': True,
                'labels': labels,
                'dados': dados,
                'cores': cores
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar situação das auditorias: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processos/detalhados')
def api_processos_detalhados():
    """Retorna a quantidade de processos que possuem etapas cadastradas (com filtros)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT COUNT(DISTINCT p.id)
                    FROM processos p
                    JOIN etapas_processo ep ON p.id = ep.processo_id
                    WHERE p.status = 'Ativo'
                    AND p.auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(DISTINCT p.id)
                    FROM processos p
                    JOIN etapas_processo ep ON p.id = ep.processo_id
                    WHERE p.status = 'Ativo'
                    AND p.auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # CASO 3: Nenhum filtro
            else:
                query = text("""
                    SELECT COUNT(DISTINCT p.id)
                    FROM processos p
                    JOIN etapas_processo ep ON p.id = ep.processo_id
                    WHERE p.status = 'Ativo'
                """)
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/processos/detalhados: {e}")
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/processos/total')
def api_processos_total():
    """Retorna o total de processos ativos (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Pega os parâmetros
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT COUNT(*) FROM processos 
                    WHERE status = 'Ativo' 
                    AND auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(*) FROM processos 
                    WHERE status = 'Ativo' AND auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # CASO 3: Nenhum filtro
            else:
                query = text("SELECT COUNT(*) FROM processos WHERE status = 'Ativo'")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/processos/total: {e}")
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/auditorias/total')
def api_auditorias_total():
    """Retorna o total de auditorias (com filtro por área)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        area_id = request.args.get('area_id')
        
        with engine.connect() as conn:
            if area_id:
                query = text("SELECT COUNT(*) FROM auditorias WHERE id_area = :area_id")
                total = conn.execute(query, {'area_id': area_id}).fetchone()[0] or 0
            else:
                query = text("SELECT COUNT(*) FROM auditorias")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
    except Exception as e:
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/riscos/total')
def api_riscos_total():
    """Retorna o total de riscos (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT COUNT(r.id) 
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(r.id) 
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # CASO 3: Nenhum filtro
            else:
                query = text("SELECT COUNT(*) FROM riscos")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/riscos/total: {e}")
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/dashboard/riscos-magnitude')
def api_dashboard_riscos_magnitude():
    """Retorna quantidade de riscos por faixa de magnitude (com suporte a filtros)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        auditoria_ids = request.args.get('auditoria_ids', '')
        auditoria_id = request.args.get('auditoria_id', '')
        
        with engine.connect() as conn:
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT 
                        SUM(CASE WHEN r.score_risco <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN r.score_risco >= 4 AND r.score_risco <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN r.score_risco >= 8 AND r.score_risco <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN r.score_risco >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id IN ({placeholders})
                """)
                result = conn.execute(query, params).fetchone()
            
            # CASO 2: Auditoria única ⭐ NOVO!
            elif auditoria_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN r.score_risco <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN r.score_risco >= 4 AND r.score_risco <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN r.score_risco >= 8 AND r.score_risco <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN r.score_risco >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id = :auditoria_id
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            # CASO 3: Nenhum filtro - todos os riscos
            else:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN score_risco <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN score_risco >= 4 AND score_risco <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN score_risco >= 8 AND score_risco <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN score_risco >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos
                """)
                result = conn.execute(query).fetchone()
            
            return jsonify({
                'success': True,
                'baixo': result[0] or 0,
                'medio': result[1] or 0,
                'alto': result[2] or 0,
                'critico': result[3] or 0
            })
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/riscos-magnitude: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/auditorias-status')
def api_dashboard_auditorias_status():
    """Retorna quantidade de auditorias por status (com filtro por área)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        area_id = request.args.get('area_id')
        
        with engine.connect() as conn:
            if area_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) as concluida,
                        SUM(CASE WHEN status = 'Em Execução' THEN 1 ELSE 0 END) as execucao,
                        SUM(CASE WHEN status = 'Planejamento' THEN 1 ELSE 0 END) as planejamento
                    FROM auditorias
                    WHERE id_area = :area_id
                """)
                result = conn.execute(query, {'area_id': area_id}).fetchone()
            else:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) as concluida,
                        SUM(CASE WHEN status = 'Em Execução' THEN 1 ELSE 0 END) as execucao,
                        SUM(CASE WHEN status = 'Planejamento' THEN 1 ELSE 0 END) as planejamento
                    FROM auditorias
                """)
                result = conn.execute(query).fetchone()
            
            return jsonify({
                'success': True,
                'concluida': result[0] or 0,
                'execucao': result[1] or 0,
                'planejamento': result[2] or 0
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/top-areas')
def api_dashboard_top_areas():
    """Retorna as áreas com mais processos (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT i.nome_area, COUNT(p.id) as total
                    FROM informacoes_area i
                    LEFT JOIN processos p ON i.id_area = p.id_area 
                        AND p.status = 'Ativo' 
                        AND p.auditoria_id IN ({placeholders})
                    GROUP BY i.id_area, i.nome_area
                    ORDER BY total DESC
                    LIMIT 5
                """)
                result = conn.execute(query, params).fetchall()
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT i.nome_area, COUNT(p.id) as total
                    FROM informacoes_area i
                    LEFT JOIN processos p ON i.id_area = p.id_area 
                        AND p.status = 'Ativo' 
                        AND p.auditoria_id = :auditoria_id
                    GROUP BY i.id_area, i.nome_area
                    ORDER BY total DESC
                    LIMIT 5
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            # CASO 3: Nenhum filtro
            else:
                query = text("""
                    SELECT i.nome_area, COUNT(p.id) as total
                    FROM informacoes_area i
                    LEFT JOIN processos p ON i.id_area = p.id_area AND p.status = 'Ativo'
                    GROUP BY i.id_area, i.nome_area
                    ORDER BY total DESC
                    LIMIT 5
                """)
                result = conn.execute(query).fetchall()
            
            areas = [{'nome_area': row[0], 'total': row[1]} for row in result]
            
            return jsonify({'success': True, 'areas': areas})
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/top-areas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/resumo-riscos')
def api_dashboard_resumo_riscos():
    """Retorna resumo de riscos por processo (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT 
                        p.id,
                        p.codigo_processo,
                        p.nome_processo,
                        COUNT(r.id) as total_riscos,
                        MAX(r.score_risco) as score_maximo
                    FROM processos p
                    LEFT JOIN riscos r ON p.id = r.processo_id
                    WHERE p.status = 'Ativo' 
                        AND p.auditoria_id IN ({placeholders})
                    GROUP BY p.id, p.codigo_processo, p.nome_processo
                    HAVING COUNT(r.id) > 0
                    ORDER BY score_maximo DESC NULLS LAST
                    LIMIT 10
                """)
                result = conn.execute(query, params).fetchall()
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT 
                        p.id,
                        p.codigo_processo,
                        p.nome_processo,
                        COUNT(r.id) as total_riscos,
                        MAX(r.score_risco) as score_maximo
                    FROM processos p
                    LEFT JOIN riscos r ON p.id = r.processo_id
                    WHERE p.status = 'Ativo' AND p.auditoria_id = :auditoria_id
                    GROUP BY p.id, p.codigo_processo, p.nome_processo
                    HAVING COUNT(r.id) > 0
                    ORDER BY score_maximo DESC NULLS LAST
                    LIMIT 10
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            # CASO 3: Nenhum filtro
            else:
                query = text("""
                    SELECT 
                        p.id,
                        p.codigo_processo,
                        p.nome_processo,
                        COUNT(r.id) as total_riscos,
                        MAX(r.score_risco) as score_maximo
                    FROM processos p
                    LEFT JOIN riscos r ON p.id = r.processo_id
                    WHERE p.status = 'Ativo'
                    GROUP BY p.id, p.codigo_processo, p.nome_processo
                    HAVING COUNT(r.id) > 0
                    ORDER BY score_maximo DESC NULLS LAST
                    LIMIT 10
                """)
                result = conn.execute(query).fetchall()
            
            processos = []
            for row in result:
                processos.append({
                    'id': row[0],
                    'codigo_processo': row[1] or '',
                    'nome_processo': row[2] or '',
                    'total_riscos': row[3] or 0,
                    'score_maximo': row[4] or 0
                })
            
            return jsonify({'success': True, 'processos': processos})
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/resumo-riscos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/controles/total')
def api_controles_total():
    """Retorna o total de controles cadastrados (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ NOVO: Pega o parâmetro de múltiplas auditorias
            auditoria_ids = request.args.get('auditoria_ids', '')
            # Mantém o antigo para compatibilidade
            auditoria_id = request.args.get('auditoria_id', '')
            
            # ⭐ CASO 1: Múltiplas auditorias (ex: "1,9")
            if auditoria_ids:
                # Converter "1,9" para lista [1, 9]
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                
                # Criar placeholders para SQL (ex: ':id0, :id1')
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                
                # Criar dicionário de parâmetros (ex: {'id0': 1, 'id1': 9})
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                # Query com IN (ex: WHERE p.auditoria_id IN (:id0, :id1))
                query = text(f"""
                    SELECT COUNT(*) FROM controles_etapa ce
                    JOIN riscos_etapa re ON ce.risco_id = re.id
                    JOIN etapas_processo ep ON re.etapa_id = ep.id
                    JOIN processos p ON ep.processo_id = p.id
                    WHERE p.auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # ⭐ CASO 2: Uma única auditoria (compatibilidade)
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(*) FROM controles_etapa ce
                    JOIN riscos_etapa re ON ce.risco_id = re.id
                    JOIN etapas_processo ep ON re.etapa_id = ep.id
                    JOIN processos p ON ep.processo_id = p.id
                    WHERE p.auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # ⭐ CASO 3: Nenhum filtro - todos os controles
            else:
                query = text("SELECT COUNT(*) FROM controles_etapa")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/controles/total: {e}")
        return jsonify({'total': 0, 'error': str(e)})

# ============================================================
# FIM API - DASHBOARD
# ============================================================

@app.route('/diagnostico-rapido')
def diagnostico_rapido():
    import time
    import psutil
    from flask import render_template_string
    
    resultados = {
        'memoria': psutil.virtual_memory().percent,
        'cpu': psutil.cpu_percent(interval=1),
    }
    
    # Teste de banco de dados
    start = time.time()
    from database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1")).fetchone()
    resultados['db_tempo'] = f"{(time.time() - start)*1000:.0f}ms"
    
    # Teste de renderização
    start = time.time()
    render_template_string('<h1>Teste</h1>')
    resultados['template_tempo'] = f"{(time.time() - start)*1000:.0f}ms"
    
    return jsonify(resultados)

# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Servidor Flask iniciando...")
    print(f"📁 SECRET_KEY configurada: {'✅ OK' if app.secret_key else '❌ FALHOU'}")
    print(f"⏱️ Timeout da sessão: {app.config['PERMANENT_SESSION_LIFETIME']}")
    print("=" * 50)
    print("\n📍 Acesse: http://127.0.0.1:5000/login")
    print("🔒 Use suas credenciais cadastradas no Supabase")
    print("\n⚠️ Aperte CTRL+C para parar o servidor\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)