// ============================================================
// VARIÁVEIS GLOBAIS
// ============================================================

export let currentRespostaIds = {};
export let arquivoSelecionadoAuditor = null;  
export let anexoExistenteNomeAuditor = null;  
export let auditoriaIdAtual = null;
export let processoIdAtual = null;
export let analisesAuditorList = [];

// Variáveis para análises do auditado
export let analisesAuditadoList = [];

// Variáveis para checklist
export let currentRespostaId = null;
export let arquivosPendentes = {};

// Variáveis para evidência da análise do auditado
export let arquivoSelecionadoAuditadoEvidencia = null;
export let anexoExistenteAuditadoEvidencia = null;

// Variável para o tipo atual do checklist
export let tipoAtual = null;

// ============================================================
// FUNÇÕES PARA MANIPULAR O ESTADO
// ============================================================

export function setProcessoId(id) {
    processoIdAtual = id;
}

export function setAuditoriaId(id) {
    auditoriaIdAtual = id;
}

export function setAnalisesAuditorList(lista) {
    analisesAuditorList = lista;
}

export function setAnalisesAuditadoList(lista) {
    analisesAuditadoList = lista;
}

export function setCurrentRespostaId(id) {
    currentRespostaId = id;
}

export function setCurrentRespostaIds(ids) {
    currentRespostaIds = ids;
}

export function setArquivosPendentes(arquivos) {
    arquivosPendentes = arquivos;
}

export function setArquivoSelecionadoAuditadoEvidencia(arquivo) {
    arquivoSelecionadoAuditadoEvidencia = arquivo;
}

export function setAnexoExistenteAuditadoEvidencia(nome) {
    anexoExistenteAuditadoEvidencia = nome;
}

export function setArquivoSelecionadoAuditor(arquivo) {
    arquivoSelecionadoAuditor = arquivo;
}

export function setAnexoExistenteNomeAuditor(nome) {
    anexoExistenteNomeAuditor = nome;
}