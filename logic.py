import streamlit as st
from sqlalchemy import text
from database import engine

MAPPING_AREAS = {
    "Gerência de Gente e gestão - GGG": 1,
    "Gerência de Finanças": 2,
    "Gerência de TI": 3,
}

MAPA_RISCO = {
    ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14, ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
    ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10, ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
    ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6, ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
    ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2, ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
}

def obter_proximo_codigo(area_selecionada):
    prefixo = MAPPING_AREAS.get(area_selecionada)
    query = text("SELECT COUNT(*) FROM processos WHERE area = :area")
    with engine.connect() as conn:
        contagem = conn.execute(query, {"area": area_selecionada}).scalar() or 0
    return f"{prefixo}.{contagem + 1}"

def processar_codigo_inteligente():
    area = st.session_state.get("area")
    nome = st.session_state.get("input_processo")
    if not area or not nome:
        st.session_state['codigo_processo'] = ""
        return
    query = text("SELECT codigo_processo FROM processos WHERE area = :area AND nome_processo = :nome")
    with engine.connect() as conn:
        resultado = conn.execute(query, {"area": area, "nome": nome}).fetchone()
    if resultado:
        st.session_state['codigo_processo'] = resultado[0]
        st.toast(f"Processo já existe! Código carregado: {resultado[0]}", icon="✅")
    else:
        st.session_state['codigo_processo'] = obter_proximo_codigo(area)

def get_estilo_risco(score):
    if score >= 12: return "#FF4B4B", "🔴" 
    elif score >= 8: return "#FF9900", "🟠"    
    elif score >= 4: return "#FFD700", "🟡"   
    elif score >= 0: return "#00CC96", "🟢" 

def salvar_no_banco():
    try: 
        with engine.begin() as conn:
            area_val = st.session_state.get("area")
            nome_val = st.session_state.get("input_processo")
            
            # Buscar ou criar processo
            query_busca = text("SELECT id FROM processos WHERE area = :area AND nome_processo = :nome")
            processo_existente = conn.execute(query_busca, {"area": area_val, "nome": nome_val}).fetchone()
            
            if processo_existente:
                processo_id = processo_existente[0]
            else:
                sql_p = text("""INSERT INTO processos (area, codigo_processo, nome_processo, objetivo, executor, descricao, etapa_ini, etapa_fim, produto) 
                                VALUES (:a, :c, :n, :o, :ex, :d, :ei, :ef, :p) RETURNING id""")
                processo_id = conn.execute(sql_p, {
                    "a": area_val, "c": st.session_state['codigo_processo'], "n": nome_val, "o": st.session_state['input_objetivo'], 
                    "ex": st.session_state['input_executor'], "d": st.session_state['input_descricao'], "ei": st.session_state['input_etapa_ini'], 
                    "ef": st.session_state['input_etapa_fim'], "p": st.session_state['input_produto']
                }).scalar()

            # Salvar Riscos
            sql_risco = text("""INSERT INTO riscos (processo_id, nome_risco, fator_risco, melhoria, impacto, probabilidade, apetite_risco, motivo_risco, score_risco) 
                                VALUES (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo, :score)""")
            for i in range(len(st.session_state['riscos'])):
                imp, prob = st.session_state.get(f"imp_{i}"), st.session_state.get(f"prob_{i}")
                score = MAPA_RISCO.get((imp, prob), 0)
                conn.execute(sql_risco, {
                    "pid": processo_id, "nome": st.session_state.get(f"nome_{i}"), "fator": st.session_state.get(f"fator_{i}"), 
                    "melhoria": st.session_state.get(f"melhoria_{i}"), "imp": imp, "prob": prob, 
                    "apetite": st.session_state.get(f"apetite_{i}"), "motivo": st.session_state.get(f"motivo_{i}"), "score": score
                })
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False