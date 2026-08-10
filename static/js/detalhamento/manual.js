// ============================================================
// manual.js - MÓDULO DO MANUAL DA ETAPA
// ============================================================

const ManualModule = {

    estado: {
        temArquivo: false,
        nomeArquivo: null,
        emAndamento: false,
        etapaIdAtual: null,
    },

    init() {
        console.log('📌 ManualModule: inicializado');

        // ⭐ Configurar evento de upload quando selecionar arquivo
        const inputFile = document.getElementById('manual_file_input');
        if (inputFile) {
            inputFile.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                // Validar tipo
                const tiposPermitidos = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
                if (!tiposPermitidos.includes(file.type)) {
                    window.mostrarToast('⚠️ Apenas PDF, DOC e DOCX são permitidos', 'warning');
                    inputFile.value = '';
                    return;
                }
                
                // Validar tamanho (10MB)
                if (file.size > 10 * 1024 * 1024) {
                    window.mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
                    inputFile.value = '';
                    return;
                }
                
                window.mostrarToast('📤 Enviando manual...', 'info');
                
                try {
                    const success = await this.upload(this.etapaIdAtual, file);
                    if (success) {
                        this.estado.temArquivo = true;
                        this.estado.nomeArquivo = file.name;
                        this.estado.emAndamento = false;
                        this.atualizarInterface();
                        window.mostrarToast('✅ Manual anexado com sucesso!', 'success');
                    }
                } catch (error) {
                    window.mostrarToast('❌ Erro ao enviar manual: ' + error.message, 'error');
                }
                
                inputFile.value = '';
            });
        }
        
        // ⭐ Configurar todos os eventos do manual (SEM onclick no HTML!)
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;
            
            if (btn.id === 'btn-marcar-andamento' || btn.classList.contains('btn-marcar-andamento')) {
                this.marcarEmAndamento();
            }
            else if (btn.id === 'btn-cancelar-andamento' || btn.classList.contains('btn-cancelar-andamento')) {
                this.cancelarAndamento();
            }
            else if (btn.id === 'btn-anexar-manual' || btn.classList.contains('btn-anexar-manual')) {
                this.anexar();
            }
            else if (btn.id === 'btn-substituir-manual' || btn.classList.contains('btn-substituir-manual')) {
                this.substituir();
            }
            else if (btn.id === 'btn-baixar-manual' || btn.classList.contains('btn-baixar-manual')) {
                this.baixar(this.etapaIdAtual);  
            }
            else if (btn.classList.contains('btn-remover-manual')) {
                this.remover(this.etapaIdAtual);  // ✅ Passa o ID!
            }
            else if (btn.id === 'btn-concluir-manual' || btn.classList.contains('btn-concluir-manual')) {
                this.anexar();
            }
        });
    },

    // ============================================================
    // CARREGAR ESTADO
    // ============================================================
    carregarEstado(etapaId) {
        window.fetchComAutenticacao(`/api/etapa/${etapaId}`)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.etapa) {
                    const etapa = data.etapa;
                    if (etapa.manual_url && etapa.manual_url.trim() !== '') {
                        this.estado.temArquivo = true;
                        this.estado.nomeArquivo = etapa.manual_nome || 'manual.pdf';
                        this.estado.emAndamento = false;
                    } else if (etapa.manual_em_andamento) {
                        this.estado.temArquivo = false;
                        this.estado.nomeArquivo = null;
                        this.estado.emAndamento = true;
                    } else {
                        this.estado.temArquivo = false;
                        this.estado.nomeArquivo = null;
                        this.estado.emAndamento = false;
                    }
                    this.atualizarInterface();
                }
            })
            .catch(err => console.error('Erro ao carregar manual:', err));
    },

    // ============================================================
    // ATUALIZAR INTERFACE
    // ============================================================
    atualizarInterface() {
        const divAnexado = document.getElementById('manual_anexado');
        const divAndamento = document.getElementById('manual_andamento');
        const divNenhum = document.getElementById('manual_nenhum');
        const checkbox = document.getElementById('manual_em_andamento');

        // ⭐ Verificar se os elementos existem
        if (!divAnexado || !divAndamento || !divNenhum) {
            console.warn('⚠️ Containers do manual não encontrados');
            return;
        }

        if (this.estado.temArquivo) {
            divAnexado.style.display = 'block';
            divAndamento.style.display = 'none';
            divNenhum.style.display = 'none';
            const nomeExibicao = document.getElementById('manual_nome_exibicao');
            if (nomeExibicao) nomeExibicao.textContent = this.estado.nomeArquivo;
            if (checkbox) {
                checkbox.checked = false;
                checkbox.disabled = true;
            }
        } else if (this.estado.emAndamento) {
            divAnexado.style.display = 'none';
            divAndamento.style.display = 'block';
            divNenhum.style.display = 'none';
            if (checkbox) {
                checkbox.checked = true;
                checkbox.disabled = false;
            }
        } else {
            divAnexado.style.display = 'none';
            divAndamento.style.display = 'none';
            divNenhum.style.display = 'block';
            if (checkbox) {
                checkbox.checked = false;
                checkbox.disabled = false;
            }
        }
    },

    // ============================================================
    // RESETAR INTERFACE
    // ============================================================
    resetarInterface() {
        ['manual_anexado', 'manual_andamento'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        const divNenhum = document.getElementById('manual_nenhum');
        if (divNenhum) divNenhum.style.display = 'block';
        const checkbox = document.getElementById('manual_em_andamento');
        if (checkbox) { checkbox.checked = false; checkbox.disabled = false; }
        const inputFile = document.getElementById('manual_file_input');
        if (inputFile) inputFile.value = '';
        this.estado = { temArquivo: false, nomeArquivo: null, emAndamento: false };
    },

    setEtapaId(id) {
        this.etapaIdAtual = id;
    },

    marcarEmAndamento() {
        if (!this.etapaIdAtual) {
            window.mostrarToast('⚠️ Etapa não identificada', 'warning');
            return;
        }
        this.estado.emAndamento = true;
        this.estado.temArquivo = false;
        this.estado.nomeArquivo = null;
        this._salvarEstado(this.etapaIdAtual, true, null);  // ⭐ Passa o ID!
        this.atualizarInterface();
        window.mostrarToast('📝 Manual marcado como em andamento', 'info');
    },

    cancelarAndamento() {
        if (!this.etapaIdAtual) {
            window.mostrarToast('⚠️ Etapa não identificada', 'warning');
            return;
        }
        if (!confirm('Cancelar o status "em andamento"?')) return;
        this.estado.emAndamento = false;
        this.estado.temArquivo = false;
        this.estado.nomeArquivo = null;
        this._salvarEstado(this.etapaIdAtual, false, null);  // ⭐ Passa o ID!
        this.atualizarInterface();
        window.mostrarToast('✅ Andamento cancelado', 'success');
    },

    // ============================================================
    // ANEXAR / SUBSTITUIR
    // ============================================================
    anexar() { document.getElementById('manual_file_input').click(); },
    substituir() {
        if (!confirm('Substituir o manual atual?')) return;
        document.getElementById('manual_file_input').click();
    },

    // ============================================================
    // BAIXAR MANUAL
    // ============================================================
    baixar(etapaId) {
        if (!etapaId || !this.estado.temArquivo) {
            window.mostrarToast('⚠️ Nenhum manual disponível', 'warning');
            return;
        }
        window.open(`/api/etapa/${etapaId}/download-manual`, '_blank');
    },

    // ============================================================
    // REMOVER MANUAL
    // ============================================================
    async remover(etapaId) {
        if (!confirm('Remover o manual?')) return;
        try {
            const resp = await window.fetchComAutenticacao(`/api/etapa/${etapaId}`);
            const dados = await resp.json();
            if (!dados.success || !dados.etapa.manual_url) {
                window.mostrarToast('⚠️ Nenhum manual para remover', 'warning');
                return;
            }
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}/remover-manual`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ etapa_id: etapaId, arquivo_url: dados.etapa.manual_url })
            });
            const data = await response.json();
            if (data.success) {
                this.estado = { temArquivo: false, nomeArquivo: null, emAndamento: false };
                this.atualizarInterface();
                window.mostrarToast('✅ Manual removido!', 'success');
            }
        } catch (error) {
            window.mostrarToast('❌ Erro de conexão', 'error');
        }
    },

    // ============================================================
    // UPLOAD DO MANUAL
    // ============================================================
    async upload(etapaId, arquivo) {
        // ⭐ Mostrar loading no modal
        const statusContainer = document.getElementById('manual_status_container');
        const loadingHTML = `
            <div style="text-align:center;padding:20px;">
                <div class="dot-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
                <p style="margin-top:10px;color:#666;">Enviando manual...</p>
            </div>
        `;
        statusContainer.innerHTML = loadingHTML;
        
        const formData = new FormData();
        formData.append('arquivo', arquivo);
        formData.append('tipo', 'manual');
        formData.append('etapa_id', etapaId || 'temp');
        formData.append('nome_personalizado', `manual_eta_${etapaId}.pdf`);

        try {
            const response = await window.fetchComAutenticacao('/api/upload/detalhamento', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.success) {
                return await this._salvarUrl(etapaId, data.url, `manual_etapa_id_${etapaId}.pdf`, data.tamanho, false);
            }
        } catch (error) {
            console.error('Erro no upload:', error);
        }
        return false;
    },

    // ============================================================
    // PRIVADOS
    // ============================================================
    async _salvarUrl(etapaId, url, nome, tamanho, emAndamento) {
        try {
            const resp = await window.fetchComAutenticacao(`/api/etapa/${etapaId}`);
            const dados = await resp.json();
            if (!dados.success) return false;

            const payload = { ...dados.etapa, id: etapaId, manual_url: url, manual_nome: nome, manual_em_andamento: emAndamento };
            const response = await window.fetchComAutenticacao('/api/etapa/salvar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            return result.success;
        } catch (error) {
            return false;
        }
    },

    async _salvarEstado(etapaId, emAndamento, arquivoUrl) {
        try {
            const resp = await window.fetchComAutenticacao(`/api/etapa/${etapaId}`);
            const dados = await resp.json();
            if (!dados.success) return false;

            const payload = { ...dados.etapa, id: etapaId, manual_em_andamento: emAndamento };
            if (arquivoUrl) { payload.manual_url = arquivoUrl; } else if (!emAndamento) { payload.remover_manual = true; }

            const response = await window.fetchComAutenticacao('/api/etapa/salvar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            return (await response.json()).success;
        } catch (error) {
            return false;
        }
    }

};