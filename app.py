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
    from database import engine
    from sqlalchemy import text
    
    # Usar funcionarios_area (correto)
    query = text("""
        SELECT id, nome_funcionario, cargo
        FROM funcionarios_area
        WHERE id_area = :area_id AND ativo = true
        ORDER BY nome_funcionario
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'area_id': area_id})
        funcionarios = [{'id': row[0], 'nome': row[1], 'cargo': row[2] or ''} for row in result]
    
    return jsonify(funcionarios)

# ====== API - SALVAR INFORMAÇÕES BÁSICAS DO PROCESSO ======
@app.route('/api/processo/salvar-basico', methods=['POST'])
def api_salvar_processo_basico():
    """Salva as informações básicas do processo (nome, código, executores)"""
    from database import engine
    from sqlalchemy import text
    from logic import gerar_codigo_processo
    
    data = request.json
    nome_processo = data.get('nome_processo')
    codigo_processo = data.get('codigo_processo')
    id_area = data.get('id_area')
    nome_area = data.get('nome_area')
    executores_ids = data.get('executores_ids', [])
    auditoria_id = data.get('auditoria_id')
    
    if not nome_processo or not id_area:
        return jsonify({'success': False, 'error': 'Nome do processo e área são obrigatórios'}), 400
    
    try:
        with engine.connect() as conn:
            # Se não veio nome_area, buscar do banco
            if not nome_area:
                busca_area = text("SELECT nome_area FROM informacoes_area WHERE id_area = :id_area")
                result_area = conn.execute(busca_area, {'id_area': id_area}).fetchone()
                nome_area = result_area[0] if result_area else ''
            
            # Verificar se o processo já existe
            check_query = text("""
                SELECT id FROM processos 
                WHERE nome_processo = :nome AND id_area = :id_area
            """)
            existing = conn.execute(check_query, {
                'nome': nome_processo,
                'id_area': id_area
            }).fetchone()
            
            if existing:
                # Atualizar processo existente
                processo_id = existing[0]
                update_query = text("""
                    UPDATE processos 
                    SET nome_processo = :nome, 
                        codigo_processo = :codigo,
                        area = :area
                    WHERE id = :id
                    RETURNING id
                """)
                result = conn.execute(update_query, {
                    'nome': nome_processo,
                    'codigo': codigo_processo,
                    'area': nome_area,
                    'id': processo_id
                })
                processo_id = result.fetchone()[0]
            else:
                # Criar novo processo
                if not codigo_processo:
                    codigo_processo = gerar_codigo_processo(id_area)
                
                insert_query = text("""
                    INSERT INTO processos (nome_processo, codigo_processo, id_area, area)
                    VALUES (:nome, :codigo, :id_area, :area)
                    RETURNING id
                """)
                result = conn.execute(insert_query, {
                    'nome': nome_processo,
                    'codigo': codigo_processo,
                    'id_area': id_area,
                    'area': nome_area
                })
                processo_id = result.fetchone()[0]
            
            # ===== SALVAR EXECUTORES (APENAS UM BLOCO, COM LOGS) =====
            if executores_ids:
                print(f"🔍 Executores recebidos: {executores_ids}")
                print(f"🔍 Tipo do primeiro ID: {type(executores_ids[0]) if executores_ids else 'Nenhum'}")
                
                # Remover executores antigos
                delete_executors = text("DELETE FROM processo_executores WHERE processo_id = :processo_id")
                result_del = conn.execute(delete_executors, {'processo_id': processo_id})
                print(f"🗑️ Removidos {result_del.rowcount} executores antigos")
                
                # Inserir novos executores
                insert_executor = text("""
                    INSERT INTO processo_executores (processo_id, funcionario_id)
                    VALUES (:processo_id, :funcionario_id)
                """)
                for func_id in executores_ids:
                    try:
                        conn.execute(insert_executor, {
                            'processo_id': processo_id,
                            'funcionario_id': func_id
                        })
                        print(f"✅ Inserido funcionário {func_id} para processo {processo_id}")
                    except Exception as e:
                        print(f"❌ Erro ao inserir {func_id}: {e}")
                
                print(f"💾 {len(executores_ids)} executores salvos com sucesso!")
            else:
                print(f"⚠️ Nenhum executor para salvar no processo {processo_id}")
            
            # ===== VINCULAR À AUDITORIA =====
            if auditoria_id:
                # Verificar se já está vinculado
                check_link = text("""
                    SELECT id FROM auditoria_processos 
                    WHERE auditoria_id = :auditoria_id AND processo_id = :processo_id
                """)
                link_exists = conn.execute(check_link, {
                    'auditoria_id': auditoria_id,
                    'processo_id': processo_id
                }).fetchone()
                
                if not link_exists:
                    insert_link = text("""
                        INSERT INTO auditoria_processos (auditoria_id, processo_id, created_at, updated_at)
                        VALUES (:auditoria_id, :processo_id, NOW(), NOW())
                    """)
                    conn.execute(insert_link, {
                        'auditoria_id': auditoria_id,
                        'processo_id': processo_id
                    })
                    print(f"✅ Processo {processo_id} vinculado à auditoria {auditoria_id}")
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'processo_id': processo_id,
                'codigo_processo': codigo_processo,
                'message': 'Informações básicas salvas com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar processo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/processo/salvar-detalhes', methods=['POST'])
def api_salvar_processo_detalhes():
    """Salva os detalhes do processo (descrição, objetivo, etc)"""
    from database import engine
    from sqlalchemy import text
    
    data = request.json
    processo_id = data.get('processo_id')
    descricao = data.get('descricao', '')
    etapa_ini = data.get('etapa_ini', '')
    etapa_fim = data.get('etapa_fim', '')
    produto = data.get('produto', '')
    objetivo = data.get('objetivo', '')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET descricao = :descricao,
                    etapa_ini = :etapa_ini,
                    etapa_fim = :etapa_fim,
                    produto = :produto,
                    objetivo = :objetivo
                WHERE id = :processo_id
            """)
            
            conn.execute(query, {
                'descricao': descricao,
                'etapa_ini': etapa_ini,
                'etapa_fim': etapa_fim,
                'produto': produto,
                'objetivo': objetivo,
                'processo_id': processo_id
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Detalhes salvos com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar detalhes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/dados')
def api_processo_dados(processo_id):
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar dados básicos + detalhes
            query = text("""
                SELECT id, nome_processo, codigo_processo, id_area,
                       descricao, etapa_ini, etapa_fim, produto, objetivo
                FROM processos 
                WHERE id = :processo_id
            """)
            processo = conn.execute(query, {'processo_id': processo_id}).fetchone()
            
            if not processo:
                return jsonify({'success': False, 'error': 'Processo não encontrado'}), 404
            
            # Buscar executores
            query_exec = text("""
                SELECT f.id, f.nome_funcionario, f.cargo
                FROM processo_executores pe
                JOIN funcionarios_area f ON pe.funcionario_id = f.id
                WHERE pe.processo_id = :processo_id
            """)
            executores = conn.execute(query_exec, {'processo_id': processo_id}).fetchall()
            
            # ===== NOVO: Buscar riscos do processo =====
            query_riscos = text("""
                SELECT id, nome_risco, fator_risco, melhoria, apetite_risco,
                       impacto, probabilidade, motivo_risco, categoria
                FROM riscos
                WHERE processo_id = :processo_id
            """)
            riscos_result = conn.execute(query_riscos, {'processo_id': processo_id}).fetchall()
            
            riscos = []
            for r in riscos_result:
                # Converter categoria (string separada por vírgula) para lista
                categorias = r[8].split(',') if r[8] else []
                riscos.append({
                    'id': r[0],
                    'nome_risco': r[1] or '',
                    'fator_risco': r[2] or '',
                    'melhoria': r[3] or '',
                    'apetite_risco': r[4] or '',
                    'impacto': r[5] or 'Médio',
                    'probabilidade': r[6] or 'Médio',
                    'motivo_risco': r[7] or '',
                    'categorias': [c.strip() for c in categorias if c.strip()]
                })
            
            print(f"📋 Buscando riscos para processo {processo_id}: {len(riscos)} riscos encontrados")
            
            return jsonify({
                'success': True,
                'nome_processo': processo[1],
                'codigo_processo': processo[2],
                'id_area': processo[3],
                'descricao': processo[4] or '',
                'etapa_ini': processo[5] or '',
                'etapa_fim': processo[6] or '',
                'produto': processo[7] or '',
                'objetivo': processo[8] or '',
                'executores': [{'id': e[0], 'nome': e[1], 'cargo': e[2] or ''} for e in executores],
                'riscos': riscos
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar dados do processo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/salvar-riscos', methods=['POST'])
def api_salvar_processo_riscos():
    from database import engine
    from sqlalchemy import text
    
    data = request.json
    processo_id = data.get('processo_id')
    riscos = data.get('riscos', [])
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    
    # Mapa de risco para calcular score
    MAPA_RISCO = {
        ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14,
        ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
        ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10,
        ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
        ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6,
        ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
        ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2,
        ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
    }
    
    def calcular_score(impacto, probabilidade):
        return MAPA_RISCO.get((impacto, probabilidade), 0)
    
    try:
        with engine.connect() as conn:
            # Remover riscos existentes
            delete_query = text("DELETE FROM riscos WHERE processo_id = :processo_id")
            conn.execute(delete_query, {'processo_id': processo_id})
            
            # Inserir novos riscos com score
            insert_query = text("""
                INSERT INTO riscos (processo_id, nome_risco, fator_risco, melhoria, 
                                    apetite_risco, impacto, probabilidade, motivo_risco, 
                                    categoria, score_risco)
                VALUES (:processo_id, :nome_risco, :fator_risco, :melhoria, 
                        :apetite_risco, :impacto, :probabilidade, :motivo_risco, 
                        :categoria, :score_risco)
            """)
            
            for risco in riscos:
                impacto = risco.get('impacto', 'Médio')
                probabilidade = risco.get('probabilidade', 'Médio')
                score = calcular_score(impacto, probabilidade)
                
                categorias = risco.get('categorias', [])
                categoria_str = ', '.join(categorias) if categorias else None
                
                conn.execute(insert_query, {
                    'processo_id': processo_id,
                    'nome_risco': risco.get('nome_risco', ''),
                    'fator_risco': risco.get('fator_risco', ''),
                    'melhoria': risco.get('melhoria', ''),
                    'apetite_risco': risco.get('apetite_risco', ''),
                    'impacto': impacto,
                    'probabilidade': probabilidade,
                    'motivo_risco': risco.get('motivo_risco', ''),
                    'categoria': categoria_str,
                    'score_risco': score
                })
            
            conn.commit()
            print(f"✅ {len(riscos)} riscos salvos para o processo {processo_id}")
            return jsonify({'success': True, 'message': f'{len(riscos)} riscos salvos'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar riscos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
                           

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