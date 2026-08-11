// ============================================================
// tabela_etapas.js - MÓDULO DA TABELA DE ETAPAS
// ============================================================

const TabelaEtapasModule = {

    processoAtualId: null,
    processoAtualCodigo: null,

    init() {
        console.log('📌 TabelaEtapasModule: inicializado');
    },

    // ============================================================
    // CARREGAR DADOS DO PROCESSO
    // ============================================================
    async carregarDadosProcesso() {
        const params = new URLSearchParams(window.location.search);
        const processoId = params.get('processo_id');
        const processoCodigo = params.get('processo_codigo');

        if (!processoId) {
            document.getElementById('processo-info').innerHTML = '<span class="alert-error">❌ Nenhum processo selecionado.</span>';
            return;
        }

        this.processoAtualId = processoId;
        this.processoAtualCodigo = processoCodigo;

        let auditoriaId = null;
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/dados`);
            const data = await response.json();
            if (data.success) {
                auditoriaId = data.auditoria_id;
            }
        } catch (error) {
            console.error('Erro ao buscar processo:', error);
        }

        document.getElementById('modal-processo-id').value = processoId;

        const container = document.getElementById('etapas-container');

        if (auditoriaId) {
            container.innerHTML = this._spinnerHTML('Verificando permissão...');
            try {
                const resp = await window.fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
                const dados = await resp.json();
                if (dados.autorizado) {
                    await this.carregarEtapas();
                } else {
                    container.innerHTML = '<div class="alert-error"><i class="fas fa-lock"></i> Sem permissão.</div>';
                    const btn = document.getElementById('btn-nova-etapa');
                    if (btn) btn.style.display = 'none';
                }
            } catch (error) {
                container.innerHTML = '<div class="alert-error">Erro ao verificar permissão.</div>';
            }
        } else {
            await this.carregarEtapas();
        }
    },

    // ============================================================
    // CARREGAR ETAPAS
    // ============================================================
    async carregarEtapas() {
        const container = document.getElementById('etapas-container');
        container.innerHTML = this._spinnerHTML('Carregando etapas...');

        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${this.processoAtualId}/etapas`);
            const data = await response.json();

            if (data.success) {
                document.getElementById('processo-info').innerHTML = `
                    <i class="fas fa-tag"></i> Processo: <strong>${escapeHtml(this.processoAtualCodigo || '')}</strong> - Total: <strong>${data.etapas.length}</strong>
                `;

                if (data.etapas.length === 0) {
                    container.innerHTML = '<div class="empty-message">Nenhuma etapa. Clique em "Nova Etapa".</div>';
                } else {
                    this.renderizar(data.etapas);
                }
            } else {
                container.innerHTML = `<div class="empty-message">❌ ${data.error || 'Erro'}</div>`;
            }
        } catch (error) {
            container.innerHTML = '<div class="empty-message">❌ Erro de conexão.</div>';
        }
    },

    // ============================================================
    // RENDERIZAR ETAPAS
    // ============================================================
    async renderizar(etapas) {
        const container = document.getElementById('etapas-container');

        const cardsHtml = await Promise.all(etapas.map(async (etapa) => {
            const executoresNomes = typeof ExecutoresModule !== 'undefined' 
                ? await ExecutoresModule.getNomes(etapa.executores_etapa) : '-';

            // Status da análise
            let analiseBadge = '';
            if (!etapa.tem_analise_auditado) {
                analiseBadge = '<span class="badge badge-pendente"><i class="fas fa-clock"></i> Análise do Auditado Pendente</span>';
            } else {
                analiseBadge = '<span class="badge badge-concluido"><i class="fas fa-check-circle"></i> Análise do Auditado Realizada</span>';
            }

            // Status do manual
            let manualBadge = '';
            if (etapa.manual_nome && etapa.manual_nome.trim() !== '') {
                manualBadge = '<span class="badge badge-concluido"><i class="fas fa-file-pdf"></i> Manual Concluído</span>';
            } else if (etapa.manual_em_andamento) {
                manualBadge = '<span class="badge badge-andamento"><i class="fas fa-clock"></i> Manual em Andamento</span>';
            } else {
                manualBadge = '<span class="badge badge-vazio"><i class="fas fa-times-circle"></i> Sem Manual</span>';
            }

            return `
                <div class="etapa-card" data-etapa-id="${etapa.id}">
                    <div class="etapa-card-body">
                        <div class="etapa-card-main">
                            <div class="etapa-codigo">${escapeHtml(etapa.codigo_etapa)}</div>
                            <div class="etapa-nome">${escapeHtml(etapa.nome_etapa)}</div>
                        </div>
                        <div class="etapa-card-info">
                            <div class="etapa-executores">
                                <i class="fas fa-users"></i> ${escapeHtml(executoresNomes)}
                            </div>
                            <!-- ⭐ Objetivo da etapa -->
                            <div class="etapa-objetivo">
                                <i class="fas fa-bullseye"></i> ${escapeHtml(etapa.objetivo_etapa || 'Sem objetivo')}
                            </div>
                            <div class="etapa-badges">
                                ${analiseBadge}
                                ${manualBadge}
                            </div>
                        </div>
                    </div>
                    <div class="etapa-card-actions">
                        <button class="btn-icon btn-view" onclick="VisualizarModule.abrir(${etapa.id})" title="Visualizar">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn-icon btn-edit" onclick="ModalEtapaModule.editar(${etapa.id})" title="Editar">
                            <i class="fas fa-pencil-alt"></i>
                        </button>
                        <button class="btn-icon btn-delete" onclick="ModalEtapaModule.excluir(${etapa.id}, '${escapeHtml(etapa.nome_etapa)}')" title="Excluir">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </div>
            `;
        }));

        container.innerHTML = cardsHtml.join('');
    },

    // ============================================================
    // SPINNER HTML
    // ============================================================
    _spinnerHTML(mensagem) {
        return `
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

};