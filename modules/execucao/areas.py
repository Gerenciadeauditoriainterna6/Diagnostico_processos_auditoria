"""
Módulo de Cadastro de Áreas e Funcionários
"""
import streamlit as st
import pandas as pd
import time as time_module
from logic import (
    salvar_area, listar_areas, salvar_funcionarios_area, 
    listar_funcionarios_area, listar_funcionarios_por_area
)
from sqlalchemy import text
from database import engine
from modules.shared.theme import get_theme_css

# modules/execucao/areas.py

def tela_cadastro_area():
    """Tela para cadastro de áreas e seus funcionários"""
    
    # --- ESTILIZAÇÃO PERSONALIZADA PARA ESTA TELA ---
    st.markdown("""
        <style>
            /* ==== ESTILIZA O CONTAINER PRINCIPAL ==== */
                
                div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) {
                    background-color: #ffffff !important;
                    border-radius: 16px !important;
                    border: 1px solid #e0e0e0 !important;
                    padding: 20px !important;
                    margin-bottom: 20px !important;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
                }

            /* ===== ESTILIZA OS CAMPOS DENTRO DO CONTAINER ===== */

            /* Estiliza os textareas */
            div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) textarea {
                background-color: var(--input) !important;
                border: 1px solid #ced4da !important;
                border-radius: 8px !important;
                padding: 10px !important;
            }

            /* Estiliza os inputs (text_input) */
            div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) input {
                background-color: var(--input) !important;
                border: 1px solid #ced4da !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
            }

            /* Estiliza os selectboxes (dropdown) */
            div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) select {
                background-color: #ffffff !important;
                border: 1px solid #ced4da !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
            }

            /* Estiliza os labels (títulos dos campos) */
            div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) label {
                color: #48606c !important;
                font-weight: 500 !important;
                margin-bottom: 4px !important;
            }

            /* Efeito ao focar nos campos */
            div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) textarea:focus,
            div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) input:focus,
            div[data-testid="stVerticalBlock"]:has(> div > .stTextArea) select:focus {
                border-color: #1848d8 !important;
                outline: none !important;
                box-shadow: 0 0 0 3px rgba(24, 72, 216, 0.1) !important;
            }
        </style>  
    """, unsafe_allow_html=True)

    st.title("🏢 Cadastro de Áreas e Funcionários")
    
    # Abas para separar as funcionalidades
    tab1, tab2, tab3 = st.tabs(["📌 Cadastrar Nova Área", "👥 Cadastrar Funcionários", "📋 Gerenciar"])
    
    with tab1:
        
        with st.container(border=True):
            st.subheader("Nova Área")
                
            nome_area = st.text_input("Nome da Área *", help="Ex: Gerência Financeira, Recursos Humanos, etc.")
            
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("E-mail", help="E-mail da área")
            with col2:
                telefone = st.text_input("Telefone", help="Telefone da área")
            
            gestor = st.text_input("Nome do Gestor *", help="Nome do responsável pela área")
            objetivo = st.text_area("Objetivo da Área", help="Descreva brevemente o propósito da área")
            
            if st.button("💾 Salvar Área", type="primary", key='btn_salvar_area'):
                if not nome_area or not gestor:
                    st.error("Nome da Área e Nome do Gestor são obrigatórios.")
                else:
                    dados_area = {
                        "nome": nome_area,
                        "objetivo": objetivo,
                        "status": "Ativo",
                        "email": email,
                        "telefone": telefone,
                        "gestor": gestor
                    }
                    
                    id_area = salvar_area(dados_area)
                    
                    if id_area:
                        st.success(f"✅ Área '{nome_area}' cadastrada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao cadastrar área.")
    
    with tab2:
        st.subheader("Cadastrar Funcionários")
        if 'funcionarios_version' not in st.session_state:
            st.session_state['funcionarios_version'] = 0
        
        # Selecionar a área primeiro
        df_areas = listar_areas()
        
        if df_areas.empty:
            st.warning("⚠️ Nenhuma área cadastrada. Cadastre uma área primeiro na aba 'Cadastrar Nova Área'.")
        else:
            # Selectbox para escolher a área
            opcoes_area = {f"{row['nome_area']}": row['id_area'] for _, row in df_areas.iterrows()}
            area_selecionada = st.selectbox(
                "Selecione a Área para cadastrar funcionários:",
                options=list(opcoes_area.keys())
            )
            id_area_selecionada = opcoes_area[area_selecionada]
            
            # Mostrar funcionários existentes
            df_func_existentes = listar_funcionarios_area(id_area_selecionada)
            if not df_func_existentes.empty:
                with st.expander("👥 Funcionários já cadastrados nesta área", expanded=False):
                    for _, func in df_func_existentes.iterrows():
                        from logic import calcular_tempo
                        tempo_funcao = calcular_tempo(func.get('data_inicio_funcao'))
                        tempo_empresa = calcular_tempo(func.get('data_inicio_empresa'))
                        st.markdown(f"""- **{func['nome_funcionario']}** *{func['cargo']}* | {tempo_funcao} na função, {tempo_empresa} na empresa""")
            
            st.divider()
            st.markdown("### ➕ Novo Funcionário")
            # ===== CSS corrigido =====
            st.markdown("""
                <style>
                    /* Pega o container principal da lista de funcionários */
                    div[data-testid="stVerticalBlock"].st-emotion-cache-139wymi {
                        background-color: #ffffff !important;
                        border-radius: 16px !important;
                        border: 1px solid #e0e0e0 !important;
                        padding: 20px !important;
                        margin-bottom: 20px !important;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
                    }
                    
                    /* Inputs dentro do container */
                    div[data-testid="stVerticalBlock"].st-emotion-cache-139wymi input {
                        background-color: var(--input) !important;
                        border: 1px solid #ced4da !important;
                        border-radius: 8px !important;
                        padding: 8px 12px !important;
                    }
                    
                    /* Labels dentro do container */
                    div[data-testid="stVerticalBlock"].st-emotion-cache-139wymi label {
                        color: #48606c !important;
                        font-weight: 500 !important;
                        margin-bottom: 4px !important;
                    }
                    
                    /* Efeito ao focar */
                    div[data-testid="stVerticalBlock"].st-emotion-cache-139wymi input:focus {
                        border-color: #1848d8 !important;
                        outline: none !important;
                        box-shadow: 0 0 0 3px rgba(24, 72, 216, 0.1) !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            with st.container(border=True):
                    
                # Inicializar lista de funcionários temporários
                if 'funcionarios_temp' not in st.session_state:
                    st.session_state['funcionarios_temp'] = [{"nome": "", "cargo": "", "data_inicio_funcao": None, "data_inicio_empresa": None}]
                
                # Mostrar funcionários para cadastro
                for i, func in enumerate(st.session_state['funcionarios_temp']):
                    st.markdown(f"**Funcionário {i+1}**")
                    
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        nome_valor = func.get('nome', '')
                        st.text_input(
                            "Nome completo *",
                            value=nome_valor,
                            key=f"func_nome_{i}_{st.session_state['funcionarios_version']}"
                        )
                        # Atualizar o valor do dicionário
                        func['nome'] = st.session_state.get(f"func_nome_{i}_{st.session_state['funcionarios_version']}", '')

                    with col_f2:
                        cargo_valor = func.get('cargo', '')
                        st.text_input(
                            "Cargo",
                            value=cargo_valor,
                            key=f"func_cargo_{i}_{st.session_state['funcionarios_version']}"
                        )
                        func['cargo'] = st.session_state.get(f"func_cargo_{i}_{st.session_state['funcionarios_version']}", '')

                    
                    # ==== NOVOS CAMPOS DE DATA ====
                    col_f3, col_f4 = st.columns(2)
                    with col_f3:
                        data_funcao = st.date_input(
                            "Data de inicio na função",
                            value=func.get('data_inicio_funcao'),
                            format="DD/MM/YYYY",
                            key=f"func_data_funcao_{i}_{st.session_state['funcionarios_version']}",
                            help="Quando o funcionário começou nesta função?"
                        )
                        func['data_inicio_funcao'] = data_funcao

                    with col_f4:
                        data_empresa = st.date_input(
                            "Data de início na empresa",
                            value=func.get('data_inicio_empresa'),
                            format="DD/MM/YYYY",
                            key=f"func_data_empresa_{i}_{st.session_state['funcionarios_version']}",
                            help="Quando o funcionário entrou na empresa"
                        )
                        func['data_inicio_empresa'] = data_empresa
                    
                    st.divider()
                
                # Botões dentro do formulário
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                with col_btn1:
                    if st.button("➕ Adicionar outro funcionário", use_container_width=True):
                        st.session_state['funcionarios_temp'].append({"nome": "", "cargo": "", "data_inicio_funcao": None, "data_inicio_empresa": None})
                        st.rerun()
                
                with col_btn2:
                    if st.button("❌ Remover último funcionário", use_container_width=True):
                        if len(st.session_state['funcionarios_temp']) > 1:
                            st.session_state['funcionarios_temp'].pop()
                            st.rerun()
                
                with col_btn3:
                    if st.button("💾 Salvar Funcionários", type="primary", use_container_width=True):
                        funcionarios_validos = [f for f in st.session_state['funcionarios_temp'] if f.get('nome', '').strip()]
                        
                        if not funcionarios_validos:
                            st.error("❌ Adicione pelo menos um funcionário com nome.")
                        else:
                            if salvar_funcionarios_area(id_area_selecionada, funcionarios_validos):
                                # ===== LIMPAR TUDO =====
                                st.session_state['funcionarios_temp'] = [{"nome": "", "cargo": "", "data_inicio_funcao": None, "data_inicio_empresa": None}]
                                # Incrementar versão para forçar recriação dos widgets
                                st.session_state['funcionarios_version'] += 1
                                
                                # Toast de sucesso
                                st.toast(f"✅ {len(funcionarios_validos)} funcionário(s) cadastrado(s) com sucesso!", icon="👥")
                                
                                time_module.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("❌ Erro ao cadastrar funcionários. Tente novamente.")
    
    with tab3:
        st.subheader("Áreas e Funcionários Cadastrados")
        
        df_areas = listar_areas()
        
        if not df_areas.empty:
            for _, row in df_areas.iterrows():
                with st.expander(f"🏢 {row['nome_area']} - Gestor: {row['gestor']}"):
                    st.write(f"**E-mail:** {row['email'] or 'Não informado'}")
                    st.write(f"**Telefone:** {row['telefone'] or 'Não informado'}")
                    st.write(f"**Objetivo:** {row['objetivo_area'] or 'Não informado'}")
                    st.write(f"**Status:** {row['status']}")
                    
                    # Listar funcionários da área
                    df_func = listar_funcionarios_area(row['id_area'])
                    
                    if not df_func.empty:
                        st.markdown("**👥 Funcionários:**")
                        from logic import calcular_tempo
                        for _, func in df_func.iterrows():
                            tempo_funcao = calcular_tempo(func.get('data_inicio_funcao'))
                            tempo_empresa = calcular_tempo(func.get('data_inicio_empresa'))
                            st.markdown(f"""
                            - **{func['nome_funcionario']}**  
                            *{func['cargo']}* | {tempo_funcao} na função, {tempo_empresa} na empresa
                            """)
                    else:
                        st.info("Nenhum funcionário cadastrado para esta área.")
        else:
            st.info("Nenhuma área cadastrada.")

def carregar_areas_banco():
    """ Busca áreas no Banco de Dados e retorna um dicionário {nome: id}."""
    query = text("SELECT id_area, nome_area FROM informacoes_area")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Transforma o DataFrame em um dicionário {'Nome da Área': id_area}
    # Zip junta as duas colunas: a primeira vira chave, a segunda vira valor
    return dict(zip(df['nome_area'], df['id_area']))