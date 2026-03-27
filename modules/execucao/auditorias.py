"""
Módulo de Detalhamento de Auditorias
Gerencia a exibição de auditorias e seus processos
"""
import streamlit as st
import pandas as pd
import time as time_module
from datetime import datetime
from sqlalchemy import text
from database import engine
from logic import (
    listar_auditorias_por_ano, buscar_auditoria_por_id, criar_nova_auditoria,
    listar_processos_da_auditoria_com_riscos, vincular_processo_a_auditoria,
    listar_processos_disponiveis_para_auditoria, remover_processo_da_auditoria, listar_riscos_do_processo, get_estilo_risco,
    normalizar_valor_risco, salvar_edicao_processo_completa,
    listar_funcionarios_por_area, listar_executores_processo,
    listar_categorias, buscar_processo_por_codigo, atualizar_etapa_no_banco,
    listar_etapas_do_processo, listar_riscos_etapa, MAPA_RISCO, salvar_risco_etapa,
    salvar_controle_no_banco, obter_proximo_codigo_etapa, salvar_etapa_no_banco
)
from modules.shared.components import formatar_risco_para_card
from modules.shared.utils import exibir_criterios_risco
from modules.execucao.areas import carregar_areas_banco

def tela_auditorias_trimestrais():
    """Gerencia as auditorias organizadas por trimestre"""
    st.title("📋 Detalhamento dos Processos")

    # Selecionar ano
    ano_atual = datetime.now().year
    ano = st.selectbox("Selecione o ano:", [ano_atual, ano_atual-1, ano_atual+1], index=0)

    # Buscar auditorias do ano selecionado
    df_auditorias = listar_auditorias_por_ano(ano)

    if df_auditorias.empty:
        st.info(f"Nenhuma auditoria encontrada para {ano}. Deseja criar uma nova?")

        with st.expander("➕ Criar Nova Auditoria"):
            with st.form("form_nova_auditoria"):
                # Dados básicos
                areas_dict = carregar_areas_banco()
                area_selecionada = st.selectbox("Área a ser auditada:", list(areas_dict.keys()))

                trimestre = st.selectbox("Trimestre:", [1, 2, 3, 4])

                col1, col2 = st.columns(2)
                with col1:
                    data_inicio = st.date_input("Data de início prevista")
                with col2:
                    data_fim = st.date_input("Data de término prevista")

                titulo =st.text_input("Titulo de auditoria", value=f"Auditoria {area_selecionada} - {ano} {trimestre}º Trimestre")
                objetivo = st.text_area("Objetivo da auditoria")
                escopo = st.text_area("Escopo (o que será avaliado)")

                if st.form_submit_button("Criar Auditoria", type="primary", key='btn_criar_auditoria'):
                    # Pegar o ID da área selecionada
                    id_area = areas_dict[area_selecionada]

                    dados = {
                        "id_area": id_area,
                        "titulo": titulo,
                        "objetivo": objetivo,
                        "escopo": escopo,
                        "ano": ano,
                        "trimestre": trimestre,
                        "data_inicio": data_inicio,
                        "data_fim": data_fim,
                        "status": "Planejamento"
                    }

                    auditoria_id, codigo = criar_nova_auditoria(dados)

                    if auditoria_id:
                        st.success(f"Auditoria criada com sucesso! Código: {codigo}")
                        st.rerun()
                    else:
                        st.error("Erro o criar auditoria. Já existe uma auditoria para esta área no trimestre?")
    else:
        # Mostrar auditorias existentes em cards
        st.subheader(f"Auditorias de {ano}")

        # Organizar por trimestre
        for trimestre in range(1, 5):
            df_trimestre = df_auditorias[df_auditorias['trimestre'] == trimestre]      

            if not df_trimestre.empty:
                with st.expander(f"📌 {trimestre}º Trimestre", expanded=True):  
                    for _, row in df_trimestre.iterrows():
                        # Card da auditoria
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                        with col1:
                            st.markdown(f"**{row['titulo']}**")
                            st.caption(f"Código: {row['codigo_auditoria']} | Área: {row['nome_area']}")

                        with col2:
                            status = row['status']
                            if status == "Planejamento":
                                st.markdown("🟡 **Planejamento**")
                            elif status == "Em Execução":
                                st.markdown("🟢 **Em Execução**")
                            else:
                                st.markdown("✅ **Concluída**")
                        
                        with col3:
                            if row['data_inicio']:
                                data_inicio_str = row['data_inicio'].strftime('%d/%m/%Y')
                            else:
                                data_inicio_str = 'TBD'
                            if row['data_fim']:
                                data_fim_str = row['data_fim'].strftime('%d/%m/%Y')
                            else:
                                data_fim_str = 'TBD'
                            
                            st.markdown(f"📅 {data_inicio_str} a {data_fim_str}")

                        with col4:
                            if st.button("🔍 Detalhar", key=f"btn_{row['id']}"):
                                st.session_state['auditoria_selecionada'] = row['id']
                                st.session_state['tela_atual'] = 'detalhe_auditoria'
                                st.rerun()
                        
                        st.divider()


def _exibir_card_processo_auditoria(row, auditoria_id):
    """Exibe o card normal do processo"""
    cor, emoji, texto_risco = formatar_risco_para_card(row['maior_risco'])
    
    with st.container(border=True):
        col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
        
        with col_p1:
            st.markdown(f"**{row['codigo_processo']} - {row['nome_processo']}**")
            st.caption(f"📝 Motivo: {row['motivo_selecao'] or 'Não informado'}")
        
        with col_p2:
            status_aval = row.get('status_avaliacao', 'Pendente')
            if status_aval == "Pendente":
                st.markdown("⏳ **Pendente**")
            elif status_aval == "Em Andamento":
                st.markdown("🔄 **Em Andamento**")
            else:
                st.markdown("✅ **Avaliado**")
        
        with col_p3:
            st.markdown(f"<span style='background-color: {cor}; padding: 5px 10px; border-radius: 5px; color: white; font-weight: bold;'>{emoji} Risco: {texto_risco}</span>", unsafe_allow_html=True)
        
        # Expander com riscos do processo
        df_riscos_processo = listar_riscos_do_processo(row['processo_id'])
        # Conta quantos riscos o processo tem
        quantidade_riscos = len(df_riscos_processo) if not df_riscos_processo.empty else 0

        # Título no expander com quantidade
        with st.expander(f"⚠️ Riscos deste Processo ({quantidade_riscos})", expanded=False):
            df_riscos_processo = listar_riscos_do_processo(row['processo_id'])
            
            if not df_riscos_processo.empty:
                df_riscos_ordenados = df_riscos_processo.sort_values('score_risco', ascending=False)
                for _, risco in df_riscos_ordenados.iterrows():
                    score = risco.get('score_risco', 0)
                    cor_risco, emoji_risco = get_estilo_risco(score)
                    
                    st.markdown(f"""
                        <div style='margin-bottom: 10px; padding: 8px; border-left: 4px solid {cor_risco}; background-color: #f9f9f9;'>
                            <strong>{emoji_risco} {risco['nome_risco']}</strong><br>
                            <span style='font-size: 0.9em; color: #666;'>
                                <strong>Fator:</strong> {risco['fator_risco']}<br>
                                <strong>Impacto:</strong> {risco['impacto']} | <strong>Probabilidade:</strong> {risco['probabilidade']}<br>
                                <strong>Magnitude:</strong> {score}
                            </span>
                        </div>""", unsafe_allow_html=True)
            else:
                st.caption("Nenhum risco mapeado para este processo.")
        
        # Botões de ação
        col_b1, col_b2, col_b3, col_b4 = st.columns([1, 1, 1, 2])
        
        with col_b1:
            if st.button("🔍 Ver Detalhes", key=f"ver_{row['processo_id']}"):
                st.session_state['processo_detalhe'] = row['processo_id']
                st.session_state['tela_atual'] = 'detalhe_processo'
                st.rerun()
        
        with col_b2:
            if st.button("✏️ Editar", key=f'editar_{row["processo_id"]}'):
                st.session_state['processo_em_edicao'] = row['processo_id']
                st.rerun()
        
        # = NÃO VAMOS UTILIZAR ESSE BOTÃO POR ENQUANTO
        # with col_b3:
        #     if st.button("📝 Checklists", key=f"check_{row['processo_id']}"):
        #         st.session_state['processo_checklist'] = row['processo_id']
        #         st.session_state['aba_ativa'] = 1
        #         st.rerun()
        
        with col_b3:
            if st.button("🗑️ Remover", key=f"rm_{row['processo_id']}"):
                st.session_state[f"confirmar_remocao_{row['processo_id']}"] = True
            
            if st.session_state.get(f'confirmar_remocao_{row["processo_id"]}', False):
                st.warning(f"Remover processo **{row['codigo_processo']}** da lista dos selecionados?")
                
                col_sim, col_nao = st.columns(2)
                with col_sim:
                    if st.button("✅ Sim, remover", key=f"conf_sim_{row['processo_id']}"):
                        if remover_processo_da_auditoria(auditoria_id, row['processo_id']):
                            st.success("Processo removido!")
                            st.session_state.pop(f"confirmar_remocao_{row['processo_id']}", None)
                            time_module.sleep(1)
                            st.rerun()
                        else:
                            st.error("Erro ao remover processo.")
                with col_nao:
                    if st.button("❌ Não", key=f"conf_nao_{row['processo_id']}"):
                        st.session_state.pop(f'confirmar_remocao_{row["processo_id"]}', None)
                        st.rerun()


def tela_detalhe_processo_auditoria():
    """Tela de detalhamento de um processo dentro do contexto da auditoria"""
    
    if 'processo_detalhe' not in st.session_state or 'auditoria_selecionada' not in st.session_state:
        st.error("Processo ou auditoria não selecionados.")
        if st.button("Voltar", key='btn_voltar'):
            st.session_state.pop('processo_detalhe', None)
            st.rerun()
        return
    
    processo_id = st.session_state['processo_detalhe']
    auditoria_id = st.session_state['auditoria_selecionada']
    
    # Buscar o código do processo a partir do ID
    query = text("SELECT codigo_processo FROM processos WHERE id = :id")
    with engine.connect() as conn:
        resultado = conn.execute(query, {"id": processo_id}).fetchone()
    
    if not resultado:
        st.error("Processo não encontrado.")
        if st.button("Voltar", key='btn_voltar_2'):
            st.session_state.pop('processo_detalhe', None)
            st.rerun()
        return
    
    codigo_processo = resultado[0]
    
    # Busca o processo completo usando o código
    processo = buscar_processo_por_codigo(codigo_processo)

    if not processo:
        st.error("Processo não encontrado.")
        return
    
    st.title(f"📌 Detalhamento do Processo: {processo['codigo_processo']} - {processo['nome_processo']}")
    st.caption(f"Auditoria: {auditoria_id} | Área: {processo['nome_area']}")
    
    # Botão para voltar
    if st.button("← Voltar para o Detalhamento dos Processos", key='btn_voltar_detalhamento_dos_processos'):
        st.session_state.pop('processo_detalhe', None)
        st.rerun()
    
    st.divider()
    
    # --- SEÇÃO DE ETAPAS (adaptada da tela_consulta_detalhada) ---
    etapa_edit = st.session_state.get("etapa_em_edicao")
    
    titulos_tabs = ["📋 Etapas Existentes", "➕ Cadastrar Nova Etapa"]
    if etapa_edit:
        titulos_tabs.append("✏️ Editar Etapa")

    tabs = st.tabs(titulos_tabs)
    tab_lista = tabs[0]
    tab_cadastro = tabs[1]

    if etapa_edit:
        tab_edicao = tabs[2]  # Pega a terceira aba
        with tab_edicao:
            st.write(f"### ✏️ Editando Etapa: {etapa_edit['codigo_etapa']}")
            
            # Botão para cancelar
            if st.button("🚫 Cancelar e Fechar Edição", use_container_width=True, key='btn_cancelar_e_fechar_edicao'):
                st.session_state["etapa_em_edicao"] = None
                st.rerun()
            
            st.divider()
            
            with st.form("form_edicao_etapa_auditoria"):
                # Dados básicos (código não editável)
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.text_input("Código", value=etapa_edit['codigo_etapa'], disabled=True)
                
                with c2:
                    desc_edit = st.text_input("Etapa", value=etapa_edit['descricao_etapa'], help="Nome da etapa")
                
                # Campos principais
                oque_edit = st.text_area("O que você faz?", value=etapa_edit.get('oque_faz', ''))
                como_edit = st.text_area("Como você faz?", value=etapa_edit.get('como_e_feito', ''))
                obj_edit = st.text_area("Qual o objetivo?", value=etapa_edit.get('objetivo_etapa', ''))
                
                # Status
                st_list = ["Ativa", "Inativa"]
                status_edit = st.selectbox(
                    "Status da etapa:", 
                    st_list, 
                    index=st_list.index(etapa_edit['status_etapa']) if etapa_edit['status_etapa'] in st_list else 0
                )
                
                # Colunas para seleções
                col_e1, col_e2, col_e3 = st.columns(3)
                
                with col_e1:
                    ef_list = ["Sim", "Não", "Parcial"]
                    correto_edit = st.selectbox(
                        "Teste de eficácia?", 
                        ef_list, 
                        index=ef_list.index(etapa_edit['realizado_corretamente']) if etapa_edit['realizado_corretamente'] in ef_list else 0
                    )
                
                with col_e2:
                    crit_list = ["Aprovado", "Em Aprovação"]
                    crit_edit = st.selectbox(
                        "Criticidade", 
                        crit_list, 
                        index=crit_list.index(etapa_edit['criticidade_etapa']) if etapa_edit['criticidade_etapa'] in crit_list else 0
                    )
                
                with col_e3:
                    # Executor (usa o do processo como fallback)
                    exec_edit = st.text_input("Executor", value=etapa_edit.get('executor', processo['executor']))
                
                # Links
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    link_d_edit = st.text_input("Link do Diagrama", value=etapa_edit.get('link_diagrama_etapa', ''))
                with col_l2:
                    link_m_edit = st.text_input("Link do Manual", value=etapa_edit.get('manual_processo_link', ''))
                
                # Políticas e análises
                pol_edit = st.text_area("Política Interna", value=etapa_edit.get('politica_interna', ''))
                ana_edit = st.text_area("Análise Crítica", value=etapa_edit.get('analise_critica', ''))
                sug_edit = st.text_area("Sugestão de Melhoria", value=etapa_edit.get('sugestao_melhoria', ''))
                
                # Melhorias
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    nec_edit = st.text_input("Necessidade para implantação", value=etapa_edit.get('necessidade_implantacao', ''))
                with col_m2:
                    gan_edit = st.text_input("Ganho previsto", value=etapa_edit.get('ganho_previsto', ''))
                
                # Obrigações regulatórias
                obri_edit = st.text_input("Obrigações Regulatórias", value=etapa_edit.get('obrigacoes_regulatorias', ''))
                
                # Botão de submit
                if st.form_submit_button("💾 Atualizar Etapa", type="primary", use_container_width=True, key='btn_atualizar_etapa'):
                    # Preparar dados para update
                    dados_update = {
                        "etapa_id": etapa_edit['id'],
                        "desc": desc_edit,
                        "oque": oque_edit,
                        "como": como_edit,
                        "obj": obj_edit,
                        "status": status_edit,
                        "real": correto_edit,
                        "crit": crit_edit,
                        "exec": exec_edit,
                        "link_d": link_d_edit,
                        "link_m": link_m_edit,
                        "pol": pol_edit,
                        "ana": ana_edit,
                        "sug": sug_edit,
                        "nec": nec_edit,
                        "gan": gan_edit,
                        "obri": obri_edit
                    }
                    
                    # Chamar função de atualização (precisa ser criada no logic.py)
                    if atualizar_etapa_no_banco(dados_update):
                        st.success("✅ Etapa atualizada com sucesso!")
                        st.session_state["etapa_em_edicao"] = None
                        time_module.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar etapa. Tente novamente.")

    
    with tab_lista:
                etapas = listar_etapas_do_processo(processo['id'], auditoria_id=auditoria_id)
                if not etapas.empty:
                    for _, etapa in etapas.iterrows():
                        with st.expander(f"Etapa {etapa['codigo_etapa']} - {etapa['descricao_etapa']}"):
                            st.subheader("Detalhes da Execução")

                            st.metric(
                                label="**Status da Etapa**", 
                                value=etapa.get('status_etapa', 'Ativa')
                            )
                            st.write(f"**O que é feito:** {etapa.get('oque_faz', 'N/A')}")
                            st.write(f"**Como é feito:** {etapa['como_e_feito']}")
                            st.write(f"**Objetivo:** {etapa['objetivo_etapa']}")
                            st.write(f"**Criticidade:** {etapa['criticidade_etapa']}")
                            st.write(f"**Teste de Eficácia:** {etapa['realizado_corretamente']}")
                            st.write(f"**Política Interna:** {etapa['politica_interna']}")
                            st.write(f"**Análise Crítica:** {etapa['analise_critica']}")
                            st.write(f"**Sugestão de melhoria:** {etapa['sugestao_melhoria']}")
                            st.write(f"**Necessidade para implantação da melhoria:** {etapa['necessidade_implantacao']}")
                            st.write(f"**Ganho Previsto:** {etapa['ganho_previsto']}")
                            
                            st.divider()
                            # Botões
                            b1, b2, b3 = st.columns(3)
                            if etapa['link_diagrama_etapa']: b1.link_button("🖼️ Desenho da Etapa", etapa['link_diagrama_etapa'])
                            if etapa['manual_processo_link']: b2.link_button("📖 Manual do Processo", etapa['manual_processo_link'])

                            if b3.button("📝 Editar Etapa", key=f"edit_btn_{etapa['id']}"):
                                st.session_state["etapa_em_edicao"] = etapa.to_dict()
                                st.rerun()
                                                        
                            st.divider()                    

                            # --- VISUALIZAÇÃO DE RISCOS (ATUALIZADA) ---
                            st.subheader("⚠️ Riscos desta Etapa")
                        
                            tab_v_risco, tab_c_risco = st.tabs(["📊 Visualizar Riscos", "➕ Adicionar Risco"], key=f"risco_tabs_{etapa['id']}")
                            
                            with tab_v_risco:
                                riscos_df = listar_riscos_etapa(etapa['id'], auditoria_id=auditoria_id)
                                if not riscos_df.empty:
                                    for _, risco in riscos_df.iterrows():
                                        # Expander para cada risco
                                        with st.expander(f"⚠️ {risco['categoria']} - {str(risco['fator_risco'])[:40]}..."):
                                            col_a, col_b = st.columns(2)
                                            col_a.write(f"**Origem:** {risco['origem']}")
                                            col_b.write(f"**Financeiro:** {'Sim' if risco['financeiro'] else 'Não'}")
                                            st.write(f"**Fator:** {risco['fator_risco']}")
                                            st.write(f"**Consequência:** {risco['consequencia']}")
                                            
                                            col_c, col_d = st.columns(2)
                                            col_c.metric("Impacto", risco['impacto'])
                                            col_d.metric("Probabilidade", risco['probabilidade'])
                                            st.info(f"Magnitude: {risco['magnitude']}")
                                            st.write(f"**Apetite:** {risco['apetite']}")
                                            st.write(f"**Tratamento:** {risco['tratamento']}")
                                            st.write(f"**Informações adicionais:** {risco['info_adicional']}")
                                            st.write(f"**Documentação legal:** {risco['doc_legal']}")
                                else:
                                    st.info("Nenhum risco mapeado para esta etapa.")
                            
                            # --- ABA ADICIONAR RISCO ---
                            with tab_c_risco:
                                # DEBUG PARA VERIFICAR SE ENTROU
                                st.write(f"✅ Entrou na aba de adicionar risco para etapa {etapa['id']}")
                                
                                # EXPANDER COM CRITÉRIOS (FORA DO FORMULÁRIO)
                                exibir_criterios_risco()
                                
                                st.divider()
                                
                                with st.form(key=f"form_risco_{etapa['id']}_{auditoria_id}", clear_on_submit=True):
                                    col1, col2 = st.columns(2)
                                    categoria = col1.selectbox(
                                        "Categoria", 
                                        ["Risco Inerente", "Risco de TI", "Risco de Fraude"], 
                                        key=f"cat_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    origem = col2.selectbox(
                                        "Origem", 
                                        ["Interna", "Externa"], 
                                        key=f"ori_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    
                                    fator = st.text_area(
                                        "Fator de Risco", 
                                        key=f"fat_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    cons = st.text_area(
                                        "Consequência", 
                                        key=f"cons_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    
                                    c3, c4 = st.columns(2)
                                    with c3:
                                        financeiro = st.selectbox(
                                            "Impacta Financeiramente?", 
                                            [True, False], 
                                            format_func=lambda x: "Sim" if x else "Não",
                                            key=f"fin_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                        )
                                    with c4:
                                        ativo = st.selectbox(
                                            "Risco Ativo?", 
                                            [True, False], 
                                            format_func=lambda x: "Sim" if x else "Não",
                                            key=f"ativ_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                        )
                                    
                                    # AVISO SOBRE OS CRITÉRIOS
                                    st.info("👆 **Consulte os critérios acima antes de selecionar Impacto e Probabilidade**")
                                    
                                    imp = st.selectbox(
                                        "Impacto", 
                                        ["Baixo", "Médio", "Alto", "Muito Alto"], 
                                        key=f"imp_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    prob = st.selectbox(
                                        "Probabilidade", 
                                        ["Baixo", "Médio", "Alto", "Muito Alto"], 
                                        key=f"prob_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    
                                    mag = MAPA_RISCO.get((imp, prob), 0)
                                    cor, emoji = get_estilo_risco(mag)
                                    st.markdown(f'''<div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white; margin-bottom: 10px;">{emoji} Magnitude: {mag}</div>''', unsafe_allow_html=True)
                                    
                                    apetite = st.text_area(
                                        "Apetite ao Risco", 
                                        key=f"apet_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    tratamento = st.text_area(
                                        "Tratamento", 
                                        key=f"trat_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    info_adicional = st.text_area(
                                        "Informações Adicionais", 
                                        key=f"info_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    doc_legal = st.text_area(
                                        "Documentação Legal", 
                                        key=f"doc_{etapa['id']}_{auditoria_id}"  # ← KEY ÚNICA
                                    )
                                    
                                    if st.form_submit_button("💾 Salvar Risco", type="primary", key='btn_salvar_risco'):
                                        if not fator or not cons:
                                            st.warning("Preencha fator e consequência.")
                                        else:
                                            with st.spinner("Salvando risco da etapa na base de dados..."):
                                                dados_r = {
                                                    "etapa_id": etapa['id'], 
                                                    "cat": categoria, 
                                                    "fator": fator, 
                                                    "cons": cons,
                                                    "info": info_adicional, 
                                                    "fin": financeiro, 
                                                    "ativo": ativo, 
                                                    "ori": origem,
                                                    "doc": doc_legal, 
                                                    "imp": imp, 
                                                    "prob": prob, 
                                                    "mag": mag, 
                                                    "apet": apetite, 
                                                    "trat": tratamento
                                                }
                                                if salvar_risco_etapa(dados_r, auditoria_id=auditoria_id):
                                                    st.toast("Risco da etapa salvo com sucesso!", icon="✅")
                                                    st.rerun()
                                                else:
                                                    st.error("Erro ao salvar no banco de dados. Tente novamente!")
                                                    time_module.sleep(2)

                            st.divider()

                            # --- VISUALIZAÇÃO DE CONTROLES ---
                            st.divider()
                            st.subheader("🎮 Controles da Etapa")

                            # --- VISUALIZAÇÃO E CADASTRO DE CONTROLES ---
                            from logic import listar_controles_da_etapa

                            tab_v_controle, tab_c_controle = st.tabs(["📊 Visualizar Controles", "➕ Adicionar Controle"])

                            with tab_v_controle:
                                controles_df = listar_controles_da_etapa(etapa['id'], auditoria_id=auditoria_id)

                                if not controles_df.empty:

                                    for _, ctrl in controles_df.iterrows():
                                        # O título agora mostra o Risco de Origem e o Nome do Controle
                                        titulo = f"🛡️ Controle: {ctrl['nome_controle']} (Risco: {ctrl['risco_pai']})"
                                        
                                        with st.expander(titulo):
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                st.write(f"**Avaliação do Risco:** {ctrl['risco_avaliacao']}")
                                                st.write(f"**Causa/Motivo:** {ctrl['causa_motivo']}")
                                                st.write(f"**Como é executado:** {ctrl['como_executado']}")
                                                st.write(f"**Objetivo:** {ctrl['objetivo_controle']}")
                                                st.write(f"**Periodicidade:** {ctrl['periodicidade_execucao']}")
                                                st.write(f"**Data Atualização:** {ctrl['data_atualizacao']}")

                                            with col2:
                                                st.write(f"**Evidência:** {ctrl['evidencia_realizacao']}")
                                                st.write(f"**Forma:** {ctrl['forma_execucao']}")
                                                st.write(f"**Natureza:** {ctrl['natureza']}")
                                                st.write(f"**Status:** {ctrl['status_controle']}")
                                                st.write(f"**Frequência:** {ctrl['frequencia_evidencia']}")
                                                st.write(f"**Responsáveis:** {ctrl['responsaveis_tratamento']}")
                                else:
                                    st.info("Nenhum controle cadastrado para esta etapa.")

                            with tab_c_controle:
                                # Precisamos carregar os riscos para saber o que mitigar
                                df_riscos_atuais = listar_riscos_etapa(etapa['id'], auditoria_id=auditoria_id)

                                if not df_riscos_atuais.empty:
                                    # Prepara as opções para o selectbox
                                    opcoes_riscos = {f"{row['categoria']} - {row['fator_risco'][:50]}...": row['id'] for _, row in df_riscos_atuais.iterrows()}
                                    
                                    selecao_risco = st.selectbox(
                                        "Selecione o Risco para mitigar:", 
                                        options=list(opcoes_riscos.keys()), 
                                        key=f"sel_risco_ctrl_{etapa['id']}"
                                    )

                                    risco_selecionado_id = opcoes_riscos[selecao_risco]
                                    # Pega o fator de risco original para exibir como "Causa" (desabilitado)
                                    fator_orig = df_riscos_atuais[df_riscos_atuais['id'] == risco_selecionado_id]['fator_risco'].values[0]

                                    with st.form(key=f"form_ctrl_novo_{etapa['id']}", clear_on_submit=True):
                                        col1, col2 = st.columns(2)
                                        # Exibimos a causa apenas para referência do usuário
                                        col1.text_area("Causa (Fator de Risco Original)", value=fator_orig, disabled=True)
                                        aval = col2.text_area("Risco e Avaliação do Controle", key=f"aval_ctrl_{etapa['id']}")

                                        nome_c = st.text_input("Nome da Ação de Controle", key=f"nome_ctrl_{etapa['id']}")

                                        c3, c4, c5 = st.columns(3)
                                        forma = c3.selectbox("Forma de Execução", ["Manual", "Automático"], key=f"forma_ctrl_{etapa['id']}")
                                        nat = c4.selectbox("Natureza", ["Preventiva", "Detectiva", "Corretiva"], key=f"nat_ctrl_{etapa['id']}")
                                        stat = c5.selectbox("Status", ["Ativo", "Inativo"], key=f"stat_ctrl_{etapa['id']}")

                                        freq = st.selectbox("Frequência de Execução", ["Diário", "Semanal", "Mensal", "Trimestral", "Anual", "Por Evento"], key=f"freq_ctrl_{etapa['id']}")
                                        resp = st.text_input("Usuário Responsável", key=f"resp_ctrl_{etapa['id']}")

                                        if st.form_submit_button("💾 Salvar Controle", type="primary", key='btn_salvar_controle'):
                                            if not nome_c or not resp:
                                                st.warning("Preencha o nome do controle e o responsável.")
                                            else:
                                                dados_c = {
                                                    "risco_id": int(risco_selecionado_id),
                                                    "nome": nome_c,
                                                    "forma": forma,
                                                    "natureza": nat,
                                                    "status": stat,
                                                    "frequencia": freq,
                                                    "responsavel": resp,
                                                    "avaliacao": aval
                                                }
                                                if salvar_controle_no_banco(dados_c):
                                                    st.toast("Controle salvo com sucesso!", icon="✅")
                                                    st.rerun()
                                                else:
                                                    st.error("Erro ao salvar controle.")    
                        
                else:
                    st.info("Nenhuma etapa cadastrada.")
                    st.warning("É necessário cadastrar um risco para essa etapa antes de cadastrar um controle.")

    with tab_cadastro:
        st.write("### Cadastro de Nova Etapa")
        prox_cod = obter_proximo_codigo_etapa(processo['id'], processo['codigo_processo'])
        with st.form("form_nova_etapa", clear_on_submit=True):
            c1, c2 = st.columns([1, 3])
            c1.text_input("Código", value=prox_cod, disabled=True)
            desc_etapa = c2.text_input("Etapa", help="Nome da etapa")
            oque = st.text_area("O que você faz?")
            como = st.text_area("Como você faz?")
            obj_etapa = st.text_area("Qual o objetivo??")
            status = st.selectbox("Status da etapa:", ["Ativa", "Inativa"])
            
            col_f1, col_f2, col_f3 = st.columns(3)
            correto = col_f1.selectbox("Teste de eficácia?", ["Sim", "Não", "Parcial"])
            executa = col_f3.text_input("Executor", value=processo['executor'])
            link_bpmn = st.text_input("Link Diagrama")
            link_manual = st.text_input("Link Manual")
            
            politica = st.text_area("Política Interna")
            analise = st.text_area("Análise Crítica")
            melhoria = st.text_area("Sugestão de Melhoria")
            
            col_f4, col_f5 = st.columns(2)
            necessidade = col_f4.text_input("Necessidade para implantação")
            ganho = col_f5.text_input("Ganho previsto")
            obrigacoes = st.text_input("Obrigações Regulatórias")
            crit_etapa = col_f2.selectbox("Criticidade", ["Aprovado", "Em Aprovação"])

            if st.form_submit_button("Salvar Detalhamento", type="primary", key='btn_salvar_detalhamento'):
                dados = {
                    "p_id": int(processo['id']), "cod": prox_cod, "desc": desc_etapa, "oque": oque,
                    "status": status, "como": como, "obj": obj_etapa, "real": correto, "link_d": link_bpmn,
                    "pol": politica, "ana": analise, "sug": melhoria, "nec": necessidade, "gan": ganho,
                    "obri": obrigacoes, "crit": crit_etapa, "man": link_manual
                }
                if salvar_etapa_no_banco(dados, auditoria_id=auditoria_id):
                    st.success("Etapa salva!")
                    st.rerun()


def _exibir_formulario_edicao_processo_auditoria(row, auditoria_id, auditoria):
    """Exibe o formulário de edição do processo dentro da tela de auditoria"""
    
    # Buscar dados completos do processo
    processo = buscar_processo_por_codigo(row['codigo_processo'])
    
    if not processo:
        st.error("Erro ao carregar dados do processo")
        if st.button("Fechar", key=f"close_error_{row['processo_id']}"):
            st.session_state['processo_em_edicao'] = None
            st.rerun()
        return
    
    # Carregar riscos do processo
    df_riscos = listar_riscos_do_processo(processo['id'])
    
    # Preparar lista de riscos
    riscos_lista = []
    if not df_riscos.empty:
        for _, risco_row in df_riscos.iterrows():
            riscos_lista.append({
                'id': risco_row.get('id'),
                'nome': risco_row.get('nome_risco', ''),
                'fator': risco_row.get('fator_risco', ''),
                'melhoria': risco_row.get('melhoria', ''),
                'apetite': risco_row.get('apetite_risco', ''),
                'motivo': risco_row.get('motivo_risco', ''),
                'categorias': risco_row.get('categorias_ids', []),
                'impacto': normalizar_valor_risco(risco_row.get('impacto', 'Médio')),
                'probabilidade': normalizar_valor_risco(risco_row.get('probabilidade', 'Médio'))
            })
    
    # Container do formulário de edição
    with st.container(border=True):
        st.markdown(f"""
        <div class="edit-form-container">
            <h3>✏️ Editando Processo</h3>
            <p><strong>Código:</strong> {row['codigo_processo']} | <strong>Área:</strong> {auditoria['nome_area']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão para cancelar edição (fora do form - é permitido)
        if st.button("❌ Cancelar Edição", key=f"cancel_edit_{row['processo_id']}", use_container_width=True):
            st.session_state['processo_em_edicao'] = None
            st.rerun()
        
        st.divider()
        
        # ===== FORMULÁRIO ÚNICO DE EDIÇÃO =====
        with st.form(key=f"form_edicao_processo_{row['processo_id']}"):
            
            # Nome do Processo
            nome_processo = st.text_input(
                "Nome do Processo *", 
                value=processo.get('nome_processo', ''),
                help="Digite o nome do processo."
            )
            
            # Código (desabilitado)
            st.text_input(
                "Código do Processo", 
                value=processo.get('codigo_processo', ''), 
                disabled=True
            )
            
            # ===== EXECUTORES DO PROCESSO =====
            st.markdown("**Funcionário(s) que executam o processo:**")
            
            id_area = processo.get('id_area')
            funcionarios_lista = listar_funcionarios_por_area(id_area) if id_area else []
            
            if not funcionarios_lista:
                st.warning("⚠️ Nenhum funcionário cadastrado para esta área. Cadastre funcionários em '🏢 Cadastro de Áreas e Funcionários'.")
                executores_selecionados = []
            else:
                funcionarios_ids = [f[0] for f in funcionarios_lista]
                funcionarios_dict = {f[0]: f[1] for f in funcionarios_lista}
                executores_atuais = listar_executores_processo(processo['id'])
                defaults_validos = [exec_id for exec_id in executores_atuais if exec_id in funcionarios_dict]
                
                executores_selecionados = st.multiselect(
                    "Selecione os funcionários que executam este processo:",
                    options=funcionarios_ids,
                    format_func=lambda x: funcionarios_dict[x],
                    default=defaults_validos,
                    help="Você pode selecionar um ou mais funcionários",
                    placeholder="Selecione os funcionários que executam este processo:"
                )
                
                if executores_selecionados:
                    nomes_selecionados = [funcionarios_dict[id] for id in executores_selecionados]
                    st.caption(f"✅ Selecionados: {', '.join(nomes_selecionados)}")
            
            st.divider()
            
            # ===== DETALHAMENTO DO PROCESSO =====
            st.markdown("### Detalhamento do Processo")
            st.info("ℹ️ Os campos abaixo são opcionais.")
            
            descricao = st.text_area(
                "O que é o processo?:",
                value=processo.get('descricao', ''),
                help="Gestor diz com as suas palavras o que entende ser o processo."
            )
            
            etapa_ini = st.text_area(
                "Onde Começa o Processo?:",
                value=processo.get('etapa_ini', ''),
                help="Onde começa o processo? - ETAPA INICIAL"
            )
            
            produto = st.text_area(
                "Qual (is) o Produto (s) Final Desse Processo?:",
                value=processo.get('produto', ''),
                help="Qual(is) o(s) produto(s) final(is) desse processo?"
            )
            
            etapa_fim = st.text_area(
                "Depois de Acabado, para onde envia?:",
                value=processo.get('etapa_fim', ''),
                help="Depois de acabado, para onde envia? - ETAPA FINAL"
            )
            
            objetivo = st.text_area(
                "Qual o Objetivo do Processo? e Por que faz?:",
                value=processo.get('objetivo', '')
            )
            
            st.divider()
            
            # ===== RISCOS ASSOCIADOS =====
            st.markdown("### Riscos Associados")
            
            # Botão para adicionar risco DENTRO do formulário usando st.form_submit_button
            col_add, _ = st.columns([1, 4])
            with col_add:
                add_risco = st.form_submit_button("➕ Adicionar Risco", use_container_width=True)
            
            st.markdown("---")
            
            # Exibir riscos existentes
            categorias_dict = listar_categorias()
            ids_categorias = list(categorias_dict.keys())
            
            # Usar uma lista mutável que será atualizada pelo form
            # Precisamos de um ID único para identificar este formulário e seus riscos
            form_key = f"form_{row['processo_id']}"
            
            # Usar session_state para manter os riscos entre submits
            if f'riscos_temp_{row["processo_id"]}' not in st.session_state:
                st.session_state[f'riscos_temp_{row["processo_id"]}'] = riscos_lista.copy()
            
            riscos_temp = st.session_state[f'riscos_temp_{row["processo_id"]}']
            
            # Verificar se o botão de adicionar risco foi pressionado
            if add_risco:
                riscos_temp.append({})
                st.session_state[f'riscos_temp_{row["processo_id"]}'] = riscos_temp
                st.rerun()
            
            # Mostrar os riscos
            indices_para_remover = []
            
            for i, risco in enumerate(riscos_temp):
                titulo_risco = risco.get('nome', f'Risco {i+1}')
                if titulo_risco and titulo_risco != f'Risco {i+1}':
                    titulo_expander = f"⚠️ {titulo_risco[:50]}"
                else:
                    titulo_expander = f"⚠️ Risco {i+1} (não nomeado)"
                
                with st.expander(titulo_expander, expanded=False):
                    col_titulo, col_remove = st.columns([5, 1])
                    with col_remove:
                        if len(riscos_temp) > 1:
                            # Botão de remover dentro do form - usar form_submit_button
                            remover = st.form_submit_button("🗑️ Remover", key=f"remove_risco_{i}_{row['processo_id']}", use_container_width=True)
                            if remover:
                                indices_para_remover.append(i)
                    
                    st.divider()
                    
                    # Campos do risco
                    risco['nome'] = st.text_input(
                        "Nome do Risco:",
                        value=risco.get('nome', ''),
                        key=f"edit_nome_{row['processo_id']}_{i}",
                        placeholder="Ex: Risco de erro no cadastro..."
                    )
                    
                    # Categorias
                    risco['categorias'] = st.multiselect(
                        "Categorias do Risco:",
                        options=ids_categorias,
                        format_func=lambda x: categorias_dict[x],
                        default=risco.get('categorias', []),
                        key=f"edit_categorias_{row['processo_id']}_{i}"
                    )
                    
                    risco['fator'] = st.text_area(
                        "Fator de Risco:",
                        value=risco.get('fator', ''),
                        key=f"edit_fator_{row['processo_id']}_{i}"
                    )
                    
                    risco['melhoria'] = st.text_area(
                        "Ponto de Melhoria:",
                        value=risco.get('melhoria', ''),
                        key=f"edit_melhoria_{row['processo_id']}_{i}"
                    )
                    
                    risco['apetite'] = st.text_area(
                        "Apetite ao risco:",
                        value=risco.get('apetite', ''),
                        key=f"edit_apetite_{row['processo_id']}_{i}"
                    )
                    
                    exibir_criterios_risco()
                    
                    col_i, col_p = st.columns(2)
                    with col_i:
                        risco['impacto'] = st.selectbox(
                            "Impacto:",
                            ["Muito Alto", "Alto", "Médio", "Baixo"],
                            index=["Muito Alto", "Alto", "Médio", "Baixo"].index(risco.get('impacto', 'Médio')),
                            key=f"edit_imp_{row['processo_id']}_{i}"
                        )
                    with col_p:
                        risco['probabilidade'] = st.selectbox(
                            "Probabilidade:",
                            ["Muito Alto", "Alto", "Médio", "Baixo"],
                            index=["Muito Alto", "Alto", "Médio", "Baixo"].index(risco.get('probabilidade', 'Médio')),
                            key=f"edit_prob_{row['processo_id']}_{i}"
                        )
                    
                    score_v = MAPA_RISCO.get((risco.get('impacto', 'Médio'), risco.get('probabilidade', 'Médio')), 0)
                    cor_risco, emoji_risco = get_estilo_risco(score_v)
                    st.markdown(f"""
                        <div style="background-color: {cor_risco}; padding: 10px; border-radius: 5px; text-align: center; color: white; margin: 10px 0;">
                            {emoji_risco} <strong>Risco Bruto: {score_v}</strong>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    risco['motivo'] = st.text_area(
                        "Motivo:",
                        value=risco.get('motivo', ''),
                        key=f"edit_motivo_{row['processo_id']}_{i}"
                    )
                    
                    st.markdown("---")
            
            # Remover riscos marcados
            for idx in reversed(indices_para_remover):
                riscos_temp.pop(idx)
            
            if indices_para_remover:
                st.session_state[f'riscos_temp_{row["processo_id"]}'] = riscos_temp
                st.rerun()
            
            st.markdown("---")
            
            # Botão de salvar
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
            
            if submitted:
                # Validar campos obrigatórios
                if not nome_processo.strip():
                    st.error("❌ O campo 'Nome do Processo' é obrigatório.")
                elif not executores_selecionados:
                    st.error("❌ Selecione pelo menos um funcionário para executar o processo.")
                else:
                    # Preparar dados para salvar
                    edit_data = {
                        'processo_id': processo['id'],
                        'nome_processo': nome_processo,
                        'objetivo': objetivo,
                        'descricao': descricao,
                        'etapa_ini': etapa_ini,
                        'etapa_fim': etapa_fim,
                        'produto': produto,
                        'executores': executores_selecionados,
                        'riscos': riscos_temp
                    }
                    
                    with st.spinner("Salvando alterações..."):
                        if salvar_edicao_processo_completa(edit_data):
                            # Limpar dados temporários
                            st.session_state.pop(f'riscos_temp_{row["processo_id"]}', None)
                            st.session_state['processo_em_edicao'] = None
                            st.toast("✅ Alterações salvas com sucesso!", icon="✅")
                            time_module.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar alterações. Tente novamente.")


def tela_detalhe_auditoria():
    """Tela de detalhamento de uma auditoria específica"""
    
    # CSS para reduzir fonte dos métricas
    st.markdown("""
        <style>
            [data-testid="stMetricValue"] { font-size: 14px !important; }
            [data-testid="stMetricLabel"] { font-size: 14px !important; }
            [data-testid="stMetricDelta"] { font-size: 12px !important; }
            .edit-form-container {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin: 10px 0;
                border: 1px solid #e0e0e0;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Verifica se temos uma auditoria selecionada
    if 'auditoria_selecionada' not in st.session_state:
        st.error("Nenhuma auditoria selecionada.")
        if st.button("🔙 Voltar para lista de auditorias", key='btn_voltar_lista_auditorias'):
            st.session_state.pop('auditoria_selecionada', None)
            st.rerun()
        return
    
    # Inicializar variável de controle de edição
    if 'processo_em_edicao' not in st.session_state:
        st.session_state['processo_em_edicao'] = None
    
    auditoria_id = st.session_state['auditoria_selecionada']
    
    # Busca dados da auditoria
    auditoria = buscar_auditoria_por_id(auditoria_id)
    
    if not auditoria:
        st.error("Auditoria não encontrada.")
        return
    
    # Cabeçalho com informações da auditoria
    st.title(f"📋 {auditoria['titulo']}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Área", auditoria['nome_area'])
    
    with col2:
        status = auditoria['status']
        if status == "Planejamento":
            st.metric("Status", "🟡 Planejamento")
        elif status == "Em Execução":
            st.metric("Status", "🟢 Em Execução")
        else:
            st.metric("Status", "✅ Concluída")
    
    with col3:
        st.metric("Trimestre", f"{auditoria['trimestre']}º/{auditoria['ano']}")
    
    # Datas
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_inicio_str = auditoria['data_inicio'].strftime('%d/%m/%Y') if auditoria['data_inicio'] else 'Não definida'
        st.info(f"📅 **Início:** {data_inicio_str}")
    with col_d2:
        data_fim_str = auditoria['data_fim'].strftime('%d/%m/%Y') if auditoria['data_fim'] else 'Não definida'
        st.info(f"📅 **Término:** {data_fim_str}")
    
    # Expander com objetivo e escopo
    with st.expander("📌 Objetivo e Escopo da Auditoria"):
        st.write(f"**Objetivo:** {auditoria['objetivo']}")
        st.write(f"**Escopo:** {auditoria['escopo']}")
    
    st.divider()
    
    # Abas para organizar o conteúdo
    tab1, tab2, tab3 = st.tabs(["📋 Processos Selecionados", "✅ Checklists", "📊 Parecer Final"])
    
    # ===== ABA 1: PROCESSOS SELECIONADOS =====
    with tab1:
        st.subheader("Processos selecionados para auditoria")
        
        # Busca os processos vinculados
        df_processos = listar_processos_da_auditoria_com_riscos(auditoria_id)
        
        if df_processos.empty:
            st.warning("Nenhum processo selecionado para esta auditoria ainda.")
            
        else:
            # Filtro de ordenação
            col_filtro1, col_filtro2 = st.columns(2)
            with col_filtro1:
                ordem_opcao = st.radio(
                    'Ordenar por:',
                    ['Código do Processo', 'Maior Risco'],
                    key='ordem_processos_auditoria',
                    horizontal=True
                )
            
            # Aplicar ordenação
            if ordem_opcao == "Código do Processo":
                df_processos['numero_ordem'] = df_processos['codigo_processo'].apply(
                    lambda x: int(x.split('.')[1]) if '.' in x and x.split('.')[1].isdigit() else 0
                )
                df_processos = df_processos.sort_values('numero_ordem', ascending=True)
            else:
                df_processos['maior_risco'] = df_processos['maior_risco'].fillna(-1)
                df_processos = df_processos.sort_values('maior_risco', ascending=False)
            
            # ===== PERCORRER CADA PROCESSO =====
            for _, row in df_processos.iterrows():
                
                # VERIFICAR SE ESTE PROCESSO ESTÁ EM MODO DE EDIÇÃO
                if st.session_state['processo_em_edicao'] == row['processo_id']:
                    # ===== EXIBIR FORMULÁRIO DE EDIÇÃO =====
                    _exibir_formulario_edicao_processo_auditoria(row, auditoria_id, auditoria)
                else:
                    # ===== EXIBIR CARD NORMAL =====
                    _exibir_card_processo_auditoria(row, auditoria_id)
            
            # """# ===== SEÇÃO PARA ADICIONAR NOVOS PROCESSOS (já existente) ===== (DESATIVADA POR ENQUANTO)
            # st.divider()
            
            # with st.expander("➕ Adicionar novo processo à auditoria"):
            #     df_disponiveis = listar_processos_disponiveis_para_auditoria(
            #         auditoria_id=auditoria_id,
            #         id_area=auditoria['id_area']
            #     )
                
            #     if df_disponiveis.empty:
            #         st.success("✅ Todos os processos da área já foram selecionados para esta auditoria!")
            #     else:
            #         st.caption(f"**{len(df_disponiveis)}** processos disponíveis para selecionar.")
                    
            #         opcoes_processos = []
            #         for _, proc_row in df_disponiveis.iterrows():
            #             risco_info = f" (Risco: {int(proc_row['maior_risco'])})" if proc_row['maior_risco'] > 0 else " (Sem risco mapeado)"
            #             opcoes_processos.append({
            #                 "id": proc_row['id'],
            #                 "display": f"{proc_row['codigo_processo']} - {proc_row['nome_processo']}{risco_info}"
            #             })
                    
            #         display_list = [item["display"] for item in opcoes_processos]
            #         id_map = {item['display']: item["id"] for item in opcoes_processos}
                    
            #         processo_selecionado_display = st.selectbox(
            #             "Selecione o Processo:",
            #             options=display_list,
            #             key="select_processo_disponivel"
            #         )
                    
            #         motivo = st.text_area(
            #             "Motivo da seleção:",
            #             placeholder="Ex: Processo com risco muito alto, crítico para a área...",
            #             key="motivo_novo_processo"
            #         )
                    
            #         col_add, col_cancel = st.columns([1, 3])
            #         with col_add:
            #             if st.button("✓ Adicionar à auditoria", type="primary", use_container_width=True, key='btn_add_a_auditoria'):
            #                 if processo_selecionado_display:
            #                     processo_id = id_map[processo_selecionado_display]
            #                     if vincular_processo_a_auditoria(auditoria_id, processo_id, motivo):
            #                         st.success("✅ Processo adicionado com sucesso!")
            #                         time_module.sleep(1)
            #                         st.rerun()
            #                     else:
            #                         st.error("Erro ao adicionar processo.")
            #                 else:
            #                     st.warning("Selecione um processo.")
            #         with col_cancel:
            #             if st.button("Cancelar", use_container_width=True, key='btn_cancelar'):
            #                 st.session_state.pop('mostrar_selecao_processos', None)
            #                 st.rerun() """
    
    # ===== ABA 2: CHECKLISTS (placeholder) =====
    with tab2:
        st.info("📝 A funcionalidade de checklists será implementada no próximo passo.")
        st.caption("Aqui você poderá avaliar a eficácia da governança, riscos e controles.")
    
    # ===== ABA 3: PARECER FINAL (placeholder) =====
    with tab3:
        st.info("📊 A funcionalidade de parecer final será implementada após os checklists.")
        st.caption("Aqui serão consolidados os resultados e gerado o parecer da auditoria.")
    
    # Botão para voltar
    st.divider()
    if st.button("← Voltar para lista de auditorias", key='btn_voltar_lista_auditorias_2'):
        st.session_state.pop('auditoria_selecionada', None)
        st.rerun()