const etapasContainer = document.getElementById('etapas-container');

// ====== CARREGAR AUDITORIAS POR ÁREA ======
export async function carregarAuditorias(areaId) {
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
        filtroAuditoriaSelect.disabled = true;
    }
}

// ====== FUNÇÃO PARA CARREGAR ETAPAS ======
export async function carregarEtapas(auditoriaId) {
    console.log('📋 Carregando etapas para auditoria:', auditoriaId);

    etapasContainer.innerHTML = `
        <div style="text-align: center; padding: 60px 20px;">
            <div class="dot-spinner">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando etapas e seus controles...</p>
        </div>
    `;

    try {
        const responseProcessos = await fetchComAutenticacao(`/api/processos-por-auditoria?auditoria_id=${auditoriaId}`);
        const dataProcessos = await responseProcessos.json();

        console.log('📦 Processos encontrados:', dataProcessos);

        if (!dataProcessos.success || !dataProcessos.processos || dataProcessos.processos.length === 0) {
            etapasContainer.innerHTML = `
                <div class="alert-info" style="text-align: center; padding: 40px;">
                    <i class="fas fa-info-circle"></i> Nenhum processo encontrado para esta auditoria.
                </div>
            `;
            return;
        }

        let htmlFinal = '';

        for (const processo of dataProcessos.processos) {
            console.log(`🔍 Buscando etapas do processo: ${processo.codigo_processo} - ${processo.nome_processo}`);

            const responseEtapas = await fetchComAutenticacao(`/api/processo/${processo.id}/etapas`);
            const dataEtapas = await responseEtapas.json();

            console.log(`   📋 Etapas encontradas: ${dataEtapas.etapas?.length || 0}`);

            htmlFinal += `
                <div class="processo-card" data-processo-id="${processo.id}">
                    <div class="processo-header" onclick="toggleProcesso(this)">
                        <div class="processo-info">
                            <i class="fas fa-folder-open"></i>
                            <strong>${processo.codigo_processo}</strong>
                            <span>${processo.nome_processo}</span>
                        </div>
                        <i class="fas fa-chevron-down processo-arrow"></i>
                    </div>
                    <div class="processo-body" style="display: none;">
                        <div class="etapas-list">
            `;

            if (dataEtapas.success && dataEtapas.etapas && dataEtapas.etapas.length > 0) {
                for (const etapa of dataEtapas.etapas) {
                    htmlFinal += `
                        <div class="etapa-card" data-etapa-id="${etapa.id}" data-etapa-codigo="${etapa.codigo_etapa}" data-etapa-nome="${escapeHtml(etapa.nome_etapa)}">
                            <div class="etapa-header" onclick="toggleEtapa(this)">
                                <div class="etapa-info">
                                    <i class="fas fa-step-forward"></i>
                                    <strong>${etapa.codigo_etapa}</strong>
                                    <span>${limitarTexto(etapa.nome_etapa, 80)}</span>
                                </div>
                                <div class="etapa-actions">
                                    <i class="fas fa-chevron-down etapa-arrow"></i>
                                </div>
                            </div>
                            <div class="etapa-body" style="display: none;">
                                <div class="riscos-container" id="riscos-etapa-${etapa.id}">
                                    <div class="loading-small">Carregando riscos...</div>
                                </div>
                            </div>
                        </div>
                    `;
                }
            } else {
                htmlFinal += `
                    <div class="empty-etapas">
                        <i class="fas fa-info-circle"></i> Nenhuma etapa cadastrada para este processo.
                    </div>
                `;
            }

            htmlFinal += `
                        </div>
                    </div>
                </div>
            `;
        }

        etapasContainer.innerHTML = htmlFinal;

        // Buscar contagem de controles
        document.querySelectorAll('.etapa-card').forEach(async (card) => {
            const etapaId = card.getAttribute('data-etapa-id');
            try {
                const resp = await fetchComAutenticacao(`/api/etapa/${etapaId}/controles/count`);
                const data = await resp.json();
                if (data.success && data.total > 0) {
                    const header = card.querySelector('.etapa-info');
                    const badge = document.createElement('span');
                    badge.className = 'etapa-controles-badge';
                    badge.innerHTML = `<i class="fas fa-shield-alt"></i> ${data.total}`;
                    badge.title = `${data.total} controle(s) cadastrado(s)`;
                    header.appendChild(badge);
                }
            } catch(e) {}
        });

    } catch (error) {
        console.error('❌ Erro ao carregar etapas:', error);
        etapasContainer.innerHTML = `
            <div class="alert-error" style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle"></i> Erro ao carregar etapas. Tente novamente.
            </div>
        `;
    }
}

// ====== FUNÇÃO PARA CARREGAR RISCOS DE UMA ETAPA (CORRIGIDO) ======
export async function carregarRiscosDaEtapa(etapaId) {
    console.log(`🔍 Buscando riscos da etapa ${etapaId}...`);

    const container = document.getElementById(`riscos-etapa-${etapaId}`);
    if (!container) return;

    try {
        const response = await fetchComAutenticacao(`/api/etapa/${etapaId}/riscos`);
        const data = await response.json();

        console.log(`📦 Riscos encontrados:`, data);

        if (!data.success || !data.riscos || data.riscos.length === 0) {
            container.innerHTML = `
                <div class="empty-riscos">
                    <i class="fas fa-info-circle"></i> Nenhum risco cadastrado para esta etapa.
                </div>
            `;
            return;
        }

        const promessasContagem = [];
        for (const risco of data.riscos) {
            const promessa = fetchComAutenticacao(`/api/risco/${risco.id}/controles/count`)
                .then(res => res.json())
                .then(data => ({
                    id: risco.id,
                    total: data.success ? data.total : 0
                }))
                .catch(() => ({ id: risco.id, total: 0 }));
            promessasContagem.push(promessa);
        }

        const contagens = await Promise.all(promessasContagem);
        const mapaContagens = {};
        contagens.forEach(cont => {
            mapaContagens[cont.id] = cont.total;
        });

        let riscosHtml = '';

        for (const risco of data.riscos) {
            const totalControles = mapaContagens[risco.id] || 0;
            
            // ⭐ Garantir que os valores estejam em maiúsculas
            const impacto = (risco.impacto || 'MÉDIO').toUpperCase();
            const probabilidade = (risco.probabilidade || 'MÉDIO').toUpperCase();
            
            let badgeClass = '';
            let badgeIcon = '';

            if (risco.magnitude <= 3) {
                badgeClass = 'risco-baixo';
                badgeIcon = '🟢';
            } else if (risco.magnitude <= 7) {
                badgeClass = 'risco-medio';
                badgeIcon = '🟡';
            } else if (risco.magnitude <= 11) {
                badgeClass = 'risco-alto';
                badgeIcon = '🟠';
            } else {
                badgeClass = 'risco-critico';
                badgeIcon = '🔴';
            }

            const controlesBadge = `
                <span class="risco-controles-badge" title="${totalControles} controle(s) cadastrado(s)">
                    <i class="fas fa-shield-alt"></i> ${totalControles}
                </span>
            `;

            // ⭐ Garantir que fator_risco e consequencia estejam em maiúsculas
            const fatorRisco = (risco.fator_risco || '').toUpperCase();
            const consequencia = (risco.consequencia || '').toUpperCase();

            riscosHtml += `
                <div class="risco-card ${badgeClass}" data-risco-id="${risco.id}" data-risco-nome="${escapeHtml(risco.nome_risco)}" onclick="toggleRisco(this, event)" style="position: relative;">
                    <div class="risco-header">
                        <div class="risco-info">
                            <span class="risco-icon">${badgeIcon}</span>
                            <strong class="risco-nome">${limitarTexto(escapeHtml(risco.nome_risco), 60)}</strong>
                            <span class="risco-score">Magnitude: ${risco.magnitude}</span>
                            ${controlesBadge}
                        </div>
                        <div class="risco-actions">
                            <span class="expandir-hint" title="Clique para ver controles">
                                <i class="fas fa-chevron-down"></i> Controles
                            </span>
                            <button class="btn-add-controle" 
                                onclick="event.stopPropagation(); abrirModalControle(${risco.id}, '${escapeHtml(risco.nome_risco)}', ${etapaId}, '${escapeHtml(fatorRisco)}')" 
                                title="Adicionar Controle">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                    <div class="risco-detalhes">
                        <div class="risco-detalhe">
                            <span class="detalhe-label">Nome do Risco:</span>
                            <span class="detalhe-valor">${escapeHtml(risco.nome_risco)}</span>
                        </div>
                        <div class="risco-detalhe">
                            <span class="detalhe-label">Impacto financeiro:</span>
                            <span class="detalhe-valor">${impacto}</span>
                        </div>
                        <div class="risco-detalhe">
                            <span class="detalhe-label">Probabilidade:</span>
                            <span class="detalhe-valor">${probabilidade}</span>
                        </div>
                        ${fatorRisco ? `
                        <div class="risco-detalhe">
                            <span class="detalhe-label">Fator de Risco:</span>
                            <span class="detalhe-valor">${escapeHtml(fatorRisco)}</span>
                        </div>
                        ` : ''}
                        ${consequencia ? `
                        <div class="risco-detalhe">
                            <span class="detalhe-label">Consequência:</span>
                            <span class="detalhe-valor">${escapeHtml(consequencia)}</span>
                        </div>
                        ` : ''}
                        
                        <div class="controles-section">
                            <div class="controles-header">
                                <span class="controles-titulo"><i class="fas fa-shield-alt"></i> Controles</span>
                            </div>
                            <div class="controles-container" id="controles-risco-${risco.id}">
                                <div class="loading-small">Carregando controles...</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        container.innerHTML = riscosHtml;

    } catch (error) {
        console.error('❌ Erro ao carregar riscos:', error);
        container.innerHTML = `
            <div class="error-riscos">
                <i class="fas fa-exclamation-triangle"></i> Erro ao carregar riscos.
            </div>
        `;
    }
}

// ====== FUNÇÃO PARA CARREGAR CONTROLES DE UM RISCO (CORRIGIDO) ======
export async function carregarControlesDoRisco(riscoId, etapaId) {
    const container = document.getElementById(`controles-risco-${riscoId}`);
    if (!container) return;

    try {
        const response = await fetchComAutenticacao(`/api/risco/${riscoId}/controles`);
        const data = await response.json();

        if (!data.success || !data.controles || data.controles.length === 0) {
            container.innerHTML = `
                <div class="empty-controles">
                    <i class="fas fa-info-circle"></i> Nenhum controle cadastrado para este risco.
                </div>
            `;
            return;
        }

        let controlesHtml = '';

        for (const controle of data.controles) {
            // ⭐ Garantir que todos os campos de texto estejam em maiúsculas
            const nomeControle = (controle.nome_controle || '').toUpperCase();
            const causaMotivo = (controle.causa_motivo || '').toUpperCase();
            const comoExecutado = (controle.como_executado || '').toUpperCase();
            const objetivoControle = (controle.objetivo_controle || '').toUpperCase();
            const periodicidade = (controle.periodicidade_execucao || '').toUpperCase();
            const evidencia = (controle.evidencia_realizacao || '').toUpperCase();
            const localEvidencia = (controle.local_evidencia || '').toUpperCase();
            const formaExecucao = (controle.forma_execucao || '').toUpperCase();
            const natureza = (controle.natureza || '').toUpperCase();
            const lgpd = (controle.lgpd || '').toUpperCase();
            const statusControle = (controle.status_controle || '').toUpperCase();
            const frequenciaEvidencia = (controle.frequencia_evidencia || '').toUpperCase();
            const responsaveis = (controle.responsaveis_tratamento || '').toUpperCase();

            controlesHtml += `
                <div class="controle-card">
                    <div class="controle-header">
                        <div class="controle-info">
                            <i class="fas fa-shield-alt"></i>
                            <strong>${escapeHtml(nomeControle)}</strong>
                        </div>
                        <div class="controle-actions">
                            <button class="btn-edit-icon" onclick="event.stopPropagation(); editarControle(${controle.id}, ${riscoId})" title="Editar Controle">
                                <i class="fas fa-pencil-alt"></i>
                            </button>
                            <button class="btn-delete-icon" onclick="event.stopPropagation(); excluirControle(${controle.id}, '${escapeHtml(nomeControle)}', ${riscoId}, ${etapaId})" title="Excluir Controle">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                    </div>
                    <div class="controle-detalhes">
                        ${causaMotivo ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Fator de Risco:</span>
                            <span class="detalhe-valor">${escapeHtml(causaMotivo)}</span>
                        </div>` : ''}
                        ${comoExecutado ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Como é executado:</span>
                            <span class="detalhe-valor">${escapeHtml(comoExecutado)}</span>
                        </div>` : ''}
                        ${objetivoControle ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Objetivo:</span>
                            <span class="detalhe-valor">${escapeHtml(objetivoControle)}</span>
                        </div>` : ''}
                        ${periodicidade ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Frequência da execução:</span>
                            <span class="detalhe-valor">${periodicidade}</span>
                        </div>` : ''}
                        ${evidencia ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Evidência:</span>
                            <span class="detalhe-valor">${escapeHtml(evidencia)}</span>
                        </div>` : ''}
                        ${localEvidencia ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Local da Evidência:</span>
                            <span class="detalhe-valor">${escapeHtml(localEvidencia)}</span>
                        </div>` : ''}
                        ${formaExecucao ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Forma de Execução:</span>
                            <span class="detalhe-valor">${formaExecucao}</span>
                        </div>` : ''}
                        ${natureza ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Natureza:</span>
                            <span class="detalhe-valor">${natureza}</span>
                        </div>` : ''}
                        ${lgpd ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">LGPD:</span>
                            <span class="detalhe-valor">${escapeHtml(lgpd)}</span>
                        </div>` : ''}
                        ${statusControle ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Status:</span>
                            <span class="detalhe-valor">${statusControle}</span>
                        </div>` : ''}
                        ${frequenciaEvidencia ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Frequência da Evidência:</span>
                            <span class="detalhe-valor">${frequenciaEvidencia}</span>
                        </div>` : ''}
                        ${responsaveis ? `
                        <div class="controle-detalhe">
                            <span class="detalhe-label">Responsável:</span>
                            <span class="detalhe-valor">${escapeHtml(responsaveis)}</span>
                        </div>` : ''}
                    </div>
                </div>
            `;
        }

        container.innerHTML = controlesHtml;

    } catch (error) {
        console.error('❌ Erro ao carregar controles:', error);
        container.innerHTML = `
            <div class="error-controles">
                <i class="fas fa-exclamation-triangle"></i> Erro ao carregar controles.
            </div>
        `;
    }
}

// ====== FUNÇÕES DE EXPANSÃO ======
export function toggleProcesso(header) {
    const processoCard = header.closest('.processo-card');
    const body = processoCard.querySelector('.processo-body');
    const arrow = header.querySelector('.processo-arrow');

    if (body.style.display === 'none') {
        body.style.display = 'block';
        if (arrow) arrow.classList.add('open');
    } else {
        body.style.display = 'none';
        if (arrow) arrow.classList.remove('open');
    }
}

export function toggleEtapa(header) {
    const etapaCard = header.closest('.etapa-card');
    const body = etapaCard.querySelector('.etapa-body');
    const arrow = header.querySelector('.etapa-arrow');
    const etapaId = etapaCard.getAttribute('data-etapa-id');

    if (body.style.display === 'none') {
        body.style.display = 'block';
        if (arrow) arrow.classList.add('open');

        const riscosContainer = body.querySelector('.riscos-container');
        if (riscosContainer && riscosContainer.innerHTML.includes('Carregando riscos')) {
            carregarRiscosDaEtapa(etapaId);
        }
    } else {
        body.style.display = 'none';
        if (arrow) arrow.classList.remove('open');
    }
}

// ====== FUNÇÃO PARA EXPANDIR RISCO ======
export function toggleRisco(riscoCard, event) {
    if (event.target.closest('.btn-edit-icon') || 
        event.target.closest('.btn-delete-icon') ||
        event.target.closest('.btn-add-controle')) {
        return;
    }

    const wasExpanded = riscoCard.classList.contains('expandido');
    riscoCard.classList.toggle('expandido');

    if (!wasExpanded) {
        const riscoId = riscoCard.getAttribute('data-risco-id');
        const etapaCard = riscoCard.closest('.etapa-card');
        const etapaId = etapaCard.getAttribute('data-etapa-id');
        
        const controlesContainer = riscoCard.querySelector('.controles-container');
        if (controlesContainer && controlesContainer.innerHTML.includes('Carregando controles')) {
            carregarControlesDoRisco(riscoId, etapaId);
        }
    }
}

// ====== FUNÇÕES PARA ATUALIZAR BADGES ======
export async function atualizarBadgeControles(riscoId) {
    try {
        const response = await fetchComAutenticacao(`/api/risco/${riscoId}/controles/count`);
        const data = await response.json();
        
        if (data.success) {
            const riscoCard = document.querySelector(`.risco-card[data-risco-id="${riscoId}"]`);
            if (riscoCard) {
                const riscoInfo = riscoCard.querySelector('.risco-info');
                const existingBadge = riscoInfo.querySelector('.risco-controles-badge');
                const total = data.total || 0;
                
                const newBadge = document.createElement('span');
                newBadge.className = 'risco-controles-badge';
                newBadge.title = `${total} controle(s) cadastrado(s)`;
                newBadge.innerHTML = `<i class="fas fa-shield-alt"></i> ${total}`;
                
                if (existingBadge) {
                    existingBadge.replaceWith(newBadge);
                } else {
                    riscoInfo.appendChild(newBadge);
                }
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar badge do risco:', error);
    }
}

export async function atualizarBadgeEtapaControles(etapaId) {
    try {
        const response = await fetchComAutenticacao(`/api/etapa/${etapaId}/controles/count`);
        const data = await response.json();
        
        if (data.success) {
            const etapaCard = document.querySelector(`.etapa-card[data-etapa-id="${etapaId}"]`);
            if (etapaCard) {
                const etapaInfo = etapaCard.querySelector('.etapa-info');
                const existingBadge = etapaInfo.querySelector('.etapa-controles-badge');
                const total = data.total || 0;
                
                if (total > 0) {
                    const newBadge = document.createElement('span');
                    newBadge.className = 'etapa-controles-badge';
                    newBadge.title = `${total} controle(s) cadastrado(s) nesta etapa`;
                    newBadge.innerHTML = `<i class="fas fa-shield-alt"></i> ${total}`;
                    
                    if (existingBadge) {
                        existingBadge.replaceWith(newBadge);
                    } else {
                        etapaInfo.appendChild(newBadge);
                    }
                } else {
                    if (existingBadge) {
                        existingBadge.remove();
                    }
                }
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar badge da etapa:', error);
    }
}

export async function excluirControle(controleId, nomeControle, riscoId, etapaId) {
    if (!confirm(`Tem certeza que deseja excluir o controle "${nomeControle}"?`)) return;
    
    try {
        const response = await fetchComAutenticacao(`/api/controle-etapa/${controleId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const resultado = await response.json();
        
        if (resultado.success) {
            mostrarToast('✅ Controle excluído com sucesso!', 'success');
            await carregarControlesDoRisco(riscoId, etapaId);
            await atualizarBadgeControles(riscoId);
            if (etapaId) {
                await atualizarBadgeEtapaControles(etapaId);
            }
        } else {
            mostrarToast('❌ Erro ao excluir: ' + (resultado.error || 'Tente novamente'), 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao excluir controle:', error);
        mostrarToast('❌ Erro de conexão. Tente novamente.', 'error');
    }
}