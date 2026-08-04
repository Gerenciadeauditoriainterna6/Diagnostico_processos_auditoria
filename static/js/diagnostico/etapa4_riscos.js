// ============================================================
// etapa4_riscos.js - ETAPA 4: Riscos Identificados
// ============================================================

const Etapa4Module = {
    
    processosPendentes: [],
    processoSelecionadoId: null,
    
    // Elementos do DOM
    listaContainer: null,
    kanbanContainer: null,
    listaProcessos: null,
    processoInfo: null,
    btnVoltarLista: null,
    btnProximoLista: null,
    btnVoltarKanban: null,
    btnAdicionarRisco: null,
    modalRisco: null,
    btnFecharModal: null,
    btnCancelarModal: null,
    btnSalvarModal: null,
    outrasCategoriasRisco: [],
    outrasCategoriasCausa: [],
    riscosData: [],
    
    // ============================================================
    // INIT
    // ============================================================
    init() {
        console.log('📌 Etapa4Module: inicializando...');
        
        this.listaContainer = document.getElementById('etapa4-lista-processos');
        this.kanbanContainer = document.getElementById('etapa4-kanban-riscos');
        this.listaProcessos = document.getElementById('etapa4-lista-container');
        this.processoInfo = document.getElementById('etapa4-processo-selecionado-info');
        this.btnVoltarLista = document.getElementById('btn-voltar-etapa3-lista');
        this.btnProximoLista = document.getElementById('btn-proximo-etapa5-lista');
        this.btnVoltarKanban = document.getElementById('btn-voltar-etapa3-kanban');
        this.btnAdicionarRisco = document.getElementById('btn-adicionar-risco');

        // Modal de risco
        this.modalRisco = document.getElementById('modal-risco');
        this.btnFecharModal = document.getElementById('btn-fechar-modal');
        this.btnCancelarModal = document.getElementById('btn-cancelar-modal');
        this.btnSalvarModal = document.getElementById('btn-salvar-modal');
        
        this.configurarEventos();
        console.log('✅ Etapa4Module: inicializado');
    },
    
    // ============================================================
    // CONFIGURAR EVENTOS
    // ============================================================
    configurarEventos() {
        // Voltar para etapa 3 (lista)
        if (this.btnVoltarLista) {
            this.btnVoltarLista.addEventListener('click', () => {
                if (typeof WizardModule !== 'undefined') WizardModule.irParaEtapa(3);
            });
        }
        
        // Próximo (lista) → etapa 5
        if (this.btnProximoLista) {
            this.btnProximoLista.addEventListener('click', () => {
                if (typeof WizardModule !== 'undefined') WizardModule.irParaEtapa(5);
            });
        }
        
        // Voltar para lista (kanban)
        if (this.btnVoltarKanban) {
            this.btnVoltarKanban.addEventListener('click', () => {
                this.mostrarLista();
            });
        }
        
        // Adicionar risco
        if (this.btnAdicionarRisco) {
            this.btnAdicionarRisco.addEventListener('click', () => {
                this.abrirModalRisco();
            });
        }

        // Fechar modal (X)
        if (this.btnFecharModal) {
            this.btnFecharModal.addEventListener('click', () => {
                this.fecharModalRisco();
            });
        }

        // Cancelar modal
        if (this.btnCancelarModal) {
            this.btnCancelarModal.addEventListener('click', () => {
                this.fecharModalRisco();
            });
        }

        // Salvar risco
        if (this.btnSalvarModal) {
            this.btnSalvarModal.addEventListener('click', () => {
                this.salvarRisco();
            });
        }

        

        // Atualizar score
        document.getElementById('modal-impacto').addEventListener('change', () => this.atualizarScorePreview());
        document.getElementById('modal-probabilidade').addEventListener('change', () => this.atualizarScorePreview());
        document.getElementById('apetite_impacto').addEventListener('change', () => this.atualizarScorePreview());
        document.getElementById('apetite_probabilidade').addEventListener('change', () => this.atualizarScorePreview());

        // Checkbox "Outra" - Categoria Risco
        const checkOutraRisco = document.getElementById('check-outra-categoria-risco');
        const outraRiscoContainer = document.getElementById('outra-categoria-risco-container');
        if (checkOutraRisco && outraRiscoContainer) {
            checkOutraRisco.addEventListener('change', () => {
                outraRiscoContainer.style.display = checkOutraRisco.checked ? 'block' : 'none';
            });
        }

        // Checkbox "Outra" - Categoria Causa
        const checkOutraCausa = document.getElementById('check-outra-categoria-causa');
        const outraCausaContainer = document.getElementById('outra-categoria-causa-container');
        if (checkOutraCausa && outraCausaContainer) {
            checkOutraCausa.addEventListener('change', () => {
                outraCausaContainer.style.display = checkOutraCausa.checked ? 'block' : 'none';
            });
        }

        // Adicionar outra categoria de risco
        const btnAddOutraRisco = document.getElementById('btn-adicionar-outra-risco');
        if (btnAddOutraRisco) {
            btnAddOutraRisco.addEventListener('click', () => {
                const texto = document.getElementById('outra-categoria-risco-texto').value.trim();
                if (texto) {
                    this.outrasCategoriasRisco.push(texto.toUpperCase());
                    this.renderizarOutrasCategorias('risco');
                    document.getElementById('outra-categoria-risco-texto').value = '';
                }
            });
        }

        // Adicionar outra categoria de causa
        const btnAddOutraCausa = document.getElementById('btn-adicionar-outra-causa');
        if (btnAddOutraCausa) {
            btnAddOutraCausa.addEventListener('click', () => {
                const texto = document.getElementById('outra-categoria-causa-texto').value.trim();
                if (texto) {
                    this.outrasCategoriasCausa.push(texto.toUpperCase());
                    this.renderizarOutrasCategorias('causa');
                    document.getElementById('outra-categoria-causa-texto').value = '';
                }
            });
        }

        // Fechar modal de visualização pelo X
        const btnFecharVisualizar = document.getElementById('btn-fechar-visualizar-modal');
        if (btnFecharVisualizar) {
            btnFecharVisualizar.addEventListener('click', () => {
                document.getElementById('modal-visualizar-risco').style.display = 'none';
            });
        }

        // Fechar modal de visualização pelo botão fechar
        const btnFecharVisualizarFooter = document.getElementById('btn-fechar-visualizar');
        if (btnFecharVisualizarFooter) {
            btnFecharVisualizarFooter.addEventListener('click', () => {
                document.getElementById('modal-visualizar-risco').style.display = 'none';
            });
        }
    },
    
    // ============================================================
    // AO ENTRAR NA ETAPA
    // ============================================================
    async aoEntrar() {
        console.log('👋 Etapa 4 ativada');
        await this.carregarProcessos();
        this.mostrarLista();
    },
    
    // ============================================================
    // CARREGAR PROCESSOS
    // ============================================================
    async carregarProcessos() {
        const idsSalvos = JSON.parse(sessionStorage.getItem('processos_salvos_ids') || '[]');
        
        if (idsSalvos.length === 0) {
            this.listaProcessos.innerHTML = '<p class="etapa4-lista-vazia">Nenhum processo para gerenciar riscos.</p>';
            return;
        }
        
        this.listaProcessos.innerHTML = '<p style="text-align:center; padding:20px;">Carregando...</p>';
        
        try {
            const response = await window.fetchComAutenticacao(
                `/api/processos-por-ids?ids=${idsSalvos.join(',')}`
            );
            const data = await response.json();
            
            if (data.success) {
                this.processosPendentes = data.processos;
                this.renderizarLista();
            }
        } catch (error) {
            console.error('Erro ao carregar processos:', error);
        }
    },

    fecharModalRisco() {
        document.getElementById('modal-risco').style.display = 'none';
        this.limparFormularioRisco();
    },

    limparFormularioRisco() {
        document.getElementById('modal-risco-idx').value = '';
        document.getElementById('modal-nome_risco').value = '';
        document.getElementById('modal-fator_risco').value = '';
        document.getElementById('modal-melhoria').value = '';
        document.getElementById('modal-impacto').value = '';
        document.getElementById('modal-probabilidade').value = '';
        document.getElementById('modal-motivo_risco').value = '';
        document.getElementById('modal-como-tratar').value = '';
        document.getElementById('modal-desc-tratamento').value = '';
        document.getElementById('modal-prazo-implantacao').value = '';
        document.getElementById('apetite_impacto').value = '';
        document.getElementById('apetite_probabilidade').value = '';
        document.getElementById('modal-score-preview').innerHTML = '<strong>Risco Bruto:</strong> Selecione impacto e probabilidade';
        document.getElementById('apetite-score-preview').innerHTML = '<strong>Apetite ao Risco:</strong> Selecione impacto e probabilidade aceitável';
        // Limpar checkboxes
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);

        this.outrasCategoriasRisco = [];
        this.outrasCategoriasCausa = [];
        document.getElementById('outras-categorias-risco-lista').innerHTML = '';
        document.getElementById('outras-categorias-causa-lista').innerHTML = '';
        document.getElementById('outra-categoria-risco-container').style.display = 'none';
        document.getElementById('outra-categoria-causa-container').style.display = 'none';
    },

    salvarRisco() {
        const nomeRisco = document.getElementById('modal-nome_risco').value.trim();
        
        if (!nomeRisco) {
            window.mostrarToast('⚠️ Informe o nome do risco!', 'warning');
            return;
        }
        
        // Coletar categorias dos checkboxes (PULAR "OUTRA")
        const categorias = [];
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]:checked').forEach(cb => {
            if (cb.value !== 'OUTRA') {  // ⭐ Pula o checkbox "Outra"
                categorias.push(cb.value);
            }
        });

        // ⭐ Depois adiciona as categorias digitadas manualmente
        const checkOutraRisco = document.getElementById('check-outra-categoria-risco');
        if (checkOutraRisco && checkOutraRisco.checked) {
            this.outrasCategoriasRisco.forEach(cat => categorias.push(cat));
        }

        // Coletar causas dos checkboxes (PULAR "OUTRA")
        const causas = [];
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]:checked').forEach(cb => {
            if (cb.value !== 'OUTRA') {  // ⭐ Pula o checkbox "Outra"
                causas.push(cb.value);
            }
        });

        // ⭐ Depois adiciona as causas digitadas manualmente
        const checkOutraCausa = document.getElementById('check-outra-categoria-causa');
        if (checkOutraCausa && checkOutraCausa.checked) {
            this.outrasCategoriasCausa.forEach(cat => causas.push(cat));
        }

        const riscoId = document.getElementById('modal-risco-idx').value;
        
        const risco = {
            processo_id: this.processoSelecionadoId,
            nome_risco: nomeRisco,
            fator_risco: document.getElementById('modal-fator_risco').value.trim(),
            melhoria: document.getElementById('modal-melhoria').value.trim(),
            impacto: document.getElementById('modal-impacto').value,
            probabilidade: document.getElementById('modal-probabilidade').value,
            motivo_risco: document.getElementById('modal-motivo_risco').value.trim(),
            categorias: categorias,
            categoria_causa: causas,
            como_tratar: document.getElementById('modal-como-tratar').value,
            desc_tratamento: document.getElementById('modal-desc-tratamento').value.trim(),
            prazo_implantacao: document.getElementById('modal-prazo-implantacao').value.trim(),
            apetite_impacto: document.getElementById('apetite_impacto').value,
            apetite_probabilidade: document.getElementById('apetite_probabilidade').value
        };

        if (riscoId) {
            risco.id = parseInt(riscoId);
        }
        
        console.log('📤 Salvando risco:', risco);
        this.enviarRiscoAPI(risco);

        console.log('📤 Categorias finais:', categorias);
        console.log('📤 Causas finais:', causas);
    },

    async enviarRiscoAPI(risco) {
        try {
            const response = await window.fetchComAutenticacao('/api/processo/salvar-riscos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    processo_id: this.processoSelecionadoId,
                    riscos: [risco]
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.mostrarToast('✅ Risco salvo com sucesso!', 'success');
                this.fecharModalRisco();
                this.carregarRiscos(); // Recarrega o kanban
            } else {
                window.mostrarToast('❌ Erro ao salvar risco', 'error');
            }
        } catch (error) {
            console.error('Erro ao salvar risco:', error);
        }
    },
    
    // ============================================================
    // RENDERIZAR LISTA DE PROCESSOS
    // ============================================================
    renderizarLista() {
        if (this.processosPendentes.length === 0) {
            this.listaProcessos.innerHTML = '<p class="etapa4-lista-vazia">Nenhum processo encontrado.</p>';
            return;
        }
        
        this.listaProcessos.innerHTML = this.processosPendentes.map(proc => {
            return `
                <div class="processo-item-lista">
                    <div>
                        <strong class="processo-codigo">${proc.codigo_processo}</strong>
                        <span class="processo-nome">${proc.nome_processo}</span>
                        <br>
                        <small style="color: #666;">
                            <i class="fas fa-exclamation-triangle"></i>
                            ${proc.qtd_riscos || 0} riscos | 
                            Score Máx: ${proc.cor_score || ''} ${proc.score_maximo || 0}
                        </small>
                    </div>
                    <button class="btn-gerenciar-riscos btn-outline btn-sm" data-processo-id="${proc.id}">
                        <i class="fas fa-exclamation-triangle"></i> Cadastrar/Editar Riscos
                    </button>
                </div>
            `;
        }).join('');
        
        this.listaProcessos.querySelectorAll('.btn-gerenciar-riscos').forEach(btn => {
            btn.addEventListener('click', () => {
                const processoId = parseInt(btn.dataset.processoId);
                this.mostrarKanban(processoId);
            });
        });
    },
    
    // ============================================================
    // MOSTRAR LISTA
    // ============================================================
    mostrarLista() {
        this.listaContainer.style.display = 'block';
        this.kanbanContainer.style.display = 'none';
        this.processoSelecionadoId = null;
        this.carregarProcessos();
    },
    
    // ============================================================
    // MOSTRAR KANBAN
    // ============================================================
    mostrarKanban(processoId) {
        const proc = this.processosPendentes.find(p => p.id === processoId);
        if (!proc) return;
        
        this.processoSelecionadoId = processoId;
        
        // Mostrar info do processo
        this.processoInfo.innerHTML = `
            <strong><i class="fas fa-tag"></i> ${proc.codigo_processo} - ${proc.nome_processo}</strong>
        `;
        
        this.listaContainer.style.display = 'none';
        this.kanbanContainer.style.display = 'block';
        
        this.carregarRiscos();
    },
    
    // ============================================================
    // CARREGAR RISCOS (KANBAN)
    // ============================================================
    async carregarRiscos() {
        if (!this.processoSelecionadoId) return;
        
        try {
            const response = await window.fetchComAutenticacao(
                `/api/processo/${this.processoSelecionadoId}/riscos`
            );
            const data = await response.json();
            
            if (data.success) {
                this.riscosData = data.riscos;  // ⭐ GUARDAR OS DADOS
                this.renderizarKanban(data.riscos);
            }
        } catch (error) {
            console.error('Erro ao carregar riscos:', error);
        }
    },
    
    // ============================================================
    // RENDERIZAR KANBAN
    // ============================================================
    renderizarKanban(riscos) {
        // Limpar colunas
        ['baixo', 'medio', 'alto', 'critico'].forEach(nivel => {
            const col = document.getElementById(`col-${nivel}`);
            const count = document.getElementById(`count-${nivel}`);
            if (col) col.innerHTML = '';
            if (count) count.textContent = '0';
        });
        
        let contagem = { baixo: 0, medio: 0, alto: 0, critico: 0 };
        
        riscos.forEach(risco => {
            const score = risco.score_risco || 0;
            let nivel;
            
            if (score <= 3) nivel = 'baixo';
            else if (score <= 7) nivel = 'medio';
            else if (score <= 11) nivel = 'alto';
            else nivel = 'critico';
            
            contagem[nivel]++;
            
            const col = document.getElementById(`col-${nivel}`);
            if (col) {
                col.innerHTML += this.renderizarCardRisco(risco);
            }
        });
        
        // Atualizar contadores
        ['baixo', 'medio', 'alto', 'critico'].forEach(nivel => {
            const count = document.getElementById(`count-${nivel}`);
            if (count) count.textContent = contagem[nivel];
        });

        this.configurarEventosKanban();
    },

    configurarEventosKanban() {
        document.querySelectorAll('.btn-editar-risco').forEach(btn => {
            btn.addEventListener('click', () => {
                const riscoId = parseInt(btn.dataset.riscoId);
                this.editarRisco(riscoId);
            });
        });

        document.querySelectorAll('.btn-excluir-risco').forEach(btn => {
            btn.addEventListener('click', () => {
                const riscoId = parseInt(btn.dataset.riscoId);
                this.excluirRisco(riscoId);
            });
        });

        document.querySelectorAll('.btn-visualizar-risco').forEach(btn => {
            btn.addEventListener('click', () => {
                const riscoId = parseInt(btn.dataset.riscoId);
                this.visualizarRisco(riscoId);
            })
        })
    },

    editarRisco(riscoId) {
        // ===== 1. ACHAR O RISCO NA LISTA =====
        const risco = this.riscosData.find(r => r.id === riscoId);
        if (!risco) return;
        
        // ===== 2. ABRIR O MODAL E MUDAR O TÍTULO =====
        document.getElementById('modal-risco').style.display = 'flex';
        document.getElementById('modal-title').innerHTML = '<i class="fas fa-shield-alt"></i> Editar Risco';
        
        // ===== 3. PREENCHER O ID (ESCONDIDO) =====
        document.getElementById('modal-risco-idx').value = risco.id;
        
        // ===== 4. PREENCHER OS CAMPOS SIMPLES =====
        document.getElementById('modal-nome_risco').value = risco.nome_risco || '';
        document.getElementById('modal-fator_risco').value = risco.fator_risco || '';
        document.getElementById('modal-melhoria').value = risco.melhoria || '';
        document.getElementById('modal-impacto').value = risco.impacto || '';
        document.getElementById('modal-probabilidade').value = risco.probabilidade || '';
        document.getElementById('modal-motivo_risco').value = risco.motivo_risco || '';
        document.getElementById('modal-desc-tratamento').value = risco.desc_tratamento || '';
        document.getElementById('modal-prazo-implantacao').value = risco.prazo_implantacao || '';
        document.getElementById('apetite_impacto').value = risco.apetite_impacto || '';
        document.getElementById('apetite_probabilidade').value = risco.apetite_probabilidade || '';
        
        // ===== 5. PREENCHER "COMO TRATAR" =====
        const mapaTratamento = {
            'ACEITAR': 'Aceitar',
            'MITIGAR': 'Mitigar',
            'COMPARTILHAR': 'Compartilhar',
            'COMPARTILHAR (TRANSFERIR)': 'Compartilhar',
            'EVITAR': 'Evitar'
        };
        const valorTratamento = mapaTratamento[(risco.como_tratar || '').toUpperCase()] || '';
        document.getElementById('modal-como-tratar').value = valorTratamento;
        
        // ===== 6. PREENCHER OBJETIVO DO PROCESSO =====
        const proc = this.processosPendentes.find(p => p.id === this.processoSelecionadoId);
        const objetivoTexto = document.getElementById('modal-objetivo-texto');
        if (objetivoTexto && proc) {
            objetivoTexto.textContent = proc.objetivo || 'Nenhum objetivo cadastrado.';
        }
        
        // ============================================================
        // 7. CATEGORIAS DE RISCO - SEPARAR CHECKBOX VS "OUTRA"
        // ============================================================
        
        // O que veio do banco (ex: ["RISCO FINANCEIRO", "RISCO TESTE"])
        const categoriasSalvas = risco.categorias || [];
        
        // Quais categorias têm checkbox fixo
        const categoriasCheckbox = [
            'Risco Financeiro', 'Risco Legal', 'Risco Inerente',
            'Risco de TI', 'Risco Reputacional', 'Risco de Integridade', 'Risco Ambiental'
        ];
        
        // Limpa a lista de "Outras"
        this.outrasCategoriasRisco = [];
        
        // Para cada checkbox no HTML
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => {
            if (cb.value === 'OUTRA') {
                const categoriasUpper = categoriasSalvas.map(c => c.toUpperCase());
                const extras = categoriasSalvas.filter(c => !categoriasCheckbox.some(fixo => fixo.toUpperCase() === c.toUpperCase()));
                cb.checked = extras.length > 0;
                this.outrasCategoriasRisco = extras;
            } else {
                // ⭐ Comparação case-insensitive
                cb.checked = categoriasSalvas.some(cat => cat.toUpperCase() === cb.value.toUpperCase());
            }
        });
        
        // Se tem categorias extras, mostra o container e as tags
        if (this.outrasCategoriasRisco.length > 0) {
            document.getElementById('outra-categoria-risco-container').style.display = 'block';
            this.renderizarOutrasCategorias('risco');
        }
        
        // ============================================================
        // 8. CATEGORIAS DE CAUSA - MESMA LÓGICA
        // ============================================================
        
        const causasSalvas = risco.categoria_causa || [];
        
        const causasCheckbox = [
            'FALHA OPERACIONAL', 'FALTA DE CONTROLE', 'NÃO CONFORMIDADE',
            'PROBLEMAS FINANCEIROS', 'FENÔMENO NATURAL', 'FRAUDE'
        ];
        
        this.outrasCategoriasCausa = [];
        
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]').forEach(cb => {
            if (cb.value === 'OUTRA') {
                const causasUpper = causasSalvas.map(c => c.toUpperCase());
                const extras = causasSalvas.filter(c => !causasCheckbox.some(fixo => fixo.toUpperCase() === c.toUpperCase()));
                cb.checked = extras.length > 0;
                this.outrasCategoriasCausa = extras;
            } else {
                // ⭐ Comparação case-insensitive
                cb.checked = causasSalvas.some(cat => cat.toUpperCase() === cb.value.toUpperCase());
            }
        });
        
        if (this.outrasCategoriasCausa.length > 0) {
            document.getElementById('outra-categoria-causa-container').style.display = 'block';
            this.renderizarOutrasCategorias('causa');
        }
        
        // ===== 9. ATUALIZAR O SCORE =====
        this.atualizarScorePreview();
    },

    async excluirRisco(riscoId) {
        const confirmado = confirm('Tem certeza que deseja excluir este risco?');
        if (!confirmado) return;
        
        try {
            const response = await window.fetchComAutenticacao(`/api/risco/${riscoId}/excluir`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.mostrarToast('✅ Risco excluído com sucesso!', 'success');
                this.carregarRiscos();  // Recarrega o kanban
            } else {
                window.mostrarToast('❌ Erro ao excluir risco', 'error');
            }
        } catch (error) {
            console.error('Erro ao excluir risco:', error);
        }
    },

    visualizarRisco(riscoId) {
        const risco = this.riscosData.find(r => r.id === riscoId);
        if (!risco) return;
        
        // Preencher o modal de visualização que já existe
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
        
        // Calcular score do apetite (mesma lógica)
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
        // ✅ Depois (garante que os valores existem e estão no formato certo):
        const impactoApetite = (risco.apetite_impacto || '').toUpperCase().trim();
        const probApetite = (risco.apetite_probabilidade || '').toUpperCase().trim();

        if (impactoApetite && probApetite) {
            const scoreApetite = mapa[`${impactoApetite},${probApetite}`];
            document.getElementById('vis-score-apetite').textContent = scoreApetite !== undefined ? scoreApetite : '-';
        } else {
            document.getElementById('vis-score-apetite').textContent = '-';
        }
        
        // Mostrar modal
        document.getElementById('modal-visualizar-risco').style.display = 'flex';
    },

    // Atualizar score quando mudar impacto ou probabilidade
    atualizarScorePreview() {
        const impacto = document.getElementById('modal-impacto').value;
        const probabilidade = document.getElementById('modal-probabilidade').value;
        const apetiteImpacto = document.getElementById('apetite_impacto').value;
        const apetiteProbabilidade = document.getElementById('apetite_probabilidade').value;
        
        const preview = document.getElementById('modal-score-preview');
        const apetitePreview = document.getElementById('apetite-score-preview');
        
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
        
        // Score da magnitude
        if (!impacto || !probabilidade) {
            preview.innerHTML = '<strong>Risco Bruto:</strong> Selecione impacto e probabilidade';
        } else {
            const score = mapa[`${impacto},${probabilidade}`] || 0;
            preview.innerHTML = `<strong>Risco Bruto: ${score}</strong>`;
        }
        
        // Score do apetite (risco residual)
        if (!apetiteImpacto || !apetiteProbabilidade) {
            apetitePreview.innerHTML = '<strong>Risco Residual:</strong> Selecione o apetite para impacto e probabilidade';
        } else {
            const scoreApetite = mapa[`${apetiteImpacto},${apetiteProbabilidade}`] || 0;
            apetitePreview.innerHTML = `<strong>Risco Residual:</strong> <span id="preview-apetite-score">${scoreApetite}</span>`;
        }
    },
    
    // ============================================================
    // RENDERIZAR CARD DE RISCO
    // ============================================================
    renderizarCardRisco(risco) {
        const score = risco.score_risco || 0;
        let classeCor;
        
        if (score <= 3) classeCor = 'low';
        else if (score <= 7) classeCor = 'medium';
        else if (score <= 11) classeCor = 'high';
        else classeCor = 'critical';
        
        return `
            <div class="kanban-card ${classeCor}">
                <div class="kanban-card-title">${risco.nome_risco || 'Sem nome'}</div>
                <div class="kanban-card-score">Score: ${score}</div>
                <div class="kanban-card-actions">
                    <button class="btn-visualizar-risco" data-risco-id="${risco.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-editar-risco" data-risco-id="${risco.id}">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-excluir-risco" data-risco-id="${risco.id}">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
        `;
    },
    
    // ============================================================
    // ABRIR MODAL DE RISCO
    // ============================================================
    abrirModalRisco() {
        this.limparFormularioRisco();
        
        const proc = this.processosPendentes.find(p => p.id === this.processoSelecionadoId);
        
        document.getElementById('modal-title').innerHTML = '<i class="fas fa-shield-alt"></i> Novo Risco';
        
        const objetivoTexto = document.getElementById('modal-objetivo-texto');
        if (objetivoTexto && proc) {
            objetivoTexto.textContent = proc.objetivo || 'Nenhum objetivo cadastrado para este processo.';
        }
        
        document.getElementById('modal-risco').style.display = 'flex';
    },

    renderizarOutrasCategorias(tipo) {
        const listaId = tipo === 'risco' ? 'outras-categorias-risco-lista' : 'outras-categorias-causa-lista';
        const lista = tipo === 'risco' ? this.outrasCategoriasRisco : this.outrasCategoriasCausa;
        const container = document.getElementById(listaId);
        
        if (!container) return;
        
        container.innerHTML = lista.map((cat, index) => `
            <span style="background:#e8f4f8; padding:4px 10px; border-radius:15px; font-size:12px; display:inline-flex; align-items:center; gap:5px;">
                ${cat}
                <button type="button" style="background:none; border:none; cursor:pointer; color:#dc3545; font-size:14px;"
                    onclick="Etapa4Module.removerOutraCategoria('${tipo}', ${index})">&times;</button>
            </span>
        `).join('');
    },

    removerOutraCategoria(tipo, index) {
        if (tipo === 'risco') {
            this.outrasCategoriasRisco.splice(index, 1);
        } else {
            this.outrasCategoriasCausa.splice(index, 1);
        }
        this.renderizarOutrasCategorias(tipo);
    },

    
    
};