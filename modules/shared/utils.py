"""
Funções utilitárias compartilhadas
"""
import streamlit as st


def exibir_descricao_categorias():
    """Exibe a descrição das categorias dos riscos"""
    with st.expander("📋 **Categorias de Risco Disponíveis**", expanded=False):
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 10px;'>
            <p style='font-weight: bold; margin-bottom: 8px;'>📋 Categorias de Risco disponíveis:</p>
            <ul style='margin: 0; padding-left: 20px;'>
                <li><strong>Risco Financeiro:</strong> - Qualquer atividade que envolva incerteza e, portanto, possa resultar em consequências financeiras negativas para a FUSVE.</li>
                <li><strong>Risco Legal:</strong> - Engloba todas as ameaças as quais a FUSVE esteja vulnerável em decorrência do descumprimento das legislações vigentes.</li>
                <li><strong>Risco Inerente:</strong> - É o nível de risco natural de uma atividade ou processo antes de qualquer ação de controle ou mitigação ser aplicada.</li>
                <li><strong>Risco de TI:</strong> - A possibilidade de ocorrência de deficiência ou inadequação de quaisquer processos que envolvem sistemas ou tecnologia.</li>
                <li><strong>Risco Integridade:</strong> - O potencial de qualquer evento, controlável ou não, de prejudicar negativamente a reputação de uma organização.</li>
                <li><strong>Risco Ambiental:</strong> - Qualquer ameaça causada por agentes físicos, químicos ou biológicos que possam acarretar em descumprimento das normas, podendo comprometer a saúde e a segurança dos envolvidos ao ecossistema.</li>
            </ul>
            <p style='margin-top: 10px; font-size: 0.85em; color: #6c757d;'>
                💡 <strong>Dica:</strong> Selecione uma ou mais categorias que melhor representam o risco.
            </p>
        </div>
        """, unsafe_allow_html=True)

def exibir_criterios_risco():
    """Exibe os critérios de Probabilidade e Impacto em um expander"""
    with st.expander("📋 **Critérios para Avaliação de Riscos**", expanded=False):
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.markdown("""
            ### 📊 **PROBABILIDADE**
            
            | Nível | Descrição |
            |-------|-----------|
            | **Baixa** | Pode ser que ocorra uma vez dentro de um ano. |
            | **Média** | Pode ser que ocorra mais de uma vez dentro de um ano. |
            | **Alta** | Pode ser que ocorra mensalmente. |
            | **Muito Alta** | Pode ser que ocorra diariamente. |
            """)
        
        with col_c2:
            st.markdown("""
            ### 💰 **IMPACTO**
            
            | Nível | Descrição |
            |-------|-----------|
            | **Baixo** | Desembolsos de até R$ 150.000,00. (Os riscos possuem consequências reversíveis em curto prazo com custos pouco baixos.) |
            | **Médio** | Desembolsos de R$ 150.000,01 até R$ 300.000,00. (Os riscos possuem consequências reversíveis em curto e médio prazo com custos médios) |
            | **Alto** | Desembolso de R$ 300.000,01 até R$ 1.500.000,00. (Os riscos possuem consequências reversíveis em médio e longo prazo com custos altos) |
            | **Muito Alto** | Desembolso acima de R$ 1.500.000,00. (Os riscos possuem consequências reversíveis em médio e longo prazo com custos muito altos)|
            """)

def limpar_campos_por_prefixo(prefixo):
    for key in st.session_state.keys():
        if key.startswith(prefixo):
            st.session_state[key] = ""

def limpar_todos_campos():
    """Limpa todos os campos da tela de diagnóstico - usa reset de formulário"""
    st.session_state['deve_limpar_diagnostico'] = True