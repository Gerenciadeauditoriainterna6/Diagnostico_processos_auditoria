// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================

export function getSugestaoImplantadaValue(selectValue) {
    if (selectValue === 'true') return true;
    if (selectValue === 'false') return false;
    return null;
}

export function setSugestaoImplantadaSelect(selectElement, valor) {
    if (valor === true) selectElement.value = 'true';
    else if (valor === false) selectElement.value = 'false';
    else selectElement.value = '';
}

export function formatarData(dataISO) {
    if (!dataISO) return '';
    const partes = dataISO.split('-');
    if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`;
    return dataISO;
}

export function escapeHtml(text) { 
    return text ? text.replace(/[&<>]/g, function(m) { 
        if (m === '&') return '&amp;'; 
        if (m === '<') return '&lt;'; 
        if (m === '>') return '&gt;'; 
        return m; 
    }) : ''; 
}

export function mostrarToast(mensagem, tipo) { 
    alert(mensagem); 
}

export function converterParaBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('Erro ao ler arquivo'));
        reader.readAsDataURL(file);
    });
}