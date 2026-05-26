"""
Arquivo principal para aplicação Flask
Sistema de Auditoria Interna - FUSVE
"""

import os
from datetime import datetime, timedelta, date
import json
import io

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
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

@app.route('/historico')
def historico():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('historico.html')

@app.route('/api/processo/<int:processo_id>/etapas')
def api_processo_etapas(processo_id):
    """Retorna todas as etapas de um processo"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, codigo_etapa, nome_etapa, descricao_etapa,
                       como_e_feito, objetivo_etapa, status_etapa, criticidade_etapa,
                       politica_interna, analise_critica, sugestao_melhoria,
                       necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                       executores_etapa,
                       diagrama_nome, manual_nome, created_at
                FROM etapas_processo
                WHERE processo_id = :processo_id
                ORDER BY codigo_etapa
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
                    'diagrama_nome': row[15] or '',
                    'manual_nome': row[16] or '',
                    'created_at': row[17].isoformat() if row[17] else ''
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
                        frequencia_evidencia, created_at, updated_at
                    ) VALUES (
                        :risco_id, :auditoria_id, :nome_controle,
                        :como_executado, :objetivo_controle,
                        :periodicidade_execucao, :natureza, :forma_execucao,
                        :status_controle, :evidencia_realizacao,
                        :responsaveis_tratamento, :risco_avaliacao, :causa_motivo,
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
                       frequencia_evidencia
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
                'frequencia_evidencia': result[13] or ''
            }
            
            return jsonify({'success': True, 'controle': controle})
            
    except Exception as e:
        print(f"❌ Erro ao buscar controle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
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
    """Salva ou atualiza as informações básicas do processo"""
    from database import engine
    from sqlalchemy import text
    from logic import gerar_codigo_processo
    
    data = request.json
    print(f"📥 Dados recebidos em salvar-basico: {data}")
    print(f"🔍 processo_id recebido: {data.get('processo_id')}")  # ← ADICIONE ESTA LINHA
    
    # ===== DADOS RECEBIDOS DO FRONTEND =====
    processo_id = data.get('processo_id')           # ← Se veio, é edição
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
                        updated_at = NOW()
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
                print(f"✅ Processo {processo_id} atualizado com sucesso!")
                
            else:
                # ===== CASO 2: NOVO PROCESSO - Vamos CRIAR =====
                print(f"➕ Criando novo processo: {nome_processo}")
                
                # Verificar se já existe outro com mesmo nome na área
                check_query = text("""
                    SELECT id FROM processos 
                    WHERE nome_processo = :nome AND id_area = :id_area
                """)
                existing = conn.execute(check_query, {
                    'nome': nome_processo,
                    'id_area': id_area
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
                            updated_at = NOW()
                        WHERE id = :id
                    """)
                    conn.execute(update_query, {
                        'nome': nome_processo,
                        'codigo': codigo_processo,
                        'area': nome_area,
                        'id': processo_id
                    })
                else:
                    # Realmente novo: gerar código e inserir
                    if not codigo_processo:
                        codigo_processo = gerar_codigo_processo(id_area)
                    
                    insert_query = text("""
                        INSERT INTO processos (nome_processo, codigo_processo, id_area, area, created_at, updated_at)
                        VALUES (:nome, :codigo, :id_area, :area, NOW(), NOW())
                        RETURNING id
                    """)
                    result = conn.execute(insert_query, {
                        'nome': nome_processo,
                        'codigo': codigo_processo,
                        'id_area': id_area,
                        'area': nome_area
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
            
            # ===== VINCULAR À AUDITORIA =====
            if auditoria_id:
                print(f"🔗 Vinculando processo {processo_id} à auditoria {auditoria_id}")
                
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
                    print(f"✅ Vinculado com sucesso!")
                else:
                    print(f"ℹ️ Processo já vinculado a esta auditoria")
            
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
    """Retorna os riscos de um processo para cálculo do score máximo"""
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, processo_id, nome_risco, fator_risco, melhoria,
                    impacto, probabilidade, apetite_risco, motivo_risco,
                    validacao_gerencia, validacao_superintendencia, relatorio_gerado,
                    created_at, score_risco, categoria, causas,
                    tratamento_risco, descricao_tratamento, prazo_implantacao
                FROM riscos
                WHERE processo_id = :processo_id
            """)
            result = conn.execute(query, {'processo_id': processo_id}).fetchall()
            
            riscos = []
            for row in result:
                categorias = row[14].split(',') if row[14] else []      # categoria
                causas = row[15].split(',') if row[15] else []          # causas
                
                riscos.append({
                    'id': row[0],
                    'nome_risco': row[2] or '',                         # ← índice 2
                    'fator_risco': row[3] or '',
                    'melhoria': row[4] or '',
                    'apetite_risco': row[7] or '',
                    'impacto': row[5] or 'Médio',
                    'probabilidade': row[6] or 'Médio',
                    'motivo_risco': row[8] or '',
                    'categorias': [c.strip() for c in categorias if c.strip()],
                    'categoria_causa': [c.strip() for c in causas if c.strip()],
                    'score_risco': row[13] or 0,
                    'como_tratar': row[16] or '',                       # tratamento_risco
                    'desc_tratamento': row[17] or '',                   # descricao_tratamento
                    'prazo_implantacao': row[18].strftime('%Y-%m-%d') if row[18] else ''  # ← índice 18
                })
            
            return jsonify({'success': True, 'riscos': riscos})
            
    except Exception as e:
        print(f"❌ Erro ao buscar riscos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/dados')
def api_processo_dados(processo_id):
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            # ===== 1. BUSCAR DADOS BÁSICOS DO PROCESSO =====
            query = text("""
                SELECT p.id, p.nome_processo, p.codigo_processo, p.id_area,
                       p.descricao, p.etapa_ini, p.etapa_fim, p.produto, p.objetivo,
                       i.nome_area
                FROM processos p
                JOIN informacoes_area i ON p.id_area = i.id_area
                WHERE p.id = :processo_id
            """)
            processo = conn.execute(query, {'processo_id': processo_id}).fetchone()
            
            if not processo:
                return jsonify({'success': False, 'error': 'Processo não encontrado'}), 404
            
            # ===== 2. BUSCAR A AUDITORIA VINCULADA AO PROCESSO =====
            query_auditoria = text("""
                SELECT ap.auditoria_id
                FROM auditoria_processos ap
                WHERE ap.processo_id = :processo_id
                LIMIT 1
            """)
            auditoria_result = conn.execute(query_auditoria, {'processo_id': processo_id}).fetchone()
            auditoria_id = auditoria_result[0] if auditoria_result else None
            
            # ===== 3. BUSCAR EXECUTORES =====
            query_exec = text("""
                SELECT f.id, f.nome_funcionario, f.cargo
                FROM processo_executores pe
                JOIN funcionarios_area f ON pe.funcionario_id = f.id
                WHERE pe.processo_id = :processo_id
            """)
            executores = conn.execute(query_exec, {'processo_id': processo_id}).fetchall()
            
            # ===== 4. BUSCAR RISCOS =====
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
            
            # ===== 5. RETORNAR TODOS OS DADOS =====
            return jsonify({
                'success': True,
                'nome_processo': processo[1],
                'codigo_processo': processo[2],
                'id_area': processo[3],
                'nome_area': processo[9],
                'auditoria_id': auditoria_id,
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
                categoria_causa = risco.get('categoria_causa', [])
                causas_str = ', '.join(categoria_causa) if categoria_causa else None
                
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
                    'prazo_implantacao': risco.get('prazo_implantacao', '')
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
            # Ordenação correta: converte a parte após o ponto para inteiro
            query = text("""
                SELECT p.id, p.codigo_processo, p.nome_processo, p.objetivo
                FROM processos p
                JOIN auditoria_processos ap ON p.id = ap.processo_id
                WHERE ap.auditoria_id = :auditoria_id
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
    doc_legal = data.get('doc_legal', '')
    financeiro = data.get('financeiro', False)
    info_adicional = data.get('info_adicional', '')

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
                        doc_legal = :doc_legal,
                        financeiro = :financeiro,
                        info_adicional = :info_adicional,
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
                    'doc_legal': doc_legal,
                    'financeiro': financeiro,
                    'info_adicional': info_adicional
                })

                print(f"✏️ Risco de etapa {risco_id} atualizado!")
            
            else:
                # NOVO RISCO: inserir risco
                query = text("""
                    INSERT INTO riscos_etapa (
                        etapa_id, auditoria_id, nome_risco, categoria,
                        fator_risco, consequencia, impacto, probabilidade,
                        magnitude, apetite, tratamento, origem,
                        doc_legal, financeiro, info_adicional, ativo, created_at
                    ) VALUES (
                        :etapa_id, :auditoria_id, :nome_risco, :categoria,
                        :fator_risco, :consequencia, :impacto, :probabilidade,
                        :magnitude, :apetite, :tratamento, :origem,
                        :doc_legal, :financeiro, :info_adicional, true, NOW()
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
                    'doc_legal': doc_legal,
                    'financeiro': financeiro,
                    'info_adicional': info_adicional
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
                       apetite, tratamento, origem, doc_legal, financeiro,
                       info_adicional, ativo
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
                'doc_legal': result[12] or '',
                'financeiro': result[13] or False,
                'info_adicional': result[14] or '',
                'ativo': result[15] if result[15] is not None else True
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
                       origem, doc_legal, financeiro, info_adicional, ativo
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
                    'doc_legal': row[11] or '',
                    'financeiro': row[12] or False,
                    'info_adicional': row[13] or '',
                    'ativo': row[14] if row[14] is not None else True
                })

            return jsonify({'success': True, 'riscos': riscos})
    
    except Exception as e:
        print(f"❌ Erro ao buscar riscos da etapa: {e}")
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
                       manual_etapa, manual_nome, manual_tipo
                FROM etapas_processo
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            # CORRIGIDO: Os índices agora estão corretos
            # Índices: 0-14 = campos text, 15 = executores_etapa, 
            # 16 = diagrama_bpmn, 17 = diagrama_nome, 18 = diagrama_tipo,
            # 19 = manual_etapa, 20 = manual_nome, 21 = manual_tipo
            
            # Converter diagrama (índice 16) se existir
            diagrama_base64 = None
            if result[16]:  # ← CORRIGIDO: era 15, agora é 16
                diagrama_base64 = base64.b64encode(result[16]).decode('utf-8')
            
            # Converter manual (índice 19) se existir
            manual_base64 = None
            if result[19]:  # ← CORRIGIDO: era 18, agora é 19
                manual_base64 = base64.b64encode(result[19]).decode('utf-8')
            
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
                'executores_etapa': result[15] or '',  # ← OK
                'diagrama_base64': diagrama_base64,
                'diagrama_nome': result[17] or '',  # ← CORRIGIDO: era 16, agora é 17
                'diagrama_tipo': result[18] or '',  # ← CORRIGIDO: era 17, agora é 18
                'manual_base64': manual_base64,
                'manual_nome': result[20] or '',  # ← CORRIGIDO: era 19, agora é 20
                'manual_tipo': result[21] or ''   # ← CORRIGIDO: era 20, agora é 21
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
                
                print(f"✏️ Etapa {etapa_id} atualizada com sucesso!")
                
            else:
                # ========== NOVO: inserir etapa ==========
                
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
                        NOW()
                    )
                    RETURNING id
                """)
                
                result = conn.execute(query, {
                    'processo_id': processo_id,
                    'auditoria_id': auditoria_id,
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
                    'manual_tipo': manual_tipo
                })
                
                novo_id = result.fetchone()[0]
                print(f"✅ Nova etapa criada! ID: {novo_id}, Código: {codigo_etapa}")
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Etapa salva com sucesso',
                'codigo_etapa': codigo_etapa
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar etapa: {e}")
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
                       risco_avaliacao, causa_motivo, created_at, updated_at
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
                    'created_at': row[12].isoformat() if row[12] else '',
                    'updated_at': row[13].strftime('%Y-%m-%d') if row[13] else ''
                })
            
            return jsonify({'success': True, 'controles': controles})
            
    except Exception as e:
        print(f"❌ Erro ao buscar controles do risco: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# COMUNICAÇÃO DOS RESULTADOS
# ============================================================

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
        'governanca': {'tabela': 'checklist_governanca_respostas', 'total': 14},
        'riscos': {'tabela': 'checklist_riscos_respostas', 'total': 11},
        'controles': {'tabela': 'checklist_controles_respostas', 'total': 11}
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
        'governanca': {'tabela': 'checklist_governanca_respostas', 'total': 14},
        'riscos': {'tabela': 'checklist_riscos_respostas', 'total': 11},
        'controles': {'tabela': 'checklist_controles_respostas', 'total': 11}
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
                SELECT id, codigo_auditoria, titulo, ano, trimestre
                FROM auditorias
                WHERE id_area = :area_id
                ORDER BY ano DESC, trimestre DESC
            """)

            result = conn.execute(query, {'area_id': area_id}).fetchall()

            auditorias = []
            for row in result:
                auditorias.append({
                    'id': row[0],
                    'codigo': row[1],
                    'titulo': row[2],
                    'ano': row[3],
                    'trimestre': row[4]
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