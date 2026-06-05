"""
Arquivo principal para aplicação Flask
Sistema de Auditoria Interna - FUSVE
"""

import os
from datetime import datetime, timedelta, date
import json
import io

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, flash
from dotenv import load_dotenv

# ============================================================
# CARREGAR CONFIGURAÇÕES
# ============================================================

load_dotenv()

# ============================================================
# IMPORTAR FUNÇÕES AUXILIARES
# ============================================================

from logic import validar_login_no_banco, gerar_relatorio_gerencial_area

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
# MIDDLEWARE PARA AUDITORIA
# ============================================================

from flask import request, g
from database import engine
from sqlalchemy import text

@app.before_request
def configurar_auditoria():
    """
    Configura variáveis no PostgreSQL para auditoria
    """
    
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
    
    # ✅ NOVA ABORDAGEM: Chama a função PostgreSQL
    try:
        with engine.connect() as conn:
            conn.execute(
                text("SELECT set_app_user(:uid, :uname, :ip)"),
                {'uid': usuario_id, 'uname': usuario_nome, 'ip': ip_origem}
            )
            conn.commit()
            print(f"✅ [AUDITORIA] Usuário configurado: {usuario_id} - {usuario_nome} - {ip_origem}")
    except Exception as e:
        print(f"⚠️ [AUDITORIA] Erro: {e}")


# ============================================================
# ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
# ============================================================

@app.route('/login', methods=["GET", "POST"])
def login():
    """Tela de login do sistema"""
    if session.get('autenticado'):
        return redirect(url_for('home'))
    
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
            return redirect(url_for('home'))
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

# ============================================================
# ROTAS PRINCIPAIS (PÁGINAS)
# ============================================================

@app.route('/plano-anual')
def plano_anual():
    """Página do Plano Anual de Auditoria"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    
    return render_template('plano_anual.html', areas=areas, usuario_perfil=usuario_perfil)

@app.route('/dashboard')
def dashboard():
    """Dashboard principal"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# ============================================================
# API - PLANO ANUNAL
# ============================================================

@app.route('/api/plano-anual-pdf')
def api_plano_anual_pdf():
    """Serve o arquivo PDF do Plano Anual baseado no código da auditoria"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    codigo_auditoria = request.args.get('codigo')
    
    if not codigo_auditoria:
        return jsonify({'error': 'Código da auditoria é obrigatório'}), 400
    
    # Usar o código diretamente como nome do arquivo
    pdf_path = os.path.join(os.path.dirname(__file__), 'assets', f'{codigo_auditoria}.pdf')
    
    print(f"🔍 Buscando: {pdf_path}")
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf', as_attachment=True)
    
    return jsonify({'error': f'Arquivo PDF do plano anual não encontrado para esta auditoria.'}), 404

@app.route('/api/auditoria/<int:auditoria_id>/fundamentos', methods=['GET'])
def api_buscar_fundamentos_auditoria(auditoria_id):
    """Busca a lista de fundamentos da auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT COALESCE(fundamentos, '[]'::jsonb) as fundamentos
                FROM auditorias
                WHERE id = :auditoria_id
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            fundamentos = result[0] if result[0] else []
            
            return jsonify({
                'success': True,
                'fundamentos': fundamentos
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar fundamentos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auditoria/<int:auditoria_id>/fundamentos', methods=['POST'])
def api_salvar_fundamentos_auditoria(auditoria_id):
    """Salva a lista completa de fundamentos da auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    fundamentos = data.get('fundamentos', [])
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            # Converter para JSONB
            fundamentos_json = json.dumps(fundamentos)
            
            query = text("""
                UPDATE auditorias 
                SET fundamentos = :fundamentos::jsonb,
                    updated_at = NOW()
                WHERE id = :auditoria_id
            """)
            conn.execute(query, {
                'fundamentos': fundamentos_json,
                'auditoria_id': auditoria_id
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Fundamentos salvos com sucesso'})
            
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
    
    return render_template('diagnostico.html', areas=areas, usuario_perfil=usuario_perfil)

@app.route('/detalhamento')
def detalhamento():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from modules.execucao.areas import carregar_areas_banco
    areas = carregar_areas_banco()
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    
    return render_template('detalhamento.html', areas=areas, usuario_perfil=usuario_perfil)

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
    return render_template('relatorios.html')

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
            query = text("""
                SELECT ep.id, ep.codigo_etapa, ep.nome_etapa, ep.descricao_etapa,
                    ep.como_e_feito, ep.objetivo_etapa, ep.status_etapa, ep.criticidade_etapa,
                    ep.politica_interna, ep.analise_critica, ep.sugestao_melhoria,
                    ep.necessidade_implantacao, ep.ganho_previsto, ep.obrigacoes_regulatorias,
                    ep.executores_etapa,
                    ep.manual_nome, ep.created_at, ep.auditoria_id,  -- ⭐ ADICIONADO auditoria_id
                    EXISTS(
                        SELECT 1 FROM analises_criticas ac 
                        WHERE ac.etapa_id = ep.id AND ac.tipo_analise = 'entrevistado'
                    ) as tem_analise_auditado,
                    EXISTS(
                        SELECT 1 FROM analises_criticas ac 
                        WHERE ac.etapa_id = ep.id AND ac.tipo_analise = 'auditor'
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
                    'auditoria_id': row[17] if len(row) > 17 else None,  # ⭐ NOVO
                    'tem_analise_auditado': row[18] if len(row) > 18 else False,
                    'tem_analise_auditor': row[19] if len(row) > 19 else False,
                })
            
            return jsonify({'success': True, 'etapas': etapas})
        
    except Exception as e:
        print(f"❌ Erro ao buscar etapas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/detalhamento_etapas')
def detalhamento_etapas():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    return render_template('detalhamento_etapas.html')

@app.route('/api/controle-etapa/salvar', methods=['POST'])
def api_controle_etapa_salvar():
    """Salva um novo controle de etapa ou atualiza existente"""
    from database import engine
    from sqlalchemy import text
    
    data = request.json
    controle_id = data.get('id')
    risco_id = data.get('risco_id')
    auditoria_id = data.get('auditoria_id')
    
    
    # Dados do controle
    nome_controle = data.get('nome_controle', '')
    como_executado = data.get('como_executado', '')
    objetivo_controle = data.get('objetivo_controle', '')
    periodicidade_execucao = data.get('periodicidade_execucao', '')
    natureza = data.get('natureza', '')
    forma_execucao = data.get('forma_execucao', '')
    status_controle = data.get('status_controle', '')
    evidencia_realizacao = data.get('evidencia_realizacao', '')
    responsaveis_tratamento = data.get('responsaveis_tratamento', '')
    risco_avaliacao = data.get('risco_avaliacao', '')
    causa_motivo = data.get('causa_motivo', '')
    frequencia_evidencia = data.get('frequencia_evidencia', '')
    local_evidencia = data.get('local_evidencia', '')
    lgpd = data.get('lgpd', '')
    
    # Validação básica
    if not risco_id:
        return jsonify({'success': False, 'error': 'ID do risco é obrigatório'}), 400
    
    if not nome_controle:
        return jsonify({'success': False, 'error': 'Nome do controle é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            if controle_id:
                # EDIÇÃO: atualizar controle existente
                query = text("""
                    UPDATE controles_etapa
                    SET nome_controle = :nome_controle,
                        como_executado = :como_executado,
                        objetivo_controle = :objetivo_controle,
                        periodicidade_execucao = :periodicidade_execucao,
                        natureza = :natureza,
                        forma_execucao = :forma_execucao,
                        status_controle = :status_controle,
                        evidencia_realizacao = :evidencia_realizacao,
                        local_evidencia = :local_evidencia,
                        lgpd = :lgpd,
                        responsaveis_tratamento = :responsaveis_tratamento,
                        risco_avaliacao = :risco_avaliacao,
                        causa_motivo = :causa_motivo,
                        frequencia_evidencia = :frequencia_evidencia,
                        updated_at = CURRENT_DATE
                    WHERE id = :controle_id
                """)
                
                conn.execute(query, {
                    'controle_id': controle_id,
                    'nome_controle': nome_controle,
                    'como_executado': como_executado,
                    'objetivo_controle': objetivo_controle,
                    'periodicidade_execucao': periodicidade_execucao,
                    'natureza': natureza,
                    'forma_execucao': forma_execucao,
                    'status_controle': status_controle,
                    'evidencia_realizacao': evidencia_realizacao,
                    'local_evidencia': local_evidencia,     
                    'lgpd': lgpd,                            
                    'frequencia_evidencia': frequencia_evidencia,
                    'responsaveis_tratamento': responsaveis_tratamento,
                    'risco_avaliacao': risco_avaliacao,
                    'causa_motivo': causa_motivo
                })
                
                print(f"✏️ Controle {controle_id} atualizado!")
                
            else:
                # NOVO CONTROLE: inserir
                query = text("""
                    INSERT INTO controles_etapa (
                        risco_id, auditoria_id, nome_controle,
                        como_executado, objetivo_controle,
                        periodicidade_execucao, natureza, forma_execucao,
                        status_controle, evidencia_realizacao,
                        responsaveis_tratamento, risco_avaliacao, causa_motivo,
                        local_evidencia, lgpd,
                        frequencia_evidencia, created_at, updated_at
                    ) VALUES (
                        :risco_id, :auditoria_id, :nome_controle,
                        :como_executado, :objetivo_controle,
                        :periodicidade_execucao, :natureza, :forma_execucao,
                        :status_controle, :evidencia_realizacao,
                        :responsaveis_tratamento, :risco_avaliacao, :causa_motivo,
                        :local_evidencia, :lgpd,
                        :frequencia_evidencia, CURRENT_TIMESTAMP, CURRENT_DATE
                    )
                    RETURNING id
                """)
                
                result = conn.execute(query, {
                    'risco_id': risco_id,
                    'auditoria_id': auditoria_id,
                    'nome_controle': nome_controle,
                    'como_executado': como_executado,
                    'objetivo_controle': objetivo_controle,
                    'periodicidade_execucao': periodicidade_execucao,
                    'natureza': natureza,
                    'forma_execucao': forma_execucao,
                    'status_controle': status_controle,
                    'evidencia_realizacao': evidencia_realizacao,
                    'responsaveis_tratamento': responsaveis_tratamento,
                    'local_evidencia': local_evidencia,
                    'lgpd': lgpd,
                    'risco_avaliacao': risco_avaliacao,
                    'causa_motivo': causa_motivo,
                    'frequencia_evidencia': frequencia_evidencia
                })
                
                novo_id = result.fetchone()[0]
                print(f"✅ Novo controle criado! ID: {novo_id}")
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Controle salvo com sucesso',
                'controle_id': controle_id or novo_id
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar controle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500   
    
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

@app.route('/api/controle-etapa/<int:controle_id>', methods=['GET'])
def api_controle_etapa_detalhes(controle_id):
    """Retorna os dados de um controle específico para edição"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, risco_id, nome_controle, como_executado, objetivo_controle,
                       periodicidade_execucao, natureza, forma_execucao, status_controle,
                       evidencia_realizacao, responsaveis_tratamento, risco_avaliacao, causa_motivo,
                       frequencia_evidencia, local_evidencia, lgpd
                FROM controles_etapa
                WHERE id = :controle_id
            """)
            
            result = conn.execute(query, {'controle_id': controle_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Controle não encontrado'}), 404
            
            controle = {
                'id': result[0],
                'risco_id': result[1],
                'nome_controle': result[2] or '',
                'como_executado': result[3] or '',
                'objetivo_controle': result[4] or '',
                'periodicidade_execucao': result[5] or '',
                'natureza': result[6] or '',
                'forma_execucao': result[7] or '',
                'status_controle': result[8] or '',
                'evidencia_realizacao': result[9] or '',
                'responsaveis_tratamento': result[10] or '',
                'risco_avaliacao': result[11] or '',
                'causa_motivo': result[12] or '',
                'frequencia_evidencia': result[13] or '',
                'local_evidencia': result[14] or '',
                'lgpd': result[15] or ''
            }
            
            return jsonify({'success': True, 'controle': controle})
            
    except Exception as e:
        print(f"❌ Erro ao buscar controle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================================================
# ROTAS DE API (BACKEND)
# ============================================================

@app.route('/api/auditorias-por-area')
def api_auditorias_por_area():
    """Retorna as auditorias de uma área"""
    from database import engine
    from sqlalchemy import text
    
    area_id = request.args.get('area_id')
    if not area_id:
        return jsonify({'error': 'area_id é obrigatório'}), 400
    
    query = text("""
        SELECT id, codigo_auditoria, titulo, trimestre, ano, status, unidade
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
    """Verifica se um processo com o mesmo nome já existe na área E auditoria"""
    nome_processo = request.args.get('nome')
    id_area = request.args.get('id_area')
    auditoria_id = request.args.get('auditoria_id')  # ← NOVO

    if not nome_processo or not id_area or not auditoria_id:
        return jsonify({'existe': False})
    
    from logic import buscar_processo_por_nome_e_area
    processo = buscar_processo_por_nome_e_area(nome_processo, id_area, auditoria_id)  # ← MODIFICAR

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
    """Salva ou atualiza as informações básicas do processo"""
    from database import engine
    from sqlalchemy import text
    from logic import gerar_codigo_processo
    
    data = request.json
    print(f"📥 Dados recebidos em salvar-basico: {data}")
    print(f"🔍 processo_id recebido: {data.get('processo_id')}")
    
    # ===== DADOS RECEBIDOS DO FRONTEND =====
    processo_id = data.get('processo_id')
    nome_processo = data.get('nome_processo')
    codigo_processo = data.get('codigo_processo')
    id_area = data.get('id_area')
    nome_area = data.get('nome_area')
    executores_ids = data.get('executores_ids', [])
    auditoria_id = data.get('auditoria_id')
    
    # ===== VALIDAÇÕES BÁSICAS =====
    if not nome_processo or not id_area:
        return jsonify({'success': False, 'error': 'Nome do processo e área são obrigatórios'}), 400
    
    try:
        with engine.connect() as conn:
            # ===== BUSCAR NOME DA ÁREA SE NÃO VEIO =====
            if not nome_area:
                busca_area = text("SELECT nome_area FROM informacoes_area WHERE id_area = :id_area")
                result_area = conn.execute(busca_area, {'id_area': id_area}).fetchone()
                nome_area = result_area[0] if result_area else ''
            
            # ===== DECIDIR ENTRE UPDATE (EDIÇÃO) OU INSERT (NOVO) =====
            if processo_id:
                # ===== CASO 1: EDIÇÃO - Processo já existe, vamos ATUALIZAR =====
                print(f"✏️ Editando processo existente ID: {processo_id}")
                
                update_query = text("""
                    UPDATE processos 
                    SET nome_processo = :nome, 
                        codigo_processo = :codigo,
                        area = :area,
                        auditoria_id = :auditoria_id,
                        updated_at = NOW()
                    WHERE id = :id
                    RETURNING id
                """)
                result = conn.execute(update_query, {
                    'nome': nome_processo,
                    'codigo': codigo_processo,
                    'area': nome_area,
                    'auditoria_id': auditoria_id,
                    'id': processo_id
                })
                processo_id = result.fetchone()[0]
                print(f"✅ Processo {processo_id} atualizado com sucesso!")
                
            else:
                # ===== CASO 2: NOVO PROCESSO - Vamos CRIAR =====
                print(f"➕ Criando novo processo: {nome_processo}")
                
                # Verificar se já existe outro com mesmo nome na área E MESMA AUDITORIA
                check_query = text("""
                    SELECT id FROM processos 
                    WHERE nome_processo = :nome 
                    AND id_area = :id_area 
                    AND auditoria_id = :auditoria_id
                """)
                existing = conn.execute(check_query, {
                    'nome': nome_processo,
                    'id_area': id_area,
                    'auditoria_id': auditoria_id
                }).fetchone()
                
                if existing:
                    # Se já existe, usar o ID existente (edição implícita)
                    processo_id = existing[0]
                    print(f"⚠️ Processo já existe! Reutilizando ID: {processo_id}")
                    
                    # Atualizar mesmo assim
                    update_query = text("""
                        UPDATE processos 
                        SET nome_processo = :nome, 
                            codigo_processo = :codigo,
                            area = :area,
                            auditoria_id = :auditoria_id,
                            updated_at = NOW()
                        WHERE id = :id
                    """)
                    conn.execute(update_query, {
                        'nome': nome_processo,
                        'codigo': codigo_processo,
                        'area': nome_area,
                        'auditoria_id': auditoria_id,
                        'id': processo_id
                    })
                else:
                    # Realmente novo: gerar código e inserir
                    if not codigo_processo:
                        codigo_processo = gerar_codigo_processo(id_area, auditoria_id)  # ← PASSAR AUDITORIA_ID
                    
                    insert_query = text("""
                        INSERT INTO processos (
                            nome_processo, codigo_processo, id_area, area, 
                            auditoria_id, created_at, updated_at
                        )
                        VALUES (
                            :nome, :codigo, :id_area, :area, 
                            :auditoria_id, NOW(), NOW()
                        )
                        RETURNING id
                    """)
                    result = conn.execute(insert_query, {
                        'nome': nome_processo,
                        'codigo': codigo_processo,
                        'id_area': id_area,
                        'area': nome_area,
                        'auditoria_id': auditoria_id
                    })
                    processo_id = result.fetchone()[0]
                    print(f"✅ Novo processo criado com ID: {processo_id}")
            
            # ===== SALVAR EXECUTORES (funcionários que executam o processo) =====
            if executores_ids:
                print(f"👥 Salvando {len(executores_ids)} executores para o processo {processo_id}")
                
                # Remover executores antigos (para não duplicar)
                delete_executors = text("DELETE FROM processo_executores WHERE processo_id = :processo_id")
                conn.execute(delete_executors, {'processo_id': processo_id})
                
                # Inserir os novos executores
                insert_executor = text("""
                    INSERT INTO processo_executores (processo_id, funcionario_id, created_at, updated_at)
                    VALUES (:processo_id, :funcionario_id, NOW(), NOW())
                """)
                for func_id in executores_ids:
                    conn.execute(insert_executor, {
                        'processo_id': processo_id,
                        'funcionario_id': func_id
                    })
                print(f"✅ {len(executores_ids)} executores salvos!")
            else:
                print(f"⚠️ Nenhum executor para salvar no processo {processo_id}")
            
            # ⭐ REMOVIDO: Bloco de vinculação à auditoria (não é mais necessário)
            # O auditoria_id já está na tabela processos!
            
            # ===== CONFIRMAR TRANSAÇÃO =====
            conn.commit()
            
            # ===== RETORNAR SUCESSO =====
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
                    impacto, probabilidade, apetite_risco, motivo_risco,
                    categoria, causas,
                    tratamento_risco, descricao_tratamento, prazo_implantacao,
                    score_risco
                FROM riscos
                WHERE processo_id = :processo_id
            """)
            result = conn.execute(query, {'processo_id': processo_id}).fetchall()
            
            riscos = []
            for row in result:
                # MAPEAMENTO CORRETO DOS ÍNDICES (0 a 13)
                # 0: id
                # 1: nome_risco
                # 2: fator_risco
                # 3: melhoria
                # 4: impacto
                # 5: probabilidade
                # 6: apetite_risco
                # 7: motivo_risco
                # 8: categoria
                # 9: causas
                # 10: tratamento_risco
                # 11: descricao_tratamento
                # 12: prazo_implantacao
                # 13: score_risco
                
                # Converter strings para listas
                categorias_str = row[8] if len(row) > 8 else ''
                causas_str = row[9] if len(row) > 9 else ''
                
                categorias = categorias_str.split(',') if categorias_str else []
                causas_list = causas_str.split(',') if causas_str else []
                
                # Formatar data
                prazo = ''
                if len(row) > 12 and row[12]:
                    if hasattr(row[12], 'strftime'):
                        prazo = row[12].strftime('%Y-%m-%d')
                    else:
                        prazo = str(row[12])
                
                risco = {
                    'id': row[0],
                    'nome_risco': row[1] if len(row) > 1 and row[1] else '',
                    'fator_risco': row[2] if len(row) > 2 and row[2] else '',
                    'melhoria': row[3] if len(row) > 3 and row[3] else '',
                    'apetite_risco': row[6] if len(row) > 6 and row[6] else '',
                    'impacto': row[4] if len(row) > 4 and row[4] else 'Médio',
                    'probabilidade': row[5] if len(row) > 5 and row[5] else 'Médio',
                    'motivo_risco': row[7] if len(row) > 7 and row[7] else '',
                    'categorias': [c.strip() for c in categorias if c.strip()],
                    'categoria_causa': [c.strip() for c in causas_list if c.strip()],
                    'score_risco': row[13] if len(row) > 13 and row[13] else 0,
                    # ⭐ CAMPOS DE TRATAMENTO CORRIGIDOS ⭐
                    'como_tratar': row[10] if len(row) > 10 and row[10] else '',
                    'desc_tratamento': row[11] if len(row) > 11 and row[11] else '',
                    'prazo_implantacao': prazo
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

@app.route('/api/processo/<int:processo_id>/dados')
def api_processo_dados(processo_id):
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            # ===== 1. BUSCAR DADOS BÁSICOS DO PROCESSO =====
            # ⭐ AGORA COM auditoria_id DIRETO NO SELECT
            query = text("""
                SELECT p.id, p.nome_processo, p.codigo_processo, p.id_area, p.auditoria_id,
                       p.descricao, p.etapa_ini, p.etapa_fim, p.produto, p.objetivo,
                       p.fluxo_bpmn_nome, p.fluxo_bpmn_tipo,
                       i.nome_area
                FROM processos p
                JOIN informacoes_area i ON p.id_area = i.id_area
                WHERE p.id = :processo_id
            """)
            processo = conn.execute(query, {'processo_id': processo_id}).fetchone()
            
            if not processo:
                return jsonify({'success': False, 'error': 'Processo não encontrado'}), 404
            
            # ⭐ REMOVIDO: A busca separada da auditoria (já não é mais necessária)
            # O auditoria_id já está no SELECT acima no índice 4
            
            # ===== 2. BUSCAR EXECUTORES =====
            query_exec = text("""
                SELECT f.id, f.nome_funcionario, f.cargo
                FROM processo_executores pe
                JOIN funcionarios_area f ON pe.funcionario_id = f.id
                WHERE pe.processo_id = :processo_id
            """)
            executores = conn.execute(query_exec, {'processo_id': processo_id}).fetchall()
            
            # ===== 3. BUSCAR RISCOS =====
            query_riscos = text("""
                SELECT id, nome_risco, fator_risco, melhoria, apetite_risco,
                       impacto, probabilidade, motivo_risco, categoria, causas,
                       tratamento_risco, descricao_tratamento, prazo_implantacao
                FROM riscos
                WHERE processo_id = :processo_id
            """)
            riscos_result = conn.execute(query_riscos, {'processo_id': processo_id}).fetchall()
            
            riscos = []
            for r in riscos_result:
                # Índices baseados na ordem do SELECT acima
                # 0=id, 1=nome_risco, 2=fator_risco, 3=melhoria, 4=apetite_risco
                # 5=impacto, 6=probabilidade, 7=motivo_risco, 8=categoria, 9=causas
                # 10=tratamento_risco, 11=descricao_tratamento, 12=prazo_implantacao
                
                categorias = r[8].split(',') if r[8] else []
                categoria_causa = r[9].split(',') if r[9] else []
                
                # Converter data
                prazo = r[12]
                prazo_str = ''
                if prazo:
                    if hasattr(prazo, 'strftime'):
                        prazo_str = prazo.strftime('%Y-%m-%d')
                    elif isinstance(prazo, str):
                        prazo_str = prazo
                
                riscos.append({
                    'id': r[0],
                    'nome_risco': r[1] or '',
                    'fator_risco': r[2] or '',
                    'melhoria': r[3] or '',
                    'apetite_risco': r[4] or '',
                    'impacto': r[5] or 'Médio',
                    'probabilidade': r[6] or 'Médio',
                    'motivo_risco': r[7] or '',
                    'categorias': [c.strip() for c in categorias if c.strip()],
                    'categoria_causa': [c.strip() for c in categoria_causa if c.strip()],
                    'como_tratar': r[10] or '',
                    'desc_tratamento': r[11] or '',
                    'prazo_implantacao': prazo_str
                })
            
            # ===== 4. RETORNAR TODOS OS DADOS =====
            # ⭐ NOVO: p.auditoria_id está no índice 4
            return jsonify({
                'success': True,
                'nome_processo': processo[1],
                'codigo_processo': processo[2],
                'id_area': processo[3],
                'auditoria_id': processo[4],  # ← AGORA VEM DIRETO DO SELECT
                'nome_area': processo[12],    # ← Índice ajustado (12 em vez de 11)
                'descricao': processo[5] or '',
                'etapa_ini': processo[6] or '',
                'etapa_fim': processo[7] or '',
                'produto': processo[8] or '',
                'objetivo': processo[9] or '',
                'fluxo_bpmn_nome': processo[10] or '',
                'fluxo_bpmn_tipo': processo[11] or '',
                'executores': [{'id': e[0], 'nome': e[1], 'cargo': e[2] or ''} for e in executores],
                'riscos': riscos
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar dados do processo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/processo/<int:processo_id>/upload-bpmn', methods=['POST'])
def api_processo_upload_bpmn(processo_id):
    """Faz upload do fluxo BPMN do processo"""
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
        # Decodificar Base64 para bytes
        if ',' in arquivo_base64:
            arquivo_base64 = arquivo_base64.split(',')[1]
        arquivo_bytes = base64.b64decode(arquivo_base64)
        
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET fluxo_bpmn = :fluxo_bpmn,
                    fluxo_bpmn_nome = :nome,
                    fluxo_bpmn_tipo = :tipo,
                    updated_at = NOW()
                WHERE id = :processo_id
            """)
            
            conn.execute(query, {
                'fluxo_bpmn': arquivo_bytes,
                'nome': nome_arquivo,
                'tipo': tipo_arquivo,
                'processo_id': processo_id
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Fluxo BPMN salvo com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar fluxo BPMN: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/download-bpmn')
def api_processo_download_bpmn(processo_id):
    """Faz download do fluxo BPMN do processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT fluxo_bpmn, fluxo_bpmn_nome, fluxo_bpmn_tipo
                FROM processos
                WHERE id = :processo_id
            """)
            result = conn.execute(query, {'processo_id': processo_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'error': 'Nenhum fluxo BPMN encontrado'}), 404
            
            return send_file(
                io.BytesIO(result[0]),
                mimetype=result[2] or 'application/octet-stream',
                as_attachment=True,
                download_name=result[1] or f'fluxo_bpmn_processo_{processo_id}'
            )
            
    except Exception as e:
        print(f"❌ Erro ao baixar fluxo BPMN: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/remover-bpmn', methods=['DELETE'])
def api_processo_remover_bpmn(processo_id):
    """Remove o fluxo BPMN do processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET fluxo_bpmn = NULL,
                    fluxo_bpmn_nome = NULL,
                    fluxo_bpmn_tipo = NULL,
                    updated_at = NOW()
                WHERE id = :processo_id
            """)
            conn.execute(query, {'processo_id': processo_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Fluxo BPMN removido'})
            
    except Exception as e:
        print(f"❌ Erro ao remover fluxo BPMN: {e}")
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
            
            # Inserir novos riscos
            insert_query = text("""
                INSERT INTO riscos (
                    processo_id, nome_risco, fator_risco, melhoria, 
                    apetite_risco, impacto, probabilidade, motivo_risco, 
                    categoria, causas, score_risco,
                    tratamento_risco, descricao_tratamento, prazo_implantacao
                )
                VALUES (
                    :processo_id, :nome_risco, :fator_risco, :melhoria, 
                    :apetite_risco, :impacto, :probabilidade, :motivo_risco, 
                    :categoria, :causas, :score_risco,
                    :tratamento_risco, :descricao_tratamento, :prazo_implantacao
                )
            """)
            
            for risco in riscos:
                impacto = risco.get('impacto', 'Médio')
                probabilidade = risco.get('probabilidade', 'Médio')
                score = calcular_score(impacto, probabilidade)
                
                # Converter arrays para strings separadas por vírgula
                categorias = risco.get('categorias', [])
                categoria_str = ', '.join(categorias) if categorias else None
                
                # IMPORTANTE: frontend envia "categoria_causa", banco chama "causas"
                causas = risco.get('categoria_causa', [])
                causas_str = ', '.join([c.strip() for c in causas]) if causas else None
                
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
                    'causas': causas_str,                              # ← corrigido
                    'score_risco': score,
                    'tratamento_risco': risco.get('como_tratar', ''),   # ← frontend → banco
                    'descricao_tratamento': risco.get('desc_tratamento', ''),
                    'prazo_implantacao': risco.get('prazo_implantacao') or None
                })
            
            conn.commit()
            print(f"✅ {len(riscos)} riscos salvos para o processo {processo_id}")
            return jsonify({'success': True, 'message': f'{len(riscos)} riscos salvos'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar riscos: {e}")
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
                SELECT p.id, p.codigo_processo, p.nome_processo, p.objetivo, p.fluxo_bpmn_nome
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
    print(f"🔍 Resultado de excluir_area({area_id}): {resultado}")
    
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
# DETALHAMENTO DOS PROCESSOS
# ============================================================

@app.route('/api/risco-etapa/salvar', methods=['POST'])
def api_risco_etapa_salvar():
    """Salva um novo risco de etapa ou atualiza existente"""
    from database import engine
    from sqlalchemy import text

    data = request.json
    risco_id = data.get('id')
    etapa_id = data.get('etapa_id')
    auditoria_id = data.get('auditoria_id')

    # Dados do risco
    nome_risco = data.get('nome_risco', '')
    categoria = data.get('categoria', '')
    fator_risco = data.get('fator_risco', '')
    consequencia = data.get('consequencia', '')
    impacto = data.get('impacto', 'Médio')
    probabilidade = data.get('probabilidade', 'Médio')
    apetite = data.get('apetite', '')
    tratamento = data.get('tratamento', '')
    origem = data.get('origem', '')
    desc_tratamento = data.get('desc_tratamento', '')
    financeiro = data.get('financeiro', False)
    info_adicional = data.get('info_adicional', '')
    causas_lista = data.get('causas', [])
    causas_str = ', '.join(causas_lista) if causas_lista else None

    # Validação básica
    if not etapa_id:
        return jsonify({'success': False, 'error': 'Nome do risco é obrigatprio'}), 400
    
    # Calcular a magnitude (score) baseado em impacto e probabilidade
    # Usando a mesma lógico que temos no diagnóstico

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

    magnitude = MAPA_RISCO.get((impacto, probabilidade), 0)

    try:
        with engine.connect() as conn:
            if risco_id:
                # EDIÇÃO: atualizar risco existente
                query = text("""
                    UPDATE riscos_etapa
                    SET nome_risco = :nome_risco,
                        categoria = :categoria,
                        fator_risco = :fator_risco,
                        consequencia = :consequencia,
                        impacto = :impacto,
                        probabilidade = :probabilidade,
                        magnitude = :magnitude,
                        apetite = :apetite,
                        tratamento = :tratamento,
                        origem = :origem,
                        desc_tratamento = :desc_tratamento,
                        financeiro = :financeiro,
                        info_adicional = :info_adicional,
                        causas = :causas,
                        updated_at = NOW()
                    WHERE id = :risco_id
                """)

                conn.execute(query, {
                    'risco_id': risco_id,
                    'nome_risco': nome_risco,
                    'categoria': categoria,
                    'fator_risco': fator_risco,
                    'consequencia': consequencia,
                    'impacto': impacto,
                    'probabilidade': probabilidade,
                    'magnitude': magnitude,
                    'apetite': apetite,
                    'tratamento': tratamento,
                    'origem': origem,
                    'desc_tratamento': desc_tratamento,
                    'financeiro': financeiro,
                    'info_adicional': info_adicional,
                    'causas': causas_str
                })

                print(f"✏️ Risco de etapa {risco_id} atualizado!")
            
            else:
                # NOVO RISCO: inserir risco
                query = text("""
                    INSERT INTO riscos_etapa (
                        etapa_id, auditoria_id, nome_risco, categoria,
                        fator_risco, consequencia, impacto, probabilidade,
                        magnitude, apetite, tratamento, origem, causas,
                        desc_tratamento, financeiro, info_adicional, ativo, created_at
                    ) VALUES (
                        :etapa_id, :auditoria_id, :nome_risco, :categoria,
                        :fator_risco, :consequencia, :impacto, :probabilidade,
                        :magnitude, :apetite, :tratamento, :origem, :causas,
                        :desc_tratamento, :financeiro, :info_adicional, true, NOW()
                    )
                    RETURNING id
                """)

                result = conn.execute(query, {
                    'etapa_id': etapa_id,
                    'auditoria_id': auditoria_id,
                    'nome_risco': nome_risco,
                    'categoria': categoria,
                    'fator_risco': fator_risco,
                    'consequencia': consequencia,
                    'impacto': impacto,
                    'probabilidade': probabilidade,
                    'magnitude': magnitude,
                    'apetite': apetite,
                    'tratamento': tratamento,
                    'origem': origem,
                    'desc_tratamento': desc_tratamento,
                    'financeiro': financeiro,
                    'info_adicional': info_adicional,
                    'causas': causas_str
                })

                novo_id = result.fetchone()[0]
                print(f"✅ Novo risco de etapa criado! ID: {novo_id}")

            conn.commit()

            return jsonify({
                'success': True,
                'message': 'Risco salvo com sucesso',
                'risco_id': risco_id or novo_id
            })
    except Exception as e:
        print(f"❌ Erro ao salvar risco de etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/risco-etapa/<int:risco_id>', methods=['DELETE'])
def api_risco_etapa_excluir(risco_id):
    """Desativa um risco de etapa (soft delete)"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # Soft delete: apenas marcar como inativo
            query = text("""
                UPDATE riscos_etapa 
                SET ativo = false, updated_at = NOW()
                WHERE id = :risco_id
            """)
            conn.execute(query, {'risco_id': risco_id})
            conn.commit()

            return jsonify({'success': True, 'message': 'Risco desativado com sucesso'})
    except Exception as e:
        print(f"❌ Erro ao desativar risco: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/risco-etapa/<int:risco_id>')
def api_risco_etapa_detalhes(risco_id):
    """Retorna os dados de um risco específico para edição"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa_id, nome_risco, categoria, fator_risco,
                       consequencia, impacto, probabilidade, magnitude,
                       apetite, tratamento, origem, desc_tratamento, financeiro,
                       info_adicional, ativo, causas
                FROM riscos_etapa
                WHERE id = :risco_id
            """)
            result = conn.execute(query, {'risco_id': risco_id}).fetchone()

            if not result:
                return jsonify({'success': False, 'error': 'Risco não encontrado'}), 404

            risco = {
                'id': result[0],
                'etapa_id': result[1],
                'nome_risco': result[2] or '',
                'categoria': result[3] or '',
                'fator_risco': result[4] or '',
                'consequencia': result[5] or '',
                'impacto': result[6] or 'Médio',
                'probabilidade': result[7] or 'Médio',
                'magnitude': result[8] or 0,
                'apetite': result[9] or '',
                'tratamento': result[10] or '',
                'origem': result[11] or '',
                'desc_tratamento': result[12] or '',
                'financeiro': result[13] or False,
                'info_adicional': result[14] or '',
                'ativo': result[15] if result[15] is not None else True,
                'causas': [c.strip() for c in result[16].split(',')] if result[16] else []
            }

            return jsonify({'success': True, 'risco': risco})

    except Exception as e:
        print(f"❌ Erro ao buscar risco: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/riscos')
def api_etapa_riscos(etapa_id):
    """Retorna todos os riscos associados a uma etapa"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_risco, categoria, fator_risco, consequencia,
                       impacto, probabilidade, magnitude, apetite, tratamento,
                       origem, desc_tratamento, financeiro, info_adicional, ativo, causas
                FROM riscos_etapa
                WHERE etapa_id = :etapa_id AND (ativo IS NULL OR ativo = true)
                ORDER BY id
            """)
            
            # ← IMPORTANTE: ESTA LINHA PRECISA ESTAR DENTRO DO WITH!
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchall()

            riscos = []
            for row in result:
                riscos.append({
                    'id': row[0],
                    'nome_risco': row[1] or '',
                    'categoria': row[2] or '',
                    'fator_risco': row[3] or '',
                    'consequencia': row[4] or '',
                    'impacto': row[5] or 'Médio',
                    'probabilidade': row[6] or 'Médio',
                    'magnitude': row[7] or 0,
                    'apetite': row[8] or '',
                    'tratamento': row[9] or '',
                    'origem': row[10] or '',
                    'desc_tratamento': row[11] or '',
                    'financeiro': row[12] or False,
                    'info_adicional': row[13] or '',
                    'ativo': row[14] if row[14] is not None else True,
                    'causas': [c.strip() for c in row[15].split(',')] if row[15] else []
                })

            return jsonify({'success': True, 'riscos': riscos})
    
    except Exception as e:
        print(f"❌ Erro ao buscar riscos da etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/riscos/count')
def api_etapa_riscos_count(etapa_id):
    """Retorna a quantidade de riscos de uma etapa"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) 
                FROM riscos_etapa 
                WHERE etapa_id = :etapa_id 
                AND (ativo IS NULL OR ativo = true)
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()

            # result[0] contém o número de riscos
            total = result[0] if result[0] else 0
            
            return jsonify({
                'success': True, 
                'total': total
            })
            
    except Exception as e:
        print(f"❌ Erro ao contar riscos da etapa {etapa_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/detalhamento_riscos')
def detalhamento_riscos():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()

    return render_template('detalhamento_riscos.html', areas=areas)

@app.route('/detalhamento_controles')
def detalhamento_controles():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    
    return render_template('detalhamento_controles.html', areas=areas)

@app.route('/api/etapa/<int:etapa_id>/download/<tipo>')
def api_etapa_download(etapa_id, tipo):
    """Download do diagrama ou manual da etapa"""
    from database import engine
    from sqlalchemy import text
    from flask import send_file
    import io
    
    if tipo not in ['diagrama', 'manual']:
        return jsonify({'error': 'Tipo inválido'}), 400
    
    try:
        with engine.connect() as conn:
            if tipo == 'diagrama':
                query = text("SELECT diagrama_bpmn, diagrama_nome, diagrama_tipo FROM etapas_processo WHERE id = :etapa_id")
            else:
                query = text("SELECT manual_etapa, manual_nome, manual_tipo FROM etapas_processo WHERE id = :etapa_id")
            
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'error': 'Arquivo não encontrado'}), 404
            
            arquivo_bytes = result[0]
            nome_arquivo = result[1] or f'{tipo}_{etapa_id}'
            tipo_arquivo = result[2] or 'application/octet-stream'
            
            return send_file(
                io.BytesIO(arquivo_bytes),
                mimetype=tipo_arquivo,
                as_attachment=True,
                download_name=nome_arquivo
            )
            
    except Exception as e:
        print(f"❌ Erro ao baixar arquivo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/excluir', methods=['DELETE'])
def api_excluir_etapa(etapa_id):
    """Remove uma etapa do processo"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM etapas_processo WHERE id = :etapa_id")
            conn.execute(query, {'etapa_id': etapa_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Etapa removida com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>')
def api_etapa_detalhes(etapa_id):
    """Retorna os dados de uma etapa específica para edição"""
    from database import engine
    from sqlalchemy import text
    import base64
    from datetime import datetime, timedelta, date
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, processo_id, codigo_etapa, nome_etapa, descricao_etapa,
                       como_e_feito, objetivo_etapa, status_etapa, criticidade_etapa,
                       politica_interna, analise_critica, sugestao_melhoria,
                       necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                       executores_etapa,
                       diagrama_bpmn, diagrama_nome, diagrama_tipo,
                       manual_etapa, manual_nome, manual_tipo,
                       arquivo_mapeamento, arquivo_mapeamento_nome, arquivo_mapeamento_tipo
                FROM etapas_processo
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            # ===== CONVERTER DIAGRAMA PARA BASE64 =====
            diagrama_base64 = None
            if result[16]:  # diagrama_bpmn
                diagrama_base64 = base64.b64encode(result[16]).decode('utf-8')
            
            # ===== CONVERTER MANUAL PARA BASE64 =====
            manual_base64 = None
            if result[19]:  # manual_etapa
                manual_base64 = base64.b64encode(result[19]).decode('utf-8')
            
            # ===== CONVERTER ARQUIVO DE MAPEAMENTO PARA BASE64 =====
            arquivo_mapeamento_base64 = None
            if result[22]:  # arquivo_mapeamento (índice 22)
                arquivo_mapeamento_base64 = base64.b64encode(result[22]).decode('utf-8')
            
            etapa = {
                'id': result[0],
                'processo_id': result[1],
                'codigo_etapa': result[2] or '',
                'nome_etapa': result[3] or '',
                'descricao_etapa': result[4] or '',
                'como_e_feito': result[5] or '',
                'objetivo_etapa': result[6] or '',
                'status_etapa': result[7] or 'Ativa',
                'criticidade_etapa': result[8] or 'Em aprovação',
                'politica_interna': result[9] or '',
                'analise_critica': result[10] or '',
                'sugestao_melhoria': result[11] or '',
                'necessidade_implantacao': result[12] or '',
                'ganho_previsto': result[13] or '',
                'obrigacoes_regulatorias': result[14] or '',
                'executores_etapa': result[15] or '',
                
                # Diagrama
                'diagrama_base64': diagrama_base64,
                'diagrama_nome': result[17] or '',
                'diagrama_tipo': result[18] or '',
                
                # Manual
                'manual_base64': manual_base64,
                'manual_nome': result[20] or '',
                'manual_tipo': result[21] or '',
                
                # Arquivo de Mapeamento (NOVO)
                'arquivo_mapeamento_base64': arquivo_mapeamento_base64,
                'arquivo_mapeamento_nome': result[23] or '',
                'arquivo_mapeamento_tipo': result[24] or '',
            }
            
            return jsonify({'success': True, 'etapa': etapa})
            
    except Exception as e:
        print(f"❌ Erro ao buscar etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/etapa/gerar-codigo')
def api_gerar_codigo_etapa():
    """Gera o próximo código de etapa para um processo"""
    from database import engine
    from sqlalchemy import text
    
    processo_id = request.args.get('processo_id')
    if not processo_id:
        return jsonify({'error': 'processo_id é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            # Buscar o código do processo
            query_processo = text("SELECT codigo_processo FROM processos WHERE id = :processo_id")
            processo = conn.execute(query_processo, {'processo_id': processo_id}).fetchone()
            
            if not processo:
                return jsonify({'error': 'Processo não encontrado'}), 404
            
            codigo_processo = processo[0]
            
            # Buscar o maior número de etapa para este processo
            query_etapas = text("""
                SELECT MAX(CAST(COALESCE(REGEXP_REPLACE(codigo_etapa, '^.*\\.', ''), '0') AS INTEGER))
                FROM etapas_processo
                WHERE processo_id = :processo_id
            """)
            result = conn.execute(query_etapas, {'processo_id': processo_id}).fetchone()
            
            ultimo_numero = result[0] if result[0] else 0
            novo_numero = ultimo_numero + 1
            
            codigo_etapa = f"{codigo_processo}.{novo_numero}"
            
            return jsonify({'success': True, 'codigo_etapa': codigo_etapa})
            
    except Exception as e:
        print(f"❌ Erro ao gerar código da etapa: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/etapa/salvar', methods=['POST'])
def api_salvar_etapa():
    """Salva uma nova etapa ou atualiza existente"""
    from database import engine
    from sqlalchemy import text
    import base64
    
    data = request.json
    etapa_id = data.get('id')
    processo_id = data.get('processo_id')
    auditoria_id = data.get('auditoria_id')
    codigo_etapa = data.get('codigo_etapa')
    nome_etapa = data.get('nome_etapa')
    descricao_etapa = data.get('descricao_etapa', '')
    como_e_feito = data.get('como_e_feito', '')
    objetivo_etapa = data.get('objetivo_etapa', '')
    status_etapa = data.get('status_etapa', 'Ativa')
    criticidade_etapa = data.get('criticidade_etapa', 'Em aprovação')
    politica_interna = data.get('politica_interna', '')
    analise_critica = data.get('analise_critica', '')
    sugestao_melhoria = data.get('sugestao_melhoria', '')
    necessidade_implantacao = data.get('necessidade_implantacao', '')
    ganho_previsto = data.get('ganho_previsto', '')
    obrigacoes_regulatorias = data.get('obrigacoes_regulatorias', '')
    executores_etapa = data.get('executores_etapa', '')
    
    # ⭐⭐⭐ CORREÇÃO: Se auditoria_id não veio, buscar do processo
    if not auditoria_id and processo_id:
        try:
            with engine.connect() as conn:
                busca_query = text("SELECT auditoria_id FROM processos WHERE id = :processo_id")
                result = conn.execute(busca_query, {'processo_id': processo_id}).fetchone()
                if result and result[0]:
                    auditoria_id = result[0]
                    print(f"🔍 Auditoria_id {auditoria_id} obtido do processo {processo_id}")
        except Exception as e:
            print(f"⚠️ Erro ao buscar auditoria_id do processo: {e}")
    
    # Processar upload de arquivos (vêm como base64)
    diagrama_bytes = None
    diagrama_nome = data.get('diagrama_nome')
    diagrama_tipo = data.get('diagrama_tipo')
    
    if data.get('diagrama_base64'):
        diagrama_bytes = base64.b64decode(data['diagrama_base64'].split(',')[1] if ',' in data['diagrama_base64'] else data['diagrama_base64'])
    
    manual_bytes = None
    manual_nome = data.get('manual_nome')
    manual_tipo = data.get('manual_tipo')
    
    if data.get('manual_base64'):
        manual_bytes = base64.b64decode(data['manual_base64'].split(',')[1] if ',' in data['manual_base64'] else data['manual_base64'])
    
    # Processar upload do arquivo do mapeamento
    arquivo_mapeamento_bytes = None
    arquivo_mapeamento_nome = data.get('arquivo_mapeamento_nome')
    arquivo_mapeamento_tipo = data.get('arquivo_mapeamento_tipo')

    if data.get('arquivo_mapeamento_base64'):
        arquivo_mapeamento_bytes = base64.b64decode(data['arquivo_mapeamento_base64'].split(',')[1] if ',' in data['arquivo_mapeamento_base64'] else data['arquivo_mapeamento_base64'])

    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    
    if not nome_etapa:
        return jsonify({'success': False, 'error': 'Nome da etapa é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            if etapa_id:
                # ========== EDIÇÃO: atualizar etapa existente ==========
                
                # Verificar se deve remover arquivos
                remover_diagrama = data.get('remover_diagrama', False)
                remover_manual = data.get('remover_manual', False)
                
                # Se deve remover o diagrama, forçar None
                if remover_diagrama:
                    diagrama_bytes = None
                    diagrama_nome = None
                    diagrama_tipo = None
                    print(f"🗑️ Removendo diagrama da etapa {etapa_id}")
                
                # Se deve remover o manual, forçar None
                if remover_manual:
                    manual_bytes = None
                    manual_nome = None
                    manual_tipo = None
                    print(f"🗑️ Removendo manual da etapa {etapa_id}")
                
                # Parâmetros básicos
                params = {
                    'etapa_id': etapa_id,
                    'nome_etapa': nome_etapa,
                    'descricao_etapa': descricao_etapa,
                    'como_e_feito': como_e_feito,
                    'objetivo_etapa': objetivo_etapa,
                    'status_etapa': status_etapa,
                    'criticidade_etapa': criticidade_etapa,
                    'politica_interna': politica_interna,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'obrigacoes_regulatorias': obrigacoes_regulatorias,
                    'executores_etapa': executores_etapa
                }
                
                # ⭐⭐⭐ Se tem auditoria_id, atualizar também
                if auditoria_id:
                    params['auditoria_id'] = auditoria_id
                
                # Campos base da query
                base_fields = """
                    nome_etapa = :nome_etapa,
                    descricao_etapa = :descricao_etapa,
                    como_e_feito = :como_e_feito,
                    objetivo_etapa = :objetivo_etapa,
                    status_etapa = :status_etapa,
                    criticidade_etapa = :criticidade_etapa,
                    politica_interna = :politica_interna,
                    analise_critica = :analise_critica,
                    sugestao_melhoria = :sugestao_melhoria,
                    necessidade_implantacao = :necessidade_implantacao,
                    ganho_previsto = :ganho_previsto,
                    obrigacoes_regulatorias = :obrigacoes_regulatorias,
                    executores_etapa = :executores_etapa
                """
                
                # ⭐⭐⭐ Adicionar auditoria_id ao UPDATE se disponível
                if auditoria_id:
                    base_fields += ", auditoria_id = :auditoria_id"
                
                update_fields = []
                
                # Diagrama: se veio um novo arquivo OU foi marcado para remover
                if data.get('diagrama_base64') or remover_diagrama:
                    update_fields.append("diagrama_bpmn = :diagrama_bpmn")
                    update_fields.append("diagrama_nome = :diagrama_nome")
                    update_fields.append("diagrama_tipo = :diagrama_tipo")
                    params['diagrama_bpmn'] = diagrama_bytes
                    params['diagrama_nome'] = diagrama_nome
                    params['diagrama_tipo'] = diagrama_tipo
                
                # Manual: se veio um novo arquivo OU foi marcado para remover
                if data.get('manual_base64') or remover_manual:
                    update_fields.append("manual_etapa = :manual_etapa")
                    update_fields.append("manual_nome = :manual_nome")
                    update_fields.append("manual_tipo = :manual_tipo")
                    params['manual_etapa'] = manual_bytes
                    params['manual_nome'] = manual_nome
                    params['manual_tipo'] = manual_tipo
                
                # Arquivo de Mapeamento
                remover_arquivo_mapeamento = data.get('remover_arquivo_mapeamento', False)
                if data.get('arquivo_mapeamento_base64') or remover_arquivo_mapeamento:
                    update_fields.append("arquivo_mapeamento = :arquivo_mapeamento")
                    update_fields.append("arquivo_mapeamento_nome = :arquivo_mapeamento_nome")
                    update_fields.append("arquivo_mapeamento_tipo = :arquivo_mapeamento_tipo")
                    params['arquivo_mapeamento'] = arquivo_mapeamento_bytes
                    params['arquivo_mapeamento_nome'] = arquivo_mapeamento_nome
                    params['arquivo_mapeamento_tipo'] = arquivo_mapeamento_tipo
                
                # Montar query final
                if update_fields:
                    query_sql = f"""
                        UPDATE etapas_processo
                        SET {base_fields}, {', '.join(update_fields)}, updated_at = NOW()
                        WHERE id = :etapa_id
                    """
                else:
                    query_sql = f"""
                        UPDATE etapas_processo
                        SET {base_fields}, updated_at = NOW()
                        WHERE id = :etapa_id
                    """
                
                query = text(query_sql)
                conn.execute(query, params)
                
                print(f"✏️ Etapa {etapa_id} atualizada com sucesso! auditoria_id={auditoria_id}")
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Etapa salva com sucesso',
                    'codigo_etapa': codigo_etapa,
                    'etapa_id': etapa_id,
                    'id': etapa_id
                })
                
            else:
                # ========== NOVA ETAPA: inserir ==========
                
                # ⭐⭐⭐ CORREÇÃO CRÍTICA: Se ainda não tem auditoria_id, buscar do processo
                if not auditoria_id and processo_id:
                    busca_query = text("SELECT auditoria_id FROM processos WHERE id = :processo_id")
                    result = conn.execute(busca_query, {'processo_id': processo_id}).fetchone()
                    if result and result[0]:
                        auditoria_id = result[0]
                        print(f"🔍 Nova etapa - auditoria_id {auditoria_id} obtido do processo {processo_id}")
                
                # Se não veio código, gerar automaticamente
                if not codigo_etapa:
                    # Buscar código do processo e gerar próximo número
                    query_codigo = text("SELECT codigo_processo FROM processos WHERE id = :processo_id")
                    processo_codigo = conn.execute(query_codigo, {'processo_id': processo_id}).fetchone()
                    
                    if processo_codigo:
                        codigo_base = processo_codigo[0]
                        query_max = text("""
                            SELECT MAX(CAST(SUBSTRING(codigo_etapa FROM '[^.]+$') AS INTEGER))
                            FROM etapas_processo
                            WHERE processo_id = :processo_id
                        """)
                        max_result = conn.execute(query_max, {'processo_id': processo_id}).fetchone()
                        proximo_num = (max_result[0] or 0) + 1
                        codigo_etapa = f"{codigo_base}.{proximo_num}"
                    else:
                        codigo_etapa = f"{processo_id}.1"
                
                query = text("""
                    INSERT INTO etapas_processo (
                        processo_id, auditoria_id, codigo_etapa, nome_etapa,
                        descricao_etapa, como_e_feito, objetivo_etapa,
                        status_etapa, criticidade_etapa,
                        politica_interna, analise_critica, sugestao_melhoria,
                        necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                        executores_etapa,
                        diagrama_bpmn, diagrama_nome, diagrama_tipo,
                        manual_etapa, manual_nome, manual_tipo,
                        arquivo_mapeamento, arquivo_mapeamento_nome, arquivo_mapeamento_tipo,
                        created_at
                    ) VALUES (
                        :processo_id, :auditoria_id, :codigo_etapa, :nome_etapa,
                        :descricao_etapa, :como_e_feito, :objetivo_etapa,
                        :status_etapa, :criticidade_etapa,
                        :politica_interna, :analise_critica, :sugestao_melhoria,
                        :necessidade_implantacao, :ganho_previsto, :obrigacoes_regulatorias,
                        :executores_etapa,
                        :diagrama_bpmn, :diagrama_nome, :diagrama_tipo,
                        :manual_etapa, :manual_nome, :manual_tipo,
                        :arquivo_mapeamento, :arquivo_mapeamento_nome, :arquivo_mapeamento_tipo,
                        NOW()
                    )
                    RETURNING id
                """)
                
                result = conn.execute(query, {
                    'processo_id': processo_id,
                    'auditoria_id': auditoria_id,  # ⭐ AGORA NÃO É MAIS NULL!
                    'codigo_etapa': codigo_etapa,
                    'nome_etapa': nome_etapa,
                    'descricao_etapa': descricao_etapa,
                    'como_e_feito': como_e_feito,
                    'objetivo_etapa': objetivo_etapa,
                    'status_etapa': status_etapa,
                    'criticidade_etapa': criticidade_etapa,
                    'politica_interna': politica_interna,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'obrigacoes_regulatorias': obrigacoes_regulatorias,
                    'executores_etapa': executores_etapa,
                    'diagrama_bpmn': diagrama_bytes,
                    'diagrama_nome': diagrama_nome,
                    'diagrama_tipo': diagrama_tipo,
                    'manual_etapa': manual_bytes,
                    'manual_nome': manual_nome,
                    'manual_tipo': manual_tipo,
                    'arquivo_mapeamento': arquivo_mapeamento_bytes,
                    'arquivo_mapeamento_nome': arquivo_mapeamento_nome,
                    'arquivo_mapeamento_tipo': arquivo_mapeamento_tipo
                })
                
                novo_id = result.fetchone()[0]
                print(f"✅ Nova etapa criada! ID: {novo_id}, Código: {codigo_etapa}, auditoria_id: {auditoria_id}")
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Etapa salva com sucesso',
                    'codigo_etapa': codigo_etapa,
                    'etapa_id': novo_id,
                    'id': novo_id
                })
            
    except Exception as e:
        print(f"❌ Erro ao salvar etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
                JOIN riscos_etapa re ON ce.risco_id = re.id
                WHERE re.etapa_id = :etapa_id AND re.ativo = true
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
                    ac.id, ac.tipo_analise, ac.categoria,
                    ac.analise_critica, ac.sugestao_melhoria,
                    ac.necessidade_implantacao, ac.ganho_previsto,
                    ep.codigo_etapa, ep.nome_etapa,
                    p.codigo_processo, p.nome_processo
                FROM analises_criticas ac
                JOIN etapas_processo ep ON ac.etapa_id = ep.id
                JOIN processos p ON ep.processo_id = p.id
                WHERE p.auditoria_id = :auditoria_id   -- ← AGORA É DIRETO!
                AND ac.categoria = :categoria
                ORDER BY p.codigo_processo, ep.codigo_etapa, ac.tipo_analise
            """)
            
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'categoria': categoria
            }).fetchall()
            
            analises = []
            for row in result:
                analises.append({
                    'id': row[0],
                    'tipo_analise': row[1],
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

@app.route('/api/checklist/carregar')
def api_checklist_carregar():
    """Carrega as respostas de um checklist para uma auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    tipo = request.args.get('tipo')  # governanca, riscos, controles
    
    if not auditoria_id or not tipo:
        return jsonify({'success': False, 'error': 'auditoria_id e tipo são obrigatórios'}), 400
    
    # Mapeamento tipo -> nome da tabela e número de perguntas
    TABELAS = {
        'governanca': {'tabela': 'checklist_governanca_respostas', 'total': 13},
        'riscos': {'tabela': 'checklist_riscos_respostas', 'total': 12},
        'controles': {'tabela': 'checklist_controles_respostas', 'total': 12}
    }
    
    if tipo not in TABELAS:
        return jsonify({'success': False, 'error': 'Tipo de checklist inválido'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            tabela = TABELAS[tipo]['tabela']
            total_perguntas = TABELAS[tipo]['total']
            
            # Buscar registro existente
            query = text(f"""
                SELECT id, status, observacoes_gerais,
                       {', '.join([f'p{i}_resposta, p{i}_comentario' for i in range(1, total_perguntas + 1)])}
                FROM {tabela}
                WHERE auditoria_id = :auditoria_id
                ORDER BY id DESC
                LIMIT 1
            """)
            
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            if result:
                resposta_id = result[0]  # ← PEGAR O ID DA RESPOSTA
                status = result[1] or 'Não iniciado'
                observacoes = result[2] or ''
                
                # Montar respostas com evidências
                respostas = []
                for i in range(1, total_perguntas + 1):
                    idx_resposta = 3 + (i - 1) * 2
                    idx_comentario = 4 + (i - 1) * 2
                    
                    resposta_valor = result[idx_resposta] if idx_resposta < len(result) else ''
                    comentario_valor = result[idx_comentario] if idx_comentario < len(result) else ''
                    
                    # ⭐ BUSCAR EVIDÊNCIAS PARA ESTA RESPOSTA
                    evidencias = []
                    query_evidencias = text("""
                        SELECT id, nome_arquivo, tipo_arquivo, tamanho_bytes
                        FROM checklist_evidencias
                        WHERE resposta_id = :resposta_id AND pergunta_numero = :pergunta_numero
                    """)
                    ev_result = conn.execute(query_evidencias, {
                        'resposta_id': resposta_id,
                        'pergunta_numero': i
                        }).fetchall()
                    
                    for ev in ev_result:
                        evidencias.append({
                            'id': ev[0],
                            'nome_arquivo': ev[1],
                            'tipo_arquivo': ev[2],
                            'tamanho_bytes': ev[3]
                        })
                    
                    respostas.append({
                        'resposta': resposta_valor,
                        'comentario': comentario_valor,
                        'evidencias': evidencias  # ← INCLUI EVIDÊNCIAS
                    })
                
                return jsonify({
                    'success': True,
                    'id': resposta_id,
                    'status': status,
                    'observacoes_gerais': observacoes,
                    'respostas': respostas
                })
            else:
                # Nenhum registro encontrado - retornar vazio sem evidências
                respostas_vazias = [{'resposta': '', 'comentario': '', 'evidencias': []} for _ in range(total_perguntas)]
                
                return jsonify({
                    'success': True,
                    'id': None,
                    'status': 'Não iniciado',
                    'observacoes_gerais': '',
                    'respostas': respostas_vazias
                })
            
    except Exception as e:
        print(f"❌ Erro ao carregar checklist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/salvar', methods=['POST'])
def api_checklist_salvar():
    """Salva as respostas de um checklist (com suporte a arquivos em Base64)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # Receber dados do JSON (não mais FormData)
    data = request.json
    auditoria_id = data.get('auditoria_id')
    tipo = data.get('tipo')
    respostas = data.get('respostas')
    observacoes_gerais = data.get('observacoes_gerais', '')
    concluir = data.get('concluir', False)
    arquivos = data.get('arquivos', {})  # Dicionário com arquivos por pergunta
    
    if not auditoria_id or not tipo or not respostas:
        return jsonify({'success': False, 'error': 'auditoria_id, tipo e respostas são obrigatórios'}), 400
    
    TABELAS = {
        'governanca': {'tabela': 'checklist_governanca_respostas', 'total': 14},
        'riscos': {'tabela': 'checklist_riscos_respostas', 'total': 11},
        'controles': {'tabela': 'checklist_controles_respostas', 'total': 11}
    }
    
    if tipo not in TABELAS:
        return jsonify({'success': False, 'error': 'Tipo de checklist inválido'}), 400
    
    from database import engine
    from sqlalchemy import text
    import base64
    
    try:
        with engine.connect() as conn:
            tabela = TABELAS[tipo]['tabela']
            total_perguntas = TABELAS[tipo]['total']
            
            # Verificar se já existe um registro
            check_query = text(f"SELECT id FROM {tabela} WHERE auditoria_id = :auditoria_id")
            existing = conn.execute(check_query, {'auditoria_id': auditoria_id}).fetchone()
            
            resposta_id = None
            
            if existing:
                # UPDATE
                set_parts = []
                params = {'id': existing[0]}
                
                for i in range(1, total_perguntas + 1):
                    if i - 1 < len(respostas):
                        set_parts.append(f"p{i}_resposta = :p{i}_resposta")
                        set_parts.append(f"p{i}_comentario = :p{i}_comentario")
                        params[f'p{i}_resposta'] = respostas[i-1].get('resposta', '')
                        params[f'p{i}_comentario'] = respostas[i-1].get('comentario', '')
                
                set_parts.append("observacoes_gerais = :observacoes")
                set_parts.append("status = :status")
                set_parts.append("updated_at = NOW()")
                params['observacoes'] = observacoes_gerais
                params['status'] = 'Concluído' if concluir else 'Em andamento'
                
                update_query = text(f"UPDATE {tabela} SET {', '.join(set_parts)} WHERE id = :id")
                conn.execute(update_query, params)
                resposta_id = existing[0]
                
            else:
                # INSERT
                colunas = ['auditoria_id', 'status', 'observacoes_gerais']
                valores_placeholders = [':auditoria_id', ':status', ':observacoes']
                params = {
                    'auditoria_id': auditoria_id,
                    'status': 'Concluído' if concluir else 'Em andamento',
                    'observacoes': observacoes_gerais
                }
                
                for i in range(1, total_perguntas + 1):
                    if i - 1 < len(respostas):
                        colunas.append(f"p{i}_resposta")
                        colunas.append(f"p{i}_comentario")
                        valores_placeholders.append(f":p{i}_resposta")
                        valores_placeholders.append(f":p{i}_comentario")
                        params[f'p{i}_resposta'] = respostas[i-1].get('resposta', '')
                        params[f'p{i}_comentario'] = respostas[i-1].get('comentario', '')
                
                insert_query = text(f"""
                    INSERT INTO {tabela} ({', '.join(colunas)})
                    VALUES ({', '.join(valores_placeholders)})
                    RETURNING id
                """)
                result = conn.execute(insert_query, params)
                resposta_id = result.fetchone()[0]
            
            # Processar arquivos enviados (apenas para controles)
            if tipo == 'controles' and arquivos:
                # Primeiro, remover evidências antigas desta resposta
                delete_evidencias = text("DELETE FROM checklist_evidencias WHERE resposta_id = :resposta_id")
                conn.execute(delete_evidencias, {'resposta_id': resposta_id})
                
                # Depois, inserir as novas evidências
                for pergunta_index, lista_arquivos in arquivos.items():
                    for arquivo in lista_arquivos:
                        # Converter Base64 para bytes
                        conteudo_base64 = arquivo['conteudo']
                        if ',' in conteudo_base64:
                            conteudo_base64 = conteudo_base64.split(',')[1]
                        conteudo_bytes = base64.b64decode(conteudo_base64)
                        
                        insert_evidencia = text("""
                            INSERT INTO checklist_evidencias (resposta_id, pergunta_numero, nome_arquivo, tipo_arquivo, conteudo, tamanho_bytes)
                            VALUES (:resposta_id, :pergunta_numero, :nome_arquivo, :tipo_arquivo, :conteudo, :tamanho)
                        """)
                        conn.execute(insert_evidencia, {
                            'resposta_id': resposta_id,
                            'pergunta_numero': int(pergunta_index) + 1,
                            'nome_arquivo': arquivo['nome'],
                            'tipo_arquivo': arquivo['tipo'],
                            'conteudo': conteudo_bytes,
                            'tamanho': len(conteudo_bytes)
                        })
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Respostas salvas com sucesso',
                'id': resposta_id
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar checklist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/checklist/progresso')
def api_checklist_progresso():
    """Retorna o progresso dos 3 checklists para uma auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    # Configuração dos checklists
    CONFIG = {
        'governanca': {'tabela': 'checklist_governanca_respostas', 'total': 13},
        'riscos': {'tabela': 'checklist_riscos_respostas', 'total': 12},
        'controles': {'tabela': 'checklist_controles_respostas', 'total': 12}
    }
    
    resultado = {}
    
    try:
        with engine.connect() as conn:
            for tipo, config in CONFIG.items():
                tabela = config['tabela']
                total = config['total']
                
                # Buscar registro
                query = text(f"""
                    SELECT id, status, 
                           {', '.join([f'p{i}_resposta' for i in range(1, total + 1)])}
                    FROM {tabela}
                    WHERE auditoria_id = :auditoria_id
                    ORDER BY id DESC
                    LIMIT 1
                """)
                
                registro = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
                
                if not registro:
                    # Nenhum registro - não iniciado
                    resultado[tipo] = {
                        'id': None,
                        'total': total,
                        'respondidas': 0,
                        'status': 'Não iniciado'
                    }
                else:
                    # Contar quantas perguntas têm resposta (não vazia)
                    respondidas = 0
                    # As respostas começam no índice 2 (id=0, status=1, depois as respostas)
                    for i in range(2, 2 + total):
                        if registro[i] and registro[i] != '':
                            respondidas += 1
                    
                    status = registro[1] or 'Em andamento'
                    if respondidas == total and status != 'Concluído':
                        status = 'Em andamento'
                    
                    resultado[tipo] = {
                        'id': registro[0],
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
            query = text("""
                SELECT id_area, nome_area, gestor
                FROM informacoes_area
                WHERE status = 'Ativo'
                ORDER BY nome_area
            """)

            result = conn.execute(query).fetchall()

            areas = []

            for row in result:
                areas.append({
                    'id': row[0],
                    'nome': row[1],
                    'gestor': row[2] or 'Não informado'
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

@app.route('/api/relatorios/gerar-gerencial', methods=['POST'])
def api_relatorios_gerar_gerencial():
    """Gera o relatório gerencial em PDF e retorna diretamente"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    area_id = data.get('area_id')
    auditoria_id = data.get('auditoria_id')
    orientacao = data.get('orientacao', 'RETRATO')
    
    if not area_id or not auditoria_id:
        return jsonify({'success': False, 'error': 'area_id e auditoria_id são obrigatórios'}), 400
    
    from database import engine
    from sqlalchemy import text
    from logic import gerar_relatorio_gerencial_area
    
    try:
        # Buscar nome da área e gestor
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor FROM informacoes_area WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area_info:
                return jsonify({'success': False, 'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0] or 'Área sem nome'
            gestor = area_info[1] or 'Gestor não informado'
        
        # Gerar o PDF
        pdf_bytes = gerar_relatorio_gerencial_area(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            orientacao=orientacao,
            auditoria_id=auditoria_id
        )
        
        # Criar nome do arquivo
        nome_arquivo = f"relatorio_gerencial_{area_nome}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Retornar o PDF diretamente (NÃO salvar na sessão)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorios/gerar-parecer', methods=['POST'])
def api_relatorios_gerar_parecer():
    """Gera o relatório de Parecer da Auditoria para um processo específico"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    print("=" * 50)
    print("🔍 Dados recebidos na rota:")
    print(f"   area_id: {data.get('area_id')}")
    print(f"   auditoria_id: {data.get('auditoria_id')}")
    print(f"   processo_id: {data.get('processo_id')}")
    print(f"   orientacao: {data.get('orientacao')}")
    print("=" * 50)
    
    area_id = data.get('area_id')
    auditoria_id = data.get('auditoria_id')
    processo_id = data.get('processo_id')
    orientacao = data.get('orientacao', 'RETRATO')
    
    if not area_id or not auditoria_id:
        return jsonify({'success': False, 'error': 'area_id e auditoria_id são obrigatórios'}), 400
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório para o parecer'}), 400
    
    from database import engine
    from sqlalchemy import text
    from logic import gerar_relatorio_parecer_auditoria
    
    try:
        # Buscar nome da área e gestor
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor FROM informacoes_area WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area_info:
                return jsonify({'success': False, 'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0] or 'Área sem nome'
            gestor = area_info[1] or 'Gestor não informado'
        
        # Pegar o nome do usuário da sessão
        usuario_nome = session.get('usuario_nome', session.get('usuario_logado', 'Auditor'))
        
        print(f"📊 Área: {area_nome}, Gestor: {gestor}, Usuário: {usuario_nome}")
        print(f"📊 Gerando parecer para processo_id: {processo_id}")
        
        # Gerar o PDF (passando o processo_id)
        pdf_bytes = gerar_relatorio_parecer_auditoria(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            auditoria_id=auditoria_id,
            processo_id=processo_id,
            usuario_nome=usuario_nome,
            orientacao=orientacao
        )
        
        print(f"✅ PDF gerado com sucesso! Tamanho: {len(pdf_bytes)} bytes")
        
        # Criar nome do arquivo
        nome_arquivo = f"parecer_auditoria_processo_{processo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        print(f"❌ Erro ao gerar parecer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

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
    """Retorna todas as análises críticas de uma etapa"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa_id, tipo_analise, categoria,
                       analise_critica, sugestao_melhoria,
                       necessidade_implantacao, ganho_previsto,
                       created_at, updated_at
                FROM analises_criticas
                WHERE etapa_id = :etapa_id
                ORDER BY tipo_analise, categoria
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchall()
            
            analises = []
            for row in result:
                analises.append({
                    'id': row[0],
                    'etapa_id': row[1],
                    'tipo_analise': row[2],
                    'categoria': row[3],
                    'analise_critica': row[4] or '',
                    'sugestao_melhoria': row[5] or '',
                    'necessidade_implantacao': row[6] or '',
                    'ganho_previsto': row[7] or '',
                    'created_at': row[8].isoformat() if row[8] else '',
                    'updated_at': row[9].strftime('%Y-%m-%d %H:%M') if row[9] else ''
                })
            
            return jsonify({'success': True, 'analises': analises})
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise/salvar', methods=['POST'])
def api_analise_salvar():
    """Salva ou atualiza uma análise crítica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('id')
    etapa_id = data.get('etapa_id')
    tipo_analise = data.get('tipo_analise', 'entrevistado')
    categoria = data.get('categoria', 'governanca')
    analise_critica = data.get('analise_critica', '')
    sugestao_melhoria = data.get('sugestao_melhoria', '')
    necessidade_implantacao = data.get('necessidade_implantacao', '')
    ganho_previsto = data.get('ganho_previsto', '')
    
    if not etapa_id:
        return jsonify({'success': False, 'error': 'etapa_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            if analise_id:
                # Atualizar
                query = text("""
                    UPDATE analises_criticas
                    SET tipo_analise = :tipo_analise,
                        categoria = :categoria,
                        analise_critica = :analise_critica,
                        sugestao_melhoria = :sugestao_melhoria,
                        necessidade_implantacao = :necessidade_implantacao,
                        ganho_previsto = :ganho_previsto,
                        updated_at = NOW()
                    WHERE id = :id
                """)
                conn.execute(query, {
                    'id': analise_id,
                    'tipo_analise': tipo_analise,
                    'categoria': categoria,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto
                })
            else:
                # Inserir nova
                query = text("""
                    INSERT INTO analises_criticas
                    (etapa_id, tipo_analise, categoria, analise_critica,
                     sugestao_melhoria, necessidade_implantacao, ganho_previsto)
                    VALUES (:etapa_id, :tipo_analise, :categoria, :analise_critica,
                            :sugestao_melhoria, :necessidade_implantacao, :ganho_previsto)
                    RETURNING id
                """)
                result = conn.execute(query, {
                    'etapa_id': etapa_id,
                    'tipo_analise': tipo_analise,
                    'categoria': categoria,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto
                })
                analise_id = result.fetchone()[0]
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'id': analise_id,
                'message': 'Análise salva com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar análise: {e}")
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

@app.route('/api/auditorias/situacao')
def api_auditorias_situacao():
    """Retorna situação das auditorias: Concluídas, Em Execução, Fora do Prazo
    Suporta filtro por área (area_id) e por auditoria específica (auditoria_id)
    """
    from database import engine
    from sqlalchemy import text
    from datetime import date
    
    try:
        area_id = request.args.get('area_id')
        auditoria_id = request.args.get('auditoria_id')  # ⭐ NOVO: suporte a auditoria única
        
        with engine.connect() as conn:
            hoje = date.today()
            
            # CASO 1: Auditoria específica (mais específico)
            if auditoria_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) as concluidas,
                        SUM(CASE WHEN status = 'Em Execução' AND data_fim >= :hoje THEN 1 ELSE 0 END) as em_execucao,
                        SUM(CASE WHEN status = 'Em Execução' AND data_fim < :hoje THEN 1 ELSE 0 END) as fora_prazo,
                        SUM(CASE WHEN status = 'Planejamento' THEN 1 ELSE 0 END) as planejamento
                    FROM auditorias
                    WHERE id = :auditoria_id
                """)
                result = conn.execute(query, {
                    'hoje': hoje,
                    'auditoria_id': auditoria_id
                }).fetchone()
            
            # CASO 2: Área específica
            elif area_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) as concluidas,
                        SUM(CASE WHEN status = 'Em Execução' AND data_fim >= :hoje THEN 1 ELSE 0 END) as em_execucao,
                        SUM(CASE WHEN status = 'Em Execução' AND data_fim < :hoje THEN 1 ELSE 0 END) as fora_prazo,
                        SUM(CASE WHEN status = 'Planejamento' THEN 1 ELSE 0 END) as planejamento
                    FROM auditorias
                    WHERE id_area = :area_id
                """)
                result = conn.execute(query, {
                    'hoje': hoje,
                    'area_id': area_id
                }).fetchone()
            
            # CASO 3: Nenhum filtro - todas as auditorias
            else:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) as concluidas,
                        SUM(CASE WHEN status = 'Em Execução' AND data_fim >= :hoje THEN 1 ELSE 0 END) as em_execucao,
                        SUM(CASE WHEN status = 'Em Execução' AND data_fim < :hoje THEN 1 ELSE 0 END) as fora_prazo,
                        SUM(CASE WHEN status = 'Planejamento' THEN 1 ELSE 0 END) as planejamento
                    FROM auditorias
                """)
                result = conn.execute(query, {'hoje': hoje}).fetchone()
            
            return jsonify({
                'success': True,
                'concluidas': result[0] or 0,
                'em_execucao': result[1] or 0,
                'fora_prazo': result[2] or 0,
                'planejamento': result[3] or 0
            })
            
    except Exception as e:
        print(f"❌ Erro em /api/auditorias/situacao: {e}")
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