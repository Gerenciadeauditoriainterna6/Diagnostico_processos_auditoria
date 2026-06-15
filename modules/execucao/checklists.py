"""
Módulo de Checklist de Governança
"""
# ===== MIGRAÇÃO PARA FLASK =====
# Streamlit removido - sistema agora usa Flask
# import streamlit as st  # REMOVIDO

# Placeholder para evitar erros (as funções Streamlit não serão chamadas no Flask)
class _DummyStreamlit:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

st = _DummyStreamlit()
import pandas as pd
from datetime import datetime
import time as time_module
from sqlalchemy import text
from database import engine
from logic import buscar_auditoria_por_id, buscar_processo_por_codigo
from modules.shared.log_sistema import registrar_log

def buscar_perguntas_checklist(tipo_checklist='governanca'):
    """Busca perguntas do checklist por tipo
    
    Tipos disponíveis:
    - 'governanca': Checklist de Eficácia de Governança (processos mapeados)
    - 'riscos': Checklist de Avaliação de Riscos
    - 'controles': Checklist de Avaliação de Controles
    """
    query = text("""
        SELECT id, pergunta, tipo_resposta, ordem
        FROM checklist_perguntas_padrao
        WHERE ativo = TRUE AND tipo_checklist = :tipo
        ORDER BY ordem
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"tipo": tipo_checklist})

def salvar_resposta_checklist(checklist_id, pergunta_id, resposta, nota=None, comentario=None):
    """Salva ou atualiza uma resposta do checklist"""
    # Primeiro, verificar se já existe
    query_check = text("""
        SELECT id FROM checklist_respostas
        WHERE checklist_id = :checklist_id AND pergunta_id = :pergunta_id
    """)
    with engine.connect() as conn:
        existing = conn.execute(query_check, {
            "checklist_id": checklist_id,
            "pergunta_id": pergunta_id
        }).fetchone()
    
    # Buscar informações da pergunta para o log
    with engine.connect() as conn:
        pergunta_info = conn.execute(
            text("SELECT pergunta FROM checklist_perguntas_padrao WHERE id = :id"),
            {"id": pergunta_id}
        ).scalar()
    
    if existing:
        # Buscar dados ANTIGOS antes do UPDATE
        with engine.connect() as conn:
            dados_antigos = conn.execute(
                text("SELECT * FROM checklist_respostas WHERE id = :id"),
                {"id": existing[0]}
            ).mappings().fetchone()
        
        # Atualizar existente
        query_update = text("""
            UPDATE checklist_respostas 
            SET resposta = :resposta, nota = :nota, comentario = :comentario, data_resposta = NOW()
            WHERE checklist_id = :checklist_id AND pergunta_id = :pergunta_id
            RETURNING id
        """)
        with engine.begin() as conn:
            result = conn.execute(query_update, {
                "checklist_id": checklist_id,
                "pergunta_id": pergunta_id,
                "resposta": resposta,
                "nota": nota,
                "comentario": comentario
            }).scalar()
            
            # ===== LOG DO UPDATE =====
            dados_novos = {
                'id': result,
                'checklist_id': checklist_id,
                'pergunta_id': pergunta_id,
                'pergunta': pergunta_info[:100] if pergunta_info else None,
                'resposta': resposta,
                'nota': nota,
                'comentario': comentario[:100] if comentario else None
            }
            
            registrar_log(
                tabela='checklist_respostas',
                registro_id=result,
                operacao='UPDATE',
                dados_anteriores=dict(dados_antigos) if dados_antigos else None,
                dados_novos=dados_novos
            )
            # ===== FIM DO LOG =====
    else:
        # Inserir novo
        query_insert = text("""
            INSERT INTO checklist_respostas (checklist_id, pergunta_id, resposta, nota, comentario, data_resposta)
            VALUES (:checklist_id, :pergunta_id, :resposta, :nota, :comentario, NOW())
            RETURNING id
        """)
        with engine.begin() as conn:
            result = conn.execute(query_insert, {
                "checklist_id": checklist_id,
                "pergunta_id": pergunta_id,
                "resposta": resposta,
                "nota": nota,
                "comentario": comentario
            }).scalar()
            
            # ===== LOG DO INSERT =====
            dados_novos = {
                'id': result,
                'checklist_id': checklist_id,
                'pergunta_id': pergunta_id,
                'pergunta': pergunta_info[:100] if pergunta_info else None,
                'resposta': resposta,
                'nota': nota,
                'comentario': comentario[:100] if comentario else None
            }
            
            registrar_log(
                tabela='checklist_respostas',
                registro_id=result,
                operacao='INSERT',
                dados_anteriores=None,
                dados_novos=dados_novos
            )
            # ===== FIM DO LOG =====
    
    # Após salvar a resposta, atualizar o status da avaliação para "Em Andamento"
    if result:
        try:
            # Buscar o processo_id e auditoria_id pelo checklist_id
            query_info = text("""
                SELECT processo_id, auditoria_id 
                FROM checklist_sessoes 
                WHERE id = :checklist_id
            """)
            with engine.begin() as conn:
                info = conn.execute(query_info, {"checklist_id": checklist_id}).fetchone()
                
                if info:
                    processo_id, auditoria_id = info
                    
                    # Verificar se o status atual não é já "Avaliado"
                    query_check_status = text("""
                        SELECT status_avaliacao 
                        FROM auditoria_processos 
                        WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id
                    """)
                    status_atual = conn.execute(query_check_status, {
                        "processo_id": processo_id,
                        "auditoria_id": auditoria_id
                    }).fetchone()
                    
                    # Só atualizar se não estiver já "Avaliado"
                    if status_atual and status_atual[0] != 'Avaliado':
                        # Buscar dados ANTIGOS do status
                        dados_antigos_status = conn.execute(
                            text("SELECT status_avaliacao FROM auditoria_processos WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id"),
                            {"processo_id": processo_id, "auditoria_id": auditoria_id}
                        ).mappings().fetchone()
                        
                        # Atualizar status para "Em Andamento"
                        query_update_status = text("""
                            UPDATE auditoria_processos 
                            SET status_avaliacao = 'Em Andamento'
                            WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id
                            RETURNING id
                        """)
                        result_status = conn.execute(query_update_status, {
                            "processo_id": processo_id,
                            "auditoria_id": auditoria_id
                        }).scalar()
                        
                        # ===== LOG DO UPDATE DE STATUS =====
                        registrar_log(
                            tabela='auditoria_processos',
                            registro_id=result_status,
                            operacao='UPDATE',
                            dados_anteriores=dict(dados_antigos_status) if dados_antigos_status else None,
                            dados_novos={'status_avaliacao': 'Em Andamento'}
                        )
                        # ===== FIM DO LOG =====
        except Exception as e:
            print(f"Erro ao atualizar status: {e}")
    
    return result


def salvar_evidencia(resposta_id, arquivo):
    """Salva uma evidência anexada diretamente no banco de dados"""
    if arquivo is not None:
        # Ler o conteúdo binário do arquivo
        conteudo = arquivo.read()
        
        query = text("""
            INSERT INTO checklist_evidencias (resposta_id, nome_arquivo, tipo_arquivo, conteudo, tamanho_bytes, data_upload)
            VALUES (:resposta_id, :nome_arquivo, :tipo_arquivo, :conteudo, :tamanho_bytes, NOW())
        """)
        with engine.begin() as conn:
            conn.execute(query, {
                "resposta_id": resposta_id,
                "nome_arquivo": arquivo.name,
                "tipo_arquivo": arquivo.type,
                "conteudo": conteudo,
                "tamanho_bytes": len(conteudo)
            })
        return True
    return False

def criar_checklist_sessao(processo_id, auditoria_id, auditor_nome):
    """Cria um novo checklist para o processo se não existir"""
    # Primeiro, verificar se já existe
    query_check = text("""
        SELECT id FROM checklist_sessoes
        WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id
    """)
    with engine.connect() as conn:
        result = conn.execute(query_check, {
            "processo_id": processo_id,
            "auditoria_id": auditoria_id
        }).fetchone()
    
    if result:
        return result[0]
    
    # Buscar informações do processo e auditoria para o log
    with engine.connect() as conn:
        processo_info = conn.execute(
            text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
            {"id": processo_id}
        ).mappings().fetchone()
        
        auditoria_info = conn.execute(
            text("SELECT codigo_auditoria, titulo FROM auditorias WHERE id = :id"),
            {"id": auditoria_id}
        ).mappings().fetchone()
    
    # Se não existe, criar
    query_insert = text("""
        INSERT INTO checklist_sessoes (processo_id, auditoria_id, auditor_nome, data_inicio, status)
        VALUES (:processo_id, :auditoria_id, :auditor_nome, NOW(), 'Em Andamento')
        RETURNING id
    """)
    with engine.begin() as conn:
        result = conn.execute(query_insert, {
            "processo_id": processo_id,
            "auditoria_id": auditoria_id,
            "auditor_nome": auditor_nome
        }).scalar()
        
        # ===== ADICIONAR LOG AQUI =====
        dados_inseridos = {
            'id': result,
            'processo_id': processo_id,
            'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
            'processo_nome': processo_info['nome_processo'] if processo_info else None,
            'auditoria_id': auditoria_id,
            'auditoria_codigo': auditoria_info['codigo_auditoria'] if auditoria_info else None,
            'auditoria_titulo': auditoria_info['titulo'] if auditoria_info else None,
            'auditor_nome': auditor_nome,
            'status': 'Em Andamento'
        }
        
        registrar_log(
            tabela='checklist_sessoes',
            registro_id=result,
            operacao='INSERT',
            dados_anteriores=None,
            dados_novos=dados_inseridos
        )
        # ===== FIM DO LOG =====
        
    return result


def buscar_respostas_existentes(checklist_id):
    """Busca respostas já salvas para este checklist"""
    query = text("""
        SELECT pergunta_id, resposta, nota, comentario
        FROM checklist_respostas
        WHERE checklist_id = :checklist_id
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"checklist_id": checklist_id})
        if not df.empty:
            return dict(zip(df['pergunta_id'], df.to_dict('records')))
    return {}


def tela_checklist_sessoes():
    """Tela para preenchimento do checklist de governança"""
    
    # Verificar se veio de um processo
    if 'processo_checklist' not in st.session_state:
        st.error("Nenhum processo selecionado.")
        if st.button("← Voltar"):
            st.session_state.pop('processo_checklist', None)
            st.session_state.pop('tela_checklist', None)
            st.rerun()
        return
    
    processo_id = st.session_state['processo_checklist']
    auditoria_id = st.session_state.get('auditoria_checklist')
    auditor_nome = st.session_state.get('usuario_logado', 'Auditor')
    
    # Buscar dados do processo
    query = text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id")
    with engine.connect() as conn:
        processo = conn.execute(query, {"id": processo_id}).fetchone()
    
    if not processo:
        st.error("Processo não encontrado.")
        return
    
    codigo_processo, nome_processo = processo
    
    # Criar ou buscar checklist
    checklist_id = criar_checklist_sessao(processo_id, auditoria_id, auditor_nome)
    
    # Buscar perguntas
    df_perguntas = buscar_perguntas_checklist()
    
    # Buscar respostas já salvas
    respostas_existentes = buscar_respostas_existentes(checklist_id)
    
    # Cabeçalho
    st.title(f"📋 Checklist de Governança")
    st.caption(f"Processo: **{codigo_processo} - {nome_processo}**")
    st.caption(f"Avaliador: {auditor_nome}")
    
    st.divider()
    
    # Formulário do checklist
    with st.form(key=f"form_checklist_{checklist_id}"):
        respostas = {}
        evidencias = {}
        comentarios = {}
        
        for _, pergunta in df_perguntas.iterrows():
            pergunta_id = pergunta['id']
            pergunta_texto = pergunta['pergunta']
            tipo = pergunta['tipo_resposta']
            
            # Buscar resposta existente
            valor_existente = None
            comentario_existente = None
            if pergunta_id in respostas_existentes:
                valor_existente = respostas_existentes[pergunta_id].get('resposta')
                comentario_existente = respostas_existentes[pergunta_id].get('comentario')
            
            with st.container(border=True):
                st.markdown(f"**{pergunta_texto}**")
                
                if tipo == 'sim_nao':
                    opcoes = ["Sim", "Não", "Não se aplica"]
                    idx = opcoes.index(valor_existente) if valor_existente in opcoes else 0
                    respostas[pergunta_id] = st.radio(
                        "Resposta:",
                        opcoes,
                        index=idx,
                        key=f"resp_{pergunta_id}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                
                elif tipo == 'arquivo':
                    st.caption("📎 Anexe as evidências deste processo")
                    evidencias[pergunta_id] = st.file_uploader(
                        "Anexar arquivo",
                        type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'docx', 'txt'],
                        key=f"file_{pergunta_id}",
                        label_visibility="collapsed"
                    )
                    # Se já tem evidência, mostrar
                    if valor_existente:
                        st.success(f"✅ Já possui evidência anexada")
                
                elif tipo == 'texto':
                    respostas[pergunta_id] = st.text_area(
                        "Resposta:",
                        value=valor_existente if valor_existente else "",
                        key=f"text_{pergunta_id}",
                        label_visibility="collapsed"
                    )
                
                elif tipo == 'nota_1_5':
                    respostas[pergunta_id] = st.slider(
                        "Nota (1 a 5):",
                        1, 5, 
                        value=int(valor_existente) if valor_existente and valor_existente.isdigit() else 3,
                        key=f"nota_{pergunta_id}"
                    )
                
                # Campo de comentário para todas as perguntas
                comentarios[pergunta_id] = st.text_area(
                    "Observações / Comentários:",
                    value=comentario_existente if comentario_existente else "",
                    key=f"coment_{pergunta_id}",
                    placeholder="Adicione observações sobre esta avaliação..."
                )
        
        st.divider()
        
        # Botões de ação
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("💾 Salvar Respostas", type="primary", use_container_width=True)
        with col2:
            finalizar = st.form_submit_button("✅ Finalizar Checklist", use_container_width=True)
        with col3:
            if st.form_submit_button("← Voltar", use_container_width=True):
                st.session_state.pop('processo_checklist', None)
                st.session_state.pop('tela_checklist', None)
                st.rerun()
        
        if submitted:
            for pergunta_id, resposta in respostas.items():
                salvar_resposta_checklist(
                    checklist_id, 
                    pergunta_id, 
                    resposta,
                    comentario=comentarios.get(pergunta_id)
                )
            
            # Salvar evidências
            for pergunta_id, arquivo in evidencias.items():
                if arquivo is not None:
                    # Primeiro, garantir que a resposta existe
                    resposta_id = salvar_resposta_checklist(checklist_id, pergunta_id, f"Arquivo: {arquivo.name}")
                    if resposta_id:
                        salvar_evidencia(resposta_id, arquivo)
            
            st.success("✅ Respostas salvas com sucesso!")
            st.rerun()
        
        if finalizar:
            # Buscar dados ANTIGOS do checklist antes de atualizar
            with engine.connect() as conn:
                dados_antigos = conn.execute(
                    text("""
                        SELECT id, processo_id, auditoria_id, status, data_conclusao, 
                               tipo_checklist, auditor_nome
                        FROM checklist_sessoes 
                        WHERE id = :checklist_id
                    """),
                    {"checklist_id": checklist_id}
                ).mappings().fetchone()
                
                # Buscar informações do processo para contexto
                processo_info = conn.execute(
                    text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
                    {"id": dados_antigos['processo_id'] if dados_antigos else None}
                ).mappings().fetchone()
            
            # Marcar checklist como concluído
            query = text("""
                UPDATE checklist_sessoes 
                SET status = 'Concluído', data_conclusao = NOW()
                WHERE id = :checklist_id
                RETURNING id
            """)
            
            with engine.begin() as conn:
                result = conn.execute(query, {"checklist_id": checklist_id}).scalar()
                
                # ===== ADICIONAR LOG AQUI =====
                dados_novos = {
                    'id': checklist_id,
                    'processo_id': dados_antigos['processo_id'] if dados_antigos else None,
                    'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                    'processo_nome': processo_info['nome_processo'] if processo_info else None,
                    'auditoria_id': dados_antigos['auditoria_id'] if dados_antigos else None,
                    'tipo_checklist': dados_antigos['tipo_checklist'] if dados_antigos else None,
                    'auditor_nome': dados_antigos['auditor_nome'] if dados_antigos else None,
                    'status_anterior': dados_antigos['status'] if dados_antigos else None,
                    'status_novo': 'Concluído',
                    'data_conclusao': 'NOW()'
                }
                
                dados_antigos_resumidos = {
                    'id': checklist_id,
                    'processo_id': dados_antigos['processo_id'] if dados_antigos else None,
                    'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                    'processo_nome': processo_info['nome_processo'] if processo_info else None,
                    'status': dados_antigos['status'] if dados_antigos else None,
                    'data_conclusao': str(dados_antigos['data_conclusao']) if dados_antigos and dados_antigos['data_conclusao'] else None
                }
                
                registrar_log(
                    tabela='checklist_sessoes',
                    registro_id=checklist_id,
                    operacao='UPDATE',
                    dados_anteriores=dados_antigos_resumidos,
                    dados_novos=dados_novos
                )
                # ===== FIM DO LOG =====
            
            st.success("✅ Checklist finalizado com sucesso!")
            st.balloons()
            time_module.sleep(2)
            st.session_state.pop('processo_checklist', None)
            st.session_state.pop('tela_checklist', None)
            st.rerun()

def listar_evidencias_por_resposta(resposta_id):
    """Lista todas as evidências de uma resposta"""
    query = text("""
        SELECT id, nome_arquivo, tipo_arquivo, tamanho_bytes, data_upload
        FROM checklist_evidencias
        WHERE resposta_id = :resposta_id
        ORDER BY data_upload DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"resposta_id": resposta_id})
    
def baixar_evidencia(evidencia_id):
    """Recupera o arquivo da evidência para download"""
    query = text("""
        SELECT encode(conteudo, 'base64'), nome_arquivo, tipo_arquivo
        FROM checklist_evidencias
        WHERE id = :evidencia_id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"evidencia_id": evidencia_id}).fetchone()
        if result:
            import base64
            conteudo_base64 = result[0]
            if conteudo_base64:
                conteudo = base64.b64decode(conteudo_base64)
                return conteudo, result[1], result[2]
    return None, None, None

from modules.shared.log_sistema import registrar_log  # Adicione no topo

def criar_checklist_sessao_por_tipo(processo_id, auditoria_id, auditoria_nome, tipo_checklist='governanca'):
    """Cria um novo checklist para o processo se não existir, por tipo"""
    # Primeiro, verificar se já existe
    query_check = text("""
        SELECT id FROM checklist_sessoes
        WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id AND tipo_checklist = :tipo
    """)
    with engine.connect() as conn:
        result = conn.execute(query_check, {
            "processo_id": processo_id,
            "auditoria_id": auditoria_id,
            "tipo": tipo_checklist
        }).fetchone()

    if result:
        return result[0]
    
    # Buscar informações do processo e auditoria para o log
    with engine.connect() as conn:
        processo_info = conn.execute(
            text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
            {"id": processo_id}
        ).mappings().fetchone()
        
        auditoria_info = conn.execute(
            text("SELECT codigo_auditoria, titulo FROM auditorias WHERE id = :id"),
            {"id": auditoria_id}
        ).mappings().fetchone()
    
    # Se não existir, criar
    query_insert = text("""
        INSERT INTO checklist_sessoes (processo_id, auditoria_id, auditor_nome, tipo_checklist, data_inicio, status)
        VALUES (:processo_id, :auditoria_id, :auditor_nome, :tipo, NOW(), 'Em Andamento')
        RETURNING id
    """)
    with engine.begin() as conn:
        result = conn.execute(query_insert, {
            "processo_id": processo_id,
            "auditoria_id": auditoria_id,
            "auditor_nome": auditoria_nome,
            "tipo": tipo_checklist
        }).scalar()
        
        # ===== ADICIONAR LOG AQUI =====
        dados_inseridos = {
            'id': result,
            'processo_id': processo_id,
            'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
            'processo_nome': processo_info['nome_processo'] if processo_info else None,
            'auditoria_id': auditoria_id,
            'auditoria_codigo': auditoria_info['codigo_auditoria'] if auditoria_info else None,
            'auditoria_titulo': auditoria_info['titulo'] if auditoria_info else None,
            'auditor_nome': auditoria_nome,
            'tipo_checklist': tipo_checklist,
            'status': 'Em Andamento'
        }
        
        registrar_log(
            tabela='checklist_sessoes',
            registro_id=result,
            operacao='INSERT',
            dados_anteriores=None,
            dados_novos=dados_inseridos
        )
        # ===== FIM DO LOG =====
    
    return result

def buscar_status_checklist_por_tipo(processo_id, auditoria_id, tipo_checklist='governanca'):
    """Busca o status de um checklist específico por tipo"""
    query = text("""
        SELECT status, id FROM checklist_sessoes
        WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id AND tipo_checklist = :tipo
        ORDER BY id DESC LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {
            'processo_id': processo_id,
            'auditoria_id': auditoria_id,
            'tipo': tipo_checklist
        }).fetchone()

    if result:
        return result[0], result[1]
    return "Não iniciado", None

def finalizar_checklist_por_tipo(checklist_id, processo_id, auditoria_id, tipo_checklist='governanca'):
    """Finaliza um checklist e atualiza o status da avaliação se for do tipo governanca"""
    
    try:
        # ===== 1. BUSCAR DADOS ANTIGOS DO CHECKLIST =====
        with engine.connect() as conn:
            dados_antigos_checklist = conn.execute(
                text("""
                    SELECT id, processo_id, auditoria_id, status, data_conclusao, 
                           tipo_checklist, auditor_nome
                    FROM checklist_sessoes 
                    WHERE id = :checklist_id
                """),
                {"checklist_id": checklist_id}
            ).mappings().fetchone()
            
            # Buscar informações do processo para contexto
            processo_info = conn.execute(
                text("SELECT codigo_processo, nome_processo FROM processos WHERE id = :id"),
                {"id": processo_id}
            ).mappings().fetchone()
        
        # ===== 2. ATUALIZAR CHECKLIST =====
        query = text("""
            UPDATE checklist_sessoes
            SET status = 'Concluído', data_conclusao = NOW()
            WHERE id = :checklist_id
            RETURNING id
        """)
        
        with engine.begin() as conn:
            result = conn.execute(query, {"checklist_id": checklist_id}).scalar()
            
            # ===== LOG DO UPDATE DO CHECKLIST =====
            dados_novos_checklist = {
                'id': checklist_id,
                'processo_id': processo_id,
                'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                'processo_nome': processo_info['nome_processo'] if processo_info else None,
                'auditoria_id': auditoria_id,
                'tipo_checklist': tipo_checklist,
                'status_anterior': dados_antigos_checklist['status'] if dados_antigos_checklist else None,
                'status_novo': 'Concluído',
                'data_conclusao': 'NOW()'
            }
            
            dados_antigos_resumidos = {
                'id': checklist_id,
                'processo_id': processo_id,
                'status': dados_antigos_checklist['status'] if dados_antigos_checklist else None,
                'data_conclusao': str(dados_antigos_checklist['data_conclusao']) if dados_antigos_checklist and dados_antigos_checklist['data_conclusao'] else None
            }
            
            registrar_log(
                tabela='checklist_sessoes',
                registro_id=checklist_id,
                operacao='UPDATE',
                dados_anteriores=dados_antigos_resumidos,
                dados_novos=dados_novos_checklist
            )
            # ===== FIM DO LOG =====

        # ===== 3. SE FOR GOVERNANÇA, ATUALIZAR STATUS DA AVALIAÇÃO =====
        if tipo_checklist == 'governanca':
            # Buscar dados ANTIGOS do status da avaliação
            with engine.connect() as conn:
                dados_antigos_avaliacao = conn.execute(
                    text("""
                        SELECT id, processo_id, auditoria_id, status_avaliacao
                        FROM auditoria_processos 
                        WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id
                    """),
                    {
                        "processo_id": processo_id,
                        "auditoria_id": auditoria_id
                    }
                ).mappings().fetchone()
            
            query_update_status = text("""
                UPDATE auditoria_processos
                SET status_avaliacao = 'Avaliado'
                WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id
                RETURNING id
            """)
            
            with engine.begin() as conn:
                result_status = conn.execute(query_update_status, {
                    "processo_id": processo_id,
                    "auditoria_id": auditoria_id
                }).scalar()
                
                # ===== LOG DO UPDATE DO STATUS =====
                dados_novos_avaliacao = {
                    'processo_id': processo_id,
                    'processo_codigo': processo_info['codigo_processo'] if processo_info else None,
                    'processo_nome': processo_info['nome_processo'] if processo_info else None,
                    'auditoria_id': auditoria_id,
                    'status_avaliacao_anterior': dados_antigos_avaliacao['status_avaliacao'] if dados_antigos_avaliacao else None,
                    'status_avaliacao_novo': 'Avaliado'
                }
                
                dados_antigos_resumidos_avaliacao = {
                    'id': dados_antigos_avaliacao['id'] if dados_antigos_avaliacao else None,
                    'processo_id': processo_id,
                    'auditoria_id': auditoria_id,
                    'status_avaliacao': dados_antigos_avaliacao['status_avaliacao'] if dados_antigos_avaliacao else None
                }
                
                registrar_log(
                    tabela='auditoria_processos',
                    registro_id=dados_antigos_avaliacao['id'] if dados_antigos_avaliacao else None,
                    operacao='UPDATE',
                    dados_anteriores=dados_antigos_resumidos_avaliacao,
                    dados_novos=dados_novos_avaliacao
                )
                # ===== FIM DO LOG =====
        
        return True
        
    except Exception as e:
        print(f"Erro ao finalizar checklist: {e}")
        return False

def obter_resumo_checklists(processo_id, auditoria_id):
    query = text("""
        SELECT 
            cg.id,
            cg.tipo_checklist,
            cg.status
        FROM checklists_sessoes cg
        WHERE cg.processo_id = :processo_id AND cg.auditoria_id = :auditoria_id
    """)

def buscar_historico_avaliacoes(processo_id, auditoria_id):
    """Busca todas as avaliações (checklists) já realizadas para um processo"""
    query = text("""
        SELECT
            cg.id,
            cg.tipo_checklist,
            cg.status,
            cg.data_inicio,
            cg.data_conclusao,
            cg.auditor_nome,
            COUNT(DISTINCT cr.id) as total_respostas,
            COUNT(DISTINCT ce.id) as total_evidencias
        FROM checklist_sessoes cg
        LEFT JOIN checklist_respostas cr ON cg.id = cr.checklist_id
        LEFT JOIN checklist_evidencias ce ON cr.id = ce.resposta_id
        WHERE cg.processo_id = :processo_id AND cg.auditoria_id = :auditoria_id
        GROUP BY cg.id
        ORDER BY
            CASE cg.tipo_checklist
                WHEN 'governanca' THEN 1
                WHEN 'riscos' THEN 2
                WHEN 'controles' THEN 3
                ELSE 4
            END,
            cg.data_conclusao DESC NULLS LAST,
            cg.data_inicio DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={
            'processo_id': processo_id,
            'auditoria_id': auditoria_id
        })
def buscar_detalhes_avaliacao(avaliacao_id):
    """Busca todos os detalhes de uma avaliação específica (perguntas, respostasa e evidências)"""
    query = text("""
        SELECT
            cr.pergunta_id,
            cr.resposta,
            cr.comentario,
            cr.data_resposta,
            cp.pergunta,
            cp.recomendacao,
            cp.tipo_checklist
        FROM checklist_respostas cr
        JOIN checklist_perguntas_padrao cp ON cr.pergunta_id = cp.id
        WHERE cr.checklist_id = :avaliacao_id
        ORDER BY cp.ordem
    """)

    with engine.connect() as conn:
        df_respostas = pd.read_sql(query, conn, params={"avaliacao_id": avaliacao_id})

        # Buscar evidências para cada resposta
        for idx, row in df_respostas.iterrows():
            query_evidencias = text("""
                SELECT id, nome_arquivo, tamanho_bytes, data_upload
                FROM checklist_evidencias ce
                JOIN checklist_respostas cr ON ce.resposta_id = cr.id
                WHERE cr.checklist_id = :avaliacao_id AND cr.pergunta_id = :pergunta_id
            """)
            with engine.connect() as conn:
                df_evidencias = pd.read_sql(query_evidencias, conn, params={
                    "avaliacao_id": avaliacao_id,
                    "pergunta_id": row['pergunta_id'],
                })
                df_respostas.at[idx, 'evidencias'] = df_evidencias.to_dict('records')
        
        return df_respostas