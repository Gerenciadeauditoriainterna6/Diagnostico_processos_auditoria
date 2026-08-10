// ============================================================
// main_etapas.js - ORQUESTRADOR DAS ETAPAS
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Página de detalhamento de etapas carregada');

    // ============================================================
    // 1. INICIALIZAR MÓDULOS
    // ============================================================
    if (typeof ObrigacoesModule !== 'undefined') ObrigacoesModule.init();
    if (typeof ExecutoresModule !== 'undefined') ExecutoresModule.init();
    if (typeof ManualModule !== 'undefined') ManualModule.init();
    if (typeof AutoSaveModule !== 'undefined') AutoSaveModule.init();
    if (typeof AnalisesModule !== 'undefined') AnalisesModule.init();
    if (typeof ModalEtapaModule !== 'undefined') ModalEtapaModule.init();
    if (typeof VisualizarModule !== 'undefined') VisualizarModule.init();

    // ============================================================
    // 2. CARREGAR DADOS
    // ============================================================
    if (typeof TabelaEtapasModule !== 'undefined') {
        TabelaEtapasModule.carregarDadosProcesso();
    }

    // ============================================================
    // 3. CONFIGURAR EVENTOS DOS BOTÕES
    // ============================================================
    
    // Botão Voltar
    const btnVoltar = document.getElementById('btn-voltar-detalhamento');
    if (btnVoltar) {
        btnVoltar.addEventListener('click', async (e) => {
            e.preventDefault();
            await salvarEstado();
            window.location.href = '/detalhamento';
        });
    }

    // Botão Nova Etapa
    const btnNovaEtapa = document.getElementById('btn-nova-etapa');
    if (btnNovaEtapa && typeof ModalEtapaModule !== 'undefined') {
        btnNovaEtapa.addEventListener('click', () => ModalEtapaModule.nova());
    }

    // Botão Nova Análise
    const btnNovaAnalise = document.getElementById('btn-nova-analise');
    if (btnNovaAnalise && typeof AnalisesModule !== 'undefined') {
        btnNovaAnalise.addEventListener('click', () => AnalisesModule.mostrarForm('novo'));
    }

    // Botão Cancelar Análise
    const btnCancelarAnalise = document.getElementById('btn-cancelar-analise');
    if (btnCancelarAnalise && typeof AnalisesModule !== 'undefined') {
        btnCancelarAnalise.addEventListener('click', () => AnalisesModule.esconderForm());
    }

    // Botão Salvar Análise
    const btnSalvarAnalise = document.getElementById('btn-salvar-analise');
    if (btnSalvarAnalise && typeof AnalisesModule !== 'undefined') {
        btnSalvarAnalise.addEventListener('click', () => AnalisesModule.salvar());
    }

    // Botão Adicionar Obrigação
    const btnAdicionarObrigacao = document.getElementById('btn-adicionar-obrigacao');
    if (btnAdicionarObrigacao && typeof ObrigacoesModule !== 'undefined') {
        btnAdicionarObrigacao.addEventListener('click', () => ObrigacoesModule.adicionarObrigacao());
    }

    // Modal - configurar eventos
    if (typeof ModalEtapaModule !== 'undefined') {
        ModalEtapaModule.configurarEventos();
    }

    // ============================================================
    // 4. AUTOSAVE
    // ============================================================
    if (typeof AutoSaveModule !== 'undefined') {
        // Salvar rascunho a cada 30 segundos
        setInterval(() => {
            const modal = document.getElementById('modal-etapa');
            if (modal && modal.style.display === 'flex') {
                AutoSaveModule.salvarRascunho();
            }
        }, 30000);

        // Aviso ao sair da página
        window.addEventListener('beforeunload', (e) => {
            if (AutoSaveModule.temRascunho()) {
                e.preventDefault();
                e.returnValue = 'Você tem um rascunho não salvo.';
            }
        });
    }

    console.log('✅ Todos os módulos inicializados');
});

// ============================================================
// FUNÇÃO AUXILIAR
// ============================================================
async function salvarEstado() {
    const params = new URLSearchParams(window.location.search);
    const processoId = params.get('processo_id');
    if (!processoId) return;

    try {
        const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/dados`);
        const data = await response.json();
        if (data.success) {
            sessionStorage.setItem('detalhamento_estado', JSON.stringify({
                area_id: data.id_area,
                auditoria_id: data.auditoria_id,
                processo_id: processoId,
                processo_codigo: params.get('processo_codigo'),
                timestamp: Date.now()
            }));
        }
    } catch (error) {
        console.error('Erro ao salvar estado:', error);
    }
}

window.voltarParaDetalhamento = function () {
    salvarEstado();
    window.location.href = '/detalhamento';
};