"""
Módulo do Plano Anual de Auditoria
"""
import streamlit as st
import os
from streamlit_pdf_viewer import pdf_viewer


def tela_plano_anual():
    """Exibe o Plano Anual de Auditoria em PDF"""
    
    # CORREÇÃO: usar st.markdown com HTML ou st.title simples
    st.markdown('<h1><i class="fas fa-calendar-alt"></i> 🗓️ Plano Anual de Auditoria - 2026</h1>', unsafe_allow_html=True)
    
    st.markdown("""
        <style>
            .block-container {
                max-width: 95% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            
            /* Remove qualquer padding lateral que possa estar limitando */
            .stApp {
                padding: 0 !important;
            }
            
            /* Força o PDF a ocupar toda a largura */
            iframe, .stElement, .stMarkdown {
                width: 100% !important;
            }
            
            /* Container do PDF */
            .stElement iframe {
                width: 100% !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.write("Visualize abaixo as diretrizes e o cronograma para o ano atual.")

    # Caminho para o arquivo PDF
    caminho_pdf = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "plano_auditoria_2026.pdf")

    if os.path.exists(caminho_pdf):
        try:
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
                use_container_width=False
            )
    else:
        st.warning("⚠️ Arquivo não encontrado na pasta assets.")
        st.write(f"Caminho procurado: {caminho_pdf}")