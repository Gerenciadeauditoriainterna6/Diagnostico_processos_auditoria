// ============================================================
// politicas_obrigacoes.js - MÓDULO DE POLÍTICAS E OBRIGAÇÕES
// ============================================================

const PoliticasObrigacoesModule = {

    // Atributos (dados do módulo)
    arquivosPoliticas: {},
    arquivosObrigacoes: {},
    politicasLista: [],

    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================
    init() {
        console.log('📌 PoliticasObrigacoesModule: inicializado');
        
        const container = document.getElementById('politicas-obrigacoes-container');
        if (container) {
            container.addEventListener('click', (e) => {
                // Botão remover política
                const btnRemoverPolitica = e.target.closest('.btn-remover-politica');
                if (btnRemoverPolitica) {
                    const item = btnRemoverPolitica.closest('.politica-item');
                    if (item) {
                        const indice = parseInt(item.getAttribute('data-index'));
                        this.excluirPolitica(indice);
                    }
                    return;
                }
                
                // Botão adicionar obrigação
                const btnAdicionarObrigacao = e.target.closest('.btn-adicionar-obrigacao');
                if (btnAdicionarObrigacao) {
                    const item = btnAdicionarObrigacao.closest('.politica-item');
                    if (item) {
                        const indice = parseInt(item.getAttribute('data-index'));
                        this.adicionarObrigacao(indice);
                    }
                    return;
                }
                
                // Botão remover obrigação
                const btnRemoverObrigacao = e.target.closest('.btn-remover-obrigacao');
                if (btnRemoverObrigacao) {
                    const itemPolitica = btnRemoverObrigacao.closest('.politica-item');
                    const itemObrigacao = btnRemoverObrigacao.closest('.obrigacao-item');
                    if (itemPolitica && itemObrigacao) {
                        const politicaIdx = parseInt(itemPolitica.getAttribute('data-index'));
                        const obrigacaoIdx = parseInt(itemObrigacao.getAttribute('data-index'));
                        this.excluirObrigacao(politicaIdx, obrigacaoIdx);
                    }
                    return;
                }
                
                // Botão upload política
                const btnUploadPolitica = e.target.closest('.btn-upload-politica');
                if (btnUploadPolitica) {
                    const item = btnUploadPolitica.closest('.politica-item');
                    if (item) {
                        const inputFile = item.querySelector('.politica-arquivo');
                        if (inputFile) inputFile.click();
                    }
                    return;
                }
                
                // Botão upload obrigação
                const btnUploadObrigacao = e.target.closest('.btn-upload-obrigacao');
                if (btnUploadObrigacao) {
                    const item = btnUploadObrigacao.closest('.obrigacao-item');
                    if (item) {
                        const inputFile = item.querySelector('.obrigacao-arquivo');
                        if (inputFile) inputFile.click();
                    }
                    return;
                }
                
                // Botão baixar arquivo da política
                const btnBaixarPolitica = e.target.closest('.btn-baixar-politica-arquivo');
                if (btnBaixarPolitica) {
                    const item = btnBaixarPolitica.closest('.politica-item');
                    if (item) this.baixarArquivoPolitica(item);
                    return;
                }
                
                // Botão baixar arquivo da obrigação
                const btnBaixarObrigacao = e.target.closest('.btn-baixar-obrigacao-arquivo');
                if (btnBaixarObrigacao) {
                    const item = btnBaixarObrigacao.closest('.obrigacao-item');
                    if (item) this.baixarArquivoObrigacao(item);
                    return;
                }
                
                // Botão remover arquivo da política
                const btnRemoverArquivoPolitica = e.target.closest('.btn-remover-politica-arquivo');
                if (btnRemoverArquivoPolitica) {
                    const item = btnRemoverArquivoPolitica.closest('.politica-item');
                    if (item) this.removerArquivoPolitica(item);
                    return;
                }
                
                // Botão remover arquivo da obrigação
                const btnRemoverArquivoObrigacao = e.target.closest('.btn-remover-obrigacao-arquivo');
                if (btnRemoverArquivoObrigacao) {
                    const item = btnRemoverArquivoObrigacao.closest('.obrigacao-item');
                    if (item) this.removerArquivoObrigacao(item);
                    return;
                }
            });
            
            // Eventos de mudança (upload)
            container.addEventListener('change', (e) => {
                if (e.target.classList.contains('politica-arquivo')) {
                    const item = e.target.closest('.politica-item');
                    if (item) this.handleUploadPolitica(item, e.target);
                }
                
                if (e.target.classList.contains('obrigacao-arquivo')) {
                    const item = e.target.closest('.obrigacao-item');
                    if (item) this.handleUploadObrigacao(item, e.target);
                }
            });
        }
        
        // Botão adicionar política
        const btnAdicionarPolitica = document.getElementById('btn-adicionar-politica');
        if (btnAdicionarPolitica) {
            btnAdicionarPolitica.addEventListener('click', () => {
                this.adicionarPolitica();
            });
        }
    },

    // ============================================================
    // ADICIONAR POLÍTICA
    // ============================================================
    adicionarPolitica(dados = null) {
        const container = document.getElementById('politicas-obrigacoes-container');
        const template = document.getElementById('template-politica');

        if (!container || !template) return;

        const item = template.content.cloneNode(true);
        const div = item.querySelector('.politica-item');

        const index = container.querySelectorAll('.politica-item').length;
        div.setAttribute('data-index', index);
        div.querySelector('.politica-index').textContent = index + 1;

        if (dados) {
            div.querySelector('.politica-titulo').value = dados.titulo || '';
            div.querySelector('.politica-tipo').value = dados.tipo || 'interna';

            if (dados.arquivo_url && dados.arquivo_nome) {
                const infoDiv = div.querySelector('.politica-arquivo-info');
                const nomeSpan = div.querySelector('.politica-arquivo-nome');

                nomeSpan.textContent = dados.arquivo_nome;
                infoDiv.style.display = 'flex';

                div.setAttribute('data-arquivo-url', dados.arquivo_url);
                div.setAttribute('data-arquivo-nome', dados.arquivo_nome);
            }

            if (dados.obrigacoes && dados.obrigacoes.length > 0) {
                const obrigacoesLista = div.querySelector('.obrigacoes-lista');
                dados.obrigacoes.forEach(obrigacao => {
                    this._adicionarObrigacaoNaLista(obrigacoesLista, obrigacao);
                });
            }
        }

        container.appendChild(div);
    },

    // ============================================================
    // ADICIONAR OBRIGAÇÃO (chamado pelo botão)
    // ============================================================
    adicionarObrigacao(politicaIdx, dados = null) {
        const container = document.getElementById('politicas-obrigacoes-container');
        const politicaItem = container.querySelectorAll('.politica-item')[politicaIdx];

        if (!politicaItem) return;

        const obrigacoesLista = politicaItem.querySelector('.obrigacoes-lista');
        this._adicionarObrigacaoNaLista(obrigacoesLista, dados);
    },

    // ============================================================
    // ADICIONAR OBRIGAÇÃO NA LISTA (função interna)
    // ============================================================
    _adicionarObrigacaoNaLista(obrigacoesLista, dados = null) {
        const template = document.getElementById('template-obrigacao-politica');
        if (!obrigacoesLista || !template) return;

        const item = template.content.cloneNode(true);
        const div = item.querySelector('.obrigacao-item');

        const index = obrigacoesLista.querySelectorAll('.obrigacao-item').length;
        div.setAttribute('data-index', index);
        div.querySelector('.obrigacao-index').textContent = index + 1;

        if (dados) {
            div.querySelector('.obrigacao-titulo').value = dados.titulo || '';
            div.querySelector('.obrigacao-orgao').value = dados.orgao_regulador || '';
            div.querySelector('.obrigacao-prazo').value = dados.prazo || '';
            div.querySelector('.obrigacao-obrigatorio').value = dados.obrigatorio ? 'true' : 'false';
            div.querySelector('.obrigacao-documento').value = dados.documento_necessario || '';
            
            if (dados.arquivo_url && dados.arquivo_nome) {
                const infoDiv = div.querySelector('.obrigacao-arquivo-info');
                const nomeSpan = div.querySelector('.obrigacao-arquivo-nome');

                nomeSpan.textContent = dados.arquivo_nome;
                infoDiv.style.display = 'flex';

                div.setAttribute('data-arquivo-url', dados.arquivo_url);
                div.setAttribute('data-arquivo-nome', dados.arquivo_nome);
            }
        }

        obrigacoesLista.appendChild(div);
    },

    // ============================================================
    // HANDLE UPLOAD - POLÍTICA
    // ============================================================
    handleUploadPolitica(item, inputFile) {
        const file = inputFile.files[0];
        if (!file) return;
        
        if (file.type !== 'application/pdf') {
            window.mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
            inputFile.value = '';
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            window.mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
            inputFile.value = '';
            return;
        }
        
        const indice = parseInt(item.getAttribute('data-index'));
        
        this.arquivosPoliticas[indice] = {
            file: file,
            nome: file.name,
            tamanho: file.size
        };
        
        const infoDiv = item.querySelector('.politica-arquivo-info');
        const nomeSpan = item.querySelector('.politica-arquivo-nome');
        
        nomeSpan.textContent = file.name;
        infoDiv.style.display = 'flex';
        
        item.removeAttribute('data-arquivo-url');
        item.removeAttribute('data-arquivo-nome');
        
        window.mostrarToast('📎 Arquivo selecionado! Salve para enviar.', 'info');
    },
    
    // ============================================================
    // HANDLE UPLOAD - OBRIGAÇÃO
    // ============================================================
    handleUploadObrigacao(item, inputFile) {
        const file = inputFile.files[0];
        if (!file) return;
        
        if (file.type !== 'application/pdf') {
            window.mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
            inputFile.value = '';
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            window.mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
            inputFile.value = '';
            return;
        }
        
        const politicaItem = item.closest('.politica-item');
        const politicaIdx = parseInt(politicaItem.getAttribute('data-index'));
        const obrigacaoIdx = parseInt(item.getAttribute('data-index'));
        
        if (!this.arquivosObrigacoes[politicaIdx]) {
            this.arquivosObrigacoes[politicaIdx] = {};
        }
        this.arquivosObrigacoes[politicaIdx][obrigacaoIdx] = {
            file: file,
            nome: file.name,
            tamanho: file.size
        };
        
        const infoDiv = item.querySelector('.obrigacao-arquivo-info');
        const nomeSpan = item.querySelector('.obrigacao-arquivo-nome');
        
        nomeSpan.textContent = file.name;
        infoDiv.style.display = 'flex';
        
        item.removeAttribute('data-arquivo-url');
        item.removeAttribute('data-arquivo-nome');
        
        window.mostrarToast('📎 Arquivo selecionado! Salve para enviar.', 'info');
    },

    // ============================================================
    // BAIXAR ARQUIVO - POLÍTICA
    // ============================================================
    baixarArquivoPolitica(item) {
        const indice = parseInt(item.getAttribute('data-index'));
        
        const urlSalva = item.getAttribute('data-arquivo-url');
        const arquivoNovo = this.arquivosPoliticas[indice]?.file;
        const nomeNovo = this.arquivosPoliticas[indice]?.nome;
        
        if (urlSalva && urlSalva.trim() !== '') {
            this._baixarComUrlAssinada(urlSalva);
            window.mostrarToast('📥 Download iniciado!', 'success');
            return;
        }
        
        if (arquivoNovo) {
            this.baixarArquivoLocal(arquivoNovo, nomeNovo || 'documento.pdf');
            return;
        }
        
        window.mostrarToast('⚠️ Nenhum arquivo anexado a esta política', 'warning');
    },
    
    // ============================================================
    // BAIXAR ARQUIVO - OBRIGAÇÃO
    // ============================================================
    baixarArquivoObrigacao(item) {
        const politicaItem = item.closest('.politica-item');
        const politicaIdx = parseInt(politicaItem.getAttribute('data-index'));
        const obrigacaoIdx = parseInt(item.getAttribute('data-index'));
        
        const urlSalva = item.getAttribute('data-arquivo-url');
        const arquivoNovo = this.arquivosObrigacoes[politicaIdx]?.[obrigacaoIdx]?.file;
        const nomeNovo = this.arquivosObrigacoes[politicaIdx]?.[obrigacaoIdx]?.nome;
        
        if (urlSalva && urlSalva.trim() !== '') {
            this._baixarComUrlAssinada(urlSalva);
            window.mostrarToast('📥 Download iniciado!', 'success');
            return;
        }
        
        if (arquivoNovo) {
            this.baixarArquivoLocal(arquivoNovo, nomeNovo || 'documento.pdf');
            return;
        }
        
        window.mostrarToast('⚠️ Nenhum arquivo anexado a esta obrigação', 'warning');
    },
    
    // ============================================================
    // REMOVER ARQUIVO - POLÍTICA
    // ============================================================
    async removerArquivoPolitica(item) {
        const indice = parseInt(item.getAttribute('data-index'));
        const urlSalva = item.getAttribute('data-arquivo-url');
        const etapaId = document.getElementById('modal-etapa-id').value;
        
        if (urlSalva && urlSalva.trim() !== '' && etapaId && etapaId !== '') {
            if (!confirm('Deseja remover o arquivo da política?')) return;
            
            try {
                window.mostrarToast('🗑️ Removendo arquivo...', 'info');
                
                const response = await fetchComAutenticacao('/api/arquivo/excluir', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        arquivo_url: urlSalva,
                        bucket: 'detalhamento_etapas'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const inputFile = item.querySelector('.politica-arquivo');
                    const infoDiv = item.querySelector('.politica-arquivo-info');
                    const nomeSpan = item.querySelector('.politica-arquivo-nome');
                    
                    if (inputFile) inputFile.value = '';
                    if (infoDiv) infoDiv.style.display = 'none';
                    if (nomeSpan) nomeSpan.textContent = '';
                    
                    item.removeAttribute('data-arquivo-url');
                    item.removeAttribute('data-arquivo-nome');
                    
                    delete this.arquivosPoliticas[indice];
                    
                    window.mostrarToast('✅ Arquivo removido!', 'success');
                } else {
                    window.mostrarToast('❌ Erro ao remover arquivo', 'error');
                }
            } catch (error) {
                console.error('Erro ao remover:', error);
                window.mostrarToast('❌ Erro de conexão', 'error');
            }
        } else {
            if (!confirm('Deseja remover o arquivo?')) return;
            
            const inputFile = item.querySelector('.politica-arquivo');
            const infoDiv = item.querySelector('.politica-arquivo-info');
            const nomeSpan = item.querySelector('.politica-arquivo-nome');
            
            if (inputFile) inputFile.value = '';
            if (infoDiv) infoDiv.style.display = 'none';
            if (nomeSpan) nomeSpan.textContent = '';
            
            item.removeAttribute('data-arquivo-url');
            item.removeAttribute('data-arquivo-nome');
            
            delete this.arquivosPoliticas[indice];
            
            window.mostrarToast('📎 Arquivo removido', 'info');
        }
    },
    
    // ============================================================
    // REMOVER ARQUIVO - OBRIGAÇÃO
    // ============================================================
    async removerArquivoObrigacao(item) {
        const politicaItem = item.closest('.politica-item');
        const politicaIdx = parseInt(politicaItem.getAttribute('data-index'));
        const obrigacaoIdx = parseInt(item.getAttribute('data-index'));
        
        const urlSalva = item.getAttribute('data-arquivo-url');
        const etapaId = document.getElementById('modal-etapa-id').value;
        
        if (urlSalva && urlSalva.trim() !== '' && etapaId && etapaId !== '') {
            if (!confirm('Deseja remover o arquivo da obrigação?')) return;
            
            try {
                window.mostrarToast('🗑️ Removendo arquivo...', 'info');
                
                const response = await fetchComAutenticacao('/api/arquivo/excluir', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        arquivo_url: urlSalva,
                        bucket: 'detalhamento_etapas'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const inputFile = item.querySelector('.obrigacao-arquivo');
                    const infoDiv = item.querySelector('.obrigacao-arquivo-info');
                    const nomeSpan = item.querySelector('.obrigacao-arquivo-nome');
                    
                    if (inputFile) inputFile.value = '';
                    if (infoDiv) infoDiv.style.display = 'none';
                    if (nomeSpan) nomeSpan.textContent = '';
                    
                    item.removeAttribute('data-arquivo-url');
                    item.removeAttribute('data-arquivo-nome');
                    
                    if (this.arquivosObrigacoes[politicaIdx]) {
                        delete this.arquivosObrigacoes[politicaIdx][obrigacaoIdx];
                    }
                    
                    window.mostrarToast('✅ Arquivo removido!', 'success');
                } else {
                    window.mostrarToast('❌ Erro ao remover arquivo', 'error');
                }
            } catch (error) {
                console.error('Erro ao remover:', error);
                window.mostrarToast('❌ Erro de conexão', 'error');
            }
        } else {
            if (!confirm('Deseja remover o arquivo?')) return;
            
            const inputFile = item.querySelector('.obrigacao-arquivo');
            const infoDiv = item.querySelector('.obrigacao-arquivo-info');
            const nomeSpan = item.querySelector('.obrigacao-arquivo-nome');
            
            if (inputFile) inputFile.value = '';
            if (infoDiv) infoDiv.style.display = 'none';
            if (nomeSpan) nomeSpan.textContent = '';
            
            item.removeAttribute('data-arquivo-url');
            item.removeAttribute('data-arquivo-nome');
            
            if (this.arquivosObrigacoes[politicaIdx]) {
                delete this.arquivosObrigacoes[politicaIdx][obrigacaoIdx];
            }
            
            window.mostrarToast('📎 Arquivo removido', 'info');
        }
    },

    // ============================================================
    // EXCLUIR POLÍTICA
    // ============================================================
    async excluirPolitica(indice) {
        const container = document.getElementById('politicas-obrigacoes-container');
        const items = container.querySelectorAll('.politica-item');
        
        if (indice >= items.length) {
            window.mostrarToast('⚠️ Política não encontrada', 'warning');
            return;
        }
        
        const item = items[indice];
        const titulo = item.querySelector('.politica-titulo').value.trim() || 'Política';
        
        if (!confirm(`Tem certeza que deseja excluir "${titulo}"?`)) return;
        
        const etapaId = document.getElementById('modal-etapa-id').value;
        const temArquivoPolitica = item.getAttribute('data-arquivo-url');
        const temArquivosObrigacoes = item.querySelectorAll('.obrigacao-item[data-arquivo-url]').length > 0;
        
        if ((temArquivoPolitica || temArquivosObrigacoes) && etapaId && etapaId !== '') {
            try {
                window.mostrarToast('🗑️ Excluindo política...', 'info');
                
                if (temArquivoPolitica) {
                    await fetchComAutenticacao('/api/arquivo/excluir', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            arquivo_url: temArquivoPolitica,
                            bucket: 'detalhamento_etapas'
                        })
                    });
                }
                
                const obrigacoesComArquivo = item.querySelectorAll('.obrigacao-item[data-arquivo-url]');
                for (const obrigacaoItem of obrigacoesComArquivo) {
                    const url = obrigacaoItem.getAttribute('data-arquivo-url');
                    if (url) {
                        await fetchComAutenticacao('/api/arquivo/excluir', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                arquivo_url: url,
                                bucket: 'detalhamento_etapas'
                            })
                        });
                    }
                }
                
                item.remove();
                this._reindexarPoliticas();
                
                delete this.arquivosPoliticas[indice];
                delete this.arquivosObrigacoes[indice];
                
                window.mostrarToast('✅ Política excluída!', 'success');
                
            } catch (error) {
                console.error('Erro ao excluir:', error);
                window.mostrarToast('❌ Erro de conexão', 'error');
            }
        } else {
            item.remove();
            this._reindexarPoliticas();
            
            delete this.arquivosPoliticas[indice];
            delete this.arquivosObrigacoes[indice];
            
            window.mostrarToast('🗑️ Política removida', 'info');
        }
    },
    
    // ============================================================
    // EXCLUIR OBRIGAÇÃO
    // ============================================================
    async excluirObrigacao(politicaIdx, obrigacaoIdx) {
        const container = document.getElementById('politicas-obrigacoes-container');
        const politicaItem = container.querySelectorAll('.politica-item')[politicaIdx];
        
        if (!politicaItem) {
            window.mostrarToast('⚠️ Política não encontrada', 'warning');
            return;
        }
        
        const obrigacoesLista = politicaItem.querySelector('.obrigacoes-lista');
        const items = obrigacoesLista.querySelectorAll('.obrigacao-item');
        
        if (obrigacaoIdx >= items.length) {
            window.mostrarToast('⚠️ Obrigação não encontrada', 'warning');
            return;
        }
        
        const item = items[obrigacaoIdx];
        const titulo = item.querySelector('.obrigacao-titulo').value.trim() || 'Obrigação';
        
        if (!confirm(`Tem certeza que deseja excluir "${titulo}"?`)) return;
        
        const etapaId = document.getElementById('modal-etapa-id').value;
        const arquivoUrl = item.getAttribute('data-arquivo-url');
        
        if (arquivoUrl && etapaId && etapaId !== '') {
            try {
                window.mostrarToast('🗑️ Excluindo obrigação...', 'info');
                
                await fetchComAutenticacao('/api/arquivo/excluir', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        arquivo_url: arquivoUrl,
                        bucket: 'detalhamento_etapas'
                    })
                });
                
                item.remove();
                this._reindexarObrigacoes(politicaItem);
                
                if (this.arquivosObrigacoes[politicaIdx]) {
                    delete this.arquivosObrigacoes[politicaIdx][obrigacaoIdx];
                }
                
                window.mostrarToast('✅ Obrigação excluída!', 'success');
                
            } catch (error) {
                console.error('Erro ao excluir:', error);
                window.mostrarToast('❌ Erro de conexão', 'error');
            }
        } else {
            item.remove();
            this._reindexarObrigacoes(politicaItem);
            
            if (this.arquivosObrigacoes[politicaIdx]) {
                delete this.arquivosObrigacoes[politicaIdx][obrigacaoIdx];
            }
            
            window.mostrarToast('🗑️ Obrigação removida', 'info');
        }
    },
    
    // ============================================================
    // REINDEXAR POLÍTICAS
    // ============================================================
    _reindexarPoliticas() {
        const container = document.getElementById('politicas-obrigacoes-container');
        const items = container.querySelectorAll('.politica-item');
        
        items.forEach((el, i) => {
            el.setAttribute('data-index', i);
            el.querySelector('.politica-index').textContent = i + 1;
        });
        
        const novoPoliticas = {};
        items.forEach((el, i) => {
            if (this.arquivosPoliticas[i]) {
                novoPoliticas[i] = this.arquivosPoliticas[i];
            }
        });
        this.arquivosPoliticas = novoPoliticas;
    },
    
    // ============================================================
    // REINDEXAR OBRIGAÇÕES
    // ============================================================
    _reindexarObrigacoes(politicaItem) {
        const politicaIdx = parseInt(politicaItem.getAttribute('data-index'));
        const obrigacoesLista = politicaItem.querySelector('.obrigacoes-lista');
        const items = obrigacoesLista.querySelectorAll('.obrigacao-item');
        
        items.forEach((el, i) => {
            el.setAttribute('data-index', i);
            el.querySelector('.obrigacao-index').textContent = i + 1;
        });
        
        if (this.arquivosObrigacoes[politicaIdx]) {
            const novo = {};
            items.forEach((el, i) => {
                if (this.arquivosObrigacoes[politicaIdx][i]) {
                    novo[i] = this.arquivosObrigacoes[politicaIdx][i];
                }
            });
            this.arquivosObrigacoes[politicaIdx] = novo;
        }
    },

    // ============================================================
    // COLETAR DADOS PARA SALVAR
    // ============================================================
    coletarDados() {
        const container = document.getElementById('politicas-obrigacoes-container');
        const politicas = [];
        
        container.querySelectorAll('.politica-item').forEach((politicaItem, politicaIdx) => {
            const politica = {
                titulo: politicaItem.querySelector('.politica-titulo').value.trim() || 'INEXISTENTE',
                tipo: politicaItem.querySelector('.politica-tipo').value || 'interna',
                arquivo_url: politicaItem.getAttribute('data-arquivo-url') || '',
                arquivo_nome: politicaItem.getAttribute('data-arquivo-nome') || '',
                obrigacoes: []
            };
            
            if (this.arquivosPoliticas[politicaIdx] && this.arquivosPoliticas[politicaIdx].file) {
                politica._upload_file = true;
                politica._file_data = this.arquivosPoliticas[politicaIdx];
            }
            
            politicaItem.querySelectorAll('.obrigacao-item').forEach((obrigacaoItem, obrigacaoIdx) => {
                const obrigacao = {
                    titulo: obrigacaoItem.querySelector('.obrigacao-titulo').value.trim() || 'INEXISTENTE',
                    orgao_regulador: obrigacaoItem.querySelector('.obrigacao-orgao').value.trim() || '',
                    prazo: obrigacaoItem.querySelector('.obrigacao-prazo').value || '',
                    obrigatorio: obrigacaoItem.querySelector('.obrigacao-obrigatorio').value === 'true',
                    documento_necessario: obrigacaoItem.querySelector('.obrigacao-documento').value.trim() || '',
                    arquivo_url: obrigacaoItem.getAttribute('data-arquivo-url') || '',
                    arquivo_nome: obrigacaoItem.getAttribute('data-arquivo-nome') || ''
                };
                
                if (this.arquivosObrigacoes[politicaIdx]?.[obrigacaoIdx]?.file) {
                    obrigacao._upload_file = true;
                    obrigacao._file_data = this.arquivosObrigacoes[politicaIdx][obrigacaoIdx];
                }
                
                politica.obrigacoes.push(obrigacao);
            });
            
            politicas.push(politica);
        });
        
        return politicas;
    },
    
    // ============================================================
    // LIMPAR TUDO
    // ============================================================
    limpar() {
        const container = document.getElementById('politicas-obrigacoes-container');
        if (container) {
            container.innerHTML = '';
        }
        this.arquivosPoliticas = {};
        this.arquivosObrigacoes = {};
        this.politicasLista = [];
    },
    
    // ============================================================
    // CARREGAR DADOS
    // ============================================================
    carregarDados(dadosJson) {
        this.limpar();
        
        if (!dadosJson) return;
        
        try {
            const dados = typeof dadosJson === 'string' ? JSON.parse(dadosJson) : dadosJson;
            
            console.log('🔍 Dados recebidos:', dados);
            console.log('🔍 Tipo:', Array.isArray(dados) ? 'Array' : typeof dados);
            
            let politicas = [];
            
            if (Array.isArray(dados)) {
                // ⭐ FORMATO ANTIGO: Array de políticas
                // Verificar se o primeiro item tem 'titulo' e 'obrigacoes' (política)
                if (dados.length > 0 && dados[0].tipo && dados[0].obrigacoes) {
                    // Já é um array de políticas (formato salvo anteriormente)
                    politicas = dados;
                } 
                // Formato antigo de obrigações (array de obrigações sem política)
                else if (dados.length > 0 && dados[0].orgao_regulador !== undefined) {
                    politicas = [{ titulo: 'Obrigações', tipo: 'interna', obrigacoes: dados }];
                }
                // Array vazio
                else {
                    politicas = [];
                }
            } 
            // ⭐ NOVO FORMATO: Objeto com .politicas
            else if (dados.politicas) {
                politicas = dados.politicas;
            }
            // Outro formato
            else {
                politicas = [];
            }
            
            console.log('🔍 Políticas extraídas:', politicas);
            
            politicas.forEach(politica => {
                this.adicionarPolitica(politica);
            });
            
        } catch (e) {
            console.error('Erro ao carregar políticas:', e);
        }
    },
    
    // ============================================================
    // INICIALIZAR NO MODAL
    // ============================================================
    inicializar(dadosJson) {
        this.limpar();
        if (dadosJson) {
            this.carregarDados(dadosJson);
        } else {
            this.adicionarPolitica();
        }
    },

    // ============================================================
    // PROCESSAR UPLOADS DE TODOS OS ARQUIVOS
    // ============================================================
    async processarUploads(politicas, etapaId) {
        const politicasProcessadas = [];
        
        for (const politica of politicas) {
            if (politica._upload_file && politica._file_data) {
                try {
                    const formData = new FormData();
                    formData.append('arquivo', politica._file_data.file);
                    formData.append('tipo', 'politica_interna');
                    formData.append('etapa_id', etapaId || 'temp');
                    formData.append('titulo_politica', politica.titulo);
                    
                    const response = await fetchComAutenticacao('/api/upload/detalhamento', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        politica.arquivo_url = data.url || '';
                        politica.arquivo_nome = data.nome_arquivo || '';
                    } else {
                        window.mostrarToast(`⚠️ Erro ao enviar arquivo da política: ${data.error || 'Erro'}`, 'warning');
                    }
                } catch (error) {
                    console.error('Erro no upload da política:', error);
                    window.mostrarToast('⚠️ Erro ao enviar arquivo da política', 'warning');
                }
            }
            
            const obrigacoesProcessadas = [];
            
            for (const obrigacao of politica.obrigacoes) {
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
                            obrigacao.arquivo_url = data.url || '';
                            obrigacao.arquivo_nome = data.nome_arquivo || '';
                        } else {
                            window.mostrarToast(`⚠️ Erro ao enviar arquivo da obrigação: ${data.error || 'Erro'}`, 'warning');
                        }
                    } catch (error) {
                        console.error('Erro no upload da obrigação:', error);
                        window.mostrarToast('⚠️ Erro ao enviar arquivo da obrigação', 'warning');
                    }
                }
                
                delete obrigacao._upload_file;
                delete obrigacao._file_data;
                
                if (!obrigacao.titulo) obrigacao.titulo = 'INEXISTENTE';
                if (!obrigacao.orgao_regulador) obrigacao.orgao_regulador = '';
                if (!obrigacao.prazo) obrigacao.prazo = '';
                if (!obrigacao.documento_necessario) obrigacao.documento_necessario = '';
                
                obrigacoesProcessadas.push(obrigacao);
            }
            
            delete politica._upload_file;
            delete politica._file_data;
            
            if (!politica.titulo) politica.titulo = 'INEXISTENTE';
            if (!politica.tipo) politica.tipo = 'interna';
            
            politica.obrigacoes = obrigacoesProcessadas;
            
            politicasProcessadas.push(politica);
        }
        
        return politicasProcessadas;
    },
    
    // ============================================================
    // BAIXAR ARQUIVO LOCAL
    // ============================================================
    baixarArquivoLocal(file, nomeArquivo) {
        if (!file) {
            window.mostrarToast('⚠️ Nenhum arquivo disponível para download', 'warning');
            return;
        }
        
        try {
            const url = URL.createObjectURL(file);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = nomeArquivo || file.name || 'documento.pdf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            setTimeout(() => {
                URL.revokeObjectURL(url);
            }, 100);
            
            window.mostrarToast('📥 Download do arquivo local iniciado!', 'success');
        } catch (error) {
            console.error('Erro ao baixar arquivo local:', error);
            window.mostrarToast('❌ Erro ao baixar arquivo', 'error');
        }
    },
    
    // ============================================================
    // BAIXAR COM URL ASSINADA
    // ============================================================
    async _baixarComUrlAssinada(caminho) {
        try {
            const response = await window.fetchComAutenticacao('/api/arquivo/url-assinada', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    caminho: caminho, 
                    bucket: 'detalhamento_etapas' 
                })
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
    
    // ============================================================
    // BAIXAR ARQUIVO POR URL (para visualização)
    // ============================================================
    baixarArquivoPorUrl(url, nomeArquivo) {
        if (!url || url.trim() === '') {
            window.mostrarToast('⚠️ Nenhum arquivo anexado', 'warning');
            return;
        }
        
        this._baixarComUrlAssinada(url);
    }

};