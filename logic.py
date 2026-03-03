import os
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import text
from database import engine

# --- CONFIGURAÇÕES E MAPEAMENTOS ---
# DICA: Tente usar caminhos relativos ao invés de C:\Users\... para evitar erros no servidor
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOGO = os.path.join(BASE_DIR, "assets", "logo_fusve.png")
CAMINHO_LOGO2 = os.path.join(BASE_DIR, "assets", "logo_auditoria.png")

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

# --- CLASSE DO PDF ---
class PDF(FPDF):
    def header(self):
        tamanho_logo = 25
        if os.path.exists(CAMINHO_LOGO):
            self.image(CAMINHO_LOGO, 15, 10, tamanho_logo)
        if os.path.exists(CAMINHO_LOGO2):
            self.image(CAMINHO_LOGO2, 15, 20, tamanho_logo)
        
        self.set_y(12)
        self.set_x(32)
        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, "RELATÓRIO DE VALIDAÇÃO DO PROCESSO", border=False, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(32)
        self.set_font('helvetica', "", 10)
        self.cell(0, 5, "Diagnóstico de Auditoria Interna - FUSVE", border=False, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(45)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_x(170)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

# --- FUNÇÕES AUXILIARES ---
def wrap_text_lines(pdf_obj, text, width):
    paragraphs = str(text).splitlines() or ['']
    out_lines = []
    for para in paragraphs:
        words = para.split()
        if not words:
            out_lines.append('')
            continue
        cur = ''
        for w in words:
            test = (cur + ' ' + w).strip()
            if pdf_obj.get_string_width(test) <= width:
                cur = test
            else:
                if cur: out_lines.append(cur)
                part = ''
                for ch in w:
                    if pdf_obj.get_string_width(part + ch) <= width:
                        part += ch
                    else:
                        if part: out_lines.append(part)
                        part = ch
                cur = part
        if cur: out_lines.append(cur)
    return out_lines

# --- LÓGICA DE BANCO DE DADOS ---
def obter_proximo_codigo(area_selecionada):
    prefixo = MAPPING_AREAS.get(area_selecionada)
    query = text("SELECT COUNT(*) FROM processos WHERE area = :area")
    with engine.connect() as conn:
        contagem = conn.execute(query, {"area": area_selecionada}).scalar() or 0
    return f"{prefixo}.{contagem + 1}"

def processar_codigo_inteligente():
    import streamlit as st
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
    else:
        st.session_state['codigo_processo'] = obter_proximo_codigo(area)

def salvar_no_banco():
    import streamlit as st
    try: 
        with engine.begin() as conn:
            area_val = st.session_state.get("area")
            nome_val = st.session_state.get("input_processo")
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
        import streamlit as st
        st.error(f"Erro ao salvar: {e}")
        return False

def buscar_dados_do_processo(id_proc):
    query = f"""
        SELECT 
            p.area AS "AREA", p.nome_processo AS "PROCESSO", p.objetivo AS "OBJETIVO",
            p.descricao AS "DESCRIÇÃO DO PROCESSO", p.executor AS "QUEM EXECUTA?",
            p.produto AS "PRODUTO DO PROCESSO", p.etapa_ini AS "ETAPA INICIAL",
            p.etapa_fim AS "ETAPA FINAL", r.nome_risco AS "RISCO",
            r.fator_risco AS "FATOR DE RISCO", r.melhoria AS "O QUE PODERIA MELHORAR?",
            r.impacto AS "IMPACTO", r.probabilidade AS "PROBABILIDADE",
            r.score_risco AS "RISCO BRUTO"
        FROM processos p
        JOIN riscos r ON p.id = r.processo_id
        WHERE p.id = {id_proc}
    """
    return pd.read_sql(query, engine)

def gerar_pdf_em_memoria(id_proc):
    df_processo = buscar_dados_do_processo(id_proc)
    if df_processo.empty: return None

    pdf = PDF()
    pdf.add_page()
    primeira_linha = df_processo.iloc[0]

    # Cabeçalho
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, f"ID DO PROCESSO: {id_proc}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.cell(0, 8, f"ÁREA: {primeira_linha['AREA']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Detalhes
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(30, 8, "PROCESSO:", border=False)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, str(primeira_linha['PROCESSO']), border=0, align="L")
    
    pdf.ln(2)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "OBJETIVO DO PROCESSO:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(0, 6, str(primeira_linha['OBJETIVO']))

    pdf.ln(2)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, "DESCRIÇÃO DETALHADA:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 9)
    pdf.multi_cell(0, 6, str(primeira_linha['DESCRIÇÃO DO PROCESSO']))
    
    pdf.ln(5)

    # Tabela Riscos
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font('helvetica', "B", 8)
    headers = ["Descrição do Risco", "Fator de Risco", "O que Melhorar?", "Imp.", "Prob.", "Risco Bruto"]
    widths = [50, 40, 40, 20, 20, 20]
    for h, w in zip(headers, widths):
        is_last = (h == "Risco Bruto")
        pdf.cell(w, 10, h, border=1, fill=True, align="C", new_x=XPos.LMARGIN if is_last else XPos.RIGHT, new_y=YPos.NEXT if is_last else None)
    
    pdf.set_font('helvetica', "", 8)
    for _, linha in df_processo.iterrows():
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        # Simplificação: use multi_cell para as colunas de texto para evitar erro de alinhamento
        # (Se o seu layout anterior era mais complexo, você pode manter seu loop original aqui)
        pdf.cell(50, 10, str(linha['RISCO']), border=1)
        pdf.cell(40, 10, str(linha['FATOR DE RISCO']), border=1)
        pdf.cell(40, 10, str(linha['O QUE PODERIA MELHORAR?']), border=1)
        pdf.cell(20, 10, str(linha['IMPACTO']), border=1, align="C")
        pdf.cell(20, 10, str(linha['PROBABILIDADE']), border=1, align="C")
        pdf.cell(20, 10, str(int(linha['RISCO BRUTO'])), border=1, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Assinaturas
    pdf.ln(20)
    y_assinatura = pdf.get_y() + 10
    pdf.line(20, y_assinatura, 90, y_assinatura)
    pdf.line(110, y_assinatura, 180, y_assinatura)
    pdf.set_y(y_assinatura + 2)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(90, 5, "Gerência", align="C")
    pdf.cell(90, 5, "Superintendência", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    return pdf.output(dest='S')

def buscar_processos_pendentes():
    # Ajuste o SELECT conforme sua necessidade para buscar processos pendentes
    query = "SELECT id, area, nome_processo FROM processos" 
    return pd.read_sql(query, engine)