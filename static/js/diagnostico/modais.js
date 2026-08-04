// ============================================================
// modais.js - MÓDULO DE MODAIS (Visualização)
// ============================================================

const ModaisModule = {
    
    init() {
        console.log('📌 ModaisModule: inicializando...');
        
        // Fechar modal de visualizar processo
        const btnFechar = document.getElementById('btn-fechar-visualizar-processo');
        const btnFecharFooter = document.getElementById('btn-fechar-visualizar-processo-footer');
        
        btnFechar?.addEventListener('click', () => this.fecharVisualizarProcesso());
        btnFecharFooter?.addEventListener('click', () => this.fecharVisualizarProcesso());
        
        console.log('✅ ModaisModule: inicializado');
    },
    
    // ============================================================
    // VISUALIZAR PROCESSO
    // ============================================================
    async abrirVisualizarProcesso(processoId) {
        const modal = document.getElementById('modal-visualizar-processo');
        const conteudo = document.getElementById('visualizar-processo-conteudo');
        
        modal.style.display = 'flex';
        conteudo.innerHTML = '<div style="text-align:center; padding:40px;"><i class="fas fa-spinner fa-spin"></i> Carregando...</div>';
        
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/dados`);
            const data = await response.json();
            
            if (data.success) {
                conteudo.innerHTML = this.renderizarProcessoCompleto(data);
                this.carregarAnexosVisualizacao(processoId);
                
                // ⭐ ADICIONE ESTE BLOCO ⭐
                setTimeout(() => {
                    document.querySelectorAll('.btn-visualizar-risco-card').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const riscoId = parseInt(btn.dataset.riscoId);
                            this.visualizarRiscoDoModal(riscoId);
                        });
                    });
                }, 200);
                
            } else {
                conteudo.innerHTML = '<p style="color:#dc3545;">Erro ao carregar dados.</p>';
            }
        } catch (error) {
            console.error('❌ Erro:', error);
            conteudo.innerHTML = '<p style="color:#dc3545;">Erro ao carregar.</p>';
        }
    },
    
    fecharVisualizarProcesso() {
        document.getElementById('modal-visualizar-processo').style.display = 'none';
    },
    
    // ============================================================
    // RENDERIZAR PROCESSO COMPLETO
    // ============================================================
    renderizarProcessoCompleto(data) {
        const executoresNomes = (data.executores || []).map(e => e.nome).join(', ') || '-';
        const riscos = data.riscos || [];
        
        return `
            <div class="vis-processo-container">
                
                <!-- Informações Básicas -->
                <div class="vis-section">
                    <h4><i class="fas fa-info-circle"></i> Informações Básicas</h4>
                    <div class="vis-grid">
                        <div class="vis-item">
                            <label>Área</label>
                            <span>${data.nome_area || '-'}</span>
                        </div>
                        <div class="vis-item">
                            <label>Entrevistado</label>
                            <span>${data.entrevistado || '-'}</span>
                        </div>
                        <div class="vis-item">
                            <label>Código</label>
                            <span><strong>${data.codigo_processo || '-'}</strong></span>
                        </div>
                        <div class="vis-item">
                            <label>Nome do Processo</label>
                            <span>${data.nome_processo || '-'}</span>
                        </div>
                        <div class="vis-item vis-full">
                            <label>Executores</label>
                            <span>${executoresNomes}</span>
                        </div>
                    </div>
                </div>
                
                <!-- Detalhes -->
                <div class="vis-section">
                    <h4><i class="fas fa-clipboard-list"></i> Detalhes do Processo</h4>
                    <div class="vis-grid">
                        <div class="vis-item vis-full">
                            <label>O que é o processo?</label>
                            <span>${data.descricao || '-'}</span>
                        </div>
                        <div class="vis-item">
                            <label>Onde começa?</label>
                            <span>${data.etapa_ini || '-'}</span>
                        </div>
                        <div class="vis-item">
                            <label>Produto final</label>
                            <span>${data.produto || '-'}</span>
                        </div>
                        <div class="vis-item">
                            <label>Para onde envia?</label>
                            <span>${data.etapa_fim || '-'}</span>
                        </div>
                        <div class="vis-item">
                            <label>Objetivo</label>
                            <span>${data.objetivo || '-'}</span>
                        </div>
                    </div>
                </div>
                
                <!-- Riscos -->
                <div class="vis-section">
                    <h4><i class="fas fa-exclamation-triangle"></i> Riscos Identificados (${riscos.length})</h4>
                    ${riscos.length === 0 ? '<p>Nenhum risco cadastrado.</p>' : this.renderizarKanbanVisualizacao(riscos)}
                </div>
                
                <!-- Anexos -->
                <div class="vis-section">
                    <h4><i class="fas fa-paperclip"></i> Fluxo(s)</h4>
                    <div id="vis-anexos-lista">Carregando...</div>
                </div>
                
            </div>
        `;
    },
    
    getScoreClass(score) {
        if (!score) return '';
        if (score <= 3) return 'score-baixo';
        if (score <= 7) return 'score-medio';
        if (score <= 11) return 'score-alto';
        return 'score-critico';
    },

    renderizarKanbanVisualizacao(riscos) {
        const colunas = {
            baixo: { titulo: 'BAIXA EXPOSIÇÃO', range: '0 - 3', classe: 'low', riscos: [] },
            medio: { titulo: 'SOB OBSERVAÇÃO', range: '4 - 7', classe: 'medium', riscos: [] },
            alto: { titulo: 'ATENÇÃO', range: '8 - 11', classe: 'high', riscos: [] },
            critico: { titulo: 'CRÍTICO', range: '12+', classe: 'critical', riscos: [] }
        };
        
        riscos.forEach(r => {
            const score = r.score_risco || 0;
            if (score <= 3) colunas.baixo.riscos.push(r);
            else if (score <= 7) colunas.medio.riscos.push(r);
            else if (score <= 11) colunas.alto.riscos.push(r);
            else colunas.critico.riscos.push(r);
        });
        
        return `
            <div class="kanban-board">
                ${Object.entries(colunas).map(([nivel, col]) => `
                    <div class="kanban-col">
                        <div class="kanban-col-header ${col.classe}">
                            <i class="fas fa-circle"></i>
                            <span>${col.titulo}</span>
                            <span class="score-range">${col.range}</span>
                            <span class="risk-count">${col.riscos.length}</span>
                        </div>
                        <div class="kanban-col-body">
                            ${col.riscos.length === 0 ? '' : 
                            col.riscos.map(r => {
                                const score = r.score_risco || 0;
                                let classeCor;
                                
                                if (score <= 3) classeCor = 'low';
                                else if (score <= 7) classeCor = 'medium';
                                else if (score <= 11) classeCor = 'high';
                                else classeCor = 'critical';
                                
                                return `
                                    <div class="kanban-card ${classeCor}">
                                        <div class="kanban-card-title">${r.nome_risco || '-'}</div>
                                        <div class="kanban-card-score">Score: ${score}</div>
                                        <button class="btn-visualizar-risco-card" data-risco-id="${r.id}"
                                            style="margin-top: 6px; background: none/ border: none; cursor: pointer; font-size: 12px;">
                                                <i class="fas fa-eye"></i>
                                        </button>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        // Configurar eventos dos botões de visualizar risco
        setTimeout(() => {
            document.querySelectorAll('.btn-visualizar-risco-card').forEach(btn => {
                btn.addEventListener('click', () => {
                    const riscoId = parseInt(btn.dataset.riscoId);
                    this.visualizarRiscoDoModal(riscoId);
                });
            });
        }, 100);
    },

    visualizarRiscoDoModal(riscoId) {
        // Buscar da API (sempre funciona, sem depender de outros módulos)
        this.carregarEAbrirRisco(riscoId);
    },

    async carregarEAbrirRisco(riscoId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/risco/${riscoId}/dados`);
            const data = await response.json();
            
            if (data.success && data.risco) {
                this.preencherModalVisualizarRisco(data.risco);
                document.getElementById('modal-visualizar-risco').style.display = 'flex';
            }
        } catch (error) {
            console.error('Erro:', error);
        }
    },

    preencherModalVisualizarRisco(risco) {
        document.getElementById('vis-nome_risco').textContent = risco.nome_risco || '-';
        document.getElementById('vis-fator_risco').textContent = risco.fator_risco || '-';
        document.getElementById('vis-categoria-causa').textContent = (risco.categoria_causa || []).join(', ') || '-';
        document.getElementById('vis-melhoria').textContent = risco.melhoria || '-';
        document.getElementById('vis-categorias').textContent = (risco.categorias || []).join(', ') || '-';
        document.getElementById('vis-impacto').textContent = risco.impacto || '-';
        document.getElementById('vis-probabilidade').textContent = risco.probabilidade || '-';
        document.getElementById('vis-apetite-impacto').textContent = risco.apetite_impacto || '-';
        document.getElementById('vis-apetite-probabilidade').textContent = risco.apetite_probabilidade || '-';
        document.getElementById('vis-score').textContent = risco.score_risco || '-';
        document.getElementById('vis-motivo_risco').textContent = risco.motivo_risco || '-';
        document.getElementById('vis-como-tratar').textContent = risco.como_tratar || '-';
        document.getElementById('vis-desc-tratamento').textContent = risco.desc_tratamento || '-';
        document.getElementById('vis-prazo-implantacao').textContent = risco.prazo_implantacao || '-';
        
        // Score do apetite
        const mapa = {
            "MUITO ALTO,MUITO ALTO": 15, "ALTO,MUITO ALTO": 14,
            "MÉDIO,MUITO ALTO": 13, "BAIXO,MUITO ALTO": 12,
            "MUITO ALTO,ALTO": 11, "ALTO,ALTO": 10,
            "MÉDIO,ALTO": 9, "BAIXO,ALTO": 8,
            "MUITO ALTO,MÉDIO": 7, "ALTO,MÉDIO": 6,
            "MÉDIO,MÉDIO": 5, "BAIXO,MÉDIO": 4,
            "MUITO ALTO,BAIXO": 3, "ALTO,BAIXO": 2,
            "MÉDIO,BAIXO": 1, "BAIXO,BAIXO": 0
        };
        const impactoApetite = (risco.apetite_impacto || '').toUpperCase().trim();
        const probApetite = (risco.apetite_probabilidade || '').toUpperCase().trim();
        
        document.getElementById('vis-score-apetite').textContent = 
            (impactoApetite && probApetite && mapa[`${impactoApetite},${probApetite}`] !== undefined) 
            ? mapa[`${impactoApetite},${probApetite}`] : '-';
    },

    async carregarAnexosVisualizacao(processoId) {
        const container = document.getElementById('vis-anexos-lista');
        if (!container) return;
        
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/anexos`);
            const data = await response.json();
            
            if (data.success && data.anexos.length > 0) {
                container.innerHTML = data.anexos.map(a => {
                    const extensao = a.nome_original?.split('.').pop()?.toUpperCase() || '';
                    const icone = this.iconeAnexo(a.tipo_mime);
                    
                    return `
                        <div class="vis-anexo-item">
                            <i class="${icone}"></i>
                            <span class="vis-anexo-nome">${a.nome_original || a.nome_arquivo}</span>
                            <span class="vis-anexo-extensao">${extensao}</span>
                        </div>
                    `;
                }).join('');
            } else {
                container.innerHTML = '<p class="vis-anexo-vazio">Nenhum fluxo anexado.</p>';
            }
        } catch (error) {
            container.innerHTML = '<p class="vis-anexo-vazio">Erro ao carregar anexos.</p>';
        }
    },

    iconeAnexo(tipo) {
        if (tipo?.includes('pdf')) return 'fas fa-file-pdf';
        if (tipo?.includes('image')) return 'fas fa-file-image';
        return 'fas fa-file';
    },


    
};