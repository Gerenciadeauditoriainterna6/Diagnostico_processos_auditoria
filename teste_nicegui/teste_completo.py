# teste_completo.py
from nicegui import ui
import pandas as pd
from datetime import datetime

# ============================================
# ESTILOS CSS PERSONALIZADOS
# ============================================

css_personalizado = """
<style>
    /* Estilo para cards de risco alto */
    .card-alto {
        background-color: #fee8e8;
        border-left: 4px solid #dc3545;
    }
    /* Estilo para cards de risco médio */
    .card-medio {
        background-color: #fff3e0;
        border-left: 4px solid #ffc107;
    }
    /* Estilo para cards de risco baixo */
    .card-baixo {
        background-color: #e8f8e8;
        border-left: 4px solid #28a745;
    }
    /* Animações */
    .hover-scale:hover {
        transform: scale(1.02);
        transition: all 0.3s ease;
    }
    .custom-card {
        transition: all 0.3s ease;
    }
    .custom-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .sidebar-item {
        cursor: pointer;
        padding: 8px 12px;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    .sidebar-item:hover {
        background-color: #e0e0e0;
    }
</style>
"""

ui.add_head_html(css_personalizado)

# ============================================
# BARRA LATERAL (SIDEBAR) COM ÍCONES
# ============================================

with ui.header().classes('bg-blue-800 text-white p-4'):
    with ui.row().classes('items-center gap-2'):
        ui.icon('assignment', size='lg')
        ui.label('Sistema de Auditoria Interna - FUSVE').classes('text-xl font-bold')

# Estado para controlar o menu ativo
menu_atual = {'value': 'dashboard'}

def mudar_menu(nome):
    menu_atual['value'] = nome
    container_conteudo.clear()
    with container_conteudo:
        if nome == 'dashboard':
            tela_dashboard()
        elif nome == 'processos':
            tela_processos()
        elif nome == 'areas':
            tela_areas()
        elif nome == 'riscos':
            tela_riscos()
        elif nome == 'auditorias':
            tela_auditorias()

with ui.row().classes('w-full'):
    # Sidebar com ícones
    with ui.column().classes('w-64 bg-gray-100 min-h-screen p-4'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('menu', size='sm', color='gray')
            ui.label('MENU').classes('text-gray-500 text-sm font-bold')
        
        # Itens do menu como botões
        ui.button('', icon='dashboard', on_click=lambda: mudar_menu('dashboard')).props('flat').classes('w-full justify-start gap-2 mb-1')
        ui.label('Dashboard').classes('text-sm ml-8 -mt-7 mb-2')
        
        ui.button('', icon='description', on_click=lambda: mudar_menu('processos')).props('flat').classes('w-full justify-start gap-2 mb-1')
        ui.label('Processos').classes('text-sm ml-8 -mt-7 mb-2')
        
        ui.button('', icon='business', on_click=lambda: mudar_menu('areas')).props('flat').classes('w-full justify-start gap-2 mb-1')
        ui.label('Áreas').classes('text-sm ml-8 -mt-7 mb-2')
        
        ui.button('', icon='risk', on_click=lambda: mudar_menu('riscos')).props('flat').classes('w-full justify-start gap-2 mb-1')
        ui.label('Riscos').classes('text-sm ml-8 -mt-7 mb-2')
        
        ui.button('', icon='calendar_month', on_click=lambda: mudar_menu('auditorias')).props('flat').classes('w-full justify-start gap-2 mb-1')
        ui.label('Auditorias').classes('text-sm ml-8 -mt-7 mb-2')
    
    # Conteúdo principal
    container_conteudo = ui.column().classes('flex-1 p-6')

# ============================================
# TELA: DASHBOARD
# ============================================

def tela_dashboard():
    with ui.row().classes('items-center gap-2 mb-6'):
        ui.icon('dashboard', color='blue-800', size='lg')
        ui.label('Dashboard').classes('text-2xl font-bold text-blue-800')
    
    # Cards de métricas com ícones
    with ui.row().classes('w-full gap-4 mb-8'):
        with ui.card().classes('flex-1 bg-blue-50 text-center p-4 custom-card'):
            with ui.row().classes('justify-center items-center gap-2'):
                ui.icon('assignment', color='blue-800')
                ui.label('45').classes('text-3xl font-bold text-blue-800')
            ui.label('Processos Mapeados').classes('text-gray-600')
        
        with ui.card().classes('flex-1 bg-red-50 text-center p-4 custom-card'):
            with ui.row().classes('justify-center items-center gap-2'):
                ui.icon('warning', color='red-800')
                ui.label('12').classes('text-3xl font-bold text-red-800')
            ui.label('Riscos Altos').classes('text-gray-600')
        
        with ui.card().classes('flex-1 bg-green-50 text-center p-4 custom-card'):
            with ui.row().classes('justify-center items-center gap-2'):
                ui.icon('verified', color='green-800')
                ui.label('8').classes('text-3xl font-bold text-green-800')
            ui.label('Controles Ativos').classes('text-gray-600')
        
        with ui.card().classes('flex-1 bg-yellow-50 text-center p-4 custom-card'):
            with ui.row().classes('justify-center items-center gap-2'):
                ui.icon('audit', color='yellow-800')
                ui.label('3').classes('text-3xl font-bold text-yellow-800')
            ui.label('Auditorias em Andamento').classes('text-gray-600')
    
    # Gráfico
    with ui.row().classes('items-center gap-2 mb-4'):
        ui.icon('bar_chart', color='blue-800')
        ui.label('Riscos por Processo').classes('font-bold')
    
    ui.echart({
        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
        'xAxis': {'type': 'category', 'data': ['Processo A', 'Processo B', 'Processo C', 'Processo D']},
        'yAxis': {'type': 'value', 'name': 'Score de Risco'},
        'series': [{
            'name': 'Risco Bruto',
            'type': 'bar',
            'data': [7, 11, 5, 9],
            'itemStyle': {'color': '#1848d8', 'borderRadius': [5, 5, 0, 0]}
        }]
    }).classes('w-full h-96')
    
    # Tabela de atividades recentes
    with ui.row().classes('items-center gap-2 mt-8 mb-4'):
        ui.icon('history', color='blue-800')
        ui.label('Atividades Recentes').classes('font-bold')
    
    dados_recentes = pd.DataFrame({
        'Data': ['15/03/2025', '14/03/2025', '13/03/2025'],
        'Processo': ['Gerar Contracheque', 'Processar Férias', 'Encerramento Folha'],
        'Ação': ['Editado', 'Criado', 'Risco Identificado']
    })
    ui.table.from_pandas(dados_recentes).classes('w-full')

# ============================================
# TELA: PROCESSOS
# ============================================

def tela_processos():
    with ui.row().classes('items-center gap-2 mb-6'):
        ui.icon('description', color='blue-800', size='lg')
        ui.label('Gestão de Processos').classes('text-2xl font-bold text-blue-800')
    
    # Abas
    with ui.tabs().classes('w-full mb-4') as tabs:
        tab_lista = ui.tab('📋 Lista de Processos')
        tab_novo = ui.tab('➕ Novo Processo')
    
    with ui.tab_panels(tabs, value=tab_lista).classes('w-full'):
        
        # Aba: Lista de Processos
        with ui.tab_panel(tab_lista):
            # Filtros
            with ui.row().classes('w-full gap-4 mb-6'):
                with ui.row().classes('flex-1 items-center gap-1'):
                    ui.icon('search', size='sm', color='gray')
                    ui.input('', placeholder='Nome ou código...').classes('w-full')
                ui.select(['Todas as Áreas', 'GGG', 'Finanças', 'TI'], label='Área').classes('w-48')
                ui.select(['Todos os Status', 'Ativo', 'Em Análise'], label='Status').classes('w-48')
            
            # Cards de processos
            processos = [
                {'codigo': '1.1', 'nome': 'Gerar Contracheque', 'area': 'GGG', 'risco': 11, 'status': 'Ativo'},
                {'codigo': '1.2', 'nome': 'Processar Férias', 'area': 'GGG', 'risco': 7, 'status': 'Ativo'},
                {'codigo': '2.1', 'nome': 'Fechamento Financeiro', 'area': 'Finanças', 'risco': 5, 'status': 'Em Análise'},
            ]
            
            for p in processos:
                cor_classe = 'card-alto' if p['risco'] >= 8 else 'card-medio' if p['risco'] >= 5 else 'card-baixo'
                with ui.card().classes(f'w-full mb-4 {cor_classe} custom-card'):
                    with ui.row().classes('justify-between items-center'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('assignment', size='sm', color='blue-800')
                            ui.label(f'{p["codigo"]} - {p["nome"]}').classes('font-bold text-lg')
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('business', size='sm', color='gray')
                            ui.label(p['area']).classes('text-gray-500')
                    
                    with ui.row().classes('justify-between items-center mt-2'):
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('warning', size='sm', color='orange')
                            ui.label(f'Risco: {p["risco"]}').classes('text-sm')
                        with ui.row().classes('items-center gap-1'):
                            status_icon = 'check_circle' if p['status'] == 'Ativo' else 'pending'
                            ui.icon(status_icon, size='sm', color='green' if p['status'] == 'Ativo' else 'orange')
                            ui.label(f'Status: {p["status"]}').classes('text-sm')
                    
                    with ui.row().classes('gap-2 mt-3 justify-end'):
                        ui.button('', icon='visibility', on_click=lambda: ui.notify('Ver detalhes')).props('outline').classes('text-sm')
                        ui.button('', icon='edit', on_click=lambda: ui.notify('Editar')).props('flat').classes('text-blue-600')
                        ui.button('', icon='delete', on_click=lambda: ui.notify('Remover')).props('flat').classes('text-red-600')
        
        # Aba: Novo Processo
        with ui.tab_panel(tab_novo):
            with ui.card().classes('w-full max-w-2xl mx-auto custom-card'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('add_circle', color='blue-800')
                    ui.label('Cadastro de Novo Processo').classes('text-xl font-bold text-blue-800')
                
                nome_processo = ui.input('Nome do Processo *').classes('w-full mb-4').props('outlined')
                
                with ui.row().classes('w-full gap-4 mb-4'):
                    area_select = ui.select(['GGG', 'Finanças', 'TI'], label='Área *').classes('flex-1')
                    ui.input('Código', value='1.3', disabled=True).classes('flex-1')
                
                descricao = ui.textarea('Descrição do Processo').classes('w-full mb-4').props('outlined rows=3')
                
                ui.label('Executores').classes('font-bold mb-2')
                executores = ui.select(['Funcionário 1', 'Funcionário 2', 'Funcionário 3'], label='Selecione', multiple=True).classes('w-full mb-4')
                
                def salvar_processo():
                    if nome_processo.value and area_select.value:
                        ui.notify(f'Processo {nome_processo.value} salvo!', type='positive')
                    else:
                        ui.notify('Preencha os campos obrigatórios!', type='warning')
                
                with ui.row().classes('gap-4 mt-4'):
                    ui.button('', icon='save', on_click=salvar_processo).classes('bg-blue-600 text-white')
                    ui.button('Cancelar', on_click=lambda: ui.notify('Cancelado')).props('outline')

# ============================================
# TELA: ÁREAS
# ============================================

def tela_areas():
    with ui.row().classes('items-center gap-2 mb-6'):
        ui.icon('business', color='blue-800', size='lg')
        ui.label('Cadastro de Áreas').classes('text-2xl font-bold text-blue-800')
    
    with ui.card().classes('w-full max-w-2xl mx-auto custom-card'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('add_location', color='blue-800')
            ui.label('Nova Área').classes('text-lg font-bold')
        
        nome = ui.input('Nome da Área *').classes('w-full mb-4').props('outlined')
        
        with ui.row().classes('w-full gap-4 mb-4'):
            email = ui.input('E-mail').classes('flex-1').props('outlined')
            telefone = ui.input('Telefone').classes('flex-1').props('outlined')
        
        gestor = ui.input('Nome do Gestor *').classes('w-full mb-4').props('outlined')
        objetivo = ui.textarea('Objetivo da Área').classes('w-full mb-4').props('outlined rows=3')
        
        def salvar_area():
            if nome.value and gestor.value:
                ui.notify(f'Área {nome.value} salva!', type='positive')
                nome.set_value('')
                email.set_value('')
                telefone.set_value('')
                gestor.set_value('')
                objetivo.set_value('')
            else:
                ui.notify('Preencha os campos obrigatórios!', type='warning')
        
        ui.button('', icon='save', on_click=salvar_area).classes('bg-blue-600 text-white w-full')

# ============================================
# TELA: RISCOS
# ============================================

def tela_riscos():
    with ui.row().classes('items-center gap-2 mb-6'):
        ui.icon('warning', color='blue-800', size='lg')
        ui.label('Gestão de Riscos').classes('text-2xl font-bold text-blue-800')
    
    with ui.card().classes('w-full custom-card'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('add_alert', color='red')
            ui.label('Novo Risco').classes('text-lg font-bold')
        
        processo_associado = ui.select(['Processo 1.1 - Gerar Contracheque', 'Processo 1.2 - Processar Férias'], label='Processo Associado *').classes('w-full mb-4')
        nome_risco = ui.input('Nome do Risco *').classes('w-full mb-4').props('outlined')
        fator_risco = ui.textarea('Fator de Risco').classes('w-full mb-4').props('outlined rows=2')
        
        with ui.row().classes('w-full gap-4 mb-4'):
            impacto = ui.select(['Muito Alto', 'Alto', 'Médio', 'Baixo'], label='Impacto').classes('flex-1')
            probabilidade = ui.select(['Muito Alta', 'Alta', 'Média', 'Baixa'], label='Probabilidade').classes('flex-1')
        
        motivo = ui.textarea('Motivo da Classificação').classes('w-full mb-4').props('outlined rows=2')
        
        def salvar_risco():
            if nome_risco.value and impacto.value and probabilidade.value:
                ui.notify(f'Risco {nome_risco.value} salvo!', type='positive')
            else:
                ui.notify('Preencha os campos obrigatórios!', type='warning')
        
        ui.button('', icon='save', on_click=salvar_risco).classes('bg-blue-600 text-white w-full')
    
    # Lista de riscos existentes
    with ui.row().classes('items-center gap-2 mt-8 mb-4'):
        ui.icon('list', color='blue-800')
        ui.label('Riscos Cadastrados').classes('font-bold text-lg')
    
    riscos = [
        {'nome': 'Risco de cadastro incorreto', 'processo': '1.1', 'impacto': 'Alto', 'score': 11},
        {'nome': 'Risco de atraso no pagamento', 'processo': '1.1', 'impacto': 'Médio', 'score': 7},
        {'nome': 'Risco de falha no sistema', 'processo': '1.2', 'impacto': 'Muito Alto', 'score': 15},
    ]
    
    for risco in riscos:
        cor = 'red' if risco['score'] >= 8 else 'orange' if risco['score'] >= 5 else 'green'
        with ui.card().classes('w-full mb-3 custom-card'):
            with ui.row().classes('justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('error', size='sm', color=cor)
                    ui.label(risco['nome']).classes('font-bold')
                ui.badge(f'Score: {risco["score"]}', color=cor).classes('text-white')
            ui.label(f'Processo: {risco["processo"]} | Impacto: {risco["impacto"]}').classes('text-sm text-gray-500')

# ============================================
# TELA: AUDITORIAS
# ============================================

def tela_auditorias():
    with ui.row().classes('items-center gap-2 mb-6'):
        ui.icon('calendar_month', color='blue-800', size='lg')
        ui.label('Planejamento de Auditorias').classes('text-2xl font-bold text-blue-800')
    
    # Seleção de ano
    with ui.row().classes('items-center gap-4 mb-6'):
        ui.icon('event', color='gray')
        ui.label('Ano:').classes('font-bold')
        ano_select = ui.select([2025, 2026, 2027], value=2025).classes('w-32')
    
    # Cards de trimestres
    with ui.row().classes('w-full gap-6'):
        for trimestre in range(1, 5):
            with ui.card().classes('flex-1 bg-gray-50 text-center custom-card'):
                ui.icon('calendar_month', color='blue-800', size='md')
                ui.label(f'{trimestre}º Trimestre').classes('font-bold text-lg text-blue-800 mt-2')
                ui.label('3 processos').classes('text-sm')
                ui.label('12 riscos identificados').classes('text-sm text-gray-500')
                ui.button('', icon='visibility', on_click=lambda t=trimestre: ui.notify(f'Trimestre {t}')).props('flat').classes('mt-2')
    
    # Nova auditoria
    with ui.card().classes('w-full mt-8 custom-card'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('add_circle', color='blue-800')
            ui.label('Criar Nova Auditoria').classes('text-lg font-bold')
        
        with ui.row().classes('w-full gap-4 mb-4'):
            area_auditoria = ui.select(['GGG', 'Finanças', 'TI'], label='Área').classes('flex-1')
            trimestre_auditoria = ui.select([1, 2, 3, 4], label='Trimestre').classes('w-32')
        
        with ui.row().classes('w-full gap-4 mb-4'):
            data_inicio = ui.date(value='2025-04-01', label='Data Início').classes('flex-1')
            data_fim = ui.date(value='2025-06-30', label='Data Fim').classes('flex-1')
        
        titulo_auditoria = ui.input('Título da Auditoria').classes('w-full mb-4').props('outlined')
        objetivo_auditoria = ui.textarea('Objetivo da Auditoria').classes('w-full mb-4').props('outlined rows=2')
        
        def criar_auditoria():
            if titulo_auditoria.value and area_auditoria.value:
                ui.notify(f'Auditoria {titulo_auditoria.value} criada!', type='positive')
            else:
                ui.notify('Preencha os campos obrigatórios!', type='warning')
        
        ui.button('', icon='check_circle', on_click=criar_auditoria).classes('bg-blue-600 text-white w-full')

# ============================================
# DIÁLOGO MODAL COM ÍCONES
# ============================================

with ui.dialog() as dialog_confirmacao:
    with ui.card():
        with ui.row().classes('items-center gap-2'):
            ui.icon('warning', color='orange')
            ui.label('Confirmar ação').classes('text-lg font-bold')
        ui.label('Deseja realmente realizar esta ação?')
        with ui.row().classes('gap-4 mt-4 justify-end'):
            ui.button('', icon='close', on_click=dialog_confirmacao.close).props('outline')
            ui.button('', icon='check', on_click=dialog_confirmacao.close).classes('bg-blue-600 text-white')

def mostrar_modal():
    dialog_confirmacao.open()

# ============================================
# BOTÕES FLUTUANTES COM ÍCONES
# ============================================

ui.button('', icon='notifications', on_click=lambda: ui.notify('Exemplo de notificação!', type='info')).classes('fixed bottom-4 right-4 bg-blue-600 text-white rounded-full')
ui.button('', icon='help', on_click=mostrar_modal).classes('fixed bottom-4 right-24 bg-gray-600 text-white rounded-full')

# ============================================
# INICIAR APLICAÇÃO
# ============================================

# Iniciar com a tela de dashboard
tela_dashboard()

ui.run(title='Sistema de Auditoria - NiceGUI', port=8080)