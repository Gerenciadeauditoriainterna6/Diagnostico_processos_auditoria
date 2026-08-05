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
        
        // ⭐ Configurar o componente RiscoModal
        RiscoModal.init({
            getProcessoId: () => this.processoSelecionadoId,
            getObjetivo: () => {
                const proc = this.processosPendentes.find(p => p.id === this.processoSelecionadoId);
                return proc?.objetivo || '';
            },
            onSave: async (dados) => {
                await this.enviarRiscoAPI(dados);
            },
            onClose: () => {
                this.carregarRiscos();
            }
        });

        this.configurarEventos();
        console.log('✅ Etapa4Module: inicializado');
    },
    
    // ============================================================
    // CONFIGURAR EVENTOS
    // ============================================================
    configurarEventos() {
        if (this.btnVoltarLista) {
            this.btnVoltarLista.addEventListener('click', () => {
                WizardModule.irParaEtapa(3);
            });
        }
        
        if (this.btnProximoLista) {
            this.btnProximoLista.addEventListener('click', () => {
                WizardModule.irParaEtapa(5);
            });
        }
        
        if (this.btnVoltarKanban) {
            this.btnVoltarKanban.addEventListener('click', () => {
                this.mostrarLista();
            });
        }
        
        if (this.btnAdicionarRisco) {
            this.btnAdicionarRisco.addEventListener('click', () => {
                RiscoModal.abrir();  // ⭐ Usa o componente!
            });
        }
        
        // Fechar modal de visualização
        document.getElementById('btn-fechar-visualizar-modal')?.addEventListener('click', () => {
            document.getElementById('modal-visualizar-risco').style.display = 'none';
        });
        
        document.getElementById('btn-fechar-visualizar')?.addEventListener('click', () => {
            document.getElementById('modal-visualizar-risco').style.display = 'none';
        });
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
        // EDITAR - usa o componente
        document.querySelectorAll('.btn-editar-risco').forEach(btn => {
            btn.addEventListener('click', () => {
                const riscoId = parseInt(btn.dataset.riscoId);
                const risco = this.riscosData.find(r => r.id === riscoId);
                if (risco) {
                    RiscoModal.abrir(risco);
                }
            });
        });

        // EXCLUIR - continua no Etapa4
        document.querySelectorAll('.btn-excluir-risco').forEach(btn => {
            btn.addEventListener('click', () => {
                const riscoId = parseInt(btn.dataset.riscoId);
                this.excluirRisco(riscoId);
            });
        });

        // VISUALIZAR - continua no Etapa4
        document.querySelectorAll('.btn-visualizar-risco').forEach(btn => {
            btn.addEventListener('click', () => {
                const riscoId = parseInt(btn.dataset.riscoId);
                this.visualizarRisco(riscoId);
            })
        })
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
};