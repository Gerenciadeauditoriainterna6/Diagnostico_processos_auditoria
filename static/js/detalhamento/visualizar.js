// ============================================================
// visualizar.js - MÓDULO DE VISUALIZAÇÃO DE ETAPA
// ============================================================

const VisualizarModule = {

    init() {
        console.log('📌 VisualizarModule: inicializado');
        
        // Configurar botão de fechar
        const btnFechar = document.querySelector('#modal-visualizar-etapa .modal-close');
        if (btnFechar) {
            btnFechar.addEventListener('click', () => this.fechar());
        }
        
    },

    // ============================================================
    // ABRIR MODAL DE VISUALIZAÇÃO
    // ============================================================
    async abrir(etapaId) {
        const modal = document.getElementById('modal-visualizar-etapa');
        const body = document.getElementById('modal-visualizar-body');
        if (!modal || !body) return;

        modal.style.display = 'flex';
        body.innerHTML = this._spinnerHTML('Carregando visualização...');

        try {
            const [respEtapa, respAnalises] = await Promise.all([
                window.fetchComAutenticacao(`/api/etapa/${etapaId}`),
                window.fetchComAutenticacao(`/api/etapa/${etapaId}/analises`)
            ]);

            const dataEtapa = await respEtapa.json();
            const dataAnalises = await respAnalises.json();

            if (dataEtapa.success) {
                body.innerHTML = await this._renderizar(dataEtapa.etapa, dataAnalises.success ? dataAnalises.analises || [] : []);
            }
        } catch (error) {
            body.innerHTML = '<div class="alert-error">Erro ao carregar dados da etapa.</div>';
        }
    },

    // ============================================================
    // FECHAR MODAL
    // ============================================================
    fechar() {
        const modal = document.getElementById('modal-visualizar-etapa');
        if (modal) modal.style.display = 'none';
    },

    // ============================================================
    // RENDERIZAR
    // ============================================================
    async _renderizar(etapa, analises) {
        const executoresNomes = typeof ExecutoresModule !== 'undefined' 
            ? await ExecutoresModule.getNomes(etapa.executores_etapa) : '-';

        const temManual = etapa.manual_nome && etapa.manual_nome.trim() !== '';
        const emAndamento = etapa.manual_em_andamento || false;

        let manualStatus = '';
        if (temManual) {
            manualStatus = '<span class="vis-badge vis-badge-success"><i class="fas fa-check-circle"></i> Manual Concluído</span>';
        } else if (emAndamento) {
            manualStatus = '<span class="vis-badge vis-badge-warning"><i class="fas fa-clock"></i> Manual em Andamento</span>';
        } else {
            manualStatus = '<span class="vis-badge vis-badge-empty"><i class="fas fa-times-circle"></i> Nenhum Manual</span>';
        }

        const statusEtapa = etapa.status_etapa === 'ATIVA' 
            ? '<span class="vis-badge vis-badge-success"><i class="fas fa-circle"></i> ATIVA</span>'
            : '<span class="vis-badge vis-badge-danger"><i class="fas fa-circle"></i> INATIVA</span>';

        const obrigacoesHtml = this._renderizarObrigacoes(etapa.obrigacoes_regulatorias);
        const analisesHtml = analises.length === 0 
            ? '<div class="vis-empty"><i class="fas fa-clipboard"></i> Nenhuma análise cadastrada</div>'
            : analises.map(a => this._renderizarAnalise(a)).join('');

        return `
            <div class="vis-etapa-container-v2">
                
                <!-- Cabeçalho -->
                <div class="vis-header">
                    <div class="vis-codigo">${escapeHtml(etapa.codigo_etapa)}</div>
                    <div class="vis-titulo">${escapeHtml(etapa.nome_etapa)}</div>
                    ${statusEtapa}
                </div>
                
                <!-- Grid de informações -->
                <div class="vis-grid-v2">
                    <div class="vis-col">
                        <!-- Executores -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-users"></i> Executores
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(executoresNomes)}
                            </div>
                        </div>
                        
                        <!-- Descrição -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-align-left"></i> Descrição
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(etapa.descricao_etapa) || '<span class="vis-nao-informado">Não informado</span>'}
                            </div>
                        </div>
                        
                        <!-- Como é feito -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-cogs"></i> Como é feito?
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(etapa.como_e_feito) || '<span class="vis-nao-informado">Não informado</span>'}
                            </div>
                        </div>
                    </div>
                    
                    <div class="vis-col">
                        <!-- Objetivo -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-bullseye"></i> Objetivo
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(etapa.objetivo_etapa) || '<span class="vis-nao-informado">Não informado</span>'}
                            </div>
                        </div>
                        
                        <!-- Política Interna -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-gavel"></i> Política Interna
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(etapa.politica_interna) || '<span class="vis-nao-informado">Não informado</span>'}
                            </div>
                        </div>
                        
                        <!-- Manual -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-book"></i> Manual da Etapa
                            </div>
                            <div class="vis-card-body">
                                ${manualStatus}
                                ${temManual ? `
                                    <div style="margin-top:6px;font-size:13px;display:flex;align-items:center;gap:10px;">
                                        📄 ${escapeHtml(etapa.manual_nome)}
                                        <button onclick="ManualModule.baixar(${etapa.id})"
                                            style="background:#0b5b99;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;">
                                            <i class="fas fa-download"></i> Baixar
                                        </button>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Obrigações Regulatórias -->
                <div class="vis-card vis-card-full">
                    <div class="vis-card-header">
                        <i class="fas fa-balance-scale"></i> Obrigações Regulatórias
                    </div>
                    <div class="vis-card-body">
                        ${obrigacoesHtml}
                    </div>
                </div>
                
                <!-- Análises -->
                <div class="vis-card vis-card-full">
                    <div class="vis-card-header">
                        <i class="fas fa-clipboard-check"></i> Análises do Auditado
                    </div>
                    <div class="vis-card-body">
                        ${analisesHtml}
                    </div>
                </div>
                
            </div>
        `;
    },

    _renderizarObrigacoes(obrigacoesJson) {
        try {
            const obrigacoes = typeof obrigacoesJson === 'string' ? JSON.parse(obrigacoesJson) : (obrigacoesJson || []);
            if (obrigacoes.length === 0) return '<span style="color:#999;">Nenhuma obrigação</span>';
            return obrigacoes.map(o => `
                <div style="background:#f8f9fa;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #184145;">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
                        <div>
                            <strong>${escapeHtml(o.titulo || 'INEXISTENTE')}</strong>
                            ${o.orgao_regulador ? `<span style="color:#666;font-size:12px;margin-left:8px;">${escapeHtml(o.orgao_regulador)}</span>` : ''}
                        </div>
                        ${o.arquivo_url && o.arquivo_url.trim() !== '' ? `
                            <button onclick="ObrigacoesModule.baixarArquivoObrigacaoPorUrl('${o.arquivo_url}', '${escapeHtml(o.arquivo_nome || 'documento.pdf')}')"
                                style="background:#0b5b99;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;white-space:nowrap;">
                                <i class="fas fa-download"></i> Baixar
                            </button>
                        ` : ''}
                    </div>
                    ${o.documento_necessario ? `<div style="font-size:12px;color:#666;margin-top:5px;"><i class="fas fa-file-alt"></i> ${escapeHtml(o.documento_necessario)}</div>` : ''}
                    ${o.prazo ? `<div style="font-size:12px;color:#666;margin-top:3px;"><i class="fas fa-calendar-alt"></i> Prazo: ${formatarDataBR(o.prazo)}</div>` : ''}
                </div>
            `).join('');
        } catch { return '<span>Erro ao carregar</span>'; }
    },

    _renderizarAnalise(a) {
        const temEvidencia = a.evidencia_nome && a.evidencia_nome.trim() !== '';
        
        return `
            <div class="analise-card">
                <div class="analise-card-info">
                    <strong>Ponto de Auditoria:</strong> ${escapeHtml(a.analise_critica || '-')}<br>
                    <strong>Sugestão:</strong> ${escapeHtml(a.sugestao_melhoria || '-')}
                    ${temEvidencia ? `
                        <br><strong>Evidência:</strong> ${escapeHtml(a.evidencia_nome)}
                        <button onclick="AnalisesModule.baixarEvidencia(${a.id}, '${escapeHtml(a.evidencia_nome)}')"
                            style="background:#0b5b99;color:white;border:none;padding:2px 10px;border-radius:4px;cursor:pointer;font-size:11px;">
                            <i class="fas fa-download"></i> Baixar
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    },

    _spinnerHTML(mensagem) {
        return `
            <div style="text-align:center;padding:60px 20px;">
                <div class="dot-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
                <p style="margin-top:25px;color:#666;font-size:14px;">${mensagem}</p>
            </div>
        `;
    }

};