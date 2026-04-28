"""
Arquivo principal para aplicação Flask
Sistema de Auditoria Interna - FUSVE
"""

from flask import Flask, render_template, request, redirect, url_for, session
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Carrega variáveis do arquivo .env
load_dotenv()

# Importa minha função de validação do login (do sistema streamlit)
# Assumindo que a função está em logic.py
from logic import validar_login_no_banco

# Cria a aplicação Flask
app = Flask(__name__)

# Configurações da sessão
app.secret_key = os.getenv('SECRET_KEY', 'chave-padrao-em-producao-mude')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=int(os.getenv('SESSION_TIMEOUT_SECONDS', 1800)))
app.config['SESSION_COOKIE_SECURE'] = False # True apenas em produção (HTTPS)
app.config['SESSION_COOKIE_HITPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Rota de login
@app.route('/login', methods=["GET", "POST"])
def login():
    """
    Tela de login do sistema
    GET: Mostra o formulário
    POST: Processa as credenciais
    """
    # Se o usuário já está logado, redireciona para a página inicial
    if session.get('autenticado'):
        return redirect(url_for('home'))
    erro = None

    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        # Valida as credenciais usando a função existente
        sucesso, usuario_id, usuario_nome, usuario_perfil = validar_login_no_banco(usuario, senha)

        if sucesso:
            # Armazena os dados na sessão
            session['autenticado'] = True
            session['usuario_logado'] = usuario
            session['usuario_nome'] = usuario_nome
            session['usuario_id'] = usuario_id
            session['usuario_perfil'] = usuario_perfil
            session['login_timestamp'] = datetime.now().isoformat()
            session.permanent = True # Faz a sessão respeitar o timeout

            # Redireciona para a página principal
            return redirect(url_for('home'))
        else:
            erro = "❌ Usuário ou senha incorretos."
    
    return render_template('login.html', erro=erro)

# Rota de logout
@app.route('/logout')
def logout():
    """Remove os dados da sessão e desloga o usuário"""
    session.clear()
    return redirect(url_for('login'))

# Rota principal (página inicial / dashboard)
@app.route('/')
def home():
    """Página inicial do sistema (apenas para usuários logados)"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
     # Exibe informações do usuário logado
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - Auditoria Interna</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f0f0f0; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
            h1 {{ color: #184145; }}
            .user-info {{ background: #e0e0e0; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
            .logout-btn {{ color: red; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏢 Sistema de Auditoria Interna - FUSVE</h1>
            <div class="user-info">
                👤 <strong>{session.get('usuario_nome', session.get('usuario_logado'))}</strong> 
                (Perfil: {session.get('usuario_perfil', 'auditor')})
                <br>
                <a href="{url_for('logout')}" class="logout-btn">Sair</a>
            </div>
            <p>✅ Login realizado com sucesso!</p>
            <p>Migração Flask em andamento. Em breve, todas as 8 páginas estarão disponíveis aqui.</p>
            <hr>
            <small>Sessão expira em 30 minutos de inatividade.</small>
        </div>
    </body>
    </html>
    """

# Rota de health check (para o UptimeRobot)
@app.route('/ping')
def ping():
    """Mantém o aplicativo ativo no Render (usado com UptimeRobot)"""
    return "OK", 200

# Ponto de entrada da aplicação
if __name__ == '__main__':
    print("🚀 Servidor Flask iniciando...")
    print(f"📁 SECRET_KEY configurada: {'OK' if app.secret_key else 'FALHOU'}")
    print(f"⏱️ Timeout da sessão: {app.config['PERMANENT_SESSION_LIFETIME']}")
    print("\n📍 Acesse: http://127.0.0.1:5000/login")
    print("🔒 Para testar o login, use suas credenciais cadastradas no Supabase")
    print("\n⚠️ Aperte CTRL+C para parar o servidor\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)