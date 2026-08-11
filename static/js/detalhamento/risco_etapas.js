// ============================================================
// CARREGAR AUDITORIAS POR ÁREA (para os filtros principais)
// ============================================================
async function carregarAuditorias(areaId) {
    if (!areaId) {
        filtroAuditoriaSelect.innerHTML = '<option value="">Selecione uma área primeiro...</option>';
        filtroAuditoriaSelect.disabled = true;
        return;
    }

    filtroAuditoriaSelect.innerHTML = '<option value="">Carregando auditorias...</option>';
    filtroAuditoriaSelect.disabled = true;

    try {
        const response = await fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();

        if (data.auditorias && data.auditorias.length > 0) {
            filtroAuditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            data.auditorias.forEach(aud => {
                const option = document.createElement('option');
                option.value = aud.id;
                option.textContent = `${aud.codigo_auditoria} - ${aud.titulo} (${aud.ano}) ${aud.trimestre}º trim) - ${aud.unidade || ''}`;
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
// FUNÇÕES DE PREVIEW DE SCORE
// ============================================================
function atualizarPreviewScore(
    impactoId,
    probabilidadeId,
    previewDivId,
    previewScoreId
) {
    const impactoSelect = document.getElementById(impactoId);
    const probabilidadeSelect = document.getElementById(probabilidadeId);
    const preview = document.getElementById(previewDivId);
    const previewScore = document.getElementById(previewScoreId);

    if (!impactoSelect || !probabilidadeSelect || !preview || !previewScore) {
        return 0;
    }

    const impacto = impactoSelect.value;
    const probabilidade = probabilidadeSelect.value;
    const score = calcularScoreRisco(impacto, probabilidade);

    let nivel = "";
    let cor = "";

    if (score <= 3) {
        nivel = "BAIXA EXPOSIÇÃO";
        cor = "#d4edda";
    } else if (score <= 7) {
        nivel = "SOB OBSERVAÇÃO";
        cor = "#fff3cd";
    } else if (score <= 11) {
        nivel = "ATENÇÃO";
        cor = "#ffe5d0";
    } else {
        nivel = "CRÍTICO";
        cor = "#f8d7da";
    }

    previewScore.textContent = score;
    preview.innerHTML = `
        <strong>Score calculado:</strong>
        <span id="${previewScoreId}">${score}</span>
        (${nivel})
    `;
    preview.style.backgroundColor = cor;

    return score;
}




// ============================================================
// EVENTOS PRINCIPAIS
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Página de Riscos de Etapas carregada');

    // Configurar modal de risco
    setupModalRisco();

    // Configurar help icons
    setupHelpIcons();

    // ============================================================
    // EVENTOS DOS FILTROS PRINCIPAIS
    // ============================================================
    if (filtroAreaSelect) {
        filtroAreaSelect.addEventListener('change', function() {
            const areaId = this.value;
            carregarAuditorias(areaId);

            etapasContainer.innerHTML = `
                <div class="alert-info" style="text-align: center; padding: 40px;">
                    <i class="fas fa-info-circle"></i> Selecione uma auditoria para visualizar as etapas.
                </div>
            `;
        });
    }

    if (filtroAuditoriaSelect) {
        filtroAuditoriaSelect.addEventListener('change', async function() {
            const auditoriaId = this.value;

            if (!auditoriaId) {
                etapasContainer.innerHTML = `
                    <div class="alert-info" style="text-align: center; padding: 40px;">
                        <i class="fas fa-info-circle"></i> Selecione uma auditoria para visualizar as etapas.
                    </div>
                `;
                return;
            }

            // Verificar permissão e carregar etapas
            etapasContainer.innerHTML = `
                <div style="text-align: center; padding: 60px 20px;">
                    <div class="dot-spinner">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                    <p style="margin-top: 25px; color: #666; font-size: 14px;">Verificando permissão...</p>
                </div>
            `;

            try {
                const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
                const data = await response.json();

                if (data.autorizado) {
                    await carregarEtapas(auditoriaId);
                } else {
                    etapasContainer.innerHTML = `
                        <div class="alert-error" style="text-align: center; padding: 40px;">
                            <i class="fas fa-lock"></i> Você não tem permissão para visualizar as etapas dos processos desta auditoria.
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Erro ao verificar permissão:', error);
                etapasContainer.innerHTML = `
                    <div class="alert-error" style="text-align: center; padding: 40px;">
                        <i class="fas fa-exclamation-triangle"></i> Erro ao verificar permissão. Tente novamente.
                    </div>
                `;
            }
        });
    }

    // Carregar áreas para a matriz de achados
    carregarAreasMatriz();

    // Se houver área pré-selecionada
    if (filtroAreaSelect && filtroAreaSelect.value) {
        carregarAuditorias(filtroAreaSelect.value);
    }

    console.log('✅ Todos os eventos configurados!');
});

// ============================================================
// CONFIGURAR HELP ICONS
// ============================================================
function setupHelpIcons() {
    // Help icon de Categorias
    const helpCat = document.getElementById('help-categorias-icon');
    const infoCat = document.getElementById('info-categorias');
    if (helpCat && infoCat) {
        helpCat.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            infoCat.style.display = infoCat.style.display === 'none' ? 'block' : 'none';
        };
    }

    // Help icon de Critérios
    const helpCriterios = document.getElementById('help-criterios-icon');
    const infoCriterios = document.getElementById('info-criterios');
    if (helpCriterios && infoCriterios) {
        helpCriterios.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            infoCriterios.style.display = infoCriterios.style.display === 'none' ? 'block' : 'none';
        };
    }

    // Help icon de Causas
    const helpCatCausa = document.getElementById('help-categorias-causa-icon');
    const infoCatCausa = document.getElementById('info-categorias-causa');
    if (helpCatCausa && infoCatCausa) {
        helpCatCausa.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            infoCatCausa.style.display = infoCatCausa.style.display === 'none' ? 'block' : 'none';
        };
    }

    // Fechar cards ao clicar no X
    document.querySelectorAll('[id^="fechar-info-"]').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const card = this.closest('.info-card');
            if (card) card.style.display = 'none';
        });
    });
}

// ============================================================
// FECHAR CARDS AO CLICAR FORA
// ============================================================
document.addEventListener('click', function(e) {
    // Fechar categorias de risco
    const infoCat = document.getElementById('info-categorias');
    const helpCat = document.getElementById('help-categorias-icon');
    if (infoCat && helpCat) {
        if (!infoCat.contains(e.target) && !helpCat.contains(e.target)) {
            infoCat.style.display = 'none';
        }
    }

    // Fechar categorias de causa
    const infoCatCausa = document.getElementById('info-categorias-causa');
    const helpCatCausa = document.getElementById('help-categorias-causa-icon');
    if (infoCatCausa && helpCatCausa) {
        if (!infoCatCausa.contains(e.target) && !helpCatCausa.contains(e.target)) {
            infoCatCausa.style.display = 'none';
        }
    }

    // Fechar critérios
    const infoCriterios = document.getElementById('info-criterios');
    const helpCriterios = document.getElementById('help-criterios-icon');
    if (infoCriterios && helpCriterios) {
        if (!infoCriterios.contains(e.target) && !helpCriterios.contains(e.target)) {
            infoCriterios.style.display = 'none';
        }
    }
});
