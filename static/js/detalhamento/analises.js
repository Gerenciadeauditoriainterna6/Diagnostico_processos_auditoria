// ============================================================
// analises.js - MÓDULO DE ANÁLISES CRÍTICAS
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

        if (analiseId && analiseId !== '') {
            this.salvarNoBanco(analiseId, analiseData, etapaId);
        } else if (tempId && tempId !== '') {
            const tempIndex = parseInt(tempId);
            if (tempIndex >= 0 && tempIndex < this.temporarias.length) {
                this.temporarias[tempIndex] = { ...this.temporarias[tempIndex], ...analiseData, _temporaria: true };
                window.mostrarToast('✅ Análise atualizada!', 'success');
                this.esconderForm();
                this.renderizar();
                this.resetarEvidencia();
            }
        } else if (!etapaId || etapaId === '') {
            this.temporarias.push({ ...analiseData, _temporaria: true, _id: Date.now() });
            window.mostrarToast('✅ Análise adicionada!', 'success');
            this.esconderForm();
            this.renderizar();
            this.resetarEvidencia();
        } else {
            this.salvarNoBanco(null, analiseData, etapaId);
        }
    },

    async salvarNoBanco(analiseId, analiseData, etapaId) {
        if (!etapaId) return;

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

        if (analiseData.evidencia_base64 && analiseData.evidencia_nome) {
            payload.evidencia_base64 = analiseData.evidencia_base64;
            payload.evidencia_nome = analiseData.evidencia_nome;
        }
        if (analiseData.remover_evidencia) {
            payload.remover_evidencia = true;
        }

        try {
            const response = await window.fetchComAutenticacao('/api/analise/salvar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (data.success) {
                window.mostrarToast('✅ Análise salva!', 'success');
                this.esconderForm();
                this.resetarEvidencia();
                await this.carregar(etapaId);
            } else {
                window.mostrarToast('❌ Erro: ' + (data.error || 'Tente novamente'), 'error');
            }
        } catch (error) {
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
        if (!etapaId) {
            this.existentes = [];
            this.renderizar();
            return;
        }
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}/analises`);
            const data = await response.json();
            if (data.success) {
                this.existentes = data.analises || [];
                this.renderizar();
            }
        } catch (error) {
            console.error('Erro ao carregar análises:', error);
        }
    },

    async carregarResumo(etapaId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}/analises`);
            const data = await response.json();
            const container = document.getElementById(`analises-resumo-${etapaId}`);
            if (!container) return;
            if (data.success && data.analises?.length > 0) {
                container.innerHTML = data.analises.map(a => `
                    <span style="display:inline-block;margin:4px 8px 4px 0;padding:4px 12px;background:#f0f4f8;border-radius:20px;font-size:12px;">
                        ${escapeHtml(a.analise_critica?.substring(0, 60) || 'Sem análise')}
                    </span>
                `).join('');
            } else {
                container.innerHTML = '<span style="color:#999;">Nenhuma análise</span>';
            }
        } catch (error) {
            // silencioso
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

        if (modo === 'editar' && index !== null) {
            const analise = isTemporaria ? this.temporarias[index - this.existentes.length] : this.existentes[index];
            if (analise) {
                document.getElementById('analise-id').value = analise.id || '';
                document.getElementById('analise-texto').value = analise.analise_critica || '';
                document.getElementById('analise-sugestao').value = analise.sugestao_melhoria || '';
                document.getElementById('analise-necessidade').value = analise.necessidade_implantacao || '';
                document.getElementById('analise-ganho').value = analise.ganho_previsto || '';
                
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
            // Limpar campos...
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
    }

};