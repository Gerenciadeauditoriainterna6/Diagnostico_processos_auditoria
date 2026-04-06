from nicegui import ui

def dizer_oi():
    ui.notify("Olá! cliquei no botão!", type='positive')

ui.label("meu primeiro Teste com NiceGUI").classes('text-2xl text-blue-600 font-bold')

ui.separator()

ui.input("Digite seu nome", placeholder="Seu nome aqui...").classes('w-64')
ui.button('Clique aqui', on_click=dizer_oi).classes('bg-blue-600 text-white')
ui.label('Este é um teste simples').classes('text-gray-500 mt-4')

ui.run()