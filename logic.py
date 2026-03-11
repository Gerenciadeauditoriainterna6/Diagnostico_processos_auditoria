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

#MAPPING_AREAS = {"Gerência de Gente e gestão - GGG": 1, "Gerência de Finanças": 2,"Gerência de TI": 3}

def buscar_processo_por_codigo(codigo):
    """Busca todos os detalhes de um processo e o nome do gestor da área."""
    query = text("""
            SELECT p.*, i.nome_area, i.gestor AS responsavel_area
            FROM processos p
            JOIN informacoes_area i ON p.id_area = i.id_area
            WHERE p.codigo_processo = :c
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"c": str(codigo)}).mappings().first()
        return dict(result) if result else None

def salvar_etapa_no_banco(dados_etapa):
    """Salva os dados de uma etapa no banco de dados."""
    try:
        query = text("""
            INSERT INTO etapas_processo (
                    processo_id, codigo_etapa, descricao_etapa, como_e_feito, objetivo_etapa,
                    realizado_corretamente, link_diagrama_etapa, politica_interna, analise_critica,
                    sugestao_melhoria, necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                    criticidade_etapa, manual_processo_link
                ) VALUES (
                    :p_id, :cod, :desc, :como, :obj, :real, :link_d, :pol, :ana, :sug, :nec, :gan, :obri, :crit, :man
                )
        """)
        
        # MUDANÇA: Use 'engine.begin()' em vez de 'engine.connect()'
        with engine.begin() as conn:
            conn.execute(query, dados_etapa)
            
        return True
    except Exception as e:
        print(f"Erro ao salvar etapa: {e}")
        return False

def listar_etapas_do_processo(processo_id):
    """Retorna todas as etapas de um processo específico."""
    query = text("SELECT * FROM etapas_processo WHERE processo_id = :id ORDER BY codigo_etapa")
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"id": processo_id})

def obter_proximo_codigo_etapa(processo_id, codigo_processo):
    """Gera o código 1.2.1 baseado no número de etapas existentes."""
    query = text("SELECT COUNT(*) FROM etapas_processo WHERE processo_id = :id")
    with engine.connect() as conn:
        contagem = conn.execute(query, {"id": processo_id}).scalar() or 0
    return f"{codigo_processo}.{contagem + 1}"
  
def carregar_areas_banco():
    """ Busca áreas no Banco de Dados e retorna um dicionário {nome: id}."""
    query = text("SELECT id_area, nome_area FROM informacoes_area")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Transforma o DataFrame em um dicionário {'Nome da Área': id_area}
    # Zip junta as duas colunas: a primeira vira chave, a segunda vira valor
    return dict(zip(df['nome_area'], df['id_area']))

def salvar_risco_etapa(dados):
    query = text("""
        INSERT INTO riscos_etapa 
        (etapa_id, categoria, fator_risco, consequencia, info_adicional, financeiro, 
         ativo, origem, doc_legal, impacto, probabilidade, magnitude, apetite, tratamento)
        VALUES (:etapa_id, :cat, :fator, :cons, :info, :fin, :ativo, :ori, :doc, :imp, :prob, :mag, :apet, :trat)
    """)
    with engine.begin() as conn:
        conn.execute(query, dados)
        return True

def listar_riscos_etapa(etapa_id):
    query = text("SELECT * FROM riscos_etapa WHERE etapa_id = :e_id")
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"e_id": etapa_id})

def buscar_todos_processos():
    query = text("""
            SELECT 
                p.area,
                p.codigo_processo,
                p.nome_processo,
                i.gestor
            FROM processos p
            JOIN informacoes_area i ON p.area = i.nome_area""")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

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
            posicao_x_direita = 210 - 10 - largura_logo_auditoria
            
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
def obter_proximo_codigo(id_area):
    query = text("SELECT COUNT(*) FROM processos WHERE id_area = :id")
    with engine.connect() as conn:
        contagem = conn.execute(query, {"id": id_area}).scalar() or 0
    return f"{id_area}.{contagem + 1}"

def processar_codigo_inteligente():
    import streamlit as st
    # Certifique-se de que aqui você usa o ID, não o nome
    id_area = st.session_state.get("id_area_selecionado") 
    nome = st.session_state.get("input_processo")
    
    if not id_area or not nome:
        st.session_state['codigo_processo'] = ""
        return
        
    query = text("SELECT codigo_processo FROM processos WHERE id_area = :id_area AND nome_processo = :nome")
    with engine.connect() as conn:
        # AQUI estava o erro: o parâmetro deve ser :id_area
        resultado = conn.execute(query, {"id_area": id_area, "nome": nome}).fetchone()
        
    if resultado:
        st.session_state['codigo_processo'] = resultado[0]
    else:
        st.session_state['codigo_processo'] = obter_proximo_codigo(id_area)

def salvar_no_banco():
    import streamlit as st
    try: 
        with engine.begin() as conn:
            id_area_val = st.session_state.get("id_area_selecionado") 
            nome_area_val = st.session_state.get("area_selectbox")
            nome_val = st.session_state.get("input_processo")
            
            query_busca = text("SELECT id FROM processos WHERE id_area = :id_a AND nome_processo = :nome")
            processo_existente = conn.execute(query_busca, {"id_a": id_area_val, "nome": nome_val}).fetchone()
            
            # Dados padrão para novos campos (evita erro na consulta detalhada)
            dados_base = {
                "o": st.session_state['input_objetivo'], 
                "ex": st.session_state['input_executor'], 
                "d": st.session_state['input_descricao'], 
                "ei": st.session_state['input_etapa_ini'], 
                "ef": st.session_state['input_etapa_fim'], 
                "p": st.session_state['input_produto'],
                "a": nome_area_val,
                "st": "Ativo",        # Valor default
                "crit": "A definir", # Valor default
                "cat": "Geral"       # Valor default
            }

            if processo_existente:
                processo_id = processo_existente[0]
                sql_update = text("""
                    UPDATE processos 
                    SET objetivo=:o, executor=:ex, descricao=:d, etapa_ini=:ei, etapa_fim=:ef, produto=:p, area=:a
                    WHERE id = :pid
                """)
                dados_base["pid"] = processo_id
                conn.execute(sql_update, dados_base)
            else:
                sql_p = text("""
                    INSERT INTO processos (id_area, area, codigo_processo, nome_processo, objetivo, executor, descricao, etapa_ini, etapa_fim, produto, status, criticidade, categoria) 
                    VALUES (:id_a, :a, :c, :n, :o, :ex, :d, :ei, :ef, :p, :st, :crit, :cat) RETURNING id
                """)
                params_insert = {**dados_base, "id_a": id_area_val, "c": st.session_state['codigo_processo'], "n": nome_val}
                processo_id = conn.execute(sql_p, params_insert).scalar()

            # Riscos... (mantenha o código de riscos como está)
            conn.execute(text("DELETE FROM riscos WHERE processo_id = :pid"), {"pid": processo_id})

            # 3. Insere a lista atual de riscos
            sql_risco = text("""INSERT INTO riscos (processo_id, nome_risco, fator_risco, melhoria, impacto, probabilidade, apetite_risco, motivo_risco, score_risco) 
                                VALUES (:pid, :nome, :fator, :melhoria, :imp, :prob, :apetite, :motivo, :score)""")
            
            for i in range(len(st.session_state['riscos'])):
                imp = st.session_state.get(f"imp_{i}")
                prob = st.session_state.get(f"prob_{i}")
                score = MAPA_RISCO.get((imp, prob), 0)
                
                conn.execute(sql_risco, {
                    "pid": processo_id, 
                    "nome": st.session_state.get(f"nome_{i}"), 
                    "fator": st.session_state.get(f"fator_{i}"), 
                    "melhoria": st.session_state.get(f"melhoria_{i}"), 
                    "imp": imp, 
                    "prob": prob, 
                    "apetite": st.session_state.get(f"apetite_{i}"), 
                    "motivo": st.session_state.get(f"motivo_{i}"), 
                    "score": score
                })
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def buscar_processos_pendentes():
    # Adicionamos um JOIN com informacoes_area para exibir o nome da área, não o número
    query = text("""
        SELECT DISTINCT p.id, p.codigo_processo, i.nome_area, p.nome_processo 
        FROM processos p
        JOIN riscos r ON p.id = r.processo_id
        JOIN informacoes_area i ON p.id_area = i.id_area
        WHERE r.relatorio_gerado != 'Sim' OR r.relatorio_gerado IS NULL
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def buscar_dados_do_processo(codigo_processo):
    # Usamos o JOIN para buscar o nome da área baseado no ID
    query = text("""
        SELECT 
            i.nome_area AS "AREA", 
            p.nome_processo AS "PROCESSO", 
            p.objetivo AS "OBJETIVO",
            p.descricao AS "DESCRIÇÃO DO PROCESSO", 
            p.executor AS "QUEM EXECUTA?",
            p.produto AS "PRODUTO DO PROCESSO", 
            p.etapa_ini AS "ETAPA INICIAL",
            p.etapa_fim AS "ETAPA FINAL", 
            r.nome_risco AS "RISCO",
            r.fator_risco AS "FATOR DE RISCO", 
            r.melhoria AS "O QUE PODERIA MELHORAR?",
            r.impacto AS "IMPACTO", 
            r.probabilidade AS "PROBABILIDADE",
            r.score_risco AS "RISCO BRUTO"
        FROM processos p
        JOIN riscos r ON p.id = r.processo_id
        JOIN informacoes_area i ON p.id_area = i.id_area
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
        return "#ff0000", "🔴" 
    elif score >= 8:
        return "#f0ad4e", "🟠" 
    elif score >= 4:
        return "#f7ed94", "🟡" 
    else:
        return "#5cb85c", "🟢"

def salvar_controle_no_banco(dados):
    """
    Insere um novo controle no banco de dados vinculado a um risco.
    """
    query = text("""
        INSERT INTO controles (
            risco_id, 
            nome_controle, 
            forma_execucao, 
            natureza, 
            status, 
            frequencia_evidencia, 
            usuario_responsavel, 
            avaliacao_risco
        ) VALUES (
            :risco_id, 
            :nome, 
            :forma, 
            :natureza, 
            :status, 
            :freq, 
            :resp, 
            :aval
        )
    """)
    
    try:
        with engine.begin() as conn:
            conn.execute(query, {
                "risco_id": dados['risco_id'],
                "nome": dados['nome'],
                "forma": dados['forma'],
                "natureza": dados['natureza'],
                "status": dados['status'],
                "freq": dados['frequencia'],
                "resp": dados['responsavel'],
                "aval": dados['avaliacao']
            })
        return True
    except Exception as e:
        print(f"Erro ao salvar controle: {e}")
        return False

def listar_controles_da_etapa(etapa_id):
    """
    Busca todos os controles que pertencem aos riscos de uma etapa específica.
    Faz um JOIN entre as tabelas 'controles' e 'riscos'.
    """
    query = text("""
        SELECT 
            c.*, 
            r.fator_risco as fator_origem
        FROM controles c
        JOIN riscos r ON c.risco_id = r.id
        WHERE r.etapa_id = :etapa_id
    """)
    
    try:
        return pd.read_sql(query, engine, params={"etapa_id": etapa_id})
    except Exception as e:
        print(f"Erro ao listar controles: {e}")
        return pd.DataFrame()