import os
import streamlit as st
import base64
import time as time_module
from datetime import datetime
from streamlit_local_storage import LocalStorage
import json
from logic import (validar_login_no_banco, TEMPO_SESSAO_SEGUNDOS)
#teste
# Importante: adicione esta função no início do seu arquivo
def custom_spinner():
    """Retorna HTML/CSS para um spinner personalizado"""
    return """
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 20px 0;">
        <div class="custom-spinner"></div>
        <p style="color: white; margin-top: 15px; font-size: 14px; font-family: sans-serif;">
            🔐 Verificando credenciais...
        </p>
    </div>
    
    <style>
        .custom-spinner {
            width: 20px;
            height: 20px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top-color: #0b5b99;
            border-bottom-color: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            animation: spin 0.7s ease-in-out infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """

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
            /* ========== 1. Fundo da tela de login ========== */
            body {{
                background: url("data:image/png;base64,{bin_fundo}")no-repeat center center fixed !important;
                background-size: cover !important;
                background-position: center !important;
                /* Remove margens padrão do body para evitar espaço extra */
                margin: 0 !important;
                padding: 0 !important;
            }}

            /* Remover o container branco e esticar o fundo */
            .st-emotion-cache-p7p7gf {{
                background: transparent !important;
                box-shadow: none !important;
                border: none !important;
                backdrop-filter: none !important;
            }}

            /* ========== 2. REMOVER ESPAÇOS EXTRAS DO STREAMLIT ========== */
            /* Remove o padding superior do conteúdo principal (block-container) */
            .block-container {{
                padding-top: 5rem !important;
                padding-bottom: 0rem !important;
                max-width: 50% !important;
            }}
            
            /* ========== 3. CARD DE LOGIN ========== */
            div[data-testid="stVerticalBlockBorder"], 
            .stVerticalBlockBorder, 
            .st-emotion-cache-139wymi, 
            .st-emotion-cache-1r6slb0
            .st-emotion-cache-18kf3ut {{
                background: linear-gradient(180deg, #6d8285 0%, #406064 100%) !important;
                border: 2.3px solid rgba(4, 46, 87, 100) !important;
                box-shadow: 0px 15px 25px rgba(0,0,0,0.3) !important;
                border-radius: 20px !important;
                padding: 25px 50px 40px 50px !important; 
                display: block !important;
                flex-direction: column !important;
                width: 85% !important;
                height: 420px !important;
                min-height: 100px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                opacity: 1 !important;
                transition: none !important;
            }}

            /* ========== 4. CONTAINER PAI DO CARD ========== */

            /* ========== 5. LOGO PRINCIPAL ========== */
            /* Estilo da Logo e Títulos */
            .logo-container {{
                text-align: center;
                margin-top: -80px;
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

            /* ========== 6. TÍTULOS ========== */
            /* Sem alterações */
            div[style*="text-align: center; width: 100%; line-height: 1.2;"] {{
                margin-bottom: 15px !important; /* Ajusta o espaçamento entre o acesso restrito e o campo de usuario */
            }}
            .acesso-restrito {{
                margin-top: 0px !important;
                margin-bottom: 50px !important;
            }}

            /* ========== 7. CAMPOS DE INPUT ========== */

            div[data-testid="stTextInput"] {{
                margin-bottom: -10px !important;
                transition: none !important;
            }}

            div[data-testid="stTextInput"] input[type="password"] {{
                margin-top: 0px !important;
                margin-bottom: 0px !important;
                transition: none !important;
            }}

            /* ========== 8. BOTÃO DE ENTRAR ========== */
            div.stButton {{
                margin-top: 35px !important;
                transition: none !important;
            }}

            button[kind="primary"] {{
                background-color: #153e5a !important;
                border: 2px solid #184145 !important;
                box-shadow: 0px 4px 10px rgba(0,0,0,0.2) !important;
            }}

            button[kind="primary"]:hover {{
                background-color: rgba(11, 91, 153, 0.8) !important;
                border: 2px solid #0b5b99 !important;
                cursor: pointer !important;
                transform: translateY(-1px) !important;
                box-shadow: 0px 6px 12px rgba(0,0,0,0.25) !important;
            }}

            /* ========== 8.1 SPINNER DE LOGIN ==========
            /* Seletor mais abrangente para o spinner */
            .stSpinner {{
                margin: 30px 0 !important;
                text-align: center !important;
            }}

            /* Para o container do spinner */
            div[class*="stSpinner"] {{
                margin: 25px auto !important;
                display: flex !important;
                justify-content: center !important;
            }}

            /* ========== SPINNER DE LOGIN - COR DOURADA ========== */

            /* Elemento i do spinner */
            i[data-testid="stSpinnerIcon"]::before {{
                color: #ffc107 !important;
                font-size: 10px !important;
                width: 20px !important;
                height: 20px !important;
            }}

            /* ========== 9. LOGOS INFERIORES (FUSVE e IIA) ========== */
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


            /* ========== 10. RESPONSIVIDADE ========== */
            @media (max-width: 768px) {{
                .block-container {{
                    padding-top: 2rem !important;   /* Menor espaçamento no celular */
                    max-width: 90% !important;
                }}
                .logo-container img {{
                    width: 90px !important;
                }}
                .fusve-container img {{
                    width: 80px !important;
                }}
                div[style*="text-align: center; margin-top: 25px; margin-bottom: 15px;"] img {{
                    height: 40px !important;
                }}
                .floating-logos img {{
                    height: 35px !important;
                }}
            }}

            @media (min-width: 1920px) {{
                .block-container {{
                    padding-top: 8rem !important;   /* Mais espaço no topo para telas grandes */
                    max-width: 40% !important;
                }}
                .floating-logos img {{
                    height: 60px !important;
                }}
            }}

            /* ========== 11. Esconde o cabeçalho padrão ========== */
            header {{ visibility: hidden; }}

            /* ========== 12. LOGOS FLUTUANTES (canto inferior direito) ========== */

            /* Logo fixa no canto inferior direito */
            .floating-logos {{
                position: fixed;
                bottom: 4vh;      /* 5% da altura da viewport */
                right: 4vw;       /* 3% da largura da viewport */
                z-index: 9999;
                display: flex;
                gap: 12px;
                transition: all 0.3s ease;
            }}
            .floating-logos img {{
                height: 50px;
                width: auto;
                /* max-width: 50px; */
                object-fit: contain;
                opacity: 0.85;
                transition: opacity 0.2s;
            }}
            .floating-logos img:hover {{
                opacity: 1;
            }}
            
            /* Ajuste para telas menores (CELULAR) */
            @media (max-width: 768px) {{
                .floating-logos {{
                    bottom: 3vh;
                    right: 3vw;
                    gap: 8px;
                    padding: 5px 8px;
                }}
                .floating-logos img {{
                    height: 30px;
                }}
            }}
            
            /* Ajuste para telas muito grandes */
            @media (min-width: 1920px) {{
                .floating-logos {{
                    bottom: 8vh;
                    right: 5vw;
                }}
                .floating-logos img {{ 
                    height: 50px;
                }}
            }} 

            /* ===== ESCONDE APENAS OS IFRAMES DO LOCALSTORAGE ===== */
            iframe[title="streamlit_local_storage.st_local_storage"] {{
                display: none !important;
                height: 0 !important;
                width: 0 !important;
                visibility: hidden !important;
            }}
            
            /* Remove apenas os containers específicos dos iframes, não todos */
            div:has(> iframe[title="streamlit_local_storage.st_local_storage"]) {{
                height: 0 !important;
                min-height: 0 !important;
                overflow: hidden !important;
            }}
        

        </style>

         
    """, unsafe_allow_html=True)

    st.markdown("""
        <script>
            // Debug: mostra as cores de fundo no console do navegador
            console.log("=== DEBUG DE CORES DE FUNDO ===");
            
            var elementos = [
                'body',
                '[data-testid="stAppViewContainer"]',
                '.st-emotion-cache-p7p7gf',
                '.st-emotion-cache-139wymi',
                '.st-emotion-cache-1r6slb0'
            ];
            
            elementos.forEach(function(sel) {
                var el = document.querySelector(sel);
                if (el) {
                    var bg = window.getComputedStyle(el).backgroundColor;
                    console.log(sel + ' -> ' + bg);
                } else {
                    console.log(sel + ' -> não encontrado');
                }
            });
        </script>
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
                <span style="color: #822a2d; font-family: sans-serif; font-size: 10px; font-weight: bold; display: block; margin-top: 10px; margin-bottom: -20px;">ACESSO RESTRITO!</span>
            </div>
            ''', unsafe_allow_html=True)

            usuario = st.text_input("", placeholder="👤 Digite seu usuário", key="user_login")
            senha = st.text_input("", type="password", placeholder="🔑 Digite sua senha", key="pass_login")
            
            if st.button("Entrar", use_container_width=True, key='btn_entrar_login', type="primary"):
                # Criar placeholder para o spinner
                spinner_placeholder = st.empty()
                
                # Mostrar spinner customizado
                spinner_placeholder.markdown(custom_spinner(), unsafe_allow_html=True)
                
                # Pequeno delay para mostrar o spinner
                time_module.sleep(1.3)
                
                sucesso, usuario_id, usuario_nome, usuario_perfil = validar_login_no_banco(usuario, senha)

                if sucesso:
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_logado'] = usuario
                    st.session_state['usuario_nome'] = usuario_nome
                    st.session_state['usuario_id'] = usuario_id
                    st.session_state['usuario_perfil'] = usuario_perfil
                    # Remove o spinner
                    spinner_placeholder.empty()
                    
                    # ========== MODAL DE SUCESSO ==========
                    modal_placeholder = st.empty()
                    
                    modal_placeholder.markdown("""
                        <div class="success-modal">
                            <div class="modal-overlay"></div>
                            <div class="modal-content">
                                <div class="checkmark-circle">
                                    <div class="checkmark"></div>
                                </div>
                                <h2>Bem-vindo!</h2>
                                <p>Login realizado com sucesso</p>
                                <p>Você está sendo redirecionado!</p>
                                <div class="loading-dots">
                                    <span>.</span><span>.</span><span>.</span>
                                </div>
                            </div>
                        </div>
                        
                        <style>
                            @keyframes fadeIn {
                                from { opacity: 0; }
                                to { opacity: 1; }
                            }
                            
                            @keyframes checkmark {
                                0% { transform: scale(0); opacity: 0; }
                                50% { transform: scale(1.2); }
                                100% { transform: scale(1); opacity: 1; }
                            }
                            
                            @keyframes dots {
                                0%, 20% { opacity: 0; }
                                40% { opacity: 1; }
                                100% { opacity: 1; }
                            }
                            
                            .success-modal {
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                z-index: 9999;
                                animation: fadeIn 0.5s ease-out;
                            }
                            
                            .modal-overlay {
                                position: absolute;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                background: rgba(0,0,0,0.5);
                            }
                            
                            .modal-content {
                                background: linear-gradient(135deg, #184145, #6b8085);
                                border-radius: 20px;
                                padding: 40px;
                                text-align: center;
                                z-index: 10000;
                                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                                animation: fadeIn 0.3s ease-out;
                            }
                            
                            .checkmark-circle {
                                width: 80px;
                                height: 80px;
                                background: white;
                                border-radius: 50%;
                                margin: 0 auto 20px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                animation: checkmark 0.5s ease-out;
                            }
                            
                            .checkmark {
                                width: 40px;
                                height: 20px;
                                border-left: 4px solid #28a745;
                                border-bottom: 4px solid #28a745;
                                transform: rotate(-45deg);
                                margin-top: -10px;
                            }
                            
                            .modal-content h2 {
                                color: white;
                                margin: 0 0 10px;
                                font-size: 24px;
                            }
                            
                            .modal-content p {
                                color: rgba(255,255,255,0.95);
                                margin: 0;
                            }
                            
                            .loading-dots {
                                margin-top: 15px;
                            }
                            
                            .loading-dots span {
                                display: inline-block;
                                font-size: 24px;
                                color: white;
                                animation: dots 1.5s infinite;
                            }
                            
                            .loading-dots span:nth-child(2) { animation-delay: 0.3s; }
                            .loading-dots span:nth-child(3) { animation-delay: 0.6s; }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    # ========== FIM DO MODAL ==========
                    
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
                    
                    # Delay para mostrar o modal antes de redirecionar
                    time_module.sleep(2.5)
                    
                    # Remove o modal
                    modal_placeholder.empty()
                    
                    st.rerun()
                else:
                    # Remove o spinner
                    spinner_placeholder.empty()
                    st.toast("❌ Usuário ou senha incorretos.")

        # Logo FUSVE (abaixo do card)
        st.markdown(f'''
            <div class="fusve-container">
                <img src="data:image/png;base64,{bin_logo_fusve}">
            </div>
        ''', unsafe_allow_html=True)
        
        # # Logo IIA (abaixo da FUSVE)
        # try:
        #     bin_logo_iia = get_base64(os.path.join("assets", "logo_iia.png"))
        #     st.markdown(f'''
        #         <div style="text-align: center; margin-top: 25px; margin-bottom: 15px;">
        #             <img src="data:image/png;base64,{bin_logo_iia}" 
        #                  style="height: 50px; width: auto; opacity: 0.9;">
        #         </div>
        #     ''', unsafe_allow_html=True)
        # except:
        #     pass

    # # ===== LOGOS DE CANTO DA TELA =====
    # try:
    #     bin_logo_coso = get_base64(os.path.join("assets", "logo_coso.png"))
    #     bin_logo_ibgc = get_base64(os.path.join("assets", "logo_ibgc.png"))
    #     bin_logo_denasus = get_base64(os.path.join("assets", "logo_denasus.png"))
    #     bin_logo_iso31000 = get_base64(os.path.join("assets", "logo_iso31000.png"))
    #     st.markdown(f'''
    #         <div class="floating-logos">
    #             <img src="data:image/png;base64,{bin_logo_coso}" style="height: 40px; width: auto;" title="Committee of Sponsoring Organizations">
    #             <img src="data:image/png;base64,{bin_logo_ibgc}" style="height: 50px; width: auto;">
    #             <img src="data:image/png;base64,{bin_logo_denasus}" style="height: 40px; width: auto;">
    #             <img src="data:image/png;base64,{bin_logo_iso31000}" style="height: 50px; width: auto;">
    
    #         </div>
    #     ''', unsafe_allow_html=True)
    # except:
    #     pass
                    
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
