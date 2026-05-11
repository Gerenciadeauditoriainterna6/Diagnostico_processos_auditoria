"""
Arquivo principal para aplicação Flask
Sistema de Auditoria Interna - FUSVE
"""

import os
from datetime import datetime, timedelta, date

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from dotenv import load_dotenv

# ============================================================
# CARREGAR CONFIGURAÇÕES
# ============================================================

load_dotenv()

# ============================================================
# IMPORTAR FUNÇÕES AUXILIARES
# ============================================================

from logic import validar_login_no_banco

# ============================================================
# FUNÇÕES DE UTILIDADE
# ============================================================

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

app = Flask(__name__)

# Configurações da sessão
app.secret_key = os.getenv('SECRET_KEY', 'chave-padrao-em-producao-mude')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=int(os.getenv('SESSION_TIMEOUT_SECONDS', 1800)))
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ============================================================
# ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
# ============================================================

@app.route('/login', methods=["GET", "POST"])
def login():
    """Tela de login do sistema"""
    if session.get('autenticado'):
        return redirect(url_for('dashboard'))
    
    erro = None
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        
        sucesso, usuario_id, usuario_nome, usuario_perfil = validar_login_no_banco(usuario, senha)
        
        if sucesso:
            session['autenticado'] = True
            session['usuario_logado'] = usuario
            session['usuario_nome'] = usuario_nome
            session['usuario_id'] = usuario_id
            session['usuario_perfil'] = usuario_perfil
            session['login_timestamp'] = datetime.now().isoformat()
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            erro = "❌ Usuário ou senha incorretos."
    
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    """Remove os dados da sessão e desloga o usuário"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/ping')
def ping():
    """Health check para o UptimeRobot"""
    return "OK", 200

# ============================================================
# ROTAS PRINCIPAIS (PÁGINAS)
# ============================================================

@app.route('/')
def home():
    """Redireciona para dashboard"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Dashboard principal"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/plano-anual')
def plano_anual():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('plano_anual.html')

@app.route('/diagnostico')
def diagnostico():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from modules.execucao.areas import carregar_areas_banco
    areas = carregar_areas_banco()
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    
    return render_template('diagnostico.html', areas=areas, usuario_perfil=usuario_perfil)

@app.route('/detalhamento')
def detalhamento():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('detalhamento.html')

@app.route('/visao-geral')
def visao_geral():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('visao_geral.html')

@app.route('/comunicacao')
def comunicacao():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('comunicacao.html')

@app.route('/relatorios')
def relatorios():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('relatorios.html')

@app.route('/areas')
def areas():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    return render_template('areas.html', usuario_perfil=usuario_perfil)

@app.route('/historico')
def historico():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('historico.html')

# ============================================================
# ROTAS DE API (BACKEND)
# ============================================================

@app.route('/api/plano-anual-pdf')
def api_plano_anual_pdf():
    """Serve o arquivo PDF do Plano Anual"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    pdf_path = os.path.join(os.path.dirname(__file__), 'assets', 'plano_auditoria_2026.pdf')
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf')
    return "Arquivo não encontrado", 404

@app.route('/api/auditorias-por-area')
def api_auditorias_por_area():
    """Retorna as auditorias de uma área"""
    from database import engine
    from sqlalchemy import text
    
    area_id = request.args.get('area_id')
    if not area_id:
        return jsonify({'error': 'area_id é obrigatório'}), 400
    
    query = text("""
        SELECT id, codigo_auditoria, titulo, trimestre, ano, status
        FROM auditorias
        WHERE id_area = :area_id
        ORDER BY ano DESC, trimestre DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"area_id": area_id})
        auditorias = [dict(row._mapping) for row in result]
    
    return jsonify({'auditorias': auditorias})

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

# ============================================================
# API - DIAGNÓSTICO DOS PROCESSOS
# ============================================================
@app.route('/api/processo/verificar')
def api_verificar_processo():
    """Verifica se um processo co o mesmo nome já existe na área"""
    nome_processo = request.args.get('nome')
    id_area = request.args.get('id_area')

    if not nome_processo or not id_area:
        return jsonify({'existe': False})
    
    from logic import buscar_processo_por_nome_e_area
    processo = buscar_processo_por_nome_e_area(nome_processo, id_area)

    if processo:
        return jsonify({
            'existe': True,
            'processo_id': processo['id'],
            'codigo': processo['codigo_processo']
        })
    return jsonify({'existe': False})

@app.route('/api/processo/gerar-codigo')
def api_gerar_codigo_processo():
    """Gera o próximo código sequencial para uma área"""
    from logic import gerar_codigo_processo
    
    id_area = request.args.get('id_area')
    if not id_area:
        return jsonify({'error': 'id_area é obrigatório'}), 400
    
    try:
        id_area = int(id_area)
    except ValueError:
        return jsonify({'error': 'id_area deve ser um número'}), 400
    
    codigo = gerar_codigo_processo(id_area)
    
    return jsonify({'codigo': codigo})

@app.route('/api/area/<int:area_id>/funcionarios-para-select')
def api_area_funcionarios_para_select(area_id):
    """Retorna funcionários da área formatados para select/multiselect"""
    from logic import listar_funcionarios_por_area

    funcionarios = listar_funcionarios_por_area(area_id)

    # Formato: [{"id": 1, "nome": "João Silva", "cargo": "Analista"}, ...]
    resultado = [
        {'id': func[0], 'nome': func[1], 'cargo': func[2] if len(func) > 2 else ''}
        for func in funcionarios
    ]

    return jsonify(resultado)


# ============================================================
# API - ÁREAS E FUNCIONÁRIOS
# ============================================================

@app.route('/api/areas')
def api_areas():
    """Retorna todas as áreas (ativas e inativas)"""
    from modules.execucao.areas import listar_areas
    
    # Passar apenas_ativas=False para buscar TODAS as áreas
    df = listar_areas(apenas_ativas=False)
    
    if df.empty:
        return jsonify([])
    
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/totais')
def api_totais():
    """Retorna totais de áreas e funcionários"""
    from modules.execucao.areas import listar_areas, listar_funcionarios_area
    
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
    """Retorna detalhes de uma área específica"""
    from logic import listar_areas
    
    # Buscar TODAS as áreas (ativas e inativas)
    df = listar_areas(apenas_ativas=False)
    area = df[df['id_area'] == area_id]
    
    if area.empty:
        return jsonify({}), 404
    
    return jsonify(area.iloc[0].to_dict())

@app.route('/api/area/<int:area_id>/funcionarios')
def api_area_funcionarios(area_id):
    """Retorna todos os funcionários de uma área com tempo calculado"""
    from modules.execucao.areas import listar_funcionarios_area
    
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
    """Desativa uma área (soft delete) - apenas administradores"""
    from logic import excluir_area
    
    perfil = session.get('usuario_perfil')
    
    if perfil not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    resultado = excluir_area(area_id)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao desativar área'}), 400

@app.route('/api/salvar-area', methods=['POST'])
def api_salvar_area():
    """Salva uma nova área"""
    from logic import salvar_area
    
    dados = request.json
    area_id = salvar_area(dados)
    
    if area_id:
        return jsonify({'success': True, 'id': area_id})
    return jsonify({'success': False}), 400

@app.route('/api/area/<int:area_id>', methods=['PUT'])
def api_atualizar_area(area_id):
    from logic import atualizar_area
    
    perfil = session.get('usuario_perfil')
    if perfil not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    dados = request.json
    resultado = atualizar_area(area_id, dados)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/area/<int:area_id>/reativar', methods=['PUT'])
def api_reativar_area(area_id):  # ← NOME DIFERENTE!
    """Reativa uma área (apenas administradores)"""
    from logic import reativar_area
    
    perfil = session.get('usuario_perfil')
    if perfil not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    resultado = reativar_area(area_id)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao reativar'}), 400

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
    """Exclui um funcionário (apenas administradores)"""
    from logic import excluir_funcionario
    
    perfil = session.get('usuario_perfil')
    
    if perfil not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    resultado = excluir_funcionario(funcionario_id)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao excluir'}), 400

@app.route('/api/funcionario/<int:funcionario_id>', methods=['PUT'])
def api_atualizar_funcionario(funcionario_id):
    from logic import atualizar_funcionario

    perfil = session.get('usuario_perfil')
    if perfil not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    dados = request.json
    resultado = atualizar_funcionario(funcionario_id, dados)

    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

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
    """Salva um novo funcionário no banco de dados"""
    from logic import salvar_funcionario
    
    dados = request.json
    resultado = salvar_funcionario(dados)
    
    if resultado:
        return jsonify({'success': True, 'id': resultado})
    return jsonify({'success': False}), 400

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