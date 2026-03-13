import streamlit as st
import os
import pandas as pd
from sqlalchemy import text
from database import engine
import time as time_module
import base64
from logic import (MAPA_RISCO, processar_codigo_inteligente, 
get_estilo_risco, salvar_no_banco, gerar_pdf_em_memoria, buscar_processos_pendentes, carregar_areas_banco,
buscar_processo_por_codigo, obter_proximo_codigo_etapa, salvar_etapa_no_banco, listar_etapas_do_processo, salvar_risco_etapa,
listar_riscos_etapa, buscar_todos_processos, salvar_controle_no_banco, validar_login_no_banco, atualizar_status_processo
)


# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Diagnóstico FUSVE", layout="centered")

def get_base64(bin_file):
    """Lê um arquivo de imagem e retorna sua versão codificada em Base64"""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

# Carregamento das imagens para o CSS
bin_fundo = get_base64(os.path.join("assets", "imagem_fundo.png"))
bin_logo = get_base64(os.path.join("assets", "logo_auditoria_recortada_circulo.png"))
bin_logo_fusve = get_base64(os.path.join("assets", "logo_fusve.png"))

import streamlit as st
import time as time_module

def login_screen():
    """Gerencia a tela de login e a sessão de usuário."""
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        # --- BLOCO CSS PARA DESIGN DO LOGIN ---
        st.markdown(f"""
            <style>
            /* 1. Fundo da tela de login */
            [data-testid="stAppViewContainer"] {{
                background: linear-gradient(rgba(0,0,0,0), rgba(0,0,0,0)),
                            url("data:image/png;base64,{bin_fundo}");
                background-size: cover !important;
                background-position: center !important;
            }}
            
            /* 2. Esconde o cabeçalho padrão */
            header {{ visibility: hidden; }}
            
            div[data-testid="stVerticalBlockBorder"], 
            .stVerticalBlockBorder, 
            .st-emotion-cache-139wymi, 
            .st-emotion-cache-1r6slb0 {{
            background: linear-gradient(180deg, #6d8285 0%, #406064 100%) !important;
            border: none !important;
            box-shadow: 0px 15px 25px rgba(0,0,0,0.3) !important;
            border-radius: 20px !important;
            
            /* Aqui garantimos o tamanho maior na parte de baixo (80px) */
            padding: 15px 50px 30px 50px !important; 
            
            display: flex !important;
            flex-direction: column !important;
            width: 85% !important;
            margin-left: auto !important;
            margin-right: auto !important;
            opacity: 1 !important;
            }}

            /* Ajuste para centralização vertical do card na tela */
            div[data-testid="stVerticalBlock"]:has(> div > [data-testid="stVerticalBlockBorder"]) {{
                margin-top: 2vh;
            }}

            /* 4. Estilo da Logo e Títulos */
            .logo-container {{
                text-align: center;
                margin-top: -85px; /* Faz a logo flutuar na borda superior */
                margin-bottom: 15px;
                position: relative;
                z-index: 10;
            }}
            .logo-container img {{
                width: 110px;
                height: auto;
                background: transparent !important;
                filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.2));
            }}

           /* 1. Faz APENAS o campo de senha subir em direção ao usuário */
            div[data-testid="stTextInput"]:has(#text_input_2){{
            margin-top: -25px !important;
            margin-bottom: 0px !important;
            }}

            /* 2. Mantém o botão na distância original ou empurra um pouco para baixo */
            div.stButton {{
            margin-top: 15px !important; /* Ajuste esse valor para a distância que deseja */
            }}

            button[kind="primary"] {{
            background-color: #153e5a !important;
            border: none !important;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2) !important;
            }}

            /* 3. COR DA MENSAGEM DE SUCESSO */
            /* Muda o fundo e a cor do texto da caixa de sucesso */
            div[data-testid="stNotification"] > div {{
            background-color: rgba(64, 96, 100, 0.9) !important;
            color: white !important;
            border: 1px solid #6d8285 !important;
            }}

            /* --- Novo estilo para a logo da FUSVE (fora do card) --- */
            .fusve-container {{
                text-align: center; /* Centraliza horizontalmente */
                margin-top: 20px;   /* Espaço entre o final do card e a logo */
                margin-bottom: 20px; /* Espaço para o final da página não colar */
                width: 100%;        /* Garante que o container ocupe a largura da coluna */
                display: flex;
                justify-content: center; /* Alinhamento robusto para flex */
            }}

            .fusve-container img {{
                width: 110px;       /* Ajuste o tamanho da logo da FUSVE aqui */
                height: auto;       /* Mantém a proporção */
                opacity: 0.8;       /* Deixa levemente transparente para não brigar com o card */
                filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.1)); /* Sombra suave */
                background: transparent !important; /* Força fundo transparente */
            }}
            </style>
        """, unsafe_allow_html=True)

        # ----- LAYOUT DO LOGIN -----
        col1, col2, col3 = st.columns([0.5, 2, 0.5]) 
        
        with col2:
            # O container com border=True agora é o nosso retângulo branco sólido
            with st.container(border=True):
                
                # Injetamos a logo e os textos centralizados
                st.markdown(f'''
                <div class="logo-container">
                    <img src="data:image/png;base64,{bin_logo}">
                </div>
                <div style="text-align: center; width: 100%; line-height: 1.2;">
                    <span style="color: white; font-family: sans-serif; font-size: 14px; display: block;">SISTEMA</span>
                    <span style="color: white; font-family: sans-serif; font-size: 16px; font-weight: bold; display: block;">GERÊNCIA DE AUDITORIA INTERNA</span>
                    <span style="color: #822a2d; font-family: sans-serif; font-size: 10px; font-weight: bold; display: block; margin-top: 10px; margin-bottom: -20px;">Acesso Restrito!</span>
                </div>
            ''', unsafe_allow_html=True)

                # Campos de entrada (Streamlit renderiza isso dentro do container branco)
                usuario = st.text_input("", placeholder="👤 Digite seu usuário", key="user_login")
                senha = st.text_input("", type="password", placeholder="🔑 Digite sua senha", key="pass_login")
                
                # O botão encerra o conteúdo do card
                if st.button("Entrar", use_container_width=True, type="primary"):
                    if validar_login_no_banco(usuario, senha):
                        st.session_state["autenticado"] = True
                        st.success("Login realizado com sucesso!")
                        time_module.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")

            st.markdown(f'''
                    <div class="fusve-container">
                        <img src="data:image/png;base64,{bin_logo_fusve}">
                    </div>
                ''', unsafe_allow_html=True)
                        
        return False
    return True

def tela_consulta_detalhada():
    st.title("🔍 Consulta Detalhada de Processos")
    st.info("Selecione um processo abaixo para detalhar as etapas.")

    # 1. Usamos o session_state para carregar a lista apenas uma vez
    if "lista_processos" not in st.session_state:
        st.session_state["lista_processos"] = buscar_todos_processos()
    
    df_processos = st.session_state["lista_processos"]

    if not df_processos.empty:
        # Exibe a tabela para referência do usuário
        with st.expander("Ver lista de processos"):
            st.dataframe(df_processos, use_container_width=True,
                         column_config={
                             "area": "Área",
                             "codigo_processo": 'Nº Processo',
                             "nome_processo": "Processo",
                             "gestor": "Gestor Responsável",
                             "aprovacao": "Criticidade"

                         },
                         column_order=("area", "codigo_processo", "nome_processo", "gestor", "aprovacao")
                         )

        # Cria uma lista formatada para o selectbox
        # Exibe: "Código - Nome"
        opcoes = [f"{row['codigo_processo']} - {row['nome_processo']}" for _, row in df_processos.iterrows()]
        
        # Selectbox para escolha
        selecao = st.selectbox("Escolha o processo:", options=[""] + opcoes)

        # 2. Lógica de busca baseada na seleção
        if selecao:
            # Extrai apenas o código (antes do " - ")
            codigo_busca = selecao.split(" - ")[0]
            processo = buscar_processo_por_codigo(codigo_busca)
            st.metric("Status", processo.get('status', 'Ativo'))
            # Exibição visual da Aprovação
            aprov = processo.get('aprovacao', 'Em Aprovação')
            cor_aprov = "orange" if aprov == "Em Aprovação" else "green"
            st.metric("Criticidade", aprov)
            st.write(f"**Gestor:** {processo['responsavel_area']}")
            st.write(f"**Área:** {processo['nome_area']}")

            # --- Botões de ação rápida ---
            c_diag1, c_diag2 = st.columns([1, 2])
            with c_diag1:
                if processo.get('url_diagrama'):
                    st.link_button('Abrir Diagrama Macro', processo['url_diagrama'], use_container_width=True)
                else:
                    st.info("Sem diagrama macro")
            
            # --- NOVO EXPANDER ---
            with st.expander("Diagrama e aprovação da criticidade"):
                col_g1, col_g2 = st.columns(2)

                with col_g1:
                    st.write("**🔗 Link do Diagrama**")
                    novo_link = st.text_input("Inserir/Editar Link do Diagrama", value=processo.get('url_diagrama', ''), key=f"edit_link_{processo['id']}")
                    if st.button('Salvar Novo Link', key=f"btn_link_{processo['id']}"):
                        atualizar_status_processo(processo['id'], novo_link, "url_diagrama")
                        st.rerun()
                with col_g2:
                    st.write("**✅ Status de Aprovação**")
                    status_atual = processo.get('aprovacao', 'Em Aprovação')
                    if status_atual == "Em Aprovação":
                        if st.button("Aprovar Processo Agora", type="primary", use_container_width=True):
                            atualizar_status_processo(processo['id'], 'Aprovado', 'aprovacao')
                            st.rerun()
                    else:
                        if st.button("Reverter para 'Em Aprovação'", use_container_width=True):
                            atualizar_status_processo(processo['id'], "Em Aprovação", 'aprovacao')
                            st.rerun()

            with st.expander("📄 Ver Objetivo e Descrição Geral"):
                st.write(f"**Objetivo:** {processo['objetivo']}")
                st.write(f"**Descrição:** {processo['descricao']}")

            st.divider()

            # --- SEÇÃO DE ETAPAS (FILHOS) ---
            tab_lista, tab_cadastro = st.tabs(["📋 Etapas Existentes", "➕ Cadastrar Nova Etapa"])

            with tab_lista:
                etapas = listar_etapas_do_processo(processo['id'])
                if not etapas.empty:
                    for _, etapa in etapas.iterrows():
                        with st.expander(f"Etapa {etapa['codigo_etapa']} - {etapa['descricao_etapa']}"):
                            # Execução
                            st.subheader("Detalhes da Execução")
                            c1, c2 = st.columns(2)
                            c1.write(f"**Como é feito:** {etapa['como_e_feito']}")
                            c1.write(f"**Objetivo:** {etapa['objetivo_etapa']}")
                            c1.write(f"**Criticidade:** {etapa['criticidade_etapa']}")
                            c2.write(f"**Realizado corretamente:** {etapa['realizado_corretamente']}")
                            c2.write(f"**Política Interna:** {etapa['politica_interna']}")
                            
                            # Auditoria e Melhorias
                            c3, c4 = st.columns(2)
                            c3.write(f"**Análise Crítica:** {etapa['analise_critica']}")
                            c3.write(f"**Sugestão:** {etapa['sugestao_melhoria']}")
                            c4.write(f"**Necessidade Implantação:** {etapa['necessidade_implantacao']}")
                            c4.write(f"**Ganho Previsto:** {etapa['ganho_previsto']}")
                            
                            st.divider()
                            # Botões
                            b1, b2 = st.columns(2)
                            if etapa['link_diagrama_etapa']: b1.link_button("🖼️ Desenho da Etapa", etapa['link_diagrama_etapa'])
                            if etapa['manual_processo_link']: b2.link_button("📖 Manual do Processo", etapa['manual_processo_link'])
                            
                            st.divider()

                            # --- VISUALIZAÇÃO DE RISCOS (ATUALIZADA) ---
                            st.subheader("⚠️ Riscos desta Etapa")
                        
                            tab_v_risco, tab_c_risco = st.tabs(["📊 Visualizar Riscos", "➕ Adicionar Risco"])
                            
                            with tab_v_risco:
                                riscos_df = listar_riscos_etapa(etapa['id'])
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
                                with st.form(key=f"form_risco_{etapa['id']}", clear_on_submit=True):
                                    col1, col2 = st.columns(2)
                                    categoria = col1.selectbox("Categoria", ["Risco Inerente", "Risco de TI", "Risco de Fraude"], key=f"cat_{etapa['id']}")
                                    origem = col2.selectbox("Origem", ["Interna", "Externa"], key=f"ori_{etapa['id']}")
                                    
                                    fator = st.text_area("Fator de Risco", key=f"fat_{etapa['id']}")
                                    cons = st.text_area("Consequência", key=f"cons_{etapa['id']}")
                                    
                                    c3, c4 = st.columns(2)
                                    financeiro = c3.selectbox("Impacta Financeiramente?", [True, False], format_func=lambda x: "Sim" if x else "Não", key=f"fin_{etapa['id']}")
                                    ativo = c4.selectbox("Risco Ativo?", [True, False], format_func=lambda x: "Sim" if x else "Não", key=f"ativ_{etapa['id']}")
                                    
                                    imp = st.selectbox("Impacto", ["Baixo", "Médio", "Alto", "Muito Alto"], key=f"imp_{etapa['id']}")
                                    prob = st.selectbox("Probabilidade", ["Baixo", "Médio", "Alto", "Muito Alto"], key=f"prob_{etapa['id']}")
                                    
                                    mag = MAPA_RISCO.get((imp, prob), 0)
                                    cor, emoji = get_estilo_risco(mag)
                                    st.markdown(f'''<div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white; margin-bottom: 10px;">{emoji} Magnitude: {mag}</div>''', unsafe_allow_html=True)
                                    
                                    apetite = st.text_area("Apetite ao Risco", key=f"apet_{etapa['id']}")
                                    tratamento = st.text_area("Tratamento", key=f"trat_{etapa['id']}")
                                    info_adicional = st.text_area("Informações Adicionais", key=f"info_{etapa['id']}")
                                    doc_legal = st.text_area("Documentação Legal", key=f"doc_{etapa['id']}")
                                    
                                    if st.form_submit_button("💾 Salvar Risco", type="primary"):
                                        if not fator or not cons:
                                            st.warning("Preencha fator e consequência.")
                                        else:
                                            with st.spinner("Salvando risco da etapa na base de dados..."):
                                                dados_r = {
                                                    "etapa_id": etapa['id'], "cat": categoria, "fator": fator, "cons": cons,
                                                    "info": info_adicional, "fin": financeiro, "ativo": ativo, "ori": origem,
                                                    "doc": doc_legal, "imp": imp, "prob": prob, "mag": mag, "apet": apetite, "trat": tratamento
                                                }
                                                if salvar_risco_etapa(dados_r):
                                                # Feedback visual que sobrevive ao rerun
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
                                controles_df = listar_controles_da_etapa(etapa['id'])

                                for _, ctrl in controles_df.iterrows():
                                    # O título agora mostra o Risco de Origem e o Nome do Controle
                                    titulo = f"🛡️ Controle: {ctrl['nome_controle']} (Risco: {ctrl['risco_pai']})"

                                    if not controles_df.empty:
                                    
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
                                df_riscos_atuais = listar_riscos_etapa(etapa['id'])

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

                                        if st.form_submit_button("💾 Salvar Controle", type="primary"):
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
                    desc_etapa = c2.text_input("Título da Etapa")
                    como = st.text_area("Como é feito?")
                    obj_etapa = st.text_area("Objetivo?")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    correto = col_f1.selectbox("Realizado corretamente?", ["Sim", "Não", "Parcial"])
                    crit_etapa = col_f2.selectbox("Criticidade", ["Baixa", "Média", "Alta", "Crítica"])
                    executa = col_f3.text_input("Executor", value=processo['executor'])
                    link_bpmn = st.text_input("Link Diagrama")
                    link_manual = st.text_input("Link Manual")
                    politica = st.text_area("Política Interna")
                    analise = st.text_area("Análise Crítica")
                    melhoria = st.text_area("Sugestão de Melhoria")
                    col_f4, col_f5 = st.columns(2)
                    necessidade = col_f4.text_input("Necessidade")
                    ganho = col_f5.text_input("Ganho")
                    obrigacoes = st.text_input("Obrigações Reg.")
                    if st.form_submit_button("Salvar Detalhamento"):
                        with st.spinner("Salvando etapa na base de dados..."):
                            dados = {"p_id": int(processo['id']), "cod": prox_cod, "desc": desc_etapa, "como": como, "obj": obj_etapa, "real": correto, "link_d": link_bpmn, "pol": politica, "ana": analise, "sug": melhoria, "nec": necessidade, "gan": ganho, "obri": obrigacoes, "crit": crit_etapa, "man": link_manual}
                            if salvar_etapa_no_banco(dados):
                                st.success("Etapa salva!")
                                st.rerun()
        else:
            st.warning("Código não encontrado.")

def limpar_campos_por_prefixo(prefixo):
    for key in st.session_state.keys():
        if key.startswith(prefixo):
            st.session_state[key] = ""

# --- INICIALIZAÇÃO DE ESTADO ---
areas_dict = carregar_areas_banco()

def atualizar_id_area():
    nome_selecionado = st.session_state['area_selectbox']
    st.session_state['id_area_selecionado'] = areas_dict[nome_selecionado]
    st.session_state['codigo_processo'] = ""
    st.session_state['input_processo'] = "" 

if 'riscos' not in st.session_state: st.session_state['riscos'] = []
if 'deve_limpar' not in st.session_state: st.session_state['deve_limpar'] = False
if 'df_pendentes' not in st.session_state: st.session_state['df_pendentes'] = pd.DataFrame()

if 'id_area_selecionado' not in st.session_state and areas_dict:
    primeiro_nome = list(areas_dict.keys())[0]
    st.session_state['id_area_selecionado'] = areas_dict[primeiro_nome]


# --- 3. LIMPEZA PÓS-SALVO ---
if st.session_state['deve_limpar']:
    campos_to_reset = ["input_processo", "input_objetivo", "input_executor", "input_descricao", "input_etapa_ini", "input_etapa_fim", "input_produto", "codigo_processo", "area"]
    for campo in campos_to_reset:
        st.session_state[campo] = None if campo == "area" else ""
    st.session_state['riscos'] = []
    st.session_state['deve_limpar'] = False
    st.rerun()

# --- 4. FUNÇÕES DE SUPORTE ---
def validar_formulario():
    campos = ["input_processo", "input_objetivo", "input_executor", "input_descricao", "input_etapa_ini", "input_etapa_fim", "input_produto", "codigo_processo"]
    for c in campos:
        if not st.session_state.get(c):
            st.error(f"O campo '{c.replace('input_', '').replace('_', ' ').capitalize()}' é obrigatório.")
            return False
    if not st.session_state['riscos']:
        st.error("Adicione pelo menos um risco.")
        return False
    if not st.session_state.get("nome_0"):
        st.error("O Risco 1 precisa de uma descrição/nome")
        return False
    return True

def marcar_relatorio_gerado(codigo_processo):
    """Atualiza o status para 'Sim' na tabela de riscos, filtrando pelo código na tabela pai."""
    query = text("""
        UPDATE riscos 
        SET relatorio_gerado = 'Sim' 
        WHERE processo_id IN (
            SELECT id FROM processos WHERE codigo_processo = :codigo
        )
    """)
    with engine.begin() as conn:
        conn.execute(query, {"codigo": codigo_processo})


# --- 5. Execução do app ---

if login_screen():

    # --- SIDEBAR ---
    with st.sidebar:
        caminho_script = os.path.dirname(os.path.abspath(__file__))
        logo_fusve = os.path.join(caminho_script, "assets", "logo_fusve.png")
        
        if os.path.exists(logo_fusve):
            st.image(logo_fusve, width=200)

        opcao = st.radio("Menu", ["Diagnóstico dos Processos", "Detalhamento dos Processos", "Geração de Relatórios"])

        st.divider()
        # Adiciona um botão de Sair no topo ou fim do sidebar
        if st.button("Logout"):
            st.session_state['autenticado'] = False
            st.rerun()

    # --- 7. LÓGICA PRINCIPAL ---
    if opcao == "Diagnóstico dos Processos":
        st.title("Diagnóstico de Processos - FUSVE")
        st.markdown("""
        <div style='font-family: helvetica; color: #000000; font-size: 14px; line-height: 1.5;'>
            <p><strong>PASSO 1:</strong> PEDIR AO GESTOR PARA ESCREVER EM UM PAPEL O FLUXO DO PASSO A PASSO DO PROCESSO, INICIO AO FIM.</p>
            <p style='margin-top: 15px;'><strong>PASSO 2:</strong> ESCREVER ABAIXO OS PROCESSOS QUE FORAM SINALIZADOS NO FLUXO.</p>
        </div>
    """, unsafe_allow_html=True)
        st.subheader("1. Dados do Processo")
        st.selectbox(
        "Selecione a Área:", 
        list(areas_dict.keys()), 
        key="area_selectbox", 
        on_change=atualizar_id_area
    )
        # Garante que o ID esteja inicializado
        if 'id_area_selecionado' not in st.session_state:
            st.session_state['id_area_selecionado'] = list(areas_dict.values())[0]
        st.text_input("Nome do Processo:", key="input_processo", on_change=processar_codigo_inteligente,
                    help="PROCESSOS OU ATIVIDADES REALIZADOS: São todas as atividades realizadas pela área. (Existem fluxos distintos dentro desse processo? Se sim é preciso criar um processo para cada fluxo).")
        st.text_input("Código do Processo:", key="codigo_processo", disabled=True)
        st.text_area("O que é o processo?:", key="input_descricao")
        st.text_area("Funcionário(s) Que Executa(m)", key="input_executor", help="Funcionário(s) que executa(m) - Alçadas (Gestão ou operação?)")
        st.text_area("Onde Começa o Proceso?:", key="input_etapa_ini", help="Onde começa o processo? (Ex: Do envio do relatório x pela área y) - ETAPA INICIAL")
        st.text_area("Qual (is) o Produto (s) Final Desse Processo?:", key="input_produto", help="Qual(is) o(s) produto(s) final(is) desse processo? (Ex: Relatório, Planilha, Sistema, Word, etc)")
        st.text_area("Depois de Acabado, para onde envia?", key="input_etapa_fim", help="Depois de acabado, para onde envia? (Ex: Área x, Arquivo físico localizado em y, Arquivo Digital localizado no z, etc.) - ETAPA FINAL")
        st.text_area("Qual o Objetivo do Processo? e Por que faz?", key="input_objetivo")
        st.write("")
        st.markdown("""
        <div style='font-family: helvetica; color: #ff0000; font-size: 20px; line-height: 1;'>
            <p><strong>AVALIAÇÃO DA MAGNITUDE DO RISCO</strong></p>
            </div>
    """, unsafe_allow_html=True)
        st.subheader("2. Riscos Associados")
        for i, _ in enumerate(st.session_state['riscos']):
            st.markdown(f"**Risco {i+1}**")
            st.text_input(f"Nome do Risco:", key=f"nome_{i}", help="1º Existem Incertezas ou Riscos do OBJETIVO DO PROCESSO não ser cumprido corretamente? 2º  Categorizar os Riscos identificados em: (RISCOS INERENTES ao processo, RISCO DE T.I E RISCO DE FRAUDE vunerabilidades de atos de irregularidades)")
            st.text_area(f"Fator de Risco:", key=f"fator_{i}", help="Fator de risco, causa ou motivo desse risco acontecer?")
            st.text_area(f"Ponto de Melhoria:", key=f"melhoria_{i}", help="O que mais te incomoda nesse processo e pensa que deveria ser melhor?")
            st.text_area(f"Apetite ao risco:", key=f"apetite_{i}", help="Dentro do critério e classificação do risco, quanto o Gestor entende ser o mínimo aceitável de ocorrência de risco, levando em consideração as combinações para chegar ao risco bruto.")
            col_i, col_p = st.columns(2)
            with col_i: st.selectbox(f"Impacto:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"imp_{i}", help="Impacto do risco materializado")
            with col_p: st.selectbox(f"Probabilidade:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"prob_{i}", help="Probabilidade do risco acontecer? Mediante isso, podemos criar os níveis que iremos classificar a probabilidade do risco acontecer.")
            
            score_v = MAPA_RISCO.get((st.session_state.get(f"imp_{i}"), st.session_state.get(f"prob_{i}")), 0)
            cor, emoji = get_estilo_risco(score_v)
            st.markdown(f'<div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white;">{emoji} Risco Bruto (Impacto + Probabilidade): {score_v}</div>', unsafe_allow_html=True)
            st.text_area(f"Motivo:", key=f"motivo_{i}", help="Qual o motivo da classificação do nivel da probabilidade? - ANÁLISE")
            st.markdown("---")

        col_add, col_save = st.columns(2)
        if col_add.button("➕ Adicionar Risco"):
            st.session_state['riscos'].append({})
            st.rerun()
        if col_save.button("💾 Salvar Todos os Dados", type="primary"):
            if validar_formulario() and salvar_no_banco():
                st.success("Dados salvos!")
                st.session_state['deve_limpar'] = True
                st.rerun()

    elif opcao == "Detalhamento dos Processos":
        tela_consulta_detalhada()

    elif opcao == "Geração de Relatórios":
        st.title("Relatórios - FUSVE")
        
        if st.button("Atualizar Lista de Processos"):
            st.session_state['df_pendentes'] = buscar_processos_pendentes()
        
        if not st.session_state['df_pendentes'].empty:
            df = st.session_state['df_pendentes']
            st.dataframe(df)
            
            # O on_change limpa o 'pdf_pronto' toda vez que o usuário escolhe um processo novo
            codigo_selecionado = st.selectbox(
                "Selecione o Código do Processo:", 
                df['codigo_processo'].tolist(),
                on_change=lambda: st.session_state.pop('pdf_pronto', None)
            )

            if st.button("Gerar e Marcar como Pronto"):
                marcar_relatorio_gerado(codigo_selecionado)
                pdf_bytes = gerar_pdf_em_memoria(codigo_selecionado)
                
                if pdf_bytes:
                    st.session_state['pdf_pronto'] = bytes(pdf_bytes)
                    st.success(f"Processo {codigo_selecionado} concluído! Clique em baixar.")
                    st.rerun() 
                else:
                    st.error("Erro ao gerar PDF.")
            
            # Download button preenchido corretamente
            if 'pdf_pronto' in st.session_state:
                st.download_button(
                    label="📥 Baixar Relatório em PDF",
                    data=st.session_state['pdf_pronto'],
                    file_name=f"relatorio_processo_{codigo_selecionado}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("Nenhum processo pendente para gerar relatório.")
