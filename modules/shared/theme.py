"""
Tema global do aplicativo
Paleta de cores personalizada
"""
import streamlit as st

# ========== CORES PRINCIPAIS ==========
PRIMARY_COLOR = "#1848d8"      # Azul principal (botões, destaques)
SECONDARY_COLOR = "#18606c"    # Azul petróleo (hover, elementos secundários)
ACCENT_COLOR = "#241824"        # Roxo escuro (alertas, destaques especiais)

# ========== CORES DE FUNDO ==========
BACKGROUND_COLOR = "#ffffff"    # Cinza claro (fundo da página)
CARD_BACKGROUND = "#e3e3e3"     # Branco (fundos de cards)
SIDEBAR_BACKGROUND = "#184145"  # Verde azulado escuro (sidebar)

# ========== CORES DE TEXTO ==========
TEXT_COLOR = "#182418"          # Verde muito escuro (texto principal)
TEXT_MUTED = "#48606c"          # Azul acinzentado (texto secundário)
TEXT_LIGHT = "#ffffff"          # Branco (texto sobre fundo escuro)
SIDEBAR_TEXT_COLOR = "#e4e4e4"  # Cinza claro (texto no sidebar)

# ========== CORES DE STATUS ==========
SUCCESS_COLOR = "#18606c"       # Azul petróleo (sucesso)
WARNING_COLOR = "#607878"       # Cinza azulado (alerta)
DANGER_COLOR = "#241824"        # Roxo escuro (erro)
INFO_COLOR = "#486c78"          # Azul claro (informação)

# ========== CORES PARA HOVER E INTERAÇÕES ==========
HOVER_COLOR = "#486c78"         # Azul claro (hover em botões)
ACTIVE_COLOR = "#1848d8"        # Azul principal (ativo)
SIDEBAR_HOVER_COLOR = "#607878" # Cinza azulado (hover no sidebar)

# ========== ESPAÇAMENTOS ==========
SPACING_SMALL = "0.5rem"
SPACING_MEDIUM = "1rem"
SPACING_LARGE = "1.5rem"

# ========== BORDAS ==========
BORDER_RADIUS = "0.5rem"
BORDER_RADIUS_CARD = "1rem"
BORDER_COLOR = "#607878"        # Cinza azulado para bordas

# ========== SOMBRAS ==========
SHADOW_SMALL = "0 1px 3px rgba(0,0,0,0.12)"
SHADOW_MEDIUM = "0 4px 6px rgba(0,0,0,0.1)"
SHADOW_LARGE = "0 10px 15px -3px rgba(0,0,0,0.1)"

# ========== TIPOGRAFIA ==========
FONT_FAMILY = "'Segoe UI', 'Helvetica Neue', sans-serif"
FONT_SIZE_BASE = "16px"
FONT_SIZE_SMALL = "14px"
FONT_SIZE_LARGE = "18px"


def get_theme_css():
    """Retorna o CSS do tema global com a nova paleta"""
    return f"""
        <style>
            /* ========== VARIÁVEIS GLOBAIS ========== */
            :root {{
                --primary: {PRIMARY_COLOR};
                --secondary: {SECONDARY_COLOR};
                --accent: {ACCENT_COLOR};
                --success: {SUCCESS_COLOR};
                --warning: {WARNING_COLOR};
                --danger: {DANGER_COLOR};
                --info: {INFO_COLOR};
                --background: {BACKGROUND_COLOR};
                --card-bg: {CARD_BACKGROUND};
                --sidebar-bg: {SIDEBAR_BACKGROUND};
                --text: {TEXT_COLOR};
                --text-muted: {TEXT_MUTED};
                --text-light: {TEXT_LIGHT};
                --sidebar-text: {SIDEBAR_TEXT_COLOR};
                --border-color: {BORDER_COLOR};
                --hover-color: {HOVER_COLOR};
                --active-color: {ACTIVE_COLOR};
                --sidebar-hover: {SIDEBAR_HOVER_COLOR};
                --border-radius: {BORDER_RADIUS};
                --border-radius-card: {BORDER_RADIUS_CARD};
                --shadow-sm: {SHADOW_SMALL};
                --shadow-md: {SHADOW_MEDIUM};
                --shadow-lg: {SHADOW_LARGE};
                --font-family: {FONT_FAMILY};
            }}
            
            /* ========== ESTILOS GLOBAIS ========== */
            .stApp {{
                background-color: var(--background);
                font-family: var(--font-family);
            }}
            
            /* ========== CABEÇALHO ========== */
            header {{
                background-color: var(--sidebar-bg) !important;
                padding: 0 !important;
                height: 60px !important;
            }}

            /* Ícone do menu hambúrguer */
            header button {{
                color: var(--sidebar-text) !important;
            }}

            /* Título do app no header (se houver) */
            header .stMarkdown {{
                color: var(--sidebar-text) !important;
            }}

            /* Se quiser remover completamente o header */
            /* header {{ display: none !important; }} */
            
            /* ========== SIDEBAR ========== */
            [data-testid="stSidebar"] {{
                background-color: var(--sidebar-bg);
                border-right: 1px solid var(--border-color);
            }}
            
            /* Texto padrão do sidebar */
            [data-testid="stSidebar"] {{
                color: var(--sidebar-text) !important;
            }}
            
            /* Todos os textos dentro do sidebar */
            [data-testid="stSidebar"] *,
            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stRadio label,
            [data-testid="stSidebar"] .stSelectbox label,
            [data-testid="stSidebar"] .stTextInput label,
            [data-testid="stSidebar"] .stNumberInput label {{
                color: var(--sidebar-text) !important;
            }}
            
            /* Títulos dentro do sidebar */
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] h5,
            [data-testid="stSidebar"] h6 {{
                color: var(--sidebar-text) !important;
                border-bottom-color: rgba(228, 228, 228, 0.2);
            }}
            
            /* Links dentro do sidebar */
            [data-testid="stSidebar"] a {{
                color: var(--sidebar-text) !important;
            }}
            
            [data-testid="stSidebar"] a:hover {{
                color: var(--sidebar-hover) !important;
            }}
            
            /* Botões dentro do sidebar */
            [data-testid="stSidebar"] .stButton button {{
                background-color: rgba(228, 228, 228, 0.2) !important;
                color: var(--sidebar-text) !important;
                border: 1px solid var(--sidebar-text) !important;
            }}
            
            [data-testid="stSidebar"] .stButton button:hover {{
                background-color: rgba(228, 228, 228, 0.3) !important;
            }}
            
            /* Inputs dentro do sidebar */
            [data-testid="stSidebar"] .stTextInput input,
            [data-testid="stSidebar"] .stSelectbox select,
            [data-testid="stSidebar"] .stTextArea textarea {{
                background-color: rgba(228, 228, 228, 0.1) !important;
                color: var(--sidebar-text) !important;
                border-color: var(--sidebar-text) !important;
            }}
            
            /* Divider dentro do sidebar */
            [data-testid="stSidebar"] hr {{
                border-color: rgba(228, 228, 228, 0.3) !important;
            }}
            
            /* Expander dentro do sidebar */
            [data-testid="stSidebar"] .streamlit-expanderHeader {{
                background-color: rgba(228, 228, 228, 0.05) !important;
                color: var(--sidebar-text) !important;
            }}
            
            [data-testid="stSidebar"] .streamlit-expanderHeader:hover {{
                background-color: rgba(228, 228, 228, 0.1) !important;
            }}
            
            /* Radio buttons dentro do sidebar */
            [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {{
                color: var(--sidebar-text) !important;
            }}
            
            /* ========== CONTAINERS PERSONALIZADOS ========== */
            /* Container padrão */
            .custom-container {{
                background-color: var(--card-bg);
                border-radius: var(--border-radius-card);
                box-shadow: var(--shadow-md);
                padding: 20px;
                margin-bottom: 20px;
                border: 1px solid var(--border-color);
            }}

            /* Container primário (destaque) */
            .custom-container-primary {{
                background-color: #e8f0fe;
                border-radius: var(--border-radius-card);
                box-shadow: var(--shadow-md);
                padding: 20px;
                margin-bottom: 20px;
                border: 2px solid var(--primary);
            }}

            /* Container de perigo/erro */
            .custom-container-danger {{
                background-color: #fee8e8;
                border-radius: var(--border-radius-card);
                box-shadow: var(--shadow-md);
                padding: 20px;
                margin-bottom: 20px;
                border: 2px solid var(--danger);
            }}

            /* Título do container */
            .custom-container-title {{
                font-size: 16px;
                font-weight: 600;
                color: var(--primary);
                margin-bottom: 15px;
                padding-bottom: 8px;
                border-bottom: 2px solid var(--border-color);
            }}

            /* Campos dentro do container */
            .custom-container div[data-testid="stTextArea"] textarea,
            .custom-container div[data-testid="stTextInput"] input,
            .custom-container-primary div[data-testid="stTextArea"] textarea,
            .custom-container-primary div[data-testid="stTextInput"] input {{
                background-color: #ffffff !important;
                border: 1px solid #ced4da !important;
                border-radius: 8px !important;
            }}
            
            /* ========== BOTÕES ========== */
            .stButton button {{
                border-radius: var(--border-radius);
                font-weight: 500;
                transition: all 0.2s ease;
                background-color: var(--primary);
                color: var(--text-light);
                border: none;
            }}
            
            .stButton button:hover {{
                background-color: var(--hover-color);
                transform: translateY(-1px);
                box-shadow: var(--shadow-sm);
            }}
            
            .stButton button:active {{
                transform: translateY(0);
            }}
            
            button[kind="secondary"] {{
                background-color: var(--background) !important;
                color: var(--primary) !important;
                border: 1px solid var(--primary) !important;
            }}
            
            button[kind="secondary"]:hover {{
                background-color: rgba(24, 72, 216, 0.1) !important;
            }}
            
            /* ========== INPUTS ========== */
            .stTextInput input, .stTextArea textarea, .stSelectbox select {{
                border-radius: var(--border-radius);
                border: 1px solid var(--border-color);
                transition: all 0.2s ease;
                background-color: var(--card-bg);
                color: var(--text);
            }}
            
            .stTextInput input:focus, .stTextArea textarea:focus {{
                border-color: var(--primary);
                box-shadow: 0 0 0 3px rgba(24, 72, 216, 0.1);
                outline: none;
            }}
            
            /* ========== EXPANDERS ========== */
            .streamlit-expanderHeader {{
                background-color: rgba(24, 72, 216, 0.05);
                border-radius: var(--border-radius);
                font-weight: 500;
                color: var(--primary);
            }}
            
            .streamlit-expanderHeader:hover {{
                background-color: rgba(24, 72, 216, 0.1);
            }}
            
            /* ========== TABELAS (DataFrame) ========== */
            .stDataFrame {{
                border-radius: var(--border-radius);
                overflow: hidden;
            }}
            
            .stDataFrame table {{
                font-size: {FONT_SIZE_SMALL};
            }}
            
            .stDataFrame th {{
                background-color: var(--primary);
                color: var(--text-light);
                font-weight: 500;
            }}
            
            .stDataFrame td {{
                color: var(--text);
            }}
            
            /* ========== MÉTRICAS ========== */
            [data-testid="stMetricValue"] {{
                font-size: 1.8rem !important;
                font-weight: 600 !important;
                color: var(--primary);
            }}
            
            [data-testid="stMetricLabel"] {{
                font-size: {FONT_SIZE_SMALL} !important;
                color: var(--text-muted);
            }}
            
            /* ========== TABS ========== */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 0px;
                border-bottom: 2px solid var(--border-color);
            }}
            
            .stTabs [data-baseweb="tab"] {{
                padding: {SPACING_SMALL} {SPACING_MEDIUM};
                font-weight: 500;
                color: var(--text-muted);
            }}
            
            .stTabs [aria-selected="true"] {{
                color: var(--primary);
                border-bottom: 2px solid var(--primary);
            }}
            
            /* ========== TÍTULOS ========== */
            h1, h2, h3, h4, h5, h6 {{
                color: var(--primary);
                font-weight: 600;
                font-family: 'helvetica' !important;
                text-transform: uppercase !important; /* Linha para transformar todos os títulos em maísculos */
            }}
            
            /* ========== LINKS ========== */
            a {{
                color: var(--primary);
                text-decoration: none;
            }}
            
            a:hover {{
                color: var(--hover-color);
                text-decoration: underline;
            }}
            
            /* ========== DIVISORES ========== */
            hr {{
                margin: {SPACING_MEDIUM} 0;
                border-color: var(--border-color);
            }}
            
            /* ========== MENSAGENS ========== */
            .stAlert {{
                border-radius: var(--border-radius);
            }}
            
            .stAlert.success {{
                background-color: rgba(24, 96, 108, 0.1);
                border-left-color: var(--success);
            }}
            
            .stAlert.warning {{
                background-color: rgba(96, 120, 120, 0.1);
                border-left-color: var(--warning);
            }}
            
            .stAlert.error {{
                background-color: rgba(36, 24, 36, 0.1);
                border-left-color: var(--danger);
            }}
            
            /* ========== BOTÕES DE DOWNLOAD ========== */
            .stDownloadButton button {{
                background-color: var(--success) !important;
                color: var(--text-light) !important;
            }}
            
            .stDownloadButton button:hover {{
                background-color: var(--hover-color) !important;
            }}
            
            /* ========== MARCADORES DE RISCO ========== */
            .risk-high {{
                background-color: var(--danger);
                color: var(--text-light);
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
            }}
            
            .risk-medium {{
                background-color: var(--warning);
                color: var(--text);
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
            }}
            
            .risk-low {{
                background-color: var(--success);
                color: var(--text-light);
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
            }}
            
            /* ========== RESPONSIVIDADE ========== */
            @media (max-width: 768px) {{
                [data-testid="stMetricValue"] {{
                    font-size: 1.4rem !important;
                }}
                .stTabs [data-baseweb="tab"] {{
                    padding: 0.25rem 0.5rem;
                    font-size: 0.85rem;
                }}
                div[data-testid="stVerticalBlockBorder"] {{
                    padding: {SPACING_MEDIUM};
                }}
            }}
            
            /* ========== SCROLLBAR PERSONALIZADA ========== */
            ::-webkit-scrollbar {{
                width: 8px;
                height: 8px;
            }}
            
            ::-webkit-scrollbar-track {{
                background: var(--background);
                border-radius: 4px;
            }}
            
            ::-webkit-scrollbar-thumb {{
                background: var(--primary);
                border-radius: 4px;
            }}
            
            ::-webkit-scrollbar-thumb:hover {{
                background: var(--hover-color);
            }}
        </style>
    """


def apply_theme():
    """Aplica o tema global no app"""
    st.markdown(get_theme_css(), unsafe_allow_html=True)

def set_page_width(width_percent: int=90):
    """Define a largura máxima do container principal"""
    st.markdown(f"""
        <style>
            .block-container {{
                max-width: {width_percent}% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }}
        </style>
    """, unsafe_allow_html=True)