// ============================================================
// main_etapas.js - ORQUESTRADOR DAS ETAPAS
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Página de detalhamento de etapas carregada');

    // ============================================================
    // 1. INICIALIZAR MÓDULOS
    // ============================================================
    
    // ⭐ LoadingModule PRIMEIRO
    if (typeof LoadingModule !== 'undefined') {
        LoadingModule.init();
        console.log('   ✅ LoadingModule inicializado');
    }
    
    if (typeof ObrigacoesModule !== 'undefined') {
        ObrigacoesModule.init();
        console.log('   ✅ ObrigacoesModule inicializado');
    }
    
    if (typeof ExecutoresModule !== 'undefined') {
        ExecutoresModule.init();
        console.log('   ✅ ExecutoresModule inicializado');
    }
    
    if (typeof ManualModule !== 'undefined') {
        ManualModule.init();
        console.log('   ✅ ManualModule inicializado');
    }
    
    if (typeof AutoSaveModule !== 'undefined') {
        AutoSaveModule.init();
        console.log('   ✅ AutoSaveModule inicializado');
    }
    
    if (typeof AnalisesModule !== 'undefined') {
        AnalisesModule.init();
        console.log('   ✅ AnalisesModule inicializado');
    }
    
    if (typeof ModalEtapaModule !== 'undefined') {
        ModalEtapaModule.init();
        console.log('   ✅ ModalEtapaModule inicializado');
    }
    
    if (typeof VisualizarModule !== 'undefined') {
        VisualizarModule.init();
        console.log('   ✅ VisualizarModule inicializado');
    }
    
    // ⭐ NOVO: PoliticaInternaModule
    if (typeof PoliticaInternaModule !== 'undefined') {
        PoliticaInternaModule.init();
        console.log('   ✅ PoliticaInternaModule inicializado');
    }

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

            // Loading ao salvar estado
            LoadingModule.mostrar('Salvando estado...');

            try {
                await salvarEstado();
            } finally {
                LoadingModule.ocultar();
            }
            
            window.location.href = '/detalhamento';
        });
    }

    // Botão Nova Etapa
    const btnNovaEtapa = document.getElementById('btn-nova-etapa');
    if (btnNovaEtapa && typeof ModalEtapaModule !== 'undefined') {
        btnNovaEtapa.addEventListener('click', () => {
            // ⭐ Loading automático
            LoadingModule.executarComLoading(
                () => ModalEtapaModule.nova(),
                'Preparando nova etapa...'
            );
        });
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
        btnSalvarAnalise.addEventListener('click', () => {
            // ⭐ Loading ao salvar análise
            LoadingModule.executarComLoading(
                () => AnalisesModule.salvar(),
                'Salvando análise...'
            );
        });
    }

    // Botão Adicionar Obrigação (delegação - funciona mesmo se criado depois)
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('#btn-adicionar-obrigacao');
        if (btn && typeof ObrigacoesModule !== 'undefined') {
            ObrigacoesModule.adicionarObrigacao();
        }
    });

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

// ============================================================
// TOOLTIP SEGUINDO O MOUSE
// ============================================================
document.addEventListener('mousemove', (e) => {
    document.querySelectorAll('.help-icon:hover').forEach(icon => {
        const tooltip = icon.getAttribute('data-tooltip');
        if (!tooltip) return;
        
        // Cria ou atualiza tooltip
        let tip = document.getElementById('active-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'active-tooltip';
            tip.style.cssText = `
                position: fixed;
                background: #1a1a1a;
                color: #fff;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 12px;
                line-height: 1.5;
                max-width: 320px;
                z-index: 999999;
                pointer-events: none;
                box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            `;
            document.body.appendChild(tip);
        }
        
        tip.textContent = tooltip;
        tip.style.left = (e.clientX + 15) + 'px';
        tip.style.top = (e.clientY - 40) + 'px';
        tip.style.display = 'block';
    });
});

// Esconde tooltip quando mouse sai
document.addEventListener('mouseout', (e) => {
    if (!e.target.closest('.help-icon')) {
        const tip = document.getElementById('active-tooltip');
        if (tip) tip.style.display = 'none';
    }
});

window.voltarParaDetalhamento = function () {
    salvarEstado();
    window.location.href = '/detalhamento';
};