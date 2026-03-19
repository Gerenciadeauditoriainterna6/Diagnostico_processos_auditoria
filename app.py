import streamlit as st
import os
import pandas as pd
from sqlalchemy import text
from database import engine
import time as time_module
import base64
from datetime import timedelta, datetime
from streamlit_local_storage import LocalStorage
from streamlit_pdf_viewer import pdf_viewer
from logic import (MAPA_RISCO, processar_codigo_inteligente, 
get_estilo_risco, salvar_no_banco, gerar_pdf_em_memoria, buscar_processos_pendentes, carregar_areas_banco,
buscar_processo_por_codigo, obter_proximo_codigo_etapa, salvar_etapa_no_banco, listar_etapas_do_processo, salvar_risco_etapa,
listar_riscos_etapa, buscar_todos_processos, salvar_controle_no_banco, validar_login_no_banco, atualizar_status_processo, 
atualizar_etapa_no_banco, criar_nova_auditoria, listar_auditorias_por_ano, buscar_auditoria_por_id, vincular_processo_a_auditoria, 
listar_processos_da_auditoria, salvar_checklist_eficacia, listar_checklists_da_auditoria, calcular_maturidade_por_pilar, salvar_conclusao_auditoria, 
buscar_conclusao_auditoria, get_resumo_trimestre, listar_processos_da_auditoria_com_riscos, listar_processos_disponiveis_para_auditoria,
remover_processo_da_auditoria
)

local_storage = LocalStorage()

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Diagnóstico FUSVE", layout="centered")

# --- 2. FUNÇÕES DE SESSÃO E IP (SUPABASE) ---

def get_base64(bin_file):
    """Lê um arquivo de imagem e retorna sua versão codificada em Base64"""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

def login_screen():
    """Gerencia a tela de login e a sessão de usuário."""

    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state['autenticado']:
        return True

    try:
        bin_fundo = get_base64(os.path.join("assets", "imagem_fundo.png"))
        bin_logo = get_base64(os.path.join("assets", "logo_auditoria_recortada_circulo.png"))
        bin_logo_auditoria = get_base64(os.path.join("assets", "logo_auditoria-removebg-preview.png"))
        bin_logo_fusve = get_base64(os.path.join("assets", "logo_fusve.png"))
    except Exception as e:
        st.error(f"erro ao carregar imagens: {e}")
        return False
    
    # --- BLOCO CSS PARA DESIGN DO LOGIN (SEU DESIGN ORIGINAL) ---
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
        with st.container(border=True):
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

            usuario = st.text_input("", placeholder="👤 Digite seu usuário", key="user_login")
            senha = st.text_input("", type="password", placeholder="🔑 Digite sua senha", key="pass_login")
            
            if st.button("Entrar", use_container_width=True, type="primary"):
                if validar_login_no_banco(usuario, senha):
                    # --- GRAVAÇÃO NO LOCAL STORAGE (ÚNICA MUDANÇA FUNCIONAL) ---
                    local_storage.setItem("usuario_audit", usuario)
                    
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_logado"] = usuario
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

def exibir_criterios_risco():
    """Exibe os critérios de Probabilidade e Impacto em um expander"""
    with st.expander("📋 **Critérios para Avaliação de Riscos**", expanded=False):
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.markdown("""
            ### 📊 **PROBABILIDADE**
            
            | Nível | Descrição |
            |-------|-----------|
            | **Baixa** | Pode ser que ocorra uma vez dentro de um ano, em função de historicamente bons controles sendo adotados. |
            | **Média** | Pode ser que ocorra mais de uma vez dentro de um ano, em função de controles moderados sendo adotados. |
            | **Alta** | Pode ser que ocorra mensalmente, em função de controles ineficazes sendo adotados. |
            | **Muito Alta** | Pode ser que ocorra diariamente, em função de controles ineficazes sendo adotados ou omitidos a execução. |
            """)
        
        with col_c2:
            st.markdown("""
            ### 💰 **IMPACTO**
            
            | Nível | Descrição |
            |-------|-----------|
            | **Baixo** | Desembolsos de até R$ 15.000,00, os riscos possuem consequências reversíveis em curto prazo com custos pouco baixos. |
            | **Médio** | Desembolsos de R$ 15.000,00 até R$ 55.000,00, os riscos possuem consequências reversíveis em curto e médio prazo com custos médios. |
            | **Alto** | Desembolso de R$ 55.000,00 até R$ 100.000,00, os riscos possuem consequências reversíveis em médio e longo prazo com custos altos. |
            | **Muito Alto** | Desembolso acima de R$ 100.000,00, os riscos possuem consequências reversíveis em médio e longo prazo com custos altos. |
            """)

def tela_visao_geral_processos():
    """Tela de visão geral de todos os processos mapeados, com filtros por área e auditoria"""
    
    st.title("📋 Visão Geral dos Processos Mapeados")
    st.caption("Consulte todos os processos já diagnosticados, com opções de filtro por área ou auditoria.")
    
    # ===== FILTROS =====
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        # Filtro por Área
        areas_dict = carregar_areas_banco()
        areas_list = ["Todas as Áreas"] + list(areas_dict.keys())
        filtro_area = st.selectbox("Filtrar por Área:", areas_list)
    
    with col_f2:
        # Filtro por Auditoria (ano/trimestre)
        # Buscar auditorias disponíveis
        df_auditorias = listar_auditorias_por_ano()
        if not df_auditorias.empty:
            opcoes_auditoria = ["Todas as Auditorias"] + [
                f"{row['codigo_auditoria']} - {row['titulo']}" 
                for _, row in df_auditorias.iterrows()
            ]
            filtro_auditoria = st.selectbox("Filtrar por Auditoria:", opcoes_auditoria)
        else:
            filtro_auditoria = "Todas as Auditorias"
            st.info("Nenhuma auditoria encontrada.")
    
    with col_f3:
        # Filtro por texto (busca rápida)
        filtro_texto = st.text_input("🔍 Buscar processo:", placeholder="Nome ou código...")
    
    # ===== CONSULTA PRINCIPAL =====
    query_base = """
        SELECT 
            p.id,
            p.codigo_processo,
            p.nome_processo,
            i.nome_area,
            p.aprovacao as criticidade,
            COUNT(DISTINCT r.id) as total_riscos,
            COALESCE(MAX(r.score_risco), 0) as maior_risco,
            COUNT(DISTINCT e.id) as total_etapas,
            COUNT(DISTINCT c.id) as total_controles
        FROM processos p
        JOIN informacoes_area i ON p.id_area = i.id_area
        LEFT JOIN riscos r ON p.id = r.processo_id
        LEFT JOIN etapas_processo e ON p.id = e.processo_id
        LEFT JOIN riscos_etapa re ON e.id = re.etapa_id
        LEFT JOIN controles_etapa c ON re.id = c.risco_id
        WHERE 1=1
    """
    
    params = {}
    
    # Aplicar filtro de área
    if filtro_area != "Todas as Áreas":
        id_area = areas_dict[filtro_area]
        query_base += " AND p.id_area = :id_area"
        params['id_area'] = id_area
    
    # Aplicar filtro de auditoria
    if filtro_auditoria != "Todas as Auditorias":
        # Extrair ID da auditoria da string selecionada
        cod_auditoria = filtro_auditoria.split(" - ")[0]
        query_base += """
            AND p.id IN (
                SELECT processo_id 
                FROM auditoria_processos 
                WHERE auditoria_id = (
                    SELECT id FROM auditorias WHERE codigo_auditoria = :cod_auditoria
                )
            )
        """
        params['cod_auditoria'] = cod_auditoria
    
    query_base += """
    GROUP BY p.id, i.nome_area
    ORDER BY 
        (string_to_array(p.codigo_processo, '.'))[1]::int,
        (string_to_array(p.codigo_processo, '.'))[2]::int,
        (string_to_array(p.codigo_processo, '.'))[3]::int
"""
    
    # Executar consulta
    with engine.connect() as conn:
        df_processos = pd.read_sql(text(query_base), conn, params=params)
    
    # Aplicar filtro de texto (em memória, após a consulta)
    if filtro_texto:
        filtro_texto = filtro_texto.lower()
        df_processos = df_processos[
            df_processos['nome_processo'].str.lower().str.contains(filtro_texto, na=False) |
            df_processos['codigo_processo'].str.lower().str.contains(filtro_texto, na=False)
        ]
    
    # ===== EXIBIÇÃO DOS RESULTADOS =====
    st.divider()
    st.subheader(f"📊 Resultados: {len(df_processos)} processos encontrados")
    
    if not df_processos.empty:
        # Métricas resumidas
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total de Processos", len(df_processos))
        with col_m2:
            st.metric("Riscos Mapeados", df_processos['total_riscos'].sum())
        with col_m3:
            st.metric("Etapas Mapeadas", df_processos['total_etapas'].sum())
        with col_m4:
            st.metric("Controles Mapeados", df_processos['total_controles'].sum())
        
        st.divider()
        
        # Tabela interativa
        st.dataframe(
            df_processos[[
                'codigo_processo', 'nome_processo', 'nome_area',
                'criticidade', 'maior_risco', 'total_riscos', 'total_etapas', 'total_controles'
            ]],
            use_container_width=True,
            column_config={
                "codigo_processo": "Código",
                "nome_processo": "Processo",
                "nome_area": "Área",
                "criticidade": "Criticidade",
                "maior_risco": "Maior Risco",
                "total_riscos": "Qtd Riscos",
                "total_etapas": "Etapas",
                "total_controles": "Controles"
            },
            hide_index=True
        )
        
        # Opção de expandir para ver detalhes completos
        with st.expander("📋 Ver detalhes completos dos processos"):
            # Selectbox para escolher um processo e ver detalhes
            opcoes_detalhe = [f"{row['codigo_processo']} - {row['nome_processo']}" for _, row in df_processos.iterrows()]
            processo_selecionado = st.selectbox("Selecione um processo para ver detalhes:", [""] + opcoes_detalhe)
            
            if processo_selecionado:
                codigo = processo_selecionado.split(" - ")[0]
                processo = buscar_processo_por_codigo(codigo)
                
                if processo:
                    st.write(f"**Objetivo:** {processo['objetivo']}")
                    st.write(f"**Descrição:** {processo['descricao']}")
                    st.write(f"**Executor:** {processo['executor']}")
                    
                    # Mostrar etapas resumidas
                    etapas = listar_etapas_do_processo(processo['id'])
                    if not etapas.empty:
                        st.write("**Etapas:**")
                        for _, etapa in etapas.iterrows():
                            st.caption(f"• {etapa['codigo_etapa']} - {etapa['descricao_etapa']}")
    else:
        st.warning("Nenhum processo encontrado com os filtros selecionados.")

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

                if st.form_submit_button("Criar Auditoria", type="primary"):
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
                            st.markdown(f"📅 {row['data_inicio'] or 'TBD'} a {row['data_fim'] or 'TBD'}")

                        with col4:
                            if st.button("🔍 Detalhar", key=f"btn_{row['id']}"):
                                st.session_state['auditoria_selecionada'] = row['id']
                                st.session_state['tela_atual'] = 'detalhe_auditoria'
                                st.rerun()
                        
                        st.divider()

def tela_detalhe_auditoria():

    """Tela de detalhamento de uma auditoria específica"""

     # CSS para reduzir fonte dos métricas
    st.markdown("""
        <style>
            /* Reduz tamanho dos valores das métricas */
            [data-testid="stMetricValue"] {
                font-size: 14px !important;
            }
            
            /* Reduz tamanho dos labels das métricas */
            [data-testid="stMetricLabel"] {
                font-size: 14px !important;
            }
            
            /* Reduz tamanho da delta (se houver) */
            [data-testid="stMetricDelta"] {
                font-size: 12px !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Verifica se temos uma auditoria selecionada
    if 'auditoria_selecionada' not in st.session_state:
        st.error("Nenhuma auditoria selecionada.")
        if st.button("🔙 Voltar para lista de auditorias"):
            st.session_state.pop('auditoria_selecionada', None)
            st.rerun()
        return
    
    auditoria_id = st.session_state['auditoria_selecionada']
    
    # Busca dados da auditoria
    auditoria = buscar_auditoria_por_id(auditoria_id)
    
    if not auditoria:
        st.error("Auditoria não encontrada.")
        return
    
    # Cabeçalho com informações da auditoria
    st.title(f"📋 {auditoria['titulo']}")
    
    # Métricas em colunas
    st.metric("Área", auditoria['nome_area'])

    col1, col2, col3 = st.columns(3)
    
    with col1:
        status = auditoria['status']
        if status == "Planejamento":
            st.metric("Status", "🟡 Planejamento")
        elif status == "Em Execução":
            st.metric("Status", "🟢 Em Execução")
        else:
            st.metric("Status", "✅ Concluída")
    
    with col2:
        st.metric("Trimestre", f"{auditoria['trimestre']}º/{auditoria['ano']}")
    
    with col3:
        st.metric("Responsável", auditoria.get('responsavel_equipe', ['Não definido'])[0] if auditoria.get('responsavel_equipe') else "Não definido")
    
    # Datas
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.info(f"📅 **Início:** {auditoria['data_inicio'] or 'Não definida'}")
    with col_d2:
        st.info(f"📅 **Término:** {auditoria['data_fim'] or 'Não definida'}")
    
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
            # Mostra cada processo em um card
            for _, row in df_processos.iterrows():
                # Define cor baseada no maior risco
                cor, emoji = get_estilo_risco(row['maior_risco'])
                
                with st.container(border=True):
                    col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
                    
                    with col_p1:
                        st.markdown(f"**{row['codigo_processo']} - {row['nome_processo']}**")
                        st.caption(f"📝 Motivo: {row['motivo_selecao'] or 'Não informado'}")
                    
                    with col_p2:
                        # Status de avaliação
                        status_aval = row['status_avaliacao']
                        if status_aval == "Pendente":
                            st.markdown("⏳ **Pendente**")
                        elif status_aval == "Em Andamento":
                            st.markdown("🔄 **Em Andamento**")
                        else:
                            st.markdown("✅ **Avaliado**")
                    
                    with col_p3:
                        # Score de risco
                        st.markdown(f"<span style='background-color: {cor}; padding: 5px 10px; border-radius: 5px; color: white; font-weight: bold;'>{emoji} Risco: {row['maior_risco'] or 'N/A'}</span>", unsafe_allow_html=True)
                    
                    # Botões de ação para o processo
                    col_b1, col_b2, col_b3 = st.columns([1, 1, 3])
                    
                    with col_b1:
                        if st.button("🔍 Ver Detalhes", key=f"ver_{row['processo_id']}"):
                            st.session_state['processo_detalhe'] = row['processo_id']
                            st.session_state['tela_atual'] = 'detalhe_processo'
                            st.rerun()
                    
                    with col_b2:
                        if st.button("📝 Checklists", key=f"check_{row['processo_id']}"):
                            st.session_state['processo_checklist'] = row['processo_id']
                            st.session_state['aba_ativa'] = 1  # Muda para aba de checklists
                            st.rerun()
                    
                    with col_b3:
                        # Botão de remover com confirmação
                        remover_key = f"rm_{row['processo_id']}_{row['processo_id']}"
                        if st.button("🗑️ Remover", key=f"rm_{row['processo_id']}"):
                            st.session_state[f"confirmar_remocao_{row["processo_id"]}"] = True
                        
                        # Mostrar confirmação se necessário
                        if st.session_state.get(f'confirmar_remocao_{row['processo_id']}', False):
                            st.warning(f"remover processo **{row['codigo_processo']}**?")
                            col_sim, col_nao = st.columns(2)

                            with col_sim:
                                if st.button("✅ Sim, remover", key=f"conf_sim_{row['processo_id']}"):
                                    if remover_processo_da_auditoria(auditoria_id, row['processo_id']):
                                        st.success("Processo removido!")
                                        # Limpar estado de confirmação
                                        st.session_state.pop(f"confirmar_remocao_{row['processo_id']}", None)
                                        time_module.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Erro ao remover processo.")
                            with col_nao:
                                if st.button("❌ Não", key=f"conf_nao_{row['processo_id']}"):
                                    st.session_state.pop(f'confirmar_remocao_{row["processo_id"]}', None)
                                    st.rerun()
                        
                            
        
        st.divider()
        
        # Seção para adicionar novos processos
        with st.expander("➕ Adicionar novo processo à auditoria"):
            # Buscar processos da área que NÃO estão nesta auditoria
            df_disponiveis = listar_processos_disponiveis_para_auditoria(
                auditoria_id=auditoria_id,
                id_area=auditoria['id_area']
            )
            
            if df_disponiveis.empty:
                st.success("✅ Todos os processos da área já foram selecionados para esta auditoria!")
                st.caption("Não há processos dispibíveis para adicionar")
            else:    
                st.caption(f"**{len(df_disponiveis)}** processos disponíveis para selecionar.")
                
                # Selectbox para escolher o processo
                opcoes_processos = []
                for _, row in df_disponiveis.iterrows():
                    risco_info = f" (Risco: {int(row['maior_risco'])})" if row['maior_risco'] > 0 else " (Sem risco mapeado)"
                    opcoes_processos.append({
                        "id": row['id'],
                        "display": f"{row['codigo_processo']} - {row['nome_processo']}{risco_info}"
                    })
            
            display_list = [item["display"] for item in opcoes_processos]
            id_map = {item['display']: item["id"] for item in opcoes_processos}

            processo_selecionado_display = st.selectbox(
                "Selecione o Processo:",
                options=display_list,
                key="select_processo_disponivel"
            )

            # Campo para motivo de seleção
            motivo = st.text_area(
                "Motivo da seleção (por que este processo será auditado?):",
                placeholder="Ex: Processo com risco muito alto (score 11), crítico para a área...",
                key="motivo_novo_processo"
            )

            # Botão para adicionar
            col_add, col_cancel = st.columns([1, 3])
            with col_add:
                if st.button("✓ Adicionar à auditoria", type="primary", use_container_width=True):
                    if processo_selecionado_display:
                        processo_id = id_map[processo_selecionado_display]

                        # Chamar a função para vincular
                        if vincular_processo_a_auditoria(auditoria_id, processo_id, motivo):
                            st.success("✅ Processo adicionado com sucesso!")
                            st.session_state['processo_adicionado'] = True
                            time_module.sleep(1)
                            st.rerun()
                        else:
                            st.error("Erro ao adicionar processo, tente novamente.")
                    else:
                        st.warning("Selecione um processo.")
            with col_cancel:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.pop('mostrar_selecao_processos', None)
                    st.rerun()

            # Placeholder - por enquanto, vamos criar a função depois
            st.info("Carregando processos disponíveis...")
            
            # Botão para buscar (temporário)
            if st.button("📋 Carregar processos disponíveis"):
                st.session_state['mostrar_selecao'] = True
                st.rerun()
            
            # Quando tiver a função, será assim:
            if st.session_state.get('mostrar_selecao', False):
                # Aqui vamos implementar a busca real
                st.write("(Aguardando implementação da função de busca)")
   
   
   
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
    if st.button("← Voltar para lista de auditorias"):
        st.session_state.pop('auditoria_selecionada', None)
        st.rerun()    

def tela_detalhe_processo_auditoria():
    """Tela de detalhamento de um processo dentro do contexto da auditoria"""
    
    if 'processo_detalhe' not in st.session_state or 'auditoria_selecionada' not in st.session_state:
        st.error("Processo ou auditoria não selecionados.")
        if st.button("Voltar"):
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
        if st.button("Voltar"):
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
    if st.button("← Voltar para a auditoria"):
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
            if st.button("🚫 Cancelar e Fechar Edição", use_container_width=True):
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
                if st.form_submit_button("💾 Atualizar Etapa", type="primary", use_container_width=True):
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
                                    
                                    if st.form_submit_button("💾 Salvar Risco", type="primary"):
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

            if st.form_submit_button("Salvar Detalhamento", type="primary"):
                dados = {
                    "p_id": int(processo['id']), "cod": prox_cod, "desc": desc_etapa, "oque": oque,
                    "status": status, "como": como, "obj": obj_etapa, "real": correto, "link_d": link_bpmn,
                    "pol": politica, "ana": analise, "sug": melhoria, "nec": necessidade, "gan": ganho,
                    "obri": obrigacoes, "crit": crit_etapa, "man": link_manual
                }
                if salvar_etapa_no_banco(dados, auditoria_id=auditoria_id):
                    st.success("Etapa salva!")
                    st.rerun()

# --- 5. Execução do app ---

def main():
    # 1. Tenta ler o usuário salvo no navegador (Local Storage)
    # Diferente do cookie, aqui a leitura é imediata
    usuario_cache = local_storage.getItem("usuario_audit")
    
    # --- PAINEL DE DEBUG (Opcional: Pode remover quando tudo estiver ok) ---
    #with st.expander("🔍 Diagnóstico de Persistência", expanded=False):
        #st.write(f"Usuário no LocalStorage: {usuario_cache}")

    # 2. Lógica de Reautenticação Automática (F5)
    if not st.session_state.get('autenticado'):
        # Verificamos se o cache existe e não é uma string vazia/nula do JS
        if usuario_cache and usuario_cache not in ["undefined", "null", "None"]:
            st.session_state['autenticado'] = True
            st.session_state['usuario_logado'] = usuario_cache
            st.rerun()

    # 3. Bloqueio de Acesso
    if not st.session_state.get('autenticado'):
        login_screen()
        st.stop()  # Interrompe a execução aqui se não estiver logado

    # --- SE CHEGOU AQUI, O USUÁRIO ESTÁ AUTENTICADO ---

    # --- SIDEBAR ---
    with st.sidebar:
        caminho_script = os.path.dirname(os.path.abspath(__file__))
        logo_auditoria_path = os.path.join(caminho_script, "assets", "logo_auditoria-removebg-preview.png")
        
        if os.path.exists(logo_auditoria_path):
            st.image(logo_auditoria_path, width=200)

        # Exibe o nome do usuário logado para confirmação
        st.markdown(f"👤 **Usuário:** {st.session_state.get('usuario_logado', 'Audit')}")
        
        opcao = st.radio(
            "Menu", 
                [
                    #"📅 Plano Anual de Auditoria",
                    "🔍 Diagnóstico dos Processos",
                    "📋 Detalhamento dos Processos",        
                    "👁️ Visão Geral do Diagnóstico"
                    #"✅ Checklists de Eficácia",           
                    #"📊 Resultados e Pareceres",
                    #"📄 Geração de Relatórios"           
                ]
            )

        st.divider()
        
        if st.sidebar.button("Sair (Logout)", use_container_width=True):
            # 1. Remove a informação do navegador
            try:
                local_storage.deleteItem("usuario_audit")
            except:
                local_storage.setItem("usuario_audit", "null")
            
            # 2. Em vez de .clear(), limpamos apenas o que interessa
            # Isso evita o KeyError nos widgets (selectbox, etc)
            st.session_state["autenticado"] = False
            st.session_state["usuario_logado"] = None
            
            # 3. Força o recarregamento
            st.rerun()

    # --- LÓGICA PRINCIPAL ---
    if opcao == "🔍 Diagnóstico dos Processos":
        st.title("Diagnóstico de Processos - FUSVE")
        st.markdown("""
        <div style='font-family: helvetica; color: #000000; font-size: 14px; line-height: 1.5;'>
            <p><strong>PASSO 1:</strong> PEDIR AO GESTOR PARA ESCREVER EM UM PAPEL O FLUXO DO PASSO A PASSO DO PROCESSO, INICIO AO FIM.</p>
            <p style='margin-top: 15px;'><strong>PASSO 2:</strong> ESCREVER ABAIXO OS PROCESSOS QUE FORAM SINALIZADOS NO FLUXO.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ===== NOVO: SELEÇÃO MANUAL DA AUDITORIA (SEM OPÇÃO "NÃO VINCULAR") =====
        st.subheader("0. Vincular à Auditoria")

        # Função para buscar auditorias disponíveis para a área
        def listar_auditorias_para_area(id_area):
            """Retorna todas as auditorias da área (qualquer trimestre/ano)"""
            query = text("""
                SELECT id, codigo_auditoria, titulo, trimestre, ano, status
                FROM auditorias
                WHERE id_area = :id_area
                AND status IN ('Planejamento', 'Em Execução')
                ORDER BY ano DESC, trimestre DESC
            """)
            
            with engine.connect() as conn:
                return pd.read_sql(query, conn, params={"id_area": id_area})

        # Selectbox de área (já existente)
        st.selectbox(
            "Selecione a Área:", 
            list(areas_dict.keys()), 
            key="area_selectbox", 
            on_change=atualizar_id_area
        )

        # Garante que o ID esteja inicializado
        if 'id_area_selecionado' not in st.session_state:
            st.session_state['id_area_selecionado'] = list(areas_dict.values())[0]

        # Buscar auditorias disponíveis para a área selecionada
        id_area_atual = st.session_state['id_area_selecionado']
        df_auditorias_area = listar_auditorias_para_area(id_area_atual)

        if not df_auditorias_area.empty:
            # Criar opções para o selectbox
            opcoes_auditoria = []
            for _, row in df_auditorias_area.iterrows():
                status_emoji = "🟡" if row['status'] == 'Planejamento' else "🟢"
                opcoes_auditoria.append({
                    "id": row['id'],
                    "display": f"{status_emoji} {row['codigo_auditoria']} - {row['titulo']} ({row['ano']} {row['trimestre']}º trim)"
                })
            
            display_list = [item["display"] for item in opcoes_auditoria]
            id_map = {item["display"]: item["id"] for item in opcoes_auditoria}
            
            # Selectbox SEM a opção "Não vincular"
            auditoria_escolhida = st.selectbox(
                "Escolha a auditoria para vincular este processo:",
                options=display_list,
                help="Selecione a auditoria à qual este processo pertence."
            )
            
            # Guardar o ID da auditoria escolhida
            st.session_state['auditoria_diagnostico'] = id_map[auditoria_escolhida]
            
            # Mostrar confirmação
            auditoria_selecionada = df_auditorias_area[df_auditorias_area['id'] == id_map[auditoria_escolhida]].iloc[0]
            st.success(f"✅ Processo será vinculado à auditoria: **{auditoria_selecionada['codigo_auditoria']}**")
            
        else:
            st.warning(f"⚠️ Nenhuma auditoria encontrada para esta área. Crie uma em '📋 Detalhamento dos Processos' primeiro.")
            if 'auditoria_diagnostico' in st.session_state:
                st.session_state.pop('auditoria_diagnostico', None)

        st.divider()
        
        # ===== RESTANTE DO SEU CÓDIGO (INALTERADO) =====
        st.subheader("1. Dados do Processo")
        
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
            exibir_criterios_risco()
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
                # ===== NOVO: Vincular à auditoria após salvar =====
                if 'auditoria_diagnostico' in st.session_state and 'processo_id' in st.session_state:
                    auditoria_id = st.session_state['auditoria_diagnostico']
                    processo_id = st.session_state.get('ultimo_processo_id')
                    
                    if processo_id:
                        vincular_processo_a_auditoria(
                            auditoria_id=auditoria_id,
                            processo_id=processo_id,
                            motivo="Processo identificado durante diagnóstico da área"
                        )
                        st.success("Processo vinculado à auditoria com sucesso!")
                
                st.success("Dados salvos!")
                st.session_state['deve_limpar'] = True
                st.rerun()

    elif opcao == "👁️ Visão Geral do Diagnóstico":
        #tela_consulta_detalhada() -> Antiga função
        tela_visao_geral_processos()

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

    elif opcao == "📅 Plano Anual de Auditoria":
        
        # 1. CSS ULTRA AGRESSIVO
        # Aqui atacamos o 'stApp', que é o pai de todos os elementos
        st.markdown("""
            <style>
                /* Remove o limite de largura de TODA a página */
                .main .block-container {
                    max-width: 98vw !important;
                    padding-left: 1rem !important;
                    padding-right: 1rem !important;
                }
                
                /* Força o título e textos a irem para o canto esquerdo real */
                .stMarkdown, .stTitle, .stText {
                    width: 100% !important;
                    text-align: left !important;
                }

                /* Alvo: O visualizador de PDF */
                #pdfViewer, .scrolling-container {
                    width: 95vw !important;
                    max-width: 95vw !important;
                    margin-left: 0 !important;
                }

                /* Garante que os frames internos não limitem a largura */
                iframe {
                    width: 100% !important;
                }
            </style>
        """, unsafe_allow_html=True)

        st.title("📊 Plano Anual de Auditoria - 2026")
        st.write("Visualize abaixo as diretrizes e o cronograma para o ano atual.")

        # Caminho dinâmico (Assets)
        caminho_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "plano_auditoria_2026.pdf")

        if os.path.exists(caminho_pdf):
            try:
                # 2. Chamada sem largura fixa para deixar o CSS acima mandar
                # Aumentei a resolução para não perder qualidade ao esticar
                pdf_viewer(caminho_pdf, height=900)
            except Exception as e:
                st.error(f"Erro ao carregar o visualizador: {e}")
            
            st.divider()
            
            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label="📥 Baixar Plano Anual (PDF)",
                    data=f,
                    file_name="Plano_Auditoria_2026.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ Arquivo não encontrado na pasta assets.")

    elif opcao == "📋 Detalhamento dos Processos": #@ Chamaremos de detalhamento dos processos
        # Verifica se há uma auditoria selecionada para detalhar
        if 'processo_detalhe' in st.session_state:
            tela_detalhe_processo_auditoria()
        # Verifica se há uma auditoria selecionada para detalhar
        elif 'auditoria_selecionada' in st.session_state:
            tela_detalhe_auditoria()
        else:
            tela_auditorias_trimestrais()



            
# --- DISPARADOR FINAL ---

if __name__ == "__main__":
    main()
