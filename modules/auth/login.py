import os
import streamlit as st
import base64
import time as time_module
from datetime import datetime
from streamlit_local_storage import LocalStorage
import json
from logic import (validar_login_no_banco, TEMPO_SESSAO_SEGUNDOS)


def get_base64(bin_file):
    """Lê um arquivo de imagem e retorna sua versão codificada em Base64."""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

def login_screen(local_storage):
    """
    Gerencia a tela de login e a sessão de usuário.
    
    Args:
        local_storage: Instância do LocalStorage (passada pelo app.py)
    """
    st.session_state["skip_auto_reset"] = False

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

        /* Estilo da Logo e Títulos */
        .logo-container {{
            text-align: center;
            margin-top: -85px;
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

        div[data-testid="stTextInput"]:has(#text_input_2){{
            margin-top: -25px !important;
            margin-bottom: 0px !important;
        }}

        div.stButton {{
            margin-top: 15px !important;
        }}

        button[kind="primary"] {{
            background-color: #153e5a !important;
            border: none !important;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.2) !important;
        }}

        div[data-testid="stNotification"] > div {{
            background-color: rgba(64, 96, 100, 0.9) !important;
            color: white !important;
            border: 1px solid #6d8285 !important;
        }}

        .fusve-container {{
            text-align: center;
            margin-top: 20px;
            margin-bottom: 20px;
            width: 100%;
            display: flex;
            justify-content: center;
        }}

        .fusve-container img {{
            width: 110px;
            height: auto;
            opacity: 0.8;
            filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.1));
            background: transparent !important;
        }}

        /* Remover o container branco e esticar o fundo */
        .st-emotion-cache-p7p7gf {{
            background: transparent !important;
            box-shadow: none !important;
            border: none !important;
            backdrop-filter: none !important;
        }}

        /* Garantir que o fundo ocupe toda a tela */
        [data-testid="st.AppViewContainer"] {{
            background: url("data:image/png;base64,{bin_fundo}") no-repeat center center fixed !important;
            background-size: cover !important;
            background-position: center !important;
            min-height: 100vh !important;
            height: 100% !important;
        }}
         
    """, unsafe_allow_html=True)

    # ----- LAYOUT DO LOGIN (3 COLUNAS) -----
    col1, col2, col3 = st.columns([0.5, 2, 0.5]) 
    
    # ===== COLUNA 1 (esquerda - vazia) =====
    with col1:
        pass
    
    # ===== COLUNA 2 (centro - card de login) =====
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
            
            if st.button("Entrar", use_container_width=True, key='btn_entrar_login', type="primary"):
                if validar_login_no_banco(usuario, senha):
                    local_storage.setItem("usuario_audit", usuario, key='set_usuario_audit')
                    local_storage.setItem("login_timestamp", datetime.now().isoformat(), key='set_login_timestamp')
                    session_data = {
                        'usuario': usuario,
                        'timestamp': datetime.now().isoformat()
                    }
                    local_storage.setItem('session_data', json.dumps(session_data))

                    st.session_state["autenticado"] = True
                    st.session_state["usuario_logado"] = usuario
                    st.session_state['login_timestamp'] = datetime.now()
                    st.session_state.pop('sessao_expirada', None)
                    st.success("Login realizado com sucesso!")
                    time_module.sleep(1)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

        # Logo FUSVE (abaixo do card)
        st.markdown(f'''
            <div class="fusve-container">
                <img src="data:image/png;base64,{bin_logo_fusve}">
            </div>
        ''', unsafe_allow_html=True)
        
        # Logo IIA (abaixo da FUSVE)
        try:
            bin_logo_iia = get_base64(os.path.join("assets", "logo_iia.png"))
            st.markdown(f'''
                <div style="text-align: center; margin-top: 25px; margin-bottom: 15px;">
                    <img src="data:image/png;base64,{bin_logo_iia}" 
                         style="height: 50px; width: auto; opacity: 0.9;">
                </div>
            ''', unsafe_allow_html=True)
        except:
            pass
    
    # ===== CSS PARA LOGO FIXA E RESPONSIVA =====
    st.markdown("""
        <style>
            /* Logo fixa no canto inferior direito */
            .floating-logos {
                position: fixed;
                bottom: 5vh;      /* 5% da altura da viewport */
                right: 7vw;       /* 3% da largura da viewport */
                z-index: 9999;
                display: flex;
                gap: 12px;
                transition: all 0.3s ease;
            }
            .floating-logos img {
                height: 50px;
                width: auto;
                /* max-width: 50px; */
                object-fit: contain;
                opacity: 0.85;
                transition: opacity 0.2s;
            }
            .floating-logos img:hover {
                opacity: 1;
            }
            
            /* Ajuste para telas menores (CELULAR) */
            @media (max-width: 768px) {
                .floating-logos {
                    bottom: 3vh;
                    right: 3vw;
                    gap: 8px;
                    padding: 5px 8px;
                }
                .floating-logos img {
                    height: 30px;
                }
            }
            
            /* Ajuste para telas muito grandes */
            @media (min-width: 1920px) {
                .floating-logos {
                    bottom: 8vh;
                    right: 5vw;
                }
                .floating-logos img {
                    height: 50px;
                }
            }
        </style>
    """, unsafe_allow_html=True)

    # ===== ADICIONAR A LOGO =====
    try:
        bin_logo_coso = get_base64(os.path.join("assets", "logo_coso.png"))
        bin_logo_ibgc = get_base64(os.path.join("assets", "logo_ibgc.png"))
        st.markdown(f'''
            <div class="floating-logos">
                <img src="data:image/png;base64,{bin_logo_coso}" 
                    style="height: 40px; width: auto;"
                    title="Committee of Sponsoring Organizations">
                <img src="data:image/png;base64,{bin_logo_ibgc}"
                    style="height: 50px; width: auto;">
    
            </div>
        ''', unsafe_allow_html=True)
    except:
        pass
                    
    return False

def verificar_sessao(local_storage=None, login_timestamp_cache=None):
    # Se não recebeu local_storage, tenta criar (fallback)
    if local_storage is None:
        from streamlit_local_storage import LocalStorage
        local_storage = LocalStorage()
    # Se não recebeu por parâmetro, tenta do session_state
    login_time = st.session_state.get("login_timestamp") or login_timestamp_cache
    if st.session_state.get("autenticado") and login_time:
        tempo_decorrido = (datetime.now() - login_time).total_seconds()
        if tempo_decorrido > TEMPO_SESSAO_SEGUNDOS:
            # expirada
            st.session_state["autenticado"] = False
            st.session_state["usuario_logado"] = None
            st.session_state.pop("login_timestamp", None)
            try:
                local_storage.deleteItem("session_data")
            except:
                local_storage.setItem("session_data", "null")
            return False
    return True
