// ============================================================
// tabela.js - MÓDULO DA TABELA DE PROCESSOS (VERSÃO COMPLETA)
// ============================================================

const TabelaModule = {
    
    container: null,
    btnNovoProcesso: null,
    processosData: [],       // Armazena os processos para ordenação
    ordenacaoAtual: {        // Estado da ordenação
    coluna: 'codigo',
    direcao: 'asc'
    },
    
    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================
    init() {
        console.log('📌 TabelaModule: inicializando...');
        
        this.container = document.getElementById('tabela-processos-container');
        this.btnNovoProcesso = document.getElementById('btn-novo-processo');
        
        if (!this.container) {
            console.warn('⚠️ TabelaModule: container da tabela não encontrado');
            return;
        }
        
        if (this.btnNovoProcesso) {
            this.btnNovoProcesso.addEventListener('click', () => {
                this.aoClicarNovoProcesso();
            });
        }
        
        console.log('✅ TabelaModule: inicializado');
    },
    
    // ============================================================
    // CARREGAR PROCESSOS
    // ============================================================
    async carregarProcessos(areaId, auditoriaId = null) {
        console.log(`📊 TabelaModule: carregando - Área: ${areaId}, Auditoria: ${auditoriaId || 'Todas'}`);
        
        this.container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div class="dot-spinner">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando processos...</p>
            </div>
        `;
        
        let url = `/api/processos-por-area?area_id=${areaId}`;
        if (auditoriaId) {
            url += `&auditoria_id=${auditoriaId}`;
        }
        
        try {
            const response = await window.fetchComAutenticacao(url);
            
            if (!response || !response.ok) throw new Error('Erro ao carregar processos');
            
            const data = await response.json();
            
            if (!data.processos || data.processos.length === 0) {
                this.mostrarVazio();
                return;
            }
            
            // Armazena os dados para ordenação
            this.processosData = data.processos;
            this.renderizarTabela();
            
        } catch (error) {
            console.error('❌ TabelaModule: erro ao carregar processos', error);
            this.container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #dc3545;">
                    <i class="fas fa-exclamation-circle"></i> Erro ao carregar processos.
                </div>
            `;
        }
    },
    
    // ============================================================
    // RENDERIZAR TABELA (VERSÃO COMPLETA)
    // ============================================================
    renderizarTabela() {
        console.log(`📋 TabelaModule: renderizando ${this.processosData.length} processos`);
        
        if (this.btnNovoProcesso) {
            this.btnNovoProcesso.style.display = 'inline-flex';
        }
        
        // Cabeçalho com ordenação
        let html = `
            <div style="overflow-x: auto;">
                <table class="tabela-processos">
                    <thead>
                        <tr>
                            <th class="sortable" data-coluna="codigo">
                                Código ${this.getSetaOrdenacao('codigo')}
                            </th>
                            <th class="sortable" data-coluna="nome">
                                Nome do Processo ${this.getSetaOrdenacao('nome')}
                            </th>
                            <th>Objetivo</th>
                            <th class="sortable" data-coluna="auditoria">
                                Auditoria ${this.getSetaOrdenacao('auditoria')}
                            </th>
                            <th class="sortable" data-coluna="score">
                                Score Máximo ${this.getSetaOrdenacao('score')}
                            </th>
                            <th class="sortable" data-coluna="riscos">
                                Riscos ${this.getSetaOrdenacao('riscos')}
                            </th>
                            <th>Anexo Fluxo</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        for (const processo of this.processosData) {
            const auditoriaDisplay = processo.codigo_auditoria || processo.auditoria_codigo || '-';
            
            // Botões de ação
            let botoesHtml = this.renderizarBotoesAcao(processo);
            
            html += `
                <tr>
                    <td>
                        <strong>${this.escapeHtml(processo.codigo_processo || '-')}</strong>
                        <button class="btn-visualizar-processo" data-ver="${processo.id}" title="Visualizar processo">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                    <td>${this.escapeHtml(processo.nome_processo || '-')}</td>
                    <td>${this.escapeHtml(processo.objetivo || '-')}</td>
                    <td><span class="auditoria-badge">${this.escapeHtml(auditoriaDisplay)}</span></td>
                    <td><span class="score-badge ${processo.texto_score || ''}">${processo.cor_score || ''} ${processo.score_maximo || 0}</span></td>
                    <td>${processo.qtd_riscos || 0}</td>
                    <td>
                        <button class="btn-anexo" data-anexar="${processo.id}" title="Anexar fluxo do processo">
                            <i class="fas fa-paperclip"></i>
                        </button>
                    </td>
                    <td>${botoesHtml}</td>
                </tr>
            `;
        }
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        this.container.innerHTML = html;
        
        // Configura todos os eventos
        this.configurarEventosTabela();
    },
    
    // ============================================================
    // RENDERIZAR BOTÕES DE AÇÃO
    // ============================================================
    renderizarBotoesAcao(processo) {
        // Verifica permissões
        const isAdmin = (typeof IS_ADMIN !== 'undefined' && IS_ADMIN) || 
                        (typeof USUARIO_PERFIL !== 'undefined' && 
                         (USUARIO_PERFIL === 'administrador' || USUARIO_PERFIL === 'admin'));
        
        if (isAdmin) {
            return `
                <div class="btn-group">
                    <button class="btn-edit-processo" data-editar="${processo.id}" title="Editar">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                    <button class="btn-delete-processo" data-excluir="${processo.id}" data-nome="${this.escapeHtml(processo.nome_processo)}" title="Excluir">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;
        } else {
            // Para não-admin, mostra botão de editar normal
            return `
                <div class="btn-group">
                    <button class="btn-edit-processo" data-editar="${processo.id}">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                </div>
            `;
        }
    },
    
    // ============================================================
    // CONFIGURAR EVENTOS DA TABELA
    // ============================================================
    configurarEventosTabela() {
        // Ordenação pelas colunas
        this.container.querySelectorAll('.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const coluna = th.getAttribute('data-coluna');
                this.ordenarProcessos(coluna);
            });
        });
        
        // Botão Visualizar (olho)
        this.container.querySelectorAll('.btn-visualizar-processo').forEach(btn => {
            btn.addEventListener('click', () => {
                const processoId = btn.getAttribute('data-ver');
                this.aoClicarVer(processoId);
            });
        });
        
        // Botão Editar (ícone - admin)
        this.container.querySelectorAll('.btn-edit-processo').forEach(btn => {
            btn.addEventListener('click', () => {
                const processoId = btn.getAttribute('data-editar');
                this.aoClicarEditar(processoId);
            });
        });
        
        // Botão Editar (texto - usuário normal)
        this.container.querySelectorAll('.btn-editar-processo').forEach(btn => {
            btn.addEventListener('click', () => {
                const processoId = btn.getAttribute('data-editar');
                this.aoClicarEditar(processoId);
            });
        });
        
        // Botão Excluir
        this.container.querySelectorAll('.btn-delete-processo').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const processoId = btn.getAttribute('data-excluir');
                const processoNome = btn.getAttribute('data-nome');
                await this.aoClicarExcluir(processoId, processoNome);
            });
        });


        // Botão Anexo
        this.container.querySelectorAll('.btn-anexo').forEach(btn => {
            btn.addEventListener('click', () => {
                const processoId = parseInt(btn.dataset.anexar);
                this.aoClicarAnexo(processoId);
            });
        });
    },
    
    // ============================================================
    // ORDENAÇÃO
    // ============================================================
    getSetaOrdenacao(coluna) {
        if (this.ordenacaoAtual.coluna === coluna) {
            return this.ordenacaoAtual.direcao === 'asc' ? '▲' : '▼';
        }
        return '↕';
    },
    
    ordenarProcessos(coluna) {
        // Inverte a direção se clicar na mesma coluna
        if (this.ordenacaoAtual.coluna === coluna) {
            this.ordenacaoAtual.direcao = this.ordenacaoAtual.direcao === 'asc' ? 'desc' : 'asc';
        } else {
            this.ordenacaoAtual.coluna = coluna;
            this.ordenacaoAtual.direcao = 'asc';
        }
        
        const direcao = this.ordenacaoAtual.direcao === 'asc' ? 1 : -1;
        
        this.processosData.sort((a, b) => {
            let valorA, valorB;
            
            switch (coluna) {
                case 'codigo':
                    valorA = a.codigo_processo || '';
                    valorB = b.codigo_processo || '';
                    break;
                case 'nome':
                    valorA = (a.nome_processo || '').toLowerCase();
                    valorB = (b.nome_processo || '').toLowerCase();
                    break;
                case 'auditoria':
                    valorA = (a.codigo_auditoria || a.auditoria_codigo || '').toLowerCase();
                    valorB = (b.codigo_auditoria || b.auditoria_codigo || '').toLowerCase();
                    break;
                case 'score':
                    valorA = a.score_maximo || 0;
                    valorB = b.score_maximo || 0;
                    break;
                case 'riscos':
                    valorA = a.qtd_riscos || 0;
                    valorB = b.qtd_riscos || 0;
                    break;
                default:
                    return 0;
            }
            
            if (valorA < valorB) return -1 * direcao;
            if (valorA > valorB) return 1 * direcao;
            return 0;
        });
        
        this.renderizarTabela();
    },
    
    // ============================================================
    // MOSTRAR VAZIO
    // ============================================================
    mostrarVazio() {
        if (this.btnNovoProcesso) {
            this.btnNovoProcesso.style.display = 'inline-flex';
        }
        
        this.container.innerHTML = `
            <div class="alert-info" style="text-align: center; padding: 40px;">
                <i class="fas fa-info-circle"></i> 
                Nenhum processo encontrado para esta área/auditoria.
                <br><br>
                <small>Clique em "Novo Processo" para cadastrar.</small>
            </div>
        `;
    },
    
    // ============================================================
    // EVENTOS
    // ============================================================
    aoClicarNovoProcesso() {
        console.log('➕ TabelaModule: novo processo');
        if (typeof WizardModule !== 'undefined') {
            WizardModule.abrir('novo');
        }
    },
    
    aoClicarVer(processoId) {
        console.log(`👁️ TabelaModule: visualizar processo ${processoId}`);
        if (typeof ModaisModule !== 'undefined') {
            ModaisModule.abrirVisualizarProcesso(processoId);
        }
    },
    
    aoClicarEditar(processoId) {
        console.log(`✏️ TabelaModule: editar processo ${processoId}`);
        if (typeof WizardModule !== 'undefined') {
            WizardModule.abrir('edicao', processoId);
        }
    },
    
    async aoClicarExcluir(processoId, processoNome) {
        console.log(`🗑️ TabelaModule: excluir processo ${processoId}`);
        
        const confirmado = confirm(`Tem certeza que deseja excluir o processo "${processoNome}"?`);
        
        if (confirmado) {
            await this.excluirProcesso(processoId);
        }
    },
    
    async excluirProcesso(processoId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/excluir`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.mostrarToast('✅ Processo excluído com sucesso!', 'success');
                this.recarregar();
            } else {
                window.mostrarToast('❌ Erro ao excluir processo', 'error');
            }
        } catch (error) {
            console.error('Erro ao excluir:', error);
        }
    },
    
    // ============================================================
    // RECARREGAR
    // ============================================================
    recarregar() {
        if (typeof FiltrosModule !== 'undefined') {
            const areaId = FiltrosModule.getAreaId();
            const auditoriaId = FiltrosModule.getAuditoriaId();
            if (areaId) {
                this.carregarProcessos(areaId, auditoriaId || null);
            }
        }
    },
    
    // ============================================================
    // UTILITÁRIOS
    // ============================================================
    escapeHtml(texto) {
        if (!texto) return '';
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    },

    aoClicarAnexo(processoId) {
        const id = parseInt(processoId); 
        const proc = this.processosData.find(p => p.id === id);
        
        if (typeof AnexosModule !== 'undefined') {
            AnexosModule.abrir(
                id,
                proc?.nome_processo || 'Processo',
                proc?.codigo_processo || ''
            );
        }
    },
    
};