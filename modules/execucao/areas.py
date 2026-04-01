"""
Módulo de Cadastro de Áreas e Funcionários
"""
import streamlit as st
import pandas as pd
from logic import (
    salvar_area, listar_areas, salvar_funcionarios_area, 
    listar_funcionarios_area, listar_funcionarios_por_area
)
from sqlalchemy import text
from database import engine
from modules.shared.theme import get_theme_css

def tela_cadastro_area():
    """Tela para cadastro de áreas e seus funcionários"""
    # CSS com seletores mais diretos
    st.markdown("""
        <style>
            /* Estiliza o container do formulário */
            .stForm {
                background-color: var(--card-bg, #ffffff) !important;
                border-radius: 16px !important;
                padding: 24px !important;
                border: 1px solid #e0e0e0 !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
            }
            
            /* Estiliza os inputs de texto dentro do formulário */
            .stForm input[type="text"],
            .stForm input[type="password"],
            .stForm input[type="email"],
            .stForm input[type="number"] {
                background-color: var(--background) !important;
                border: 1px solid #ced4da !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
                color: #182418 !important;
            }
            
            /* Estiliza as áreas de texto */
            .stForm textarea {
                background-color: var(--background) !important;
                border: 1px solid #ced4da !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
                color: #182418 !important;
            }
            
            /* Estiliza os selects (dropdowns) */
            .stForm select {
                background-color: #ffffff !important;
                border: 1px solid #ced4da !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
                color: #182418 !important;
            }
            
            /* Efeito ao focar no campo */
            .stForm input:focus,
            .stForm textarea:focus,
            .stForm select:focus {
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
            
            /* Estiliza os containers de funcionário (com borda) */
            .funcionario-card {
                background-color: var(--card-bg, #ffffff) !important;
                border-radius: 16px !important;
                padding: 24px !important;
                border: 1px solid #e0e0e0 !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
                }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🏢 Cadastro de Áreas e Funcionários")
    
    # Abas para separar as funcionalidades
    tab1, tab2, tab3 = st.tabs(["📌 Cadastrar Nova Área", "👥 Cadastrar Funcionários", "📋 Gerenciar"])
    
    with tab1:
        st.subheader("Nova Área")
        
        with st.form("form_nova_area"):
        
            nome_area = st.text_input("Nome da Área *", help="Ex: Gerência Financeira, Recursos Humanos, etc.")
            
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("E-mail", help="E-mail da área")
            with col2:
                telefone = st.text_input("Telefone", help="Telefone da área")
            
            gestor = st.text_input("Nome do Gestor *", help="Nome do responsável pela área")
            objetivo = st.text_area("Objetivo da Área", help="Descreva brevemente o propósito da área")

            st.markdown("""
                <style>
                    /* Seleciona o selectbox de Status pelo aria-label */
                    div[aria-label="Selected Ativo. Status"] {
                        width: 200px !important;
                    }
                    
                    /* Ou se preferir pelo container principal */
                    div[data-baseweb="select"] {
                        width: 200px !important;
                    }
                    
                    /* Para afetar apenas dentro do formulário de nova área */
                    form[data-testid="stForm"] div[data-baseweb="select"] {
                        width: 200px !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # status = st.selectbox("Status", ["Ativo", "Inativo"]) Removido por enquanto
            
            if st.form_submit_button("💾 Salvar Área", type="primary", key='btn_salvar_area'):
                if not nome_area or not gestor:
                    st.error("Nome da Área e Nome do Gestor são obrigatórios.")
                else:
                    dados_area = {
                        "nome": nome_area,
                        "objetivo": objetivo,
                        #"status": status,
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
                        st.markdown(f"""
                        - **{func['nome_funcionario']}**  
                          *{func['cargo']}* | {func['tempo_funcao']} na função, {func['tempo_empresa']} na empresa
                        """)
            
            st.divider()
            st.markdown("### ➕ Novo Funcionário")
            
            # Inicializar lista de funcionários temporários
            if 'funcionarios_temp' not in st.session_state:
                st.session_state['funcionarios_temp'] = [{"nome": "", "cargo": "", "tempo_funcao": "", "tempo_empresa": ""}]
            
            with st.form(key="form_funcionarios"):
                # Mostrar funcionários para cadastro
                for i, func in enumerate(st.session_state['funcionarios_temp']):
                    st.markdown(f"**Funcionário {i+1}**")
                    
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        func['nome'] = st.text_input(
                            "Nome completo *",
                            value=func.get('nome', ''),
                            key=f"func_nome_{i}"
                        )
                    with col_f2:
                        func['cargo'] = st.text_input(
                            "Cargo",
                            value=func.get('cargo', ''),
                            key=f"func_cargo_{i}"
                        )
                    
                    col_f3, col_f4 = st.columns(2)
                    with col_f3:
                        func['tempo_funcao'] = st.text_input(
                            "Tempo na função",
                            value=func.get('tempo_funcao', ''),
                            key=f"func_tempof_{i}",
                            placeholder="Ex: 2 anos"
                        )
                    with col_f4:
                        func['tempo_empresa'] = st.text_input(
                            "Tempo na empresa",
                            value=func.get('tempo_empresa', ''),
                            key=f"func_tempoe_{i}",
                            placeholder="Ex: 3 anos"
                        )
                    
                    st.divider()
                
                # Botões dentro do formulário
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                with col_btn1:
                    if st.form_submit_button("➕ Adicionar outro funcionário", use_container_width=True):
                        st.session_state['funcionarios_temp'].append({"nome": "", "cargo": "", "tempo_funcao": "", "tempo_empresa": ""})
                        st.rerun()
                
                with col_btn2:
                    if st.form_submit_button("❌ Remover último funcionário", use_container_width=True):
                        if len(st.session_state['funcionarios_temp']) > 1:
                            st.session_state['funcionarios_temp'].pop()
                            st.rerun()
                
                with col_btn3:
                    if st.form_submit_button("💾 Salvar Funcionários", type="primary", use_container_width=True):
                        funcionarios_validos = [f for f in st.session_state['funcionarios_temp'] if f.get('nome', '').strip()]
                        
                        if not funcionarios_validos:
                            st.error("Adicione pelo menos um funcionário com nome.")
                        else:
                            if salvar_funcionarios_area(id_area_selecionada, funcionarios_validos):
                                st.success(f"✅ {len(funcionarios_validos)} funcionário(s) cadastrado(s) com sucesso!")
                                st.session_state['funcionarios_temp'] = [{"nome": "", "cargo": "", "tempo_funcao": "", "tempo_empresa": ""}]
                                st.rerun()
                            else:
                                st.error("Erro ao cadastrar funcionários.")
    
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
                        for _, func in df_func.iterrows():
                            st.markdown(f"""
                            - **{func['nome_funcionario']}**  
                              *{func['cargo']}* | {func['tempo_funcao']} na função, {func['tempo_empresa']} na empresa
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