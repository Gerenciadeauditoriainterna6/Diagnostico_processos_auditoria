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
            
            if st.button("Entrar", use_container_width=True, key='btn_entrar_login',type="primary"):
                if validar_login_no_banco(usuario, senha):
                    # --- GRAVAÇÃO NO LOCAL STORAGE (ÚNICA MUDANÇA FUNCIONAL) ---
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

        st.markdown(f'''
                <div class="fusve-container">
                    <img src="data:image/png;base64,{bin_logo_fusve}">
                </div>
            ''', unsafe_allow_html=True)
        
        # ===== NOVA LOGO: IIA (abaixo da FUSVE) =====
        try:
            bin_logo_iia = get_base64(os.path.join("assets", "logo_iia.png"))
            st.markdown(f'''
                <div style="text-align: center; margin-top: -10px; margin-bottom: 15px;">
                    <img src="data:image/png;base64,{bin_logo_iia}" 
                        style="height: 50px; width: auto; opacity: 0.9;">
                </div>
            ''', unsafe_allow_html=True)
        except Exception as e:
            # Se a imagem não for encontrada, apenas ignora
            pass

        # ===== CSS PARA AS LOGOS DO RODAPÉ =====
        st.markdown("""
            <style>
                /* Container para as logos do rodapé (canto inferior direito) */
                .footer-logos {
                    position: fixed;
                    bottom: 10px;
                    right: 10px;
                    display: flex;
                    gap: 12px;
                    z-index: 999;
                    background-color: rgba(255, 255, 255, 0.85);
                    padding: 6px 12px;
                    border-radius: 8px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .footer-logos img {
                    height: 35px;
                    width: auto;
                    max-width: 70px;
                    object-fit: contain;
                }
                /* Ajuste para telas menores */
                @media (max-width: 768px) {
                    .footer-logos img {
                        height: 25px;
                    }
                    .footer-logos {
                        gap: 8px;
                        padding: 4px 8px;
                    }
                }
            </style>
        """, unsafe_allow_html=True)

        # ===== LOGOS DO RODAPÉ (canto inferior direito) =====
        try:
            # Carregar a logo do CFC
            bin_logo_cfc = get_base64(os.path.join("assets", "logo_cfc.png"))
            
            st.markdown(f'''
                <div class="footer-logos">
                    <img src="data:image/png;base64,{bin_logo_cfc}" title="Conselho Federal de Contabilidade">
                </div>
            ''', unsafe_allow_html=True)
        except Exception as e:
            # Se a imagem não for encontrada, apenas ignora
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
