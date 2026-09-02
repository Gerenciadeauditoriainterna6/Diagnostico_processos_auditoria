// ============================================================
// modal_etapa.js - MÓDULO DO MODAL DE ETAPA
// ============================================================

const ModalEtapaModule = {

    isSalva: false,
    etapaIdAtual: null,

    init() {
        console.log('📌 ModalEtapaModule: inicializado');
        this.configurarCollapsibles();
    },

    configurarCollapsibles() {
        document.querySelectorAll('.collapsible-section').forEach(section => {
            const header = section.querySelector('.collapsible-header');
            
            if (header) {
                header.addEventListener('click', () => {
                    section.classList.toggle('collapsed');
                });
            }
        });
    },

    configurarEventos() {
        const btnFechar = document.getElementById('btn-fechar-modal-etapa');
        const btnCancelar = document.getElementById('btn-cancelar-modal-etapa');
        const btnSalvar = document.getElementById('btn-salvar-modal-etapa');

        if (btnFechar) btnFechar.addEventListener('click', () => this.fechar());
        if (btnCancelar) btnCancelar.addEventListener('click', () => this.fechar());
        if (btnSalvar) btnSalvar.addEventListener('click', () => this.salvar());
    },

    // ============================================================
    // NOVA ETAPA
    // ============================================================
    async nova() {
        console.log('📌 Abrindo modal de nova etapa...');
        
        LoadingModule.mostrar('Preparando cadastro de nova etapa...');
        
        try {
            this.limparFormulario();
            document.getElementById('modal-etapa-title').innerHTML = '<i class="fas fa-plus-circle"></i> Nova Etapa';
            ManualModule.setEtapaId(null);
            await this.gerarCodigo();
            await ExecutoresModule.carregar(TabelaEtapasModule.processoAtualId);
            ExecutoresModule.limpar();
            AutoSaveModule.setup();

            PoliticasObrigacoesModule.inicializar('[]');
            AnalisesModule.temporarias = [];
            AnalisesModule.existentes = [];
            AnalisesModule.renderizar();
            AnalisesModule.esconderForm();
            
            // ⭐ Limpar Política Interna
            if (typeof PoliticaInternaModule !== 'undefined') {
                PoliticaInternaModule.limpar();
            }

            ManualModule.resetarInterface();
            AutoSaveModule.carregarRascunho();
            document.getElementById('modal-etapa').style.display = 'flex';
            
        } catch (error) {
            console.error('❌ Erro ao abrir nova etapa:', error);
            window.mostrarToast('Erro ao abrir nova etapa', 'error');
            
        } finally {
            LoadingModule.ocultar();
        }
    },

    // ============================================================
    // EDITAR ETAPA
    // ============================================================
    async editar(etapaId) {
        console.log('📌 Abrindo modal de edição...');
        
        LoadingModule.mostrar('Carregando dados da etapa...');
        
        try {
            this.limparFormulario();
            AutoSaveModule.desabilitar();
            AutoSaveModule.limparRascunho();
            AnalisesModule.temporarias = [];

            ManualModule.setEtapaId(etapaId);

            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}`);
            const data = await response.json();

            if (data.success) {
                const etapa = data.etapa;
                document.getElementById('modal-etapa-title').innerHTML = '<i class="fas fa-edit"></i> Editar Etapa';
                document.getElementById('modal-etapa-id').value = etapa.id;
                document.getElementById('modal-codigo-etapa').value = etapa.codigo_etapa;
                document.getElementById('modal-nome-etapa').value = etapa.nome_etapa;
                document.getElementById('modal-descricao-etapa').value = etapa.descricao_etapa;
                document.getElementById('modal-como-feito').value = etapa.como_e_feito;
                document.getElementById('modal-objetivo-etapa').value = etapa.objetivo_etapa;
                document.getElementById('modal-status-etapa').value = etapa.status_etapa;
                document.getElementById('modal-politica-interna').value = etapa.politica_interna || '';

                // ⭐ NOVO: Carregar arquivo da política interna
                if (typeof PoliticaInternaModule !== 'undefined') {
                    console.log('📎 Carregando política interna:', {
                        url: etapa.politica_interna_url,
                        nome: etapa.politica_interna_nome
                    });
                    
                    await PoliticaInternaModule.carregarPoliticaInterna(
                        etapa.politica_interna_url || '',
                        etapa.politica_interna_nome || ''
                    );
                }

                PoliticasObrigacoesModule.inicializar(etapa.obrigacoes_regulatorias);
                await ExecutoresModule.carregar(TabelaEtapasModule.processoAtualId);
                ExecutoresModule.limpar();

                if (etapa.executores_etapa) {
                    ExecutoresModule.carregarSalvos(etapa.executores_etapa);
                }

                AutoSaveModule.setup();
                AutoSaveModule.habilitar();
                await AnalisesModule.carregar(etapaId);
                AnalisesModule.esconderForm();
                ManualModule.carregarEstado(etapaId);
                ManualModule.atualizarInterface(etapa);

                document.getElementById('modal-etapa').style.display = 'flex';
            } else {
                window.mostrarToast('❌ Erro: ' + (data.error || 'Erro ao carregar etapa'), 'error');
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar etapa:', error);
            window.mostrarToast('Erro ao carregar dados da etapa', 'error');
            
        } finally {
            LoadingModule.ocultar();
        }
    },
    // ============================================================
    // EXCLUIR ETAPA
    // ============================================================
    async excluir(etapaId, etapaNome) {
        if (!confirm(`Excluir a etapa "${etapaNome}"?`)) return;
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}/excluir`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            if (data.success) {
                window.mostrarToast('✅ Etapa excluída!', 'success');
                TabelaEtapasModule.carregarEtapas();
            } else {
                window.mostrarToast('❌ Erro: ' + (data.error || 'Desconhecido'), 'error');
            }
        } catch (error) {
            window.mostrarToast('❌ Erro de conexão', 'error');
        }
    },

    // ============================================================
    // SALVAR ETAPA
    // ============================================================
    async salvar() {
        if (!this.validar()) {
            window.mostrarToast('⚠️ Preencha o nome da etapa', 'warning');
            return;
        }

        const nomeEtapa = document.getElementById('modal-nome-etapa').value.trim();
        if (!nomeEtapa) return;

        // ⭐ Loading global
        LoadingModule.mostrar('Salvando etapa...');

        try {
            const etapaId = document.getElementById('modal-etapa-id').value || null;
            // ⭐ Processar upload da política interna
            let politicaInternaArquivo = null;
            if (typeof PoliticaInternaModule !== 'undefined') {
                politicaInternaArquivo = await PoliticaInternaModule.processarUpload(etapaId);
            }
            const obrigacoes = await PoliticasObrigacoesModule.coletarDados();
            const politicasProcessadas = await PoliticasObrigacoesModule.processarUploads(obrigacoes, etapaId);

            const payload = {
                id: etapaId,
                processo_id: TabelaEtapasModule.processoAtualId,
                auditoria_id: null,
                codigo_etapa: document.getElementById('modal-codigo-etapa')?.value || '',
                nome_etapa: nomeEtapa,
                descricao_etapa: document.getElementById('modal-descricao-etapa')?.value || '',
                como_e_feito: document.getElementById('modal-como-feito')?.value || '',
                objetivo_etapa: document.getElementById('modal-objetivo-etapa')?.value || '',
                status_etapa: document.getElementById('modal-status-etapa')?.value || 'ATIVA',
                politica_interna: document.getElementById('modal-politica-interna')?.value || '',
                obrigacoes_regulatorias: JSON.stringify({ politicas: politicasProcessadas }),
                executores_etapa: ExecutoresModule.getSelectedIds().join(','),
                manual_em_andamento: document.getElementById('manual_em_andamento')?.checked || false,
                politica_interna_url: politicaInternaArquivo?.url || '',
                politica_interna_nome: politicaInternaArquivo?.nome || ''
            };

            const response = await window.fetchComAutenticacao('/api/etapa/salvar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (AnalisesModule.temporarias.length > 0) {
                    await AnalisesModule.salvarTemporarias(data.etapa_id);
                }
                window.mostrarToast('✅ Etapa salva!', 'success');
                AutoSaveModule.limparRascunho();
                document.getElementById('modal-etapa').style.display = 'none';
                AnalisesModule.temporarias = [];
                AnalisesModule.existentes = [];
                TabelaEtapasModule.carregarEtapas();
            } else {
                window.mostrarToast('❌ Erro: ' + (data.error || 'Desconhecido'), 'error');
            }
            
        } catch (error) {
            console.error('❌ Erro ao salvar:', error);
            window.mostrarToast('❌ Erro de conexão', 'error');
            
        } finally {
            // ⭐ SEMPRE esconder loading
            LoadingModule.ocultar();
        }
    },

    // ============================================================
    // FECHAR MODAL
    // ============================================================
    fechar() {
        AutoSaveModule.salvarRascunho();
        document.getElementById('modal-etapa').style.display = 'none';
        this.limparFormulario();
    },

    // ============================================================
    // VALIDAÇÃO
    // ============================================================
    validar() {
        document.querySelectorAll('#modal-etapa .form-group').forEach(g => g.classList.remove('error'));
        const nomeEtapa = document.getElementById('modal-nome-etapa').value.trim();
        if (!nomeEtapa) {
            document.getElementById('modal-nome-etapa').closest('.form-group').classList.add('error');
            return false;
        }
        return true;
    },

    // ============================================================
    // LIMPAR FORMULÁRIO
    // ============================================================
    limparFormulario() {
        ['modal-etapa-id', 'modal-codigo-etapa', 'modal-nome-etapa', 'modal-descricao-etapa',
        'modal-como-feito', 'modal-objetivo-etapa', 'modal-politica-interna']
            .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

        const statusSelect = document.getElementById('modal-status-etapa');
        if (statusSelect) statusSelect.value = 'ATIVA';

        // ⭐ Substituir ObrigacoesModule por PoliticasObrigacoesModule
        if (typeof PoliticasObrigacoesModule !== 'undefined') {
            PoliticasObrigacoesModule.limpar();
        }
        
        document.querySelectorAll('#modal-etapa .form-group').forEach(g => g.classList.remove('error'));

        ManualModule.resetarInterface();
        
        AnalisesModule.temporarias = [];
        AnalisesModule.existentes = [];
        if (typeof AnalisesModule.renderizar === 'function') AnalisesModule.renderizar();
        if (typeof AnalisesModule.esconderForm === 'function') AnalisesModule.esconderForm();
    },

    // ============================================================
    // GERAR CÓDIGO
    // ============================================================
    async gerarCodigo() {
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/gerar-codigo?processo_id=${TabelaEtapasModule.processoAtualId}`);
            const data = await response.json();
            if (data.success) {
                document.getElementById('modal-codigo-etapa').value = data.codigo_etapa;
            }
        } catch (error) {
            console.error('Erro ao gerar código:', error);
        }
    }

};