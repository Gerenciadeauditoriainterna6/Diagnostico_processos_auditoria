"""
Módulo de Checklist de Governança
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import time as time_module
from sqlalchemy import text
from database import engine
from logic import buscar_auditoria_por_id, buscar_processo_por_codigo


def buscar_perguntas_checklist():
    """Busca todas as perguntas do checklist padrão"""
    query = text("""
        SELECT id, pergunta, tipo_resposta, ordem
        FROM checklist_perguntas_padrao
        WHERE ativo = TRUE
        ORDER BY ordem
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


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
    
    if existing:
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
        SELECT id FROM checklist_governanca
        WHERE processo_id = :processo_id AND auditoria_id = :auditoria_id
    """)
    with engine.connect() as conn:
        result = conn.execute(query_check, {
            "processo_id": processo_id,
            "auditoria_id": auditoria_id
        }).fetchone()
    
    if result:
        return result[0]
    
    # Se não existe, criar
    query_insert = text("""
        INSERT INTO checklist_governanca (processo_id, auditoria_id, auditor_nome, data_inicio, status)
        VALUES (:processo_id, :auditoria_id, :auditor_nome, NOW(), 'Em Andamento')
        RETURNING id
    """)
    with engine.begin() as conn:
        result = conn.execute(query_insert, {
            "processo_id": processo_id,
            "auditoria_id": auditoria_id,
            "auditor_nome": auditor_nome
        }).scalar()
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


def tela_checklist_governanca():
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
            # Marcar checklist como concluído
            query = text("""
                UPDATE checklist_governanca 
                SET status = 'Concluído', data_conclusao = NOW()
                WHERE id = :checklist_id
            """)
            with engine.begin() as conn:
                conn.execute(query, {"checklist_id": checklist_id})
            
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