"""
Módulo de Visão Geral dos Processos Mapeados
"""
# ===== MIGRAÇÃO PARA FLASK =====
# Streamlit removido - sistema agora usa Flask
# import streamlit as st  # REMOVIDO

# Placeholder para evitar erros (as funções Streamlit não serão chamadas no Flask)
class _DummyStreamlit:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

st = _DummyStreamlit()
import pandas as pd
from sqlalchemy import text
from database import engine
from logic import (listar_auditorias_por_ano, 
    buscar_processo_por_codigo, listar_executores_processo_com_nomes,
    listar_etapas_do_processo
)

from modules.execucao.areas import carregar_areas_banco

def tela_visao_geral_processos():
    """Tela de visão geral de todos os processos mapeados, com filtros por área e auditoria"""
    
    st.title("📋 Visão Geral dos Processos Mapeados")
    st.caption("Consulte todos os processos já diagnosticados, com opções de filtro por área ou auditoria.")
    
    # ===== FILTROS =====
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        # Filtro por Área
        areas_dict = carregar_areas_banco()
        areas_list = ["Todas as Áreas"] + list(areas_dict.keys())
        filtro_area = st.selectbox("Filtrar por Área:", areas_list)
    
    with col_f2:
        # Filtro por Auditoria (ano/trimestre)
        # Buscar auditorias disponíveis
        df_auditorias = listar_auditorias_por_ano()
        if not df_auditorias.empty:
            opcoes_auditoria = ["Todas as Auditorias"] + [
                f"{row['codigo_auditoria']} - {row['titulo']}" 
                for _, row in df_auditorias.iterrows()
            ]
            filtro_auditoria = st.selectbox("Filtrar por Auditoria:", opcoes_auditoria)
        else:
            filtro_auditoria = "Todas as Auditorias"
            st.info("Nenhuma auditoria encontrada.")
    
    with col_f3:
        # Filtro por texto (busca rápida)
        filtro_texto = st.text_input("🔍 Buscar processo:", placeholder="Nome ou código...")
    
    # ===== CONSULTA PRINCIPAL =====
    query_base = """
        SELECT 
            p.id,
            p.codigo_processo,
            p.nome_processo,
            i.nome_area,
            p.aprovacao as criticidade,
            COUNT(DISTINCT r.id) as total_riscos,
            COALESCE(MAX(r.score_risco), 0) as maior_risco,
            COUNT(DISTINCT e.id) as total_etapas,
            COUNT(DISTINCT c.id) as total_controles
        FROM processos p
        JOIN informacoes_area i ON p.id_area = i.id_area
        LEFT JOIN riscos r ON p.id = r.processo_id
        LEFT JOIN etapas_processo e ON p.id = e.processo_id
        LEFT JOIN riscos_etapa re ON e.id = re.etapa_id
        LEFT JOIN controles_etapa c ON re.id = c.risco_id
        WHERE 1=1
    """
    
    params = {}
    
    # Aplicar filtro de área
    if filtro_area != "Todas as Áreas":
        id_area = areas_dict[filtro_area]
        query_base += " AND p.id_area = :id_area"
        params['id_area'] = id_area
    
    # Aplicar filtro de auditoria
    if filtro_auditoria != "Todas as Auditorias":
        # Extrair ID da auditoria da string selecionada
        cod_auditoria = filtro_auditoria.split(" - ")[0]
        query_base += """
            AND p.id IN (
                SELECT processo_id 
                FROM auditoria_processos 
                WHERE auditoria_id = (
                    SELECT id FROM auditorias WHERE codigo_auditoria = :cod_auditoria
                )
            )
        """
        params['cod_auditoria'] = cod_auditoria
    
    query_base += """
    GROUP BY p.id, i.nome_area
    ORDER BY 
        (string_to_array(p.codigo_processo, '.'))[1]::int,
        (string_to_array(p.codigo_processo, '.'))[2]::int,
        (string_to_array(p.codigo_processo, '.'))[3]::int
"""
    
    # Executar consulta
    with engine.connect() as conn:
        df_processos = pd.read_sql(text(query_base), conn, params=params)
    
    # Aplicar filtro de texto (em memória, após a consulta)
    if filtro_texto:
        filtro_texto = filtro_texto.lower()
        df_processos = df_processos[
            df_processos['nome_processo'].str.lower().str.contains(filtro_texto, na=False) |
            df_processos['codigo_processo'].str.lower().str.contains(filtro_texto, na=False)
        ]
    
    # ===== EXIBIÇÃO DOS RESULTADOS =====
    st.divider()
    st.subheader(f"📊 Resultados: {len(df_processos)} processos encontrados")
    
    if not df_processos.empty:
        # Métricas resumidas
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total de Processos", len(df_processos))
        with col_m2:
            st.metric("Riscos Mapeados", df_processos['total_riscos'].sum())
        with col_m3:
            st.metric("Etapas Mapeadas", df_processos['total_etapas'].sum())
        with col_m4:
            st.metric("Controles Mapeados", df_processos['total_controles'].sum())
        
        st.divider()
        
        # Tabela interativa
        st.dataframe(
            df_processos[[
                'codigo_processo', 'nome_processo', 'nome_area',
                'criticidade', 'maior_risco', 'total_riscos', 'total_etapas', 'total_controles'
            ]],
            use_container_width=True,
            column_config={
                "codigo_processo": "Código",
                "nome_processo": "Processo",
                "nome_area": "Área",
                "criticidade": "Criticidade",
                "maior_risco": "Maior Risco",
                "total_riscos": "Qtd Riscos",
                "total_etapas": "Etapas",
                "total_controles": "Controles"
            },
            hide_index=True
        )
        
        # Opção de expandir para ver detalhes completos
        with st.expander("📋 Ver detalhes completos dos processos"):
            # Selectbox para escolher um processo e ver detalhes
            opcoes_detalhe = [f"{row['codigo_processo']} - {row['nome_processo']}" for _, row in df_processos.iterrows()]
            processo_selecionado = st.selectbox("Selecione um processo para ver detalhes:", [""] + opcoes_detalhe)
            
            if processo_selecionado:
                codigo = processo_selecionado.split(" - ")[0]
                processo = buscar_processo_por_codigo(codigo)
                
                if processo:
                    st.write(f"**Objetivo:** {processo['objetivo']}")
                    st.write(f"**Descrição:** {processo['descricao']}")

                    # ===== MOSTRAR EXECUTORES CORRETAMENTE =====
                    executores = listar_executores_processo_com_nomes(processo['id'])
                    if executores:
                        st.write("**Executores:**")
                        for exec_nome in executores:
                            st.write(f"- {exec_nome}")
                    else:
                        st.write("**Executores:** Nenhum executor cadastrado")
                    
                    # Mostrar etapas resumidas
                    etapas = listar_etapas_do_processo(processo['id'])
                    if not etapas.empty:
                        st.write("**Etapas:**")
                        for _, etapa in etapas.iterrows():
                            st.caption(f"• {etapa['codigo_etapa']} - {etapa['descricao_etapa']}")
    else:
        st.warning("Nenhum processo encontrado com os filtros selecionados.")