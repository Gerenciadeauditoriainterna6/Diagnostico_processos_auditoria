const EtapasRiscosModule = {
    
    container: null,
    auditoriaIdAtual: null,
    
    init() {
        this.container = document.getElementById('etapas-container');
        
        document.addEventListener('click', (e) => {
            // Botão Editar
            const btnEdit = e.target.closest('.btn-edit-icon');
            if (btnEdit) {
                e.stopPropagation();  // ⭐ Impede que o card expanda
                const riscoId = btnEdit.dataset.riscoId;
                const etapaId = btnEdit.dataset.etapaId;
                const codigo = btnEdit.dataset.codigo;
                const nome = btnEdit.dataset.nome;
                ModalRiscoEtapaModule.editar(riscoId, etapaId, codigo, nome, EtapasRiscosModule.auditoriaIdAtual);
                return;  // ⭐ Sair para não verificar outros botões
            }
            
            // Botão Excluir
            const btnDelete = e.target.closest('.btn-delete-icon');
            if (btnDelete) {
                e.stopPropagation();  // ⭐
                const riscoId = btnDelete.dataset.riscoId;
                const nomeRisco = btnDelete.dataset.nomeRisco;
                const etapaId = btnDelete.dataset.etapaId;
                const codigo = btnDelete.dataset.codigo;
                const nome = btnDelete.dataset.nome;
                ModalRiscoEtapaModule.excluir(riscoId, nomeRisco, etapaId, codigo, nome, EtapasRiscosModule.auditoriaIdAtual);
                return;
            }
            
            // Botão Toggle Status
            const btnToggle = e.target.closest('.btn-toggle-status');
            if (btnToggle) {
                e.stopPropagation();  // ⭐
                const riscoId = btnToggle.dataset.riscoId;
                const novoStatus = btnToggle.dataset.novoStatus === 'true';
                const etapaId = btnToggle.dataset.etapaId;
                const codigo = btnToggle.dataset.codigo;
                const nome = btnToggle.dataset.nome;
                EtapasRiscosModule.alternarStatusRisco(riscoId, novoStatus, etapaId, codigo, nome);
                return;
            }
        });
    },
    
    limpar() {
        if (this.container) {
            this.container.innerHTML = '<div class="alert-info">Selecione uma auditoria...</div>';
        }
    },
    
    async carregarEtapas(auditoriaId) {
        console.log('📋 Carregando etapas para auditoria:', auditoriaId);

        this.auditoriaIdAtual = auditoriaId

        this.container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div class="dot-spinner">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando etapas e seus riscos...</p>
            </div>
        `;

        try {
            const responseProcessos = await fetchComAutenticacao(`/api/processos-por-auditoria?auditoria_id=${auditoriaId}`);
            const dataProcessos = await responseProcessos.json();

            if (!dataProcessos.success || !dataProcessos.processos || dataProcessos.processos.length === 0) {
                this.container.innerHTML = `
                    <div class="alert-info" style="text-align: center; padding: 40px;">
                        <i class="fas fa-info-circle"></i> Nenhum processo encontrado para esta auditoria
                    </div>
                `;
                return;
            }

            let htmlFinal = '';

            for (const processo of dataProcessos.processos) {
                const responseEtapas = await fetchComAutenticacao(`/api/processo/${processo.id}/etapas`);
                const dataEtapas = await responseEtapas.json();

                htmlFinal += `
                    <div class="processo-card" data-processo-id="${processo.id}">
                        <div class="processo-header" onclick="EtapasRiscosModule.toggleProcesso(this)">
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
                    const promessasContagem = [];
                    const etapasTemp = [];

                    for (const etapa of dataEtapas.etapas) {
                        etapasTemp.push(etapa);

                        const promessa = fetchComAutenticacao(`/api/etapa/${etapa.id}/riscos/count`)
                            .then(res => res.json())
                            .then(data => ({
                                id: etapa.id,
                                total: data.success ? data.total : 0
                            }))
                            .catch(error => {
                                console.error(`Erro ao contar riscos da etapa ${etapa.id}:`, error);
                                return { id: etapa.id, total: 0 };
                            });

                        promessasContagem.push(promessa);
                    }

                    const contagens = await Promise.all(promessasContagem);

                    const mapaContagens = {};
                    contagens.forEach(cont => {
                        mapaContagens[cont.id] = cont.total;
                    });

                    for (const etapa of etapasTemp) {
                        const totalRiscos = mapaContagens[etapa.id] || 0;

                        htmlFinal += `
                            <div class="etapa-card" data-etapa-id="${etapa.id}">
                                <div class="etapa-header" onclick="EtapasRiscosModule.toggleEtapa(this)">
                                    <div class="etapa-info">
                                        <i class="fas fa-step-forward"></i>
                                        <strong>${etapa.codigo_etapa}</strong>
                                        <span>${EtapasRiscosModule.limitarTexto(etapa.nome_etapa, 50)}</span>
                                        <span class="badge-riscos" title="${totalRiscos} risco(s) cadastrado(s)">
                                            <i class="fas fa-exclamation-triangle"></i> ${totalRiscos}
                                        </span>
                                    </div>
                                    <div class="etapa-actions">
                                        <button class="btn-add-risco" onclick="event.stopPropagation(); ModalRiscoEtapaModule.abrir(${etapa.id}, '${etapa.codigo_etapa}', '${escapeHtml(etapa.nome_etapa)}', ${this.auditoriaIdAtual})">
                                            <i class="fas fa-plus"></i> Adicionar Risco
                                        </button>
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

            this.container.innerHTML = htmlFinal;

        } catch (error) {
            console.error('❌ Erro ao carregar etapas:', error);
            this.container.innerHTML = `
                <div class="alert-error" style="text-align: center; padding: 40px;">
                    <i class="fas fa-exclamation-triangle"></i> Erro ao carregar etapas. Tente novamente.
                </div>
            `;
        }
    },

    async carregarRiscosDaEtapa(etapaId, codigoEtapa, nomeEtapa) {
        console.log(`🔍 Buscando riscos da etapa ${etapaId}...`);

        const container = document.getElementById(`riscos-etapa-${etapaId}`);
        if (!container) return;

        try {
            const response = await fetchComAutenticacao(`/api/etapa/${etapaId}/riscos/todos`);
            const data = await response.json();

            if (!data.success || !data.riscos || data.riscos.length === 0) {
                container.innerHTML = `
                    <div class="empty-riscos">
                        <i class="fas fa-info-circle"></i> Nenhum risco cadastrado para esta etapa.
                    </div>
                `;
                return;
            }

            let riscosHtml = '';

            for (const risco of data.riscos) {
                // ⭐ Garantir que os valores estejam em maiúsculas para exibição
                const impacto = (risco.impacto || 'MÉDIO').toUpperCase();
                const probabilidade = (risco.probabilidade || 'MÉDIO').toUpperCase();
                const tratamento = (risco.tratamento || '').toUpperCase();
                
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

                const isAtivo = risco.ativo !== false;
                const statusBadge = isAtivo ?
                    `<span class="status-badge status-ativo" title="Risco Ativo">
                        <i class="fas fa-circle"></i> ATIVO
                    </span>` :
                    `<span class="status-badge status-inativo" title="Risco Inativo">
                        <i class="fas fa-circle"></i> INATIVO
                    </span>`;

                // ⭐ Garantir que categorias estejam em maiúsculas
                const categoriasLista = risco.categoria ? risco.categoria.split(', ').map(c => c.toUpperCase()) : [];
                const causasLista = risco.causas || [];

                const categoriasHtml = categoriasLista.map(cat =>
                    `<span class="risco-categoria-tag">${escapeHtml(cat)}</span>`
                ).join('');

                const causasHtml = causasLista.map(causa =>
                    `<span class="risco-causa-tag">${escapeHtml(causa)}</span>`
                ).join('');

                const toggleIcon = isAtivo ? 'fa-pause-circle' : 'fa-play-circle';
                const toggleTitle = isAtivo ? 'Desativar Risco' : 'Ativar Risco';

                // ⭐ Garantir que a origem esteja em maiúsculas
                const origem = (risco.origem || '').toUpperCase();
                const fatorRisco = (risco.fator_risco || '').toUpperCase();
                const consequencia = (risco.consequencia || '').toUpperCase();

                riscosHtml += `
                    <div class="risco-mini-card ${badgeClass}" data-risco-id="${risco.id}" 
                        onclick="EtapasRiscosModule.toggleDetalhesRisco(this)" 
                        title="Clique para ver detalhes">
                        
                        <!-- Indicador de severidade + nome -->
                        <div class="mini-card-top">
                            <span class="mini-icone">${badgeIcon}</span>
                            <span class="mini-nome">${escapeHtml(risco.nome_risco)}</span>
                        </div>
                        
                        <!-- Magnitude + Status -->
                        <div class="mini-card-middle">
                            <span class="mini-magnitude">Magnitude: ${risco.magnitude}</span>
                            ${statusBadge}
                        </div>
                        
                        <!-- Categorias (resumido) -->
                        ${categoriasLista.length > 0 ? `
                        <div class="mini-card-tags">
                            ${categoriasLista.slice(0, 2).map(cat => 
                                `<span class="risco-categoria-tag">${escapeHtml(cat)}</span>`
                            ).join('')}
                            ${categoriasLista.length > 2 ? `<span class="mini-mais-tags">+${categoriasLista.length - 2}</span>` : ''}
                        </div>
                        ` : ''}
                        
                        <!-- Botões de ação -->
                        <div class="mini-card-actions">
                            <button class="btn-edit-icon" 
                                data-risco-id="${risco.id}" data-etapa-id="${etapaId}" 
                                data-codigo="${codigoEtapa}" data-nome="${escapeHtml(nomeEtapa)}" 
                                title="Editar">
                                <i class="fas fa-pencil-alt"></i>
                            </button>
                            <button class="btn-delete-icon" 
                                data-risco-id="${risco.id}" data-nome-risco="${escapeHtml(risco.nome_risco)}" 
                                data-etapa-id="${etapaId}" data-codigo="${codigoEtapa}" 
                                data-nome="${escapeHtml(nomeEtapa)}" title="Excluir">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                            <button class="btn-toggle-status" 
                                data-risco-id="${risco.id}" data-novo-status="${!isAtivo}" 
                                data-etapa-id="${etapaId}" data-codigo="${codigoEtapa}" 
                                data-nome="${escapeHtml(nomeEtapa)}" title="${isAtivo ? 'Desativar' : 'Ativar'}">
                                <i class="fas ${toggleIcon}"></i>
                            </button>
                        </div>
                        
                        <!-- Detalhes (escondidos por padrão, mostram ao clicar) -->
                        <div class="mini-card-detalhes" style="display: none;">
                            <div class="mini-detalhe-grid">
                                ${risco.categoria ? `<div class="mini-detalhe"><strong>Categorias:</strong> ${categoriasHtml}</div>` : ''}
                                ${risco.causas && risco.causas.length > 0 ? `<div class="mini-detalhe"><strong>Causas:</strong> ${causasHtml}</div>` : ''}
                                <div class="mini-detalhe"><strong>Fator de Risco:</strong> ${escapeHtml(fatorRisco) || '-'}</div>
                                <div class="mini-detalhe"><strong>Consequência:</strong> ${escapeHtml(consequencia) || '-'}</div>
                                <div class="mini-detalhe"><strong>Origem:</strong> ${escapeHtml(origem) || '-'}</div>
                                <div class="mini-detalhe"><strong>Impacto:</strong> ${impacto} | <strong>Prob:</strong> ${probabilidade}</div>
                                <div class="mini-detalhe"><strong>Motivo:</strong> ${escapeHtml(risco.motivo_classificacao || '').toUpperCase() || '-'}</div>
                                <div class="mini-detalhe"><strong>Apetite:</strong> I: ${escapeHtml(risco.impacto_aceitavel || '-')} | P: ${escapeHtml(risco.probabilidade_aceitavel || '-')}</div>
                                ${risco.tratamento ? `<div class="mini-detalhe"><strong>Tratamento:</strong> ${tratamento}</div>` : ''}
                                ${risco.financeiro !== null ? `<div class="mini-detalhe"><strong>Financeiro:</strong> ${risco.financeiro ? 'SIM' : 'NÃO'}</div>` : ''}
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
    },

    toggleProcesso(header) {
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
    },

    toggleEtapa(header) {
        const etapaCard = header.closest('.etapa-card');
        const body = etapaCard.querySelector('.etapa-body');
        const arrow = header.querySelector('.etapa-arrow');
        const etapaId = etapaCard.getAttribute('data-etapa-id');

        if (body.style.display === 'none') {
            body.style.display = 'block';
            if (arrow) arrow.classList.add('open');

            const riscosContainer = body.querySelector(`.riscos-container`);
            if (riscosContainer && riscosContainer.innerHTML.includes('Carregando riscos')) {
                const etapaCard = header.closest('.etapa-card');
                const codigoEtapa = etapaCard.querySelector('.etapa-info strong')?.textContent || '';
                const nomeEtapa = etapaCard.querySelector('.etapa-info span')?.textContent || '';
                this.carregarRiscosDaEtapa(etapaId, codigoEtapa, nomeEtapa);
            }
        } else {
            body.style.display = 'none';
            if (arrow) arrow.classList.remove('open');
        }
    },

    limitarTexto(texto, limite = 50) {
        if (!texto) return '';
        if (texto.length <= limite) return texto;
        return texto.substring(0, limite) + '...';
    },

    async atualizarBadgeRiscos(etapaId) {
        try {
            const response = await fetchComAutenticacao(`/api/etapa/${etapaId}/riscos/count`);
            const data = await response.json();

            if (data.success) {
                const etapaCard = document.querySelector(`.etapa-card[data-etapa-id="${etapaId}"]`);
                if (etapaCard) {
                    const etapaInfo = etapaCard.querySelector('.etapa-info');
                    const existingBadge = etapaInfo.querySelector('.badge-riscos');
                    const total = data.total || 0;

                    const newBadge = document.createElement('span');
                    newBadge.className = 'badge-riscos';
                    newBadge.title = `${total} risco(s) cadastrado(s)`;
                    newBadge.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${total}`;

                    if (existingBadge) {
                        existingBadge.replaceWith(newBadge);
                    } else {
                        etapaInfo.appendChild(newBadge);
                    }
                }
            }
        } catch (error) {
            console.error('Erro ao atualizar badge:', error);
        }
    },

    async alternarStatusRisco(riscoId, novoStatus, etapaId, codigoEtapa, nomeEtapa) {
        const statusTexto = novoStatus ? 'ATIVAR' : 'DESATIVAR';
        const confirmado = confirm(`Tem certeza que deseja ${statusTexto} este risco?`);

        if (!confirmado) return;

        try {
            const btn = document.querySelector(`.risco-card[data-risco-id="${riscoId}"] .btn-toggle-status i`);
            if (btn) {
                btn.className = 'fas fa-spinner fa-spin';
            }

            const response = await fetchComAutenticacao(`/api/risco-etapa/${riscoId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ativo: novoStatus
                })
            });

            const resultado = await response.json();

            if (resultado.success) {
                window.mostrarToast(`✅ Risco ${novoStatus ? 'ativado' : 'desativado'} com sucesso!`, 'success');
                await this.carregarRiscosDaEtapa(etapaId, codigoEtapa, nomeEtapa);
                await this.atualizarBadgeRiscos(etapaId);
            } else {
                window.mostrarToast('❌ Erro ao alterar status: ' + (resultado.error || 'Tente novamente'), 'error');
            }
        } catch (error) {
            console.error('❌ Erro ao alterar status:', error);
            window.mostrarToast('❌ Erro de conexão. Tente novamente.', 'error');
        }
    },

    toggleDetalhesRisco(card) {
        // Pega a div de detalhes dentro do card clicado
        const detalhes = card.querySelector('.mini-card-detalhes');
        
        if (detalhes) {
            // Se está escondido, mostra. Se está visível, esconde.
            if (detalhes.style.display === 'none') {
                detalhes.style.display = 'block';
            } else {
                detalhes.style.display = 'none';
            }
        }
    },

};