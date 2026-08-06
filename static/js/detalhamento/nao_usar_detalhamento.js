
// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function converterParaBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function mostrarToast(mensagem, tipo = 'info') {
    // Usa a função do base.html se existir, senão cria uma local
    if (typeof window.mostrarToast === 'function') {
        window.mostrarToast(mensagem, tipo);
        return;
    }
    alert(mensagem);
}

// ============================================================
// CARREGAR ÁREAS
// ============================================================

async function carregarAreas() {
    const selectArea = document.getElementById('detalhamento_area_select');
    if (!selectArea) return;

    selectArea.innerHTML = '<option value="">Carregando áreas...</option>';

    try {
        const response = await fetchComAutenticacao('/api/areas');
        const areas = await response.json();

        if (areas && areas.length > 0) {
            selectArea.innerHTML = '<option value="">Selecione uma área...</option>';
            areas.forEach(area => {
                const option = document.createElement('option');
                option.value = area.id_area;
                
                // ⭐ FORMATAR NOME COM UNIDADE (se tiver)
                let nomeCompleto = area.nome_area;
                if (area.loc_unidade && area.loc_unidade.trim()) {
                    nomeCompleto = `${area.nome_area} - ${area.loc_unidade}`;
                } else if (area.nome_area_original && area.loc_unidade) {
                    // Caso a API retorne campos separados
                    nomeCompleto = `${area.nome_area_original} - ${area.loc_unidade}`;
                }
                
                option.textContent = nomeCompleto;
                selectArea.appendChild(option);
            });
            selectArea.disabled = false;
        } else {
            selectArea.innerHTML = '<option value="">Nenhuma área encontrada</option>';
            selectArea.disabled = true;
        }
    } catch (error) {
        console.error('Erro ao carregar áreas:', error);
        selectArea.innerHTML = '<option value="">Erro ao carregar áreas</option>';
        selectArea.disabled = true;
    }
}

// ============================================================
// FUNÇÃO PARA RESTAURAR ESTADO (CORRIGIDA)
// ============================================================

function restaurarEstadoDetalhamento() {
    const estadoSalvo = sessionStorage.getItem('detalhamento_estado');
    if (!estadoSalvo) {
        console.log('📭 Nenhum estado salvo encontrado');
        return;
    }

    const estado = JSON.parse(estadoSalvo);
    console.log('🔄 Estado encontrado:', estado);
    
    // Verificar se o estado não é muito antigo (ex: 5 minutos)
    const agora = new Date().getTime();
    const diffMinutes = (agora - estado.timestamp) / 1000 / 60;
    
    if (diffMinutes > 5) {
        console.log('⚠️ Estado muito antigo, removendo');
        sessionStorage.removeItem('detalhamento_estado');
        return;
    }
    
    // Aguardar o carregamento das áreas
    setTimeout(async () => {
        const selectArea = document.getElementById('detalhamento_area_select');
        const selectAuditoria = document.getElementById('detalhamento_auditoria_select');
        
        console.log('🔍 Buscando elementos:', {
            selectArea: !!selectArea,
            selectAuditoria: !!selectAuditoria,
            area_id: estado.area_id,
            auditoria_id: estado.auditoria_id
        });
        
        if (selectArea && estado.area_id) {
            // Aguardar as áreas serem carregadas
            let tentativas = 0;
            const aguardarAreas = setInterval(() => {
                const options = selectArea.querySelectorAll('option');
                const hasValue = Array.from(options).some(opt => opt.value == estado.area_id);
                
                if (hasValue || tentativas > 20) {
                    clearInterval(aguardarAreas);
                    
                    if (hasValue) {
                        // Selecionar a área
                        selectArea.value = estado.area_id;
                        console.log('✅ Área selecionada:', selectArea.value);
                        
                        // Forçar o carregamento das auditorias
                        const event = new Event('change', { bubbles: true });
                        selectArea.dispatchEvent(event);
                        
                        // Aguardar o carregamento das auditorias e selecionar
                        setTimeout(() => {
                            if (selectAuditoria && estado.auditoria_id) {
                                // Aguardar as auditorias serem carregadas
                                let tentativasAud = 0;
                                const aguardarAuditorias = setInterval(() => {
                                    const auditOptions = selectAuditoria.querySelectorAll('option');
                                    const hasAuditValue = Array.from(auditOptions).some(opt => opt.value == estado.auditoria_id);
                                    
                                    if (hasAuditValue || tentativasAud > 20) {
                                        clearInterval(aguardarAuditorias);
                                        
                                        if (hasAuditValue) {
                                            selectAuditoria.value = estado.auditoria_id;
                                            console.log('✅ Auditoria selecionada:', selectAuditoria.value);
                                            
                                            // Disparar evento change para carregar processos
                                            const auditEvent = new Event('change', { bubbles: true });
                                            selectAuditoria.dispatchEvent(auditEvent);
                                            
                                            // Limpar o estado depois de restaurar
                                            setTimeout(() => {
                                                sessionStorage.removeItem('detalhamento_estado');
                                                console.log('🗑️ Estado removido após restauração');
                                            }, 1000);
                                        }
                                    }
                                    tentativasAud++;
                                }, 200);
                            }
                        }, 800);
                    }
                }
                tentativas++;
            }, 200);
        }
    }, 500);
}

// ============================================================
// FUNÇÕES DE CARREGAMENTO
// ============================================================

async function carregarAuditoriasDetalhamento(areaId) {
    const selectAuditoria = document.getElementById('detalhamento_auditoria_select');
    const tabelaContainer = document.getElementById('detalhamento-tabela-container');
    
    if (!areaId) {
        if (selectAuditoria) {
            selectAuditoria.innerHTML = '<option value="">Selecione uma área primeiro...</option>';
            selectAuditoria.disabled = true;
        }
        if (tabelaContainer) {
            tabelaContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma área para começar.</div>';
        }
        return;
    }

    if (selectAuditoria) {
        selectAuditoria.innerHTML = '<option value="">Carregando auditorias...</option>';
        selectAuditoria.disabled = true;
    }

    try {
        const response = await fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();

        if (selectAuditoria) {
            if (data.auditorias && data.auditorias.length > 0) {
                selectAuditoria.innerHTML = '<option value="">Selecione uma auditoria...</option>';
                data.auditorias.forEach(aud => {
                    const option = document.createElement('option');
                    option.value = aud.id;
                    option.textContent = `${aud.codigo_auditoria} - ${aud.titulo} (${aud.ano}) ${aud.trimestre}º trim) - ${aud.unidade || ''}`;
                    selectAuditoria.appendChild(option);
                });
                selectAuditoria.disabled = false;
            } else {
                selectAuditoria.innerHTML = '<option value="">Nenhuma auditoria encontrada</option>';
                selectAuditoria.disabled = true;
            }
        }
    } catch (error) {
        console.error('Erro ao carregar auditorias:', error);
        if (selectAuditoria) {
            selectAuditoria.innerHTML = '<option value="">Erro ao carregar</option>';
            selectAuditoria.disabled = true;
        }
    }
}

async function carregarProcessosDetalhamento(auditoriaId) {
    const tabelaContainer = document.getElementById('detalhamento-tabela-container');
    
    if (!auditoriaId) {
        if (tabelaContainer) {
            tabelaContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma auditoria para visualizar os processos.</div>';
        }
        return;
    }

    if (tabelaContainer) {
        tabelaContainer.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div class="dot-spinner">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <p style="margin-top: 25px; color: #666; font-size: 14px;">Verificando permissão...</p>
            </div>
        `;
    }

    try {
        // ===== 1. VERIFICAR PERMISSÃO DO USUÁRIO =====
        const respPermissao = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
        const dadosPermissao = await respPermissao.json();
        
        if (!dadosPermissao.autorizado) {
            // Usuário NÃO autorizado
            if (tabelaContainer) {
                tabelaContainer.innerHTML = `
                    <div class="alert-error" style="text-align: center; padding: 40px;">
                        <i class="fas fa-lock"></i> Você não tem permissão para visualizar processos desta auditoria.
                    </div>
                `;
            }
            return;
        }
        
        // ===== 2. USUÁRIO AUTORIZADO - CARREGAR PROCESSOS =====
        if (tabelaContainer) {
            tabelaContainer.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div class="dot-spinner">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <p style="margin-top: 25px; color: #666; font-size: 14px;">Carregando processos para detalhar...</p>
            </div>
        `;
        }
        
        const response = await fetchComAutenticacao(`/api/processos-por-auditoria?auditoria_id=${auditoriaId}`);
        const data = await response.json();

        if (!data.success || !data.processos || data.processos.length === 0) {
            if (tabelaContainer) {
                tabelaContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Nenhum processo encontrado para esta auditoria.</div>';
            }
            return;
        }

        // Montar a tabela de processos (código existente)
        let html = `
            <div style="overflow-x: auto;">
                <table class="tabela-processos">
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Nome do Processo</th>
                            <th>Objetivo</th>
                            <th>Fluxo BPMN</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        for (const processo of data.processos) {
            const temBpmn = processo.fluxo_bpmn_nome && processo.fluxo_bpmn_nome.trim() !== '';
            const corBpmn = temBpmn ? '#28a745' : '#184145';
            
            html += `
                <tr>
                    <td><strong>${escapeHtml(processo.codigo_processo)}</strong></td>
                    <td>${escapeHtml(processo.nome_processo)}</td>
                    <td>${escapeHtml(processo.objetivo || '-')}</td>
                    <td>
                        <button class="btn-bpmn-processo" 
                                data-processo-id="${processo.id}" 
                                title="${temBpmn ? 'Fluxo BPMN anexado - Clique para gerenciar' : 'Clique para anexar fluxo BPMN'}"
                                style="background: ${corBpmn};">
                            <i class="fas fa-project-diagram"></i> BPMN
                        </button>
                    </td>
                    <td>
                        <button class="btn-detalhar-processo" data-processo-id="${processo.id}" data-processo-codigo="${processo.codigo_processo}">
                            <i class="fas fa-eye"></i> Detalhar
                        </button>
                    </td>
                </tr>
            `;
        }

        html += `
                    </tbody>
                </table>
            </div>
        `;

        if (tabelaContainer) {
            tabelaContainer.innerHTML = html;
        }

        // Adicionar eventos aos botões
        document.querySelectorAll('.btn-detalhar-processo').forEach(btn => {
            btn.addEventListener('click', () => {
                const processoId = btn.getAttribute('data-processo-id');
                const processoCodigo = btn.getAttribute('data-processo-codigo');
                window.location.href = `/detalhamento_etapas?processo_id=${processoId}&processo_codigo=${processoCodigo}`;
            });
        });

    } catch (error) {
        console.error('Erro ao carregar processos:', error);
        if (tabelaContainer) {
            tabelaContainer.innerHTML = '<div class="alert-error" style="text-align: center; padding: 40px;"><i class="fas fa-exclamation-triangle"></i> Erro ao carregar processos. Tente novamente.</div>';
        }
    }
}

// ============================================================
// EVENTOS
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Página de detalhamento carregada');
    
    // Carregar áreas primeiro
    await carregarAreas();
    
    // Depois de carregar as áreas, tentar restaurar o estado
    setTimeout(() => {
        restaurarEstadoDetalhamento();
    }, 500);
    
    // Configurar eventos
    const selectArea = document.getElementById('detalhamento_area_select');
    const selectAuditoria = document.getElementById('detalhamento_auditoria_select');
    const tabelaContainer = document.getElementById('detalhamento-tabela-container');
    
    if (selectArea) {
        selectArea.addEventListener('change', () => {
            const areaId = selectArea.value;
            carregarAuditoriasDetalhamento(areaId);
            if (tabelaContainer) {
                tabelaContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma auditoria para visualizar os processos.</div>';
            }
        });
    }
    
    if (selectAuditoria) {
        selectAuditoria.addEventListener('change', () => {
            const auditoriaId = selectAuditoria.value;
            if (auditoriaId) {
                carregarProcessosDetalhamento(auditoriaId);
            } else if (tabelaContainer) {
                tabelaContainer.innerHTML = '<div class="alert-info" style="text-align: center; padding: 40px;"><i class="fas fa-info-circle"></i> Selecione uma auditoria para visualizar os processos.</div>';
            }
        });
    }
});


// ============================================================
// MODAL BPMN DO PROCESSO
// ============================================================

let processoBPMNAtual = null;

function abrirModalBPMN(processoId) {
    processoBPMNAtual = processoId;
    const modal = document.getElementById('modal-bpmn');
    const body = document.getElementById('modal-bpmn-body');
    
    if (!modal || !body) return;
    
    modal.style.display = 'flex';
    body.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin"></i> Carregando...</div>';
    
    // Buscar dados do processo para verificar se já tem BPMN
    fetchComAutenticacao(`/api/processo/${processoId}/dados`)
        .then(res => res.json())
        .then(data => {
            if (data.fluxo_bpmn_nome) {
                // Já tem BPMN
                body.innerHTML = `
                    <div style="text-align: center;">
                        <div style="margin-bottom: 20px;">
                            <i class="fas fa-file-code" style="font-size: 48px; color: #184145;"></i>
                        </div>
                        <p style="margin-bottom: 5px;"><strong>${escapeHtml(data.fluxo_bpmn_nome)}</strong></p>
                        <p style="color: #666; font-size: 12px; margin-bottom: 20px;">Arquivo BPMN anexado</p>
                        <div style="display: flex; gap: 10px; justify-content: center;">
                            <button class="btn-primary" onclick="baixarBPMN(${processoId})">
                                <i class="fas fa-download"></i> Baixar
                            </button>
                            <button class="btn-outline" onclick="substituirBPMN(${processoId})">
                                <i class="fas fa-exchange-alt"></i> Substituir
                            </button>
                            <button class="btn-outline" style="border-color: #dc3545; color: #dc3545;" onclick="removerBPMN(${processoId})">
                                <i class="fas fa-trash"></i> Remover
                            </button>
                        </div>
                    </div>
                `;
            } else {
                // Não tem BPMN
                body.innerHTML = `
                    <div style="text-align: center;">
                        <div style="margin-bottom: 20px;">
                            <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: #184145;"></i>
                        </div>
                        <p style="color: #666; margin-bottom: 20px;">Nenhum fluxo BPMN anexado para este processo.</p>
                        <button class="btn-primary" onclick="uploadBPMN(${processoId})">
                            <i class="fas fa-upload"></i> Anexar Fluxo BPMN
                        </button>
                    </div>
                `;
            }
        })
        .catch(err => {
            body.innerHTML = '<div class="alert-error">Erro ao carregar dados do processo.</div>';
        });
}

function fecharModalBPMN() {
    document.getElementById('modal-bpmn').style.display = 'none';
    processoBPMNAtual = null;
}

function baixarBPMN(processoId) {
    window.open(`/api/processo/${processoId}/download-bpmn`, '_blank');
}

function uploadBPMN(processoId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.bpmn,.xml,.jpg,.jpeg,.png,.pdf';
    input.onchange = async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Mostrar loading
        const body = document.getElementById('modal-bpmn-body');
        body.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin"></i> Enviando arquivo...</div>';
        
        try {
            const base64 = await converterParaBase64(file);
            const response = await fetchComAutenticacao(`/api/processo/${processoId}/upload-bpmn`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    arquivo_base64: base64,
                    nome_arquivo: file.name,
                    tipo_arquivo: file.type || 'application/octet-stream'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                mostrarToast('✅ Fluxo BPMN salvo!', 'success');
                abrirModalBPMN(processoId); // Recarregar modal
            } else {
                mostrarToast('❌ Erro: ' + (data.error || 'Tente novamente'), 'error');
                abrirModalBPMN(processoId);
            }
        } catch (error) {
            mostrarToast('❌ Erro ao enviar arquivo', 'error');
            abrirModalBPMN(processoId);
        }
    };
    input.click();
}

function substituirBPMN(processoId) {
    uploadBPMN(processoId);
}

async function removerBPMN(processoId) {
    if (!confirm('Tem certeza que deseja remover o fluxo BPMN deste processo?')) return;
    
    try {
        const response = await fetchComAutenticacao(`/api/processo/${processoId}/remover-bpmn`, { method: 'DELETE' });
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('✅ Fluxo BPMN removido', 'success');
            abrirModalBPMN(processoId);
        } else {
            mostrarToast('❌ Erro ao remover', 'error');
        }
    } catch (error) {
        mostrarToast('❌ Erro ao remover', 'error');
    }
}

// Evento para abrir modal ao clicar no botão BPMN
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn-bpmn-processo');
    if (btn) {
        const processoId = btn.getAttribute('data-processo-id');
        abrirModalBPMN(processoId);
    }
});


// ============================================================
// FUNÇÕES PARA COMENTÁRIOS
// ============================================================

let comentarioAuditoriaAtual = null;
let arquivosAnexados = [];

// ============================================================
// BAIXAR ANEXO
// ============================================================

async function baixarAnexo(achadoId, anexoIndex) {
    try {
        const response = await fetchComAutenticacao(`/api/achado/anexo/${achadoId}/${anexoIndex}/download`);
        const data = await response.json();
        
        if (data.success && data.url) {
            // Abrir a URL assinada em uma nova aba
            window.open(data.url, '_blank');
        } else {
            mostrarToast('❌ Erro ao baixar anexo: ' + (data.error || 'Tente novamente'), 'error');
        }
    } catch (error) {
        console.error('Erro ao baixar anexo:', error);
        mostrarToast('❌ Erro ao baixar anexo.', 'error');
    }
}

// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================

function getIconeArquivo(nome) {
    const ext = nome.split('.').pop().toLowerCase();
    const icones = {
        'pdf': 'fa-file-pdf',
        'doc': 'fa-file-word',
        'docx': 'fa-file-word',
        'xls': 'fa-file-excel',
        'xlsx': 'fa-file-excel',
        'jpg': 'fa-file-image',
        'jpeg': 'fa-file-image',
        'png': 'fa-file-image',
        'gif': 'fa-file-image',
        'txt': 'fa-file-alt',
        'zip': 'fa-file-archive',
        'rar': 'fa-file-archive',
        'ppt': 'fa-file-powerpoint',
        'pptx': 'fa-file-powerpoint'
    };
    return icones[ext] || 'fa-file';
}

function formatarTamanho(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
}

// Anexo - mostrar nome do arquivo selecionado
document.addEventListener('DOMContentLoaded', function() {
    const inputAnexo = document.getElementById('comentario_anexo');
    if (inputAnexo) {
        inputAnexo.addEventListener('change', function(e) {
            const nomeSpan = document.getElementById('anexo-nome');
            const files = e.target.files;
            
            if (files.length > 0) {
                const nomes = Array.from(files).map(f => f.name);
                if (nomes.length === 1) {
                    nomeSpan.textContent = nomes[0];
                } else {
                    nomeSpan.textContent = `${nomes.length} arquivos selecionados`;
                }
            } else {
                nomeSpan.textContent = '';
            }
        });
    }
    
    // Botão enviar
    const btnEnviar = document.getElementById('btn-enviar-comentario');
    if (btnEnviar) {
        btnEnviar.addEventListener('click', enviarComentario);
    }
    
    // Enter para enviar (Ctrl+Enter)
    const textarea = document.getElementById('comentario_texto');
    if (textarea) {
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                enviarComentario();
            }
        });
    }
});

// ============================================================
// INTEGRAÇÃO COM O CARREGAMENTO DE AUDITORIA
// ============================================================

// Sobrescrever a função carregarProcessosDetalhamento para incluir comentários
// Mantém a função original e adiciona a chamada para comentários

// Salvar a função original
const _carregarProcessosDetalhamentoOriginal = window.carregarProcessosDetalhamento || function() {};
