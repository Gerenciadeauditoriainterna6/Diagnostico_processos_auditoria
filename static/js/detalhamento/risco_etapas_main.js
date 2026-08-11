// ============================================================
// riscos_etapas_main.js - ORQUESTRADOR DOS RISCOS DAS ETAPAS
// ============================================================

// ====== MAPA PARA CÁLCULO DE SCORE ======
const MAPA_RISCO = {
    "MUITO ALTO_MUITO ALTO": 15,
    "ALTO_MUITO ALTO": 14,
    "MÉDIO_MUITO ALTO": 13,
    "BAIXO_MUITO ALTO": 12,
    "MUITO ALTO_ALTO": 11,
    "ALTO_ALTO": 10,
    "MÉDIO_ALTO": 9,
    "BAIXO_ALTO": 8,
    "MUITO ALTO_MÉDIO": 7,
    "ALTO_MÉDIO": 6,
    "MÉDIO_MÉDIO": 5,
    "BAIXO_MÉDIO": 4,
    "MUITO ALTO_BAIXO": 3,
    "ALTO_BAIXO": 2,
    "MÉDIO_BAIXO": 1,
    "BAIXO_BAIXO": 0
};

function calcularScoreRisco(impacto, probabilidade) {
    const impactoUpper = (impacto || '').toUpperCase().trim();
    const probabilidadeUpper = (probabilidade || '').toUpperCase().trim();
    const chave = `${impactoUpper}_${probabilidadeUpper}`;
    const score = MAPA_RISCO[chave];
    return score !== undefined ? score : 0;
}

// ============================================================
// INICIALIZAÇÃO
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Página de Riscos das Etapas carregada');

    if (typeof RiscoModal !== 'undefined') {
        RiscoModal.init({
            getProcessoId: () => ModalRiscoEtapaModule.etapaIdAtual,
            getObjetivo: () => document.getElementById('modal-objetivo-texto')?.textContent || '',
            onSave: async (dados) => {
                // API da etapa
                const response = await window.fetchComAutenticacao('/api/risco-etapa/salvar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ...dados,
                        etapa_id: ModalRiscoEtapaModule.etapaIdAtual,
                        auditoria_id: document.getElementById('filtro_auditoria_select')?.value || null
                    })
                });
                const data = await response.json();
                if (data.success) {
                    window.mostrarToast('✅ Risco salvo!', 'success');
                    ModalRiscoEtapaModule.fechar();
                    await EtapasRiscosModule.carregarRiscosDaEtapa(
                        ModalRiscoEtapaModule.etapaIdAtual,
                        ModalRiscoEtapaModule.codigoEtapaAtual,
                        ModalRiscoEtapaModule.nomeEtapaAtual
                    );
                }
                return data.success;
            },
            onClose: () => {}
        });
    }

    // Inicializar módulos
    if (typeof EtapasRiscosModule !== 'undefined') EtapasRiscosModule.init();
    if (typeof ModalRiscoEtapaModule !== 'undefined') ModalRiscoEtapaModule.init();

    // Elementos do DOM
    const filtroAreaSelect = document.getElementById('filtro_area_select');
    const filtroAuditoriaSelect = document.getElementById('filtro_auditoria_select');

    // ============================================================
    // EVENTO: MUDANÇA DE ÁREA
    // ============================================================
    if (filtroAreaSelect) {
        filtroAreaSelect.addEventListener('change', function() {
            const areaId = this.value;
            
            // Carregar auditorias
            carregarAuditorias(areaId);

            // Limpar container de etapas
            if (typeof EtapasRiscosModule !== 'undefined') {
                EtapasRiscosModule.limpar();
            }
        });
    }

    // ============================================================
    // EVENTO: MUDANÇA DE AUDITORIA
    // ============================================================
    if (filtroAuditoriaSelect) {
        filtroAuditoriaSelect.addEventListener('change', async function() {
            const auditoriaId = this.value;

            if (!auditoriaId) {
                if (typeof EtapasRiscosModule !== 'undefined') {
                    EtapasRiscosModule.limpar();
                }
                return;
            }

            // Verificar permissão
            if (typeof EtapasRiscosModule !== 'undefined') {
                EtapasRiscosModule.container.innerHTML = `
                    <div style="text-align: center; padding: 60px 20px;">
                        <div class="dot-spinner">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                        </div>
                        <p style="margin-top: 25px; color: #666; font-size: 14px;">Verificando permissão...</p>
                    </div>
                `;
            }

            try {
                const response = await window.fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
                const data = await response.json();

                if (data.autorizado) {
                    if (typeof EtapasRiscosModule !== 'undefined') {
                        await EtapasRiscosModule.carregarEtapas(auditoriaId);
                    }
                } else {
                    if (typeof EtapasRiscosModule !== 'undefined') {
                        EtapasRiscosModule.container.innerHTML = `
                            <div class="alert-error" style="text-align: center; padding: 40px;">
                                <i class="fas fa-lock"></i> Você não tem permissão para visualizar as etapas desta auditoria.
                            </div>
                        `;
                    }
                }
            } catch (error) {
                console.error('Erro ao verificar permissão:', error);
                if (typeof EtapasRiscosModule !== 'undefined') {
                    EtapasRiscosModule.container.innerHTML = `
                        <div class="alert-error" style="text-align: center; padding: 40px;">
                            <i class="fas fa-exclamation-triangle"></i> Erro ao verificar permissão.
                        </div>
                    `;
                }
            }
        });
    }

    // ============================================================
    // CONFIGURAR HELP ICONS
    // ============================================================
    setupHelpIcons();

    console.log('✅ Todos os módulos inicializados');
});

// ============================================================
// CARREGAR AUDITORIAS POR ÁREA
// ============================================================
async function carregarAuditorias(areaId) {
    const filtroAuditoriaSelect = document.getElementById('filtro_auditoria_select');
    
    if (!areaId) {
        filtroAuditoriaSelect.innerHTML = '<option value="">Selecione uma área primeiro...</option>';
        filtroAuditoriaSelect.disabled = true;
        return;
    }

    filtroAuditoriaSelect.innerHTML = '<option value="">Carregando auditorias...</option>';
    filtroAuditoriaSelect.disabled = true;

    try {
        const response = await window.fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();

        if (data.auditorias && data.auditorias.length > 0) {
            filtroAuditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            data.auditorias.forEach(aud => {
                const option = document.createElement('option');
                option.value = aud.id;
                option.textContent = `${aud.codigo_auditoria || ''} - ${aud.titulo || ''}`.trim();
                filtroAuditoriaSelect.appendChild(option);
            });
            filtroAuditoriaSelect.disabled = false;
        } else {
            filtroAuditoriaSelect.innerHTML = '<option value="">Nenhuma auditoria encontrada</option>';
            filtroAuditoriaSelect.disabled = true;
        }
    } catch (error) {
        console.error('Erro ao carregar auditorias:', error);
        filtroAuditoriaSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

// ============================================================
// CONFIGURAR HELP ICONS
// ============================================================
function setupHelpIcons() {
    // Help icon de Categorias
    const helpCat = document.getElementById('help-categorias-icon');
    const infoCat = document.getElementById('info-categorias');
    if (helpCat && infoCat) {
        helpCat.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            infoCat.style.display = infoCat.style.display === 'none' ? 'block' : 'none';
        });
    }

    // Help icon de Critérios
    const helpCriterios = document.getElementById('help-criterios-icon');
    const infoCriterios = document.getElementById('info-criterios');
    if (helpCriterios && infoCriterios) {
        helpCriterios.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            infoCriterios.style.display = infoCriterios.style.display === 'none' ? 'block' : 'none';
        });
    }

    // Help icon de Causas
    const helpCatCausa = document.getElementById('help-categorias-causa-icon');
    const infoCatCausa = document.getElementById('info-categorias-causa');
    if (helpCatCausa && infoCatCausa) {
        helpCatCausa.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            infoCatCausa.style.display = infoCatCausa.style.display === 'none' ? 'block' : 'none';
        });
    }

    // Fechar cards ao clicar no X
    document.querySelectorAll('[id^="fechar-info-"]').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const card = this.closest('.info-card');
            if (card) card.style.display = 'none';
        });
    });

    // Fechar cards ao clicar fora
    document.addEventListener('click', function(e) {
        const cards = ['info-categorias', 'info-categorias-causa', 'info-criterios'];
        const icons = ['help-categorias-icon', 'help-categorias-causa-icon', 'help-criterios-icon'];
        
        cards.forEach((cardId, i) => {
            const card = document.getElementById(cardId);
            const icon = document.getElementById(icons[i]);
            if (card && icon && !card.contains(e.target) && !icon.contains(e.target)) {
                card.style.display = 'none';
            }
        });
    });
}