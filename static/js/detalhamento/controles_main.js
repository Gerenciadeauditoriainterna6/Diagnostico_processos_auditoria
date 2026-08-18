// ============================================================
// controles_main.js - INICIALIZAÇÃO DA PÁGINA DE CONTROLES
// ============================================================

import { 
    carregarEtapas
} from './controles_etapas.js';

import { 
    setupModalControle,
    fecharModalControle
} from './controles_modal.js';

// ====== ELEMENTOS DO DOM ======
const etapasContainer = document.getElementById('etapas-container');

// ====== FUNÇÃO PARA MOSTRAR SPINNER ======
function mostrarSpinner(mensagem) {
    etapasContainer.innerHTML = `
        <div style="text-align: center; padding: 60px 20px;">
            <div class="dot-spinner">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <p style="margin-top: 25px; color: #666; font-size: 14px;">${mensagem}</p>
        </div>
    `;
}

// ====== FUNÇÃO PARA MOSTRAR MENSAGEM VAZIA ======
function mostrarMensagemVazia() {
    etapasContainer.innerHTML = `
        <div class="alert-info" style="text-align: center; padding: 40px;">
            <i class="fas fa-info-circle"></i> Selecione uma área e auditoria para visualizar as etapas.
        </div>
    `;
}

// ====== FUNÇÃO PARA HANDLE DA TECLA ESC ======
function handleEscKey(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('modal-controle');
        if (modal && modal.style.display === 'flex') {
            fecharModalControle();
        }
    }
}

// ====== INICIALIZAÇÃO DA PÁGINA ======
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Página de Controles de Etapas carregada');
    
    // Configurar modal
    setupModalControle();
    
    // Tecla ESC
    document.addEventListener('keydown', handleEscKey);
    
    // ⭐ Configurar filtros usando o componente reutilizável
    FiltrosModule.init({
        prefix: 'filtro',
        onAreaChange: (areaId) => {
            mostrarMensagemVazia();
        },
        onAuditoriaChange: async (auditoriaId) => {
            if (!auditoriaId) {
                mostrarMensagemVazia();
                return;
            }
            
            mostrarSpinner('Verificando permissão...');
            
            try {
                const response = await window.fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
                const data = await response.json();
                
                if (data.autorizado) {
                    await carregarEtapas(auditoriaId);
                } else {
                    etapasContainer.innerHTML = `
                        <div class="alert-error" style="text-align: center; padding: 40px;">
                            <i class="fas fa-lock"></i> Você não tem permissão para visualizar etapas dos processos desta auditoria.
                        </div>
                    `;
                }
            } catch (error) {
                console.error('❌ ERRO DETALHADO:', error);  // ⭐ ADICIONE AQUI
                etapasContainer.innerHTML = `...`;
                etapasContainer.innerHTML = `
                    <div class="alert-error" style="text-align: center; padding: 40px;">
                        <i class="fas fa-exclamation-triangle"></i> Erro ao verificar permissão. Tente novamente.
                    </div>
                `;
            }
        }
    });
    
    console.log('✅ Todos os eventos configurados!');
});

// ====== EXPORTAR FUNÇÕES GLOBAIS (para onclick no HTML) ======
window.toggleProcesso = (header) => {
    import('./controles_etapas.js').then(module => {
        module.toggleProcesso(header);
    });
};

window.toggleEtapa = (header) => {
    import('./controles_etapas.js').then(module => {
        module.toggleEtapa(header);
    });
};

window.toggleRisco = (card, event) => {
    import('./controles_etapas.js').then(module => {
        module.toggleRisco(card, event);
    });
};

window.abrirModalControle = (riscoId, riscoNome, etapaId, fatorRisco) => {
    import('./controles_modal.js').then(module => {
        module.abrirModalControle(riscoId, riscoNome, etapaId, fatorRisco);
    });
};

window.editarControle = (controleId, riscoId) => {
    import('./controles_modal.js').then(module => {
        module.editarControle(controleId, riscoId);
    });
};

window.excluirControle = (controleId, nomeControle, riscoId, etapaId) => {
    import('./controles_etapas.js').then(module => {
        module.excluirControle(controleId, nomeControle, riscoId, etapaId);
    });
};