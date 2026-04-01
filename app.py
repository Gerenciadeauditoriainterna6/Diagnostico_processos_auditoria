import streamlit as st
import os
import pandas as pd
from datetime import datetime
from streamlit_local_storage import LocalStorage

from logic import (gerar_pdf_em_memoria,buscar_processos_pendentes)

from modules.execucao.areas import tela_cadastro_area, carregar_areas_banco
from modules.execucao.visao_geral import tela_visao_geral_processos
from modules.planejamento.plano_anual import tela_plano_anual
from modules.execucao.auditorias import (tela_auditorias_trimestrais, tela_detalhe_auditoria, tela_detalhe_processo_auditoria)
from modules.auth.login import login_screen, verificar_sessao
from modules.comunicacaoresultados.relatorios import marcar_relatorio_gerado
from modules.execucao.processos import tela_diagnostico_processos
from modules.shared.theme import apply_theme


MAPA_RISCO = {
    ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14, ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
    ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10, ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
    ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6, ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
    ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2, ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
}

TEMPO_SESSAO_SEGUNDOS = 1800

local_storage = LocalStorage()

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="SISTEMA GERÊNCIA DE AUDITORIA INTERNA - FUSVE", layout="centered")
# --- Script que remove o localstorage sempre que a aba do navegador se fecha, impossibilitando vazamento de segurança ---
st.markdown(
    """
    <script>
        window.addEventListener('beforeunload', function() {
        localStorage.removeItem('usuario_audit');
        });
        </script>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE ESTADO ---
areas_dict = carregar_areas_banco()

if 'riscos' not in st.session_state: st.session_state['riscos'] = []
if 'deve_limpar' not in st.session_state: st.session_state['deve_limpar'] = False
if 'df_pendentes' not in st.session_state: st.session_state['df_pendentes'] = pd.DataFrame()
if 'codigo_processo_display' not in st.session_state: st.session_state['codigo_processo_display'] = "" 
if 'id_area_selecionado' not in st.session_state and areas_dict:
    primeiro_nome = list(areas_dict.keys())[0]
    st.session_state['id_area_selecionado'] = areas_dict[primeiro_nome]


# --- 5. Execução do app ---

def main():
     # --- LER DO LOCALSTORAGE UMA VEZ ---
    import json
    session_data_str = local_storage.getItem("session_data")
    usuario_cache = None
    login_timestamp_cache = None
    if session_data_str and session_data_str not in ["undefined", "null", "None"]:
        try:
            data = json.loads(session_data_str)
            usuario_cache = data.get("usuario")
            ts_str = data.get("timestamp")
            if ts_str:
                login_timestamp_cache = datetime.fromisoformat(ts_str)
        except Exception:
            pass

    # --- VERIFICAR EXPIRAÇÃO DA SESSÃO ---
    if not verificar_sessao(local_storage=local_storage, login_timestamp_cache=login_timestamp_cache):
        # Mostrar tela de sessão expirada
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h2>⏰ Sua sessão expirou</h2>
            <p>Por questões de segurança, sua sessão foi encerrada após 30 minutos de inatividade.</p>
            <p>Clique no botão abaixo para fazer login novamente.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔐 Fazer Login Novamente", type="primary", use_container_width=True, key='btn_fazer_login_novamente'):
            st.session_state.pop("sessao_expirada", None)
            st.rerun()
        
        st.stop()
    
    # --- REAUTENTICAÇÃO ---
    if not st.session_state.get('autenticado'):
        if usuario_cache and usuario_cache not in ["undefined", "null", "None"]:
            if login_timestamp_cache:
                if (datetime.now() - login_timestamp_cache).total_seconds() <= TEMPO_SESSAO_SEGUNDOS:
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_logado'] = usuario_cache
                    st.session_state['login_timestamp'] = login_timestamp_cache
                else:
                    # expirado, limpa localStorage
                    try:
                        local_storage.deleteItem("session_data")
                    except:
                        local_storage.setItem("session_data", "null")
            else:
                # não tem timestamp, limpa cache
                try:
                    local_storage.deleteItem("session_data")
                except:
                    local_storage.setItem("session_data", "null")

    # --- BLOQUEIO DE ACESSO ---
    if not st.session_state.get('autenticado'):
        login_screen(local_storage)
        st.stop()

    # --- SE CHEGOU AQUI, USUÁRIO ESTÁ AUTENTICADO ---
    if st.session_state.get('autenticado'):
        st.session_state['login_timestamp'] = datetime.now()
    
    # ==== APLICAR TEMA GLOBAL ====
    # Executado depois do login para não interferir na tela de login
    apply_theme()
    
    # ==== REDIRECIONAMENTO PARA EDIÇÃO DE PROCESSO ====
    # Se veio da auditoria para editar um processo
    if st.session_state.get('processo_para_editar') and st.session_state.get('opcao_menu'):
        # Forçar a opção do menu para Diagnóstico dos processos
        opcao = st.session_state['opcao_menu']
        # Limpar após usar
        # Não limpar ainda, vamos usar depois
    else:
        # Menu normal do sidebar

        # --- SIDEBAR ---
        with st.sidebar:
            # CSS para controlar a largura do sidebar
            st.markdown("""
                <style>
                        /* Ajsta a largura do sidebar */
                        [data-testid="stSidebar"] {{
                            min-width: 250px;
                            max-width: 350px;
                            width: 20vw !important;
                        }}

                        /* Ajusta o conteúdo do sidebar para se adaptar */
                        [data-testid="stSidebar"] .sidebar-content {{
                            width: 100%;
                        }}
                </style>
            """, unsafe_allow_html=True)

            caminho_script = os.path.dirname(os.path.abspath(__file__))
            logo_auditoria_path = os.path.join('assets', 'logo_auditoria.png')

            # CSS para centralizar a imagem usando HTML direto
            st.markdown("""
            <style>
                /* Reduz a altura do header do sidebar */
                [data-testid="stSidebarHeader"] {
                    height: 20px !important;
                    min-height: 20px !important;
                    padding: 0 !important;
                    margin: 0 !important;
                }
                
                /* Ajusta o botão de recolher */
                [data-testid="stSidebarHeader"] button {
                    padding: 0 !important;
                    margin: 0 !important;
                    margin-top: 25px !important;  /* ← controla a posição do botão */
                    height: 10px !important;
                }
                    
                /* Ícone do botão recolher (sidebar expandido) */
                [data-testid="stSidebarHeader"] button svg {
                    fill: #e4e4e4 !important;
                    stroke: #e4e4e4 !important;
                }
                
                /* Ícone do botão recolher (sidebar recolhido) */
                button[kind="icon"] svg {
                    fill: #e4e4e4 !important;
                    stroke: #e4e4e4 !important;
                }
                
                /* Ícone do controle recolhido */
                [data-testid="collapsedControl"] svg {
                    fill: #e4e4e4 !important;
                    stroke: #e4e4e4 !important;
                }
                    
                /* Container da imagem no sidebar */
                .sidebar-logo-container {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    width: 100%;
                    margin-bottom: 1rem;
                    margin-top: 8px;  /* ← espaço acima da imagem */
                }
                .sidebar-logo-container img {
                    max-width: 200px;
                    width: 100%;
                    height: auto;
                    transform: translateY(-20px);  /* ← move a imagem para cima */
                }
                        
                /* ... seu CSS existente ... */
        
                /* Ícone do botão quando o sidebar está recolhido */
                span[data-testid="stIconMaterial"] {
                    color: #e4e4e4 !important;
                }
                
                /* Classe específica do ícone */
                .st-emotion-cache-1g48ntn {
                    color: #e4e4e4 !important;
                }
                
                /* Para garantir em qualquer estado */
                span[data-testid="stIconMaterial"] svg,
                span[data-testid="stIconMaterial"] {
                    color: #e4e4e4 !important;
                    fill: #e4e4e4 !important;
                }
            </style>
        """, unsafe_allow_html=True)
            
            if os.path.exists(logo_auditoria_path):
                # Usa HTML direto em vez de st.image
                with open(logo_auditoria_path, "rb") as f:
                    import base64
                    img_data = base64.b64encode(f.read()).decode()
                
                st.markdown(f'''
                    <div class="sidebar-logo-container">
                        <img src="data:image/png;base64,{img_data}">
                    </div>
                ''', unsafe_allow_html=True)
            else:
                st.image(logo_auditoria_path, width=200)  # fallback

            # Exibe o nome do usuário logado para confirmação
            st.markdown(f"👤 **Usuário:** {st.session_state.get('usuario_logado', 'Audit')}")

            
            opcao = st.radio(
                "Menu", 
                    [
                        "📅 Plano Anual de Auditoria",
                        "🏢 Cadastro de Áreas e Funcionários",
                        "🔍 Diagnóstico dos Processos",
                        "📋 Detalhamento dos Processos",        
                        "👁️ Visão Geral do Diagnóstico"
                        #"✅ Checklists de Eficácia",           
                        #"📊 Resultados e Pareceres",
                        #"📄 Geração de Relatórios"           
                    ]
                )

            st.divider()

            if st.session_state.get('autenticado'):
                login_time = st.session_state.get("login_timestamp")
                if login_time:
                    tempo_decorrido = (datetime.now() - login_time).total_seconds()
                    if tempo_decorrido > TEMPO_SESSAO_SEGUNDOS:
                        st.error("⚠️ SESSÃO EXPIRADA")
                
            if st.sidebar.button("Sair (Logout)", use_container_width=True, key='btn_logout'):
                # 1. Remove a informação do navegador
                try:
                    local_storage.deleteItem("session_data")
                except:
                    local_storage.setItem('session_data', 'null')
                
                # 2. Em vez de .clear(), limpamos apenas o que interessa
                # Isso evita o KeyError nos widgets (selectbox, etc)
                st.session_state["autenticado"] = False
                st.session_state["usuario_logado"] = None
                
                # 3. Força o recarregamento
                st.rerun()

            #if st.session_state.get('autenticado'):
                #st.markdown(f"<small>⏳ Tempo até o término da sessão: {tempo_restante_sessao()}</small>", unsafe_allow_html=True)
            
            # Botão para renovar sessão
            if st.button("🔄 Renovar Sessão", key='btn_renew', use_container_width=True):
                st.session_state["login_timestamp"] = datetime.now()
            
                session_data = {
                    "usuario": st.session_state.get("usuario_logado"),
                    "timestamp": datetime.now().isoformat()
                }
                local_storage.setItem("session_data", json.dumps(session_data))
                st.toast("Sessão renovada por mais 30 minutos!", icon="🔄")
                # Não chame st.rerun() aqui - deixa o rerun natural do Streamlit
        

    # --- LÓGICA PRINCIPAL ---
    if opcao == "🔍 Diagnóstico dos Processos":
       tela_diagnostico_processos()

    elif opcao == "🏢 Cadastro de Áreas e Funcionários":
        tela_cadastro_area()

    elif opcao == "👁️ Visão Geral do Diagnóstico":
        tela_visao_geral_processos()

    elif opcao == "Geração de Relatórios":
        st.title("Relatórios - FUSVE")
        
        if st.button("Atualizar Lista de Processos", key='btn_atualizar_lista_de_processos'):
            st.session_state['df_pendentes'] = buscar_processos_pendentes()
        
        if not st.session_state['df_pendentes'].empty:
            df = st.session_state['df_pendentes']
            st.dataframe(df)
            
            codigo_selecionado = st.selectbox(
                "Selecione o Código do Processo:", 
                df['codigo_processo'].tolist(),
                on_change=lambda: st.session_state.pop('pdf_pronto', None)
            )

            if st.button("Gerar e Marcar como Pronto", key='btn_gerar_e_marcar_pronto'):
                marcar_relatorio_gerado(codigo_selecionado)
                pdf_bytes = gerar_pdf_em_memoria(codigo_selecionado)
                
                if pdf_bytes:
                    st.session_state['pdf_pronto'] = bytes(pdf_bytes)
                    st.success(f"Processo {codigo_selecionado} concluído! Clique em baixar.")
                    st.rerun() 
                else:
                    st.error("Erro ao gerar PDF.")
            
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
        
        tela_plano_anual()

    elif opcao == "📋 Detalhamento dos Processos":
        if 'processo_detalhe' in st.session_state:
            tela_detalhe_processo_auditoria()
        elif 'auditoria_selecionada' in st.session_state:
            tela_detalhe_auditoria()
        else:
            tela_auditorias_trimestrais()


# --- DISPARADOR FINAL ---

if __name__ == "__main__":
    main()