// ============================================================
// politica_interna.js - MÓDULO DE POLÍTICA INTERNA
// ============================================================

const PoliticaInternaModule = {
    
    // Atributos
    arquivoPolitica: null,          // File object para upload novo
    arquivoUrlExistente: '',        // URL do arquivo já salvo
    arquivoNomeExistente: '',       // Nome do arquivo já salvo
    
    init() {
        console.log('📌 PoliticaInternaModule: inicializado');
       
        this.configurarEventos();
    },

    
    configurarEventos() {
        const inputFile = document.getElementById('politica_interna_input');
        const btnAnexar = document.querySelector('.btn-anexar-politica');
        const btnSubstituir = document.querySelector('.btn-substituir-politica');
        const btnBaixar = document.querySelector('.btn-baixar-politica');
        const btnRemover = document.querySelector('.btn-remover-politica');
        
        // Anexar novo arquivo
        if (btnAnexar) {
            btnAnexar.addEventListener('click', () => {
                inputFile.click();
            });
        }
        
        // Substituir arquivo
        if (btnSubstituir) {
            btnSubstituir.addEventListener('click', () => {
                inputFile.click();
            });
        }
        
        // Input file change
        if (inputFile) {
            inputFile.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                // Validar tipo
                if (file.type !== 'application/pdf') {
                    mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
                    inputFile.value = '';
                    return;
                }
                
                // Validar tamanho
                if (file.size > 10 * 1024 * 1024) {
                    mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
                    inputFile.value = '';
                    return;
                }
                
                // Salvar arquivo
                this.arquivoPolitica = file;
                this.mostrarArquivoAnexado(file.name);
                
                mostrarToast('📎 Arquivo selecionado! Salve para enviar.', 'info');
            });
        }
        
        // Baixar arquivo
        if (btnBaixar) {
            btnBaixar.addEventListener('click', () => {
                this.baixarArquivo();
            });
        }
        
        // Remover arquivo
        if (btnRemover) {
            btnRemover.addEventListener('click', async () => {
                await this.removerArquivo();
            });
        }
    },
    
    mostrarArquivoAnexado(nomeArquivo) {
        const nenhumDiv = document.getElementById('politica_interna_nenhum');
        const anexadoDiv = document.getElementById('politica_interna_anexado');
        const nomeExibicao = document.getElementById('politica_interna_nome_exibicao');
        
        if (nenhumDiv) nenhumDiv.style.display = 'none';
        if (anexadoDiv) anexadoDiv.style.display = 'block';
        if (nomeExibicao) nomeExibicao.textContent = nomeArquivo;
    },
    
    mostrarNenhumArquivo() {
        const nenhumDiv = document.getElementById('politica_interna_nenhum');
        const anexadoDiv = document.getElementById('politica_interna_anexado');
        
        if (nenhumDiv) nenhumDiv.style.display = 'block';
        if (anexadoDiv) anexadoDiv.style.display = 'none';
    },
    
    async baixarArquivo() {
        try {
            // Se tem URL existente, baixar do bucket
            if (this.arquivoUrlExistente && this.arquivoUrlExistente.trim() !== '') {
                const response = await window.fetchComAutenticacao('/api/arquivo/url-assinada', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        caminho: this.arquivoUrlExistente, 
                        bucket: 'detalhamento_etapas' 
                    })
                });
                
                const data = await response.json();
                
                if (data.success && data.url) {
                    window.open(data.url, '_blank');
                    mostrarToast('📥 Download iniciado!', 'success');
                } else {
                    mostrarToast('❌ Erro ao gerar link de download', 'error');
                }
                return;
            }
            
            // Se tem arquivo novo (não salvo), baixar localmente
            if (this.arquivoPolitica) {
                const url = URL.createObjectURL(this.arquivoPolitica);
                const link = document.createElement('a');
                link.href = url;
                link.download = this.arquivoPolitica.name;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                setTimeout(() => URL.revokeObjectURL(url), 100);
                
                mostrarToast('📥 Download iniciado!', 'success');
                return;
            }
            
            mostrarToast('⚠️ Nenhum arquivo anexado', 'warning');
            
        } catch (error) {
            console.error('Erro ao baixar:', error);
            mostrarToast('❌ Erro ao baixar arquivo', 'error');
        }
    },
    
    async removerArquivo() {
        const etapaId = document.getElementById('modal-etapa-id').value;
        
        // Se tem URL existente e etapa salva, excluir do bucket
        if (this.arquivoUrlExistente && etapaId && etapaId !== '') {
            if (!confirm('Deseja remover o documento da política interna?')) return;
            
            try {
                mostrarToast('🗑️ Removendo arquivo...', 'info');
                
                const response = await fetchComAutenticacao('/api/arquivo/excluir', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        arquivo_url: this.arquivoUrlExistente,
                        bucket: 'detalhamento_etapas'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.arquivoUrlExistente = '';
                    this.arquivoNomeExistente = '';
                    this.arquivoPolitica = null;
                    this.mostrarNenhumArquivo();
                    
                    // Limpar input file
                    const inputFile = document.getElementById('politica_interna_input');
                    if (inputFile) inputFile.value = '';
                    
                    mostrarToast('✅ Arquivo removido!', 'success');
                } else {
                    mostrarToast('❌ Erro ao remover', 'error');
                }
            } catch (error) {
                console.error('Erro ao remover:', error);
                mostrarToast('❌ Erro de conexão', 'error');
            }
        } else {
            // Apenas limpar interface
            if (confirm('Deseja remover o arquivo anexado?')) {
                this.arquivoPolitica = null;
                this.mostrarNenhumArquivo();
                
                const inputFile = document.getElementById('politica_interna_input');
                if (inputFile) inputFile.value = '';
                
                mostrarToast('📎 Arquivo removido', 'info');
            }
        }
    },
    
    async carregarPoliticaInterna(url, nome) {
        if (url && nome) {
            this.arquivoUrlExistente = url;
            this.arquivoNomeExistente = nome;
            this.mostrarArquivoAnexado(nome);
        } else {
            this.arquivoUrlExistente = '';
            this.arquivoNomeExistente = '';
            this.mostrarNenhumArquivo();
        }
    },
    
    limpar() {
        this.arquivoPolitica = null;
        this.arquivoUrlExistente = '';
        this.arquivoNomeExistente = '';
        
        const inputFile = document.getElementById('politica_interna_input');
        if (inputFile) inputFile.value = '';
        
        this.mostrarNenhumArquivo();
    },
    
    async processarUpload(etapaId) {
        // Se tem arquivo novo para upload
        if (this.arquivoPolitica) {
            try {
                const formData = new FormData();
                formData.append('arquivo', this.arquivoPolitica);
                formData.append('tipo', 'politica_interna');
                formData.append('etapa_id', etapaId || 'temp');
                
                const response = await fetchComAutenticacao('/api/upload/detalhamento', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    return {
                        url: data.url || '',
                        nome: data.nome_arquivo || '',
                        tamanho: data.tamanho || 0
                    };
                } else {
                    mostrarToast(`⚠️ Erro ao enviar arquivo: ${data.error || 'Erro desconhecido'}`, 'warning');
                    return null;
                }
            } catch (error) {
                console.error('Erro no upload:', error);
                mostrarToast('⚠️ Erro ao enviar arquivo da política interna', 'warning');
                return null;
            }
        }
        
        // Se não tem arquivo novo, retornar existente
        if (this.arquivoUrlExistente) {
            return {
                url: this.arquivoUrlExistente,
                nome: this.arquivoNomeExistente,
                tamanho: 0
            };
        }
        
        return null;
    },

    async baixarArquivoPorUrl(url, nomeArquivo) {
        if (!url || url.trim() === '') {
            mostrarToast('⚠️ Nenhum arquivo anexado', 'warning');
            return;
        }
        
        try {
            const response = await window.fetchComAutenticacao('/api/arquivo/url-assinada', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    caminho: url, 
                    bucket: 'detalhamento_etapas' 
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.url) {
                window.open(data.url, '_blank');
                mostrarToast('📥 Download iniciado!', 'success');
            } else {
                mostrarToast('❌ Erro ao gerar link de download', 'error');
            }
        } catch (error) {
            console.error('Erro ao baixar:', error);
            mostrarToast('❌ Erro ao baixar arquivo', 'error');
        }
    }
    
};