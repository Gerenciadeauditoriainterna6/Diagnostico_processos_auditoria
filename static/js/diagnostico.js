
// ===== RESTAURAR FILTROS SALVOS =====
function restaurarFiltros() {
    const areaSalva = sessionStorage.getItem('filtro_area_id');
    const auditoriaSalva = sessionStorage.getItem('filtro_auditoria_id');
    
    console.log('🔄 Restaurando filtros - Área:', areaSalva, 'Auditoria:', auditoriaSalva);
    
    // Restaurar área se existir
    if (areaSalva && filtroAreaSelect) {
        let optionExists = false;
        for (let i = 0; i < filtroAreaSelect.options.length; i++) {
            if (filtroAreaSelect.options[i].value == areaSalva) {
                optionExists = true;
                break;
            }
        }
        
        if (optionExists) {
            filtroAreaSelect.value = areaSalva;
            
            // ⭐ CARREGAR AUDITORIAS COM A SELECIONADA
            carregarAuditoriasFiltro(areaSalva, auditoriaSalva || null);
            
            // Carregar tabela
            if (areaSalva) {
                carregarTabelaProcessos(auditoriaSalva || null, areaSalva);
            }
        }
    }
}

// MONITOR DE REMOÇÃO DO sessionStorage
const originalRemoveItem = sessionStorage.removeItem;
sessionStorage.removeItem = function(key) {
    if (key === 'processo_id') {
        console.trace('🔴 sessionStorage.removeItem("processo_id") foi chamado!');
        console.log('Stack trace da remoção:');
    }
    return originalRemoveItem.apply(this, arguments);
};
let usuarioAutorizado = false;

// ====== ELEMENTOS DA PÁGINA PRINCIPAL ======
const filtroAreaSelect = document.getElementById('filtro_area_select');
const filtroAuditoriaSelect = document.getElementById('filtro_auditoria_select');
const btnNovoProcesso = document.getElementById('btn-novo-processo');
const modalWizard = document.getElementById('modal-wizard');
const btnFecharWizard = document.getElementById('btn-fechar-wizard')
const tabelaProcessosContainer = document.getElementById('tabela-processos-container');

if (btnNovoProcesso) {
    btnNovoProcesso.addEventListener('click', abrirModalNovoProcesso);
    console.log('✅ Evento do botão Novo Processo conectado');
}

// ===== ABRIR MODAL PARA NOVO PROCESSO =====
function abrirModalNovoProcesso() {
    console.log('abrirModalNovoProcesso foi chamado!')

    // Resetar sessionStorage para não restaurar dados antigos
    sessionStorage.removeItem('processo_id');
    sessionStorage.removeItem('auditoria_id');
    sessionStorage.removeItem('modo_edicao');
    sessionStorage.removeItem('etapa_atual');
    sessionStorage.removeItem('detalhes_temp');
    sessionStorage.removeItem('riscos_temp');
    
    // Resetar variáveis globais
    riscosLista = [];
    executoresSelecionados = [];
    
    // Resetar campos da etapa 3
    resetarCamposDetalhes();

    // Resetar campo nome do processo
    if (nomeProcessoInput) {
        nomeProcessoInput.value = '';
    }

    // Resetar campo do código do processo
    if(codigoProcessoInput) {
        codigoProcessoInput.value = '';
    }
    
    // Resetar badges e lista de funcionários
    atualizarBadges();
    
    // ===== HERDAR OS VALORES DO FILTRO =====
    const areaFiltro = filtroAreaSelect.value;
    const auditoriaFiltro = filtroAuditoriaSelect.value;
    const areaNomeFiltro = filtroAreaSelect.options[filtroAreaSelect.selectedIndex]?.text || '';
    
    // Preencher área no modal
    if (areaSelect && areaFiltro) {
        areaSelect.value = areaFiltro;
        // Disparar evento change para carregar funcionários e auditorias
        const changeEvent = new Event('change');
        areaSelect.dispatchEvent(changeEvent);
    }
    
    // Aguardar o carregamento das auditorias e preencher
    setTimeout(() => {
        if (auditoriaSelect && auditoriaFiltro) {
            // Verificar se a opção existe no select
            let optionExists = false;
            for (let i = 0; i < auditoriaSelect.options.length; i++) {
                if (auditoriaSelect.options[i].value == auditoriaFiltro) {
                    optionExists = true;
                    break;
                }
            }
            
            if (optionExists) {
                auditoriaSelect.value = auditoriaFiltro;
                // Disparar evento change para validar responsável
                const auditEvent = new Event('change');
                auditoriaSelect.dispatchEvent(auditEvent);
            }
        }
    }, 500); // Aguardar as auditorias carregarem
    
    // Garantir que estamos na etapa 1
    irParaEtapa(1);
    
    // Mostrar o modal
    if (modalWizard) modalWizard.style.display = 'flex';
}

// ===== FECHAR MODAL WIZARD COM LIMPEZA COMPLETA =====
function fecharModalWizard() {
    if (modalWizard) {
        modalWizard.style.display = 'none';
    }
    
    // ⭐ LIMPEZA COMPLETA AO FECHAR O MODAL
    // Isso evita que dados antigos interfiram na próxima abertura
    setTimeout(() => {
        // Resetar variáveis globais
        riscosLista = [];
        executoresSelecionados = [];
        
        // Limpar sessionStorage (mantendo apenas filtros)
        const areaSalva = sessionStorage.getItem('filtro_area_id');
        const auditoriaSalva = sessionStorage.getItem('filtro_auditoria_id');
        
        sessionStorage.removeItem('processo_id');
        sessionStorage.removeItem('auditoria_id');
        sessionStorage.removeItem('modo_edicao');
        sessionStorage.removeItem('etapa_atual');
        sessionStorage.removeItem('detalhes_temp');
        sessionStorage.removeItem('riscos_temp');
        sessionStorage.removeItem('area_id_selecionada');
        
        // Restaurar filtros
        if (areaSalva) {
            sessionStorage.setItem('filtro_area_id', areaSalva);
        }
        if (auditoriaSalva) {
            sessionStorage.setItem('filtro_auditoria_id', auditoriaSalva);
        }
        
        // Resetar campos
        resetarCamposDetalhes();
        if (nomeProcessoInput) nomeProcessoInput.value = '';
        if (codigoProcessoInput) codigoProcessoInput.value = '';
        atualizarBadges();
        
        // Resetar selects do wizard
        if (areaSelect) areaSelect.value = '';
        if (auditoriaSelect) {
            auditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            auditoriaSelect.value = '';
        }
        
        // Esconder o inner da auditoria
        const auditoriaInner = document.getElementById('auditoria-inner');
        if (auditoriaInner) {
            auditoriaInner.style.display = 'none';
        }
        
        // Desabilitar botão próximo
        habilitarProximoEtapa1(false);
        
        // Remover avisos
        removerAvisoProcessoExistente();
        
        // Resetar lista de funcionários
        funcionariosDisponiveis = [];
        const listaDiv = document.getElementById('lista-funcionarios');
        if (listaDiv) {
            listaDiv.innerHTML = '<div class="loading-message">Carregando funcionários...</div>';
        }
        const totalSpan = document.getElementById('total-funcionarios');
        if (totalSpan) totalSpan.textContent = '0';
        
        const entrevistadoInput = document.getElementById('entrevistado_processo');
        if (entrevistadoInput) entrevistadoInput.value = '';
        
        // Ir para etapa 1
        etapaWizard = 1;
        atualizarProgressoWizard(1);
        
        console.log('🧹 Wizard completamente limpo');
    }, 100);
}

// Evento para fechar o modal
if (btnFecharWizard) {
    btnFecharWizard.addEventListener('click', fecharModalWizard);
}

// ===== ABRIR MODAL DE VISUALIZAÇÃO DO PROCESSO =====
async function abrirModalVisualizarProcesso(processoId) {
    const modal = document.getElementById('modal-visualizar-processo');
    const conteudo = document.getElementById('visualizar-processo-conteudo');
    
    modal.style.display = 'flex';
    conteudo.innerHTML = `
        <div style="text-align: center; padding: 60px 20px;">
            <div class="dot-spinner">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando processos...</p>
        </div>
    `;
    
    try {
        // Buscar dados do processo
        const response = await fetchComAutenticacao(`/api/processo/${processoId}/dados`);
        const data = await response.json();
        
        if (data.success) {
            // Buscar riscos do processo
            const riscosResponse = await fetchComAutenticacao(`/api/processo/${processoId}/riscos`);
            const riscosData = await riscosResponse.json();
            console.log('Riscos recebidos do backend (RAW):', riscosData);

            // Tentar encontrar o array de riscos
            let riscosArray = riscosData.riscos || riscosData;
            if (!Array.isArray(riscosArray)) {
                riscosArray = [];
            }
            console.log('Riscos array após normalização:', riscosArray);

            let riscosHtml = '';
            if (riscosArray.length > 0) {
                // Verificar o primeiro risco
                console.log('Primeiro risco:', riscosArray[0]);
                console.log('Propriedades:', Object.keys(riscosArray[0]));
                
                // ⭐ CORREÇÃO: Mapear TODOS os campos, incluindo os de tratamento ⭐
                const riscosFormatados = riscosArray.map(risco => ({
                    id: risco.id,
                    nome_risco: (risco.nome_risco || risco.nome || 'Risco sem nome').toUpperCase(),
                    impacto: (risco.impacto || risco.impact || 'Médio').toUpperCase(),
                    probabilidade: (risco.probabilidade || risco.probability || 'Médio').toUpperCase(),
                    fator_risco: (risco.fator_risco || '').toUpperCase(),
                    melhoria: (risco.melhoria || '').toUpperCase(),
                    apetite_impacto: (risco.apetite_impacto || 'Médio').toUpperCase(),
                    apetite_probabilidade: (risco.apetite_probabilidade || 'Médio').toUpperCase(),
                    motivo_risco: (risco.motivo_risco || '').toUpperCase(),
                    categorias: risco.categorias ? risco.categorias.map(c => c.toUpperCase()) : (risco.categoria ? risco.categoria.split(',').map(c => c.trim().toUpperCase()) : []),
                    categoria_causa: risco.categoria_causa ? risco.categoria_causa.map(c => c.toUpperCase()) : [],
                    como_tratar: (risco.como_tratar || '').toUpperCase(),
                    desc_tratamento: (risco.desc_tratamento || '').toUpperCase(),
                    prazo_implantacao: (risco.prazo_implantacao || '').toUpperCase(),
                    score_risco: risco.score_risco || 0
                }));
                
                console.log('✅ Riscos formatados COM TODOS OS CAMPOS:', riscosFormatados);
                console.log('Primeiro risco - como_tratar:', riscosFormatados[0]?.como_tratar);
                console.log('Primeiro risco - desc_tratamento:', riscosFormatados[0]?.desc_tratamento);
                
                riscosHtml = gerarKanbanVisualizacao(riscosFormatados);
            } else {
                riscosHtml = '<div class="alert-info" style="text-align: center; padding: 20px;"><i class="fas fa-info-circle"></i> Nenhum risco identificado para este processo.</div>';
            }
            
            conteudo.innerHTML = `
                <div class="vis-processo-container">
                    <!-- Informações Básicas -->
                    <div class="vis-secao">
                        <h4><i class="fas fa-tag"></i> Informações Básicas</h4>
                        <div class="vis-grid">
                            <div class="vis-item">
                                <label>Código do Processo</label>
                                <span>${escapeHtml(data.codigo_processo)}</span>
                            </div>
                            <div class="vis-item">
                                <label>Nome do Processo</label>
                                <span>${escapeHtml(data.nome_processo)}</span>
                            </div>
                            <div class="vis-item full-width">
                                <label>Executores</label>
                                <span>${data.executores.map(e => escapeHtml(e.nome)).join(', ') || '-'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Detalhes do Processo -->
                    <div class="vis-secao">
                        <h4><i class="fas fa-clipboard-list"></i> Detalhes do Processo</h4>
                        <div class="vis-grid">
                            <div class="vis-item full-width">
                                <label>O que é o processo?</label>
                                <span>${escapeHtml(data.descricao) || '-'}</span>
                            </div>
                            <div class="vis-item half">
                                <label>Onde começa?</label>
                                <span>${escapeHtml(data.etapa_ini) || '-'}</span>
                            </div>
                            <div class="vis-item half">
                                <label>Produto final</label>
                                <span>${escapeHtml(data.produto) || '-'}</span>
                            </div>
                            <div class="vis-item half">
                                <label>Para onde envia?</label>
                                <span>${escapeHtml(data.etapa_fim) || '-'}</span>
                            </div>
                            <div class="vis-item half">
                                <label>Objetivo</label>
                                <span>${escapeHtml(data.objetivo) || '-'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Riscos Identificados -->
                    <div class="vis-secao">
                        <h4><i class="fas fa-exclamation-triangle"></i> Riscos Identificados</h4>
                        ${riscosHtml}
                    </div>
                </div>
            `;
        } else {
            conteudo.innerHTML = '<div class="alert-error" style="text-align: center; padding: 40px;"><i class="fas fa-exclamation-triangle"></i> Erro ao carregar dados do processo.</div>';
        }
    } catch (error) {
        console.error('Erro:', error);
        conteudo.innerHTML = '<div class="alert-error" style="text-align: center; padding: 40px;"><i class="fas fa-exclamation-triangle"></i> Erro ao carregar dados.</div>';
    }
}

// Função para gerar o Kanban na visualização
function gerarKanbanVisualizacao(riscos) {
    if (!riscos || riscos.length === 0) {
        return '<div class="alert-info" style="text-align: center; padding: 20px;"><i class="fas fa-info-circle"></i> Nenhum risco identificado para este processo.</div>';
    }
    
    // Processar riscos com score e nível
    const riscosProcessados = riscos.map((risco, idx) => {
        // Usar score_risco se existir, senão calcular
        let score = risco.score_risco;
        if (!score && score !== 0) {
            score = calcularScoreRisco(risco.impacto || 'Médio', risco.probabilidade || 'Médio');
        }
        
        // ⭐ CALCULAR SCORE DO APETITE
        const apetiteScore = calcularScoreRisco(
            risco.apetite_impacto || 'Médio', 
            risco.apetite_probabilidade || 'Médio'
        );
        
        // Determinar nível do score do apetite
        let apetiteNivel = '';
        let apetiteNivelTexto = '';
        if (apetiteScore <= 3) {
            apetiteNivel = 'low';
            apetiteNivelTexto = 'BAIXA EXPOSIÇÃO';
        } else if (apetiteScore >= 4 && apetiteScore <= 7) {
            apetiteNivel = 'medium';
            apetiteNivelTexto = 'SOB OBSERVAÇÃO';
        } else if (apetiteScore >= 8 && apetiteScore <= 11) {
            apetiteNivel = 'high';
            apetiteNivelTexto = 'ATENÇÃO';
        } else {
            apetiteNivel = 'critical';
            apetiteNivelTexto = 'CRÍTICO';
        }
        
        // ⭐ CORREÇÃO DOS LIMITES DOS NÍVEIS ⭐
        let nivel = '';
        let nivelTexto = '';
        
        if (score <= 3) { 
            nivel = 'low'; 
            nivelTexto = 'BAIXA EXPOSIÇÃO'; 
        }
        else if (score >= 4 && score <= 7) { 
            nivel = 'medium'; 
            nivelTexto = 'SOB OBSERVAÇÃO'; 
        }
        else if (score >= 8 && score <= 11) { 
            nivel = 'high'; 
            nivelTexto = 'ATENÇÃO'; 
        }
        else { // score >= 12
            nivel = 'critical'; 
            nivelTexto = 'CRÍTICO'; 
        }
        
        // Garantir que categorias seja um array
        let categorias = risco.categorias || [];
        if (typeof categorias === 'string') {
            categorias = categorias.split(',').map(c => c.trim());
        }
        
        return { 
            ...risco, 
            nome_risco: risco.nome_risco || 'Risco sem nome',
            score, 
            nivel, 
            nivelTexto,
            categorias: categorias,
            // ⭐ NOVOS CAMPOS DO APETITE
            apetiteScore: apetiteScore,
            apetiteNivel: apetiteNivel,
            apetiteNivelTexto: apetiteNivelTexto
        };
    });
    
    // Separar por nível
    const baixo = riscosProcessados.filter(r => r.nivel === 'low');
    const medio = riscosProcessados.filter(r => r.nivel === 'medium');
    const alto = riscosProcessados.filter(r => r.nivel === 'high');
    const critico = riscosProcessados.filter(r => r.nivel === 'critical');
    
    // Armazenar riscos globalmente para visualização
    window.riscosVisualizacao = riscosProcessados;

    // Log para debug
    console.log('✅ Riscos processados para visualização:', riscosProcessados);
    console.log('📊 Distribuição:', { baixo: baixo.length, medio: medio.length, alto: alto.length, critico: critico.length });
    
    // Gerar cards
    const gerarCards = (riscosLista, nivelClasse) => {
        if (riscosLista.length === 0) {
            return '<div class="empty-col-message">Nenhum risco nesta categoria</div>';
        }
        return riscosLista.map((risco, cardIdx) => {
            const categoriasHtml = (risco.categorias || []).map(cat => 
                `<span class="kanban-card-categoria-tag">${escapeHtml(cat)}</span>`
            ).join('');
            
            // Usar índice do risco original
            const originalIdx = riscosProcessados.findIndex(r => r === risco);
            
            // ⭐ ÍCONE PARA O SCORE DO APETITE
            let apetiteIcon = '';
            if (risco.apetiteScore <= 3) apetiteIcon = '';
            else if (risco.apetiteScore <= 7) apetiteIcon = '';
            else if (risco.apetiteScore <= 11) apetiteIcon = '';
            else apetiteIcon = '';
            
            return `
                <div class="kanban-card ${nivelClasse}" data-risco-id="${risco.id}">
                    <div class="kanban-card-title">${escapeHtml(risco.nome_risco)}</div>
                    <div class="kanban-card-score">
                        <span style="font-size: 11px; color: #666;">Magnitude do risco:</span>
                        <span class="kanban-card-badge impact">Impacto Financeiro: ${(risco.impacto || 'Médio').toUpperCase()}</span>
                        <span class="kanban-card-badge prob">Probabilidade: ${ (risco.probabilidade || 'Médio').toUpperCase()}</span>
                        <span><strong>Score do risco (magnitude): ${risco.score}</strong> (${risco.nivelTexto})</span>
                    </div>
                    <!-- ⭐ NOVO: Score do Apetite -->
                    <div class="kanban-card-score" style="margin-top: 4px; padding-top: 4px; border-top: 1px dashed #eee;">
                        <span style="font-size: 11px; color: #666;">Apetite:</span>
                        <span class="kanban-card-badge impact" style="background: #e8f4f8;">Apetite do Impacto Fin.: ${ (risco.apetite_impacto || 'Médio').toUpperCase()}</span>
                        <span class="kanban-card-badge prob" style="background: #e8f4f8;">Apetite da Prob.: ${ (risco.apetite_probabilidade || 'Médio').toUpperCase()}</span>
                        <span><strong>Score do apetite (risco residual): ${risco.apetiteScore}</strong> ${apetiteIcon} (${risco.apetiteNivelTexto})</span>
                    </div>
                    <div class="kanban-card-categorias">
                        ${categoriasHtml || '<span class="text-muted">Sem categorias</span>'}
                    </div>
                    <div class="kanban-card-actions">
                        <button class="btn-view-risk" onclick="visualizarRiscoVisualizacao(${originalIdx})" title="Visualizar detalhes do risco">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    };
    
    return `
        <div class="kanban-board">
            <div class="kanban-col">
                <div class="kanban-col-header low">
                    <i class="fas fa-circle"></i> <span>BAIXA EXPOSIÇÃO</span>
                    <span class="score-range">0 - 3</span>
                    <span class="risk-count">${baixo.length}</span>
                </div>
                <div class="kanban-col-body">
                    ${gerarCards(baixo, 'low')}
                </div>
            </div>
            <div class="kanban-col">
                <div class="kanban-col-header medium">
                    <i class="fas fa-circle"></i> <span>SOB OBSERVAÇÃO</span>
                    <span class="score-range">4 - 7</span>
                    <span class="risk-count">${medio.length}</span>
                </div>
                <div class="kanban-col-body">
                    ${gerarCards(medio, 'medium')}
                </div>
            </div>
            <div class="kanban-col">
                <div class="kanban-col-header high">
                    <i class="fas fa-circle"></i> <span>ATENÇÃO</span>
                    <span class="score-range">8 - 11</span>
                    <span class="risk-count">${alto.length}</span>
                </div>
                <div class="kanban-col-body">
                    ${gerarCards(alto, 'high')}
                </div>
            </div>
            <div class="kanban-col">
                <div class="kanban-col-header critical">
                    <i class="fas fa-circle"></i> <span>CRÍTICO</span>
                    <span class="score-range">12+</span>
                    <span class="risk-count">${critico.length}</span>
                </div>
                <div class="kanban-col-body">
                    ${gerarCards(critico, 'critical')}
                </div>
            </div>
        </div>
    `;
}

// Função global para visualizar risco - VERSÃO EXTREMA
window.visualizarRiscoVisualizacao = function(idx) {
    try {
        const risco = window.riscosVisualizacao ? window.riscosVisualizacao[idx] : null;
        
        if (!risco) {
            mostrarToast('Erro: Risco não encontrado', 'error');
            return;
        }
        
        // Preencher todos os campos do modal
        document.getElementById('vis-nome_risco').textContent = risco.nome_risco || '-';
        document.getElementById('vis-fator_risco').textContent = risco.fator_risco || '-';
        document.getElementById('vis-categoria-causa').textContent = (risco.categoria_causa || []).join(', ') || '-';
        document.getElementById('vis-melhoria').textContent = risco.melhoria || '-';
        document.getElementById('vis-categorias').textContent = (risco.categorias || []).join(', ') || '-';
        
        // ⭐ Garantir que os valores sejam exibidos em maiúsculas
        document.getElementById('vis-impacto').textContent = (risco.impacto || 'MÉDIO').toUpperCase();
        document.getElementById('vis-probabilidade').textContent = (risco.probabilidade || 'MÉDIO').toUpperCase();
        document.getElementById('vis-apetite-impacto').textContent = (risco.apetite_impacto || 'MÉDIO').toUpperCase();
        document.getElementById('vis-apetite-probabilidade').textContent = (risco.apetite_probabilidade || 'MÉDIO').toUpperCase();
        
        document.getElementById('vis-motivo_risco').textContent = risco.motivo_risco || '-';
        document.getElementById('vis-como-tratar').textContent = risco.como_tratar || '-';
        document.getElementById('vis-desc-tratamento').textContent = risco.desc_tratamento || '-';
        document.getElementById('vis-prazo-implantacao').textContent = risco.prazo_implantacao || '-';
        
        // Calcular scores (usando os valores em maiúsculas)
        const score = risco.score || calcularScoreRisco(risco.impacto || 'MÉDIO', risco.probabilidade || 'MÉDIO');
        const apetiteScore = calcularScoreRisco(
            risco.apetite_impacto || 'MÉDIO', 
            risco.apetite_probabilidade || 'MÉDIO'
        );
        
        let nivelTexto = '';
        let corScore = '';
        if (score <= 3) {
            nivelTexto = 'BAIXA EXPOSIÇÃO';
            corScore = '🟢';
        } else if (score <= 7) {
            nivelTexto = 'SOB OBSERVAÇÃO';
            corScore = '🟡';
        } else if (score <= 11) {
            nivelTexto = 'ATENÇÃO';
            corScore = '🟠';
        } else {
            nivelTexto = 'CRÍTICO';
            corScore = '🔴';
        }
        
        const apetiteLevel = getScoreLevelText(apetiteScore);
        document.getElementById('vis-score').innerHTML = `${corScore} ${score} (${nivelTexto})`;
        document.getElementById('vis-score-apetite').textContent = `${apetiteScore} (${apetiteLevel})`;
        
        // ===== ABRIR MODAL =====
        const modal = document.getElementById('modal-visualizar-risco');
        if (modal) {
            modal.style.display = 'flex';
            modal.style.visibility = 'visible';
            modal.style.opacity = '1';
            modal.classList.add('visible');
            console.log('✅ Modal aberto com sucesso!');
        } else {
            console.error('❌ Modal não encontrado!');
            mostrarToast('Erro: Modal não encontrado', 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao visualizar risco:', error);
        mostrarToast('Erro ao visualizar risco: ' + error.message, 'error');
    }
};


// ===== DESATIVAR PROCESSO (soft delete) =====
async function desativarProcesso(processoId) {
    try {
        const response = await fetchComAutenticacao(`/api/processo/${processoId}/desativar`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const resultado = await response.json();
        
        if (resultado.success) {
            mostrarToast('✅ Processo desativado com sucesso!', 'success');
            
            // Recarregar a tabela de processos
            const auditoriaId = filtroAuditoriaSelect.value;
            if (auditoriaId) {
                await carregarTabelaProcessos(auditoriaId);
            }
        } else {
            mostrarToast('❌ Erro ao desativar processo. Tente novamente.', 'error');
        }
    } catch (error) {
        console.error('Erro ao desativar processo:', error);
        mostrarToast('❌ Erro de conexão.', 'error');
    }
}

// ===== MODAL DE CONFIRMAÇÃO PERSONALIZADO =====
let confirmacaoResolve = null;

function mostrarConfirmacao(mensagem) {
    return new Promise((resolve) => {
        // Verificar se o modal já existe, se não, criar
        let modal = document.getElementById('modalConfirmacao');
        
        if (!modal) {
            // Criar modal dinamicamente
            modal = document.createElement('div');
            modal.id = 'modalConfirmacao';
            modal.className = 'modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 100000;
            `;
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 400px; margin: 0 auto;">
                    <div class="modal-header">
                        <h2><i class="fas fa-question-circle"></i> Confirmar Ação</h2>
                        <button class="modal-close" id="btnFecharConfirmacao" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p id="mensagemConfirmacao">Tem certeza que deseja realizar esta ação?</p>
                        <p style="font-size: 12px; color: #666; margin-top: 10px;">Esta ação não poderá ser desfeita.</p>
                        <div class="modal-buttons" style="margin-top: 25px; display: flex; justify-content: flex-end; gap: 10px;">
                            <button type="button" class="btn-cancelar-modal" id="btnCancelarConfirmacao" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">Cancelar</button>
                            <button type="button" class="btn-salvar-area" id="btnConfirmarAcao" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">Confirmar</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        const modalEl = document.getElementById('modalConfirmacao');
        const mensagemEl = document.getElementById('mensagemConfirmacao');
        const btnConfirmar = document.getElementById('btnConfirmarAcao');
        const btnCancelar = document.getElementById('btnCancelarConfirmacao');
        const btnFechar = document.getElementById('btnFecharConfirmacao');
        
        mensagemEl.textContent = mensagem;
        
        // Garantir que o modal esteja visível e centralizado
        modalEl.style.display = 'flex';
        modalEl.style.alignItems = 'center';
        modalEl.style.justifyContent = 'center';
        document.body.style.overflow = 'hidden';
        
        function resolver(valor) {
            modalEl.style.display = 'none';
            document.body.style.overflow = 'auto';
            resolve(valor);
        }
        
        // Remover listeners antigos para evitar duplicação
        const newBtnConfirmar = btnConfirmar.cloneNode(true);
        const newBtnCancelar = btnCancelar.cloneNode(true);
        const newBtnFechar = btnFechar.cloneNode(true);
        
        btnConfirmar.parentNode.replaceChild(newBtnConfirmar, btnConfirmar);
        btnCancelar.parentNode.replaceChild(newBtnCancelar, btnCancelar);
        btnFechar.parentNode.replaceChild(newBtnFechar, btnFechar);
        
        newBtnConfirmar.onclick = () => resolver(true);
        newBtnCancelar.onclick = () => resolver(false);
        newBtnFechar.onclick = () => resolver(false);
        
        modalEl.onclick = (e) => {
            if (e.target === modalEl) resolver(false);
        };
    });
}

// ====== FILTROS DA PÁGINA PRINCIPAL ======
async function carregarAuditoriasFiltro(areaId, auditoriaSelecionada = null) {
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
            
            // ⭐ SE TIVER UMA AUDITORIA SELECIONADA, MARCAR
            if (auditoriaSelecionada) {
                // Verificar se a opção existe
                let optionExists = false;
                for (let i = 0; i < filtroAuditoriaSelect.options.length; i++) {
                    if (filtroAuditoriaSelect.options[i].value == auditoriaSelecionada) {
                        optionExists = true;
                        break;
                    }
                }
                
                if (optionExists) {
                    filtroAuditoriaSelect.value = auditoriaSelecionada;
                    console.log('✅ Auditoria selecionada no filtro:', auditoriaSelecionada);
                    
                    // Disparar evento change para carregar a tabela
                    const changeEvent = new Event('change', { bubbles: true });
                    filtroAuditoriaSelect.dispatchEvent(changeEvent);
                } else {
                    console.warn('⚠️ Auditoria', auditoriaSelecionada, 'não encontrada nas opções');
                }
            }
        } else {
            filtroAuditoriaSelect.innerHTML = '<option value="">Nenhuma auditoria encontrada</option>';
            filtroAuditoriaSelect.disabled = true;
        }
    } catch (error) {
        console.error('Erro ao carregar auditorias:', error);
        filtroAuditoriaSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

// ===== CARREGAR TABELA DE PROCESSOS COM ORDENAÇÃO =====
let processosData = [];
let ordenacaoAtual = { coluna: 'nenhuma', direcao: 'asc' };

async function carregarTabelaProcessos(auditoriaId, areaId = null) {
    // Se não veio areaId, pega do filtro
    if (!areaId) {
        areaId = filtroAreaSelect?.value;
    }
    
    // Se não tem área selecionada, não carrega nada
    if (!areaId) {
        if (tabelaProcessosContainer) {
            tabelaProcessosContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma área para visualizar os processos.</div>';
        }
        return;
    }
    
    // ⭐ SE AUDITORIA_ID FOR NULL OU VAZIO, BUSCAR TODOS OS PROCESSOS DA ÁREA
    const url = auditoriaId 
        ? `/api/processos-por-area?area_id=${areaId}&auditoria_id=${auditoriaId}`
        : `/api/processos-por-area?area_id=${areaId}`;
    
    tabelaProcessosContainer.innerHTML = `
        <div style="text-align: center; padding: 60px 20px;">
            <div class="dot-spinner">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando processos...</p>
        </div>
    `;
    
    try {
        const response = await fetchComAutenticacao(url);
        const data = await response.json();
        
        if (!data.success || !data.processos || data.processos.length === 0) {
            let mensagem = auditoriaId 
                ? 'Nenhum processo encontrado para esta auditoria.'
                : 'Nenhum processo encontrado para esta área. Clique em "Novo Processo" para começar.';
            tabelaProcessosContainer.innerHTML = `<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> ${mensagem}</div>`;
            return;
        }
        
        // Buscar riscos para cada processo
        for (const processo of data.processos) {
            const riscosResponse = await fetchComAutenticacao(`/api/processo/${processo.id}/riscos`);
            const riscosData = await riscosResponse.json();
            
            let scoreMaximo = 0;
            let corScore = '';
            let textoScore = '';
            
            if (riscosData.riscos && riscosData.riscos.length > 0) {
                scoreMaximo = Math.max(...riscosData.riscos.map(r => r.score_risco || 0));
                
                if (scoreMaximo <= 3) {
                    corScore = '🟢';
                    textoScore = 'baixo';
                } else if (scoreMaximo <= 7) {
                    corScore = '🟡';
                    textoScore = 'médio';
                } else if (scoreMaximo <= 11) {
                    corScore = '🟠';
                    textoScore = 'alto';
                } else {
                    corScore = '🔴';
                    textoScore = 'crítico';
                }
            } else {
                corScore = '⚪';
                textoScore = 'sem-risco';
            }
            
            processo.scoreMaximo = scoreMaximo;
            processo.corScore = corScore;
            processo.textoScore = textoScore;
            processo.qtdRiscos = riscosData.riscos ? riscosData.riscos.length : 0;
        }
        
        processosData = data.processos;
        ordenacaoAtual = { coluna: 'nenhuma', direcao: 'asc' };
        
        renderizarTabela();
        
    } catch (error) {
        console.error('Erro ao carregar processos:', error);
        tabelaProcessosContainer.innerHTML = '<div class="alert-error" style="text-align: center; padding: 40px;"><i class="fas fa-exclamation-triangle"></i> Erro ao carregar processos. Tente novamente.</div>';
    }
}

function ordenarProcessos(coluna) {
    if (ordenacaoAtual.coluna === coluna) {
        ordenacaoAtual.direcao = ordenacaoAtual.direcao === 'asc' ? 'desc' : 'asc';
    } else {
        ordenacaoAtual.coluna = coluna;
        ordenacaoAtual.direcao = 'asc';
    }
    
    processosData.sort((a, b) => {
        let valorA, valorB;
        
        switch(coluna) {
            case 'codigo':
                // Extrair a parte depois do ponto e converter para número
                const numA = parseInt(a.codigo_processo.split('.')[1], 10);
                const numB = parseInt(b.codigo_processo.split('.')[1], 10);
                valorA = numA;
                valorB = numB;
                break;
            case 'nome':
                valorA = a.nome_processo.toLowerCase();
                valorB = b.nome_processo.toLowerCase();
                break;
            case 'score':
                valorA = a.scoreMaximo;
                valorB = b.scoreMaximo;
                break;
            case 'riscos':
                valorA = a.qtdRiscos;
                valorB = b.qtdRiscos;
                break;
            default:
                return 0;
        }
        
        if (valorA < valorB) return ordenacaoAtual.direcao === 'asc' ? -1 : 1;
        if (valorA > valorB) return ordenacaoAtual.direcao === 'asc' ? 1 : -1;
        return 0;
    });
    
    renderizarTabela();
}

function renderizarTabela() {
    let html = `
        <div style="overflow-x: auto;">
            <table class="tabela-processos">
                <thead>
                    <tr>
                        <th class="sortable" data-coluna="codigo">Código ${ordenacaoAtual.coluna === 'codigo' ? (ordenacaoAtual.direcao === 'asc' ? '▲' : '▼') : '↕'}</th>
                        <th class="sortable" data-coluna="nome">Nome do Processo ${ordenacaoAtual.coluna === 'nome' ? (ordenacaoAtual.direcao === 'asc' ? '▲' : '▼') : '↕'}</th>
                        <th>Objetivo</th>
                        <th class="sortable" data-coluna="auditoria">Auditoria ${ordenacaoAtual.coluna === 'auditoria' ? (ordenacaoAtual.direcao === 'asc' ? '▲' : '▼') : '↕'}</th>
                        <th class="sortable" data-coluna="score">Score Máximo ${ordenacaoAtual.coluna === 'score' ? (ordenacaoAtual.direcao === 'asc' ? '▲' : '▼') : '↕'}</th>
                        <th class="sortable" data-coluna="riscos">Riscos ${ordenacaoAtual.coluna === 'riscos' ? (ordenacaoAtual.direcao === 'asc' ? '▲' : '▼') : '↕'}</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    for (const processo of processosData) {
        const isAdmin = (USUARIO_PERFIL === 'administrador' || USUARIO_PERFIL === 'admin');
        
        let botoesHtml = '';
        
        if (isAdmin) {
            botoesHtml = `
                <button class="btn-edit-processo" data-processo-id="${processo.id}" data-processo-codigo="${processo.codigo_processo}" title="Editar">
                    <i class="fas fa-pencil-alt"></i>
                </button>
                <button class="btn-delete-processo" data-processo-id="${processo.id}" data-processo-nome="${escapeHtml(processo.nome_processo)}" title="Excluir">
                    <i class="fas fa-trash-alt"></i>
                </button>
            `;
        } else {
            if (usuarioAutorizado) {
                botoesHtml = `
                    <button class="btn-editar-processo" data-processo-id="${processo.id}" data-processo-codigo="${processo.codigo_processo}">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                `;
            } else {
                botoesHtml = `<span class="text-muted">-</span>`;
            }
        }
        
        // Formatar código da auditoria para exibição
        const auditoriaDisplay = processo.codigo_auditoria || (processo.auditoria_codigo || '-');
        
        html += `
            <tr>
                <td>
                    <strong>${escapeHtml(processo.codigo_processo)}</strong>
                    <button class="btn-visualizar-processo" data-processo-id="${processo.id}" title="Clique para visualizar todas as informações do processo">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
                <td>${escapeHtml(processo.nome_processo)}</td>
                <td>${escapeHtml(processo.objetivo || '-')}</td>
                <td><span class="auditoria-badge">${escapeHtml(auditoriaDisplay)}</span></td>
                <td><span class="score-badge ${processo.textoScore}">${processo.corScore} ${processo.scoreMaximo}</span></td>
                <td>${processo.qtdRiscos}</td>
                <td>${botoesHtml}</td>
            </tr>
        `;
    }
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    tabelaProcessosContainer.innerHTML = html;
    
    // Adicionar eventos de ordenação
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const coluna = th.getAttribute('data-coluna');
            ordenarProcessos(coluna);
        });
    });
    
    // Adicionar eventos aos botões de editar (para ADMIN - ícone)
    document.querySelectorAll('.btn-edit-processo').forEach(btn => {
        btn.addEventListener('click', () => {
            const processoId = btn.getAttribute('data-processo-id');
            const processoCodigo = btn.getAttribute('data-processo-codigo');
            abrirModalEdicao(processoId, processoCodigo);
        });
    });

    // ⭐ ADICIONAR EVENTOS AOS BOTÕES DE EDITAR (para USUÁRIOS AUTORIZADOS - com texto)
    document.querySelectorAll('.btn-editar-processo').forEach(btn => {
        btn.addEventListener('click', () => {
            const processoId = btn.getAttribute('data-processo-id');
            const processoCodigo = btn.getAttribute('data-processo-codigo');
            abrirModalEdicao(processoId, processoCodigo);
        });
    });

    // Adicionar eventos aos botões de excluir
    document.querySelectorAll('.btn-delete-processo').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const processoId = btn.getAttribute('data-processo-id');
            const processoNome = btn.getAttribute('data-processo-nome');
            
            const confirmado = await mostrarConfirmacao(`Tem certeza que deseja excluir o processo "${processoNome}"?`);
            if (confirmado) {
                await desativarProcesso(processoId);
            }
        });
    });
    
    // Adicionar eventos aos botões de visualizar processo
    document.querySelectorAll('.btn-visualizar-processo').forEach(btn => {
        btn.addEventListener('click', () => {
            const processoId = btn.getAttribute('data-processo-id');
            abrirModalVisualizarProcesso(processoId);
        });
    });
}

// Evento de filtro da área
if (filtroAreaSelect) {
    filtroAreaSelect.addEventListener('change', async () => {
        const areaId = filtroAreaSelect.value;

        // SALVAR O FILTRO NO SESSIONSTORAGE
        if (areaId) {
            sessionStorage.setItem('filtro_area_id', areaId);
        } else {
            sessionStorage.removeItem('filtro_area_id');
        }
        sessionStorage.removeItem('filtro_auditoria_id');

        // Limpar o select de auditoria
        if (filtroAuditoriaSelect) {
            filtroAuditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            filtroAuditoriaSelect.disabled = false;
        }
        
        // ⭐ CARREGAR AUDITORIAS (sem selecionar nenhuma)
        await carregarAuditoriasFiltro(areaId);
        
        // ⭐ CARREGAR PROCESSOS DA ÁREA
        if (areaId) {
            // Resetar autorização
            usuarioAutorizado = true;
            
            // Mostrar botão de novo processo
            const btnNovoProcesso = document.getElementById('btn-novo-processo');
            if (btnNovoProcesso) btnNovoProcesso.style.display = 'flex';
            
            // Carregar todos os processos da área
            carregarTabelaProcessos(null, areaId);
        } else {
            // Se não tem área, limpar tabela
            if (tabelaProcessosContainer) {
                tabelaProcessosContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma área para visualizar os processos.</div>';
            }
            const btnNovoProcesso = document.getElementById('btn-novo-processo');
            if (btnNovoProcesso) btnNovoProcesso.style.display = 'none';
        }
    });
}

// Evento do filtro de auditoria
if (filtroAuditoriaSelect) {
    filtroAuditoriaSelect.addEventListener('change', () => {
        const auditoriaId = filtroAuditoriaSelect.value;

        // SALVAR O FILTRO NO SESSIONSTORAGE
        if (auditoriaId) {
            sessionStorage.setItem('filtro_auditoria_id', auditoriaId);
        } else {
            sessionStorage.removeItem('filtro_auditoria_id');
        }

        const btnNovoProcesso = document.getElementById('btn-novo-processo');
        const areaId = filtroAreaSelect?.value;
        
        if (areaId) {
            // Se tem área, carregar processos (com ou sem auditoria)
            const auditoriaParaVerificar = auditoriaId && auditoriaId !== '' ? auditoriaId : null;
            
            // ⭐ Se não tem auditoria, já estamos mostrando todos os processos
            // Então só precisa verificar se o usuário tem permissão para alguma auditoria?
            if (!auditoriaParaVerificar) {
                // Já está mostrando todos, não precisa verificar permissão específica
                usuarioAutorizado = true;
                if (btnNovoProcesso) btnNovoProcesso.style.display = 'flex';
                carregarTabelaProcessos(null, areaId);
            } else {
                verificarResponsavelEAcao(auditoriaParaVerificar, () => {
                    usuarioAutorizado = true;
                    if (btnNovoProcesso) btnNovoProcesso.style.display = 'flex';
                    carregarTabelaProcessos(auditoriaId, areaId);
                }, () => {
                    usuarioAutorizado = false;
                    if (btnNovoProcesso) btnNovoProcesso.style.display = 'none';
                    if (tabelaProcessosContainer) {
                        tabelaProcessosContainer.innerHTML = '<div class="alert-error" style="text-align: center; padding: 40px;"><i class="fas fa-lock"></i> Você não tem permissão para visualizar processos desta auditoria.</div>';
                    }
                });
            }
        } else {
            if (btnNovoProcesso) btnNovoProcesso.style.display = 'none';
            if (tabelaProcessosContainer) {
                tabelaProcessosContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma área para visualizar os processos.</div>';
            }
        }
    });
}

// ===== BOTÃO PRÓXIMO DA SEÇÃO 1 =====
const btnProximoEtapa2 = document.getElementById('btn-proximo-etapa2');

function habilitarProximoEtapa1(habilitar) {
    if (btnProximoEtapa2) {
        btnProximoEtapa2.disabled = !habilitar;
    }
}

// Evento de clique do botão próximo da etapa 1
if (btnProximoEtapa2) {
    btnProximoEtapa2.addEventListener('click', () => {
        irParaEtapa(2);
    });
}

// ====== JAVASCRIPT PARA DIAGNÓSTICO ======

const areaSelect = document.getElementById('area_select');
const auditoriaSection = document.getElementById('auditoria-section');
const auditoriaSelect = document.getElementById('auditoria_select');
const novaAuditoriaBtn = document.getElementById('nova-auditoria-btn');

// Função para escapar HTML e prevenir XSS
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Função para formatar data de YYYY-MM-DD para DD/MM/YYYY na visualização
function formatarDataParaExibicao(dataString) {
    if (!dataString) return '-';
    const partes = dataString.split('-');
    if (partes.length === 3) {
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }
    return dataString;
}

// ===== RESETAR CAMPOS DA SEÇÃO 3 =====
function resetarCamposDetalhes() {
    const descricao = document.getElementById('descricao_processo');
    const etapaIni = document.getElementById('etapa_ini_processo');
    const produto = document.getElementById('produto_processo');
    const etapaFim = document.getElementById('etapa_fim_processo');
    const objetivo = document.getElementById('objetivo_processo');
    
    if (descricao) descricao.value = '';
    if (etapaIni) etapaIni.value = '';
    if (produto) produto.value = '';
    if (etapaFim) etapaFim.value = '';
    if (objetivo) objetivo.value = '';
}

// ===== GERENCIAR NOME DO PROCESSO E CÓDIGO =====
let timeoutId = null;
let ultimoNomeVerificado = '';
let ultimoCodigoGerado = '';

const nomeProcessoInput = document.getElementById('nome_processo');
const codigoProcessoInput = document.getElementById('codigo_processo');
const idAreaSelecionado = document.getElementById('id_area_selecionado');

// ===== MULTISELECT DE EXECUTORES COM LISTA VISÍVEL =====
let funcionariosDisponiveis = [];
let executoresSelecionados = [];

// Carregar funcionários da área e exibir na grid
async function carregarFuncionariosArea(areaId) {
    if (!areaId) {
        console.log('❌ Nenhum areaId fornecido');
        return;
    }
    
    console.log(`🔄 Carregando funcionários da área ${areaId}...`);
    
    try {
        const response = await fetchComAutenticacao(`/api/area/${areaId}/funcionarios-para-select`);
        
        if (!response.ok) {
            console.error(`❌ Erro HTTP: ${response.status}`);
            return;
        }
        
        const data = await response.json();
        funcionariosDisponiveis = data;
        
        // Atualizar contador total
        const totalSpan = document.getElementById('total-funcionarios');
        if (totalSpan) {
            totalSpan.textContent = funcionariosDisponiveis.length;
        }
        
        console.log(`✅ ${funcionariosDisponiveis.length} funcionários carregados`);
        
        // Exibir lista de funcionários
        exibirListaFuncionarios();
        
    } catch (error) {
        console.error('❌ Erro ao carregar funcionários:', error);
        funcionariosDisponiveis = [];
        const listaDiv = document.getElementById('lista-funcionarios');
        if (listaDiv) {
            listaDiv.innerHTML = '<div class="empty-funcionarios">❌ Erro ao carregar funcionários</div>';
        }
    }
}

// Exibir todos os funcionários disponíveis
function exibirListaFuncionarios() {
    const listaDiv = document.getElementById('lista-funcionarios');
    if (!listaDiv) return;
    
    if (funcionariosDisponiveis.length === 0) {
        listaDiv.innerHTML = '<div class="empty-funcionarios">📌 Nenhum funcionário cadastrado para esta área</div>';
        return;
    }
    
    // Filtrar pelo termo de busca (se houver)
    const buscaInput = document.getElementById('buscar-executor');
    const termo = buscaInput ? buscaInput.value.toLowerCase().trim() : '';
    
    let funcionariosFiltrados = funcionariosDisponiveis;
    if (termo) {
        funcionariosFiltrados = funcionariosDisponiveis.filter(f => 
            f.nome.toLowerCase().includes(termo)
        );
    }
    
    if (funcionariosFiltrados.length === 0) {
        listaDiv.innerHTML = '<div class="empty-funcionarios">🔍 Nenhum funcionário encontrado com esse nome</div>';
        return;
    }
    
    // Exibir cards
    listaDiv.innerHTML = funcionariosFiltrados.map(f => {
        const jaSelecionado = executoresSelecionados.some(exec => exec.id === f.id);
        const classeAdicionado = jaSelecionado ? 'adicionado' : '';
        const botaoTexto = jaSelecionado ? '✓ Selecionado' : '+ Adicionar';
        const botaoDisabled = jaSelecionado ? 'disabled' : '';
        
        return `
            <div class="funcionario-card ${classeAdicionado}" data-id="${f.id}">
                <div class="info">
                    <div class="avatar-small">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="details">
                        <div class="nome">${f.nome}</div>
                        <div class="cargo">${f.cargo || 'Sem cargo'}</div>
                    </div>
                </div>
                <button class="btn-adicionar-card" 
                        onclick="adicionarExecutor(${f.id}, '${f.nome.replace(/'/g, "\\'")}', '${(f.cargo || '').replace(/'/g, "\\'")}')"
                        ${botaoDisabled}>
                    ${botaoTexto}
                </button>
            </div>
        `;
    }).join('');
}

// Filtrar lista quando o usuário digitar
function filtrarListaFuncionarios() {
    exibirListaFuncionarios();
}

// Adicionar executor
function adicionarExecutor(id, nome, cargo) {
    // Verificar se já está selecionado
    if (executoresSelecionados.some(e => e.id === id)) {
        mostrarToast('Este funcionário já foi selecionado', 'warning');
        return;
    }
    
    executoresSelecionados.push({ id, nome, cargo: cargo || 'Sem cargo' });
    atualizarBadges();
    
    // Re-exibir lista para atualizar o botão
    exibirListaFuncionarios();
    
    // Habilitar botão próximo se tiver pelo menos um executor
    const btnProximo = document.getElementById('btn-proximo-etapa3');
    if (btnProximo && executoresSelecionados.length > 0) {
        btnProximo.disabled = false;
    }

}

// Remover executor
function removerExecutor(id, nome) {
    executoresSelecionados = executoresSelecionados.filter(e => e.id !== id);
    atualizarBadges();
    
    // Re-exibir lista para atualizar o botão
    exibirListaFuncionarios();
    
    // Desabilitar botão se não tiver executores
    const btnProximo = document.getElementById('btn-proximo-etapa3');
    if (btnProximo && executoresSelecionados.length === 0) {
        btnProximo.disabled = true;
    }
    
    mostrarToast(`⚠️ ${nome} removido dos executores`, 'info');
}

// Atualizar visual dos badges selecionados
function atualizarBadges() {
    const container = document.getElementById('executores-selecionados');
    const contadorSpan = document.getElementById('contador-executores');
    const hiddenInput = document.getElementById('executores_ids');
    
    if (!container) return;
    
    // Atualizar contador
    if (contadorSpan) {
        contadorSpan.textContent = executoresSelecionados.length;
    }
    
    // Atualizar hidden input
    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(executoresSelecionados.map(e => e.id));
    }
    
    // Mostrar mensagem ou badges
    if (executoresSelecionados.length === 0) {
        container.innerHTML = '<div class="empty-message"><i class="fas fa-ban" style="color:#0b5b99";></i> Nenhum executor selecionado</div>';
        return;
    }
    
    container.innerHTML = executoresSelecionados.map(exec => `
        <div class="executor-badge">
            <div class="info">
                <div class="avatar">
                    <i class="fas fa-user-check"></i>
                </div>
                <div class="details">
                    <div class="nome">${exec.nome}</div>
                    <div class="cargo">${exec.cargo}</div>
                </div>
            </div>
            <button type="button" class="btn-remover" onclick="removerExecutor(${exec.id}, '${exec.nome.replace(/'/g, "\\'")}')">
                <i class="fas fa-trash-alt"></i> Remover
            </button>
        </div>
    `).join('');
}

// ===== EVENT LISTENERS =====
const buscaExecutor = document.getElementById('buscar-executor');
if (buscaExecutor) {
    buscaExecutor.addEventListener('input', filtrarListaFuncionarios);
}

// Carregar funcionários quando a área for selecionada
// Chamar esta função dentro do change da área

// Função principal que verifica e gera o código
async function verificarEGerarCodigo() {
    // ====== SE FOR EDIÇÃO, PULA COMPLETAMENTE A VERIFICAÇÃO ======
    const modoEdicao = sessionStorage.getItem('modo_edicao');
    if (modoEdicao === 'true') {
        console.log('✏️ Modo edição ativo - pulando verificação de duplicidade');
        return;
    }
    const nomeProcesso = nomeProcessoInput?.value.trim().toUpperCase();
    const areaId = idAreaSelecionado?.value || areaSelect?.value;

    // Buscar o auditoriaId do elemento select
    const auditoriaSelectEl = document.getElementById('auditoria_select');
    const auditoriaId = auditoriaSelectEl?.value;
    
    // Se não tem nome ou área, limpa o código
    if (!nomeProcesso || !areaId || !auditoriaId) {
        if (codigoProcessoInput) {
            codigoProcessoInput.value = '';
            codigoProcessoInput.style.backgroundColor = '#e9ecef';
        }
        return;
    }
    
    // Debounce: espera o usuário parar de digitar (500ms)
    if (timeoutId) clearTimeout(timeoutId);
    
    timeoutId = setTimeout(async () => {
        try {
            
            // Verificar se o processo já existe com este nome
            const response = await fetchComAutenticacao(
                `/api/processo/verificar?nome=${encodeURIComponent(nomeProcesso)}&id_area=${areaId}&auditoria_id=${auditoriaId}`
            );
            const data = await response.json();
            
            if (data.existe) {
                // ===== CASO 1: PROCESSO JÁ EXISTE =====
                if (codigoProcessoInput) {
                    codigoProcessoInput.value = data.codigo;
                    codigoProcessoInput.style.backgroundColor = '#fff3cd';
                    codigoProcessoInput.style.border = '1px solid #ffc107';
                    codigoProcessoInput.style.color = '#856404';
                }
                
                mostrarAvisoProcessoExistente(nomeProcesso, data.codigo);
                ultimoNomeVerificado = nomeProcesso;
                desabilitarProximoStep(true, "Este processo já existe. Utilize a aba de edição para modificá-lo.");
                mostrarToast(`⚠️ Processo "${nomeProcesso}" já existe!`, 'warning');
                
                // Limpar sessionStorage para não tentar salvar como novo
                sessionStorage.removeItem('processo_id');
                sessionStorage.removeItem('modo_edicao');
                
            } else {
                // ===== CASO 2: PROCESSO NOVO - GERAR NOVO CÓDIGO =====
                const codigoResponse = await fetchComAutenticacao(
                    `/api/processo/gerar-codigo?id_area=${areaId}&auditoria_id=${auditoriaId}`
                );
                const codigoData = await codigoResponse.json();
                
                if (codigoResponse.ok && codigoData.codigo) {
                    if (codigoProcessoInput) {
                        codigoProcessoInput.value = codigoData.codigo;
                        codigoProcessoInput.style.backgroundColor = '#e8f4f8';
                        codigoProcessoInput.style.border = '1px solid #184145';
                        codigoProcessoInput.style.color = '#184145';
                    }
                    
                    removerAvisoProcessoExistente();
                    ultimoNomeVerificado = nomeProcesso;
                    ultimoCodigoGerado = codigoData.codigo;
                    desabilitarProximoStep(false, "");
                    
                    // RESETAR DADOS ANTERIORES (pois é um novo processo)
                    executoresSelecionados = [];
                    atualizarBadges();
                    exibirListaFuncionarios();
                    resetarCamposDetalhes();
                    
                    // Limpar sessionStorage para começar novo processo
                    sessionStorage.removeItem('processo_id');
                    sessionStorage.removeItem('auditoria_id');
                    sessionStorage.removeItem('modo_edicao');
                    sessionStorage.removeItem('detalhes_temp');
                    
                    console.log(`✅ Código gerado para novo processo: ${codigoData.codigo}`);
                } else {
                    console.error('Erro ao gerar código:', codigoData);
                    mostrarToast('❌ Erro ao gerar código do processo', 'error');
                }
            }
        } catch (error) {
            console.error('Erro ao verificar processo:', error);
            mostrarToast('❌ Erro ao verificar processo. Tente novamente.', 'error');
        }
    }, 500);
}

// Função para mostrar aviso de processo existente
function mostrarAvisoProcessoExistente(nomeProcesso, codigoExistente) {
    const modoEdicao = sessionStorage.getItem('modo_edicao');

    // ===== CASO 1: EDIÇÃO - Mostra card AZUL (informativo) =====
    if (modoEdicao === 'true') {
        // Remove aviso anterior se existir
        removerAvisoProcessoExistente();
        
        // Usa o container global (que não some ao mudar de etapa)
        const container = document.getElementById('global-avisos-container');
        if (!container) {
            console.warn('⚠️ Container global-avisos-container não encontrado');
            return;
        }
        
        // Cria o card de aviso
        const avisoDiv = document.createElement('div');
        avisoDiv.id = 'aviso-processo-existente';
        avisoDiv.className = 'alert-info';
        avisoDiv.style.marginBottom = '15px';
        avisoDiv.style.padding = '12px 16px';
        avisoDiv.style.borderRadius = '8px';
        avisoDiv.style.borderLeft = '4px solid #0b5b99';
        avisoDiv.style.backgroundColor = '#e8f4f8';
        avisoDiv.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <i class="fas fa-edit" style="color: #0b5b99; margin-right: 8px;"></i>
                    <strong style="color: #184145;">Editando processo:</strong>
                    <span style="margin-left: 8px;">Você está editando o processo 
                    <strong>${escapeHtml(nomeProcesso)}</strong> (código <strong>${escapeHtml(codigoExistente)}</strong>)</span>
                </div>
                <button type="button" id="fechar-aviso-edicao" style="background: none; border: none; font-size: 18px; cursor: pointer; color: #999;">&times;</button>
            </div>
            <small style="display: block; margin-top: 8px; color: #0c5460;">
                <i class="fas fa-info-circle"></i> Modifique os campos abaixo e clique em "Próximo" para salvar as alterações.
            </small>
        `;
        
        container.appendChild(avisoDiv);
        
        // Evento para fechar o aviso se o usuário clicar no X
        const closeBtn = document.getElementById('fechar-aviso-edicao');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                removerAvisoProcessoExistente();
            });
        }
        return;
    }
    
    // ===== CASO 2: NOVO PROCESSO - Mostra card AMARELO (alerta) =====
    removerAvisoProcessoExistente();
    
    const avisoDiv = document.createElement('div');
    avisoDiv.id = 'aviso-processo-existente';
    avisoDiv.className = 'alert-warning';
    avisoDiv.style.marginTop = '10px';
    avisoDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        <strong>Processo já cadastrado!</strong><br>
        O processo "${nomeProcesso}" já existe com o código <strong>${codigoExistente}</strong>.
        <br><br>
        <small>💡 Para modificar este processo, utilize a aba <strong>"Edição"</strong>.</small>
    `;
    
    // Para novos processos, insere após o campo de código
    if (codigoProcessoInput && codigoProcessoInput.parentNode) {
        codigoProcessoInput.parentNode.insertAdjacentElement('afterend', avisoDiv);
    }
}

// Função para remover aviso de processo existente
function removerAvisoProcessoExistente() {
    // Remove o aviso do container global (usado na edição)
    const avisoGlobal = document.getElementById('aviso-processo-existente');
    if (avisoGlobal) {
        avisoGlobal.remove();
    }
}

// Função para habilitar/desabilitar o botão de próximo step
function desabilitarProximoStep(desabilitar, mensagem) {
    const btnProximo = document.getElementById('btn-proximo-etapa3');
    if (btnProximo) {
        btnProximo.addEvent
        btnProximo.disabled = desabilitar;
        if (desabilitar && mensagem) {
            btnProximo.title = mensagem;
        } else {
            btnProximo.title = '';
        }
    }
}

// ===== QUANDO A ÁREA É ALTERADA, RESETAR A VERIFICAÇÃO =====
function resetarVerificacaoProcesso() {
    // ===== SE FOR EDIÇÃO, NÃO LIMPA NADA! =====
    const modoEdicao = sessionStorage.getItem('modo_edicao');
    if (modoEdicao === 'true') {
        console.log('✏️ Modo edição ativo - resetarVerificacaoProcesso ignorado');
        return;
    }
    
    ultimoNomeVerificado = '';
    ultimoCodigoGerado = '';
    
    if (codigoProcessoInput) {
        codigoProcessoInput.value = '';
        codigoProcessoInput.style.backgroundColor = '#e9ecef';
    }
    
    removerAvisoProcessoExistente();
    
    const nomeProcesso = nomeProcessoInput?.value.trim();
    if (nomeProcesso && (idAreaSelecionado?.value || areaSelect?.value)) {
        verificarEGerarCodigo();
    }
}

// ===== EVENT LISTENERS =====
if (nomeProcessoInput) {
    nomeProcessoInput.addEventListener('input', () => {
        // 🔧 Se for edição, não faz a verificação
        const modoEdicao = sessionStorage.getItem('modo_edicao');
        if (modoEdicao === 'true') {
            console.log('✏️ Edição ativa - ignorando verificação de nome');
            return;
        }
        verificarEGerarCodigo();
    });
}

if (areaSelect) {
    areaSelect.addEventListener('change', () => {
        const modoEdicao = sessionStorage.getItem('modo_edicao');
        if (modoEdicao !== 'true') {
            resetarVerificacaoProcesso();
        }
    });
}

if (idAreaSelecionado) {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'value') {
                resetarVerificacaoProcesso();
            }
        });
    });
    observer.observe(idAreaSelecionado, { attributes: true });
}

// ===== TOAST DE NOTIFICAÇÃO =====
function mostrarToast(mensagem, tipo = 'info') {
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 100000000 !important;
        `;
        document.body.appendChild(toastContainer);
    }
    
    const cores = {
        success: { bg: '#d4edda', border: '#28a745', text: '#155724', icon: '✅' },
        error: { bg: '#f8d7da', border: '#dc3545', text: '#721c24', icon: '❌' },
        warning: { bg: '#fff3cd', border: '#ffc107', text: '#856404', icon: '⚠️' },
        info: { bg: '#d1ecf1', border: '#17a2b8', text: '#0c5460', icon: 'ℹ️' }
    };
    
    const cor = cores[tipo] || cores.info;
    
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.cssText = `
        background: ${cor.bg};
        border-left: 4px solid ${cor.border};
        color: ${cor.text};
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 8px;
        font-size: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
    `;
    
    toast.innerHTML = `
        <span style="font-size: 18px;">${cor.icon}</span>
        <span>${mensagem}</span>
        <span style="margin-left: auto; cursor: pointer; opacity: 0.7;" onclick="this.parentElement.remove()">✕</span>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        if (toast && toast.parentElement) {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 4000);
}

// Adicionar CSS para animações
if (!document.getElementById('toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// ===== LIMPAR AVISOS =====
function limparAvisos() {
    const aviso = document.getElementById('aviso-sem-auditorias');
    const msgPermissao = document.getElementById('msg-permissao');
    const msgNaoAutorizado = document.getElementById('msg-nao-autorizado');
    
    if (aviso) aviso.remove();
    if (msgPermissao) msgPermissao.remove();
    if (msgNaoAutorizado) msgNaoAutorizado.remove();
}

// ===== EVENTO DE MUDANÇA DE ÁREA =====
areaSelect.addEventListener('change', async function() {
    // VERIFICAR SE ESTÁ CARREGANDO A PÁGINA (NÃO LIMPAR STORAGE NESSE CASO)
    const isLoading = document.readyState !== 'complete';
    if (!isLoading) {
        const modoEdicaoAtivo = sessionStorage.getItem('modo_edicao');
        if (modoEdicaoAtivo !== 'true') {
            resetarCamposDetalhes();
        }
        if (modoEdicaoAtivo !== 'true') {
            sessionStorage.removeItem('modo_edicao');
            sessionStorage.removeItem('processo_id');
            sessionStorage.removeItem('auditoria_id');
            riscosLista = [];
            sessionStorage.removeItem('riscos_temp');
            sessionStorage.removeItem('etapa_atual');
        }
    }
    
    const areaId = this.value;
    if (areaId) {
        sessionStorage.setItem('area_id_selecionada', areaId);
    }
    const areaNome = this.options[this.selectedIndex]?.text || '';

    if (areaId) {
        document.getElementById('id_area_selecionado').value = areaId;
    }

    if (areaId) {
        await carregarFuncionariosArea(parseInt(areaId));
    }
    
    limparAvisos();

    // Resetar o select de auditoria
    auditoriaSelect.innerHTML = '<option value="">Carregando auditorias...</option>';
    auditoriaSelect.value = '';
    
    // ⭐ GARANTIR QUE O INNER DA AUDITORIA FIQUE VISÍVEL
    const auditoriaInner = document.getElementById('auditoria-inner');
    if (auditoriaInner) {
        auditoriaInner.style.display = 'block';
    }

    // Esconder seção de informações básicas
    const infoBasicasSection = document.getElementById('info-basicas-section');
    if (infoBasicasSection) {
        infoBasicasSection.style.display = 'none';
    }

    if (!areaId) {
        // ⭐ SE NÃO TIVER ÁREA, ESCONDER O INNER
        if (auditoriaInner) {
            auditoriaInner.style.display = 'none';
        }
        return;
    }
    
    if (novaAuditoriaBtn) {
        novaAuditoriaBtn.style.display = 'none';
    }
    
    try {
        const response = await fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();
        
        console.log('Auditorias recebidas:', data);
        
        if (data.auditorias && data.auditorias.length > 0) {
            // ⭐ GARANTIR QUE O INNER ESTEJA VISÍVEL
            if (auditoriaInner) {
                auditoriaInner.style.display = 'block';
            }

            auditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            
            data.auditorias.forEach(aud => {
                const option = document.createElement('option');
                option.value = aud.id;
                option.textContent = `${aud.codigo_auditoria} - ${aud.titulo} (${aud.ano}) ${aud.trimestre}º trim) - ${aud.unidade || ''}`;
                auditoriaSelect.appendChild(option);
            });
            
            auditoriaSelect.style.display = 'block';
            
            if (novaAuditoriaBtn) {
                novaAuditoriaBtn.style.display = 'none';
            }
            
        } else {
            // ⭐ GARANTIR QUE O INNER ESTEJA VISÍVEL MESMO SEM AUDITORIAS
            if (auditoriaInner) {
                auditoriaInner.style.display = 'block';
            }

            auditoriaSelect.innerHTML = '';
            auditoriaSelect.style.display = 'none';
            
            const aviso = document.createElement('div');
            aviso.id = 'aviso-sem-auditorias';
            aviso.className = 'alert-warning';
            aviso.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i> 
                <strong>Nenhuma auditoria encontrada</strong><br>
                A área "${areaNome}" não possui auditorias cadastradas para esta área.
            `;
            auditoriaInner?.appendChild(aviso);
            
            if (isAdmin && novaAuditoriaBtn) {
                novaAuditoriaBtn.style.display = 'block';
            } else if (!isAdmin && novaAuditoriaBtn) {
                novaAuditoriaBtn.style.display = 'none';
                
                if (!document.getElementById('msg-permissao')) {
                    const msgPermissao = document.createElement('div');
                    msgPermissao.id = 'msg-permissao';
                    msgPermissao.className = 'alert-info';
                    msgPermissao.innerHTML = `
                        <i class="fas fa-lock"></i> 
                        Apenas administradores podem criar novas auditorias.
                    `;
                    auditoriaInner?.appendChild(msgPermissao);
                }
            }
        }
    } catch (error) {
        console.error('Erro ao carregar auditorias:', error);
        auditoriaSelect.innerHTML = '<option value="">Erro ao carregar auditorias</option>';
    }
});

// ===== VERIFICAR RESPONSÁVEL PELA AUDITORIA =====
auditoriaSelect.addEventListener('change', async function() {
    const auditoriaId = this.value;
    const hasOptions = this.options.length > 1;
    
    if (!hasOptions || !auditoriaId) {
        // DESABILITAR O BOTÃO SE NÃO TIVER AUDITORIA SELECIONADA
        habilitarProximoEtapa1(false);
        return;
    }
    
    const infoBasicasSection = document.getElementById('info-basicas-section');
    if (infoBasicasSection) {
        infoBasicasSection.style.display = 'none';
    }
    
    const msgNaoAutorizado = document.getElementById('msg-nao-autorizado');
    if (msgNaoAutorizado) {
        msgNaoAutorizado.remove();
    }
    
    try {
        const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
        const data = await response.json();
        
        console.log('Verificação de responsável:', data);
        
        if (data.autorizado) {
            // HABILITAR O BOTÃO PRÓXIMO DA SEÇÃO 1
            habilitarProximoEtapa1(true);
            
            // NÃO AVANÇAR AUTOMATICAMENTE - deixar o usuário clicar no botão
            
            if (data.perfil === 'administrador' || data.perfil === 'admin') {
                mostrarToast('Acesso concedido (Administrador).', 'success');
            } else {
                mostrarToast('Você está autorizado a diagnosticar processos nesta auditoria.', 'success');
            }
        } else {
            // DESABILITAR O BOTÃO SE NÃO FOR AUTORIZADO
            habilitarProximoEtapa1(false);
            
            if (infoBasicasSection) {
                infoBasicasSection.style.display = 'none';
            }
            
            const msgDiv = document.createElement('div');
            msgDiv.id = 'msg-nao-autorizado';
            msgDiv.className = 'alert-error';
            msgDiv.innerHTML = `
                <i class="fas fa-lock"></i> 
                <strong>Acesso negado!</strong><br>
                Você não está autorizado a diagnosticar processos nesta auditoria.
                ${data.responsaveis?.length ? `<br>Responsáveis: ${data.responsaveis.join(', ')}` : '<br>Nenhum responsável definido para esta auditoria.'}
            `;
            
            const auditoriaSectionElem = document.getElementById('auditoria-section');
            if (auditoriaSectionElem) {
                auditoriaSectionElem.parentNode.insertBefore(msgDiv, auditoriaSectionElem.nextSibling);
            }
            
            mostrarToast('Você não tem permissão para esta auditoria.', 'error');
        }
    } catch (error) {
        console.error('Erro ao verificar responsável:', error);
        mostrarToast('Erro ao verificar permissão.', 'error');
    }
});

// ===== CONTROLE DO WIZARD =====
let etapaWizard = 1;

async function irParaEtapa(etapa) {
    console.log(`📍 irParaEtapa: mudando para etapa ${etapa}`);

    const etapaAtual = etapaWizard;
    
    // ===== VALIDAÇÃO AO SAIR DA ETAPA 2 (apenas se estiver avançando) =====
    if (etapaAtual === 2 && etapa > etapaAtual) {
        const nomeProcesso = document.getElementById('nome_processo')?.value.trim();
        
        if (!nomeProcesso) {
            mostrarToast('⚠️ Por favor, informe o nome do processo antes de avançar.', 'warning');
            return;
        }
        
        if (executoresSelecionados.length === 0) {
            mostrarToast('⚠️ Selecione pelo menos um executor para o processo.', 'warning');
            return;
        }
        
        // 🔧 Só salva se NÃO for edição
        const modoEdicao = sessionStorage.getItem('modo_edicao');
        if (modoEdicao !== 'true') {
            await salvarInfoBasicasAntesDeAvancar();
        }
    }
    
    // ===== VALIDAÇÃO AO SAIR DA ETAPA 3 (apenas se estiver avançando) =====
    if (etapaAtual === 3 && etapa > etapaAtual) {
        await salvarDetalhesAntesDeAvancar();
    }

    /// SALVAR ETAPA ATUAL
    sessionStorage.setItem('etapa_atual', etapa.toString());

    const etapa1 = document.getElementById('auditoria-section');
    const etapa2 = document.getElementById('info-basicas-section');
    const etapa3 = document.getElementById('detalhes-section');
    const etapa4 = document.getElementById('riscos-section');
    const etapa5 = document.getElementById('visualizar-section');
    
    // Esconder todas
    if (etapa1) etapa1.style.display = 'none';
    if (etapa2) etapa2.style.display = 'none';
    if (etapa3) etapa3.style.display = 'none';
    if (etapa4) etapa4.style.display = 'none';
    if (etapa5) etapa5.style.display = 'none';
    
    // Mostrar etapa selecionada
    if (etapa === 1 && etapa1) etapa1.style.display = 'block';
    if (etapa === 2 && etapa2) etapa2.style.display = 'block';
    if (etapa === 3 && etapa3) etapa3.style.display = 'block';
    if (etapa === 4 && etapa4) etapa4.style.display = 'block';
    if (etapa === 5 && etapa5) etapa5.style.display = 'block';

    sessionStorage.setItem('etapa_atual', etapa.toString());
    
    atualizarProgressoWizard(etapa);
    etapaWizard = etapa;
    
    // ===== CARREGAR DADOS AO ENTRAR NA ETAPA (NOVO) =====
    // Isso resolve o problema de voltar da etapa 4 para 3
    setTimeout(() => {
        if (etapa === 3) {
            carregarDetalhesProcesso();
        }
        if (etapa === 4) {
            carregarRiscosProcesso();
        }
        if (etapa === 5) {
            carregarResumoProcesso();
        }
    }, 50);
}

function atualizarProgressoWizard(etapa) {
    for (let i = 1; i <= 5; i++) {
        const stepElement = document.querySelector(`.step[data-step="${i}"]`);
        if (stepElement) {
            if (i < etapa) {
                stepElement.classList.add('completed');
                stepElement.classList.remove('active');
            } else if (i === etapa) {
                stepElement.classList.add('active');
                stepElement.classList.remove('completed');
            } else {
                stepElement.classList.remove('active', 'completed');
            }
        }
    }
}

// ===== NAVEGAÇÃO (SÓ EXECUTA SE OS ELEMENTOS EXISTIREM) =====
const btnVoltar = document.getElementById('btn-voltar-etapa1');
if (btnVoltar) {
    btnVoltar.addEventListener('click', () => {
        // Restaurar área e auditoria dos valores salvos
        const areaSalva = sessionStorage.getItem('area_id_selecionada');
        const auditoriaSalva = sessionStorage.getItem('auditoria_id');

        if (areaSalva) {
            const areaSelectEl = document.getElementById('area_select');
            if (areaSelectEl) areaSelectEl.value = areaSalva;
        }

        if (auditoriaSalva) {
            const auditoriaSelectEl = document.getElementById('auditoria_select');
            if (auditoriaSelectEl) auditoriaSelectEl.value = auditoriaSalva;
        }
        
        irParaEtapa(1);
    });
}

// ===== NOVO: Botão voltar da etapa 3 para etapa 2 =====
const btnVoltarEtapa2 = document.getElementById('btn-voltar-etapa2');
if (btnVoltarEtapa2) {
    btnVoltarEtapa2.addEventListener('click', () => {
        irParaEtapa(2);
    });
}

const btnProximo = document.getElementById('btn-proximo-etapa3');
if (btnProximo) {
    btnProximo.addEventListener('click', async () => {
        const nomeProcesso = document.getElementById('nome_processo')?.value.trim();
        if (!nomeProcesso) {
            mostrarToast('⚠️ Por favor, informe o nome do processo', 'warning');
            return;
        }
        
        if (executoresSelecionados.length === 0) {
            mostrarToast('⚠️ Selecione pelo menos um executor para o processo', 'warning');
            return;
        }
        
        const areaId = document.getElementById('id_area_selecionado')?.value || areaSelect.value;
        const codigoProcesso = document.getElementById('codigo_processo')?.value;
        const auditoriaId = auditoriaSelect.value;
        const areaSelectElement = document.getElementById('area_select');
        const nomeArea = areaSelectElement.options[areaSelectElement.selectedIndex]?.text || '';
        
        // 🔧 FORÇAR a verificação do modo edição
        const modoEdicao = sessionStorage.getItem('modo_edicao');
        let processoId = sessionStorage.getItem('processo_id');
        
        // 🔧 Se o storage perdeu o ID, tenta recuperar do código do processo? Não, melhor buscar do backend
        console.log('🔍 [DEBUG] modo_edicao:', modoEdicao);
        console.log('🔍 [DEBUG] processo_id do storage:', processoId);
        
        try {
            const payload = {
                nome_processo: nomeProcesso,
                codigo_processo: codigoProcesso,
                id_area: parseInt(areaId),
                nome_area: nomeArea,
                executores_ids: executoresSelecionados.map(e => e.id),
                auditoria_id: parseInt(auditoriaId)
            };

            // 🔧 CORREÇÃO CRÍTICA: Se for edição, MAS o processo_id está vazio, tenta buscar
            if (modoEdicao === 'true') {
                if (processoId) {
                    payload.processo_id = parseInt(processoId);
                    console.log('🔍 [DEBUG] Edição com ID do storage:', payload.processo_id);
                } else {
                    // Tenta buscar o processo pelo código
                    console.log('🔍 [DEBUG] Storage sem ID, tentando buscar pelo código:', codigoProcesso);
                    const buscaResponse = await fetchComAutenticacao(`/api/processo/buscar-por-codigo?codigo=${codigoProcesso}&area_id=${areaId}`);
                    const buscaData = await buscaResponse.json();
                    if (buscaData.id) {
                        payload.processo_id = buscaData.id;
                        sessionStorage.setItem('processo_id', buscaData.id);
                        console.log('🔍 [DEBUG] ID recuperado da busca:', buscaData.id);
                    }
                }
            } else if (processoId && modoEdicao !== 'true') {
                // Se tem ID mas não é modo edição, ainda assim usar (pode ser edição que perdeu o flag)
                payload.processo_id = parseInt(processoId);
                sessionStorage.setItem('modo_edicao', 'true');
                console.log('🔍 [DEBUG] Usando ID mesmo sem flag de edição');
            }

            console.log('🔍 [DEBUG] Payload final:', payload);

            const response = await fetchComAutenticacao('/api/processo/salvar-basico', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (data.success) {
                sessionStorage.setItem('processo_id', data.processo_id);
                sessionStorage.setItem('auditoria_id', auditoriaId);
                sessionStorage.setItem('modo_edicao', 'true');
                
                mostrarToast('✅ Informações básicas salvas!', 'success');
                irParaEtapa(3);
            } else {
                mostrarToast('❌ Erro ao salvar: ' + (data.error || 'Tente novamente'), 'error');
            }
        } catch (error) {
            console.error('Erro ao salvar:', error);
            mostrarToast('❌ Erro ao salvar informações básicas', 'error');
        }
    });
}

// ===== ATUALIZAR ID DA ÁREA QUANDO SELECIONADA =====
function atualizarIdArea() {
    const areaSelect = document.getElementById('area_select');
    const selectedOption = areaSelect.options[areaSelect.selectedIndex];
    const areaNome = selectedOption?.text || '';
    
    // Buscar o ID da área pelo nome (já que o value é o ID)
    const areaId = areaSelect.value;
    
    if (areaId) {
        document.getElementById('id_area_selecionado').value = areaId;
        console.log(`Área selecionada: ID=${areaId}, Nome=${areaNome}`);
        
        // Carregar funcionários da área selecionada
        carregarFuncionariosArea(parseInt(areaId));
    }
}

async function carregarAuditoriasPorArea(areaId) {
    try {
        const response = await fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();
        
        if (data.auditorias && data.auditorias.length > 0) {
            const auditoriaInner = document.getElementById('auditoria-inner');
            if (auditoriaInner) auditoriaInner.style.display = 'block';
            
            auditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            data.auditorias.forEach(aud => {
                const option = document.createElement('option');
                option.value = aud.id;
                option.textContent = `${aud.codigo_auditoria} - ${aud.titulo} (${aud.ano}) ${aud.trimestre}º trim) - ${aud.unidade || ''}`;
                auditoriaSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar auditorias:', error);
    }
}

// ====== ETAPA 3: INFORMAÇÕES DO PROCESSO ======
let detalhesCarregados = false;

// Carregar detalhes salvos ao entrar na etapa 3
async function carregarDetalhesProcesso() {
    console.log('💾 [DENTRO carregarDetalhesProcesso] processo_id:', sessionStorage.getItem('processo_id'));
    const processoId = sessionStorage.getItem('processo_id');
    console.log('🔍 carregarDetalhesProcesso chamado, processoId:', processoId);
    
    if (!processoId) {
        console.log('❌ Nenhum processo_id encontrado');
        return;
    }
    
    // Primeiro, verificar se há dados temporários do rascunho
    const detalhesTemp = sessionStorage.getItem('detalhes_temp');
    console.log('🔍 detalhes_temp:', detalhesTemp);
    
    if (detalhesTemp) {
        const dados = JSON.parse(detalhesTemp);
        console.log('📝 Dados carregados do detalhes_temp:', dados);
        document.getElementById('descricao_processo').value = dados.descricao || '';
        document.getElementById('etapa_ini_processo').value = dados.etapa_ini || '';
        document.getElementById('produto_processo').value = dados.produto || '';
        document.getElementById('etapa_fim_processo').value = dados.etapa_fim || '';
        document.getElementById('objetivo_processo').value = dados.objetivo || '';
        sessionStorage.removeItem('detalhes_temp');
        console.log('✅ Detalhes carregados do sessionStorage');
        return;
    }
    
    // Se não houver dados temporários, buscar do banco
    console.log('🔍 Buscando detalhes do backend...');
    try {
        const response = await fetchComAutenticacao(`/api/processo/${processoId}/dados`);
        const data = await response.json();
        console.log('📦 Dados do backend:', data);
        
        if (data.success) {
            document.getElementById('descricao_processo').value = data.descricao || '';
            document.getElementById('etapa_ini_processo').value = data.etapa_ini || '';
            document.getElementById('produto_processo').value = data.produto || '';
            document.getElementById('etapa_fim_processo').value = data.etapa_fim || '';
            document.getElementById('objetivo_processo').value = data.objetivo || '';
            console.log('✅ Detalhes carregados do backend');
        } else {
            console.log('❌ Erro ao buscar detalhes:', data.error);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar detalhes:', error);
    }
}

// Salvar detlahes do processo
async function salvarDetalhesProcesso() {
    const processoId = sessionStorage.getItem('processo_id');
    if (!processoId) {
        mostrarToast('❌ Nenhum processo em andamento', 'error');
        return false;
    }
    
    const descricao = document.getElementById('descricao_processo')?.value || '';
    const etapaIni = document.getElementById('etapa_ini_processo')?.value || '';
    const produto = document.getElementById('produto_processo')?.value || '';
    const etapaFim = document.getElementById('etapa_fim_processo')?.value || '';
    const objetivo = document.getElementById('objetivo_processo')?.value || '';
    
    try {
        const response = await fetchComAutenticacao('/api/processo/salvar-detalhes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'  // ← VERIFIQUE ESTA LINHA
            },
            body: JSON.stringify({
                processo_id: parseInt(processoId),
                descricao: descricao,
                etapa_ini: etapaIni,
                etapa_fim: etapaFim,
                produto: produto,
                objetivo: objetivo
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('=' .repeat(50));
            console.log('📝 SALVAMENTO ETAPA 3 (Detalhes do Processo)');
            console.log(`   Processo ID: ${processoId}`);
            console.log(`   Descrição: "${descricao.substring(0, 50)}${descricao.length > 50 ? '...' : ''}"`);
            console.log(`   Etapa Inicial: "${etapaIni.substring(0, 50)}${etapaIni.length > 50 ? '...' : ''}"`);
            console.log(`   Produto: "${produto.substring(0, 50)}${produto.length > 50 ? '...' : ''}"`);
            console.log(`   Etapa Final: "${etapaFim.substring(0, 50)}${etapaFim.length > 50 ? '...' : ''}"`);
            console.log(`   Objetivo: "${objetivo.substring(0, 50)}${objetivo.length > 50 ? '...' : ''}"`);
            console.log('=' .repeat(50));
            
            mostrarToast('✅ Detalhes do processo salvos!', 'success');
            return true;
        } else {
            mostrarToast('❌ Erro ao salvar: ' + (data.error || 'Tente novamente'), 'error');
            return false;
        }
    } catch (error) {
        console.error('Erro ao salvar detalhes:', error);
        mostrarToast('❌ Erro ao salvar detalhes do processo', 'error');
        return false;
    }
}

// Event listener para o botão salvar detalhes
const btnSalvarDetalhes = document.getElementById('btn-salvar-detalhes');
if (btnSalvarDetalhes) {
    btnSalvarDetalhes.addEventListener('click', async () => {
        const success = await salvarDetalhesProcesso();
        if (success) {
            irParaEtapa(4); // Avançar para etapa 4 (Riscos)
        }
    });
}

// Botão voltar da etapa 4 para etapa 3
const btnVoltarEtapa3 = document.getElementById('btn-voltar-etapa3');
if (btnVoltarEtapa3) {
    btnVoltarEtapa3.addEventListener('click', () => {
        irParaEtapa(3);
    });
}

// ====== SEÇÃO 4: RISCOS - KANBAN ======
let riscosLista = [];

// ===== FUNÇÃO PARA SALVAR RISCOS NO STORAGE =====
function salvarRiscosNoStorage() {
    sessionStorage.setItem('riscos_temp', JSON.stringify(riscosLista));
    sessionStorage.setItem('riscos_temp_timestamp', Date.now().toString());
}

// ===== MAPA DE RISCO - Versão correta para JavaScript =====
const MAPA_RISCO = {
    // Impacto Muito Alto
    "MUITO ALTO_MUITO ALTO": 15,
    "ALTO_MUITO ALTO": 14,
    "MÉDIO_MUITO ALTO": 13,
    "BAIXO_MUITO ALTO": 12,
    // Impacto Alto
    "MUITO ALTO_ALTO": 11,
    "ALTO_ALTO": 10,
    "MÉDIO_ALTO": 9,
    "BAIXO_ALTO": 8,
    // Impacto Médio
    "MUITO ALTO_MÉDIO": 7,
    "ALTO_MÉDIO": 6,
    "MÉDIO_MÉDIO": 5,
    "BAIXO_MÉDIO": 4,
    // Impacto Baixo
    "MUITO ALTO_BAIXO": 3,
    "ALTO_BAIXO": 2,
    "MÉDIO_BAIXO": 1,
    "BAIXO_BAIXO": 0
};

function calcularScoreRisco(impacto, probabilidade) {
    // 🔧 Garantir que ambos estejam em maiúsculas para a chave
    const impactoUpper = impacto.toUpperCase().trim();
    const probabilidadeUpper = probabilidade.toUpperCase().trim();
    const chave = `${impactoUpper}_${probabilidadeUpper}`;
    
    const score = MAPA_RISCO[chave];
    
    if (score === undefined) {
        console.warn(`⚠️ Combinação não encontrada no mapa: "${chave}"`);
        console.warn(`   Impacto Financeiro: "${impactoUpper}", Probabilidade: "${probabilidadeUpper}"`);
        return 0;
    }
    
    return score;
}

// Determinar nível baseado no score
function getScoreLevel(score) {
    if (score <= 3) return 'low';
    if (score <= 7) return 'medium';
    if (score <= 11) return 'high';
    return 'critical';
}

// Obter texto do nível
function getScoreLevelText(score) {
    if (score <= 3) return 'BAIXA EXPOSIÇÃO';
    if (score <= 7) return 'SOB OBSERVAÇÃO';
    if (score <= 11) return 'ATENÇÃO';
    return 'CRÍTICO';
}

// Renderizar Kanban
function renderizarKanban() {
    // Limpar colunas
    document.getElementById('col-baixo').innerHTML = '';
    document.getElementById('col-medio').innerHTML = '';
    document.getElementById('col-alto').innerHTML = '';
    document.getElementById('col-critico').innerHTML = '';
    
    let countBaixo = 0, countMedio = 0, countAlto = 0, countCritico = 0;
    
    riscosLista.forEach((risco, idx) => {
        // ⭐ CALCULAR SCORE DO RISCO BRUTO
        const score = calcularScoreRisco(risco.impacto || 'Médio', risco.probabilidade || 'Médio');
        const level = getScoreLevel(score);
        const levelText = getScoreLevelText(score);
        
        // ⭐ CALCULAR SCORE DO APETITE (RISCO RESIDUAL)
        const apetiteScore = calcularScoreRisco(
            risco.apetite_impacto || 'Médio', 
            risco.apetite_probabilidade || 'Médio'
        );
        
        // Determinar nível do score do apetite
        let apetiteNivel = '';
        let apetiteNivelTexto = '';
        if (apetiteScore <= 3) {
            apetiteNivel = 'low';
            apetiteNivelTexto = 'BAIXA EXPOSIÇÃO';
        } else if (apetiteScore >= 4 && apetiteScore <= 7) {
            apetiteNivel = 'medium';
            apetiteNivelTexto = 'SOB OBSERVAÇÃO';
        } else if (apetiteScore >= 8 && apetiteScore <= 11) {
            apetiteNivel = 'high';
            apetiteNivelTexto = 'ATENÇÃO';
        } else {
            apetiteNivel = 'critical';
            apetiteNivelTexto = 'CRÍTICO';
        }
        
        // ⭐ ÍCONE PARA O SCORE DO APETITE
        let apetiteIcon = '';
        if (apetiteScore <= 3) apetiteIcon = '';
        else if (apetiteScore <= 7) apetiteIcon = '';
        else if (apetiteScore <= 11) apetiteIcon = '';
        else apetiteIcon = '';
        
        // Criar card
        const card = document.createElement('div');
        card.className = `kanban-card ${level}`;
        card.setAttribute('data-risco-idx', idx);
        
        // Categorias formatadas
        const categoriasHtml = (risco.categorias || []).map(cat => 
            `<span class="kanban-card-categoria-tag">${escapeHtml(cat)}</span>`
        ).join('');
        
        card.innerHTML = `
            <div class="kanban-card-title">${escapeHtml(risco.nome_risco || 'Risco sem nome')}</div>
            <div class="kanban-card-score">
                <span style="font-size: 11px; color: #666;">Magnitude do risco:</span>
                <span class="kanban-card-badge impact">Impacto Financeiro: ${risco.impacto || 'Médio'}</span>
                <span class="kanban-card-badge prob">Probabilidade: ${risco.probabilidade || 'Médio'}</span>
                <span><strong>Score do risco (magnitude): ${score}</strong> (${levelText})</span>
            </div>
            <!-- ⭐ NOVO: Score do Apetite (Risco Residual) -->
            <div class="kanban-card-score" style="margin-top: 4px; padding-top: 4px; border-top: 1px dashed #eee;">
                <span style="font-size: 11px; color: #666;">Apetite do risco:</span>
                <span class="kanban-card-badge impact" style="background: #e8f4f8;">Apetite do Impacto Fin.: ${risco.apetite_impacto || 'Médio'}</span>
                <span class="kanban-card-badge prob" style="background: #e8f4f8;">Apetite da Prob.: ${risco.apetite_probabilidade || 'Médio'}</span>
                <span><strong>Score do apetite (risco residual): ${apetiteScore}</strong> ${apetiteIcon} (${apetiteNivelTexto})</span>
            </div>
            <div class="kanban-card-categorias">
                ${categoriasHtml || '<span class="text-muted">Sem categorias</span>'}
            </div>
            <div class="kanban-card-actions">
                <button class="btn-view-risk" onclick="visualizarRisco(${idx})" title="Visualizar">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn-edit-risk" onclick="editarRisco(${idx})" title="Editar">
                    <i class="fas fa-pencil-alt"></i>
                </button>
            </div>
        `;
        
        // Adicionar à coluna correta (baseado no score do risco bruto)
        if (level === 'low') {
            document.getElementById('col-baixo').appendChild(card);
            countBaixo++;
        } else if (level === 'medium') {
            document.getElementById('col-medio').appendChild(card);
            countMedio++;
        } else if (level === 'high') {
            document.getElementById('col-alto').appendChild(card);
            countAlto++;
        } else {
            document.getElementById('col-critico').appendChild(card);
            countCritico++;
        }
    });
    
    // Atualizar contadores
    document.getElementById('count-baixo').textContent = countBaixo;
    document.getElementById('count-medio').textContent = countMedio;
    document.getElementById('count-alto').textContent = countAlto;
    document.getElementById('count-critico').textContent = countCritico;
    
    // Mostrar mensagem de vazio nas colunas
    if (countBaixo === 0) document.getElementById('col-baixo').innerHTML = '<div class="empty-col-message">Nenhum risco</div>';
    if (countMedio === 0) document.getElementById('col-medio').innerHTML = '<div class="empty-col-message">Nenhum risco</div>';
    if (countAlto === 0) document.getElementById('col-alto').innerHTML = '<div class="empty-col-message">Nenhum risco</div>';
    if (countCritico === 0) document.getElementById('col-critico').innerHTML = '<div class="empty-col-message">Nenhum risco</div>';
}

// Modal control
let modalModo = 'novo'; // novo, editar, visualizar
let modalEditandoIdx = null;

function abrirModal(modo, idx = null) {
    console.log('🔍 abrirModal chamado - modo:', modo, 'idx:', idx);

    if (modo === 'editar' && idx !== null) {
        console.log('🔍 Risco sendo editado:', riscosLista[idx]);
        console.log('📅 Data do risco:', riscosLista[idx].prazo_implantacao);
        carregarRiscoNoModal(riscosLista[idx]);
    }

    modalModo = modo;
    modalEditandoIdx = idx;
    const modal = document.getElementById('modal-risco');
    const title = document.getElementById('modal-title');
    
    if (modo === 'novo') {
        title.textContent = '➕ Novo Risco';
        limparModal();
        // Reativar campos
        document.querySelectorAll('#modal-risco input, #modal-risco textarea, #modal-risco select').forEach(el => {
            el.disabled = false;
        });
    } else if (modo === 'editar' && idx !== null) {
        title.textContent = '✏️ Editar Risco';
        carregarRiscoNoModal(riscosLista[idx]);
        document.querySelectorAll('#modal-risco input, #modal-risco textarea, #modal-risco select').forEach(el => {
            el.disabled = false;
        });
    } else if (modo === 'visualizar' && idx !== null) {
        title.textContent = '👁️ Visualizar Risco';
        carregarRiscoNoModal(riscosLista[idx]);
        // Desabilitar campos para só visualização
        document.querySelectorAll('#modal-risco input, #modal-risco textarea, #modal-risco select').forEach(el => {
            el.disabled = true;
        });
    }
    
    atualizarPreviewScore();
    modal.style.display = 'flex';
}

function fecharModal() {
    document.getElementById('modal-risco').style.display = 'none';
}

function limparCheckboxes(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        const checkboxes = container.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = false);
    }
}

function limparModal() {
    document.getElementById('modal-nome_risco').value = '';
    document.getElementById('modal-fator_risco').value = '';
    document.getElementById('modal-melhoria').value = '';
    
    limparCheckboxes('categorias-checkboxes');
    limparCheckboxes('causa-checkboxes');
    
    // ⭐ RISCO BRUTO - Valores em MAIÚSCULAS
    document.getElementById('modal-impacto').value = 'MÉDIO';
    document.getElementById('modal-probabilidade').value = 'MÉDIO';
    document.getElementById('modal-motivo_risco').value = '';
    
    // ⭐ APETITE (RISCO RESIDUAL)
    document.getElementById('apetite_impacto').value = 'MÉDIO';
    document.getElementById('apetite_probabilidade').value = 'MÉDIO';
    
    document.getElementById('modal-como-tratar').value = '';
    document.getElementById('modal-desc-tratamento').value = '';
    document.getElementById('modal-prazo-implantacao').value = '';
    
    atualizarPreviewScore();
    atualizarPreviewApetite();
}

function carregarRiscoNoModal(risco) {
    document.getElementById('modal-nome_risco').value = risco.nome_risco || '';
    document.getElementById('modal-fator_risco').value = risco.fator_risco || '';
    document.getElementById('modal-melhoria').value = risco.melhoria || '';

    // Categorias
    const categoriasSelecionadas = risco.categorias || [];
    document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => {
        cb.checked = categoriasSelecionadas.includes(cb.value.toUpperCase());
    });

    // Causas
    const causasSelecionadas = risco.categoria_causa || [];
    document.querySelectorAll('#causa-checkboxes input[type="checkbox"]').forEach(cb => {
        cb.checked = causasSelecionadas.includes(cb.value.toUpperCase());
    });

    // Verificar se tem "OUTRA" categoria selecionada
    const temOutra = categoriasSelecionadas.some(cat => 
        !['RISCO FINANCEIRO', 'RISCO LEGAL', 'RISCO INERENTE', 'RISCO DE TI', 'RISCO REPUTACIONAL', 'RISCO DE INTEGRIDADE', 'RISCO AMBIENTAL'].includes(cat.toUpperCase())
    );
    if (temOutra) {
        const checkOutra = document.getElementById('check-outra-categoria');
        if (checkOutra) {
            checkOutra.checked = true;
            document.getElementById('outra-categoria-container').style.display = 'block';
            const outras = categoriasSelecionadas.filter(cat => 
                !['RISCO FINANCEIRO', 'RISCO LEGAL', 'RISCO INERENTE', 'RISCO DE TI', 'RISCO REPUTACIONAL', 'RISCO DE INTEGRIDADE', 'RISCO AMBIENTAL'].includes(cat.toUpperCase())
            );
            document.getElementById('outra-categoria-texto').value = outras.join(', ');
        }
    }

    // ⭐ RISCO BRUTO - Garantir que os selects sejam preenchidos corretamente
    document.getElementById('modal-impacto').value = (risco.impacto || 'MÉDIO').toUpperCase();
    document.getElementById('modal-probabilidade').value = (risco.probabilidade || 'MÉDIO').toUpperCase();
    document.getElementById('modal-motivo_risco').value = risco.motivo_risco || '';
    
    // ⭐ APETITE (RISCO RESIDUAL)
    document.getElementById('apetite_impacto').value = (risco.apetite_impacto || 'MÉDIO').toUpperCase();
    document.getElementById('apetite_probabilidade').value = (risco.apetite_probabilidade || 'MÉDIO').toUpperCase();

    document.getElementById('modal-como-tratar').value = risco.como_tratar || '';
    document.getElementById('modal-desc-tratamento').value = risco.desc_tratamento || '';
    document.getElementById('modal-prazo-implantacao').value = risco.prazo_implantacao || '';
    
    // ⭐ ATUALIZAR OS SCORES
    atualizarPreviewScore();
    atualizarPreviewApetite();
}

function salvarDoModal() {
    const nome = document.getElementById('modal-nome_risco').value.trim().toUpperCase();
    if (!nome) {
        mostrarToast('⚠️ Nome do risco é obrigatório', 'warning');
        return;
    }

    // RISCO BRUTO - Os valores já vêm em maiúsculas dos selects
    const impacto = document.getElementById('modal-impacto').value;
    const probabilidade = document.getElementById('modal-probabilidade').value;
    const motivo = document.getElementById('modal-motivo_risco').value.trim().toUpperCase();

    // RISCO RESIDUAL (APETITE AO RISCO)
    const apetiteImpacto = document.getElementById('apetite_impacto').value;
    const apetiteProbabilidade = document.getElementById('apetite_probabilidade').value;

    // Coletar categorias marcadas
    const categorias = [];
    document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]:checked').forEach(cb => {
        if (cb.value === 'OUTRA') {
            const texto = document.getElementById('outra-categoria-texto').value.trim().toUpperCase();
            if (texto) categorias.push(texto);
        } else {
            categorias.push(cb.value.toUpperCase());
        }
    });

    // Coletar causas marcadas
    const categoriaCausa = [];
    document.querySelectorAll('#causa-checkboxes input[type="checkbox"]:checked').forEach(cb => {
        categoriaCausa.push(cb.value.toUpperCase());
    });

    const novoRisco = {
        nome_risco: nome,
        fator_risco: document.getElementById('modal-fator_risco').value.trim().toUpperCase(),
        melhoria: document.getElementById('modal-melhoria').value.trim().toUpperCase(),
        categorias: categorias,
        categoria_causa: categoriaCausa,
        impacto: impacto, // Já em maiúsculas
        probabilidade: probabilidade, // Já em maiúsculas
        motivo_risco: motivo,
        apetite_impacto: apetiteImpacto, // Já em maiúsculas
        apetite_probabilidade: apetiteProbabilidade, // Já em maiúsculas
        como_tratar: document.getElementById('modal-como-tratar').value.trim().toUpperCase(),
        desc_tratamento: document.getElementById('modal-desc-tratamento').value.trim().toUpperCase(),
        prazo_implantacao: document.getElementById('modal-prazo-implantacao').value.trim().toUpperCase()
    };

    if (modalModo === 'novo') {
        riscosLista.push(novoRisco);
        mostrarToast('✅ Risco adicionado!', 'success');
    } else if (modalModo === 'editar' && modalEditandoIdx !== null) {
        if (riscosLista[modalEditandoIdx].id) {
            novoRisco.id = riscosLista[modalEditandoIdx].id;
        }
        riscosLista[modalEditandoIdx] = novoRisco;
        mostrarToast('✅ Risco atualizado!', 'success');
    }

    salvarRiscosNoStorage();

    renderizarKanban();
    fecharModal();
}

// Evento para mostrar/esconder card de categorias
// Evento para mostrar/esconder card de categorias
document.addEventListener('DOMContentLoaded', function() {
    // =============================================
    // 1. Categorias do Risco
    // =============================================
    const helpCat = document.getElementById('help-categorias-icon');
    const infoCat = document.getElementById('info-categorias');
    const closeCat = document.getElementById('fechar-info-categorias');
    
    if (helpCat && infoCat) {
        helpCat.addEventListener('click', () => {
            infoCat.style.display = infoCat.style.display === 'none' ? 'block' : 'none';
        });
        if (closeCat) {
            closeCat.addEventListener('click', () => {
                infoCat.style.display = 'none';
            });
        }
    }

    // =============================================
    // 2. ⭐ NOVO: Categorias de Causa
    // =============================================
    const helpCatCausa = document.getElementById('help-categorias-causa-icon');
    const infoCatCausa = document.getElementById('info-categorias-causa');
    const closeCatCausa = document.getElementById('fechar-info-categorias-causa');

    if (helpCatCausa && infoCatCausa) {
        helpCatCausa.addEventListener('click', () => {
            infoCatCausa.style.display = infoCatCausa.style.display === 'none' ? 'block' : 'none';
        });
        if (closeCatCausa) {
            closeCatCausa.addEventListener('click', () => {
                infoCatCausa.style.display = 'none';
            });
        }
    }

    // =============================================
    // 3. Campo "Outra" Categoria
    // =============================================
    const checkOutra = document.getElementById('check-outra-categoria');
    const containerOutra = document.getElementById('outra-categoria-container');
    const textoOutra = document.getElementById('outra-categoria-texto');

    if (checkOutra && containerOutra) {
        checkOutra.addEventListener('change', function() {
            if (this.checked) {
                containerOutra.style.display = 'block';
                if (textoOutra) textoOutra.focus();
            } else {
                containerOutra.style.display = 'none';
                if (textoOutra) textoOutra.value = '';
            }
        });
    }

    // =============================================
    // 4. Critérios de Avaliação
    // =============================================
    const helpCriterios = document.getElementById('help-criterios-icon');
    const infoCriterios = document.getElementById('info-criterios');
    const closeCriterios = document.getElementById('fechar-info-criterios');

    if (helpCriterios && infoCriterios) {
        helpCriterios.addEventListener('click', () => {
            infoCriterios.style.display = infoCriterios.style.display === 'none' ? 'block' : 'none';
        });
        if (closeCriterios) {
            closeCriterios.addEventListener('click', () => {
                infoCriterios.style.display = 'none';
            });
        }
    }

    // =============================================
    // 5. ⭐ FECHAR CARDS AO CLICAR FORA
    // =============================================
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

        // Fechar critérios de avaliação
        const infoCriterios = document.getElementById('info-criterios');
        const helpCriterios = document.getElementById('help-criterios-icon');
        if (infoCriterios && helpCriterios) {
            if (!infoCriterios.contains(e.target) && !helpCriterios.contains(e.target)) {
                infoCriterios.style.display = 'none';
            }
        }
    });

    // =============================================
    // 6. Restaurar Filtros
    // =============================================
    restaurarFiltros();

    // =============================================
    // 7. Habilitar Navegação entre Etapas
    // =============================================
    habilitarNavegacaoEtapas();
    
    // =============================================
    // 8. Event Listeners da Etapa 5
    // =============================================
    const btnVoltarEtapa4 = document.getElementById('btn-voltar-etapa4');
    if (btnVoltarEtapa4) {
        btnVoltarEtapa4.addEventListener('click', () => {
            irParaEtapa(4);
        });
    }
    
    const btnFinalizar = document.getElementById('btn-finalizar-processo');
    if (btnFinalizar) {
        btnFinalizar.addEventListener('click', () => {
            finalizarWizard();
        });
    }

    console.log('✅ DOM carregado - Todos os cards informativos configurados!');
});

function visualizarRisco(idx) {
    console.log('🔵 FUNÇÃO visualizarRisco CHAMADA');
    
    const risco = riscosLista[idx];
    if (!risco) {
        mostrarToast('Risco não encontrado', 'error');
        return;
    }
    
    // ===== 1. PREENCHER CAMPOS DE TEXTO =====
    document.getElementById('vis-nome_risco').textContent = risco.nome_risco || '-';
    document.getElementById('vis-fator_risco').textContent = risco.fator_risco || '-';
    document.getElementById('vis-melhoria').textContent = risco.melhoria || '-';
    document.getElementById('vis-categorias').textContent = (risco.categorias || []).join(', ') || '-';
    document.getElementById('vis-categoria-causa').textContent = (risco.categoria_causa || []).join(', ') || '-';
    document.getElementById('vis-motivo_risco').textContent = risco.motivo_risco || '-';
    document.getElementById('vis-como-tratar').textContent = risco.como_tratar || '-';
    document.getElementById('vis-desc-tratamento').textContent = risco.desc_tratamento || '-';
    document.getElementById('vis-prazo-implantacao').textContent = risco.prazo_implantacao || '-';
    
    // ===== 2. PREENCHER CAMPOS DE IMPACTO E PROBABILIDADE (em maiúsculas) =====
    // IMPORTANTE: Os valores no banco estão em MAIÚSCULAS (BAIXO, MÉDIO, ALTO, MUITO ALTO)
    const impacto = (risco.impacto || 'MÉDIO').toUpperCase();
    const probabilidade = (risco.probabilidade || 'MÉDIO').toUpperCase();
    const apetiteImpacto = (risco.apetite_impacto || 'MÉDIO').toUpperCase();
    const apetiteProbabilidade = (risco.apetite_probabilidade || 'MÉDIO').toUpperCase();
    
    document.getElementById('vis-impacto').textContent = impacto;
    document.getElementById('vis-probabilidade').textContent = probabilidade;
    document.getElementById('vis-apetite-impacto').textContent = apetiteImpacto;
    document.getElementById('vis-apetite-probabilidade').textContent = apetiteProbabilidade;
    
    // ===== 3. CALCULAR SCORES (usando os valores em maiúsculas) =====
    const score = calcularScoreRisco(impacto, probabilidade);
    const apetiteScore = calcularScoreRisco(apetiteImpacto, apetiteProbabilidade);
    
    // ===== 4. DETERMINAR NÍVEL E COR DO SCORE =====
    let nivelTexto = '';
    let corScore = '';
    let emoji = '';
    
    if (score <= 3) {
        nivelTexto = 'BAIXA EXPOSIÇÃO';
        corScore = '#28a745';  // Verde
        emoji = '🟢';
    } else if (score <= 7) {
        nivelTexto = 'SOB OBSERVAÇÃO';
        corScore = '#ffc107';  // Amarelo
        emoji = '🟡';
    } else if (score <= 11) {
        nivelTexto = 'ATENÇÃO';
        corScore = '#fd7e14';  // Laranja
        emoji = '🟠';
    } else {
        nivelTexto = 'CRÍTICO';
        corScore = '#dc3545';  // Vermelho
        emoji = '🔴';
    }
    
    // ===== 5. DETERMINAR NÍVEL DO APETITE =====
    const apetiteLevel = getScoreLevelText(apetiteScore);
    
    // ===== 6. EXIBIR SCORES =====
    // Score do risco bruto (com emoji e cor)
    document.getElementById('vis-score').innerHTML = `
        <span style="font-weight: bold; color: ${corScore};">${emoji} ${score}</span> 
        (${nivelTexto})
    `;
    
    // Score do apetite
    document.getElementById('vis-score-apetite').textContent = `${apetiteScore} (${apetiteLevel})`;
    
    // ===== 7. ABRIR MODAL =====
    const modal = document.getElementById('modal-visualizar-risco');
    if (modal) {
        modal.style.display = 'flex';
        modal.style.visibility = 'visible';
        modal.style.opacity = '1';
        modal.classList.add('visible');
        console.log('✅ Modal de visualização aberto');
    } else {
        console.error('❌ Modal não encontrado!');
        mostrarToast('Erro: Modal não encontrado', 'error');
    }
}

function editarRisco(idx) {
    abrirModal('editar', idx);
}

function adicionarRisco() {
    abrirModal('novo');
}

function atualizarPreviewScore() {
    const impacto = document.getElementById('modal-impacto').value;
    const probabilidade = document.getElementById('modal-probabilidade').value;
    const score = calcularScoreRisco(impacto, probabilidade);
    const levelText = getScoreLevelText(score);
    
    let corPreview = '';
    if (score <= 4) corPreview = '#d4edda';
    else if (score <= 9) corPreview = '#fff3cd';
    else if (score <= 15) corPreview = '#ffe5d0';
    else corPreview = '#f8d7da';
    
    const previewDiv = document.getElementById('modal-score-preview');
    previewDiv.style.backgroundColor = corPreview;
    previewDiv.innerHTML = `<strong>Score: ${score}</strong> (${levelText})`;
}

// ===== ATUALIZAR PREVIEW DO SCORE DO APETITE =====
function atualizarPreviewApetite() {
    const impacto = document.getElementById('apetite_impacto')?.value;
    const probabilidade = document.getElementById('apetite_probabilidade')?.value;
    
    if (!impacto || !probabilidade) return;
    
    const score = calcularScoreRisco(impacto, probabilidade);
    const levelText = getScoreLevelText(score);
    
    const previewDiv = document.getElementById('apetite-score-preview');
    const scoreSpan = document.getElementById('preview-apetite-score');
    
    if (previewDiv) {
        let corPreview = '';
        if (score <= 3) corPreview = '#d4edda';
        else if (score <= 7) corPreview = '#fff3cd';
        else if (score <= 11) corPreview = '#ffe5d0';
        else corPreview = '#f8d7da';
        
        previewDiv.style.backgroundColor = corPreview;
        previewDiv.innerHTML = `<strong>Score do Apetite:</strong> ${score} (${levelText})`;
    }
}

function carregarRiscosProcesso() {
    const processoId = sessionStorage.getItem('processo_id');
    if (!processoId) return;
    
    // ⭐ PRIORIDADE: BUSCAR DO BANCO DE DADOS
    fetchComAutenticacao(`/api/processo/${processoId}/riscos`)
        .then(response => response.json())
        .then(data => {
            if (data.riscos && data.riscos.length > 0) {
                // Converter riscos do banco para o formato usado no frontend
                riscosLista = data.riscos.map(risco => ({
                    id: risco.id,
                    nome_risco: risco.nome_risco || '',
                    fator_risco: risco.fator_risco || '',
                    melhoria: risco.melhoria || '',
                    impacto: risco.impacto || 'MÉDIO',
                    probabilidade: risco.probabilidade || 'MÉDIO',
                    motivo_risco: risco.motivo_risco || '',
                    apetite_impacto: risco.apetite_impacto || 'MÉDIO',
                    apetite_probabilidade: risco.apetite_probabilidade || 'MÉDIO',
                    categorias: risco.categoria ? risco.categoria.split(',').map(c => c.trim()) : [],
                    categoria_causa: risco.causas ? risco.causas.split(',').map(c => c.trim()) : [],
                    como_tratar: risco.tratamento_risco || '',
                    desc_tratamento: risco.descricao_tratamento || '',
                    prazo_implantacao: risco.prazo_implantacao || '',
                    score_risco: risco.score_risco || 0
                }));
                
                // Salvar no storage local
                salvarRiscosNoStorage();
                renderizarKanban();
            } else {
                // Se não tem riscos no banco, verificar storage local
                const riscosTemp = sessionStorage.getItem('riscos_temp');
                if (riscosTemp) {
                    riscosLista = JSON.parse(riscosTemp);
                    renderizarKanban();
                } else {
                    riscosLista = [];
                    renderizarKanban();
                }
            }
        })
        .catch(error => {
            console.error('Erro ao carregar riscos:', error);
            // Fallback: tentar do storage local
            const riscosTemp = sessionStorage.getItem('riscos_temp');
            if (riscosTemp) {
                riscosLista = JSON.parse(riscosTemp);
                renderizarKanban();
            }
        });
}

// ⭐ FUNÇÃO PARA SALVAR RISCOS NO BACKEND (APENAS QUANDO O USUÁRIO CLICAR)
async function salvarRiscosNoBackend() {
    const processoId = sessionStorage.getItem('processo_id');
    if (!processoId) {
        mostrarToast('❌ Nenhum processo em andamento', 'error');
        return false;
    }
    
    if (riscosLista.length === 0) {
        mostrarToast('ℹ️ Nenhum risco para salvar', 'info');
        return false;
    }
    
    // Validar campos obrigatórios
    let temErro = false;
    let riscosComErro = [];
    riscosLista.forEach((risco, idx) => {
        if (!risco.nome_risco?.trim()) {
            riscosComErro.push(idx + 1);
            temErro = true;
        }
    });
    
    if (temErro) {
        mostrarToast(`⚠️ Risco(s) ${riscosComErro.join(', ')}: Nome é obrigatório`, 'warning');
        return false;
    }
    
    // ⭐ MOSTRAR INDICADOR DE CARREGAMENTO
    const btnSalvar = document.getElementById('btn-salvar-riscos');
    if (btnSalvar) {
        btnSalvar.disabled = true;
        btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    }
    
    try {
        const response = await fetchComAutenticacao('/api/processo/salvar-riscos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                processo_id: parseInt(processoId),
                riscos: riscosLista
                // ⭐ REMOVEMOS o sobrescrever: true porque não é mais necessário
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ ${riscosLista.length} riscos salvos com sucesso!`);
            mostrarToast(`✅ ${riscosLista.length} riscos salvos com sucesso!`, 'success');
            
            // ⭐ ATUALIZAR IDs DOS RISCOS (se a API retornar)
            if (data.riscos) {
                // Se a API retornou a lista completa com IDs atualizados
                riscosLista = data.riscos;
                salvarRiscosNoStorage();
            } else if (data.riscos_salvos) {
                // Se a API retornou apenas os IDs salvos (formato antigo)
                data.riscos_salvos.forEach((riscoSalvo, idx) => {
                    if (idx < riscosLista.length) {
                        riscosLista[idx].id = riscoSalvo.id;
                    }
                });
                salvarRiscosNoStorage();
            }
            
            // ⭐ RECARREGAR OS RISCOS DO BANCO PARA GARANTIR DADOS ATUALIZADOS
            await carregarRiscosProcesso();
            
            return true;
        } else {
            mostrarToast('❌ Erro ao salvar riscos: ' + (data.error || 'Tente novamente'), 'error');
            return false;
        }
    } catch (error) {
        console.error('Erro ao salvar riscos:', error);
        mostrarToast('❌ Erro ao salvar riscos. Tente novamente.', 'error');
        return false;
    } finally {
        // ⭐ RESTAURAR BOTÃO
        if (btnSalvar) {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = 'Salvar Riscos';
        }
    }
}

// Event listeners
const btnAdicionarRiscoModal = document.getElementById('btn-adicionar-risco');
if (btnAdicionarRiscoModal) {
    btnAdicionarRiscoModal.addEventListener('click', adicionarRisco);
}

const btnFecharModal = document.getElementById('btn-fechar-modal');
const btnCancelarModal = document.getElementById('btn-cancelar-modal');
if (btnFecharModal) btnFecharModal.addEventListener('click', fecharModal);
if (btnCancelarModal) btnCancelarModal.addEventListener('click', fecharModal);

const btnSalvarModal = document.getElementById('btn-salvar-modal');
if (btnSalvarModal) {
    btnSalvarModal.addEventListener('click', salvarDoModal);
}



// ⭐ EVENT LISTENERS PARA O RISCO BRUTO
document.getElementById('modal-impacto')?.addEventListener('change', atualizarPreviewScore);
document.getElementById('modal-probabilidade')?.addEventListener('change', atualizarPreviewScore);

// ⭐ EVENT LISTENERS PARA O APETITE (RISCO RESIDUAL)
document.getElementById('apetite_impacto')?.addEventListener('change', atualizarPreviewApetite);
document.getElementById('apetite_probabilidade')?.addEventListener('change', atualizarPreviewApetite);

// Botão salvar todos os riscos (backup)
const btnSalvarTodosRiscos = document.getElementById('btn-salvar-riscos');
if (btnSalvarTodosRiscos) {
    btnSalvarTodosRiscos.addEventListener('click', async () => {
        if (riscosLista.length === 0) {
            mostrarToast('ℹ️ Nenhum risco para salvar', 'info');
            return;
        }
        
        // Validar campos obrigatórios
        let temErro = false;
        let riscosComErro = [];
        riscosLista.forEach((risco, idx) => {
            if (!risco.nome_risco?.trim()) {
                riscosComErro.push(idx + 1);
                temErro = true;
            }
        });
        
        if (temErro) {
            mostrarToast(`⚠️ Risco(s) ${riscosComErro.join(', ')}: Nome é obrigatório`, 'warning');
            return;
        }
        
        // ⭐ SALVAR UMA ÚNICA VEZ
        await salvarRiscosNoBackend();
        
        // Avançar para a etapa 5 (visualização)
        irParaEtapa(5);
        mostrarToast('✅ Riscos salvos com sucesso!', 'success');
    });
}

function removerRisco(idx) {
    if (confirm(`Tem certeza que deseja remover este risco?`)) {
        riscosLista.splice(idx, 1);
        salvarRiscosNoStorage();
        
        renderizarKanban();
        mostrarToast('Risco removido', 'info');
    }
}
// ===== AUTO-SAVE ETAPA 2 (Nome + Executores) =====
let autoSaveTimeout = null;

async function autoSaveEtapa2() {
    // 🔧 VERIFICAR SE É MODO EDIÇÃO - NÃO EXECUTAR AUTO-SAVE
    const modoEdicao = sessionStorage.getItem('modo_edicao');
    const processoIdExistente = sessionStorage.getItem('processo_id');
    
    if (modoEdicao === 'true' && processoIdExistente) {
        console.log('✏️ Modo edição ativo - AUTO-SAVE desabilitado');
        return;
    }
    
    const nomeProcesso = document.getElementById('nome_processo')?.value.trim().toUpperCase();
    const executores = executoresSelecionados;
    const entrevistado = document.getElementById('entrevistado_processo')?.value.trim().toUpperCase() || '';
    
    if (!nomeProcesso || executores.length === 0) return;
    
    const areaId = document.getElementById('id_area_selecionado')?.value || areaSelect.value;
    const auditoriaId = auditoriaSelect.value;
    const codigoProcesso = document.getElementById('codigo_processo')?.value;
    const areaSelectElement = document.getElementById('area_select');
    const nomeArea = areaSelectElement.options[areaSelectElement.selectedIndex]?.text || '';
    
    try {
        const response = await fetchComAutenticacao('/api/processo/salvar-basico', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome_processo: nomeProcesso,
                codigo_processo: codigoProcesso,
                id_area: parseInt(areaId),
                nome_area: nomeArea,
                executores_ids: executores.map(e => e.id),
                auditoria_id: parseInt(auditoriaId),
                entrevistado: entrevistado
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 🔧 Só atualiza o storage se NÃO for edição
            if (modoEdicao !== 'true') {
                sessionStorage.setItem('processo_id', data.processo_id);
                sessionStorage.setItem('auditoria_id', auditoriaId);
                sessionStorage.setItem('modo_edicao', 'true');
                console.log('💾 Auto-save etapa 2 realizado (novo processo)');
            } else {
                console.log('💾 Auto-save etapa 2 ignorado (modo edição)');
            }
        }
    } catch (error) {
        console.error('Erro auto-save etapa 2:', error);
    }
}

// Disparar auto-save no nome do processo
if (nomeProcessoInput) {
    nomeProcessoInput.addEventListener('input', () => {
        if (autoSaveTimeout) clearTimeout(autoSaveTimeout);
        autoSaveTimeout = setTimeout(autoSaveEtapa2, 1000);
    });
}

// ===== AUTO-SAVE ETAPA 3 (Detalhes) =====
let autoSaveDetalhesTimeout = null;

async function autoSaveEtapa3() {
    const processoId = sessionStorage.getItem('processo_id');
    if (!processoId) return;
    
    const descricao = document.getElementById('descricao_processo')?.value.trim().toUpperCase() || '';
    const etapaIni = document.getElementById('etapa_ini_processo')?.value.trim().toUpperCase() || '';
    const produto = document.getElementById('produto_processo')?.value.trim().toUpperCase() || '';
    const etapaFim = document.getElementById('etapa_fim_processo')?.value.trim().toUpperCase() || '';
    const objetivo = document.getElementById('objetivo_processo')?.value.trim().toUpperCase() || '';
    
    try {
        const response = await fetchComAutenticacao('/api/processo/salvar-detalhes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                processo_id: parseInt(processoId),
                descricao: descricao,
                etapa_ini: etapaIni,
                etapa_fim: etapaFim,
                produto: produto,
                objetivo: objetivo
            })
        });
        
        const data = await response.json();
        if (data.success) {
            console.log('💾 Auto-save etapa 3 realizado');
        }
    } catch (error) {
        console.error('Erro auto-save etapa 3:', error);
        sessionStorage.setItem('rascunho_etapa3', JSON.stringify({
            descricao, etapaIni, produto, etapaFim, objetivo
        }));
    }
}

// Adicionar listeners para os campos da etapa 3
const camposEtapa3 = ['descricao_processo', 'etapa_ini_processo', 'produto_processo', 'etapa_fim_processo', 'objetivo_processo'];
camposEtapa3.forEach(campoId => {
    const campo = document.getElementById(campoId);
    if (campo) {
        campo.addEventListener('input', () => {
            if (autoSaveDetalhesTimeout) clearTimeout(autoSaveDetalhesTimeout);
            autoSaveDetalhesTimeout = setTimeout(autoSaveEtapa3, 1000);
        });
    }
});

// ===== AUTO-SAVE ETAPA 4 (Riscos) =====
let autoSaveRiscosTimeout = null;

async function autoSaveEtapa4() {
    const processoId = sessionStorage.getItem('processo_id');
    if (!processoId || riscosLista.length === 0) return;
    
    console.log('=' .repeat(50));
    console.log('📝 AUTO-SAVE ETAPA 4 (Riscos)');
    console.log(`   Processo ID: ${processoId}`);
    console.log(`   Total de riscos: ${riscosLista.length}`);
    
    // Detalhar cada risco
    riscosLista.forEach((risco, idx) => {
        console.log(`   Risco ${idx + 1}:`);
        console.log(`      - ID: ${risco.id || 'novo'}`);
        console.log(`      - Nome: ${risco.nome_risco || '(não informado)'}`);
        console.log(`      - Impacto: ${risco.impacto}`);
        console.log(`      - Probabilidade: ${risco.probabilidade}`);
        console.log(`      - Categorias: ${(risco.categorias || []).join(', ') || '(nenhuma)'}`);
    });

    try {
        const response = await fetchComAutenticacao('/api/processo/salvar-riscos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                processo_id: parseInt(processoId),
                riscos: riscosLista
            })
        });
        
        const data = await response.json();
        if (data.success) {
            console.log(`   ✅ ${riscosLista.length} riscos salvos com sucesso!`);
            console.log('=' .repeat(50));
            salvarRiscosNoStorage();
        }
    } catch (error) {
        console.error(`   ❌ Erro ao salvar riscos: ${error}`);
        console.log('=' .repeat(50));
        salvarRiscosNoStorage();
    }
}

// ===== VERIFICAR RESPONSÁVEL PELA AUDITORIA (para o filtro) =====
async function verificarResponsavelEAcao(auditoriaId, onAutorizado, onNaoAutorizado) {
    // ⭐ SE NÃO TEM AUDITORIA, NÃO FAZ VERIFICAÇÃO
    if (!auditoriaId || auditoriaId === '' || auditoriaId === 'null') {
        console.log('ℹ️ Nenhuma auditoria selecionada - ignorando verificação');
        if (onAutorizado) onAutorizado();
        return;
    }
    
    try {
        const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
        
        // Verificar se a resposta é ok
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.autorizado) {
            if (onAutorizado) onAutorizado();
        } else {
            if (onNaoAutorizado) onNaoAutorizado();
            mostrarToast('Você não tem permissão para acessar esta auditoria.', 'error');
        }
    } catch (error) {
        console.error('Erro ao verificar responsável:', error);
        // ⭐ Em caso de erro, assume que não está autorizado
        if (onNaoAutorizado) onNaoAutorizado();
        mostrarToast('Erro ao verificar permissão.', 'error');
    }
}

// Eventos para fechar modal de visualização
const btnFecharVisualizar = document.getElementById('btn-fechar-visualizar');
const btnFecharVisualizarModal = document.getElementById('btn-fechar-visualizar-modal');
const modalVisualizar = document.getElementById('modal-visualizar-risco');

function fecharModalVisualizar() {
    if (modalVisualizar) modalVisualizar.style.display = 'none';
}

if (btnFecharVisualizar) {
    btnFecharVisualizar.addEventListener('click', fecharModalVisualizar);
}
if (btnFecharVisualizarModal) {
    btnFecharVisualizarModal.addEventListener('click', fecharModalVisualizar);
}


// ===== FECHAR MODAL DE VISUALIZAÇÃO DE RISCO =====
function fecharModalVisualizarRisco() {
    console.log('🔴 Fechando modal de visualização...');
    
    const modal = document.getElementById('modal-visualizar-risco');
    if (modal) {
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
        modal.style.opacity = '0';
        modal.classList.remove('visible');
        console.log('✅ Modal fechado');
    }
    
    // Remover overlay de fallback se existir
    const overlays = document.querySelectorAll('div[style*="2147483646"]');
    overlays.forEach(el => {
        if (el.parentNode) {
            el.parentNode.removeChild(el);
        }
    });
}

// ===== CONFIGURAR EVENT LISTENERS DO MODAL =====
function configurarEventListenersModalVisualizar() {
    console.log('🔧 Configurando event listeners do modal de visualização...');
    
    // Botão X (no header)
    const btnClose = document.getElementById('btn-fechar-visualizar-modal');
    if (btnClose) {
        // Remover listeners antigos para evitar duplicação
        const newBtn = btnClose.cloneNode(true);
        btnClose.parentNode.replaceChild(newBtn, btnClose);
        newBtn.addEventListener('click', fecharModalVisualizarRisco);
        console.log('✅ Botão X configurado');
    } else {
        console.warn('⚠️ Botão btn-fechar-visualizar-modal não encontrado');
    }
    
    // Botão Fechar (no footer)
    const btnFooter = document.getElementById('btn-fechar-visualizar');
    if (btnFooter) {
        const newBtn = btnFooter.cloneNode(true);
        btnFooter.parentNode.replaceChild(newBtn, btnFooter);
        newBtn.addEventListener('click', fecharModalVisualizarRisco);
        console.log('✅ Botão Fechar configurado');
    } else {
        console.warn('⚠️ Botão btn-fechar-visualizar não encontrado');
    }
    
    // Clicar fora do modal (no overlay)
    const modal = document.getElementById('modal-visualizar-risco');
    if (modal) {
        // Remover listener antigo
        const newModal = modal.cloneNode(true);
        modal.parentNode.replaceChild(newModal, modal);
        newModal.addEventListener('click', function(e) {
        
        });
        console.log('✅ Evento de clique fora configurado');
    }
}

// Chamar após o DOM carregar
document.addEventListener('DOMContentLoaded', function() {
    configurarEventListenersModalVisualizar();
    
    // Também chamar novamente após qualquer renderização do kanban
    // (pois o modal pode ser recriado)
    setTimeout(configurarEventListenersModalVisualizar, 500);
});

// ===== FUNÇÃO PARA FECHAR O MODAL =====
function fecharModalRisco() {
    const modal = document.getElementById('modal-visualizar-risco');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('visible');
        console.log('✅ Modal fechado');
    }
}

// Eventos do modal de visualização do processo
const modalVisProcesso = document.getElementById('modal-visualizar-processo');
const btnFecharVisProcesso = document.getElementById('btn-fechar-visualizar-processo');
const btnFecharVisProcessoFooter = document.getElementById('btn-fechar-visualizar-processo-footer');

function fecharModalVisualizarProcesso() {
    if (modalVisProcesso) modalVisProcesso.style.display = 'none';
}

if (btnFecharVisProcesso) btnFecharVisProcesso.addEventListener('click', fecharModalVisualizarProcesso);
if (btnFecharVisProcessoFooter) btnFecharVisProcessoFooter.addEventListener('click', fecharModalVisualizarProcesso);


// ===== FUNÇÃO PARA EDITAR PROCESSO EXISTENTE ======
function abrirModalEdicao(processoId, processoCodigo) {
    console.log('✏️ Abrindo edição do processo:', processoId, '-', processoCodigo);

    // ⭐ LIMPEZA COMPLETA ANTES DE CARREGAR
    // Limpar sessionStorage (mantendo apenas filtros)
    const areaSalva = sessionStorage.getItem('filtro_area_id');
    const auditoriaSalva = sessionStorage.getItem('filtro_auditoria_id');
    
    sessionStorage.clear(); // Limpa tudo
    
    // Restaurar filtros
    if (areaSalva) sessionStorage.setItem('filtro_area_id', areaSalva);
    if (auditoriaSalva) sessionStorage.setItem('filtro_auditoria_id', auditoriaSalva);
    
    // ===== SALVAR ID IMEDIATAMENTE =====
    sessionStorage.setItem('processo_id', processoId);
    sessionStorage.setItem('modo_edicao', 'true');

    // ===== LIMPAR VARIÁVEIS GLOBAIS =====
    riscosLista = [];
    executoresSelecionados = [];

    // ===== RESETAR CAMPOS =====
    resetarCamposDetalhes();
    if (nomeProcessoInput) nomeProcessoInput.value = '';
    if (codigoProcessoInput) codigoProcessoInput.value = '';
    atualizarBadges();

    // ===== GARANTIR QUE O AUDITORIA-INNER ESTEJA VISÍVEL =====
    const auditoriaInner = document.getElementById('auditoria-inner');
    if (auditoriaInner) {
        auditoriaInner.style.display = 'block';
    }

    // ===== BUSCAR DADOS DO PROCESSO =====
    fetchComAutenticacao(`/api/processo/${processoId}/dados`)
        .then(response => response.json())
        .then(data => {
            console.log('📦 Dados recebidos do backend:', data);

            if (data.success) {
                // ===== SALVAR DADOS NO SESSIONSTORAGE =====
                sessionStorage.setItem('id_area_selecionado', data.id_area || '');

                // ===== 1. PREENCHER ÁREA =====
                const areaSelectElement = document.getElementById('area_select');
                if (areaSelectElement && data.id_area) {
                    console.log('🔍 Selecionando área ID:', data.id_area);
                    
                    // Forçar o valor da área
                    areaSelectElement.value = data.id_area;
                    
                    // ⭐ GARANTIR QUE O INNER DA AUDITORIA FIQUE VISÍVEL
                    const auditoriaInnerEl = document.getElementById('auditoria-inner');
                    if (auditoriaInnerEl) {
                        auditoriaInnerEl.style.display = 'block';
                    }
                    
                    // Disparar evento change para carregar auditorias E funcionários
                    const changeEvent = new Event('change', { bubbles: true });
                    areaSelectElement.dispatchEvent(changeEvent);
                    
                    console.log('✅ Área selecionada:', areaSelectElement.value);
                }

                // ===== 2. PREENCHER AUDITORIA (APÓS CARREGAR) =====
                // ⭐ RESETAR O VALOR ANTERIOR DO SELECT
                const auditoriaSelectEl = document.getElementById('auditoria_select');
                if (auditoriaSelectEl) {
                    auditoriaSelectEl.value = '';
                }
                
                function tentarSelecionarAuditoria(tentativa = 0) {
                    const auditoriaSelectEl = document.getElementById('auditoria_select');
                    
                    if (auditoriaSelectEl && data.auditoria_id) {
                        // Verificar se a opção existe
                        let optionExists = false;
                        for (let i = 0; i < auditoriaSelectEl.options.length; i++) {
                            if (auditoriaSelectEl.options[i].value == data.auditoria_id) {
                                optionExists = true;
                                break;
                            }
                        }
                        
                        if (optionExists) {
                            auditoriaSelectEl.value = data.auditoria_id;
                            console.log('✅ Auditoria selecionada:', data.auditoria_id);
                            
                            // ⭐ GARANTIR QUE O INNER DA AUDITORIA FIQUE VISÍVEL
                            const auditoriaInnerEl = document.getElementById('auditoria-inner');
                            if (auditoriaInnerEl) {
                                auditoriaInnerEl.style.display = 'block';
                            }
                            
                            // Disparar evento change para validar responsável
                            const auditEvent = new Event('change', { bubbles: true });
                            auditoriaSelectEl.dispatchEvent(auditEvent);
                            
                            // HABILITAR O BOTÃO PRÓXIMO DA ETAPA 1
                            habilitarProximoEtapa1(true);
                            return true;
                        } else if (tentativa < 15) { // Aumentei para 15 tentativas
                            // Tentar novamente após 200ms
                            console.log(`⏳ Aguardando auditorias carregarem... tentativa ${tentativa + 1}`);
                            setTimeout(() => tentarSelecionarAuditoria(tentativa + 1), 200);
                            return false;
                        } else {
                            console.warn('⚠️ Auditoria não encontrada após várias tentativas');
                            // ⭐ MESMO ASSIM, MANTER O INNER VISÍVEL
                            const auditoriaInnerEl = document.getElementById('auditoria-inner');
                            if (auditoriaInnerEl) {
                                auditoriaInnerEl.style.display = 'block';
                            }
                            return false;
                        }
                    }
                    return false;
                }

                // Iniciar tentativa de selecionar auditoria
                setTimeout(() => tentarSelecionarAuditoria(0), 500);

                // ===== 3. PREENCHER NOME E CÓDIGO =====
                if (nomeProcessoInput) {
                    nomeProcessoInput.value = data.nome_processo || '';
                }
                
                if (codigoProcessoInput) {
                    codigoProcessoInput.value = data.codigo_processo || '';
                }

                const entrevistadoInput = document.getElementById('entrevistado_processo');
                if (entrevistadoInput && data.entrevistado) {
                    entrevistadoInput.value = data.entrevistado;
                }

                // ===== 4. CARREGAR EXECUTORES =====
                if (data.executores && data.executores.length > 0) {
                    executoresSelecionados = data.executores.map(exec => ({
                        id: exec.id,
                        nome: exec.nome,
                        cargo: exec.cargo || 'Sem cargo'
                    }));
                } else {
                    executoresSelecionados = [];
                }
                atualizarBadges();

                // ===== 5. CARREGAR FUNCIONÁRIOS DA ÁREA =====
                if (data.id_area) {
                    carregarFuncionariosArea(parseInt(data.id_area));
                }

                // ===== 6. SALVAR DETALHES PARA ETAPA 3 =====
                const detalhesTemp = {
                    descricao: data.descricao || '',
                    etapa_ini: data.etapa_ini || '',
                    etapa_fim: data.etapa_fim || '',
                    produto: data.produto || '',
                    objetivo: data.objetivo || ''
                };
                sessionStorage.setItem('detalhes_temp', JSON.stringify(detalhesTemp));

                // ===== 7. SALVAR RISCOS =====
                riscosLista = data.riscos || [];
                sessionStorage.setItem('riscos_temp', JSON.stringify(riscosLista));

                // ===== 8. HABILITAR BOTÃO PRÓXIMO =====
                const btnProximoEtapa3 = document.getElementById('btn-proximo-etapa3');
                if (btnProximoEtapa3 && executoresSelecionados.length > 0) {
                    btnProximoEtapa3.disabled = false;
                }

                // ===== 9. MOSTRAR AVISO DE EDIÇÃO =====
                mostrarAvisoProcessoExistente(data.nome_processo, data.codigo_processo);

                // ===== 10. GARANTIR QUE O BOTÃO PRÓXIMO ESTEJA HABILITADO =====
                habilitarProximoEtapa1(true);

                // ===== 11. ABRIR WIZARD NA ETAPA 1 =====
                if (modalWizard) {
                    modalWizard.style.display = 'flex';
                }

                // ===== 12. IR PARA ETAPA 1 =====
                irParaEtapa(1);

                mostrarToast('✅ Processo carregado para edição!', 'success');
            } else {
                mostrarToast('❌ Erro ao carregar dados do processo', 'error');
            }
        })
        .catch(error => {
            console.error('❌ Erro ao buscar processo:', error);
            mostrarToast('❌ Erro ao carregar dados. Tente novamente.', 'error');
        });
}

// ====== FUNÇÃO PARA PERMITIR CLIQUE NAS ETAPAS DO WIZARD ======
function habilitarNavegacaoEtapas() {
    const steps = document.querySelectorAll('.step');
    steps.forEach(step => {
        step.style.cursor = 'pointer';
        step.addEventListener('click', (e) => {
            // Não fazer nada se clicar no step ativo
            if (step.classList.contains('active')) {
                return;
            }

            // Obter o número da etapa clicada
            const etapaNum = parseInt(step.getAttribute('data-step'));

            // Verificar se é uma transição válida (impedir pular para etapas não disponíveis)
            const etapaAtual = parseInt(document.querySelector('.step.active')?.getAttribute('data-step') || 1);

            // Regras de validação
            if (etapaNum > etapaAtual) {
                // Avançando: verificar se as etapas anteriores estão completas?
                // Por enquanto, permitir qualquer navegação
                console.log(`🖱️ Navegando da etapa ${etapaAtual} para etapa ${etapaNum}`);
            } else {
                // Voltando: sempre permitido
                console.log(`🖱️ Voltando da etapa ${etapaAtual} para etapa ${etapaNum}`);
            }

            // Ir para a etapa clicada
            irParaEtapa(etapaNum);
        });
    });
}

// Função para salvar informações básicas antes de avançar

async function salvarInfoBasicasAntesDeAvancar() {
    const nomeProcesso = document.getElementById('nome_processo')?.value.trim().toUpperCase();
    if (!nomeProcesso || executoresSelecionados.length === 0) return;

    const entrevistado = document.getElementById('entrevistado_processo')?.value.trim().toUpperCase() || '';

    // 🔍 LOG
    console.log('🔍 [DEBUG] salvarInfoBasicasAntesDeAvancar chamada');
    console.log('  modo_edicao:', sessionStorage.getItem('modo_edicao'));
    console.log('  processo_id:', sessionStorage.getItem('processo_id'));
    
    // 🔧 VERIFICAR SE É MODO EDIÇÃO
    const modoEdicao = sessionStorage.getItem('modo_edicao');
    const processoIdExistente = sessionStorage.getItem('processo_id');
    
    // ⚠️ Se for modo edição, NÃO SALVAR AUTOMATICAMENTE
    if (modoEdicao === 'true' && processoIdExistente) {
        console.log('✏️ Modo edição ativo - NÃO salvando informações básicas automaticamente');
        return;
    }
    
    const areaId = document.getElementById('id_area_selecionado')?.value || areaSelect.value;
    const codigoProcesso = document.getElementById('codigo_processo')?.value;
    const auditoriaId = auditoriaSelect.value;
    const areaSelectElement = document.getElementById('area_select');
    const nomeArea = areaSelectElement.options[areaSelectElement.selectedIndex]?.text?.toUpperCase() || '';
    
    const payload = {
        nome_processo: nomeProcesso,
        codigo_processo: codigoProcesso,
        id_area: parseInt(areaId),
        nome_area: nomeArea,
        executores_ids: executoresSelecionados.map(e => e.id),
        auditoria_id: parseInt(auditoriaId),
        entrevistado: entrevistado
    };
    
    // Só adiciona processo_id se existir e NÃO for edição
    if (processoIdExistente && modoEdicao !== 'true') {
        payload.processo_id = parseInt(processoIdExistente);
    }
    
    try {
        const response = await fetchComAutenticacao('/api/processo/salvar-basico', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.success) {
            sessionStorage.setItem('processo_id', data.processo_id);
            sessionStorage.setItem('auditoria_id', auditoriaId);
            sessionStorage.setItem('modo_edicao', 'true');
            console.log('💾 Informações básicas salvas automaticamente');
        }
    } catch (error) {
        console.error('Erro ao salvar automaticamente:', error);
        sessionStorage.setItem('rascunho_etapa2', JSON.stringify({
            nome_processo: nomeProcesso,
            executores_ids: executoresSelecionados.map(e => e.id),
            codigo_processo: codigoProcesso
        }));
    }
}

// Função para salvar detalhes antes de avançar
async function salvarDetalhesAntesDeAvancar() {
    const processoId = sessionStorage.getItem('processo_id');
    if (!processoId) return;
    
    const descricao = document.getElementById('descricao_processo')?.value.trim().toUpperCase() || '';
    const etapaIni = document.getElementById('etapa_ini_processo')?.value.trim().toUpperCase() || '';
    const produto = document.getElementById('produto_processo')?.value.trim().toUpperCase() || '';
    const etapaFim = document.getElementById('etapa_fim_processo')?.value.trim().toUpperCase() || '';
    const objetivo = document.getElementById('objetivo_processo')?.value.trim().toUpperCase() || '';
    
    try {
        const response = await fetchComAutenticacao('/api/processo/salvar-detalhes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                processo_id: parseInt(processoId),
                descricao: descricao,
                etapa_ini: etapaIni,
                etapa_fim: etapaFim,
                produto: produto,
                objetivo: objetivo
            })
        });
        
        const data = await response.json();
        if (data.success) {
            console.log('💾 Detalhes salvos automaticamente');
        }
    } catch (error) {
        console.error('Erro ao salvar detalhes:', error);
    }
}

// ===== CARREGAR RESUMO DO PROCESSO NA ETAPA 5 =====
function carregarResumoProcesso() {
    const processoId = sessionStorage.getItem('processo_id');
    if (!processoId) {
        console.log('❌ Nenhum processo_id encontrado')
        return;
    }

    // Buscar dados do backend para garantir dados atualizados
    fetchComAutenticacao(`/api/processo/${processoId}/dados`)
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            // Informações Básicas
            document.getElementById('resumo-codigo').textContent = data.codigo_processo || '-';
            document.getElementById('resumo-nome').textContent = data.nome_processo || '-';

            const entrevistadoSpan = document.getElementById('resumo-entrevistado');
            if (entrevistadoSpan) {
                entrevistadoSpan.textContent = data.entrevistado || '-';
            }
            
            const executoresNomes = data.executores.map(e => e.nome).join(', ');
            document.getElementById('resumo-executores').textContent = executoresNomes || '-';

            // Detalhes do Processo
            document.getElementById('resumo-descricao').textContent = data.descricao || '-';
            document.getElementById('resumo-etapa-ini').textContent = data.etapa_ini || '-';
            document.getElementById('resumo-produto').textContent = data.produto || '-';
            document.getElementById('resumo-etapa-fim').textContent = data.etapa_fim || '-';
            document.getElementById('resumo-objetivo').textContent = data.objetivo || '-';

            // Riscos
            const riscos = data.riscos || [];
            document.getElementById('resumo-qtd-riscos').textContent = `${riscos.length} ${riscos.length === 1 ? 'risco': 'riscos'}`;

            const container = document.getElementById('resumo-riscos-container');
            if (riscos.length === 0) {
                container.innerHTML = '<div class="empty-message">📌 Nenhum risco cadastrado para este processo.</div>';
            } else {
                container.innerHTML = riscos.map(risco => {
                    // Calcular score e nível
                    const score = calcularScoreRisco(risco.impacto || 'Médio', risco.probabilidade || 'Médio');
                    let nivel = 'low';
                    let nivelTexto = 'BAIXO';
                    if (score <= 3) { nivel ='low'; nivelTexto = 'BAIXA EXPOSIÇÃO'; }
                    else if (score <= 7) { nivel = 'medium'; nivelTexto = "SOB OBSERVAÇÃO"; }
                    else if (score <= 11) { nivel = 'high'; nivelTexto = "ATENÇÃO"; }
                    else { nivel = 'critical'; nivelTexto = 'CRÍTICO'; }

                    let corScore = '';
                    if (score <= 3) corScore = '🟢';
                    else if (score <= 7) corScore = '🟡';
                    else if (score <= 11) corScore = '🟠';
                    else corScore = '🔴';

                    return `
                        <div class="resumo-risco-card ${nivel}">
                            <div class="resumo-risco-header">
                                <span class="resumo-risco-nome">${escapeHtml(risco.nome_risco).toUpperCase()}</span>
                                <span class="resumo-risco-score">${corScore} ${score} (${nivelTexto})</span>
                            </div>
                            <div class="resumo-risco-detalhes">
                                <div class="detalhe">
                                    <span class="detalhe-label">Impacto Financeiro</span>
                                    <span class="detalhe-value">${risco.impacto || 'Médio'}</span>
                                </div>
                                <div class="detalhe">
                                    <span class="detalhe-label">Probabilidade</span>
                                    <span class="detalhe-value">${risco.probabilidade || 'Médio'}</span>
                                </div>
                                
                                <!-- ⭐ NOVOS CAMPOS: Apetite -->
                                <div class="detalhe">
                                    <span class="detalhe-label">Apetite do Impacto Financeiro</span>
                                    <span class="detalhe-value">${risco.apetite_impacto || 'Médio'}</span>
                                </div>
                                <div class="detalhe">
                                    <span class="detalhe-label">Apetite da Probabilidade</span>
                                    <span class="detalhe-value">${risco.apetite_probabilidade || 'Médio'}</span>
                                </div>
                                
                                ${risco.categorias && risco.categorias.length ? `
                                <div class="detalhe">
                                    <span class="detalhe-label">Categorias</span>
                                    <span class="detalhe-value">${risco.categorias.join(', ')}</span>
                                </div>
                                ` : ''}
                                ${risco.como_tratar ? `
                                <div class="detalhe">
                                    <span class="detalhe-label">Tratamento</span>
                                    <span class="detalhe-value">${escapeHtml(risco.como_tratar)}</span>
                                </div>
                                ` : ''}
                                ${risco.prazo_implantacao ? `
                                <div class="detalhe">
                                    <span class="detalhe-label">Prazo</span>
                                    <span class="detalhe-value">${escapeHtml(risco.prazo_implantacao)}</span>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }).join('');
            }
        }
    })
    .catch(error => {
        console.error('❌ Erro ao carregar resumo:', error);
    });
}

// ===== FINALIZAR PROCESSO (fecha wizard e recarrega a tabela) =====
function finalizarWizard() {
    // Fechar o modal
    if (modalWizard) {
        modalWizard.style.display = 'none';
    }

    // Recarregar a tabela de processos (mantendo área e auditoria selecionadas)
    const auditoriaId = filtroAuditoriaSelect.value;
    if (auditoriaId) {
        carregarTabelaProcessos(auditoriaId);
        mostrarToast('✅ Processo salvo com sucesso!', 'success');
    } else {
        // Se não tiver auditoria selecionada, apenas limpar
        if (tabelaProcessosContainer) {
            tabelaProcessosContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma área e auditoria para visualizar os processos.</div>';
        }
    }

    // Limpar sessionStorage (opcional, para nã interferir em próximos processos)
    sessionStorage.removeItem('processo_id');
    sessionStorage.removeItem('modo_edicao');
    sessionStorage.removeItem('riscos_temp');
    sessionStorage.removeItem('detalhes_temp');
    sessionStorage.removeItem('etapa_atual');
}

// ===== FECHAR COM TECLA ESC =====
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('modal-visualizar-risco');
        if (modal && modal.style.display === 'flex') {
            fecharModalVisualizarRisco();
        }
    }
});
