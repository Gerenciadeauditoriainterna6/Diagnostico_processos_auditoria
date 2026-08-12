// ============================================================
// obrigacoes.js - MÓDULO DE OBRIGAÇÕES REGULATÓRIAS
// ============================================================

const ObrigacoesModule = {

    // Atributos (dados do módulo)
    arquivosObrigacoes: {},
    obrigacoesLista: [],

    // Métodos (funções do módulo)
    init() {
        console.log('📌 ObrigacoesModule: inicializado');
        
        // ⭐ Delegar eventos de clique para botões dentro do container
        const container = document.getElementById('obrigacoes-container');
        if (container) {
            container.addEventListener('click', (e) => {
                // Botão de excluir
                const btnExcluir = e.target.closest('.btn-remover-obrigacao');
                if (btnExcluir) {
                    const item = btnExcluir.closest('.obrigacao-item');
                    if (item) {
                        const indice = parseInt(item.getAttribute('data-index'));
                        this.excluirObrigacao(indice);
                    }
                }
                
                // ⭐ Botão de download
                const btnDownload = e.target.closest('.btn-download-arquivo');
                if (btnDownload) {
                    e.preventDefault();
                    this.baixarArquivoObrigacao(btnDownload);
                }
            });
        }
    },

    carregarObrigacoes(dadosJson) {
        if (!dadosJson) return;
        
        try {
            const dados = typeof dadosJson === 'string' ? JSON.parse(dadosJson) : dadosJson;
            
            if (!Array.isArray(dados) || dados.length === 0) {
                this.adicionarObrigacao();
                return;
            }
            
            dados.forEach((obrigacao) => {
                // Garantir que a estrutura está completa
                const dadosCompletos = {
                    prazo: obrigacao.prazo || '',
                    titulo: obrigacao.titulo || 'INEXISTENTE',
                    arquivo_url: obrigacao.arquivo_url || '',
                    obrigatorio: obrigacao.obrigatorio || false,
                    arquivo_nome: obrigacao.arquivo_nome || '',
                    arquivo_tamanho: obrigacao.arquivo_tamanho || 0,
                    orgao_regulador: obrigacao.orgao_regulador || '',
                    descricao_completa: obrigacao.descricao_completa || 'INEXISTENTE',
                    documento_necessario: obrigacao.documento_necessario || ''
                };
                this.adicionarObrigacao(dadosCompletos);
            });
        } catch (e) {
            console.error('Erro ao carregar obrigações:', e);
            this.adicionarObrigacao();
        }
    },

    // Adicionar nova obrigação
    adicionarObrigacao(dados = null) {
        const container = document.getElementById('obrigacoes-container');
        const template = document.getElementById('template-obrigacao');
        
        if (!container || !template) return;
        
        // Clonar o template
        const item = template.content.cloneNode(true);
        const div = item.querySelector('.obrigacao-item');
        
        // Gerar índice
        const index = container.querySelectorAll('.obrigacao-item').length;
        div.setAttribute('data-index', index);
        div.querySelector('.obrigacao-index').textContent = index + 1;
        
        // 🔥 SE TIVER DADOS, PREENCHER
        if (dados) {
            div.querySelector('.obrigacao-titulo').value = dados.titulo || '';
            div.querySelector('.obrigacao-orgao').value = dados.orgao_regulador || '';
            div.querySelector('.obrigacao-prazo').value = dados.prazo || '';
            div.querySelector('.obrigacao-obrigatorio').value = dados.obrigatorio ? 'true' : 'false';
            div.querySelector('.obrigacao-documento').value = dados.documento_necessario || '';
            
            // ⭐ SE TIVER ARQUIVO, MOSTRAR COM DOWNLOAD
            if (dados.arquivo_nome && dados.arquivo_url) {
                const infoDiv = div.querySelector('.obrigacao-arquivo-info');
                const nomeSpan = div.querySelector('.obrigacao-arquivo-nome');
                
                nomeSpan.textContent = dados.arquivo_nome;
                infoDiv.style.display = 'flex';
                
                // ⭐ ARMazenar URL no elemento para download
                infoDiv.setAttribute('data-arquivo-url', dados.arquivo_url);
                infoDiv.setAttribute('data-arquivo-nome', dados.arquivo_nome);
                div.setAttribute('data-arquivo-url', dados.arquivo_url);
                div.setAttribute('data-arquivo-nome', dados.arquivo_nome);
                
                // ⭐ Configurar botão de download
                const btnDownload = div.querySelector('.btn-download-arquivo');
                if (btnDownload) {
                    btnDownload.setAttribute('data-url', dados.arquivo_url);
                    btnDownload.setAttribute('data-nome', dados.arquivo_nome);
                }
            }
        }
        
        // Configurar upload
        const uploadArea = div.querySelector('.obrigacao-upload-area');
        const obrigatorioSelect = div.querySelector('.obrigacao-obrigatorio');
        
        uploadArea.style.display = 'block';
    
        // Configurar upload de arquivo
        const btnUpload = div.querySelector('.btn-upload-obrigacao');
        const inputFile = div.querySelector('.obrigacao-arquivo');
        const infoDiv = div.querySelector('.obrigacao-arquivo-info');
        const nomeSpan = div.querySelector('.obrigacao-arquivo-nome');
        const btnRemover = div.querySelector('.btn-remover-arquivo-obrigacao');
        
        if (btnUpload && inputFile) {
            btnUpload.addEventListener('click', () => {
                inputFile.click();
            });
            
            inputFile.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                if (file.type !== 'application/pdf') {
                    mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
                    inputFile.value = '';
                    return;
                }
                
                if (file.size > 10 * 1024 * 1024) {
                    mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
                    inputFile.value = '';
                    return;
                }
                
                // 🔥 SALVAR O ARQUIVO COMO FILE OBJETO (não converte para Base64)
                const idx = parseInt(div.getAttribute('data-index'));
                
                if (!this.arquivosObrigacoes[idx]) {
                    this.arquivosObrigacoes[idx] = {};
                }
                this.arquivosObrigacoes[idx] = {
                    file: file,
                    nome: file.name,
                    tamanho: file.size
                };
                
                nomeSpan.textContent = file.name;
                infoDiv.style.display = 'flex';
                
                // 🔥 REMOVER URL SALVA (se existia) para não confundir
                div.removeAttribute('data-arquivo-url');
                div.removeAttribute('data-arquivo-nome');
                infoDiv.removeAttribute('data-arquivo-url');
                infoDiv.removeAttribute('data-arquivo-nome');
                
                // 🔥 ATUALIZAR O BOTÃO DE DOWNLOAD PARA USAR O ARQUIVO LOCAL
                const btnDownload = div.querySelector('.btn-download-arquivo');
                if (btnDownload) {
                    btnDownload.removeAttribute('data-url');
                    btnDownload.removeAttribute('data-nome');
                }
                
                mostrarToast('📎 Arquivo selecionado! Salve para enviar.', 'info');
            });
        }
        
        // Dentro da função this.adicionarObrigacao(), no evento do btnRemover:

        if (btnRemover) {
            btnRemover.addEventListener('click', async () => {
                const inputFile = div.querySelector('.obrigacao-arquivo');
                const infoDiv = div.querySelector('.obrigacao-arquivo-info');
                const nomeSpan = div.querySelector('.obrigacao-arquivo-nome');
                const idx = parseInt(div.getAttribute('data-index'));
                
                // Verificar se tem URL salva (arquivo já foi enviado para o storage)
                const urlSalva = div.getAttribute('data-arquivo-url');
                const etapaId = document.getElementById('modal-etapa-id').value;
                
                // 🔥 Se tem URL salva e a etapa já está salva, excluir do storage
                if (urlSalva && urlSalva.trim() !== '' && etapaId && etapaId !== '') {
                    if (confirm('Deseja remover apenas o arquivo anexado?')) {
                        try {
                            mostrarToast('🗑️ Removendo arquivo...', 'info');
                            
                            const response = await fetchComAutenticacao('/api/obrigacao/remover-arquivo', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    etapa_id: parseInt(etapaId),
                                    indice: idx,
                                    arquivo_url: urlSalva
                                })
                            });
                            
                            const data = await response.json();
                            
                            if (data.success) {
                                // Limpar a interface
                                inputFile.value = '';
                                infoDiv.style.display = 'none';
                                infoDiv.removeAttribute('data-arquivo-url');
                                infoDiv.removeAttribute('data-arquivo-nome');
                                nomeSpan.textContent = '';
                                div.removeAttribute('data-arquivo-url');
                                div.removeAttribute('data-arquivo-nome');
                                
                                // Limpar do objeto this.arquivosObrigacoes se existir
                                if (this.arquivosObrigacoes[idx]) {
                                    delete this.arquivosObrigacoes[idx];
                                }
                                
                                mostrarToast('✅ Arquivo removido com sucesso!', 'success');
                            } else {
                                mostrarToast('❌ Erro ao remover arquivo: ' + (data.error || 'Tente novamente'), 'error');
                            }
                        } catch (error) {
                            console.error('Erro ao remover arquivo:', error);
                            mostrarToast('❌ Erro ao conectar com o servidor', 'error');
                        }
                    }
                } else {
                    // Se não tem URL salva (arquivo local, não salvo), apenas limpar a interface
                    inputFile.value = '';
                    infoDiv.style.display = 'none';
                    infoDiv.removeAttribute('data-arquivo-url');
                    infoDiv.removeAttribute('data-arquivo-nome');
                    nomeSpan.textContent = '';
                    div.removeAttribute('data-arquivo-url');
                    div.removeAttribute('data-arquivo-nome');
                    
                    if (this.arquivosObrigacoes[idx]) {
                        delete this.arquivosObrigacoes[idx];
                    }
                    
                    mostrarToast('📎 Arquivo removido', 'info');
                }
            });
        }
        
        
        // 🔥 IMPORTANTE: container.appendChild(div) DEVE ESTAR AQUI, FORA DO EVENTO
        container.appendChild(div);
    },

    // Coletar dados das obrigações para salvar
    coletarObrigacoes() {
        const items = document.querySelectorAll('.obrigacao-item');
        const obrigacoes = [];
        
        for (const item of items) {
            const titulo = item.querySelector('.obrigacao-titulo').value.trim();
            const index = parseInt(item.getAttribute('data-index'));
            
            // 🔥 ESTRUTURA FIXA COM TODOS OS CAMPOS
            const obrigacao = {
                prazo: item.querySelector('.obrigacao-prazo').value || '',
                titulo: titulo || 'INEXISTENTE',
                arquivo_url: '',
                obrigatorio: item.querySelector('.obrigacao-obrigatorio').value === 'true',
                arquivo_nome: '',
                arquivo_tamanho: 0,
                orgao_regulador: item.querySelector('.obrigacao-orgao').value.trim() || '',
                descricao_completa: 'INEXISTENTE',
                documento_necessario: item.querySelector('.obrigacao-documento').value.trim() || ''
            };
            
            // Verificar se tem arquivo novo para upload
            if (this.arquivosObrigacoes[index] && this.arquivosObrigacoes[index].file) {
                obrigacao._upload_file = true;
                obrigacao._file_data = this.arquivosObrigacoes[index];
                obrigacao._index = index;
            } else if (item.getAttribute('data-arquivo-url')) {
                // Arquivo já existe (referência salva)
                obrigacao.arquivo_url = item.getAttribute('data-arquivo-url');
                obrigacao.arquivo_nome = item.getAttribute('data-arquivo-nome');
                obrigacao.arquivo_tamanho = parseInt(item.getAttribute('data-arquivo-tamanho')) || 0;
            }
            
            obrigacoes.push(obrigacao);
        }
        
        return obrigacoes;
    },

    // Limpar obrigações (usado ao fechar modal)
    limparObrigacoes() {
        const container = document.getElementById('obrigacoes-container');
        if (container) {
            container.innerHTML = '';
        }
        this.arquivosObrigacoes = {};
    },

    // Inicializar obrigações no modal (chamar ao abrir)
    inicializarObrigacoes(dadosJson) {
        this.limparObrigacoes();
        if (dadosJson) {
            this.carregarObrigacoes(dadosJson);
        } else {
            // Adicionar uma obrigação vazia
            this.adicionarObrigacao();
        }
    },

    baixarArquivoObrigacao(botao) {
        // Buscar os elementos
        const itemDiv = botao.closest('.obrigacao-item');
        const infoDiv = botao.closest('.obrigacao-arquivo-info') || itemDiv?.querySelector('.obrigacao-arquivo-info');
        
        if (!itemDiv) {
            mostrarToast('⚠️ Erro: elemento não encontrado', 'error');
            return;
        }
        
        const index = parseInt(itemDiv.getAttribute('data-index'));
        
        // Verificar se tem URL salva (arquivo já foi salvo no bucket)
        const urlSalva = itemDiv.getAttribute('data-arquivo-url');
        const nomeSalvo = itemDiv.getAttribute('data-arquivo-nome');
        
        // Verificar se tem arquivo novo (anexado mas não salvo)
        const arquivoNovo = this.arquivosObrigacoes[index]?.file;
        const nomeNovo = this.arquivosObrigacoes[index]?.nome;
        
        // 🔥 PRIORIDADE: Se tem URL salva, baixar do bucket
        if (urlSalva && urlSalva.trim() !== '') {
            this._baixarComUrlAssinada(urlSalva);
            mostrarToast('📥 Download iniciado!', 'success');
            return;
        }
        
        // 🔥 Se não tem URL, mas tem arquivo novo, baixar localmente
        if (arquivoNovo) {
            this.baixarArquivoLocal(arquivoNovo, nomeNovo || 'documento.pdf');
            return;
        }
        
        // Se chegou aqui, não tem arquivo
        mostrarToast('⚠️ Nenhum arquivo anexado a esta obrigação', 'warning');
    },

    baixarArquivoLocal(file, nomeArquivo) {
        if (!file) {
            mostrarToast('⚠️ Nenhum arquivo disponível para download', 'warning');
            return;
        }
        
        try {
            // Criar URL para o objeto File
            const url = URL.createObjectURL(file);
            
            // Criar link para download
            const link = document.createElement('a');
            link.href = url;
            link.download = nomeArquivo || file.name || 'documento.pdf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Liberar URL após o download
            setTimeout(() => {
                URL.revokeObjectURL(url);
            }, 100);
            
            mostrarToast('📥 Download do arquivo local iniciado!', 'success');
        } catch (error) {
            console.error('Erro ao baixar arquivo local:', error);
            mostrarToast('❌ Erro ao baixar arquivo', 'error');
        }
    },

    baixarArquivoObrigacaoPorUrl(url, nomeArquivo) {
        if (!url || url.trim() === '') {
            mostrarToast('⚠️ Nenhum arquivo anexado', 'warning');
            return;
        }
        
        window.open(url, '_blank');
        mostrarToast('📥 Download iniciado!', 'success');
    },

    async excluirObrigacao(indice) {
        const items = document.querySelectorAll('.obrigacao-item');
        if (indice >= items.length) {
            window.mostrarToast('⚠️ Obrigação não encontrada', 'warning');
            return;
        }
        
        const item = items[indice];
        const titulo = item.querySelector('.obrigacao-titulo').value.trim() || 'Obrigação';
        
        if (!confirm(`Tem certeza que deseja excluir "${titulo}"?`)) return;
        
        const etapaId = document.getElementById('modal-etapa-id').value;
        const arquivoUrl = item.getAttribute('data-arquivo-url');
        
        // ⭐ Verificar se a obrigação TEM dados salvos (já foi salva antes)
        const tituloSalvo = item.querySelector('.obrigacao-titulo').value.trim();
        const temUrlSalva = arquivoUrl && arquivoUrl.trim() !== '';
        const obrigacaoJaExisteNoBanco = (etapaId && etapaId !== '') && (tituloSalvo || temUrlSalva);
        
        if (obrigacaoJaExisteNoBanco) {
            // ⭐ Já foi salva → excluir do banco e storage
            try {
                window.mostrarToast('🗑️ Excluindo obrigação...', 'info');
                
                const response = await window.fetchComAutenticacao('/api/obrigacao/excluir', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        etapa_id: parseInt(etapaId),
                        indice: indice,
                        arquivo_url: arquivoUrl || ''
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    item.remove();
                    this._reindexar();
                    delete this.arquivosObrigacoes[indice];
                    window.mostrarToast('✅ Obrigação excluída!', 'success');
                } else {
                    window.mostrarToast('❌ ' + (data.error || 'Erro'), 'error');
                }
            } catch (error) {
                window.mostrarToast('❌ Erro de conexão', 'error');
            }
        } else {
            // ⭐ NUNCA foi salva → apenas remover do frontend
            item.remove();
            this._reindexar();
            delete this.arquivosObrigacoes[indice];
            window.mostrarToast('🗑️ Obrigação removida', 'info');
        }
    },

    _reindexar() {
        document.querySelectorAll('.obrigacao-item').forEach((el, i) => {
            el.setAttribute('data-index', i);
            const idxSpan = el.querySelector('.obrigacao-index');
            if (idxSpan) idxSpan.textContent = i + 1;
        });
        
        const novo = {};
        document.querySelectorAll('.obrigacao-item').forEach((el, i) => {
            const idx = parseInt(el.getAttribute('data-index'));
            if (this.arquivosObrigacoes[idx]) {
                novo[i] = this.arquivosObrigacoes[idx];
            }
        });
        this.arquivosObrigacoes = novo;
    },

    async processarUploadsObrigacoes(obrigacoes, etapaId) {
        const obrigacoesProcessadas = [];
        
        for (const obrigacao of obrigacoes) {
            // Se tiver arquivo para upload
            if (obrigacao._upload_file && obrigacao._file_data) {
                try {
                    const formData = new FormData();
                    formData.append('arquivo', obrigacao._file_data.file);
                    formData.append('tipo', 'obrigacao');
                    formData.append('etapa_id', etapaId || 'temp');
                    formData.append('titulo_obrigacao', obrigacao.titulo);
                    
                    const response = await fetchComAutenticacao('/api/upload/detalhamento', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // ✅ PREENCHER OS CAMPOS CORRETOS
                        obrigacao.arquivo_url = data.url || '';
                        obrigacao.arquivo_nome = data.nome_arquivo || '';
                        obrigacao.arquivo_tamanho = data.tamanho || 0;
                    } else {
                        mostrarToast(`⚠️ Erro ao enviar arquivo: ${data.error || 'Erro desconhecido'}`, 'warning');
                    }
                } catch (error) {
                    console.error('Erro no upload:', error);
                    mostrarToast('⚠️ Erro ao enviar arquivo da obrigação', 'warning');
                }
            }
            
            // Remover campos temporários
            delete obrigacao._upload_file;
            delete obrigacao._file_data;
            delete obrigacao._index;
            
            // Garantir que todos os campos existam
            if (!obrigacao.titulo) obrigacao.titulo = 'INEXISTENTE';
            if (!obrigacao.descricao_completa) obrigacao.descricao_completa = 'INEXISTENTE';
            
            obrigacoesProcessadas.push(obrigacao);
        }
        
        return obrigacoesProcessadas;
    },

    async _baixarComUrlAssinada(caminho) {
        try {
            // ⭐ ESTA é a nova chamada!
            const response = await window.fetchComAutenticacao('/api/arquivo/url-assinada', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ caminho: caminho, bucket: 'detalhamento_etapas' })
            });
            
            const data = await response.json();
            
            if (data.success && data.url) {
                window.open(data.url, '_blank');
                window.mostrarToast('📥 Download iniciado!', 'success');
            } else {
                window.mostrarToast('❌ Erro ao gerar link de download', 'error');
            }
        } catch (error) {
            window.mostrarToast('❌ Erro de conexão', 'error');
        }
    },

}
    
