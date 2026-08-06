const DetalhamentoTabelaModule = {

    container: null,

    init() {
        console.log('📌 DetalhamentoTabela: inicializando...');

        this.container = document.getElementById('detalhamento-tabela-container');

        console.log('✅ DetalhamentoTabela: inicializado');
    },

    async carregarProcessosDetalhamento(auditoriaId) {
        
        if (!auditoriaId) {
            if (this.container) {
                this.container.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma auditoria para visualizar os processos.</div>';
            }
            return;
        }

        if (this.container) {
            this.container.innerHTML = `
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
            // ===== 1. VERIFICAR PERMISSÃO DO USUÁRIO =====
            const respPermissao = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
            const dadosPermissao = await respPermissao.json();
            
            if (!dadosPermissao.autorizado) {
                // Usuário NÃO autorizado
                if (this.container) {
                    this.container.innerHTML = `
                        <div class="alert-error" style="text-align: center; padding: 40px;">
                            <i class="fas fa-lock"></i> Você não tem permissão para visualizar processos desta auditoria.
                        </div>
                    `;
                }
                return;
            }
            
            // ===== 2. USUÁRIO AUTORIZADO - CARREGAR PROCESSOS =====
            if (this.container) {
                this.container.innerHTML = `
                <div style="text-align: center; padding: 60px 20px;">
                    <div class="dot-spinner">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                    <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando processos para detalhar...</p>
                </div>
            `;
            }
            
            const response = await fetchComAutenticacao(`/api/processos-por-auditoria?auditoria_id=${auditoriaId}`);
            const data = await response.json();

            if (!data.success || !data.processos || data.processos.length === 0) {
                if (this.container) {
                    this.container.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Nenhum processo encontrado para esta auditoria.</div>';
                }
                return;
            }

            // Montar a tabela de processos (código existente)
            let html = `
                <div style="overflow-x: auto;">
                    <table class="tabela-processos">
                        <thead>
                            <tr>
                                <th>Código</th>
                                <th>Nome do Processo</th>
                                <th>Objetivo</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            for (const processo of data.processos) {
                const temBpmn = processo.fluxo_bpmn_nome && processo.fluxo_bpmn_nome.trim() !== '';
                const corBpmn = temBpmn ? '#28a745' : '#184145';
                
                html += `
                    <tr>
                        <td><strong>${escapeHtml(processo.codigo_processo)}</strong></td>
                        <td>${escapeHtml(processo.nome_processo)}</td>
                        <td>${escapeHtml(processo.objetivo || '-')}</td>
                        <td>
                            <button class="btn-detalhar-processo" data-processo-id="${processo.id}" data-processo-codigo="${processo.codigo_processo}">
                                <i class="fas fa-eye"></i> Detalhar
                            </button>
                        </td>
                    </tr>
                `;
            }

            html += `
                        </tbody>
                    </table>
                </div>
            `;

            if (this.container) {
                this.container.innerHTML = html;
            }

            // Adicionar eventos aos botões
            document.querySelectorAll('.btn-detalhar-processo').forEach(btn => {
                btn.addEventListener('click', () => {
                    const processoId = btn.getAttribute('data-processo-id');
                    const processoCodigo = btn.getAttribute('data-processo-codigo');
                    window.location.href = `/detalhamento_etapas?processo_id=${processoId}&processo_codigo=${processoCodigo}`;
                });
            });

        } catch (error) {
            console.error('Erro ao carregar processos:', error);
            if (this.container) {
                this.container.innerHTML = '<div class="alert-error" style="text-align: center; padding: 40px;"><i class="fas fa-exclamation-triangle"></i> Erro ao carregar processos. Tente novamente.</div>';
            }
        }
    },

}
