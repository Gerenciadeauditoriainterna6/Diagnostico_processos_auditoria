// ============================================================
// controles_main.js - INICIALIZAÇÃO DA PÁGINA DE CONTROLES
// ============================================================

import { 
    carregarEtapas,
    excluirControle
} from './controles_etapas.js';

import { 
    abrirModalControle,
    visualizarControle,
    editarControle,
    fecharModalControle,
    setupModalControle,
    salvarControle
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

    document.getElementById('btn-fechar-modal-ajuda')?.addEventListener('click', () => {
        document.getElementById('modal-ajuda').style.display = 'none';
    });

    document.getElementById('btn-fechar-modal-ajuda-rodape')?.addEventListener('click', () => {
        document.getElementById('modal-ajuda').style.display = 'none';
    });
    
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

    document.addEventListener('click', (e) => {
        // Botão Adicionar Controle
        const btnAddControle = e.target.closest('.btn-add-controle');
        if (btnAddControle) {
            e.stopPropagation();
            const riscoId = btnAddControle.dataset.riscoId;
            const riscoNome = btnAddControle.dataset.riscoNome;
            const etapaId = btnAddControle.dataset.etapaId;
            const fatorRisco = btnAddControle.dataset.fator || '';
            abrirModalControle(riscoId, riscoNome, etapaId, fatorRisco);
            return;
        }
        
        // Botão Visualizar Controle
        const btnView = e.target.closest('.btn-view-icon');
        if (btnView) {
            e.stopPropagation();
            const controleId = btnView.dataset.controleId;
            const riscoId = btnView.dataset.riscoId;
            visualizarControle(controleId, riscoId);
            return;
        }
        
        // Botão Editar Controle
        const btnEditControle = e.target.closest('.btn-edit-icon');
        if (btnEditControle) {
            e.stopPropagation();
            const controleId = btnEditControle.dataset.controleId;
            const riscoId = btnEditControle.dataset.riscoId;
            editarControle(controleId, riscoId);
            return;
        }

        // ⭐ Botão Salvar Controle
        const btnSalvarControle = e.target.closest('#btn-salvar-modal-controle');
        if (btnSalvarControle) {
            e.preventDefault();
            salvarControle();  // ⭐ Importado no topo do controles_main.js
            return;
        }
        
        // Botão Excluir Controle
        const btnDeleteControle = e.target.closest('.btn-delete-icon');
        if (btnDeleteControle) {
            e.stopPropagation();
            const controleId = btnDeleteControle.dataset.controleId;
            const nomeControle = btnDeleteControle.dataset.controleNome;
            const riscoId = btnDeleteControle.dataset.riscoId;
            const etapaId = btnDeleteControle.dataset.etapaId;
            excluirControle(controleId, nomeControle, riscoId, etapaId);
            return;
        }
        
        const btnAjuda = e.target.closest('.help-icon');
        if (btnAjuda) {
            e.stopPropagation();
            const texto = btnAjuda.getAttribute('data-ajuda');
            const titulo = btnAjuda.closest('label')?.textContent?.trim() || 'Ajuda';
            
            // ⭐ FORMATAR o texto
            const textoFormatado = formatarTextoAjuda(texto);
            
            document.getElementById('modal-ajuda-titulo').innerHTML = `<i class="fas fa-question-circle"></i> ${titulo}`;
            document.getElementById('modal-ajuda-texto').innerHTML = textoFormatado;  // ⭐ innerHTML
            document.getElementById('modal-ajuda').style.display = 'flex';
            return;
        }

    })
    
    
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

function formatarTextoAjuda(texto) {
    // Divide por linhas
    const linhas = texto.split('\n');
    
    // Para cada linha, coloca em negrito o que vem antes do ':'
    const linhasFormatadas = linhas.map(linha => {
        if (linha.includes(':')) {
            const [antes, ...depois] = linha.split(':');
            return `<strong>${antes}:</strong>${depois.join(':')}`;
        }
        return linha;
    });
    
    return linhasFormatadas.join('<br>');
}