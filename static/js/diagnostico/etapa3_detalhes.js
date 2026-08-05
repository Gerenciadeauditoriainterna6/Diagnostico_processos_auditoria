// ============================================================
// etapa3_detalhes.js - ETAPA 3: Detalhamento dos Processos
// 
// Lógica:
// 1. Mostrar lista de processos cadastrados na etapa 2
// 2. Usuário escolhe UM para detalhar
// 3. Mostrar formulário com os campos de detalhamento
// 4. Salvar detalhes no banco
// 5. Voltar para lista para detalhar outro
// ============================================================

const Etapa3Module = {
    
    // Estado
    processosPendentes: [],       // Processos carregados do banco
    processoSelecionadoId: null,  // ID do processo sendo detalhado agora
    
    // Elementos do DOM
    listaContainer: null,
    formDetalhamento: null,
    listaProcessos: null,
    processoInfo: null,
    btnVoltarLista: null,
    btnVoltarForm: null,
    btnSalvarDetalhes: null,
    btnProximoLista: null,
    
    // Campos do formulário
    descricaoInput: null,
    etapaIniInput: null,
    produtoInput: null,
    etapaFimInput: null,
    objetivoInput: null,
    
    // ============================================================
    // INIT
    // ============================================================
    init() {
        console.log('📌 Etapa3Module: inicializando...');
        
        // Containers
        this.listaContainer = document.getElementById('etapa3-lista-processos');
        this.formDetalhamento = document.getElementById('etapa3-form-detalhamento');
        this.listaProcessos = document.getElementById('etapa3-lista-container');
        this.processoInfo = document.getElementById('etapa3-processo-selecionado-info');
        
        // Botões
        this.btnVoltarLista = document.getElementById('btn-voltar-etapa2-lista');
        this.btnVoltarForm = document.getElementById('btn-voltar-etapa2-form');
        this.btnSalvarDetalhes = document.getElementById('btn-salvar-detalhes');
        this.btnProximoLista = document.getElementById('btn-proximo-etapa4-lista');
        
        // Campos
        this.descricaoInput = document.getElementById('descricao_processo');
        this.etapaIniInput = document.getElementById('etapa_ini_processo');
        this.produtoInput = document.getElementById('produto_processo');
        this.etapaFimInput = document.getElementById('etapa_fim_processo');
        this.objetivoInput = document.getElementById('objetivo_processo');
        
        this.configurarEventos();
        console.log('✅ Etapa3Module: inicializado');
    },
    
    // ============================================================
    // CONFIGURAR EVENTOS
    // ============================================================
    configurarEventos() {
        // Voltar para etapa 2 (da lista)
        if (this.btnVoltarLista) {
            this.btnVoltarLista.addEventListener('click', () => {
                if (typeof WizardModule !== 'undefined') WizardModule.irParaEtapa(2);
            });
        }
        
        // Voltar para lista (do formulário)
        if (this.btnVoltarForm) {
            this.btnVoltarForm.addEventListener('click', () => {
                this.mostrarLista();
            });
        }
        
        // Salvar detalhes
        if (this.btnSalvarDetalhes) {
            this.btnSalvarDetalhes.addEventListener('click', () => {
                this.salvarDetalhes();
            });
        }

        if (this.btnProximoLista) {
            this.btnProximoLista.addEventListener('click', () => {
                if (typeof WizardModule !== 'undefined') WizardModule.irParaEtapa(4);
            });
        }
    },
    
    // ============================================================
    // AO ENTRAR NA ETAPA
    // ============================================================
    async aoEntrar() {
        console.log('👋 Etapa 3 ativada');
        await this.carregarProcessos();
        this.mostrarLista();
    },
    
    // ============================================================
    // CARREGAR PROCESSOS DA ÁREA/AUDITORIA
    // ============================================================
    async carregarProcessos() {
        const areaId = document.getElementById('id_area_selecionado')?.value || 
                    document.getElementById('area_select')?.value;
        const auditoriaId = document.getElementById('auditoria_select')?.value;
        
        // ⭐ PEGAR IDs SALVOS NA ETAPA 2
        const idsSalvos = JSON.parse(sessionStorage.getItem('processos_salvos_ids') || '[]');
        
        if (!areaId || !auditoriaId || idsSalvos.length === 0) {
            this.listaProcessos.innerHTML = '<p class="etapa3-lista-vazia">Nenhum processo para detalhar.</p>';
            return;
        }
        
        this.listaProcessos.innerHTML = `
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
            // ⭐ FILTRAR APENAS PELOS IDs
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
    
    // ============================================================
    // RENDERIZAR LISTA DE PROCESSOS
    // ============================================================
    renderizarLista() {
        if (this.processosPendentes.length === 0) {
            this.listaProcessos.innerHTML = '<p class="etapa3-lista-vazia">Nenhum processo encontrado.</p>';
            return;
        }
        
        this.listaProcessos.innerHTML = this.processosPendentes.map(proc => {
            const detalhado = proc.descricao && proc.descricao.trim() !== '';
            
            return `
                <div class="processo-item-lista">
                    <div>
                        <strong class="processo-codigo">${proc.codigo_processo}</strong>
                        <span class="processo-nome">${proc.nome_processo}</span>
                        <br>
                        <small class="processo-status ${detalhado ? 'status-detalhado' : 'status-pendente'}">
                            <i class="fas fa-${detalhado ? 'check-circle' : 'clock'}"></i>
                            ${detalhado ? 'Detalhado' : 'Pendente'}
                        </small>
                    </div>
                    <button class="btn-detalhar-processo btn-outline btn-sm" data-processo-id="${proc.id}">
                        <i class="fas fa-${detalhado ? 'edit' : 'plus'}"></i>
                        ${detalhado ? 'Editar' : 'Detalhar'}
                    </button>
                </div>
            `;
        }).join('');
        
        this.listaProcessos.querySelectorAll('.btn-detalhar-processo').forEach(btn => {
            btn.addEventListener('click', () => {
                const processoId = parseInt(btn.dataset.processoId);
                this.abrirFormulario(processoId);
            });
        });
    },
    
    // ============================================================
    // MOSTRAR LISTA
    // ============================================================
    mostrarLista() {
        this.listaContainer.style.display = 'block';
        this.formDetalhamento.style.display = 'none';
        this.processoSelecionadoId = null;
        this.carregarProcessos();
    },
    
    // ============================================================
    // ABRIR FORMULÁRIO DE DETALHAMENTO
    // ============================================================
    abrirFormulario(processoId) {
        const proc = this.processosPendentes.find(p => p.id === processoId);
        if (!proc) return;
        
        this.processoSelecionadoId = processoId;
        
        // Mostrar info do processo
        this.processoInfo.innerHTML = `
            <strong><i class="fas fa-tag"></i> ${proc.codigo_processo} - ${proc.nome_processo}</strong>
        `;
        
        // Preencher campos (se já existirem)
        this.descricaoInput.value = proc.descricao || '';
        this.etapaIniInput.value = proc.etapa_ini || '';
        this.produtoInput.value = proc.produto || '';
        this.etapaFimInput.value = proc.etapa_fim || '';
        this.objetivoInput.value = proc.objetivo || '';
        
        // Trocar visão
        this.listaContainer.style.display = 'none';
        this.formDetalhamento.style.display = 'block';
    },
    
    // ============================================================
    // SALVAR DETALHES
    // ============================================================
    async salvarDetalhes() {
        if (!this.processoSelecionadoId) return;
        
        const dados = {
            processo_id: this.processoSelecionadoId,
            descricao: this.descricaoInput.value.trim(),
            etapa_ini: this.etapaIniInput.value.trim(),
            produto: this.produtoInput.value.trim(),
            etapa_fim: this.etapaFimInput.value.trim(),
            objetivo: this.objetivoInput.value.trim()
        };
        
        try {
            const response = await window.fetchComAutenticacao('/api/processo/salvar-detalhes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.mostrarToast('✅ Detalhes salvos com sucesso!', 'success');
                this.mostrarLista(); // Volta para a lista
            } else {
                window.mostrarToast('❌ Erro ao salvar', 'error');
            }
        } catch (error) {
            console.error('Erro ao salvar detalhes:', error);
        }
    }
    
};