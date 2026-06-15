"""
Módulo de Diagnóstico de Processos
"""
# ===== MIGRAÇÃO PARA FLASK =====
# Streamlit removido - sistema agora usa Flask
# import streamlit as st  # REMOVIDO

# Placeholder para evitar erros (as funções Streamlit não serão chamadas no Flask)
class _DummyStreamlit:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

st = _DummyStreamlit()
from sqlalchemy import text
from database import engine
import pandas as pd
import time as time_module
from datetime import datetime, timedelta
from modules.execucao.areas import carregar_areas_banco
from modules.shared.utils import exibir_criterios_risco, exibir_descricao_categorias
from modules.shared.validators import validar_formulario
from logic import (listar_riscos_do_processo, normalizar_valor_risco, buscar_processo_por_codigo, listar_executores_processo,
listar_funcionarios_area, processar_codigo_inteligente, listar_funcionarios_por_area, validar_basicos, salvar_informacoes_basicas,
listar_categorias, MAPA_RISCO, get_estilo_risco, salvar_no_banco, vincular_processo_a_auditoria, salvar_edicao_processo_completa)

areas_dict = carregar_areas_banco()

# ==== FUNÇÕES AUXILIARES ====

def listar_auditorias_para_area(id_area):
    query = text("""
        SELECT id, codigo_auditoria, titulo, trimestre, ano, status
        FROM auditorias
        WHERE id_area = :id_area
        ORDER BY ano DESC, trimestre DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"id_area": id_area})

def atualizar_id_area():
    areas = carregar_areas_banco()
    nome_selecionado = st.session_state['area_selectbox']
    st.session_state['id_area_selecionado'] = areas[nome_selecionado]
    st.session_state['codigo_processo'] = ""
    st.session_state['input_processo'] = ""
    # Limpar auditoria selecionada para forçar recarregamento
    if 'auditoria_diagnostico' in st.session_state:
        st.session_state.pop('auditoria_diagnostico', None)

def atualizar_id_area_edit():
        """Atualiza o ID da área selecionada na aba de edição"""
        areas = carregar_areas_banco()
        nome_selecionado = st.session_state['area_selectbox_edit']
        st.session_state['id_area_selecionado_edit'] = areas[nome_selecionado]
        st.session_state['codigo_processo'] = ""
        st.session_state['input_processo'] = ""

def carregar_riscos_processo(processo_id):
    """Carrega os riscos do processo para a session_state"""
    df_riscos = listar_riscos_do_processo(processo_id)
    
    if not df_riscos.empty:
        # Limpar riscos existentes
        st.session_state['riscos'] = []
        
        # Limpar keys antigas
        keys_to_remove = [key for key in st.session_state.keys() 
                         if any(key.startswith(prefix) for prefix in 
                               ['nome_', 'fator_', 'melhoria_', 'apetite_', 
                                'imp_', 'prob_', 'motivo_', 'categorias_'])]
        for key in keys_to_remove:
            st.session_state.pop(key)
        
        # Carregar cada risco
        for idx, (_, row) in enumerate(df_riscos.iterrows()):
            st.session_state['riscos'].append({})
            
            # Preencher campos básicos
            st.session_state[f'nome_{idx}'] = row['nome_risco'] or ""
            st.session_state[f'fator_{idx}'] = row['fator_risco'] or ""
            st.session_state[f'melhoria_{idx}'] = row['melhoria'] or ""
            st.session_state[f'apetite_{idx}'] = row['apetite_risco'] or ""
            st.session_state[f'motivo_{idx}'] = row['motivo_risco'] or ""
            
            # Carregar categorias
            st.session_state[f'categorias_{idx}'] = row['categorias_ids'] if row['categorias_ids'] else []
            
            # NORMALIZAR impacto e probabilidade
            st.session_state[f'imp_{idx}'] = normalizar_valor_risco(row['impacto'])
            st.session_state[f'prob_{idx}'] = normalizar_valor_risco(row['probabilidade'])
    else:
        st.session_state['riscos'] = []

def carregar_dados_processo_para_edicao(processo_id):
    """Carrega os dados de um processo existente para edição"""
    
    # Buscar o código do processo
    query = text("SELECT codigo_processo FROM processos WHERE id = :id")
    with engine.connect() as conn:
        resultado = conn.execute(query, {"id": processo_id}).fetchone()
    
    if not resultado:
        return None
    
    codigo = resultado[0]
    processo = buscar_processo_por_codigo(codigo)
    
    if not processo:
        return None
    
    # ===== CARREGAR DADOS BÁSICOS =====
    st.session_state['input_processo'] = processo.get('nome_processo', '')
    st.session_state['codigo_processo'] = processo.get('codigo_processo', '')
    st.session_state['processo_existente_id'] = processo['id']
    
    # ===== CARREGAR EXECUTORES =====
    executores_ids = listar_executores_processo(processo_id)
    st.session_state['executores_selecionados'] = executores_ids
    
    # ===== CARREGAR DETALHAMENTO =====
    st.session_state['input_objetivo'] = processo.get('objetivo', '')
    st.session_state['input_descricao'] = processo.get('descricao', '')
    st.session_state['input_etapa_ini'] = processo.get('etapa_ini', '')
    st.session_state['input_etapa_fim'] = processo.get('etapa_fim', '')
    st.session_state['input_produto'] = processo.get('produto', '')
    
    # ===== CARREGAR RISCOS =====
    carregar_riscos_processo(processo['id'])
    
    # ===== ATIVAR FLAG DE INFORMAÇÕES BÁSICAS SALVAS =====
    st.session_state['info_basicas_salvas'] = True
    
    return True

def verificar_e_carregar_processo():
    """
    Verifica se o processo já existe no banco.
    Se existir, carrega todos os dados para edição.
    Retorna True se encontrou, False se é novo.
    """
    nome_processo = st.session_state.get("input_processo", "").strip()
    id_area = st.session_state.get("id_area_selecionado")
    
    if not nome_processo or not id_area:
        return False
    
    # Buscar processo pelo nome e área
    query = text("""
        SELECT id, codigo_processo, objetivo, executor, descricao, 
               etapa_ini, etapa_fim, produto
        FROM processos 
        WHERE id_area = :id_area AND nome_processo = :nome
    """)
    
    with engine.connect() as conn:
        resultado = conn.execute(query, {
            "id_area": id_area,
            "nome": nome_processo
        }).mappings().first()
    
    if resultado:
        # Processo existe! Carregar todos os dados
        st.session_state['processo_existente_id'] = resultado['id']
        st.session_state['codigo_processo'] = resultado['codigo_processo']
        st.session_state['input_objetivo'] = resultado['objetivo'] or ""
        st.session_state['input_executor'] = resultado['executor'] or ""
        st.session_state['input_descricao'] = resultado['descricao'] or ""
        st.session_state['input_etapa_ini'] = resultado['etapa_ini'] or ""
        st.session_state['input_etapa_fim'] = resultado['etapa_fim'] or ""
        st.session_state['input_produto'] = resultado['produto'] or ""
        
        # Mostrar mensagem de que está editando
        st.info(f"📝 Processo **{nome_processo}** já existe. Carregando dados para edição...")
        return True
    
    # Processo não existe - limpar ID de edição
    if 'processo_existente_id' in st.session_state:
        st.session_state.pop('processo_existente_id', None)
    return False

def gerar_codigo_auditoria(area_nome, ano, trimestre):
    """Gerar o código da auditoria no padrão AUD-SIGLA-ANO-TRIMESTRE"""
    
    # Extrair sigla
    if ' - ' in area_nome:
        sigla = area_nome.split(' - ')[-1].strip()
    elif '-' in area_nome:
        sigla = area_nome.split('-')[-1].strip()
    else:
        # Pegar primeiras letras de cada palavra
        sigla = ''.join([p[0] for p in area_nome.split() if p])[:3].upper()
    
    # Garantir que a sigla tenha no máximo 5 caracteres
    sigla = sigla[:5].upper()
    
    return f"AUD-{sigla}-{ano}-{trimestre}"

# Função auxiliar para manter o expander aberto
def manter_expander_aberto(indice):
    """Callback para manter o expander aberto quando houver interação"""
    if 'expanders_abertos' not in st.session_state:
        st.session_state['expanders_abertos'] = {}
    st.session_state['expanders_abertos'][indice] = True

# Função auxiliar para manter o expander aberto na edição
def manter_expander_aberto_edit(indice):
    """Callback para manter o expander aberto quando houver interação na edição"""
    if 'edit_expanders_abertos' not in st.session_state:
        st.session_state['edit_expanders_abertos'] = {}
    st.session_state['edit_expanders_abertos'][indice] = True

# ==== FUNÇÕES DAS ABAS DENTRO DE DIAGNÓSTICO DOS PROCESSOS ====

def _tela_novo_processo():
    """Sub-tela de cadastro de novo processo"""
    from logic import calcular_tempo
    from modules.execucao.auditorias import criar_nova_auditoria

    # ===== INICIALIZAR ESTADOS DO FORMULÁRIO =====
    if 'mostrar_form_auditoria' not in st.session_state:
        st.session_state['mostrar_form_auditoria'] = False
    # ==== INICIALIZAR DICIONPARIO PARA CONTROLAR EXPANDERS ABERTOS ====
    if 'expanders_abertos' not in st.session_state:
        st.session_state['expanders_abertos'] = {}

    # ===== RESETAR ESTADO DA ÁREA AO ENTRAR NA TELA =====
    # Forçar sincronização entre o selectbox e o session_state
    if 'area_selectbox' in st.session_state and 'id_area_selecionado' in st.session_state:
        areas_dict = carregar_areas_banco()
        nome_atual = st.session_state['area_selectbox']
        if nome_atual in areas_dict:
            id_correto = areas_dict[nome_atual]
            if st.session_state['id_area_selecionado'] != id_correto:
                st.session_state['id_area_selecionado'] = id_correto
                # Limpar auditoria antiga
                if 'auditoria_diagnostico' in st.session_state:
                    st.session_state.pop('auditoria_diagnostico', None)
    st.markdown("""
        <style>
            /* Estiliza o formulário de novo processo - usando o container pai */
            .stForm {
                background-color: #ffffff !important;
                border-radius: 16px !important;
                padding: 24px !important;
                border: 1px solid #e0e0e0 !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
                margin-bottom: 20px !important;
            }
            
            /* Input em foco */
            .stForm input:focus,
            .stForm textarea:focus {
                border-color: #1848d8 !important;
                outline: none !important;
                box-shadow: 0 0 0 2px rgba(24, 72, 216, 0.2) !important;
            }
            
            /* Estiliza os labels */
            .stForm label {
                color: #48606c !important;
                font-weight: 500 !important;
                margin-bottom: 4px !important;
            }
            
            /* Estiliza o campo desabilitado (código do processo) */
            .stForm input:disabled {
                background-color: #e9ecef !important;
                color: #6c757d !important;
                cursor: not-allowed !important;
            }
            
            /* Botões do formulário */
            .stForm .stFormSubmitButton button {
                background-color: #1848d8 !important;
                color: white !important;
                border-radius: 8px !important;
                padding: 8px 16px !important;
                font-weight: 500 !important;
                transition: all 0.2s ease !important;
            }
            
            .stForm .stFormSubmitButton button:hover {
                background-color: #0e3ab3 !important;
                transform: translateY(-1px) !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            }
            
            /* Botão secundário (Limpar) */
            .stForm .stFormSubmitButton button[kind="secondaryFormSubmit"] {
                background-color: #f8f9fa !important;
                color: #6c757d !important;
                border: 1px solid #dee2e6 !important;
            }
            
            .stForm .stFormSubmitButton button[kind="secondaryFormSubmit"]:hover {
                background-color: #e9ecef !important;
                color: #495057 !important;
            }
                            
        </style>
    """, unsafe_allow_html=True)

    # ===== TAB 1: NOVO PROCESSO =====
    
    if 'multiselect_key_counter' not in st.session_state:
        st.session_state['multiselect_key_counter'] = 0     
    # Resetar estado para novo processo
    if 'novo_processo_existente_id' in st.session_state:
        st.session_state.pop('novo_processo_existente_id', None)
    if 'novo_executores_selecionados' in st.session_state:
        st.session_state.pop('novo_executores_selecionados', None)
    #if 'info_basicas_salvas' in st.session_state:
        #   st.session_state['info_basicas_salvas'] = False
    if 'riscos' not in st.session_state or len(st.session_state['riscos']) == 0:
        st.session_state['riscos'] = []

    # ===== LIMPEZA PÓS-SALVO (NOVO) =====
    if st.session_state.get('deve_limpar_diagnostico', False):
        campos_to_reset = ["input_processo", "input_objetivo", "input_descricao", 
                        "input_etapa_ini", "input_etapa_fim", "input_produto"]
        for campo in campos_to_reset:
            if campo in st.session_state:
                st.session_state[campo] = ""
        
        # Limpar executores
        st.session_state['novo_executores_selecionados'] = []  # <-- ADICIONAR
        
        # Limpar código do processo
        st.session_state['codigo_processo_display'] = ""  # <-- ADICIONAR
        
        # FORÇAR RECRIAÇÃO DO MULTISELECT
        st.session_state['multiselect_key_counter'] += 1  # <-- ADICIONAR

        st.session_state['riscos'] = []
        st.session_state['info_basicas_salvas'] = False
        st.session_state['deve_limpar_diagnostico'] = False
        st.rerun()
    
    st.title("🔍 Diagnóstico dos Processos")
    st.markdown("""
    <div style='font-family: helvetica==; color: #000000; font-size: 14px; line-height: 1.5;'>
        <p><strong>PASSO 1:</strong> PEDIR AO GESTOR PARA ESCREVER EM UM PAPEL O FLUXO DO PASSO A PASSO DO PROCESSO, INICIO AO FIM.</p>
        <p style='margin-top: 15px;'><strong>PASSO 2:</strong> ESCREVER ABAIXO OS PROCESSOS QUE FORAM SINALIZADOS NO FLUXO.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== SEÇÃO 0: VINCULAR À AUDITORIA =====
    st.subheader("1. Vincular à Auditoria")

    # Garantir que o selectbox tenha um valor padrão
    area_atual = st.session_state.get("area_selectbox", list(areas_dict.keys())[0])
    
    # SEGUNDO: Usar a função no selectbox
    st.selectbox(
        "Selecione a Área:", 
        list(areas_dict.keys()),
        index=list(areas_dict.keys()).index(area_atual) if area_atual in areas_dict else 0,
        key="area_selectbox", 
        on_change=atualizar_id_area
    )

    id_area_atual = st.session_state.get('id_area_selecionado')
    if id_area_atual:
        df_funcionarios = listar_funcionarios_area(id_area_atual)
        if not df_funcionarios.empty:
            with st.expander("👥 Funcionários da Área", expanded=False):
                for _, func in df_funcionarios.iterrows():
                    tempo_funcao = calcular_tempo(func.get('data_inicio_funcao'))
                    tempo_empresa = calcular_tempo(func.get('data_inicio_empresa'))
                    st.markdown(f"""
                    - **{func['nome_funcionario']}**  
                    *{func['cargo']}* | {tempo_funcao} na função, {tempo_empresa} na empresa
                    """)

    if 'id_area_selecionado' not in st.session_state:
        st.session_state['id_area_selecionado'] = list(areas_dict.values())[0]

    id_area_atual = st.session_state['id_area_selecionado']
    df_auditorias_area = listar_auditorias_para_area(id_area_atual)

    if not df_auditorias_area.empty:
        opcoes_auditoria = []
        for _, row in df_auditorias_area.iterrows():
            status_emoji = "🟡" if row['status'] == 'Planejamento' else "🟢"
            opcoes_auditoria.append({
                "id": row['id'],
                "display": f"{status_emoji} {row['codigo_auditoria']} - {row['titulo']} ({row['ano']} {row['trimestre']}º trim)"
            })
        
        display_list = [item["display"] for item in opcoes_auditoria]
        id_map = {item["display"]: item["id"] for item in opcoes_auditoria}
        
        auditoria_escolhida = st.selectbox(
            "Escolha a auditoria para vincular este processo:",
            options=display_list,
            help="Selecione a auditoria à qual este processo pertence."
        )
        
        st.session_state['auditoria_diagnostico'] = id_map[auditoria_escolhida]
        auditoria_selecionada = df_auditorias_area[df_auditorias_area['id'] == id_map[auditoria_escolhida]].iloc[0]
        st.success(f"✅ Processo será vinculado à auditoria: **{auditoria_selecionada['codigo_auditoria']}**")
        
    else:
        st.warning(f"⚠️ Nenhuma auditoria encontrada para esta área.")
        st.info("💡 Para diagnosticar processos, é necessário vincular a uma auditoria.")
        
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            if not st.session_state['mostrar_form_auditoria']:
                if st.button("➕ Criar Auditoria para esta Área", key="btn_criar_auditoria_diagnostico", use_container_width=True):
                    st.session_state['mostrar_form_auditoria'] = True
                    st.rerun()
        
        # ===== FORMULÁRIO INLINE PARA CRIAR AUDITORIA =====
        if st.session_state['mostrar_form_auditoria']:
            with st.container(border=True):
                st.markdown("#### 📝 Criar Nova Auditoria")
                st.caption(f"Área: **{st.session_state.get('area_selectbox', '')}**")
                
                # Campos de seleção
                col1, col2 = st.columns(2)
                with col1:
                    trimestre = st.selectbox("Trimestre:", [1, 2, 3, 4], key="trimestre_auditoria")
                with col2:
                    ano = st.number_input("Ano:", min_value=2024, max_value=2030, value=datetime.now().year, key="ano_auditoria")
                
                # Gerar código automaticamente
                area_nome = st.session_state.get('area_selectbox', '')
                codigo_gerado = gerar_codigo_auditoria(area_nome, ano, trimestre)
                
                # Mostrar o código que será gerado
                st.info(f"📌 **Código que será gerado:** `{codigo_gerado}`")
                
                col3, col4 = st.columns(2)
                with col3:
                    data_inicio = st.date_input("Data de início prevista", value=datetime.now().date())
                with col4:
                    data_fim = st.date_input("Data de término prevista", value=datetime.now().date() + timedelta(days=90))
                
                titulo = st.text_input(
                    "Título da auditoria", 
                    value=f"Auditoria {area_nome} - {ano} {trimestre}º Trimestre"
                )
                objetivo = st.text_area(
                    "Objetivo da auditoria", 
                    value="Avaliar a eficácia dos processos da área"
                )
                escopo = st.text_area(
                    "Escopo (o que será avaliado)", 
                    value="Processos críticos da área"
                )
                
                # Botões de ação
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                with col_btn1:
                    criar_click = st.button("✅ Criar Auditoria", type="primary", use_container_width=True)
                with col_btn2:
                    cancelar = st.button("❌ Cancelar", use_container_width=True)
                
                # ===== CONFIRMAÇÃO ANTES DE CRIAR =====
                if criar_click:
                    # Inicializar estado de confirmação
                    st.session_state['confirmar_criacao_auditoria'] = True
                
                if st.session_state.get('confirmar_criacao_auditoria', False):
                    st.markdown("---")
                    st.warning(f"⚠️ **Confirmação de criação**")
                    st.markdown(f"O código **`{codigo_gerado}`** será registrado no banco de dados.")
                    st.markdown("Deseja realmente criar esta auditoria?")
                    
                    col_conf1, col_conf2, col_conf3 = st.columns([1, 1, 2])
                    with col_conf1:
                        if st.button("✅ Sim, Criar", use_container_width=True):
                            dados = {
                                "id_area": id_area_atual,
                                "codigo_auditoria": codigo_gerado,
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
                                st.success(f"✅ Auditoria criada com sucesso! Código: {codigo}")
                                st.balloons()
                                st.session_state['auditoria_diagnostico'] = auditoria_id
                                st.session_state['mostrar_form_auditoria'] = False
                                st.session_state['confirmar_criacao_auditoria'] = False
                                time_module.sleep(1.5)
                                st.rerun()
                            else:
                                st.error("❌ Erro ao criar auditoria. Já existe uma auditoria para esta área no trimestre?")
                                st.session_state['confirmar_criacao_auditoria'] = False
                                st.rerun()
                    
                    with col_conf2:
                        if st.button("❌ Não, Cancelar", use_container_width=True):
                            st.toast("❌ Criação cancelada pelo usuário.", icon="❌")
                            st.session_state['confirmar_criacao_auditoria'] = False
                            st.rerun()
                
                if cancelar:
                    if st.session_state.get('confirmar_criacao_auditoria', False):
                        st.session_state['confirmar_criacao_auditoria'] = False
                    else:
                        st.session_state['mostrar_form_auditoria'] = False
                        st.rerun()
            
            # Botão alternativo para fechar
            if st.button("✖️ Fechar", use_container_width=True):
                st.session_state['mostrar_form_auditoria'] = False
                st.session_state['confirmar_criacao_auditoria'] = False
                st.rerun()

    st.divider()
    
    # ===== SEÇÃO 1: INFORMAÇÕES BÁSICAS (OBRIGATÓRIAS) =====
    st.markdown("""
        <div style='display: flex; align-items: center; gap: -2px; margin: 10px 0 5px 0;'>
            <h3 style='margin: 0; padding: 0;'>2. Informações Iniciais do Processo</h3>
            <span style='cursor: help; font-size: 1.2rem;' title='Associe o aos processos ou atividades, os funcionários que executam os mesmos. Em seguida, preencha os demais campos do diagnóstico conforme solicitado.'>ⓘ</span>
        </div>
    """, unsafe_allow_html=True)

    # Nome do Processo (obrigatório)
    nome_processo = st.text_input(
        "Nome do Processo:", 
        key="input_processo", 
        help="Digite o nome do processo.",
        placeholder="Ex: Processo de Fechamento Financeiro, Processo de Recrutamento e Seleção, etc."
    )

    # Atualiza o código automaticamente sempre que o nome do processo mudar
    # Usando sessions_state para detectar mudanças
    if 'ultimo_nome_processo' not in st.session_state:
        st.session_state['ultimo_nome_processo'] = ''
    if nome_processo != st.session_state['ultimo_nome_processo']:
        st.session_state['ultimo_nome_processo'] = nome_processo
        # Chama a função para gerar o código inteligente
        processar_codigo_inteligente()
    col_codigo = st.columns([1, 4])
    with col_codigo[0]:
        # Código do Processo (gerado automaticamente) - APENAS EXIBIÇÃO, SEM STATE
        codigo_atual = st.session_state.get('codigo_processo_display', '')
        st.text_input("Código do Processo:", value=codigo_atual, disabled=True, help="Código gerado automaticamente com base no nome do processo e na área selecionada. Não é editável.")

    with st.form(key="form_novo_processo"):
        # ===== EXECUTORES DO PROCESSO =====
        st.markdown("**Funcionário(s) que executam o processo:**")

        # Buscar funcionários da área selecionada
        id_area_atual = st.session_state.get('id_area_selecionado')
        funcionarios_lista = []

        if id_area_atual:
            funcionarios_lista = listar_funcionarios_por_area(id_area_atual)

        if not funcionarios_lista:
            st.warning("⚠️ Nenhum funcionário cadastrado para esta área. Cadastre funcionários em '🏢 Cadastro de Áreas e Funcionários'.")
            if 'novo_executores_selecionados' not in st.session_state:
                st.session_state['novo_executores_selecionados'] = []
        else:
            funcionarios_ids = [f[0] for f in funcionarios_lista]
            funcionarios_dict = {f[0]: f[1] for f in funcionarios_lista}
            
            defaults_validos = []
            if 'novo_executores_selecionados' in st.session_state:
                for exec_id in st.session_state['executores_selecionados']:
                    if exec_id in funcionarios_dict:
                        defaults_validos.append(exec_id)

            selecionados = st.multiselect(
                "",
                options=funcionarios_ids,
                format_func=lambda x: funcionarios_dict[x],
                default=defaults_validos,
                key=f"multiselect_executores_{st.session_state.get('multiselect_key_counter', 0)}",
                help="Você pode selecionar um ou mais funcionários",
                placeholder="Selecione os funcionários que executam este processo:"
            )
            
            st.session_state['novo_executores_selecionados'] = selecionados
            
            if selecionados:
                nomes_selecionados = [funcionarios_dict[id] for id in selecionados]
                st.caption(f"✅ Selecionados: {', '.join(nomes_selecionados)}")

        # Botões do formulário
        col_form1, col_form2 = st.columns([1, 3])
        with col_form1:
            submitted_salvar = st.form_submit_button("💾 Salvar Informações Básicas", type="primary", use_container_width=False)  # <-- MUDAR PARA FORM_SUBMIT_BUTTON
        with col_form2:
            submitted_limpar = st.form_submit_button("🧹 Limpar Informações do Funcionário", type="secondary", use_container_width=False, key='btn_limpar_form')  # <-- MUDAR PARA FORM_SUBMIT_BUTTON
            
        if submitted_salvar:
            processo_ja_existe = 'novo_processo_existente_id' in st.session_state
            if validar_basicos():
                with st.spinner("Salvando informações básicas..."):
                    resultado, novo_codigo = salvar_informacoes_basicas()  # Retorna também o código
                    if resultado:
                        if novo_codigo:
                            st.session_state['codigo_processo_display'] = novo_codigo
                        st.session_state['info_basicas_salvas'] = True
                        st.success("✅ Informações básicas salvas com sucesso!")
                        time_module.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar informações básicas. Tente novamente.")
            if submitted_limpar:
                st.session_state['deve_limpar_diagnostico'] = True
                st.session_state['info_basicas_salvas'] = False

                if 'novo_processo_existente_id' in st.session_state:
                    st.session_state.pop('novo_processo_existente_id')
                st.rerun()

    # ===== SEÇÃO 2: DETALHAMENTO DO PROCESSO (OPCIONAL) =====
    if st.session_state.get('info_basicas_salvas', False):
        st.divider()

        st.markdown("""
            <div style='display: flex; align-items: center; gap: -2px; margin: 10px 0 5px 0;'>
                <h3 style='margin: 0; padding: 0;'>2. Dados do Processo</h3>
                <span style='cursor: help; font-size: 1.2rem;' title='Campos opcionais para complementar o diagnóstico'>ⓘ</span>
            </div>
        """, unsafe_allow_html=True)

        st.info("ℹ️ Os campos abaixo são opcionais. Você pode preenchê-los agora ou editar depois.")

        # ==== CONTAINER ESTILIZADO PARA DETALHAMENTO ====
        # CSS para estilizar o container
        st.markdown("""
            <style>
                /* Estiliza o container de detalhamento */
                div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) {
                    background-color: #ffffff !important;
                    border-radius: 16px !important;
                    border: 1px solid #e0e0e0 !important;
                    padding: 20px !important;
                    margin-bottom: 20px !important;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
                }
                /* Pelo data-testid do elemento pai (mais estável) */
                div[data-testid="stTextArea"] textarea {
                    background-color: var(--input) !important;
                    border: 1px solid #ced4da !important;
                    border-radius: 8px !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # ==== CONTAINER ESTILIZADO ====
        with st.container():

            # Dados do Processo
            st.text_area("O que é o processo?:", key="input_descricao", help="Gestor diz com as suas palavras o que entende ser o processo.")
            st.text_area("Onde Começa o Processo?:", key="input_etapa_ini", 
                        help="Onde começa o processo? (Ex: Do envio do relatório x pela área y) - ETAPA INICIAL")
            st.text_area("Qual (is) o Produto (s) Final Desse Processo?:", key="input_produto", 
                        help="Qual(is) o(s) produto(s) final(is) desse processo? (Ex: Relatório, Planilha, Sistema, Word, etc)")
            st.text_area("Depois de Acabado, para onde envia?:", key="input_etapa_fim", 
                        help="Depois de acabado, para onde envia? (Ex: Área x, Arquivo físico localizado em y, Arquivo Digital localizado no z, etc.) - ETAPA FINAL")
            st.text_area("Qual o Objetivo do Processo? e Por que faz?:", key="input_objetivo",
                         placeholder="Garantir o que exatamente?")

            st.write("")

        
        # ===== SEÇÃO 3: RISCOS ASSOCIADOS =====
        st.markdown("""
        <div style='font-family: helvetica; color: #ff0000; font-size: 20px; line-height: 1;'>
            <p><strong>AVALIAÇÃO DA MAGNITUDE DO RISCO</strong></p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        
        st.subheader("3. Riscos Associados")

        # CSS para estilizar os campos de risco
        st.markdown("""
            <style>
                    /* Container dos riscos */
                    .riscos-container {{
                        background-color: #ffffff !important;
                        border-radius: 16px !important;
                        border: 1px solid #e0e0e0 !important;
                        padding: 20px !important;
                        margin-bottom: 20px !important;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
                    }}

                    /* Estiliza todos os textareas dentro dos riscos */
                    .riscos-container textarea,
                    div[data-testid="st.TextArea"] textarea {{
                        background-color: var(--card-bg) !important;
                        border: 1px solid #ced4da !important;
                        border-radius: 8px !important;
                        padding: 10px !important;
                    }}

                    /* Estiliza todos os inputs dentro dos riscos */
                    .riscos-container input,
                    div[data-testid="stTextInput"] input {
                        background-color: var(--input) !important;
                        border: 1px solid #ced4da !important;
                        border-radius: 8px !important;
                        padding: 8px 12px !important;
                    }
                    
                    /* Estiliza os selectboxes dentro dos riscos */
                    .riscos-container select,
                    div[data-testid="stSelectbox"] select {
                        background-color: var(--card-bg) !important;
                        border: 1px solid #ced4da !important;
                        border-radius: 8px !important;
                        padding: 8px 12px !important;
                    }
                    
                    /* Estiliza os multiselect dentro dos riscos */
                    .riscos-container .stMultiSelect {
                        background-color: #ffffff !important;
                        border-radius: 8px !important;
                    }
                    
                    /* Efeito ao focar nos campos */
                    .riscos-container textarea:focus,
                    .riscos-container input:focus,
                    .riscos-container select:focus {
                        border-color: #1848d8 !important;
                        outline: none !important;
                        box-shadow: 0 0 0 3px rgba(24, 72, 216, 0.1) !important;
                    }
                    
                    /* Labels dentro dos riscos */
                    .riscos-container label {
                        color: #48606c !important;
                        font-weight: 500 !important;
                    }

                    /* Estiliza o expander de critérios de risco */
                    div[data-testid="stExpander"] details {
                        background-color: #ffffff !important;
                        border-radius: 8px !important;
                        border: 1px solid #e0e0e0 !important;
                    }

                    /* Estiliza o cabeçalho do expander */
                    div[data-testid="stExpander"] summary {
                        background-color: #ffffff !important;
                        border-radius: 8px !important;
                        padding: 8px 12px !important;
                    }

                    /* Estiliza o conteúdo interno do expander */
                    div[data-testid="stExpander"] .st-emotion-cache-1v0mbdj {
                        background-color: #ffffff !important;
                        padding: 15px !important;
                    }
            </style>
        """, unsafe_allow_html=True)

        # Lista para armazenar índices a remover - NÃO REMOVA ESTA LINHA!
        indices_para_remover = []

        # Mostrar cada risco em um expander
        for i, _ in enumerate(st.session_state['riscos']):
            # Título do expander
            titulo_risco = st.session_state.get(f'nome_{i}', f'Risco {i+1}')
            if titulo_risco and titulo_risco != f'Risco {i+1}':
                titulo_expander = f"⚠️ {titulo_risco[:50]}"
            else:
                titulo_expander = f"⚠️ Risco {i+1} (não nomeado)"
            # ==== CONTROLE DE ESTADO DO EXPANDER ====
            # Verficar se este expander deve estar aberto
            expanded_default = st.session_state['expanders_abertos'].get(i, False)

            # Criar o expander com controle de estado            
            with st.expander(titulo_expander, expanded=expanded_default):
                # Atualizar estado para aberto quando o usuário interagir
                # Isso é feito através de um callback que será executado no p´roximo rerun
                if not expanded_default:
                    # se estava fechado e agora está aberto, marcar como aberto.
                    st.session_state['expanders_abertos'][i] = True

                # Cabeçalho com botão de remover
                col_titulo, col_remove = st.columns([5, 1])
                with col_titulo:
                    st.markdown(f"**Detalhes do Risco {i+1}**")
                with col_remove:
                    if len(st.session_state['riscos']) != 0:
                        if st.button("🗑️ Remover Risco", key=f"remove_risco_{i}", use_container_width=True):
                            indices_para_remover.append(i)
                            st.toast(f"✅ Risco {i+1} removido!")
                            # Limpar estado do expander ao remover
                            if i in st.session_state['expanders_abertos']:
                                del st.session_state['expanders_abertos'][i]
                            st.toast(f"✅ Risco {i+1} removido!")
                            time_module.sleep(0.5)
                            st.rerun()
                st.divider()

                # Campos do risco
                st.text_input(
                    f"Nome do Risco:",
                    key=f"nome_{i}",
                    placeholder="Risco pela possibilidade de acontecer o que?",
                    help="Descreva o risco de forma clara e objetiva",
                    on_change=lambda idx=1: manter_expander_aberto(idx)
                )

                # Categorias
                categorias_dict = listar_categorias()   
                ids_categorias = list(categorias_dict.keys())

                # Chama a função que exibe o expander com descrição das categorias
                exibir_descricao_categorias()

                st.multiselect(
                    f"Categorias do Risco:",
                    options=ids_categorias,
                    format_func=lambda x: categorias_dict[x],
                    default=st.session_state.get(f"categorias_{i}", []),
                    key=f"categorias_{i}",
                    help="Selecione uma ou mais categorias para este risco",
                    on_change=lambda idx=i: manter_expander_aberto(idx)
                )

                # Fator de Risco
                st.text_area(
                    f"Fator de Risco",
                    key=f"fator_{i}",
                    placeholder="Pelo motivo de?",
                    help="Fator de risco, causa ou motivo desse risco acontecer.",
                    on_change=lambda idx=i: manter_expander_aberto(idx)
                )

                    # Ponto de Melhoria
                st.text_area(
                    f"Ponto de Melhoria:", 
                    key=f"melhoria_{i}", 
                    placeholder="O que poderia ser melhorado para reduzir ou eliminar este risco?",
                    help="O que mais te incomoda nesse processo e pensa que deveria ser melhor?",
                    on_change=lambda idx=i: manter_expander_aberto(idx)
                )
                
                # Apetite ao Risco
                st.text_area(
                    f"Apetite ao risco:", 
                    key=f"apetite_{i}", 
                    placeholder="Qual o nível de risco que a organização está disposta a aceitar?",
                    help="Dentro do critério e classificação do risco, quanto o Gestor entende ser o mínimo aceitável de ocorrência de risco.",
                    on_change=lambda idx=i: manter_expander_aberto(idx)
                )   

                # Critérios
                exibir_criterios_risco()

                # Impacto e Probabilidade
                col_i, col_p = st.columns(2)
                with col_i:
                    st.selectbox(
                        f"Impacto:", 
                        ["Muito Alto", "Alto", "Médio", "Baixo"], 
                        key=f"imp_{i}", 
                        help="Impacto do risco materializado",
                        on_change=lambda idx=i: manter_expander_aberto(idx)
                    )
                with col_p:
                    st.selectbox(
                        f"Probabilidade:", 
                        ["Muito Alto", "Alto", "Médio", "Baixo"], 
                        key=f"prob_{i}", 
                        help="Probabilidade do risco acontecer?",
                        on_change=lambda idx=i: manter_expander_aberto(idx)
                    )
                
                # Cálculo do Risco Bruto
                score_v = MAPA_RISCO.get((st.session_state.get(f"imp_{i}"), st.session_state.get(f"prob_{i}")), 0)
                cor, emoji = get_estilo_risco(score_v)
                st.markdown(f"""
                <div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white; margin: 10px 0;">
                    {emoji} <strong>Risco Bruto (Impacto + Probabilidade): {score_v}</strong>
                </div>
                """, unsafe_allow_html=True)

                # Motivo da classificação
                st.text_area(
                    f"Motivo:",
                    key=f"motivo_{i}",
                    placeholder="Justifique a escolha do impacto e probabilidade acima.",
                    help="Qual o motivo da classificação do nível da probabilidade? - ANÁLISE",
                    on_change=lambda idx=i: manter_expander_aberto(idx)
                )

                st.markdown("---")
        # Remover os riscos marcados
        for idx in reversed(indices_para_remover):
            st.session_state['riscos'].pop(idx)
            keys_to_remove = [f'nome_{idx}', f'categorias_{idx}', f'fator_{idx}', f'melhoria_{idx}',
                                f'apetite_{idx}', f'imp_{idx}', f'prob_{idx}', f'motivo_{idx}']
            for key in keys_to_remove:
                if key in st.session_state:
                    st.session_state.pop(key)
        if indices_para_remover:
            st.rerun()

        # Adicionar Risco/Salvar
        col_add, col_save = st.columns(2)
        with col_add:
            if st.button("➕ Adicionar Risco", key="add_risco_bottom", use_container_width=True):
                st.session_state['riscos'].append({})
                st.rerun()
        with col_save:
            if st.button("💾 Salvar Todos os Dados", type="primary", use_container_width=True, key='btn_salvar_todos_os_dados'):
                if validar_formulario() and salvar_no_banco():
                    # Vincular à auditoria após salvar
                    if 'auditoria_diagnostico' in st.session_state and 'ultimo_processo_id' in st.session_state:
                        auditoria_id = st.session_state['auditoria_diagnostico']
                        processo_id = st.session_state.get('ultimo_processo_id')
                        if processo_id:
                            vincular_processo_a_auditoria(
                                auditoria_id=auditoria_id,
                                processo_id=processo_id,
                                motivo="Processo identificado durante diagnóstico da área"
                            )
                            st.success("Processo vinculado à auditoria com sucesso!")
                            time_module.sleep(1)
                    st.toast("Dados salvos!", icon='✅')
                    time_module.sleep(1.5)
                    st.session_state['deve_limpar_diagnostico'] = True
                    st.rerun()
        
    else:
        st.info("👆 **Primeiro, preencha e salve as Informações Básicas do Processo.**")
        st.info("Após salvar, você poderá adicionar o detalhamento e os riscos.")


def _tela_editar_processo():
    """Sub-tela de edição de processo existente"""
    from logic import calcular_tempo

    # Atualizar ID da área quando mudar
    def atualizar_id_area_edit():
        nome_selecionado = st.session_state['area_selectbox_edit']
        st.session_state['id_area_selecionado_edit'] = areas_dict[nome_selecionado]
        
    # ===== TAB 2: EDITAR PROCESSO EXISTENTE =====
    
    # Criar um placeholder para o formulário de edição
    if 'edit_form_placeholder' not in st.session_state:
        st.session_state['edit_form_placeholder'] = st.empty()

    if 'processo_selecionado_para_editar' not in st.session_state:
        st.session_state['processo_selecionado_para_editar'] = None

    # ==== INICIALIZAR UM DICIONÁRIO PARA CONTROLAR EXPANDERS ABERTOS NA EDIÇÃO ====
    if 'edit_expanders_abertos' not in st.session_state:
        st.session_state['edit_expanders_abertos'] = {}

    st.divider()
    st.title("Edição de processo existente")
    st.markdown("Selecione um processo abaixo para editar suas informações.")
    
    # ===== VINCULAR À AUDITORIA (MESMO DA TAB 1) =====
    st.subheader("1. Vincular à Auditoria")
    
    def listar_auditorias_para_area(id_area):
        query = text("""
            SELECT id, codigo_auditoria, titulo, trimestre, ano, status
            FROM auditorias
            WHERE id_area = :id_area
            AND status IN ('Planejamento', 'Em Execução')
            ORDER BY ano DESC, trimestre DESC
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"id_area": id_area})
    
    # Usar a função no selectbox
    st.selectbox(
        "Selecione a Área:", 
        list(areas_dict.keys()), 
        key="area_selectbox_edit",
        on_change=atualizar_id_area_edit
    )
    
    # Garantir que o ID da área esteja inicializado
    if 'id_area_selecionado_edit' not in st.session_state:
        st.session_state['id_area_selecionado_edit'] = list(areas_dict.values())[0]
    
    # ==== DEFINIR VARIÁVEIS ====
    id_area_atual_edit = st.session_state.get('id_area_selecionado_edit')

    # Mostrar funcionários da área (opcional)
    if id_area_atual_edit:
        df_funcionarios = listar_funcionarios_area(id_area_atual_edit)
        if not df_funcionarios.empty:
            with st.expander("👥 Funcionários da Área", expanded=False):
                for _, func in df_funcionarios.iterrows():
                    tempo_funcao = calcular_tempo(func.get('data_inicio_funcao'))
                    tempo_empresa = calcular_tempo(func.get('data_inicio_empresa'))
                    st.markdown(f"""
                    - **{func['nome_funcionario']}**  
                    *{func['cargo']}* | {tempo_funcao} na função, {tempo_empresa} na empresa
                    """)
    
    # Buscar auditorias da área selecionada
    df_auditorias_area = listar_auditorias_para_area(id_area_atual_edit)
    
    if not df_auditorias_area.empty:
        opcoes_auditoria = []
        for _, row in df_auditorias_area.iterrows():
            status_emoji = "🟡" if row['status'] == 'Planejamento' else "🟢"
            opcoes_auditoria.append({
                "id": row['id'],
                "display": f"{status_emoji} {row['codigo_auditoria']} - {row['titulo']} ({row['ano']} {row['trimestre']}º trim)"
            })
        
        display_list = [item["display"] for item in opcoes_auditoria]
        id_map_auditoria = {item["display"]: item["id"] for item in opcoes_auditoria}
                        
        auditoria_escolhida = st.selectbox(
            "Escolha a auditoria para filtrar os processos:",
            options=display_list,
            key="auditoria_select_edit",
            help="Selecione a auditoria à qual o processo pertence."
        )
        
        st.session_state['auditoria_edit'] = id_map_auditoria[auditoria_escolhida]
        st.success(f"Filtrando processos da auditoria: **{auditoria_escolhida.split(' - ')[0]}**")
    else:
        st.warning(f"⚠️ Nenhuma auditoria encontrada para esta área. Crie uma em '📋 Detalhamento dos Processos' primeiro.")
        st.session_state['auditoria_edit'] = None
    
    st.divider()

    # ==== CARREGAMENTO AUTOMÁTICO (QUANDO VINDO DA AUDITORIA) ====
    # Verificar se veio da auditoria para editar um processo
    if st.session_state.get('processo_para_editar') and st.session_state.get('aba_editar_ativa'):
        processo_id_automatico = st.session_state['processo_para_editar']

        # Buscar dados do processo
        query_codigo = text("SELECT codigo_processo, id_area FROM processos WHERE id = :id")
        with engine.connect() as conn:
            resultado = conn.execute(query_codigo, {'id': processo_id_automatico}).fetchone()

        if resultado:
            codigo = resultado[0]
            id_area_processo = resultado[1]

            # Ajustar a área selecionada para a área do processo
            areas_dict_inv = {v: k for k, v in areas_dict.items()}
            if id_area_processo in areas_dict_inv:
                st.session_state['area_selectbox_edit'] = areas_dict_inv[id_area_processo]
                st.session_state['id_area_selecionado_edit'] = id_area_processo
                id_area_atual_edit = id_area_processo

            processo = buscar_processo_por_codigo(codigo)

            if processo:
                # Salvar todos os dados em session_state
                st.session_state['edit_processo_data'] = {
                    'codigo': codigo,
                    'id': processo['id'],
                    'nome_processo': processo.get('nome_processo', ''),
                    'codigo_processo': processo.get('codigo_processo', ''),
                    'objetivo': processo.get('objetivo', ''),
                    'descricao': processo.get('descricao', ''),
                    'etapa_ini': processo.get('etapa_ini', ''),
                    'etapa_fim': processo.get('etapa_fim', ''),
                    'produto': processo.get('produto', ''),
                    'executores': listar_executores_processo(processo['id']),
                    'riscos': []
                }

                # carregar riscos

                # No carregamento automático (quando vem da auditoria):
                df_riscos = listar_riscos_do_processo(processo['id'])
                if not df_riscos.empty:
                    for idx, row in df_riscos.iterrows():
                        st.session_state['edit_processo_data']['riscos'].append({
                            'nome': row['nome_risco'] or '',
                            'fator': row['fator_risco'] or '',
                            'melhoria': row['melhoria'] or '',
                            'apetite': row['apetite_risco'] or '',
                            'motivo': row['motivo_risco'] or '',
                            'categorias_ids': row['categorias_ids'] if 'categorias_ids' in row else [],  # Agora vem como lista de IDs
                            'categorias_string': row['categoria'] if 'categoria' in row else '',  # Guardar a string original
                            'impacto': normalizar_valor_risco(row['impacto']),
                            'probabilidade': normalizar_valor_risco(row['probabilidade'])
                        })
                        # Inicialiar expander abertos para todos os riscos carregados
                        st.session_state['edit_expanders_abertos'][idx] = True

                st.session_state['modo_edicao'] = True
                st.session_state['edit_form_version'] = st.session_state.get('edit_form_version', 0) + 1

                # Limpar a flag para não recarregar novamente
                st.session_state.pop('processo_para_editar', None)
                st.session_state.pop('aba_editar_ativa', None)
                st.rerun()

    st.subheader("2. Seleção do Processo para Edição")
    
    # ===== BUSCAR PROCESSOS DA ÁREA E AUDITORIA SELECIONADAS =====
    if id_area_atual_edit and st.session_state.get('auditoria_edit'):
        
        query = text("""
            SELECT p.id, p.codigo_processo, p.nome_processo
            FROM processos p
            JOIN auditoria_processos ap ON p.id = ap.processo_id
            WHERE p.id_area = :id_area
            AND ap.auditoria_id = :auditoria_id
            ORDER BY 
                (string_to_array(p.codigo_processo, '.'))[1]::int,
                (string_to_array(p.codigo_processo, '.'))[2]::int,
                (string_to_array(p.codigo_processo, '.'))[3]::int
        """)
        
        with engine.connect() as conn:
            df_processos = pd.read_sql(query, conn, params={
                "id_area": id_area_atual_edit,
                "auditoria_id": st.session_state['auditoria_edit']
            })
        
        if not df_processos.empty:
            opcoes = []
            for _, row in df_processos.iterrows():
                opcoes.append({
                    "display": f"{row['codigo_processo']} - {row['nome_processo']}",
                    "id": row['id']
                })
            
            display_list = [item["display"] for item in opcoes]
            id_map = {item["display"]: item["id"] for item in opcoes}
            
            processo_escolhido = st.selectbox(
                "Selecione o processo para editar:",
                options=[""] + display_list,
                key="select_processo_editar_tab"
            )
            
            if processo_escolhido:
                st.session_state['processo_selecionado_para_editar'] = processo_escolhido
                if st.button("📂 Carregar Processo", type="primary", use_container_width=False, key='btn_carregar_processo'):
                    if st.session_state.get('processo_selecionado_para_editar'):
                        processo_escolhido = st.session_state['processo_selecionado_para_editar']
                    
                    # ===== CARREGAR DADOS DO PROCESSO =====
                    processo_id = id_map[processo_escolhido]
                    
                    query_codigo = text("SELECT codigo_processo FROM processos WHERE id = :id")
                    with engine.connect() as conn:
                        resultado = conn.execute(query_codigo, {"id": processo_id}).fetchone()
                    
                    if resultado:
                        codigo = resultado[0]
                        processo = buscar_processo_por_codigo(codigo)
                        
                        if processo:
                            # Salvar todos os dados em session_state
                            st.session_state['edit_processo_data'] = {
                                'codigo': codigo,
                                'id': processo['id'],
                                'nome_processo': processo.get('nome_processo', ''),
                                'codigo_processo': processo.get('codigo_processo', ''),
                                'objetivo': processo.get('objetivo', ''),
                                'descricao': processo.get('descricao', ''),
                                'etapa_ini': processo.get('etapa_ini', ''),
                                'etapa_fim': processo.get('etapa_fim', ''),
                                'produto': processo.get('produto', ''),
                                'executores': listar_executores_processo(processo['id']),
                                'riscos': []
                            }
                            
                            # ===== CARREGAR RISCOS =====
                            df_riscos = listar_riscos_do_processo(processo['id'])
                            
                            if not df_riscos.empty:
                                for idx, row in df_riscos.iterrows():
                                    st.session_state['edit_processo_data']['riscos'].append({
                                        'nome': row['nome_risco'] or "",
                                        'fator': row['fator_risco'] or "",
                                        'melhoria': row['melhoria'] or "",
                                        'apetite': row['apetite_risco'] or "",
                                        'motivo': row['motivo_risco'] or "",
                                        'categorias_ids': row['categorias_ids'] if 'categorias_ids' in row else [],
                                        'categorias_string': row['categoria'] if 'categoria' in row else '',
                                        'impacto': normalizar_valor_risco(row['impacto']),
                                        'probabilidade': normalizar_valor_risco(row['probabilidade'])
                                    })
                                    # Inicializar expander abertos apra todos os riscos
                                    st.session_state['edit_expanders_abertos'][idx] = True

                            st.session_state['modo_edicao'] = True
                            st.session_state['edit_form_version'] = st.session_state.get('edit_form_version', 0) + 1
                            st.rerun()
                            

        else:
            st.info("Nenhum processo cadastrado para esta área e auditoria.")
    else:
        if not id_area_atual_edit:
            st.info("Selecione uma área no menu superior para ver os processos disponíveis.")
        elif not st.session_state.get('auditoria_edit'):
            st.info("Selecione uma auditoria para filtrar os processos.")
    
    # ===== FORMULÁRIO DE EDIÇÃO (✏️ EDITAR PROCESSO EXISTENTE) =====
    if st.session_state.get('modo_edicao', False):
        # Usar o placeholder para recriar o formulário
        with st.session_state['edit_form_placeholder'].container():
            # Incrementar versão apra garantir recriação
            form_version = st.session_state.get('edit_form_version', 0)

            st.divider()
            st.subheader("✏️ Editando Processo")

            # Obter dados do processo
            processo_data = st.session_state.get('edit_processo_data', {})

        
            # ===== DADOS BÁSICOS =====
            st.text_input(
                "Nome do Processo:",
                value=processo_data.get('nome_processo', ''), 
                key=f"edit_input_processo_{form_version}",
                help="Digite o nome do processo."
            )
            
            st.text_input(
                "Código do Processo:",
                value=processo_data.get('codigo_processo', ''),
                key=f"edit_codigo_processo_{form_version}",
                disabled=True
            )
        
        # ===== EXECUTORES =====
        st.markdown("**Funcionário(s) que executam o processo:**")
        
        id_area_atual = st.session_state.get('id_area_selecionado_edit')
        funcionarios_lista = []
        
        if id_area_atual_edit:
            funcionarios_lista = listar_funcionarios_por_area(id_area_atual_edit)
        
        if not funcionarios_lista:
            st.warning("⚠️ Nenhum funcionário cadastrado para esta área.")
        else:
            funcionarios_ids = [f[0] for f in funcionarios_lista]
            funcionarios_dict = {f[0]: f[1] for f in funcionarios_lista}
            
            # Obter os IDs dos executores já salvos no processo (carregados anteriormente)
            executores_ids = processo_data.get('executores', [])
            # Filtrar apenas os que ainda existem na área (caso algum funcionário tenha sido removido)
            defaults_validos = [exec_id for exec_id in executores_ids if exec_id in funcionarios_dict]
            
            selecionados = st.multiselect(
                "",
                options=funcionarios_ids,
                format_func=lambda x: funcionarios_dict[x],
                default=defaults_validos,
                key=f'edit_multiselect_executores_{form_version}',
                help="Você pode selecionar um ou mais funcionários",
                placeholder= 'Selecione os funcionários que executam este processo: '
            )
            
            # Salvar no session_state para uso nno salvamento
            st.session_state['edit_executores_selecionados'] = selecionados
            
            if selecionados:
                nomes_selecionados = [funcionarios_dict[id] for id in selecionados]
                st.caption(f"✅ Selecionados: {', '.join(nomes_selecionados)}")
        
        st.divider()
        
        # ===== DETALHAMENTO DO PROCESSO FORMULÁRIO DE EDIÇÃO =====
        st.markdown("### Detalhamento do Processo")
        st.info("ℹ️ Os campos abaixo são opcionais.")
        
        st.text_area(
            "O que é o processo?:", 
            value=processo_data.get('descricao', ''),
            key=f"edit_input_descricao_{form_version}",
            help="Gestor diz com as suas palavras o que entende ser o processo."
        )
        st.text_area(
            "Onde Começa o Processo?:", 
            value=processo_data.get('etapa_ini', ''),
            key=f"edit_input_etapa_ini_{form_version}",
            help="Onde começa o processo? - ETAPA INICIAL"
        )
        st.text_area(
            "Qual (is) o Produto (s) Final Desse Processo?:", 
            value=processo_data.get('produto', ''),
            key=f"edit_input_produto_{form_version}",
            help="Qual(is) o(s) produto(s) final(is) desse processo?"
        )
        st.text_area(
            "Depois de Acabado, para onde envia?:", 
            value=processo_data.get('etapa_fim', ''),
            key=f"edit_input_etapa_fim_{form_version}",
            help="Depois de acabado, para onde envia? - ETAPA FINAL"
        )
        st.text_area(
            "Qual o Objetivo do Processo? e Por que faz?:", 
            value=processo_data.get('objetivo', ''),
            key=f"edit_input_objetivo_{form_version}"
        )
        
        st.write("")
        
        # ===== RISCOS ASSOCIADOS =====
        st.markdown("### Riscos Associados")
        
        # Botão para adicionar risco
        col_add_risco, col_spacer = st.columns([1, 4])
        with col_add_risco:
            if st.button("➕ Adicionar Risco", key=f"edit_add_risco_{form_version}", use_container_width=True):
                if 'edit_riscos_temp' not in st.session_state:
                    st.session_state['edit_riscos_temp'] = processo_data.get('riscos', []).copy()
                novo_idx = len(st.session_state['edit_riscos_temp'])
                st.session_state['edit_riscos_temp'].append({})
                # Marcar o novo expander como aberto automaticamente
                st.session_state['edit_expanders_abertos'][novo_idx] = True
                st.rerun()
        
        st.divider()
        
        # ===== EXIBIÇÃO DOS RISCOS =====
        riscos_lista = st.session_state.get('edit_riscos_temp', processo_data.get('riscos', []))
        
        if riscos_lista:
            indices_para_remover = []
            
            
            for i, risco in enumerate(riscos_lista):
                # Título do expander
                titulo_risco = risco.get('nome', f'Risco {i+1}')
                if titulo_risco and titulo_risco != f'Risco {i+1}':
                    titulo_expander = f"⚠️ {titulo_risco[:60]}..."
                else:
                    titulo_expander = f"⚠️ Risco {i+1} (não nomeado)"


                
                # ===== CONTROLE DE ESTADO DO EXPANDER NA EDIÇÃO =====
                expanded_default = st.session_state['edit_expanders_abertos'].get(i, True)  # Padrão True para mostrar
                
                with st.expander(titulo_expander, expanded=expanded_default):
                    # Atualizar estado para aberto quando o usuário interagir
                    if not expanded_default:
                        st.session_state['edit_expanders_abertos'][i] = True
                    
                    # Cabeçalho com botão de remover
                    col_titulo, col_remove = st.columns([5, 1])
                    with col_titulo:
                        st.markdown(f"**Detalhes do Risco {i+1}**")
                    with col_remove:
                        if len(riscos_lista) > 1:
                            if st.button("🗑️ Remover", key=f"edit_remove_risco_{form_version}_{i}", use_container_width=True):
                                indices_para_remover.append(i)
                                # Limpar estado do expander ao remover
                                if i in st.session_state['edit_expanders_abertos']:
                                    del st.session_state['edit_expanders_abertos'][i]
                                st.rerun()
                    
                    st.divider()
                    
                    # Campos do risco com callbacks para manter expander aberto
                    novo_nome = st.text_input(
                        "Nome do Risco:",
                        value=risco.get('nome', ''), 
                        key=f"edit_nome_{form_version}_{i}", 
                        placeholder="Ex: Risco de erro no cadastro...",
                        help="Descreva o risco de forma clara e objetiva",
                        on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                    )
                    risco['nome'] = novo_nome
                    
                    # Categorias
                    categorias_dict = listar_categorias()
                    ids_categorias = list(categorias_dict.keys())

                    # Chamar a função que exibe o expander com descrição das categorias
                    exibir_descricao_categorias()
                    
                    # Garantir que default seja uma lista válida
                    categorias_default = risco.get('categorias_ids', [])  # Agora vem como lista de IDs

                    categorias_selecionadas_ids = st.multiselect(
                        "Categorias do Risco:", 
                        options=list(categorias_dict.keys()),  # IDs [1,2,3,4,5,6,7]
                        format_func=lambda x: categorias_dict[x],  # Mostra o nome
                        default=categorias_default,  # IDs pré-selecionados
                        key=f"edit_categorias_{form_version}_{i}",
                        help="Selecione uma ou mais categorias para este risco",
                        on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                    )

                    # Salvar os IDs para uso futuro
                    risco['categorias_ids'] = categorias_selecionadas_ids

                    novo_fator = st.text_area(
                        "Fator de Risco:",
                        value=risco.get('fator', ''),
                        key=f"edit_fator_{form_version}_{i}", 
                        placeholder="O que causa ou contribui para que este risco aconteça?",
                        help="Fator de risco, causa ou motivo desse risco acontecer.",
                        on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                    )
                    risco['fator'] = novo_fator
                    
                    nova_melhoria = st.text_area(
                        "Ponto de Melhoria:",
                        value=risco.get('melhoria', ''),
                        key=f"edit_melhoria_{form_version}_{i}", 
                        placeholder="O que poderia ser melhorado para reduzir ou eliminar este risco?",
                        help="O que mais te incomoda nesse processo e pensa que deveria ser melhor?",
                        on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                    )
                    risco['melhoria'] = nova_melhoria
                    
                    novo_apetite = st.text_area(
                        "Apetite ao risco:",
                        value=risco.get('apetite', ''),
                        key=f"edit_apetite_{form_version}_{i}", 
                        placeholder="Qual o nível de risco que a organização está disposta a aceitar?",
                        help="Dentro do critério e classificação do risco, quanto o Gestor entende ser o mínimo aceitável.",
                        on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                    )
                    risco['apetite'] = novo_apetite
                    
                    exibir_criterios_risco()
                    
                    col_i, col_p = st.columns(2)
                    with col_i:
                        novo_impacto = st.selectbox(
                            "Impacto:", 
                            ["Muito Alto", "Alto", "Médio", "Baixo"], 
                            index=["Muito Alto", "Alto", "Médio", "Baixo"].index(risco.get('impacto', 'Médio')),
                            key=f"edit_imp_{form_version}_{i}", 
                            help="Impacto do risco materializado",
                            on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                        )
                        risco['impacto'] = novo_impacto
                    with col_p:
                        nova_probabilidade = st.selectbox(
                            "Probabilidade:", 
                            ["Muito Alto", "Alto", "Médio", "Baixo"],
                            index=["Muito Alto", "Alto", "Médio", "Baixo"].index(risco.get('probabilidade', 'Médio')),
                            key=f"edit_prob_{form_version}_{i}", 
                            help="Probabilidade do risco acontecer?",
                            on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                        )
                        risco['probabilidade'] = nova_probabilidade
                    
                    score_v = MAPA_RISCO.get((risco.get('impacto', 'Médio'), risco.get('probabilidade', 'Médio')), 0)
                    cor, emoji = get_estilo_risco(score_v)
                    st.markdown(f"""
                    <div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center; color: white; margin: 10px 0;">
                        {emoji} <strong>Risco Bruto (Impacto + Probabilidade): {score_v}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    novo_motivo = st.text_area(
                        "Motivo:",
                        value=risco.get('motivo', ''), 
                        key=f"edit_motivo_{form_version}_{i}", 
                        placeholder="Justifique a escolha do impacto e probabilidade acima.",
                        help="Qual o motivo da classificação do nível da probabilidade?",
                        on_change=lambda idx=i: manter_expander_aberto_edit(idx)
                    )
                    risco['motivo'] = novo_motivo
                    
                    st.markdown("---")
            
            # Remover riscos marcados
            for idx in reversed(indices_para_remover):
                riscos_lista.pop(idx)
                # Reorganizar os índices dos expanders abertos
                new_expanders = {}
                for old_idx, new_idx in enumerate(range(len(riscos_lista))):
                    if old_idx in st.session_state['edit_expanders_abertos']:
                        new_expanders[new_idx] = st.session_state['edit_expanders_abertos'][old_idx]
                st.session_state['edit_expanders_abertos'] = new_expanders
            
            if indices_para_remover:
                st.session_state['edit_riscos_temp'] = riscos_lista
                st.rerun()
        
        else:
            st.info("📌 Nenhum risco cadastrado para este processo. Clique em 'Adicionar Risco' para começar.")
        
        # ===== BOTÕES DE AÇÃO =====
        col_save, col_cancel = st.columns(2)
        
        with col_save:
            if st.button("💾 Atualizar Alterações", type="primary", key=f"edit_save_{form_version}", use_container_width=True):
                # Preparar dados para salvar
                edit_data = {
                    'processo_id': processo_data.get('id'),
                    'nome_processo': st.session_state.get(f"edit_input_processo_{form_version}", ''),
                    'objetivo': st.session_state.get(f"edit_input_objetivo_{form_version}", ''),
                    'descricao': st.session_state.get(f"edit_input_descricao_{form_version}", ''),
                    'etapa_ini': st.session_state.get(f"edit_input_etapa_ini_{form_version}", ''),
                    'etapa_fim': st.session_state.get(f"edit_input_etapa_fim_{form_version}", ''),
                    'produto': st.session_state.get(f"edit_input_produto_{form_version}", ''),
                    'executores': st.session_state.get('edit_executores_selecionados', []),
                    'riscos': riscos_lista
                }
                
                if salvar_edicao_processo_completa(edit_data):
                    st.toast("Alterações salvas com sucesso!", icon="✅")
                    time_module.sleep(1.5)
                    # Limpar estados de edição
                    st.session_state.pop('modo_edicao', None)
                    st.session_state.pop('edit_processo_data', None)
                    st.session_state.pop('edit_riscos_temp', None)
                    st.session_state.pop('edit_expanders_abertos', None)
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar alterações.")
        
        with col_cancel:
            if st.button("❌ Cancelar Edição", key=f"edit_cancel_{form_version}", use_container_width=True):
                st.session_state.pop('modo_edicao', None)
                st.session_state.pop('edit_processo_data', None)
                st.session_state.pop('edit_riscos_temp', None)
                st.session_state.pop('edit_expanders_abertos', None)
                
                # Se veio da auditoria, voltar pra ela
                if st.session_state.get('auditoria_origem'):
                    st.session_state['auditoria_selecionada'] = st.session_state['auditoria_origem']
                    st.session_state.pop('auditoria_origem', None)
                    st.session_state['tela_atual'] = 'detalhe_auditoria'

                st.rerun()

def tela_diagnostico_processos():
    """Tela principal de diagnóstico de processos (novo e editar)"""
    
    # NOVA ESTRUTURA COM DUAS ABAS
    # # Estilo CSS para fazer o radio parecer tabs
    # st.markdown("""
    # <style>
    #     /* Container do radio */
    #     div[data-testid="stHorizontalRadio"] {
    #         gap: 0px !important;
    #         background-color: transparent !important;
    #         border-bottom: 1px solid #e0e0e0;
    #         padding-bottom: 0px;
    #         margin-bottom: 1rem;
    #     }
        
    #     /* Cada opção do radio */
    #     div[data-testid="stHorizontalRadio"] label {
    #         background-color: transparent !important;
    #         border: none !important;
    #         border-radius: 0px !important;
    #         padding: 0.5rem 1rem !important;
    #         margin: 0px !important;
    #         font-size: 1rem;
    #         font-weight: 500;
    #         color: #6c6c6c;
    #         transition: all 0.2s ease;
    #     }
        
    #     /* Efeito hover */
    #     div[data-testid="stHorizontalRadio"] label:hover {
    #         color: #153e5a;
    #         background-color: rgba(21, 62, 90, 0.05) !important;
    #     }
        
    #     /* Opção selecionada */
    #     div[data-testid="stHorizontalRadio"] label[data-baseweb="radio"]:has(input:checked) {
    #         color: #153e5a !important;
    #         border-bottom: 2px solid #153e5a !important;
    #         background-color: transparent !important;
    #     }
        
    #     /* Esconder o botão de rádio original */
    #     div[data-testid="stHorizontalRadio"] label .st-ae {
    #         display: none !important;
    #     }
        
    #     /* Ajuste para alinhamento */
    #     div[data-testid="stHorizontalRadio"] label .st-bw {
    #         display: none !important;
    #     }
        
    #     /* Espaçamento entre as opções */
    #     div[data-testid="stHorizontalRadio"] label:not(:last-child) {
    #         margin-right: 0px !important;
    #     }
    # </style>
    # """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📝 Novo Processo", "✏️ Editar Processo Existente"])
    
    # ===== TAB 1: NOVO PROCESSO =====
    with tab1:
        _tela_novo_processo()
    
    # ===== TAB 2: EDITAR PROCESSO EXISTENTE =====
    with tab2:
        _tela_editar_processo()