"""
Módulo do Plano Anual de Auditoria
"""
import streamlit as st
import os
from streamlit_pdf_viewer import pdf_viewer


def tela_plano_anual():
    """Exibe o Plano Anual de Auditoria em PDF"""
    
    st.markdown("""
        <style>
            .main .block-container {
                max-width: 98vw !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .stMarkdown, .stTitle, .stText {
                width: 100% !important;
                text-align: left !important;
            }
            #pdfViewer, .scrolling-container {
                width: 95vw !important;
                max-width: 95vw !important;
                margin-left: 0 !important;
            }
            iframe {
                width: 100% !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("📊 Plano Anual de Auditoria - 2026")
    st.write("Visualize abaixo as diretrizes e o cronograma para o ano atual.")

    # Caminho para o arquivo PDF (ajustado para funcionar a partir do módulo)
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
                use_container_width=True
            )
    else:
        st.warning("⚠️ Arquivo não encontrado na pasta assets.")
        st.write(f"Caminho procurado: {caminho_pdf}")