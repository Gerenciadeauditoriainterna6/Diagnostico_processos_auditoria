// ============================================================
// riscos_etapas_main.js - ORQUESTRADOR DOS RISCOS DAS ETAPAS
// ============================================================

// ====== MAPA PARA CÁLCULO DE SCORE ======
const MAPA_RISCO = {
    "MUITO ALTO_MUITO ALTO": 15, "ALTO_MUITO ALTO": 14,
    "MÉDIO_MUITO ALTO": 13, "BAIXO_MUITO ALTO": 12,
    "MUITO ALTO_ALTO": 11, "ALTO_ALTO": 10,
    "MÉDIO_ALTO": 9, "BAIXO_ALTO": 8,
    "MUITO ALTO_MÉDIO": 7, "ALTO_MÉDIO": 6,
    "MÉDIO_MÉDIO": 5, "BAIXO_MÉDIO": 4,
    "MUITO ALTO_BAIXO": 3, "ALTO_BAIXO": 2,
    "MÉDIO_BAIXO": 1, "BAIXO_BAIXO": 0
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

    // ⭐ Configurar RiscoModal para etapas (ÚNICO lugar que salva!)
    if (typeof RiscoModal !== 'undefined') {
        RiscoModal.init({
            getProcessoId: () => ModalRiscoEtapaModule.etapaIdAtual,
            getObjetivo: () => document.getElementById('modal-objetivo-texto')?.textContent || '',
            onSave: async (dados) => {
                console.log('📤 Salvando via RiscoModal:', dados);
                
                // Adicionar campos específicos da etapa
                const payload = {
                    ...dados,
                    etapa_id: ModalRiscoEtapaModule.etapaIdAtual,
                    auditoria_id: document.getElementById('filtro_auditoria_select')?.value || null,
                    consequencia: document.getElementById('risco_consequencia')?.value?.trim()?.toUpperCase() || '',
                    info_adicional: document.getElementById('risco_info_adicional')?.value?.trim()?.toUpperCase() || '',
                    origem: document.getElementById('risco_origem')?.value?.trim()?.toUpperCase() || '',
                };
                
                // Se for edição, incluir ID
                if (ModalRiscoEtapaModule.riscoIdEditando) {
                    payload.id = ModalRiscoEtapaModule.riscoIdEditando;
                }
                
                try {
                    const response = await window.fetchComAutenticacao('/api/risco-etapa/salvar', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
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
                        await EtapasRiscosModule.atualizarBadgeRiscos(ModalRiscoEtapaModule.etapaIdAtual);
                        return true;
                    } else {
                        window.mostrarToast('❌ ' + (data.error || 'Erro'), 'error');
                        return false;
                    }
                } catch (error) {
                    window.mostrarToast('❌ Erro de conexão', 'error');
                    return false;
                }
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
            carregarAuditorias(areaId);
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
                if (typeof EtapasRiscosModule !== 'undefined') EtapasRiscosModule.limpar();
                return;
            }

            if (typeof EtapasRiscosModule !== 'undefined') {
                EtapasRiscosModule.container.innerHTML = `
                    <div style="text-align:center;padding:60px 20px;">
                        <div class="dot-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
                        <p style="margin-top:25px;color:#666;font-size:14px;">Verificando permissão...</p>
                    </div>`;
            }

            try {
                const response = await window.fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
                const data = await response.json();
                if (data.autorizado && typeof EtapasRiscosModule !== 'undefined') {
                    await EtapasRiscosModule.carregarEtapas(auditoriaId);
                } else if (typeof EtapasRiscosModule !== 'undefined') {
                    EtapasRiscosModule.container.innerHTML = '<div class="alert-error"><i class="fas fa-lock"></i> Sem permissão.</div>';
                }
            } catch (error) {
                if (typeof EtapasRiscosModule !== 'undefined') {
                    EtapasRiscosModule.container.innerHTML = '<div class="alert-error">Erro ao verificar.</div>';
                }
            }
        });
    }

    // Configurar help icons
    setupHelpIcons();

    console.log('✅ Todos os módulos inicializados');
});

// ============================================================
// CARREGAR AUDITORIAS
// ============================================================
async function carregarAuditorias(areaId) {
    const select = document.getElementById('filtro_auditoria_select');
    if (!areaId) {
        select.innerHTML = '<option value="">Selecione uma área primeiro...</option>';
        select.disabled = true;
        return;
    }
    select.innerHTML = '<option value="">Carregando...</option>';
    select.disabled = true;
    try {
        const response = await window.fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();
        if (data.auditorias?.length > 0) {
            select.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            data.auditorias.forEach(aud => {
                const opt = document.createElement('option');
                opt.value = aud.id;
                opt.textContent = `${aud.codigo_auditoria || ''} - ${aud.titulo || ''}`.trim();
                select.appendChild(opt);
            });
            select.disabled = false;
        } else {
            select.innerHTML = '<option value="">Nenhuma auditoria</option>';
        }
    } catch (error) {
        select.innerHTML = '<option value="">Erro</option>';
    }
}

// ============================================================
// HELP ICONS
// ============================================================
function setupHelpIcons() {
    const configs = [
        { icon: 'help-categorias-icon', card: 'info-categorias' },
        { icon: 'help-criterios-icon', card: 'info-criterios' },
        { icon: 'help-categorias-causa-icon', card: 'info-categorias-causa' }
    ];
    
    configs.forEach(({ icon, card }) => {
        const iconEl = document.getElementById(icon);
        const cardEl = document.getElementById(card);
        if (iconEl && cardEl) {
            iconEl.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                cardEl.style.display = cardEl.style.display === 'none' ? 'block' : 'none';
            });
        }
    });

    document.querySelectorAll('[id^="fechar-info-"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const card = btn.closest('.info-card');
            if (card) card.style.display = 'none';
        });
    });

    document.addEventListener('click', (e) => {
        ['info-categorias', 'info-categorias-causa', 'info-criterios'].forEach((cardId, i) => {
            const card = document.getElementById(cardId);
            const icon = document.getElementById(configs[i]?.icon);
            if (card && icon && !card.contains(e.target) && !icon.contains(e.target)) {
                card.style.display = 'none';
            }
        });
    });
}