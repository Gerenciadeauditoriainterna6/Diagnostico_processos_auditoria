// ============================================================
// anexos.js - MÓDULO DE ANEXOS
// ============================================================

const AnexosModule = {
    
    processoId: null,
    modal: null,
    
    init() {
        this.modal = document.getElementById('modal-anexos');
        
        // Fechar
        document.getElementById('btn-fechar-modal-anexos')?.addEventListener('click', () => this.fechar());
        document.getElementById('btn-fechar-modal-anexos-footer')?.addEventListener('click', () => this.fechar());
        
        // Upload
        const uploadArea = document.getElementById('upload-area');
        const inputFile = document.getElementById('input-upload-anexo');
        
        uploadArea?.addEventListener('click', () => inputFile.click());
        
        uploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#184145';
        });
        
        uploadArea?.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '#ccc';
        });
        
        uploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#ccc';
            const file = e.dataTransfer.files[0];
            if (file) this.uploadArquivo(file);
        });
        
        inputFile?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) this.uploadArquivo(file);
        });
    },
    
    abrir(processoId, nomeProcesso, codigoProcesso) {
        this.processoId = processoId;
        
        // Mostrar info
        document.getElementById('anexos-processo-info').innerHTML = `
            <strong><i class="fas fa-tag"></i> Processo: ${codigoProcesso} - ${nomeProcesso}</strong>
        `;
        
        this.modal.style.display = 'flex';
        this.carregarAnexos();
    },
    
    fechar() {
        this.modal.style.display = 'none';
    },
    
    async carregarAnexos() {
        const container = document.getElementById('anexos-lista');
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div class="dot-spinner">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando anexos...</p>
            </div>
        `;
        
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${this.processoId}/anexos`);
            const data = await response.json();
            
            if (data.success && data.anexos.length > 0) {
                container.innerHTML = data.anexos.map(a => `
                    <div class="anexo-item" style="
                        display: flex; justify-content: space-between; align-items: center;
                        padding: 10px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 8px;
                    ">
                        <div>
                            <i class="fas fa-${this.iconeTipo(a.tipo_mime)}" style="color: #184145; margin-right: 8px;"></i>
                            <span>${a.nome_original}</span>
                            <br>
                            <small style="color: #999;">${this.formatarTamanho(a.tamanho_bytes)}</small>
                        </div>
                        <div>
                            <button class="btn-visualizar btn-sm" onclick="AnexosModule.visualizar(${a.id})">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn-excluir btn-sm" onclick="AnexosModule.excluir(${a.id})">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p style="text-align:center; padding:20px; color:#999;">Nenhum anexo.</p>';
            }
        } catch (error) {
            container.innerHTML = '<p style="text-align:center; color:#dc3545;">Erro ao carregar.</p>';
        }
    },
    
    async uploadArquivo(file) {
        // Validar tipo
        const tiposPermitidos = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
        if (!tiposPermitidos.includes(file.type)) {
            window.mostrarToast('❌ Tipo de arquivo não permitido!', 'error');
            return;
        }
        
        // Validar tamanho (10MB)
        if (file.size > 10 * 1024 * 1024) {
            window.mostrarToast('❌ Arquivo excede 10MB!', 'error');
            return;
        }
        
        const formData = new FormData();
        formData.append('arquivo', file);
        
        window.mostrarToast('📤 Enviando arquivo...', 'info');
        
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${this.processoId}/anexos`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.mostrarToast('✅ Arquivo enviado!', 'success');
                this.carregarAnexos();
            } else {
                window.mostrarToast('❌ ' + (data.error || 'Erro no upload'), 'error');
            }
        } catch (error) {
            window.mostrarToast('❌ Erro no upload', 'error');
        }
    },
    
    async visualizar(anexoId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/anexo/${anexoId}/url`);
            const data = await response.json();
            
            if (data.success && data.url) {
                window.open(data.url, '_blank');
            }
        } catch (error) {
            window.mostrarToast('❌ Erro ao abrir arquivo', 'error');
        }
    },
    
    async excluir(anexoId) {
        if (!confirm('Excluir este anexo?')) return;
        
        try {
            const response = await window.fetchComAutenticacao(`/api/anexo/${anexoId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.mostrarToast('✅ Anexo excluído!', 'success');
                this.carregarAnexos();
            }
        } catch (error) {
            window.mostrarToast('❌ Erro ao excluir', 'error');
        }
    },
    
    iconeTipo(tipo) {
        if (tipo?.includes('pdf')) return 'file-pdf';
        if (tipo?.includes('image')) return 'file-image';
        return 'file';
    },
    
    formatarTamanho(bytes) {
        if (!bytes) return '0 B';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
    
};