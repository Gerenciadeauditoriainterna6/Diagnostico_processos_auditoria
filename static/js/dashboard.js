// ====== VARIÁVEIS GLOBAIS ======
let filtros = {
    ano: '',
    area: '',
    auditoria: ''
};

// ====== CARREGAR FILTROS ======
async function carregarFiltros() {
    try {
        const response = await fetch('/api/novo-dashboard/filtros');
        const data = await response.json();
        
        if (data.success) {
            // Carregar anos
            const selectAno = document.getElementById('filtro-ano');
            selectAno.innerHTML = '<option value="">Todos os anos</option>';
            data.dados.anos.forEach(ano => {
                const option = document.createElement('option');
                option.value = ano;
                option.textContent = ano;
                selectAno.appendChild(option);
            });

            // Carregar áreas
            const selectArea = document.getElementById('filtro-area');
            selectArea.innerHTML = '<option value="">Todas as áreas</option>';
            data.dados.areas.forEach(area => {
                const option = document.createElement('option');
                option.value = area.id;
                option.textContent = area.nome;
                selectArea.appendChild(option);
            });

            console.log('✅ Filtros carregados!');
        }
    } catch (error) {
        console.error('❌ Erro ao carregar filtros:', error);
    }
}

// ====== CARREGAR AUDITORIAS POR ÁREA ======
async function carregarAuditoriasPorArea(areaId) {
    const selectAuditoria = document.getElementById('filtro-auditoria');
    
    if (!areaId) {
        selectAuditoria.innerHTML = '<option value="">Selecione uma área primeiro</option>';
        selectAuditoria.disabled = true;
        return;
    }

    selectAuditoria.innerHTML = '<option value="">Carregando...</option>';
    selectAuditoria.disabled = true;

    try {
        const response = await fetch(`/api/novo-dashboard/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();
        
        if (data.success && data.dados.auditorias.length > 0) {
            selectAuditoria.innerHTML = '<option value="">Todas as auditorias</option>';
            data.dados.auditorias.forEach(aud => {
                const option = document.createElement('option');
                option.value = aud.id;
                option.textContent = `${aud.codigo} - ${aud.titulo} (${aud.ano})`;
                selectAuditoria.appendChild(option);
            });
            selectAuditoria.disabled = false;
        } else {
            selectAuditoria.innerHTML = '<option value="">Nenhuma auditoria encontrada</option>';
            selectAuditoria.disabled = true;
        }
    } catch (error) {
        console.error('❌ Erro ao carregar auditorias:', error);
        selectAuditoria.innerHTML = '<option value="">Erro ao carregar</option>';
        selectAuditoria.disabled = true;
    }
}

// ====== CARREGAR CARDS ======
async function carregarCards() {
    const params = new URLSearchParams();
    if (filtros.ano) params.append('ano', filtros.ano);
    if (filtros.area) params.append('area_id', filtros.area);
    if (filtros.auditoria) params.append('auditoria_id', filtros.auditoria);
    
    const url = `/api/novo-dashboard/cards?${params.toString()}`;
    
    console.log(`📡 Chamando API: ${url}`);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            // Card 1: Auditorias
            document.getElementById('card-total-auditorias-card').textContent = data.dados.total_auditorias;
            
            // Card 2: Riscos Identificados
            document.getElementById('card-riscos-identificados').textContent = data.dados.riscos_identificados || 0;
            
            // Card 3: Processos Identificados
            document.getElementById('card-processos-mapeados').textContent = data.dados.processos_mapeados || 0;
            
            // Card 4: Controles Identificados
            document.getElementById('card-total-auditorias').textContent = data.dados.total_controles || 0;  // ⭐ CORRIGIDO
            
            console.log('✅ Cards atualizados:', data.dados);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar cards:', error);
    }
}

// ====== CONFIGURAR EVENTOS DOS FILTROS ======
function setupFiltros() {
    const selectAno = document.getElementById('filtro-ano');
    const selectArea = document.getElementById('filtro-area');
    const selectAuditoria = document.getElementById('filtro-auditoria');
    const btnLimpar = document.getElementById('btn-limpar-filtros');

    selectAno.addEventListener('change', function() {
        filtros.ano = this.value;
        console.log('📅 Ano selecionado:', filtros.ano);
        carregarDashboard();
    });

    selectArea.addEventListener('change', function() {
        const areaId = this.value;
        filtros.area = areaId;
        filtros.auditoria = '';
        carregarAuditoriasPorArea(areaId);
        console.log('🏢 Área selecionada:', filtros.area);
        carregarDashboard();
    });

    selectAuditoria.addEventListener('change', function() {
        filtros.auditoria = this.value;
        console.log('📋 Auditoria selecionada:', filtros.auditoria);
        carregarDashboard();
    });

    btnLimpar.addEventListener('click', function() {
        selectAno.value = '';
        selectArea.value = '';
        selectAuditoria.innerHTML = '<option value="">Selecione uma área primeiro</option>';
        selectAuditoria.disabled = true;
        filtros = { ano: '', area: '', auditoria: '' };
        console.log('🧹 Filtros limpos');
        carregarDashboard();
    });
}

// ====== INICIALIZAÇÃO ======
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 Iniciando dashboard...');
    
    // Carregar filtros primeiro
    await carregarFiltros();
    
    // Configurar eventos dos filtros
    setupFiltros();
    
    // Carregar todos os dados (cards + gráficos)
    await carregarDashboard();  // ← ⭐ AGORA CARREGA TUDO!
    
    console.log('✅ Dashboard pronto!');
    console.log('📊 Filtros iniciais:', filtros);
});

// ====== GRÁFICO 1: SITUAÇÃO DAS AUDITORIAS ======
let chartSituacao = null;

async function carregarGraficoSituacao() {
    // Construir URL com filtros
    const params = new URLSearchParams();
    if (filtros.ano) params.append('ano', filtros.ano);
    if (filtros.area) params.append('area_id', filtros.area);
    
    const url = `/api/novo-dashboard/situacao-auditorias?${params.toString()}`;
    
    console.log(`📡 Chamando API situação: ${url}`);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('📊 Dados do gráfico situação:', data);
        
        if (data.success) {
            const ctx = document.getElementById('graficoSituacao').getContext('2d');
            
            // Destruir gráfico anterior se existir
            if (chartSituacao) {
                chartSituacao.destroy();
            }
            
            // ⭐ Verificar se há dados válidos
            if (!data.dados.valores || data.dados.valores.length === 0) {
                console.warn('⚠️ Nenhum dado para o gráfico de situação');
                return;
            }
            
            chartSituacao = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.dados.labels,
                    datasets: [{
                        data: data.dados.valores,
                        backgroundColor: data.dados.cores,
                        borderWidth: 3,
                        borderColor: '#fff',
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: { size: 12 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
            
            console.log('✅ Gráfico Situação atualizado:', data.dados);
        }
    } catch (error) {
        console.error('❌ Erro no gráfico situação:', error);
    }
}

// ====== GRÁFICO 2: RISCOS POR MAGNITUDE ======
let chartRiscosMagnitude = null;

async function carregarGraficoRiscosMagnitude() {
    // Construir URL com filtros
    const params = new URLSearchParams();
    if (filtros.area) params.append('area_id', filtros.area);
    if (filtros.auditoria) params.append('auditoria_id', filtros.auditoria);
    
    const url = `/api/novo-dashboard/riscos-magnitude?${params.toString()}`;
    
    console.log(`📡 Chamando API riscos magnitude: ${url}`);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('📊 Dados do gráfico riscos magnitude:', data);
        
        if (data.success) {
            const ctx = document.getElementById('graficoRiscosMagnitude').getContext('2d');
            
            // Destruir gráfico anterior se existir
            if (chartRiscosMagnitude) {
                chartRiscosMagnitude.destroy();
            }
            
            chartRiscosMagnitude = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.dados.labels,
                    datasets: [{
                        label: 'Quantidade de Riscos',
                        data: data.dados.valores,
                        backgroundColor: data.dados.cores,
                        borderColor: data.dados.cores.map(c => c),
                        borderWidth: 2,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
            
            console.log('✅ Gráfico Riscos Magnitude atualizado');
        }
    } catch (error) {
        console.error('❌ Erro no gráfico riscos magnitude:', error);
    }
}

// ====== GRÁFICO 3: EVOLUÇÃO (MENSAL OU ANUAL) ======
let chartEvolucao = null;

async function carregarGraficoEvolucao() {
    // Construir URL com filtros
    const params = new URLSearchParams();
    if (filtros.ano) params.append('ano', filtros.ano);
    if (filtros.area) params.append('area_id', filtros.area);
    
    const url = `/api/novo-dashboard/evolucao-mensal?${params.toString()}`;
    
    console.log(`📡 Chamando API evolução: ${url}`);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('📊 Dados do gráfico evolução:', data);
        
        if (data.success) {
            const ctx = document.getElementById('graficoEvolucao').getContext('2d');
            
            // Destruir gráfico anterior se existir
            if (chartEvolucao) {
                chartEvolucao.destroy();
            }
            
            // ⭐ Caso não haja dados
            if (data.dados.tipo === 'vazio') {
                chartEvolucao = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Sem dados'],
                        datasets: [{
                            label: 'Nenhuma auditoria encontrada',
                            data: [0],
                            backgroundColor: ['#e0e0e0']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });
                return;
            }
            
            const labels = data.dados.dados.map(item => item.label);
            const valores = data.dados.dados.map(item => item.valor);
            
            // ⭐ Definir tipo de gráfico e cores baseado no tipo
            let tipoGrafico = 'bar';
            let cor = '#0b5b99';
            
            if (data.dados.tipo === 'mensal') {
                tipoGrafico = 'line';
                cor = '#0b5b99';
            } else {
                tipoGrafico = 'bar';
                cor = '#0b5b99';
            }
            
            chartEvolucao = new Chart(ctx, {
                type: tipoGrafico,
                data: {
                    labels: labels,
                    datasets: [{
                        label: data.dados.titulo || 'Auditorias',
                        data: valores,
                        borderColor: cor,
                        backgroundColor: tipoGrafico === 'line' 
                            ? 'rgba(11, 91, 153, 0.1)' 
                            : cor,
                        fill: tipoGrafico === 'line',
                        tension: 0.4,
                        pointBackgroundColor: cor,
                        pointRadius: tipoGrafico === 'line' ? 4 : 0,
                        borderRadius: tipoGrafico === 'bar' ? 8 : 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: { size: 12 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.parsed.y} auditoria${context.parsed.y !== 1 ? 's' : ''}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            },
                            title: {
                                display: true,
                                text: data.dados.label_y || 'Quantidade'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: data.dados.label_x || (data.dados.tipo === 'mensal' ? 'Mês' : 'Ano')
                            }
                        }
                    }
                }
            });
            
            console.log(`✅ Gráfico Evolução (${data.dados.tipo}) atualizado`);
        }
    } catch (error) {
        console.error('❌ Erro no gráfico evolução:', error);
    }
}

// ====== GRÁFICO 4: RISCOS POR CATEGORIA ======
let chartRiscosCategoria = null;

async function carregarGraficoRiscosCategoria() {
    // Construir URL com filtros
    const params = new URLSearchParams();
    if (filtros.area) params.append('area_id', filtros.area);
    if (filtros.auditoria) params.append('auditoria_id', filtros.auditoria);
    
    const url = `/api/novo-dashboard/riscos-categoria?${params.toString()}`;
    
    console.log(`📡 Chamando API riscos categoria: ${url}`);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('📊 Dados do gráfico riscos categoria:', data);
        
        if (data.success) {
            const ctx = document.getElementById('graficoRiscosCategoria').getContext('2d');
            
            // Destruir gráfico anterior se existir
            if (chartRiscosCategoria) {
                chartRiscosCategoria.destroy();
            }
            
            // Verificar se há dados válidos
            if (!data.dados.valores || data.dados.valores.length === 0) {
                console.warn('⚠️ Nenhum dado para o gráfico de riscos por categoria');
                return;
            }
            
            chartRiscosCategoria = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.dados.labels,
                    datasets: [{
                        data: data.dados.valores,
                        backgroundColor: data.dados.cores,
                        borderWidth: 3,
                        borderColor: '#fff',
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 12,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: { size: 11 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '60%'
                }
            });
            
            console.log('✅ Gráfico Riscos por Categoria atualizado');
        }
    } catch (error) {
        console.error('❌ Erro no gráfico riscos categoria:', error);
    }
}

// ====== GRÁFICO 5: TOP ÁREAS ======
let chartTopAreas = null;

async function carregarGraficoTopAreas() {
    // ⭐ APENAS O ANO FILTRA
    const params = new URLSearchParams();
    if (filtros.ano) params.append('ano', filtros.ano);
    
    const url = `/api/novo-dashboard/top-areas?${params.toString()}`;
    
    console.log(`📡 Chamando API top áreas: ${url}`);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('📊 Dados do gráfico top áreas:', data);
        
        if (data.success) {
            const ctx = document.getElementById('graficoTopAreas').getContext('2d');
            
            // Destruir gráfico anterior se existir
            if (chartTopAreas) {
                chartTopAreas.destroy();
            }
            
            // Verificar se há dados válidos
            if (!data.dados.valores || data.dados.valores.length === 0) {
                console.warn('⚠️ Nenhum dado para o gráfico de top áreas');
                return;
            }
            
            chartTopAreas = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.dados.labels,
                    datasets: [{
                        label: 'Processos Identificados',
                        data: data.dados.valores,
                        backgroundColor: data.dados.cores,
                        borderRadius: 8,
                        borderWidth: 2,
                        borderColor: data.dados.cores.map(c => c)
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',  // ⭐ Barras horizontais (mais fácil de ler os nomes)
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        },
                        y: {
                            ticks: {
                                font: {
                                    size: 11
                                }
                            }
                        }
                    }
                }
            });
            
            console.log('✅ Gráfico Top Áreas atualizado');
        }
    } catch (error) {
        console.error('❌ Erro no gráfico top áreas:', error);
    }
}

// ====== GRÁFICO 6: CONTROLES POR STATUS ======
let chartControlesStatus = null;

async function carregargraficoControlesNatureza() {
    // Construir URL com filtros
    const params = new URLSearchParams();
    if (filtros.area) params.append('area_id', filtros.area);
    if (filtros.auditoria) params.append('auditoria_id', filtros.auditoria);
    
    const url = `/api/novo-dashboard/controles-status?${params.toString()}`;
    
    console.log(`📡 Chamando API controles status: ${url}`);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('📊 Dados do gráfico controles status:', data);
        
        if (data.success) {
            const ctx = document.getElementById('graficoControlesNatureza').getContext('2d');
            
            // Destruir gráfico anterior se existir
            if (chartControlesStatus) {
                chartControlesStatus.destroy();
            }
            
            // Verificar se há dados válidos
            if (!data.dados.valores || data.dados.valores.length === 0) {
                console.warn('⚠️ Nenhum dado para o gráfico de controles por status');
                return;
            }
            
            chartControlesStatus = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.dados.labels,
                    datasets: [{
                        data: data.dados.valores,
                        backgroundColor: data.dados.cores,
                        borderWidth: 3,
                        borderColor: '#fff',
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: { size: 12 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
            
            console.log('✅ Gráfico Controles por Status atualizado');
        }
    } catch (error) {
        console.error('❌ Erro no gráfico controles status:', error);
    }
}

// ====== CARREGAR CARDS E GRÁFICOS ======
async function carregarDashboard() {
    console.log('🔄 Carregando dashboard com filtros:', filtros);
    
    try {
        await Promise.all([
            carregarCards(),
            carregarGraficoSituacao(),
            carregarGraficoRiscosMagnitude(),
            carregarGraficoEvolucao(),
            carregarGraficoRiscosCategoria(),
            carregarGraficoTopAreas(),
            carregargraficoControlesNatureza()
        ]);
        
        console.log('✅ Dashboard atualizado!');
    } catch (error) {
        console.error('❌ Erro ao carregar dashboard:', error);
    }
}

