// ============================================================
// analises.js - MÓDULO DE ANÁLISES CRÍTICAS DO MODAL DE CADASTRO DA ETAPA
// ============================================================

const AnalisesModule = {

    // Atributos
    temporarias: [],
    existentes: [],
    evidenciaArquivo: null,
    evidenciaExistente: null,
    evidenciaNomeExistente: null,

    init() {
        console.log('📌 AnalisesModule: inicializado');
        this.configurarCheckboxNaoHaAnalise();
    },

    // ============================================================
    // EDITAR
    // ============================================================
    editar(index, isTemporaria) {
        this.mostrarForm('editar', index, isTemporaria);
    },

    async baixarEvidencia(analiseId, nomeArquivo) {
        try {
            const response = await window.fetchComAutenticacao(`/api/analise/${analiseId}/evidencia`);
            
            if (!response.ok) {
                window.mostrarToast('❌ Erro ao baixar evidência', 'error');
                return;
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = nomeArquivo || 'evidencia.pdf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            setTimeout(() => window.URL.revokeObjectURL(url), 100);
            
            window.mostrarToast('✅ Download iniciado!', 'success');
        } catch (error) {
            window.mostrarToast('❌ Erro ao baixar', 'error');
        }
    },

    // ============================================================
    // SALVAR
    // ============================================================
    salvar() {
        const tipoAnalise = 'auditado';
        const radioSelecionado = document.querySelector('#form-analise input[name="sugestao-status-auditado-radio"]:checked');
        let sugestaoSeraImplantada = null;

        if (radioSelecionado) {
            sugestaoSeraImplantada = radioSelecionado.value === 'true' ? true : 
                                     radioSelecionado.value === 'false' ? false : null;
        }

        const temEvidencia = this.evidenciaArquivo !== null;
        const removerEvidencia = document.getElementById('remover_analise_evidencia')?.value === 'true';

        const analiseData = {
            tipo_analise: tipoAnalise,
            categoria: 'governanca',
            analise_critica: document.getElementById('analise-texto').value,
            sugestao_melhoria: document.getElementById('analise-sugestao').value,
            necessidade_implantacao: document.getElementById('analise-necessidade').value,
            ganho_previsto: document.getElementById('analise-ganho').value,
            sugestao_sera_implantada: sugestaoSeraImplantada
        };

        // Se não tem N/A, pelo menos análise deve estar preenchida
        const checkboxNaoHa = document.getElementById('analise-nao-ha');
        if (!checkboxNaoHa?.checked && !analiseData.analise_critica.trim()) {
            window.mostrarToast('⚠️ Preencha a análise ou marque "Não há análise"', 'warning');
            return;
        }

        if (removerEvidencia) {
            analiseData.remover_evidencia = true;
        }

        if (temEvidencia) {
            converterParaBase64(this.evidenciaArquivo)
                .then(base64 => {
                    analiseData.evidencia_base64 = base64;
                    analiseData.evidencia_nome = this.evidenciaArquivo.name;
                    this._processarSalvamento(analiseData);
                })
                .catch(error => {
                    console.error('Erro ao converter evidência:', error);
                    window.mostrarToast('❌ Erro ao processar evidência', 'error');
                });
        } else {
            this._processarSalvamento(analiseData);
        }
    },

    _processarSalvamento(analiseData) {
        const analiseId = document.getElementById('analise-id').value;
        const tempId = document.getElementById('analise-temp-id').value;
        const etapaId = document.getElementById('modal-etapa-id').value;

        console.log('🔍 _processarSalvamento:');
        console.log('   analiseId:', analiseId);
        console.log('   tempId:', tempId);
        console.log('   etapaId:', etapaId);
        console.log('   temporarias ANTES:', this.temporarias);

        // ⭐ CASO 1: Editando análise existente (já salva no banco)
        if (analiseId && analiseId !== '') {
            // Buscar a análise existente para obter o etapa_id CORRETO
            const analiseExistente = this.existentes.find(a => a.id == analiseId);
            const etapaCorreta = analiseExistente?.etapa_id || etapaId;
            
            console.log('   ✅ Análise existente - etapa correta:', etapaCorreta);
            
            this.salvarNoBanco(analiseId, analiseData, etapaCorreta);
            return; // Importante: sair da função
        }
        
        // ⭐ CASO 2: Atualizando análise temporária
        if (tempId && tempId !== '') {
            const tempIndex = parseInt(tempId);
            if (tempIndex >= 0 && tempIndex < this.temporarias.length) {
                this.temporarias[tempIndex] = { 
                    ...this.temporarias[tempIndex], 
                    ...analiseData, 
                    _temporaria: true 
                };
                window.mostrarToast('✅ Análise atualizada!', 'success');
                this.esconderForm();
                this.renderizar();
                this.resetarEvidencia();
            } else {
                console.warn('⚠️ Índice de temporária inválido:', tempIndex);
            }
            return;
        }
        
        // ⭐ CASO 3: Nova análise temporária (sem etapa definida)
        if (!etapaId || etapaId === '') {
            this.temporarias.push({ 
                ...analiseData, 
                _temporaria: true, 
                _id: Date.now() 
            });
            window.mostrarToast('✅ Análise adicionada!', 'success');
            this.esconderForm();
            this.renderizar();
            this.resetarEvidencia();
            return;
        }
        
        // ⭐ CASO 4: Nova análise com etapa definida (salva direto no banco)
        this.salvarNoBanco(null, analiseData, etapaId);

        console.log('   temporarias DEPOIS:', this.temporarias);
    },

    async salvarNoBanco(analiseId, analiseData, etapaId) {
        console.log('💾 salvarNoBanco chamado:');
        console.log('   analiseId:', analiseId);
        console.log('   etapaId:', etapaId);
        console.log('   analiseData:', analiseData);
        
        if (!etapaId) {
            console.error('❌ etapaId vazio! Não é possível salvar.');
            window.mostrarToast('❌ Erro: Etapa não identificada', 'error');
            return;
        }
        
        const payload = {
            id: analiseId || null,
            etapa_id: parseInt(etapaId),
            tipo_analise: 'auditado',
            categoria: analiseData.categoria,
            analise_critica: analiseData.analise_critica,
            sugestao_melhoria: analiseData.sugestao_melhoria,
            necessidade_implantacao: analiseData.necessidade_implantacao,
            ganho_previsto: analiseData.ganho_previsto
        };
        
        // Adicionar evidência se existir
        if (analiseData.evidencia_base64 && analiseData.evidencia_nome) {
            payload.evidencia_base64 = analiseData.evidencia_base64;
            payload.evidencia_nome = analiseData.evidencia_nome;
        }
        
        // Adicionar flag de remoção de evidência
        if (analiseData.remover_evidencia) {
            payload.remover_evidencia = true;
        }
        
        console.log('📤 Payload a enviar:', payload);
        
        try {
            const response = await window.fetchComAutenticacao('/api/analise/salvar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            console.log('📥 Resposta da API:', data);
            
            if (data.success) {
                window.mostrarToast('✅ Análise salva!', 'success');
                this.esconderForm();
                this.resetarEvidencia();
                await this.carregar(etapaId);
            } else {
                window.mostrarToast('❌ Erro: ' + (data.error || 'Tente novamente'), 'error');
            }
        } catch (error) {
            console.error('❌ Erro de conexão:', error);
            window.mostrarToast('❌ Erro de conexão', 'error');
        }
    },

    // ============================================================
    // EXCLUIR
    // ============================================================
    excluir(index, isTemporaria) {
        if (!confirm('Excluir esta análise?')) return;

        if (isTemporaria) {
            const tempIndex = index - this.existentes.length;
            if (tempIndex >= 0 && tempIndex < this.temporarias.length) {
                this.temporarias.splice(tempIndex, 1);
                window.mostrarToast('✅ Análise removida', 'success');
                this.renderizar();
            }
            return;
        }

        const analise = this.existentes[index];
        if (!analise || !analise.id) {
            this.existentes.splice(index, 1);
            this.renderizar();
            return;
        }
        this.excluirDoBanco(analise.id);
    },

    async excluirDoBanco(analiseId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/analise/${analiseId}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                window.mostrarToast('✅ Análise excluída', 'success');
                const etapaId = document.getElementById('modal-etapa-id').value;
                if (etapaId) await this.carregar(etapaId);
            }
        } catch (error) {
            window.mostrarToast('❌ Erro ao excluir', 'error');
        }
    },

    // ============================================================
    // SALVAR TEMPORÁRIAS
    // ============================================================
    async salvarTemporarias(etapaId) {
        if (this.temporarias.length === 0) return;

        for (const analise of this.temporarias) {
            const payload = {
                etapa_id: parseInt(etapaId),
                tipo_analise: 'auditado',
                categoria: analise.categoria,
                analise_critica: analise.analise_critica,
                sugestao_melhoria: analise.sugestao_melhoria,
                necessidade_implantacao: analise.necessidade_implantacao,
                ganho_previsto: analise.ganho_previsto
            };
            if (analise.evidencia_base64) {
                payload.evidencia_base64 = analise.evidencia_base64;
                payload.evidencia_nome = analise.evidencia_nome;
            }
            try {
                await window.fetchComAutenticacao('/api/analise/salvar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } catch (error) {
                console.error('Erro ao salvar temporária:', error);
            }
        }
        this.temporarias = [];
    },

    // ============================================================
    // CARREGAR
    // ============================================================
    async carregar(etapaId) {
        console.log('📥 Carregando análises da etapa:', etapaId);
        
        // ⭐ Guardar etapa atual
        this.etapaIdAtual = etapaId;
        
        if (!etapaId) {
            this.existentes = [];
            this.renderizar();
            return;
        }
        
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}/analises`);
            const data = await response.json();
            
            console.log('📥 Resposta da API:', data);
            
            if (data.success) {
                this.existentes = data.analises || [];
                
                // ⭐ Verificar se cada análise tem etapa_id
                this.existentes.forEach(a => {
                    console.log(`   Análise ${a.id}: etapa_id = ${a.etapa_id}`);
                });
                
                this.renderizar();
            }
        } catch (error) {
            console.error('❌ Erro ao carregar análises:', error);
        }
    },

    async carregar(etapaId) {
        console.log('📥 Carregando análises da etapa:', etapaId);
        
        if (!etapaId) {
            this.existentes = [];
            this.renderizar();
            return;
        }
        
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}/analises`);
            const data = await response.json();
            console.log('📥 Resposta:', data);
            
            if (data.success) {
                this.existentes = data.analises || [];
                console.log('📥 Análises carregadas:', this.existentes);
                this.renderizar();
            }
        } catch (error) {
            console.error('Erro ao carregar análises:', error);
        }
    },

    // ============================================================
    // RENDERIZAR
    // ============================================================
    renderizar() {
        const container = document.getElementById('analises-lista');
        if (!container) return;

        const todas = [...this.existentes, ...this.temporarias];
        if (todas.length === 0) {
            container.innerHTML = '<div class="analises-empty">Nenhuma análise.</div>';
            return;
        }

        container.innerHTML = todas.map((analise, index) => {
            const isTemporaria = analise._temporaria === true;
            const temEvidencia = analise.evidencia_nome && analise.evidencia_nome.trim() !== '';
            
            return `
                <div class="analise-card">
                    <div class="analise-card-info">
                        <strong>Análise:</strong> ${escapeHtml(analise.analise_critica || '-')}<br>
                        <strong>Sugestão:</strong> ${escapeHtml(analise.sugestao_melhoria || '-')}
                        ${temEvidencia ? `
                            <br><strong>Evidência:</strong> ${escapeHtml(analise.evidencia_nome)}
                            <button onclick="AnalisesModule.baixarEvidencia(${analise.id}, '${escapeHtml(analise.evidencia_nome)}')"
                                style="background:#0b5b99;color:white;border:none;padding:2px 10px;border-radius:4px;cursor:pointer;font-size:11px;">
                                <i class="fas fa-download"></i> Baixar
                            </button>
                        ` : ''}
                    </div>
                    <div class="analise-card-actions">
                        <button onclick="AnalisesModule.editar(${index}, ${isTemporaria})">✏️</button>
                        <button onclick="AnalisesModule.excluir(${index}, ${isTemporaria})">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');
    },

    // ============================================================
    // FORMULÁRIO
    // ============================================================
    mostrarForm(modo = 'novo', index = null, isTemporaria = false) {
        const form = document.getElementById('form-analise');
        if (!form) return;
        form.style.display = 'block';
        this.resetarEvidencia();

        this.limparCheckboxNaoHaAnalise();

        if (modo === 'editar' && index !== null) {
            // ⭐ MODO EDIÇÃO: Preenche campos
            const analise = isTemporaria 
                ? this.temporarias[index - this.existentes.length] 
                : this.existentes[index];
                
            if (analise) {
                document.getElementById('analise-id').value = analise.id || '';
                document.getElementById('analise-temp-id').value = isTemporaria ? (index - this.existentes.length) : '';
                document.getElementById('analise-texto').value = analise.analise_critica || '';
                document.getElementById('analise-sugestao').value = analise.sugestao_melhoria || '';
                document.getElementById('analise-necessidade').value = analise.necessidade_implantacao || '';
                document.getElementById('analise-ganho').value = analise.ganho_previsto || '';

                if (analise.analise_critica === 'N/A') {
                    const checkbox = document.getElementById('analise-nao-ha');
                    if (checkbox) {
                        checkbox.checked = true;
                        this.preencherComNA();
                    }
                }
                
                // ⭐ Limpar radio buttons de sugestão
                const radios = document.querySelectorAll('#form-analise input[name="sugestao-status-auditado-radio"]');
                radios.forEach(radio => {
                    radio.checked = (radio.value === String(analise.sugestao_sera_implantada));
                });
                
                // ⭐ Carregar evidência existente
                if (analise.evidencia_url && analise.evidencia_nome) {
                    const infoDiv = document.getElementById('analise_evidencia_info');
                    const nomeSpan = document.getElementById('analise_evidencia_nome');
                    if (infoDiv) infoDiv.style.display = 'block';
                    if (nomeSpan) nomeSpan.textContent = analise.evidencia_nome;
                    this.evidenciaExistente = analise.evidencia_url;
                    this.evidenciaNomeExistente = analise.evidencia_nome;
                }
            }
        } else {
            // ⭐ MODO NOVO: Limpar todos os campos
            document.getElementById('analise-id').value = '';
            document.getElementById('analise-temp-id').value = '';
            document.getElementById('analise-texto').value = '';
            document.getElementById('analise-sugestao').value = '';
            document.getElementById('analise-necessidade').value = '';
            document.getElementById('analise-ganho').value = '';
            
            // Limpar radio buttons
            const radios = document.querySelectorAll('#form-analise input[name="sugestao-status-auditado-radio"]');
            radios.forEach(radio => {
                radio.checked = false;
            });
            
            // Limpar evidência
            const infoDiv = document.getElementById('analise_evidencia_info');
            const nomeSpan = document.getElementById('analise_evidencia_nome');
            if (infoDiv) infoDiv.style.display = 'none';
            if (nomeSpan) nomeSpan.textContent = '';
            
            this.evidenciaExistente = null;
            this.evidenciaNomeExistente = null;
            this.evidenciaArquivo = null;
        }
        
        this.setupEvidenciaUpload();
        form.scrollIntoView({ behavior: 'smooth', block: 'center' });
    },

    esconderForm() {
        const form = document.getElementById('form-analise');
        if (form) form.style.display = 'none';
        this.resetarEvidencia();
    },

    // ============================================================
    // EVIDÊNCIA
    // ============================================================
    setupEvidenciaUpload() {
        const btnUpload = document.getElementById('btn_analise_evidencia');
        const inputFile = document.getElementById('analise_evidencia_input');
        const infoDiv = document.getElementById('analise_evidencia_info');
        const nomeSpan = document.getElementById('analise_evidencia_nome');
        const btnRemover = document.getElementById('btn_remover_analise_evidencia');

        if (!btnUpload || !inputFile) return;

        btnUpload.addEventListener('click', () => inputFile.click());

        inputFile.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            if (file.type !== 'application/pdf') { window.mostrarToast('⚠️ Apenas PDF', 'warning'); return; }
            if (file.size > 10 * 1024 * 1024) { window.mostrarToast('⚠️ Máx 10MB', 'warning'); return; }

            this.evidenciaArquivo = file;
            if (nomeSpan) nomeSpan.textContent = file.name;
            if (infoDiv) infoDiv.style.display = 'block';
            this.evidenciaExistente = null;
            this.evidenciaNomeExistente = null;
        });

        if (btnRemover) {
            btnRemover.replaceWith(btnRemover.cloneNode(true));  // Remove todos os eventos
            const newBtnRemover = document.getElementById('btn_remover_analise_evidencia');
            newBtnRemover.addEventListener('click', async () => {
                // ⭐ Se tem evidência existente, excluir do Storage
                if (this.evidenciaExistente) {
                    if (confirm('Remover evidência permanentemente?')) {
                        try {
                            window.mostrarToast('🗑️ Removendo evidência...', 'info');
                            
                            const response = await window.fetchComAutenticacao('/api/arquivo/excluir', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    arquivo_url: this.evidenciaExistente,
                                    bucket: 'evidencia_analises_auditado'
                                })
                            });
                            
                            const data = await response.json();
                            if (data.success) {
                                // Marcar para remover no banco também
                                let hidden = document.getElementById('remover_analise_evidencia');
                                if (!hidden) {
                                    hidden = document.createElement('input');
                                    hidden.type = 'hidden';
                                    hidden.id = 'remover_analise_evidencia';
                                    hidden.value = 'true';
                                    document.getElementById('form-analise').appendChild(hidden);
                                }
                                window.mostrarToast('✅ Evidência removida!', 'success');
                            } else {
                                window.mostrarToast('❌ Erro ao remover', 'error');
                            }
                        } catch (error) {
                            window.mostrarToast('❌ Erro de conexão', 'error');
                        }
                    }
                }
                
                // Limpar interface
                inputFile.value = '';
                this.evidenciaArquivo = null;
                this.evidenciaExistente = null;
                this.evidenciaNomeExistente = null;
                if (infoDiv) infoDiv.style.display = 'none';
                if (nomeSpan) nomeSpan.textContent = '';
            });
        }
    },

    resetarEvidencia() {
        const infoDiv = document.getElementById('analise_evidencia_info');
        const nomeSpan = document.getElementById('analise_evidencia_nome');
        const inputFile = document.getElementById('analise_evidencia_input');
        const hidden = document.getElementById('remover_analise_evidencia');
        if (infoDiv) infoDiv.style.display = 'none';
        if (nomeSpan) nomeSpan.textContent = '';
        if (inputFile) inputFile.value = '';
        if (hidden) hidden.remove();
        this.evidenciaArquivo = null;
        this.evidenciaExistente = null;
        this.evidenciaNomeExistente = null;
        this.limparCheckboxNaoHaAnalise();
    },

    // ============================================================
    // CHECKBOX "NÃO HÁ ANÁLISE"
    // ============================================================

    configurarCheckboxNaoHaAnalise() {
        const checkbox = document.getElementById('analise-nao-ha');
        if (!checkbox) return;
        
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                this.preencherComNA();
            } else {
                this.limparCamposNA();
            }
        });
    },

    preencherComNA() {
        const campos = [
            'analise-texto',
            'analise-sugestao',
            'analise-necessidade',
            'analise-ganho'
        ];
        
        campos.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) {
                campo.value = 'N/A';
                campo.disabled = true;
                campo.style.background = '#e9ecef';
                campo.style.cursor = 'not-allowed';
            }
        });
        
        console.log('✅ Campos preenchidos com N/A');
    },

    limparCamposNA() {
        const campos = [
            'analise-texto',
            'analise-sugestao',
            'analise-necessidade',
            'analise-ganho'
        ];
        
        campos.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) {
                campo.value = '';
                campo.disabled = false;
                campo.style.background = '';
                campo.style.cursor = '';
            }
        });
        
        console.log('✅ Campos liberados');
    },

    limparCheckboxNaoHaAnalise() {
        const checkbox = document.getElementById('analise-nao-ha');
        if (checkbox) {
            checkbox.checked = false;
        }
        
        this.limparCamposNA();
    },

};