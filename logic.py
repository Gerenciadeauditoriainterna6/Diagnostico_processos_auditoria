import os
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import text
from database import engine
from datetime import datetime

# --- CONFIGURAÇÕES ---
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
        y_posicao = 10
        altura_fixa = 12 # Altura em mm

        # Logo FUSVE (Esquerda - Fixo em 10mm)
        if os.path.exists(CAMINHO_LOGO):
            self.image(CAMINHO_LOGO, 10, y_posicao, h=altura_fixa)
            
        # Logo Auditoria (Direita - Cálculo Automático)
        if os.path.exists(CAMINHO_LOGO2):
            # Para descobrir a largura, o FPDF permite calcular ou estimar.
            # Se você quer a logo à direita, force o X para um valor alto,
            # mas vamos garantir que ele não corte:
            
            largura_logo_auditoria = 40 # Defina o tamanho que você deseja para ela
            posicao_x_direita = 210 - 30 # - largura_logo_auditoria
            
            self.image(CAMINHO_LOGO2, posicao_x_direita, y_posicao, w=largura_logo_auditoria, h=altura_fixa)

        # Textos Centralizados
        self.set_y(12)
        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, "RELATÓRIO DE VALIDAÇÃO DO PROCESSO", border=False, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font('helvetica', "", 10)
        self.cell(0, 5, "Diagnóstico de Auditoria Interna - FUSVE", border=False, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Linha e espaçamento
        self.set_y(45)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_x(170)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

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

def buscar_processos_pendentes():
    # O "IS NULL" garante que os processos antigos entrem na lista.
    # O "!= 'Sim'" garante que só apareça o que não foi finalizado.
    query = text("""
        SELECT DISTINCT p.id, p.codigo_processo, p.area, p.nome_processo 
        FROM processos p
        JOIN riscos r ON p.id = r.processo_id
        WHERE r.relatorio_gerado != 'Sim' OR r.relatorio_gerado IS NULL
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def buscar_dados_do_processo(codigo_processo):
    # Alteramos a query para filtrar por codigo_processo
    query = text("""
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
        WHERE p.codigo_processo = :codigo
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"codigo": codigo_processo})

def draw_table_header(pdf, headers, widths):
    pdf.set_fill_color(200, 220, 255) # Cor de fundo azul claro
    pdf.set_font('helvetica', "B", 6)
    
    line_h = 5
    padding = 1
    
    # 1. Pré-processa os cabeçalhos (quebra as linhas se necessário)
    wrapped_headers = [wrap_text_lines(pdf, h, w - 2*padding) for h, w in zip(headers, widths)]
    
    # 2. Calcula a altura necessária para o cabeçalho (baseado na linha mais longa)
    max_lines = max(len(col) for col in wrapped_headers)
    header_height = max_lines * line_h + 2 # + 2 de respiro
    
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    
    # 3. Desenha cada célula do cabeçalho
    for i, (lines, w) in enumerate(zip(wrapped_headers, widths)):
        x_col = x_start + sum(widths[:i])
        
        # Desenha o fundo e a borda
        pdf.rect(x_col, y_start, w, header_height, style='F') # 'F' preenche
        pdf.rect(x_col, y_start, w, header_height)            # Desenha borda
        
        # Centraliza o texto verticalmente dentro do cabeçalho
        # Se max_lines for maior que a qtd de linhas desta célula, centralizamos visualmente
        offset_y = (header_height - (len(lines) * line_h)) / 2
        
        for j, line in enumerate(lines):
            pdf.set_xy(x_col + padding, y_start + offset_y + (j * line_h))
            pdf.cell(w - 2*padding, line_h, line, align="C")
            
    # 4. Posiciona o cursor para começar a tabela exatamente abaixo do cabeçalho
    pdf.set_xy(x_start, y_start + header_height)

# --- 1. A FUNÇÃO DE AJUDA ---
def wrap_text_lines(pdf_obj, text, width):
    """Calcula a quebra de texto por largura."""
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
                if cur:
                    out_lines.append(cur)
                part = ''
                for ch in w:
                    if pdf_obj.get_string_width(part + ch) <= width:
                        part += ch
                    else:
                        if part:
                            out_lines.append(part)
                        part = ch
                cur = part
        if cur:
            out_lines.append(cur)
    return out_lines

# --- 2. A FUNÇÃO QUE DESENHA A LINHA ---
def draw_table_row(pdf, data, widths, headers):
    line_h = 5
    padding = 2
    
    # Agora ela encontra a função wrap_text_lines acima!
    wrapped = []
    for i, item in enumerate(data):
        wrapped.append(wrap_text_lines(pdf, str(item), widths[i] - 2*padding))
    
    max_lines = max(len(col) for col in wrapped)
    altura_linha = max_lines * line_h
    
    # Verifica quebra de página
    if pdf.get_y() + altura_linha > (pdf.h - pdf.b_margin):
        pdf.add_page()
        # Certifique-se de que sua função draw_table_header está definida neste mesmo arquivo ou importada
        draw_table_header(pdf, headers, widths) 
    
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    
    for i, (w, lines_list) in enumerate(zip(widths, wrapped)):
        x_col = x_start + sum(widths[:i])
        pdf.rect(x_col, y_start, w, altura_linha)
        
        for j, line in enumerate(lines_list):
            pdf.set_xy(x_col + padding, y_start + (j * line_h) + padding/2)
            pdf.cell(w - 2*padding, line_h, line, border=0, align="L")
            
    pdf.set_xy(x_start, y_start + altura_linha)

def gerar_pdf_em_memoria(id_proc):
    df_processo = buscar_dados_do_processo(id_proc)
    if df_processo.empty: return None

    pdf = PDF()
    pdf.add_page()
    primeira_linha = df_processo.iloc[0]

    # --- Cabeçalho e Detalhes ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 8, f"ID DO PROCESSO: {id_proc}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.cell(0, 8, f"ÁREA: {primeira_linha['AREA']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
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

    # --- Tabela ---
    headers = ["RISCO", "FATOR DE RISCO", "O QUE PODERIA MELHORAR?", "IMPACTO", "PROBABILIDADE", "RISCO BRUTO"]
    widths = [50, 40, 40, 15, 15, 20]

    draw_table_header(pdf, headers, widths)

    for _, linha in df_processo.iterrows():
        data = [
            linha['RISCO'],
            linha['FATOR DE RISCO'],
            linha['O QUE PODERIA MELHORAR?'],
            linha['IMPACTO'],
            linha['PROBABILIDADE'],
            int(linha['RISCO BRUTO'])
        ]
        draw_table_row(pdf, data, widths, headers)
    
    # --- Seção de Assinaturas (Ao final da página) ---
    posicao_ancora = 240
    
    # Se a tabela não chegou no final, pula para a âncora
    if pdf.get_y() < posicao_ancora:
        pdf.set_y(posicao_ancora)
    
    # 1. Desenha a Data
    data_hoje = datetime.now()
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    data_formatada = f"Vassouras, {data_hoje.day} de {meses[data_hoje.month - 1]} de {data_hoje.year}."
    
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, data_formatada, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # 2. Desenha as assinaturas
    y_assinatura = pdf.get_y() + 10
    pdf.line(20, y_assinatura, 90, y_assinatura)
    pdf.line(110, y_assinatura, 180, y_assinatura)
    
    pdf.set_y(y_assinatura + 2)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(90, 5, "Gerência", align="C")
    pdf.cell(90, 5, "Superintendência", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # --- IMPORTANTE: O Retorno ---
    return pdf.output(dest='S')

def get_estilo_risco(score):
    if score >= 12:
        return "#d9534f", "🔴" 
    elif score >= 8:
        return "#f0ad4e", "🟠" 
    elif score >= 4:
        return "#f7d794", "🟡" 
    else:
        return "#5cb85c", "🟢"