// ============================================================
// etapa2_basicas.js - ETAPA 2: Processos e Funcionários
// 
// Lógica:
// 1. Usuário adiciona PROCESSOS (nome + código automático)
// 2. Para CADA processo, seleciona quais funcionários executam
// 3. Um funcionário pode estar em vários processos
// 4. Ao avançar, salva tudo no banco
// ============================================================

const Etapa2Module = {
    
    // Lista de processos: [{ nome, codigo, tempId, funcionarios: [{id, nome}] }]
    processos: [],
    
    // Lista de funcionários disponíveis (carregados da API)
    funcionariosDisponiveis: [],
    
    // Controle de sequencial
    proximoSequencial: 1,
    
    // Elementos do DOM
    entrevistadoInput: null,
    processosContainer: null,
    btnProximo: null,
    btnVoltar: null,
    btnAdicionarProcesso: null,
    funcionariosComProcessos: {},
    
    // Debounce
    timeoutGerarCodigo: null,
    
    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================
    init() {
        console.log('📌 Etapa2Module: inicializando...');
        
        this.entrevistadoInput = document.getElementById('entrevistado_processo');
        this.processosContainer = document.getElementById('processos-executores-lista');
        this.btnProximo = document.getElementById('btn-proximo-etapa3');
        this.btnVoltar = document.getElementById('btn-voltar-etapa1');
        this.btnAdicionarProcesso = document.getElementById('btn-adicionar-processo');
        
        this.configurarEventos();
        console.log('✅ Etapa2Module: inicializado');
    },
    
    // ============================================================
    // CONFIGURAR EVENTOS
    // ============================================================
    configurarEventos() {
        if (this.btnVoltar) {
            this.btnVoltar.addEventListener('click', () => {
                if (typeof WizardModule !== 'undefined') WizardModule.irParaEtapa(1);
            });
        }
        
        if (this.btnProximo) {
            this.btnProximo.addEventListener('click', () => this.avancar());
        }

        if (this.btnAdicionarProcesso) {
            this.btnAdicionarProcesso.addEventListener('click', () => this.adicionarProcesso());
        }
    },

    async carregarDadosEdicao() {
        const processoId = WizardModule.getProcessoId();
        
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/dados`);
            const data = await response.json();
            
            if (data.success) {
                this.entrevistadoInput.value = data.entrevistado || '';
                
                // ⭐ Preencher this.processos (array) para a renderização funcionar
                this.processos = [{
                    nome: data.nome_processo || '',
                    codigo: data.codigo_processo || '',
                    tempId: Date.now(),
                    existente: true,
                    funcionarios: data.executores.map(exec => ({
                        id: exec.id || exec.funcionario_id,
                        nome: exec.nome
                    }))
                }];
                
                this.carregarFuncionarios();
            }
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
        }
    },
    
    // ============================================================
    // AO ENTRAR NA ETAPA
    // ============================================================
    async aoEntrar() {
        console.log('👋 Etapa 2 ativada');
        
        // ⭐ Usar spinnerHTML do utils.js
        const loadingContainer = document.getElementById('etapa2-loading');
        const conteudo = document.getElementById('etapa2-conteudo');
        
        if (loadingContainer && conteudo) {
            // Mostrar spinner
            loadingContainer.innerHTML = spinnerHTML('Carregando informações...');
            loadingContainer.style.display = 'block';
            conteudo.style.display = 'none';
        }
        
        try {
            // Sua lógica de carregamento
            if (WizardModule.isEdicao()) {
                await this.carregarDadosEdicao();
            } else {
                this.resetar();
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar etapa 2:', error);
            window.mostrarToast('Erro ao carregar dados', 'error');
            
        } finally {
            // Esconder spinner
            if (loadingContainer && conteudo) {
                loadingContainer.style.display = 'none';
                loadingContainer.innerHTML = '';
                conteudo.style.display = 'block';
            }
        }
    },
    
    // ============================================================
    // BUSCAR ÚLTIMO SEQUENCIAL
    // ============================================================
    async buscarUltimoSequencial() {
        const areaId = this.getAreaId();
        if (!areaId) return;
        
        try {
            const response = await window.fetchComAutenticacao(
                `/api/processo/ultimo-sequencial?id_area=${areaId}`
            );
            const data = await response.json();
            this.proximoSequencial = (data.ultimo_sequencial || 0) + 1;
        } catch (error) {
            console.error('Erro ao buscar sequencial:', error);
        }
    },
    
    // ============================================================
    // CARREGAR FUNCIONÁRIOS
    // ============================================================
    async carregarFuncionarios() {
        const areaId = this.getAreaId();
        if (!areaId) return;
        
        try {
            const response = await window.fetchComAutenticacao(
                `/api/area/${areaId}/funcionarios-para-select`
            );
            const data = await response.json();
            
            if (data.funcionarios) {
                this.funcionariosDisponiveis = data.funcionarios;
            }
        } catch (error) {
            console.error('Erro ao carregar funcionários:', error);
        }
    },
    
    // ============================================================
    // ADICIONAR PROCESSO
    // ============================================================
    adicionarProcesso() {
        this.processos.push({
            nome: '',
            codigo: '',
            tempId: Date.now(),
            existente: false,
            funcionarios: []
        });
        this.renderizarTudo();
    },
    
    // ============================================================
    // REMOVER PROCESSO
    // ============================================================
    removerProcesso(tempId) {
        this.processos = this.processos.filter(p => p.tempId !== tempId);
        this.renderizarTudo();
    },
    
    // ============================================================
    // ATUALIZAR NOME DO PROCESSO (com debounce)
    // ============================================================
    atualizarNomeProcesso(tempId, nome) {
        const proc = this.processos.find(p => p.tempId === tempId);
        if (!proc) return;
        
        // Guarda o nome E código anterior
        if (proc.nome && proc.nome.trim().length >= 3 && proc.codigo && 
            proc.nome.trim().toUpperCase() !== nome.trim().toUpperCase()) {
            if (!proc._historico) proc._historico = {};
            proc._historico[proc.nome.trim().toUpperCase()] = proc.codigo;
        }
        
        proc.nome = nome;
        
        if (nome.trim().length < 3) {
            proc.codigo = '';
            proc.existente = false;
            const codigoInput = document.querySelector(`.processo-codigo-input[data-temp-id="${tempId}"]`);
            if (codigoInput) codigoInput.value = '';
            this.verificarHabilitarProximo();
            return;
        }
        
        const nomeUpper = nome.trim().toUpperCase();
        if (proc._historico && proc._historico[nomeUpper]) {
            proc.codigo = proc._historico[nomeUpper];
            proc.existente = false;
            // ✅ Atualiza SÓ o input de código (sem perder foco)
            const codigoInput = document.querySelector(`.processo-codigo-input[data-temp-id="${tempId}"]`);
            if (codigoInput) codigoInput.value = proc.codigo;
            this.verificarHabilitarProximo();
            return;
        }
        
        if (this.timeoutGerarCodigo) clearTimeout(this.timeoutGerarCodigo);
        
        this.timeoutGerarCodigo = setTimeout(async () => {
            // Guarda qual input está com foco
            const focusedInput = document.activeElement;
            const cursorPosition = focusedInput ? focusedInput.selectionStart : 0;
            
            await this.gerarCodigoProcesso(proc);
            
            // ✅ Renderiza mantendo o foco
            this.renderizarTudo();
            
            // Restaura o foco
            setTimeout(() => {
                const input = document.querySelector(`.processo-nome-input[data-temp-id="${tempId}"]`);
                if (input) {
                    input.focus();
                    input.setSelectionRange(cursorPosition, cursorPosition);
                }
            }, 0);
            
            this.verificarHabilitarProximo();
        }, 500);
    },
    
    // ============================================================
    // GERAR CÓDIGO DO PROCESSO
    // ============================================================
    async gerarCodigoProcesso(proc) {
        if (WizardModule.isEdicao()) {
            return;
        }
        
        const areaId = this.getAreaId();
        const nomeUpper = proc.nome.trim().toUpperCase();
        
        if (!areaId || !nomeUpper) return;
        
        // ===== PRIMEIRO: Verifica se o nome já existe em OUTRO processo DESTA etapa =====
        const duplicadoNaEtapa = this.processos.find(p => 
            p.tempId !== proc.tempId && 
            p.nome.trim().toUpperCase() === nomeUpper
        );
        
        if (duplicadoNaEtapa && duplicadoNaEtapa.codigo) {
            // Usa o mesmo código do processo duplicado
            proc.codigo = duplicadoNaEtapa.codigo;
            proc.existente = duplicadoNaEtapa.existente;
            
            if (typeof window !== 'undefined' && window.mostrarToast) {
                window.mostrarToast(`⚠️ Este processo já foi adicionado nesta etapa (código: ${duplicadoNaEtapa.codigo})`, 'warning');
            }
            return;
        }
        
        // ===== SEGUNDO: Verifica se o nome já existia antes (em outro campo que foi alterado) =====
        const nomeAnterior = this.processos.find(p => 
            p.tempId !== proc.tempId && 
            p._nomesAnteriores && 
            p._nomesAnteriores.includes(nomeUpper)
        );
        
        if (nomeAnterior && nomeAnterior.codigo) {
            proc.codigo = nomeAnterior.codigo;
            proc.existente = nomeAnterior.existente;
            return;
        }
        
        // ===== TERCEIRO: Verifica no banco =====
        try {
            const response = await window.fetchComAutenticacao(
                `/api/processo/verificar?nome=${encodeURIComponent(nomeUpper)}&id_area=${areaId}`
            );
            const data = await response.json();
            
            if (data.existe) {
                proc.codigo = data.codigo;
                proc.existente = true;
            } else {
                // Gera novo código sequencial
                const outrosComCodigo = this.processos.filter(p => 
                    p.tempId !== proc.tempId && 
                    !p.existente && 
                    p.codigo !== '' &&
                    p.nome.trim().toUpperCase() !== nomeUpper  // Não conta nomes iguais
                ).length;
                
                proc.codigo = `${areaId}.${this.proximoSequencial + outrosComCodigo}`;
                proc.existente = false;
            }
        } catch (error) {
            console.error('Erro ao gerar código:', error);
        }
    },
    
    // ============================================================
    // TOGGLE FUNCIONÁRIO NO PROCESSO
    // ============================================================
    toggleFuncionario(tempId, funcId, funcNome) {
        const proc = this.processos.find(p => p.tempId === tempId);
        if (!proc) return;
        
        const index = proc.funcionarios.findIndex(f => f.id === funcId);
        
        if (index >= 0) {
            // Remove
            proc.funcionarios.splice(index, 1);
        } else {
            // Adiciona
            proc.funcionarios.push({ id: funcId, nome: funcNome });
        }
        
        this.renderizarTudo();
    },
    
    // ============================================================
    // RENDERIZAR TUDO
    // ============================================================
    renderizarTudo() {
        const outerContainer = document.getElementById('processos-executores-container');
        
        if (this.processos.length === 0) {
            outerContainer.style.display = 'none';
            this.processosContainer.innerHTML = '';
        } else {
            outerContainer.style.display = 'block';
            this.processosContainer.innerHTML = this.processos.map(proc => 
                this.renderizarProcesso(proc)
            ).join('');
        }
        
        this.configurarEventosProcessos();
        this.verificarHabilitarProximo();
    },
    
    // ============================================================
    // RENDERIZAR UM PROCESSO
    // ============================================================
    renderizarProcesso(proc) {
        const temFuncionarios = proc.funcionarios.length > 0;
        
        return `
            <div class="processo-card" style="border:1px solid #e0e0e0; border-radius:10px; padding:15px; margin-bottom:15px; background:white;">
                
                <!-- Nome e Código -->
                <div style="display:flex; gap:10px; align-items:flex-end; margin-bottom:15px;">
                    <div style="flex:1;">
                        <label style="font-size:12px; color:#666;">Nome do Processo</label>
                        <input type="text" 
                            class="processo-nome-input" 
                            placeholder="Digite o nome do processo..."
                            data-temp-id="${proc.tempId}"
                            value="${proc.nome}"
                            style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px;">
                    </div>
                    <div style="width:120px;">
                        <label style="font-size:12px; color:#666;">Código</label>
                        <input type="text" 
                            class="processo-codigo-input"
                            data-temp-id="${proc.tempId}"
                            value="${proc.codigo}" 
                            readonly
                            style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px; background:#f0f0f0; font-weight:bold; text-align:center;">
                    </div>
                    <button class="btn-remover-processo" data-temp-id="${proc.tempId}"
                        style="background:none; border:none; color:#dc3545; cursor:pointer; font-size:18px; padding:8px;">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
                
                ${proc.existente ? '<small style="color:#856404;">⚠️ Editando o Processo</small>' : ''}
                
                <!-- Funcionários -->
                <div>
                    <label style="font-size:12px; color:#666; display:block; margin-bottom:8px;">
                        <i class="fas fa-users"></i> Funcionários que executam este processo
                        ${temFuncionarios ? `<span style="color:#28a745;">(${proc.funcionarios.length} selecionados)</span>` : ''}
                    </label>
                    <div style="display:flex; flex-wrap:wrap; gap:8px;">
                        ${this.funcionariosDisponiveis.map(func => {
                            const selecionado = proc.funcionarios.some(f => f.id === func.id);
                            return `
                                <button class="btn-funcionario-toggle ${selecionado ? 'btn-funcionario-selecionado' : ''}"
                                    data-temp-id="${proc.tempId}"
                                    data-func-id="${func.id}"
                                    data-func-nome="${func.nome}">
                                    ${selecionado ? '✓' : '+'} ${func.nome}
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            </div>
        `;
    },
    
    // ============================================================
    // CONFIGURAR EVENTOS DOS PROCESSOS RENDERIZADOS
    // ============================================================
    configurarEventosProcessos() {
        // Input de nome do processo
        document.querySelectorAll('.processo-nome-input').forEach(input => {
            // Remove evento antigo para não duplicar
            input.removeEventListener('input', input._inputHandler);
            input._inputHandler = () => {
                const tempId = parseInt(input.dataset.tempId);
                this.atualizarNomeProcesso(tempId, input.value);
            };
            input.addEventListener('input', input._inputHandler);
        });
        
        // Botão remover processo
        document.querySelectorAll('.btn-remover-processo').forEach(btn => {
            btn.addEventListener('click', () => {
                const tempId = parseInt(btn.dataset.tempId);
                this.removerProcesso(tempId);
            });
        });
        
        // Botão toggle funcionário
        document.querySelectorAll('.btn-funcionario-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const tempId = parseInt(btn.dataset.tempId);
                const funcId = parseInt(btn.dataset.funcId);
                const funcNome = btn.dataset.funcNome;
                this.toggleFuncionario(tempId, funcId, funcNome);
            });
        });
    },
    
    // ============================================================
    // VERIFICAR HABILITAR PRÓXIMO
    // ============================================================
    verificarHabilitarProximo() {
        if (!this.btnProximo) return;
        
        if (this.processos.length === 0) {
            this.btnProximo.disabled = true;
            return;
        }
        
        // Todos os processos precisam ter nome e código
        const todosOk = this.processos.every(proc => {
            return proc.nome.trim() !== '' && proc.codigo !== '';
        });
        
        this.btnProximo.disabled = !todosOk;
    },
    
    // ============================================================
    // AVANÇAR
    // ============================================================
    async avancar() {
        const salvou = await this.salvarProcessos();
        if (salvou) {
            if (typeof WizardModule !== 'undefined') WizardModule.irParaEtapa(3);
        }
    },
    
    // ============================================================
    // SALVAR PROCESSOS
    // ============================================================
    async salvarProcessos() {
        const areaId = this.getAreaId();
        const auditoriaId = this.getAuditoriaId();
        const entrevistado = this.entrevistadoInput?.value?.trim() || '';
        
        if (!entrevistado) {
            window.mostrarToast('Informe o nome do entrevistado!', 'warning');
            return false;
        }
        
        const processosParaSalvar = [];
        
        const processoId = WizardModule.isEdicao() ? WizardModule.getProcessoId() : null;

        this.processos.forEach(proc => {
            if (!proc.nome.trim()) return;  // Pula se estiver vazio
            
            if (WizardModule.isEdicao()) {
                // ⭐ EDIÇÃO: sempre envia com o ID
                processosParaSalvar.push({
                    id: processoId,
                    nome: proc.nome.trim().toUpperCase(),
                    codigo: proc.codigo,
                    funcionarios_ids: proc.funcionarios.map(f => f.id),
                    entrevistado: entrevistado,
                    area_id: areaId,
                    auditoria_id: auditoriaId
                });
            } else {
                // ⭐ NOVO: só se não existir
                if (!proc.existente) {
                    processosParaSalvar.push({
                        nome: proc.nome.trim().toUpperCase(),
                        codigo: proc.codigo,
                        funcionarios_ids: proc.funcionarios.map(f => f.id),
                        entrevistado: entrevistado,
                        area_id: areaId,
                        auditoria_id: auditoriaId
                    });
                }
            }
        });
        
        if (processosParaSalvar.length === 0) {
            window.mostrarToast('Nenhum processo novo para salvar', 'info');
            return true;
        }
        
        try {
            const response = await window.fetchComAutenticacao('/api/processo/salvar-basicos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ processos: processosParaSalvar })
            });
            
            const data = await response.json();
            
            if (data.success) {
                sessionStorage.setItem('processos_salvos_ids', JSON.stringify(data.ids));
                
                window.mostrarToast(`${data.quantidade} processo(s) salvos!`, 'success');
                return true;
            }
        } catch (error) {
            console.error('Erro ao salvar:', error);
        }
        
        return false;
    },
    
    // ============================================================
    // GETTERS
    // ============================================================
    getAreaId() {
        return document.getElementById('id_area_selecionado')?.value || 
               document.getElementById('area_select')?.value;
    },
    
    getAuditoriaId() {
        return document.getElementById('auditoria_select')?.value;
    }
    
};