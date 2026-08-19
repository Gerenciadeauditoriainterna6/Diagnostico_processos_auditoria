let etapaIdAtualControle = null;
let riscoIdAtual = null;
let controleIdEditando = null;
const filtroAuditoriaSelect = document.getElementById('filtro_auditoria_select');

import { carregarControlesDoRisco, atualizarBadgeControles, atualizarBadgeEtapaControles } from './controles_etapas.js';

export function abrirModalControle(riscoId, riscoNome, etapaId, fatorRisco = '') {
    etapaIdAtualControle = etapaId;
    riscoIdAtual = riscoId;
    controleIdEditando = null;
    
    console.log(`📝 Abrindo modal para adicionar controle no risco: ${riscoNome}`);
    
    const modalTitle = document.getElementById('modal-controle-title');
    if (modalTitle) {
        modalTitle.innerHTML = `<i class="fas fa-shield-alt"></i> Novo Controle - ${riscoNome}`;
    }
    
    limparFormularioControle();

    // ⭐ HABILITAR TODOS OS CAMPOS
    const campos = [
        'controle_nome',
        'controle_causa_motivo',
        'controle_como_executado',
        'controle_objetivo',
        'controle_periodicidade',
        'controle_evidencia',
        'controle_local_evidencia',
        'controle_forma_execucao',
        'controle_natureza',
        'controle_lgpd',
        'controle_status',
        'controle_frequencia_evidencia',
        'controle_responsaveis'
    ];

    campos.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.disabled = false;
            campo.style.background = '';
            campo.style.color = '';
        }
    });

    // ⭐ MOSTRAR BOTÃO SALVAR
    const btnSalvar = document.getElementById('btn-salvar-modal-controle');
    if (btnSalvar) {
        btnSalvar.style.display = 'inline-flex';
    }
    
    if (fatorRisco) {
        document.getElementById('controle_causa_motivo').value = fatorRisco;
    }
    
    const modal = document.getElementById('modal-controle');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

export async function editarControle(controleId, riscoId) {
    try {
        const response = await fetchComAutenticacao(`/api/controle-etapa/${controleId}`);
        const data = await response.json();
        
        if (!data.success) {
            mostrarToast('❌ Erro ao carregar dados do controle', 'error');
            return;
        }
        
        const controle = data.controle;
        
        controleIdEditando = controleId;
        riscoIdAtual = riscoId;
        
        document.getElementById('controle_nome').value = controle.nome_controle || '';
        document.getElementById('controle_causa_motivo').value = controle.causa_motivo || '';
        document.getElementById('controle_como_executado').value = controle.como_executado || '';
        document.getElementById('controle_objetivo').value = controle.objetivo_controle || '';
        document.getElementById('controle_periodicidade').value = controle.periodicidade_execucao || '';
        document.getElementById('controle_evidencia').value = controle.evidencia_realizacao || '';
        document.getElementById('controle_local_evidencia').value = controle.local_evidencia || '';
        document.getElementById('controle_forma_execucao').value = controle.forma_execucao || '';
        document.getElementById('controle_natureza').value = controle.natureza || '';
        document.getElementById('controle_lgpd').value = controle.lgpd || '';
        document.getElementById('controle_status').value = controle.status_controle || '';
        document.getElementById('controle_frequencia_evidencia').value = controle.frequencia_evidencia || '';
        document.getElementById('controle_responsaveis').value = controle.responsaveis_tratamento || '';
        
        const riscoCard = document.querySelector(`.risco-card[data-risco-id="${riscoId}"]`);
        const riscoNome = riscoCard ? riscoCard.getAttribute('data-risco-nome') : 'Controle';
        
        const modalTitle = document.getElementById('modal-controle-title');
        if (modalTitle) {
            modalTitle.innerHTML = `<i class="fas fa-shield-alt"></i> Editar Controle - ${riscoNome}`;
        }

        // ⭐ RE-HABILITAR TODOS OS CAMPOS
        const campos = [
            'controle_nome',
            'controle_causa_motivo',
            'controle_como_executado',
            'controle_objetivo',
            'controle_periodicidade',
            'controle_evidencia',
            'controle_local_evidencia',
            'controle_forma_execucao',
            'controle_natureza',
            'controle_lgpd',
            'controle_status',
            'controle_frequencia_evidencia',
            'controle_responsaveis'
        ];

        campos.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) {
                campo.disabled = false;
                campo.style.background = '';
                campo.style.color = '';
            }
        });

        // ⭐ MOSTRAR BOTÃO SALVAR
        const btnSalvar = document.getElementById('btn-salvar-modal-controle');
        if (btnSalvar) {
            btnSalvar.style.display = 'inline-flex';
        }
        
        const modal = document.getElementById('modal-controle');
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
        
    } catch (error) {
        console.error('❌ Erro ao carregar controle:', error);
        mostrarToast('❌ Erro ao carregar dados do controle', 'error');
    }
}

export function fecharModalControle() {
    const modal = document.getElementById('modal-controle');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

export function limparFormularioControle() {
    document.getElementById('controle_id').value = '';
    document.getElementById('controle_nome').value = '';
    document.getElementById('controle_como_executado').value = '';
    document.getElementById('controle_objetivo').value = '';
    document.getElementById('controle_evidencia').value = '';
    document.getElementById('controle_local_evidencia').value = '';
    document.getElementById('controle_lgpd').value = '';
    document.getElementById('controle_responsaveis').value = '';
    document.getElementById('controle_causa_motivo').value = '';
    document.getElementById('controle_periodicidade').value = '';
    document.getElementById('controle_natureza').value = '';
    document.getElementById('controle_forma_execucao').value = '';
    document.getElementById('controle_status').value = '';
    document.getElementById('controle_frequencia_evidencia').value = '';
    controleIdEditando = null;
}

export async function salvarControle() {
    console.log('💾 Iniciando salvamento do controle...');
    
    const nomeControle = document.getElementById('controle_nome').value.trim().toUpperCase();
    if (!nomeControle) {
        mostrarToast('❌ O nome do controle é obrigatório!', 'error');
        return;
    }
    
    const dados = {
        id: controleIdEditando,
        risco_id: riscoIdAtual,
        nome_controle: nomeControle,
        causa_motivo: document.getElementById('controle_causa_motivo').value.trim().toUpperCase(),
        como_executado: document.getElementById('controle_como_executado').value.trim().toUpperCase(),
        objetivo_controle: document.getElementById('controle_objetivo').value.trim().toUpperCase(),
        periodicidade_execucao: document.getElementById('controle_periodicidade').value.toUpperCase(),
        evidencia_realizacao: document.getElementById('controle_evidencia').value.trim().toUpperCase(),
        local_evidencia: document.getElementById('controle_local_evidencia').value.trim().toUpperCase(),
        forma_execucao: document.getElementById('controle_forma_execucao').value.toUpperCase(),
        natureza: document.getElementById('controle_natureza').value.toUpperCase(),
        lgpd: document.getElementById('controle_lgpd').value.trim().toUpperCase(),
        status_controle: document.getElementById('controle_status').value.toUpperCase(),
        frequencia_evidencia: document.getElementById('controle_frequencia_evidencia').value.toUpperCase(),
        responsaveis_tratamento: document.getElementById('controle_responsaveis').value.trim().toUpperCase(),
        auditoria_id: filtroAuditoriaSelect.value || null
    };
    
    try {
        const btnSalvar = document.getElementById('btn-salvar-modal-controle');
        const textoOriginal = btnSalvar.innerHTML;
        btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
        btnSalvar.disabled = true;
        
        const response = await fetchComAutenticacao('/api/controle-etapa/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        
        const resultado = await response.json();
        
        if (resultado.success) {
            mostrarToast('✅ Controle salvo com sucesso!', 'success');
            fecharModalControle();
            
            await carregarControlesDoRisco(riscoIdAtual, etapaIdAtualControle);
            await atualizarBadgeControles(riscoIdAtual);
            
            if (etapaIdAtualControle) {
                await atualizarBadgeEtapaControles(etapaIdAtualControle);
            }
            
        } else {
            mostrarToast('❌ Erro ao salvar: ' + (resultado.error || 'Tente novamente'), 'error');
        }
        
        btnSalvar.innerHTML = textoOriginal;
        btnSalvar.disabled = false;
        
    } catch (error) {
        console.error('❌ Erro na requisição:', error);
        mostrarToast('❌ Erro de conexão. Tente novamente.', 'error');
        
        const btnSalvar = document.getElementById('btn-salvar-modal-controle');
        if (btnSalvar) {
            btnSalvar.innerHTML = '<i class="fas fa-save"></i> Salvar Controle';
            btnSalvar.disabled = false;
        }
    }
}

export function setupModalControle() {
    const modal = document.getElementById('modal-controle');
    const btnFechar = document.getElementById('btn-fechar-modal-controle');
    const btnCancelar = document.getElementById('btn-cancelar-modal-controle');
    const btnSalvar = document.getElementById('btn-salvar-modal-controle');
    
    console.log('🔧 Configurando modal de controle...');
    
    // 1. Botão X (fechar) - Usando onclick diretamente
    if (btnFechar) {
        btnFechar.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('❌ Fechando modal pelo X');
            fecharModalControle();
        };
    }
    
    // 2. Botão Cancelar - Usando onclick diretamente
    if (btnCancelar) {
        btnCancelar.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('❌ Fechando modal pelo Cancelar');
            fecharModalControle();
        };
    }
    

    
    // 5. Botão Salvar - Usando onclick diretamente
    if (btnSalvar) {
        btnSalvar.onclick = function(e) {
            e.preventDefault();
            console.log('💾 Salvando controle...');
            salvarControle();
        };
    }
    
    console.log('✅ Modal de controle configurado!');
}

export async function visualizarControle(controleId, riscoId) {
    try {
        const response = await fetchComAutenticacao(`/api/controle-etapa/${controleId}`);
        const data = await response.json();

        if (!data.success) {
            mostrarToast('❌ Erro ao carregar dados do controle', 'error');
            return;
        }

        const controle = data.controle;

        // Preencher campos
        document.getElementById('controle_nome').value = controle.nome_controle || '';
        document.getElementById('controle_causa_motivo').value = controle.causa_motivo || '';
        document.getElementById('controle_como_executado').value = controle.como_executado || '';
        document.getElementById('controle_objetivo').value = controle.objetivo_controle || '';
        document.getElementById('controle_periodicidade').value = controle.periodicidade_execucao || '';
        document.getElementById('controle_evidencia').value = controle.evidencia_realizacao || '';
        document.getElementById('controle_local_evidencia').value = controle.local_evidencia || '';
        document.getElementById('controle_forma_execucao').value = controle.forma_execucao || '';
        document.getElementById('controle_natureza').value = controle.natureza || '';
        document.getElementById('controle_lgpd').value = controle.lgpd || '';
        document.getElementById('controle_status').value = controle.status_controle || '';
        document.getElementById('controle_frequencia_evidencia').value = controle.frequencia_evidencia || '';
        document.getElementById('controle_responsaveis').value = controle.responsaveis_tratamento || '';

        // MUDAR TÍTULO
        const modalTitle = document.getElementById('modal-controle-title');
        if (modalTitle) {
            modalTitle.innerHTML = `<i class="fas fa-eye"></i> Visualizar Controle`;
        }

        // DESABILITAR TODOS OS CAMPOS
        const campos = [
            'controle_nome',
            'controle_causa_motivo',
            'controle_como_executado',
            'controle_objetivo',
            'controle_periodicidade',
            'controle_evidencia',
            'controle_local_evidencia',
            'controle_forma_execucao',
            'controle_natureza',
            'controle_lgpd',
            'controle_status',
            'controle_frequencia_evidencia',
            'controle_responsaveis'
        ];

        campos.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) {
                campo.disabled = true;
                campo.style.background = '#f5f5f5';
                campo.style.color = '#555';
            }
        });

        // ESCONDER BOTÃO SALVAR
        const btnSalvar = document.getElementById('btn-salvar-modal-controle');
        if (btnSalvar) {
            btnSalvar.style.display = 'none';
        }

        // MOSTRAR MODAL
        const modal = document.getElementById('modal-controle');
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }

    } catch (error) {
        console.error('❌ Erro ao carregar controle:', error);
        mostrarToast('❌ Erro ao carregar dados do controle', 'error');
    }
}