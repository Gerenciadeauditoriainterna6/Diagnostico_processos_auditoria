import streamlit as st
import os
import time
from sqlalchemy import create_engine, text

# Conexão com o banco de dados
db_url = st.secrets["connections"]["url"]
engine = create_engine(db_url)

# --- CONFIGURAÇÃO DE CAMINHOS ---
caminho_script = os.path.dirname(os.path.abspath(__file__))
arquivo_excel = os.path.join(caminho_script, "AUDITORIA DE DIAGNÓSTICO FUSVE.xlsx")
logo_fusve = os.path.join(caminho_script, "logo_fusve.png")
logo_auditoria = os.path.join(caminho_script, "logo_auditoria.png")

# --- TABELA DE RISCO ---
MAPA_RISCO = {
    ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14, ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
    ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10, ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
    ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6, ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
    ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2, ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
}

# --- LÓGICA DE LIMPEZA (DEVE FICAR NO TOPO) ---
if 'deve_limpar' in st.session_state and st.session_state['deve_limpar']:
    campos_para_limpar = ["input_processo", "input_objetivo", "input_executor", 
                          "input_descricao", "input_etapa_ini", "input_etapa_fim", "input_produto"]
    for campo in campos_para_limpar:
        if campo in st.session_state: del st.session_state[campo]
    st.session_state['riscos'] = []
    st.session_state['deve_limpar'] = False
    st.rerun()

# --- FUNÇÕES AUXILIARES ---
def get_estilo_risco(score):
    if score >= 12: return "#FF4B4B", "🔴" 
    elif score >= 8: return "#FF9900", "🟠"    
    elif score >= 4: return "#FFD700", "🟡"   
    elif score >= 0: return "#00CC96", "🟢"   

def salvar_no_banco():
    try: 
        with engine.begin() as conn: # 'begin' inicia a transação automaticamente
            
            # 1. Salva o Processo e recupera o ID criado.
            sql_processo = text("""
                INSERT INTO processos (area, codigo_processo, nome_processo, objetivo, executor, descricao, etapa_ini, etapa_fim, produto)
                VALUES (:area, :cod, :nome, :obj, :exec, :desc, :e_ini, :e_fim, :prod)
                RETURNING id
            """)

            # Executa e pega o ID do processo recém-criado
            resultado = conn.execute(sql_processo, {
                "area": st.session_state.get("area"),
                "cod": "1.1",
                "nome": st.session_state.get("input_processo"),
                "obj": st.session_state.get("input_objetivo"),
                "exec": st.session_state.get("input_executor"),
                "desc": st.session_state.get("input_descricao"),
                "e_ini": st.session_state.get("input_etapa_ini"),
                "e_fim": st.session_state.get("input_etapa_fim"),
                "prod": st.session_state.get("input_produto")
            })
            processo_id = resultado.scalar()  # Pega o ID retornado

            # 2. Salva cada Risco vinculado ao ID do processo
            sql_risco = text("""
                INSERT INTO riscos (processo_id, nome_risco, fator_risco, melhoria, impacto, probabilidade, apetite_risco, motivo_risco)
                VALUES (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo)
            """)

            for i in range(len(st.session_state['riscos'])):
                conn.execute(sql_risco, {
                    "pid": processo_id,
                    "nome": st.session_state.get(f"nome_{i}"),
                    "fator": st.session_state.get(f"fator_{i}"),
                    "melhoria": st.session_state.get(f"melhoria_{i}"),
                    "imp": st.session_state.get(f"imp_{i}"),
                    "prob": st.session_state.get(f"prob_{i}"),
                    "apetite": st.session_state.get(f"apetite_{i}"),
                    "motivo": st.session_state.get(f"motivo_{i}")
                })

        return True
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")
        return False
   
# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Diagnóstico de Processos", layout="centered")

# Sidebar com logo verificada
if os.path.exists(logo_fusve): st.sidebar.image(logo_fusve, width=200)

st.markdown("<style>.stApp { background-color: #ffffff; }</style>", unsafe_allow_html=True)

# Centro com logo verificada
if os.path.exists(logo_auditoria):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2: st.image(logo_auditoria, width=300)

st.title("Diagnóstico de Processos - Auditoria Interna FUSVE")

if 'riscos' not in st.session_state: st.session_state['riscos'] = []
if 'errors' not in st.session_state: st.session_state['errors'] = {}

def mostrar_erro(key):
    if key in st.session_state['errors']: st.error(st.session_state['errors'][key])

# --- FORMULÁRIO ---
st.subheader("1. Dados do Processo")
area = st.selectbox("Área", ["Gerência de Gente e gestão - GGG", "Gerência de Finanças", "Gerência de Operações", "Gerência de Tecnologia", "Gerência de Marketing"], key="area")
st.text_area("Processo:", key="input_processo")
mostrar_erro("input_processo")
st.text_area("Objetivo:", key="input_objetivo")
mostrar_erro("input_objetivo")
st.text_area("Quem Executa?", key="input_executor")
mostrar_erro("input_executor")
st.text_area("Descrição:", key="input_descricao")
mostrar_erro("input_descricao")
st.text_area("Etapa Inicial:", key="input_etapa_ini")
mostrar_erro("input_etapa_ini")
st.text_area("Etapa Final:", key="input_etapa_fim")
mostrar_erro("input_etapa_fim")
st.text_area("Produto:", key="input_produto")
mostrar_erro("input_produto")

st.divider()

st.subheader("2. Riscos Associados")
for i, _ in enumerate(st.session_state['riscos']):
    st.markdown(f"**Risco {i+1}**")
    st.text_input(f"Nome do Risco:", key=f"nome_{i}")
    st.text_area(f"Fator de Risco:", key=f"fator_{i}")
    st.text_area(f"Melhoria:", key=f"melhoria_{i}")
    st.text_area(f"Apetite ao risco:", key=f"apetite_{i}")
    
    col_i, col_p = st.columns(2)
    with col_i: impacto = st.selectbox(f"Impacto:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"imp_{i}")
    with col_p: prob = st.selectbox(f"Probabilidade:", ["Muito Alto", "Alto", "Médio", "Baixo"], key=f"prob_{i}")
    
    risco_calc = MAPA_RISCO.get((impacto, prob), 0)
    cor, emoji = get_estilo_risco(risco_calc)
    
    st.markdown(f"""
        <div style="background-color: {cor}; padding: 10px; border-radius: 5px; text-align: center;">
            <h3 style="color: white; margin: 0;">{emoji} {risco_calc}</h3>
        </div>
    """, unsafe_allow_html=True)
    
    st.text_area(f"Motivo:", key=f"motivo_{i}")
    st.markdown("---")

# --- BOTÕES ---
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("➕ Adicionar Risco", use_container_width=True):
        st.session_state['riscos'].append({})
        st.rerun()

with col_btn2:
    if st.button("💾 Salvar Todos os Dados", type="primary", use_container_width=True):
        campos_fixos = ["input_processo", "input_objetivo", "input_executor", "input_descricao", "input_etapa_ini", "input_etapa_fim", "input_produto"]
        erro_encontrado = False
        for campo in campos_fixos:
            if not st.session_state.get(campo):
                st.session_state['errors'][campo] = "Campo obrigatório."
                erro_encontrado = True
        
        if not erro_encontrado:
            if salvar_no_excel(arquivo_excel):
                st.session_state['errors'] = {}
                st.session_state['deve_limpar'] = True
                st.rerun()