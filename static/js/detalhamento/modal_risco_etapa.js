// ============================================================
// modal_risco_etapa.js - MÓDULO DO MODAL DE RISCO DA ETAPA
// ============================================================

// ⭐ PROTEGER CONTRA CONFLITOS
(function() {
    if (typeof RiscoModalModule !== 'undefined') {
        console.warn('⚠️ RiscoModalModule detectado! Neutralizando...');
        RiscoModalModule.init = function() {
            console.log('⏭️ RiscoModalModule.init() BLOQUEADO');
        };
    }
})();

const ModalRiscoEtapaModule = {
    
    etapaIdAtual: null,
    auditoriaIdAtual: null,
    codigoEtapaAtual: null,
    nomeEtapaAtual: null,
    riscoIdEditando: null,
    categoriasPersonalizadasRisco: [],
    categoriasPersonalizadasCausa: [],
    
    init() {
        console.log('📌 ModalRiscoEtapaModule: inicializado');
        setTimeout(() => {
            this._vincularEventos();
        }, 200);
    },

    _vincularEventos() {
        console.log('🔗 Vinculando eventos do modal de etapa...');
        
        const btnFechar = document.getElementById('btn-fechar-modal-risco');
        const btnCancelar = document.getElementById('btn-cancelar-modal-risco');
        const btnSalvar = document.getElementById('btn-salvar-modal-risco');
        
        if (btnFechar) btnFechar.addEventListener('click', () => this.fechar());
        if (btnCancelar) btnCancelar.addEventListener('click', () => this.fechar());
        if (btnSalvar) {
            btnSalvar.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.salvar();
            });
            console.log('✅ Botão Salvar vinculado!');
        } else {
            console.error('❌ Botão Salvar não encontrado!');
        }
        
        document.getElementById('risco_impacto')?.addEventListener('change', () => this.atualizarScoreRisco());
        document.getElementById('risco_probabilidade')?.addEventListener('change', () => this.atualizarScoreRisco());

        
        document.getElementById('check-outra-categoria-risco')?.addEventListener('change', function() {
            const container = document.getElementById('outra-categoria-risco-container');
            if (container) container.style.display = this.checked ? 'block' : 'none';
        });
        
        document.getElementById('btn-adicionar-outra-risco')?.addEventListener('click', () => {
            this.adicionarCategoriaPersonalizada('risco');
        });
        
        document.getElementById('outra-categoria-risco-texto')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.adicionarCategoriaPersonalizada('risco');
            }
        });
        
        document.getElementById('check-outra-categoria-causa')?.addEventListener('change', function() {
            const container = document.getElementById('outra-categoria-causa-container');
            if (container) container.style.display = this.checked ? 'block' : 'none';
        });
        
        document.getElementById('btn-adicionar-outra-causa')?.addEventListener('click', () => {
            this.adicionarCategoriaPersonalizada('causa');
        });
        
        document.getElementById('outra-categoria-causa-texto')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.adicionarCategoriaPersonalizada('causa');
            }
        });
        
        console.log('✅ Todos os eventos vinculados!');
    },

    async salvar() {
        console.log('💾 Salvando risco da etapa...');
        
        const dados = {
            etapa_id: this.etapaIdAtual,
            auditoria_id: this.auditoriaIdAtual,
            nome_risco: document.getElementById('risco_nome')?.value || '',
            fator_risco: document.getElementById('risco_fator')?.value || '',
            consequencia: document.getElementById('risco_consequencia')?.value || '',
            info_adicional: document.getElementById('risco_info_adicional')?.value || '',
            origem: document.getElementById('risco_origem')?.value || '',
            financeiro: document.getElementById('risco_financeiro')?.value === 'true',
            ativo: document.querySelector('input[name="risco_ativo"]:checked')?.value === 'true',
            impacto: document.getElementById('risco_impacto')?.value || '',
            probabilidade: document.getElementById('risco_probabilidade')?.value || '',
            motivo_classificacao: document.getElementById('risco_motivo')?.value || '',
        };
        
        const categoriasSelecionadas = [];
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]:checked').forEach(cb => {
            if (cb.value !== 'OUTRA') categoriasSelecionadas.push(cb.value);
        });
        categoriasSelecionadas.push(...this.categoriasPersonalizadasRisco);
        dados.categoria = categoriasSelecionadas.join(', ');
        
        const causasSelecionadas = [];
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]:checked').forEach(cb => {
            if (cb.value !== 'OUTRA') causasSelecionadas.push(cb.value);
        });
        causasSelecionadas.push(...this.categoriasPersonalizadasCausa);
        dados.causas = causasSelecionadas;
        
        console.log('📤 Dados:', dados);
        
        if (!dados.nome_risco) {
            window.mostrarToast('⚠️ Nome do risco é obrigatório', 'warning');
            return;
        }
        if (!dados.impacto || !dados.probabilidade) {
            window.mostrarToast('⚠️ Impacto e Probabilidade são obrigatórios', 'warning');
            return;
        }
        
        try {
            const url = this.riscoIdEditando 
                ? `/api/risco-etapa/${this.riscoIdEditando}` 
                : '/api/risco-etapa';
            const method = this.riscoIdEditando ? 'PUT' : 'POST';
            
            console.log(`📡 ${method} ${url}`);
            
            const response = await window.fetchComAutenticacao(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            });
            
            const resultado = await response.json();
            console.log('📥 Resposta:', resultado);
            
            if (resultado.success) {
                window.mostrarToast('✅ Risco salvo com sucesso!', 'success');
                this.fechar();
                await EtapasRiscosModule.carregarRiscosDaEtapa(this.etapaIdAtual, this.codigoEtapaAtual, this.nomeEtapaAtual);
                await EtapasRiscosModule.atualizarBadgeRiscos(this.etapaIdAtual);
            } else {
                window.mostrarToast('❌ ' + (resultado.error || 'Erro ao salvar'), 'error');
            }
        } catch (error) {
            console.error('❌ Erro:', error);
            window.mostrarToast('❌ Erro de conexão', 'error');
        }
    },
    
    // ⭐ NOVO: Função para adicionar categoria personalizada
    adicionarCategoriaPersonalizada(tipo) {
        const inputId = tipo === 'risco' ? 'outra-categoria-risco-texto' : 'outra-categoria-causa-texto';
        const listaId = tipo === 'risco' ? 'outras-categorias-risco-lista' : 'outras-categorias-causa-lista';
        const arrayRef = tipo === 'risco' ? 'categoriasPersonalizadasRisco' : 'categoriasPersonalizadasCausa';
        
        const input = document.getElementById(inputId);
        const lista = document.getElementById(listaId);
        
        if (!input || !lista) return;
        
        const valor = input.value.trim();
        
        if (!valor) {
            window.mostrarToast('⚠️ Digite um nome para a categoria', 'warning');
            return;
        }
        
        // Verificar se já existe
        if (this[arrayRef].includes(valor)) {
            window.mostrarToast('⚠️ Esta categoria já foi adicionada', 'warning');
            input.value = '';
            return;
        }
        
        // Adicionar ao array
        this[arrayRef].push(valor);
        
        // Criar tag visual
        const tag = document.createElement('span');
        tag.className = 'categoria-tag';
        tag.style.cssText = `
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: #0b5b99;
            color: white;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 12px;
        `;
        tag.innerHTML = `
            ${valor}
            <button type="button" 
                style="background: none; border: none; color: white; cursor: pointer; padding: 0; font-size: 14px;"
                onclick="ModalRiscoEtapaModule.removerCategoriaPersonalizada('${tipo}', '${valor.replace(/'/g, "\\'")}', this)">
                &times;
            </button>
        `;
        
        lista.appendChild(tag);
        
        // Limpar input
        input.value = '';
        input.focus();
    },
    
    // ⭐ NOVO: Função para remover categoria personalizada
    removerCategoriaPersonalizada(tipo, valor, element) {
        const arrayRef = tipo === 'risco' ? 'categoriasPersonalizadasRisco' : 'categoriasPersonalizadasCausa';
        
        // Remover do array
        const index = this[arrayRef].indexOf(valor);
        if (index > -1) {
            this[arrayRef].splice(index, 1);
        }
        
        // Remover elemento visual
        if (element && element.parentElement) {
            element.parentElement.remove();
        }
    },
    
    abrir(etapaId, codigoEtapa, nomeEtapa, auditoriaId) {
        console.log('🔓 Abrindo modal para etapa:', etapaId, codigoEtapa, nomeEtapa);
        
        this.etapaIdAtual = etapaId;
        this.auditoriaIdAtual = auditoriaId;
        this.codigoEtapaAtual = codigoEtapa;
        this.nomeEtapaAtual = nomeEtapa;
        this.riscoIdEditando = null;
        
        // Título do modal
        const tituloElement = document.getElementById('modal-risco-title');
        if (tituloElement) {
            tituloElement.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Novo Risco - ${codigoEtapa} - ${nomeEtapa}`;
        } else {
            console.error('❌ Elemento #modal-risco-title não encontrado!');
        }

        this.limpar();
        this.atualizarScoreRisco();
        
        // ⭐ Carregar objetivo da etapa
        this.carregarObjetivoEtapa(etapaId);

        // Mostrar modal
        const modalElement = document.getElementById('modal-risco-etapa');
        if (modalElement) {
            modalElement.style.display = 'flex';
        } else {
            console.error('❌ Elemento #modal-risco-etapa não encontrado!');
        }
    },

    async carregarObjetivoEtapa(etapaId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}`);
            const data = await response.json();
            if (data.success && data.etapa) {
                const objetivoElement = document.getElementById('modal-objetivo-texto');
                if (objetivoElement) {
                    objetivoElement.textContent = data.etapa.objetivo_etapa || 'Nenhum objetivo cadastrado para esta etapa.';
                }
            }
        } catch (error) {
            console.error('❌ Erro ao carregar objetivo:', error);
            const objetivoElement = document.getElementById('modal-objetivo-texto');
            if (objetivoElement) {
                objetivoElement.textContent = 'Erro ao carregar objetivo da etapa.';
            }
        }
    },
    
    async editar(riscoId, etapaId, codigoEtapa, nomeEtapa, auditoriaId) {
        console.log('✏️ Editando risco:', riscoId);
        
        this.auditoriaIdAtual = auditoriaId
        this.etapaIdAtual = etapaId;
        this.codigoEtapaAtual = codigoEtapa;
        this.nomeEtapaAtual = nomeEtapa;

        this.carregarObjetivoEtapa(etapaId);

        try {
            const response = await window.fetchComAutenticacao(`/api/risco-etapa/${riscoId}`);
            const data = await response.json();
            if (!data.success) { 
                window.mostrarToast('❌ Erro ao carregar risco', 'error'); 
                return; 
            }

            const risco = data.risco;
            this.riscoIdEditando = riscoId;

            // Preencher campos básicos
            this.setValueIfExists('risco_nome', risco.nome_risco || '');
            this.setValueIfExists('risco_fator', risco.fator_risco || '');
            this.setValueIfExists('risco_consequencia', risco.consequencia || '');
            this.setValueIfExists('risco_info_adicional', risco.info_adicional || '');
            this.setValueIfExists('risco_origem', risco.origem || '');
            this.setValueIfExists('risco_financeiro', risco.financeiro ? 'true' : 'false');
            this.setValueIfExists('risco_motivo', risco.motivo_classificacao || '');
            this.setValueIfExists('risco_impacto', (risco.impacto || '').toUpperCase());
            this.setValueIfExists('risco_probabilidade', (risco.probabilidade || '').toUpperCase());
     

            // Status ativo/inativo
            if (risco.ativo !== undefined) {
                const radioAtivo = document.querySelector(`input[name="risco_ativo"][value="${risco.ativo ? 'true' : 'false'}"]`);
                if (radioAtivo) radioAtivo.checked = true;
            }

            // ⭐ Preencher categorias de risco
            const categorias = risco.categoria ? risco.categoria.split(', ').map(c => c.trim()) : [];
            document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => {
                const valor = cb.value;
                // Verificar se é uma categoria padrão
                if (valor !== 'OUTRA') {
                    cb.checked = categorias.some(cat => 
                        cat.toUpperCase() === valor.toUpperCase()
                    );
                }
            });
            
            // ⭐ Verificar se tem categorias personalizadas
            const categoriasPadrao = ['Risco Financeiro', 'Risco Legal', 'Risco Inerente', 'Risco de TI', 
                                       'Risco Reputacional', 'Risco de Integridade', 'Risco Ambiental'];
            const categoriasPersonalizadas = categorias.filter(cat => 
                !categoriasPadrao.some(padrao => cat.toUpperCase() === padrao.toUpperCase())
            );
            
            if (categoriasPersonalizadas.length > 0) {
                // Marcar checkbox "Outra"
                const checkOutra = document.getElementById('check-outra-categoria-risco');
                if (checkOutra) {
                    checkOutra.checked = true;
                    document.getElementById('outra-categoria-risco-container').style.display = 'block';
                }
                
                // Adicionar tags personalizadas
                this.categoriasPersonalizadasRisco = [];
                const lista = document.getElementById('outras-categorias-risco-lista');
                if (lista) {
                    lista.innerHTML = '';
                    categoriasPersonalizadas.forEach(cat => {
                        this.categoriasPersonalizadasRisco.push(cat);
                        const tag = document.createElement('span');
                        tag.className = 'categoria-tag';
                        tag.style.cssText = `
                            display: inline-flex;
                            align-items: center;
                            gap: 5px;
                            background: #0b5b99;
                            color: white;
                            padding: 4px 10px;
                            border-radius: 15px;
                            font-size: 12px;
                        `;
                        tag.innerHTML = `
                            ${cat}
                            <button type="button" 
                                style="background: none; border: none; color: white; cursor: pointer; padding: 0; font-size: 14px;"
                                onclick="ModalRiscoEtapaModule.removerCategoriaPersonalizada('risco', '${cat.replace(/'/g, "\\'")}', this)">
                                &times;
                            </button>
                        `;
                        lista.appendChild(tag);
                    });
                }
            }

            // ⭐ Preencher categorias de causa
            const causas = risco.causas || [];
            document.querySelectorAll('#causa-checkboxes input[type="checkbox"]').forEach(cb => {
                const valor = cb.value;
                if (valor !== 'OUTRA') {
                    cb.checked = causas.some(causa => 
                        causa.toUpperCase() === valor.toUpperCase()
                    );
                }
            });
            
            // ⭐ Verificar se tem causas personalizadas
            const causasPadrao = ['FALHA OPERACIONAL', 'FALTA DE CONTROLE', 'NÃO CONFORMIDADE', 
                                  'PROBLEMAS FINANCEIROS', 'FENÔMENO NATURAL', 'FRAUDE'];
            const causasPersonalizadas = causas.filter(causa => 
                !causasPadrao.some(padrao => causa.toUpperCase() === padrao.toUpperCase())
            );
            
            if (causasPersonalizadas.length > 0) {
                const checkOutraCausa = document.getElementById('check-outra-categoria-causa');
                if (checkOutraCausa) {
                    checkOutraCausa.checked = true;
                    document.getElementById('outra-categoria-causa-container').style.display = 'block';
                }
                
                this.categoriasPersonalizadasCausa = [];
                const listaCausa = document.getElementById('outras-categorias-causa-lista');
                if (listaCausa) {
                    listaCausa.innerHTML = '';
                    causasPersonalizadas.forEach(causa => {
                        this.categoriasPersonalizadasCausa.push(causa);
                        const tag = document.createElement('span');
                        tag.className = 'categoria-tag';
                        tag.style.cssText = `
                            display: inline-flex;
                            align-items: center;
                            gap: 5px;
                            background: #17a2b8;
                            color: white;
                            padding: 4px 10px;
                            border-radius: 15px;
                            font-size: 12px;
                        `;
                        tag.innerHTML = `
                            ${causa}
                            <button type="button" 
                                style="background: none; border: none; color: white; cursor: pointer; padding: 0; font-size: 14px;"
                                onclick="ModalRiscoEtapaModule.removerCategoriaPersonalizada('causa', '${causa.replace(/'/g, "\\'")}', this)">
                                &times;
                            </button>
                        `;
                        listaCausa.appendChild(tag);
                    });
                }
            }

            this.atualizarScoreRisco();

            // Título
            const tituloElement = document.getElementById('modal-risco-title');
            if (tituloElement) {
                tituloElement.innerHTML = `<i class="fas fa-edit"></i> Editar Risco - ${codigoEtapa} - ${nomeEtapa}`;
            }

            // Mostrar modal
            const modalElement = document.getElementById('modal-risco-etapa');
            if (modalElement) {
                modalElement.style.display = 'flex';
            }

        } catch (error) {
            console.error('❌ Erro ao carregar risco:', error);
            window.mostrarToast('❌ Erro ao carregar', 'error');
        }
    },
    
    // Função auxiliar para setar valores com segurança
    setValueIfExists(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.value = value;
        } else {
            console.warn(`⚠️ Elemento #${elementId} não encontrado no DOM`);
        }
    },
    
    async excluir(riscoId, nomeRisco, etapaId, codigoEtapa, nomeEtapa) {
        if (!confirm(`Excluir o risco "${nomeRisco}"?`)) return;
        try {
            const response = await window.fetchComAutenticacao(`/api/risco-etapa/${riscoId}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                window.mostrarToast('✅ Risco excluído!', 'success');
                await EtapasRiscosModule.carregarRiscosDaEtapa(etapaId, codigoEtapa, nomeEtapa);
                await EtapasRiscosModule.atualizarBadgeRiscos(etapaId);
            }
        } catch (error) {
            window.mostrarToast('❌ Erro', 'error');
        }
    },
    
    fechar() {
        const modalElement = document.getElementById('modal-risco-etapa');
        if (modalElement) {
            modalElement.style.display = 'none';
        }
    },

    limpar() {
        // Limpar campos com IDs do modal_risco_etapa.html
        this.setValueIfExists('risco_nome', '');
        this.setValueIfExists('risco_fator', '');
        this.setValueIfExists('risco_consequencia', '');
        this.setValueIfExists('risco_info_adicional', '');
        this.setValueIfExists('risco_origem', '');
        this.setValueIfExists('risco_financeiro', 'false');

        this.setValueIfExists('risco_motivo', '');

        this.setValueIfExists('risco_impacto', '');
        this.setValueIfExists('risco_probabilidade', '');

        
        // Resetar radio button para "Ativo"
        const radioAtivo = document.querySelector('input[name="risco_ativo"][value="true"]');
        if (radioAtivo) radioAtivo.checked = true;
        
        // Limpar checkboxes
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
        
        // ⭐ Limpar categorias personalizadas
        this.categoriasPersonalizadasRisco = [];
        this.categoriasPersonalizadasCausa = [];
        
        // ⭐ Limpar listas visuais
        const listaRisco = document.getElementById('outras-categorias-risco-lista');
        if (listaRisco) listaRisco.innerHTML = '';
        
        const listaCausa = document.getElementById('outras-categorias-causa-lista');
        if (listaCausa) listaCausa.innerHTML = '';
        
        // ⭐ Esconder containers de categorias personalizadas
        const containerRisco = document.getElementById('outra-categoria-risco-container');
        if (containerRisco) containerRisco.style.display = 'none';
        
        const containerCausa = document.getElementById('outra-categoria-causa-container');
        if (containerCausa) containerCausa.style.display = 'none';
        
        // ⭐ Limpar inputs de texto
        this.setValueIfExists('outra-categoria-risco-texto', '');
        this.setValueIfExists('outra-categoria-causa-texto', '');
        
        this.atualizarScoreRisco();
    
    },

    atualizarScoreRisco() {
        const impacto = document.getElementById('risco_impacto')?.value || '';
        const prob = document.getElementById('risco_probabilidade')?.value || '';
        
        if (!impacto || !prob) {
            const preview = document.getElementById('risco-score-preview');
            if (preview) {
                preview.innerHTML = `<strong>Risco bruto:</strong> <span id="preview-score">-</span>`;
            }
            return 0;
        }
        
        const score = calcularScoreRisco(impacto, prob);
        const preview = document.getElementById('risco-score-preview');
        if (preview) {
            preview.innerHTML = `<strong>Risco bruto:</strong> <span id="preview-score">${score}</span> (${this.getNivelRisco(score)})`;
        }
        return score;
    },

    
    getNivelRisco(score) {
        if (score <= 3) return 'BAIXO';
        if (score <= 6) return 'MÉDIO';
        if (score <= 12) return 'ALTO';
        return 'CRÍTICO';
    }
    
};