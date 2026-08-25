let etapaIdAtualControle = null;
let riscoIdAtual = null;
let controleIdEditando = null;
const filtroAuditoriaSelect = document.getElementById('filtro_auditoria_select');

import { carregarControlesDoRisco, atualizarBadgeControles, atualizarBadgeEtapaControles } from './controles_etapas.js';

export async function abrirModalControle(riscoId, riscoNome, etapaId, fatorRisco = '') {
    etapaIdAtualControle = etapaId;
    riscoIdAtual = riscoId;
    controleIdEditando = null;
    
    console.log(`📝 Abrindo modal para adicionar controle no risco: ${riscoNome}`);
    
    try {
        const response = await fetchComAutenticacao(`/api/risco-etapa/${riscoId}/basico`);
        const data = await response.json();
        
        if (data.success) {
            const impacto = data.impacto || 'Não informado';
            const probabilidade = data.probabilidade || 'Não informado';

            document.getElementById('info-risco-impacto').textContent = data.impacto || 'Não informado';
            document.getElementById('info-risco-probabilidade').textContent = data.probabilidade || 'Não informado';

            calcularRiscoBruto(impacto, probabilidade);

        }

        function calcularRiscoBruto(impacto, probabilidade) {
            const mapa = {
                "MUITO ALTO,MUITO ALTO": 15, "ALTO,MUITO ALTO": 14,
                "MÉDIO,MUITO ALTO": 13, "BAIXO,MUITO ALTO": 12,
                "MUITO ALTO,ALTO": 11, "ALTO,ALTO": 10,
                "MÉDIO,ALTO": 9, "BAIXO,ALTO": 8,
                "MUITO ALTO,MÉDIO": 7, "ALTO,MÉDIO": 6,
                "MÉDIO,MÉDIO": 5, "BAIXO,MÉDIO": 4,
                "MUITO ALTO,BAIXO": 3, "ALTO,BAIXO": 2,
                "MÉDIO,BAIXO": 1, "BAIXO,BAIXO": 0
            };

            const score = mapa[`${impacto},${probabilidade}`] || 0;
            
            const scoreElement = document.getElementById('info-risco-score-bruto');
            if (scoreElement) {
                scoreElement.innerHTML = `Risco Bruto: <strong>${score}</strong>`;
            }
        }
    } catch (error) {
        console.error('❌ Erro ao buscar dados do risco:', error);
    }
    
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
        document.getElementById('controle_causa_motivo').disabled = true;
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

        try {
            const responseRisco = await fetchComAutenticacao(`/api/risco-etapa/${riscoId}/basico`);
            const dataRisco = await responseRisco.json();
            
            if (dataRisco.success) {
                const impacto = dataRisco.impacto || 'Não informado';
                const probabilidade = dataRisco.probabilidade || 'Não informado';
                
                document.getElementById('info-risco-impacto').textContent = impacto;
                document.getElementById('info-risco-probabilidade').textContent = probabilidade;
                
                calcularRiscoBruto(impacto, probabilidade);
            }
        } catch (error) {
            console.error('❌ Erro ao buscar dados do risco:', error);
        }
        
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
        
        document.getElementById('controle_apetite_impacto').value = controle.apetite_impacto || '';
        document.getElementById('controle_apetite_probabilidade').value = controle.apetite_probabilidade || '';

        document.getElementById('controle_tratamento_risco').value = controle.tratamento_risco || '';
        document.getElementById('controle_descricao_tratamento').value = controle.descricao_tratamento || '';
        document.getElementById('controle_prazo_implantacao').value = controle.prazo_implantacao || '';
        
        calcularScoreResidual();
        
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
            'controle_responsaveis',
            'controle_apetite_impacto',
            'controle_apetite_probabilidade',
            'controle_tratamento_risco',
            'controle_descricao_tratamento',
            'controle_prazo_implantacao'
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

    document.getElementById('controle_apetite_impacto').value = '';
    document.getElementById('controle_apetite_probabilidade').value = '';
    document.getElementById('controle_tratamento_risco').value = '';
    document.getElementById('controle_descricao_tratamento').value = '';
    document.getElementById('controle_prazo_implantacao').value = '';

    controleIdEditando = null;
}

export async function salvarControle() {
    console.log('💾 Iniciando salvamento do controle...');
    
    const nomeControle = document.getElementById('controle_nome').value.trim().toUpperCase();
    console.log('📝 Nome do controle:', nomeControle);
    
    if (!nomeControle) {
        mostrarToast('❌ O nome do controle é obrigatório!', 'error');
        return;
    }
    
    console.log('📦 Montando dados...');
    
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
        auditoria_id: filtroAuditoriaSelect.value || null,
        
        apetite_impacto: document.getElementById('controle_apetite_impacto').value.toUpperCase(),
        apetite_probabilidade: document.getElementById('controle_apetite_probabilidade').value.toUpperCase(),
        tratamento_risco: document.getElementById('controle_tratamento_risco').value.toUpperCase(),
        descricao_tratamento: document.getElementById('controle_descricao_tratamento').value.trim().toUpperCase(),
        prazo_implantacao: document.getElementById('controle_prazo_implantacao').value.trim().toUpperCase()
    };
    
    console.log('📤 Dados a enviar:', JSON.stringify(dados, null, 2));
    
    try {
        const btnSalvar = document.getElementById('btn-salvar-modal-controle');
        const textoOriginal = btnSalvar.innerHTML;
        btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
        btnSalvar.disabled = true;
        
        console.log('📡 Enviando requisição para /api/controle-etapa/salvar...');
        
        const response = await fetchComAutenticacao('/api/controle-etapa/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        
        console.log('📥 Resposta recebida! Status:', response.status);
        console.log('📥 Content-Type:', response.headers.get('content-type'));
        
        const textoResposta = await response.text();
        console.log('📥 Resposta crua:', textoResposta);
        
        let resultado;
        try {
            resultado = JSON.parse(textoResposta);
        } catch (e) {
            console.error('❌ Resposta não é JSON:', textoResposta);
            throw new Error('Resposta inválida do servidor');
        }
        
        console.log('📦 Resultado parseado:', resultado);
        
        if (resultado.success) {
            console.log('✅ Sucesso! Fechando modal e recarregando...');
            mostrarToast('✅ Controle salvo com sucesso!', 'success');
            fecharModalControle();
            
            await carregarControlesDoRisco(riscoIdAtual, etapaIdAtualControle);
            await atualizarBadgeControles(riscoIdAtual);
            
            if (etapaIdAtualControle) {
                await atualizarBadgeEtapaControles(etapaIdAtualControle);
            }
            
        } else {
            console.error('❌ Erro do servidor:', resultado.error);
            mostrarToast('❌ Erro ao salvar: ' + (resultado.error || 'Tente novamente'), 'error');
        }
        
        btnSalvar.innerHTML = textoOriginal;
        btnSalvar.disabled = false;
        
    } catch (error) {
        console.error('❌ ERRO COMPLETO:', error);
        console.error('❌ Stack:', error.stack);
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

    document.getElementById('controle_apetite_impacto')?.addEventListener('change', calcularScoreResidual);
    document.getElementById('controle_apetite_probabilidade')?.addEventListener('change', calcularScoreResidual);
    
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
    
    document.getElementById('btn-fechar-modal-matriz')?.addEventListener('click', fecharModalMatriz);
    document.getElementById('btn-fechar-modal-matriz-rodape')?.addEventListener('click', fecharModalMatriz);
    document.querySelectorAll('.btn-ver-matriz').forEach(btn => {
        btn.addEventListener('click', abrirModalMatriz);
    });
        
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

        try {
            const responseRisco = await fetchComAutenticacao(`/api/risco-etapa/${riscoId}/basico`);
            const dataRisco = await responseRisco.json();
            
            if (dataRisco.success) {
                const impacto = dataRisco.impacto || 'Não informado';
                const probabilidade = dataRisco.probabilidade || 'Não informado';
                
                document.getElementById('info-risco-impacto').textContent = impacto;
                document.getElementById('info-risco-probabilidade').textContent = probabilidade;
                
                calcularRiscoBruto(impacto, probabilidade);
            }
        } catch (error) {
            console.error('❌ Erro ao buscar dados do risco:', error);
        }

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

        document.getElementById('controle_apetite_impacto').value = controle.apetite_impacto || '';
        document.getElementById('controle_apetite_probabilidade').value = controle.apetite_probabilidade || '';
        document.getElementById('controle_tratamento_risco').value = controle.tratamento_risco || '';
        document.getElementById('controle_descricao_tratamento').value = controle.descricao_tratamento || '';
        document.getElementById('controle_prazo_implantacao').value = controle.prazo_implantacao || '';

        calcularScoreResidual();

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
            'controle_responsaveis',

            'controle_apetite_impacto',
            'controle_apetite_probabilidade',
            'controle_tratamento_risco',
            'controle_descricao_tratamento',
            'controle_prazo_implantacao'
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

function calcularScoreResidual() {
    const impacto = document.getElementById('controle_apetite_impacto').value;
    const probabilidade = document.getElementById('controle_apetite_probabilidade').value;
    
    const preview = document.getElementById('controle-score-residual');
    
    if (!impacto || !probabilidade) {
        if (preview) preview.innerHTML = '<strong>Risco Residual:</strong> -';
        return 0;
    }
    
    const mapa = {
        "MUITO ALTO,MUITO ALTO": 15, "ALTO,MUITO ALTO": 14,
        "MÉDIO,MUITO ALTO": 13, "BAIXO,MUITO ALTO": 12,
        "MUITO ALTO,ALTO": 11, "ALTO,ALTO": 10,
        "MÉDIO,ALTO": 9, "BAIXO,ALTO": 8,
        "MUITO ALTO,MÉDIO": 7, "ALTO,MÉDIO": 6,
        "MÉDIO,MÉDIO": 5, "BAIXO,MÉDIO": 4,
        "MUITO ALTO,BAIXO": 3, "ALTO,BAIXO": 2,
        "MÉDIO,BAIXO": 1, "BAIXO,BAIXO": 0
    };
    
    const score = mapa[`${impacto},${probabilidade}`] || 0;
    
    if (preview) {
        preview.innerHTML = `<strong>Risco Residual: ${score}</strong>`;
    }
    
    return score;
}

function calcularRiscoBruto(impacto, probabilidade) {
    const mapa = {
        "MUITO ALTO,MUITO ALTO": 15, "ALTO,MUITO ALTO": 14,
        "MÉDIO,MUITO ALTO": 13, "BAIXO,MUITO ALTO": 12,
        "MUITO ALTO,ALTO": 11, "ALTO,ALTO": 10,
        "MÉDIO,ALTO": 9, "BAIXO,ALTO": 8,
        "MUITO ALTO,MÉDIO": 7, "ALTO,MÉDIO": 6,
        "MÉDIO,MÉDIO": 5, "BAIXO,MÉDIO": 4,
        "MUITO ALTO,BAIXO": 3, "ALTO,BAIXO": 2,
        "MÉDIO,BAIXO": 1, "BAIXO,BAIXO": 0
    };
    
    const score = mapa[`${impacto},${probabilidade}`] || 0;
    
    const scoreElement = document.getElementById('info-risco-score-bruto');
    if (scoreElement) {
        scoreElement.innerHTML = `Risco Bruto: <strong>${score}</strong>`;
    }
}

function abrirModalMatriz() {
    document.getElementById('modal-matriz-calor').style.display = 'flex';
}

function fecharModalMatriz() {
    document.getElementById('modal-matriz-calor').style.display = 'none';
}

