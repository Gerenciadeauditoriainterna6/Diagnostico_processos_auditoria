// ====== ATUALIZAR CONTADOR DE FUNCIONÁRIOS DE UMA ÁREA ======
async function atualizarContadorArea(areaId) {
  try {
    const response = await fetchComAutenticacao(`/api/area/${areaId}/funcionarios`);
    const funcionarios = await response.json();
    const count = funcionarios.length;

    const countSpan = document.querySelector(
      `#func-count-${areaId} .count-number`,
    );
    if (countSpan) {
      countSpan.textContent = count;
    }
  } catch (error) {
    console.error(`Erro ao atualizar contador da área ${areaId}:`, error);
  }
}

// ====== ORDENAÇÃO ======
let ordemAtual = "nome_asc"; // Valor padrão

// ====== PAGINAÇÃO ======
let paginaAtual = 1;
let itensPorPagina = 3;
let todasAreasLista = [];

// ====== VARIÁVEIS DO ORGANOGRAMA ======
let arquivoOrganograma = null;
let organogramaExistente = null;
let organogramaAreaId = null;

// ====== CONVERTER ARQUIVO PARA BASE64 ======
function converterParaBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
    reader.readAsDataURL(file);
  });
}

// ====== CARREGAR ORGANOGRAMA EXISTENTE ======
async function carregarOrganograma(areaId) {
  try {
    const response = await fetchComAutenticacao(`/api/area/${areaId}/organograma`);
    const data = await response.json();

    const infoDiv = document.getElementById("organograma_info");
    const nomeSpan = document.getElementById("organograma_nome_exibicao");
    const icone = document.getElementById("organograma_icone");

    if (data.tem_organograma) {
      organogramaExistente = data.url;
      nomeSpan.textContent = data.nome || "Organograma";

      // Definir ícone baseado na extensão
      const extensao = (data.nome || "").split(".").pop().toLowerCase();
      if (extensao === "pdf") {
        icone.className = "fas fa-file-pdf";
      } else if (["png", "jpg", "jpeg"].includes(extensao)) {
        icone.className = "fas fa-file-image";
      } else {
        icone.className = "fas fa-file";
      }

      infoDiv.style.display = "block";
    } else {
      infoDiv.style.display = "none";
      organogramaExistente = null;
    }
  } catch (error) {
    console.error("Erro ao carregar organograma:", error);
  }
}

// ====== CONFIGURAR UPLOAD DO ORGANOGRAMA ======
function setupOrganogramaUpload(areaId) {
  organogramaAreaId = areaId;

  const inputFile = document.getElementById("organograma_input");
  const btnUpload = document.getElementById("btn_upload_organograma");
  const btnRemover = document.getElementById("btn_remover_organograma");
  const btnVisualizar = document.getElementById("btn_visualizar_organograma");
  const infoDiv = document.getElementById("organograma_info");
  const nomeSpan = document.getElementById("organograma_nome_exibicao");
  const icone = document.getElementById("organograma_icone");

  if (!btnUpload) return;

  // Carregar organograma existente
  carregarOrganograma(areaId);

  // ⭐ REMOVER LISTENERS ANTERIORES (clonando os elementos)
  // Isso remove todos os listeners antigos
  const newInputFile = inputFile.cloneNode(true);
  inputFile.parentNode.replaceChild(newInputFile, inputFile);

  const newBtnUpload = btnUpload.cloneNode(true);
  btnUpload.parentNode.replaceChild(newBtnUpload, btnUpload);

  // Atualizar referências para os novos elementos
  const currentInputFile = document.getElementById("organograma_input");
  const currentBtnUpload = document.getElementById("btn_upload_organograma");
  const currentBtnRemover = document.getElementById("btn_remover_organograma");
  const currentBtnVisualizar = document.getElementById(
    "btn_visualizar_organograma",
  );
  const currentInfoDiv = document.getElementById("organograma_info");
  const currentNomeSpan = document.getElementById("organograma_nome_exibicao");
  const currentIcone = document.getElementById("organograma_icone");

  // Botão de upload - listener de click
  currentBtnUpload.addEventListener("click", () => {
    currentInputFile.click();
  });

  // Quando selecionar um arquivo
  currentInputFile.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validar tipo
    const tiposPermitidos = ["application/pdf", "image/png", "image/jpeg"];
    if (!tiposPermitidos.includes(file.type)) {
      mostrarToast("⚠️ Apenas PDF, PNG e JPG são permitidos", "warning");
      currentInputFile.value = "";
      return;
    }

    // Validar tamanho (5MB)
    if (file.size > 5 * 1024 * 1024) {
      mostrarToast("⚠️ Arquivo muito grande. Máximo 5MB", "warning");
      currentInputFile.value = "";
      return;
    }

    arquivoOrganograma = file;
    currentNomeSpan.textContent = file.name;

    // Definir ícone
    const extensao = file.name.split(".").pop().toLowerCase();
    if (extensao === "pdf") {
      currentIcone.className = "fas fa-file-pdf";
    } else if (["png", "jpg", "jpeg"].includes(extensao)) {
      currentIcone.className = "fas fa-file-image";
    } else {
      currentIcone.className = "fas fa-file";
    }

    currentInfoDiv.style.display = "block";
    organogramaExistente = null;

    mostrarToast(
      "📎 Arquivo selecionado. Salve a área para confirmar.",
      "info",
    );
  });

  // Botão de remover
  if (currentBtnRemover) {
    currentBtnRemover.addEventListener("click", async () => {
      if (!organogramaExistente && !arquivoOrganograma) {
        currentInfoDiv.style.display = "none";
        return;
      }

      // Se tem arquivo existente no banco, confirmar remoção
      if (organogramaExistente) {
        const confirmado = await mostrarConfirmacao(
          "Tem certeza que deseja remover o organograma?",
        );
        if (!confirmado) return;

        // Remover via API
        try {
          const response = await fetchComAutenticacao(`/api/area/${areaId}/organograma`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
          });
          const data = await response.json();

          if (data.success) {
            mostrarToast("✅ Organograma removido com sucesso!", "success");
            currentInfoDiv.style.display = "none";
            organogramaExistente = null;
            arquivoOrganograma = null;
            currentInputFile.value = "";
          } else {
            mostrarToast("❌ Erro ao remover organograma", "error");
          }
        } catch (error) {
          console.error("Erro:", error);
          mostrarToast("❌ Erro de conexão", "error");
        }
      } else {
        // Apenas remove o arquivo selecionado (não salvo ainda)
        currentInfoDiv.style.display = "none";
        arquivoOrganograma = null;
        currentInputFile.value = "";
        mostrarToast("Arquivo removido", "info");
      }
    });
  }

  // ⭐ CORRIGIR: Botão de visualizar (usar URL assinada)
  if (currentBtnVisualizar) {
    currentBtnVisualizar.addEventListener("click", () => {
      if (organogramaExistente) {
        // ⭐ Usar a função com URL assinada
        visualizarOrganograma(areaId);
      } else if (arquivoOrganograma) {
        const url = URL.createObjectURL(arquivoOrganograma);
        window.open(url, "_blank");
        setTimeout(() => URL.revokeObjectURL(url), 10000);
      } else {
        mostrarToast("Nenhum organograma para visualizar", "warning");
      }
    });
  }
}

// ====== CONFIGURAR UPLOAD DO ORGANOGRAMA - NOVA ÁREA ======
function setupOrganogramaUploadNova() {
  const inputFile = document.getElementById("organograma_input_nova");
  const btnUpload = document.getElementById("btn_upload_organograma_nova");
  const btnRemover = document.getElementById("btn_remover_organograma_nova");
  const btnVisualizar = document.getElementById("btn_visualizar_organograma");
  const infoDiv = document.getElementById("organograma_info_nova");
  const nomeSpan = document.getElementById("organograma_nome_exibicao_nova");
  const icone = document.getElementById("organograma_icone_nova");

  if (!btnUpload) return;

  // Botão de upload
  btnUpload.addEventListener("click", () => {
    inputFile.click();
  });

  // Quando selecionar um arquivo
  inputFile.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validar tipo
    const tiposPermitidos = ["application/pdf", "image/png", "image/jpeg"];
    if (!tiposPermitidos.includes(file.type)) {
      mostrarToast("⚠️ Apenas PDF, PNG e JPG são permitidos", "warning");
      inputFile.value = "";
      return;
    }

    // Validar tamanho (5MB)
    if (file.size > 5 * 1024 * 1024) {
      mostrarToast("⚠️ Arquivo muito grande. Máximo 5MB", "warning");
      inputFile.value = "";
      return;
    }

    arquivoOrganograma = file;
    nomeSpan.textContent = file.name;

    // Definir ícone
    const extensao = file.name.split(".").pop().toLowerCase();
    if (extensao === "pdf") {
      icone.className = "fas fa-file-pdf";
    } else if (["png", "jpg", "jpeg"].includes(extensao)) {
      icone.className = "fas fa-file-image";
    } else {
      icone.className = "fas fa-file";
    }

    infoDiv.style.display = "block";
    mostrarToast(
      "📎 Arquivo selecionado. Salve a área para confirmar.",
      "info",
    );
  });

  // Botão de remover (apenas remove o arquivo selecionado, não salvo ainda)
  btnRemover?.addEventListener("click", () => {
    infoDiv.style.display = "none";
    arquivoOrganograma = null;
    inputFile.value = "";
    mostrarToast("Arquivo removido", "info");
  });

  // ⭐ CORRIGIR: Botão de visualizar (usar URL assinada)
  btnVisualizar?.addEventListener("click", () => {
    if (organogramaExistente) {
      // ⭐ Se tiver organograma existente (edição), usar URL assinada
      visualizarOrganograma(organogramaAreaId);
    } else if (arquivoOrganograma) {
      const url = URL.createObjectURL(arquivoOrganograma);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } else {
      mostrarToast("Nenhum organograma para visualizar", "warning");
    }
  });
}

// ====== SALVAR ORGANOGRAMA ======
async function salvarOrganograma(areaId) {
  if (!arquivoOrganograma) return null;

  try {
    const base64 = await converterParaBase64(arquivoOrganograma);

    const response = await fetchComAutenticacao(`/api/area/${areaId}/upload-organograma`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        arquivo_base64: base64,
        nome_arquivo: arquivoOrganograma.name,
        tipo_arquivo: arquivoOrganograma.type,
      }),
    });

    const data = await response.json();

    if (data.success) {
      arquivoOrganograma = null;
      organogramaExistente = data.url;
      return data;
    } else {
      mostrarToast(
        "❌ Erro ao salvar organograma: " + (data.error || "Erro desconhecido"),
        "error",
      );
      return null;
    }
  } catch (error) {
    console.error("Erro ao salvar organograma:", error);
    mostrarToast("❌ Erro de conexão ao salvar organograma", "error");
    return null;
  }
}

function ordenarAreas(areas, criterio) {
  const areasCopy = [...areas]; // Criar cópia para não modificar original

  switch (criterio) {
    case "nome_asc":
      return areasCopy.sort((a, b) =>
        (a.nome_area || "").localeCompare(b.nome_area || ""),
      );
    case "nome_desc":
      return areasCopy.sort((a, b) =>
        (b.nome_area || "").localeCompare(a.nome_area || ""),
      );
    case "status_asc":
      // Ativos primeiro
      return areasCopy.sort((a, b) => {
        const statusA = (a.status || "Ativo") === "Ativo" ? 0 : 1;
        const statusB = (b.status || "Ativo") === "Ativo" ? 0 : 1;
        return statusA - statusB;
      });
    case "status_desc":
      // Inativos primeiro
      return areasCopy.sort((a, b) => {
        const statusA = (a.status || "Ativo") === "Ativo" ? 0 : 1;
        const statusB = (b.status || "Ativo") === "Ativo" ? 0 : 1;
        return statusB - statusA;
      });
    case "data_asc":
      // Mais antigos primeiro (por id_area, que é sequencial)
      return areasCopy.sort((a, b) => (a.id_area || 0) - (b.id_area || 0));
    case "data_desc":
      // Mais recentes primeiro (por id_area, que é sequencial)
      return areasCopy.sort((a, b) => (b.id_area || 0) - (a.id_area || 0));
    default:
      return areasCopy;
  }
}

// ====== MODAL DE CONFIRMAÇÃO PERSONALIZADO ======
let confirmacaoResolve = null;

function mostrarConfirmacao(mensagem) {
  return new Promise((resolve) => {
    const modal = document.getElementById("modalConfirmacao");
    const mensagemEl = document.getElementById("mensagemConfirmacao");
    const btnConfirmar = document.getElementById("btnConfirmarAcao");
    const btnCancelar = document.getElementById("btnCancelarConfirmacao");
    const btnFechar = document.getElementById("btnFecharConfirmacao");

    mensagemEl.textContent = mensagem;
    modal.style.display = "block";
    document.body.style.overflow = "hidden";

    function resolver(valor) {
      modal.style.display = "none";
      document.body.style.overflow = "auto";
      confirmacaoResolve = null;
      resolve(valor);
    }

    const handleConfirmar = () => resolver(true);
    const handleCancelar = () => resolver(false);

    btnConfirmar.addEventListener("click", handleConfirmar, { once: true });
    btnCancelar.addEventListener("click", handleCancelar, { once: true });
    btnFechar.addEventListener("click", handleCancelar, { once: true });

    // Clicar fora do modal também cancela
    modal.addEventListener(
      "click",
      (e) => {
        if (e.target === modal) resolver(false);
      },
      { once: true },
    );

    confirmacaoResolve = resolver;
  });
}

// ====== FORMATAR TELEFONE PARA EXIBIÇÃO ======
function formatarTelefoneExibicao(telefone) {
  if (!telefone) return "Não informado";

  // Remove tudo que não é número (por segurança)
  const numeros = telefone.toString().replace(/\D/g, "");

  if (numeros.length === 0) return "Não informado";

  // Aplica a máscara (XX) XXXXX-XXXX
  if (numeros.length <= 10) {
    // Telefone fixo: (XX) XXXX-XXXX
    return numeros.replace(/(\d{2})(\d{4})(\d{4})/, "($1) $2-$3");
  } else {
    // Celular: (XX) XXXXX-XXXX
    return numeros.replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
  }
}

// ====== BUSCAR CONTAGEM DE FUNCIONÁRIOS ======
async function buscarContagemFuncionarios(areaId) {
  try {
    const response = await fetchComAutenticacao(`/api/area/${areaId}/funcionarios`);
    const funcionarios = await response.json();
    return funcionarios.length;
  } catch (error) {
    console.error("Erro ao buscar funcionários da área ${areaId}:", error);
    return 0;
  }
}

// ====== PERFIL DO USUÁRIO ======
const usuarioPerfil = "{{ usuario_perfil }}";
const isAdmin = usuarioPerfil === "administrador" || usuarioPerfil === "admin";
console.log("Perfil do usuário:", usuarioPerfil, "é admin?", isAdmin);

// ====== CARREGAR DETALHES DA ÁREA ======

async function carregarDetalhesArea(areaId) {
  console.log("carregarDetalhesArea chamado com areaId:", areaId);

  if (!areaId) {
    console.error("areaId é undefined!");
    return;
  }

  try {
    const response = await fetchComAutenticacao(`/api/area/${areaId}`);
    const area = await response.json();

    const container = document.querySelector(".area-details");

    if (!area) {
      container.innerHTML = '<p class="text-muted">Área não encontrada</p>';
      return;
    }

    // Renderizar detalhes da área
    container.innerHTML = `
            <div class="area-detail-content">
                <!-- ==== PARTE 1: CABEÇALHO E STATUS ==== -->
                <div class="detail-header">
                    <h2><i class="fas fa-building"></i> ${area.nome_area}</h2>
                    <span class="detail-status ${area.status === "Ativo" ? "status-ativo" : "status-inativo"}">
                        ${area.status === "Ativo" ? "ATIVA" : "INATIVA"}
                    </span>
                </div>

                <!-- ==== PARTE 2: UNIDADE ==== -->
                <div class="info-group">
                    <label><i class="fas fa-map-marker-alt"></i> <strong>Unidade</strong></label>
                    <p>${area.unidade || area.loc_unidade || "Não informado"}</p>
                </div>
                
                <!-- ==== PARTE 3: DEMAIS INFORMAÇÕES ==== -->
                <div class="detail-info">
                    <div class="info-group"><label>Gestor</label><p>${area.gestor || "Não informado"}</p></div>
                    <div class="info-group"><label>Superintendente</label><p>${area.superintendente || "Não informado"}</p></div>
                    <div class="info-group"><label>Diretor</label><p>${area.diretor || "Não informado"}</p></div>
                    <div class="info-group"><label>E-mail</label><p>${area.email || "Não informado"}</p></div>
                    <div class="info-group"><label>Telefone</label><p>${formatarTelefoneExibicao(area.telefone) || "Não informado"}</p></div>
                    <div class="info-group"><label>Objetivo da área</label><p>${area.objetivo_area || "Não informado"}</p></div>
                </div>

                
                <div class="info-group">
                    <label><i class="fas fa-sitemap"></i> Organograma</label>
                    ${
                      area.organograma_url
                        ? `
                        <p style="margin-top: 10px;">
                            <button onclick="visualizarOrganograma(${area.id_area})" 
                                    class="btn-download-anexo" 
                                    style="display: inline-flex; padding: 4px 12px; font-size: 12px; background: #184145; color: white; border-radius: 6px; text-decoration: none; align-items: center; gap: 8px; border: none; cursor: pointer;">
                                <i class="fas fa-eye"></i> Ver organograma
                            </button>
                            <span style="font-size: 11px; color: #666; margin-left: 8px;">${area.organograma_nome || ""}</span>
                            <button onclick="baixarOrganograma(${area.id_area})" 
                                    style="background: none; border: none; color: #0b5b99; cursor: pointer; margin-left: 8px; font-size: 14px;" 
                                    title="Baixar organograma">
                                <i class="fas fa-download"></i>
                            </button>
                        </p>
                    `
                        : `
                        <p>Não informado</p>
                    `
                    }
                </div>
                
                <!-- ==== PARTE 4: FUNCIONÁRIOS (é aqui que você está pensando) ==== -->
                <div class="funcionarios-section">
                    <h3><i class="fas fa-users"></i> Funcionários</h3>
                    <div id="funcionariosList">
                        <p class="text-muted">Carregando funcionários...</p>
                    </div>
                    ${
                      area.status === "Ativo"
                        ? `
                    <button id="btnAddFuncionario">
                        <i class="fas fa-user-plus"></i> Adicionar Funcionário
                    </button>
                    `
                        : `
                    <div class="area-inativa-alert">
                        <i class="fas fa-info-circle"></i> Área inativa. Não é possível adicionar funcionários.
                    </div>
                    `
                    }
                </div>
            </div>
        `;

    // Carregar funcionários da área

    carregarFuncionariosArea(areaId, area.status === "Ativo");

    // ====== ADICIONAR EVENTO AO BOTÃO ADICIONAR FUNCIONÁRIO ======
    const btnAdd = document.getElementById("btnAddFuncionario");
    if (btnAdd) {
      btnAdd.addEventListener("click", () => {
        if (window.abrirModalFuncionario) {
          window.abrirModalFuncionario(areaId);
        }
      });
    }
  } catch (error) {
    console.error("Erro ao carregar detalhes:", error);
    document.querySelector(".area-details").innerHTML =
      '<p class="text-muted">Erro ao carregar detalhes</p>';
  }
}

// ====== CARREGAR FUNCIONÁRIOS DA ÁREA ======
async function carregarFuncionariosArea(areaId, isAreaAtiva) {
  console.log(
    "carregarFuncionariosArea chamado com areaId:",
    areaId,
    "isAreaAtiva:",
    isAreaAtiva,
  );

  try {
    // SEMPRE buscar TODOS os funcionários (ativos e inativos)
    const endpoint = `/api/area/${areaId}/todos-funcionarios`;
    const response = await fetchComAutenticacao(endpoint);

    console.log("Resposta da API:", response.status);

    if (!response.ok) {
      console.error("Erro na API:", response.status);
      const container = document.getElementById("funcionariosList");
      if (container) {
        container.innerHTML =
          '<p class="text-muted">Erro ao carregar funcionários</p>';
      }
      return;
    }

    const funcionarios = await response.json();
    console.log("Funcionários recebidos:", funcionarios);

    const container = document.getElementById("funcionariosList");

    if (!container) return;

    if (!funcionarios || funcionarios.length === 0) {
      container.innerHTML =
        '<p class="text-muted">Nenhum funcionário cadastrado nesta área</p>';
      return;
    }

    // Renderizar funcionários
    container.innerHTML = funcionarios
      .map((func) => {
        const funcId = func.id;
        const isFuncAtivo = func.ativo !== false;
        const statusBadge = !isFuncAtivo
          ? '<span class="badge-func-inativo">INATIVO</span>'
          : "";

        return `
                <div class="funcionario-item ${!isFuncAtivo ? "funcionario-inativo" : ""}" data-func-id="${funcId}">
                    <div class="funcionario-info">
                        <strong><i class="fas fa-user"></i> ${func.nome_funcionario} ${statusBadge}</strong>
                        <span class="funcionario-cargo">${func.cargo || "Cargo não informado"}</span>
                    </div>
                    <div class="funcionario-datas">
                        <small><i class="fas fa-clock"></i> Tempo na função: ${func.tempo_funcao || "Não informado"}</small>
                        <small><i class="fas fa-building"></i> Tempo na empresa: ${func.tempo_empresa || "Não informado"}</small>
                    </div>
                    ${
                      isAreaAtiva && isFuncAtivo
                        ? `
                    <div class="funcionario-actions">
                        <button class="btn-edit-icon btn-edit-func" data-id="${funcId}" data-nome="${func.nome_funcionario}" title="Editar Funcionário">
                            <i class="fas fa-pencil-alt"></i>
                        </button>
                        <button class="btn-delete-icon btn-delete-func" data-id="${funcId}" data-nome="${func.nome_funcionario}" title="Excluir Funcionário">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                    `
                        : ""
                    }
                </div>
            `;
      })
      .join("");

    // ====== ADICIONAR EVENTO DE EXCLUSÃO (apenas se for admin e área ativa) ======

    document.querySelectorAll(".btn-delete-func").forEach((btn) => {
      btn.removeEventListener("click", btn.clickHandler);
      btn.clickHandler = async (e) => {
        e.stopPropagation();
        const funcId = btn.getAttribute("data-id");
        const funcNome = btn.getAttribute("data-nome");
        const confirmado = await mostrarConfirmacao(
          `Tem certeza que deseja excluir o funcionário "${funcNome}"?`,
        );
        if (confirmado) {
          await excluirFuncionario(funcId, areaId, btn);
        }
      };
      btn.addEventListener("click", btn.clickHandler);
    });

    document.querySelectorAll(".btn-edit-func").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const funcId = btn.getAttribute("data-id");
        await abrirModalEditarFuncionario(funcId, areaId);
      });
    });

    console.log("✅ Lista de funcionários atualizada com sucesso!");
  } catch (error) {
    console.error("Erro detalhado ao carregar funcionários:", error);
    const container = document.getElementById("funcionariosList");
    if (container) {
      container.innerHTML =
        '<p class="text-muted">Erro ao carregar funcionários</p>';
    }
  }
}

async function excluirFuncionario(funcionarioId, areaId, btnElement) {
  try {
    // ======= LOADING STATE =======
    const textoOriginal = btnElement.innerHTML;
    btnElement.disabled = true;
    btnElement.classList.add("btn-loading");
    btnElement.innerHTML = '<i class="fas fa-spinner"></i> Excluindo...';

    const response = await fetchComAutenticacao(`/api/funcionario/${funcionarioId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const resultado = await response.json();

    if (resultado.success) {
      mostrarToast("Funcionário excluído com sucesso!", "success");
      // Recarregar APENAS a lista de funcionários
      await carregarFuncionariosArea(areaId);

      // ====== ATUALIZAR CONTADOR DA ÁREA ======
      await atualizarContadorArea(areaId);

      // Garantir que o card da área continue selecionado
      document.querySelectorAll(".area-card").forEach((card) => {
        if (card.getAttribute("data-id") == areaId) {
          card.classList.add("selected");
        }
      });
    } else {
      mostrarToast("❌ Erro ao excluir funcionário. Tente novamente.", "error");
    }
  } catch (error) {
    console.error("Erro ao excluir:", error);
    mostrarToast("❌ Erro de conexão. Verifique sua internet.", "error");
  } finally {
    // ====== RESTAURAR BOTÃO ======
    btnElement.disabled = false;
    btnElement.classList.remove("btn-loading");
    btnElement.innerHTML = textoOriginal;
  }
}

// ====== EXCLUIR ÁREA (DESATIVAR) ======
async function excluirArea(areaId, areaNome, btnElement) {
  try {
    // ====== LOADING STATE ======
    const textoOriginal = btnElement.innerHTML;
    btnElement.disabled = true;
    btnElement.classList.add("btn-loading");
    btnElement.innerHTML = '<i class="fas fa-spinner"></i> Desativando...';

    const response = await fetchComAutenticacao(`/api/area/${areaId}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    });

    const resultado = await response.json();

    if (resultado.success) {
      mostrarToast(`Área "${areaNome}" desativada com sucesso!`, "success");
      await carregarDados(); // Recarregar lista e métricas
      // Limpar painel direito
      document.querySelector(".area-details").innerHTML = `
                <div class="details-placeholder">
                    <i class="fas fa-building fa-3x"></i>
                    <p>Selecione uma área para ver os detalhes</p>
                </div>
            `;
    } else {
      mostrarToast("❌ Erro ao desativar área. Tente novamente.", "error");
    }
  } catch (error) {
    console.error("Erro:", error);
    mostrarToast("❌ Erro de conexão.", "error");
  } finally {
    // ====== RESTAURAR BOTÃO ======
    btnElement.disabled = false;
    btnElement.classList.remove("btn-loading");
    btnElement.innerHTML = textoOriginal;
  }
}

function limparMascaraTelefone(valor) {
  return valor.replace(/\D/g, "");
}

// ====== CARREGAR DADOS INICIAIS ======
async function carregarDados() {
  await carregarAreas();
}

carregarDados();

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("modalNovaArea");
  const btnNovaArea = document.getElementById("btnNovaArea");
  const btnFecharModal = document.getElementById("btnFecharModal");
  const btnCancelarModal = document.getElementById("btnCancelarModal");

  // Evento de ordenação
  const orderBySelect = document.getElementById("orderBySelect");
  if (orderBySelect) {
    orderBySelect.addEventListener("change", () => {
      ordemAtual = orderBySelect.value;
      paginaAtual = 1;
      aplicarFiltroOuPagina();
    });
  }

  // Abrir modal
  if (btnNovaArea) {
    btnNovaArea.addEventListener("click", () => {
      console.log("Botão Nova Área clicado!");
      modal.style.display = "block";
      document.body.style.overflow = "hidden";
    });
  }

  // Fechar modal
  function fecharModal() {
    modal.style.display = "none";
    document.body.style.overflow = "auto";
  }

  if (btnFecharModal) {
    btnFecharModal.addEventListener("click", fecharModal);
  }

  if (btnCancelarModal) {
    btnCancelarModal.addEventListener("click", fecharModal);
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal && modal.style.display === "block") {
      fecharModal();
    }
  });

  // ====== SALVAR NOVA ÁREA ======
  const formNovaArea = document.getElementById("formNovaArea");
  if (formNovaArea) {
    formNovaArea.addEventListener("submit", async (e) => {
      e.preventDefault();

      const btnSubmit = document.querySelector(
        "#modalNovaArea .btn-salvar-area",
      );
      if (!btnSubmit) {
        console.error("❌ Botão Salvar não encontrado!");
        return;
      }

      const textoOriginal = btnSubmit.innerHTML;

      btnSubmit.disabled = true;
      btnSubmit.classList.add("btn-loading");
      btnSubmit.innerHTML = '<i class="fas fa-spinner"></i> Salvando...';

      const dados = {
        nome: document.getElementById("nome_area").value.trim().toUpperCase(),
        loc_unidade: document
          .getElementById("unidade_area")
          .value.trim()
          .toUpperCase(),
        email: document.getElementById("email").value.trim().toLowerCase(), // email em minúsculas
        telefone: limparMascaraTelefone(
          document.getElementById("telefone").value,
        ),
        gestor: document.getElementById("gestor").value.trim().toUpperCase(),
        superintendente: document
          .getElementById("superintendente")
          .value.trim()
          .toUpperCase(),
        diretor: document.getElementById("diretor").value.trim().toUpperCase(),
        objetivo: document
          .getElementById("objetivo")
          .value.trim()
          .toUpperCase(),
        status: "Ativo",
      };

      if (!dados.nome || !dados.gestor) {
        mostrarToast(
          "Preencha os campos obrigatórios: Nome da Área e Gestor",
          "error",
        );
        btnSubmit.disabled = false;
        btnSubmit.classList.remove("btn-loading");
        btnSubmit.innerHTML = textoOriginal;
        return;
      }

      try {
        const response = await fetchComAutenticacao("/api/salvar-area", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(dados),
        });

        const resultado = await response.json();

        if (resultado.success) {
          const novaAreaId = resultado.id;
          mostrarToast("Área cadastrada com sucesso!", "success");

          if (arquivoOrganograma && novaAreaId) {
            console.log("📎 Salvando organograma da nova área...");
            const resultadoOrganograma = await salvarOrganograma(novaAreaId);
            if (resultadoOrganograma) {
              console.log("✅ Organograma salvo:", resultadoOrganograma);
            } else {
              console.warn("⚠️ Organograma não foi salvo");
            }
          }

          fecharModal();
          formNovaArea.reset();
          await carregarDados();
        } else {
          mostrarToast("❌ Erro ao cadastrar área. Tente novamente.", "error");
        }
      } catch (error) {
        console.error("Erro:", error);
        mostrarToast("❌ Erro de conexão. Verifique sua internet.", "error");
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.classList.remove("btn-loading");
        btnSubmit.innerHTML = textoOriginal;
      }
    });
  }

  // ⭐⭐⭐ ADICIONAR AQUI - NO FINAL DO DOMContentLoaded ⭐⭐⭐
  // ====== CONFIGURAR ORGANOGRAMA PARA NOVA ÁREA ======
  setupOrganogramaUploadNova();
});

// ====== MODAL ADICIONAR FUNCIONÁRIO ======
let areaIdAtual = null;

document.addEventListener("DOMContentLoaded", function () {
  const modalFunc = document.getElementById("modalAddFuncionario");
  const btnAddFuncionario = document.getElementById("btnAddFuncionario");
  const btnFecharModalFunc = document.getElementById("btnFecharModalFunc");
  const btnCancelarModalFunc = document.getElementById("btnCancelarModalFunc");
  const formAddFuncionario = document.getElementById("formAddFuncionario");

  // Função para abrir o modal
  window.abrirModalFuncionario = function (areaId) {
    areaIdAtual = areaId;
    document.getElementById("func_area_id").value = areaId;
    modalFunc.style.display = "block";
    document.body.style.overflow = "hidden";
    // Limpar formulário
    formAddFuncionario.reset();
  };

  // Fechar modal
  function fecharModalFunc() {
    modalFunc.style.display = "none";
    document.body.style.overflow = "auto";
    areaIdAtual = null;
  }

  if (btnFecharModalFunc)
    btnFecharModalFunc.addEventListener("click", fecharModalFunc);
  if (btnCancelarModalFunc)
    btnCancelarModalFunc.addEventListener("click", fecharModalFunc);

  // Salvar funcionário
  if (formAddFuncionario) {
    formAddFuncionario.addEventListener("submit", async (e) => {
      e.preventDefault();

      // ====== LOADING STATE ======
      const btnSubmit = formAddFuncionario.querySelector(
        'button[type="submit"]',
      );
      const textoOriginal = btnSubmit.innerHTML;

      btnSubmit.disabled = true;
      btnSubmit.classList.add("btn-loading");
      btnSubmit.innerHTML = '<i class="fas fa-spinner"></i> Salvando...';

      // ====== VALIDAÇÃO DE DATAS ======
      const dataFuncao = document.getElementById("func_data_funcao").value;
      const dataEmpresa = document.getElementById("func_data_empresa").value;
      const erroDataDiv = document.getElementById("erroData");

      if (dataFuncao && dataEmpresa) {
        const dataFuncaoObj = new Date(dataFuncao);
        const dataEmpresaObj = new Date(dataEmpresa);

        if (dataFuncaoObj < dataEmpresaObj) {
          erroDataDiv.style.display = "block";
          // Restaura botão
          btnSubmit.disabled = false;
          btnSubmit.classList.remove("btn-loading");
          btnSubmit.innerHTML = textoOriginal;
          return;
        } else {
          erroDataDiv.style.display = "none";
        }
      } else {
        erroDataDiv.style.display = "none";
      }

      const dados = {
        id_area: document.getElementById("func_area_id").value,
        nome: document.getElementById("func_nome").value.trim().toUpperCase(),
        cargo: document.getElementById("func_cargo").value.trim().toUpperCase(),
        data_inicio_funcao:
          document.getElementById("func_data_funcao").value || null,
        data_inicio_empresa:
          document.getElementById("func_data_empresa").value || null,
      };

      if (!dados.nome) {
        mostrarToast("❌ O nome do funcionário é obrigatório.", "error");
        // Restaurar botão
        btnSubmit.disabled = false;
        btnSubmit.classList.remove("btn-loading");
        btnSubmit.innerHTML = textoOriginal;
        return;
      }

      // SALVAR O ID DA ÁREA EM UMA VARIÁVEL TEMPORÁRIA ANTES DE FECHAR
      const areaIdParaRecarregar = areaIdAtual;

      try {
        const response = await fetchComAutenticacao("/api/salvar-funcionario", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(dados),
        });

        const resultado = await response.json();

        if (resultado.success) {
          mostrarToast("Funcionário cadastrado com sucesso!", "success");

          // Fechar o modal (isso vai definir areaIdAtual = null)
          fecharModalFunc();

          // USAR A VARIÁVEL TEMPORÁRIA PARA RECARREGAR
          if (areaIdParaRecarregar) {
            console.log(
              "Recarregando funcionários para área:",
              areaIdParaRecarregar,
            );
            await carregarFuncionariosArea(areaIdParaRecarregar);

            // ====== ATUALIZAR CONTADOR DA ÁREA ======
            await atualizarContadorArea(areaIdParaRecarregar);

            // Garantir que o card da área continue selecionado
            document.querySelectorAll(".area-card").forEach((card) => {
              const cardId = card.getAttribute("data-id");
              if (cardId == areaIdParaRecarregar) {
                card.classList.add("selected");
              }
            });
          } else {
            console.error("areaIdParaRecarregar está null!");
            location.reload();
          }
        } else {
          console.error("areaIdParaRecarregar está null!");
          mostrarToast(
            "❌ Erro ao cadastrar funcionário. Tente novamente.",
            "error",
          );
          location.reload();
        }
      } catch (error) {
        console.error("Erro:", error);
        mostrarToast("❌ Erro de conexão. Verifique sua internet.", "error");
      } finally {
        // ====== RESTAURAR BOTÃO ======
        btnSubmit.disabled = false;
        btnSubmit.classList.remove("btn-loading");
        btnSubmit.innerHTML = textoOriginal;
      }
    });
  }
});

// ====== MÁSCARA DE TELEFONE ======
function aplicarMascaraTelefone(input) {
  let valor = input.value.replace(/\D/g, ""); // Remove tudo que não é número

  if (valor.length === 0) {
    input.value = "";
    return;
  }

  // Aplica a máscara (XX) XXXXX-XXXX
  if (valor.length <= 10) {
    // Telefone fixo: (XX) XXXX-XXXX
    valor = valor.replace(/(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3");
  } else {
    // Celular: (XX) XXXXX-XXXX
    valor = valor.replace(/(\d{2})(\d{5})(\d{0,4})/, "($1) $2-$3");
  }

  input.value = valor;
}

// ====== EDITAR ÁREA ======
const modalEditarArea = document.getElementById("modalEditarArea");
const btnFecharEditarArea = document.getElementById("btnFecharEditarArea");
const btnCancelarEditarArea = document.getElementById("btnCancelarEditarArea");
const formEditarArea = document.getElementById("formEditarArea");

function fecharModalEditarArea() {
  modalEditarArea.style.display = "none";
  document.body.style.overflow = "auto";
}

if (btnFecharEditarArea)
  btnFecharEditarArea.addEventListener("click", fecharModalEditarArea);
if (btnCancelarEditarArea)
  btnCancelarEditarArea.addEventListener("click", fecharModalEditarArea);

async function abrirModalEditarArea(areaId) {
  try {
    const response = await fetchComAutenticacao(`/api/area/${areaId}`);
    const area = await response.json();

    console.log("=== DEBUG COMPLETO ===");
    console.log("Area completa:", area);
    console.log("loc_unidade:", area.loc_unidade);
    console.log("unidade (se existir):", area.unidade);
    console.log("======================");

    document.getElementById("edit_area_id").value = area.id_area;
    document.getElementById("edit_nome_area").value = area.nome_area || "";

    // Tenta pegar de onde vier
    const valorUnidade = area.loc_unidade || area.unidade || "";
    const selectUnidade = document.getElementById("edit_unidade");

    console.log("Valor que será selecionado:", valorUnidade);

    selectUnidade.value = valorUnidade;

    console.log("Valor após seleção:", selectUnidade.value);
    console.log(
      "Options disponíveis:",
      Array.from(selectUnidade.options).map(
        (opt) => `${opt.value} (${opt.text})`,
      ),
    );

    document.getElementById("edit_email").value = area.email || "";
    document.getElementById("edit_telefone").value = area.telefone || "";
    document.getElementById("edit_gestor").value = area.gestor || "";
    document.getElementById("edit_objetivo").value = area.objetivo_area || "";

    // ⭐ NOVO: Carregar superintendente e diretor
    document.getElementById("edit_superintendente").value =
      area.superintendente || "";
    document.getElementById("edit_diretor").value = area.diretor || "";

    setupOrganogramaUpload(areaId);

    modalEditarArea.style.display = "block";
    document.body.style.overflow = "hidden";
  } catch (error) {
    console.error("Erro ao carregar área:", error);
    mostrarToast("❌ Erro ao carregar dados da área.", "error");
  }
}

// Salvar edição da área
if (formEditarArea) {
  formEditarArea.addEventListener("submit", async (e) => {
    e.preventDefault();

    // ⭐ CORREÇÃO: Buscar o botão pelo ID ou pelo seletor fora do form
    const btnSubmit = document.querySelector(
      "#modalEditarArea .btn-salvar-area",
    );

    if (!btnSubmit) {
      console.error("❌ Botão Salvar não encontrado!");
      return;
    }

    const textoOriginal = btnSubmit.innerHTML;

    btnSubmit.disabled = true;
    btnSubmit.classList.add("btn-loading");
    btnSubmit.innerHTML = '<i class="fas fa-spinner"></i> Salvando...';

    const areaId = document.getElementById("edit_area_id").value;
    const dados = {
      nome: document
        .getElementById("edit_nome_area")
        .value.trim()
        .toUpperCase(),
      loc_unidade: document
        .getElementById("edit_unidade")
        .value.trim()
        .toUpperCase(),
      email: document.getElementById("edit_email").value.trim().toLowerCase(),
      telefone: limparMascaraTelefone(
        document.getElementById("edit_telefone").value,
      ),
      gestor: document.getElementById("edit_gestor").value.trim().toUpperCase(),
      superintendente: document
        .getElementById("edit_superintendente")
        .value.trim()
        .toUpperCase(),
      diretor: document
        .getElementById("edit_diretor")
        .value.trim()
        .toUpperCase(),
      objetivo: document
        .getElementById("edit_objetivo")
        .value.trim()
        .toUpperCase(),
      status: "Ativo",
    };

    console.log("📤 Enviando dados para API:", dados);

    try {
      const response = await fetchComAutenticacao(`/api/area/${areaId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
      });

      const resultado = await response.json();
      console.log("📥 Resposta da API:", resultado);

      if (resultado.success) {
        mostrarToast("Área atualizada com sucesso!", "success");

        const areaIdEditada = document.getElementById("edit_area_id").value;

        // SALVAR ORGANOGRAMA (se houver)
        if (arquivoOrganograma && areaIdEditada) {
          console.log("📎 Salvando organograma...");
          const resultadoOrganograma = await salvarOrganograma(areaIdEditada);
          if (resultadoOrganograma) {
            console.log("✅ Organograma salvo:", resultadoOrganograma);
          } else {
            console.warn("⚠️ Organograma não foi salvo");
          }
        }

        fecharModalEditarArea();

        await carregarAreas();
        await carregarDetalhesArea(areaIdEditada);

        document.querySelectorAll(".area-card").forEach((card) => {
          if (card.getAttribute("data-id") == areaIdEditada) {
            card.classList.add("selected");
          }
        });
      } else {
        mostrarToast("❌ Erro ao atualizar área.", "error");
      }
    } catch (error) {
      console.error("Erro:", error);
      mostrarToast("❌ Erro de conexão.", "error");
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.classList.remove("btn-loading");
      btnSubmit.innerHTML = textoOriginal;
    }
  });
}

// ====== EDITAR FUNCIONÁRIO ======
const modalEditarFuncionario = document.getElementById(
  "modalEditarFuncionario",
);
const btnFecharEditarFuncionario = document.getElementById(
  "btnFecharEditarFuncionario",
);
const btnCancelarEditarFuncionario = document.getElementById(
  "btnCancelarEditarFuncionario",
);
const formEditarFuncionario = document.getElementById("formEditarFuncionario");

function fecharModalEditarFuncionario() {
  modalEditarFuncionario.style.display = "none";
  document.body.style.overflow = "auto";
}

if (btnFecharEditarFuncionario)
  btnFecharEditarFuncionario.addEventListener(
    "click",
    fecharModalEditarFuncionario,
  );
if (btnCancelarEditarFuncionario)
  btnCancelarEditarFuncionario.addEventListener(
    "click",
    fecharModalEditarFuncionario,
  );

async function abrirModalEditarFuncionario(funcionarioId, areaIdAtual) {
  try {
    const response = await fetchComAutenticacao(`/api/funcionario/${funcionarioId}`);
    const func = await response.json();

    document.getElementById("edit_func_id").value = func.id;
    document.getElementById("edit_func_area_id").value = areaIdAtual;
    document.getElementById("edit_func_nome").value =
      func.nome_funcionario || "";
    document.getElementById("edit_func_cargo").value = func.cargo || "";
    document.getElementById("edit_func_data_funcao").value =
      func.data_inicio_funcao || "";
    document.getElementById("edit_func_data_empresa").value =
      func.data_inicio_empresa || "";

    modalEditarFuncionario.style.display = "block";
    document.body.style.overflow = "hidden";
  } catch (error) {
    console.error("Erro ao carregar funcionário:", error);
    mostrarToast("Erro ao carregar dados do funcionário", "error");
  }
}

// Salvar edição do funcionário
if (formEditarFuncionario) {
  formEditarFuncionario.addEventListener("submit", async (e) => {
    e.preventDefault();

    const btnSubmit = formEditarFuncionario.querySelector(
      'button[type="submit"]',
    );
    const textoOriginal = btnSubmit.innerHTML;

    btnSubmit.disabled = true;
    btnSubmit.classList.add("btn-loading");
    btnSubmit.innerHTML = '<i class="fas fa-spinner"></i> Salvando...';

    const funcionarioId = document.getElementById("edit_func_id").value;
    const areaId = document.getElementById("edit_func_area_id").value;
    const dados = {
      nome: document
        .getElementById("edit_func_nome")
        .value.trim()
        .toUpperCase(),
      cargo: document
        .getElementById("edit_func_cargo")
        .value.trim()
        .toUpperCase(),
      data_inicio_funcao:
        document.getElementById("edit_func_data_funcao").value || null,
      data_inicio_empresa:
        document.getElementById("edit_func_data_empresa").value || null,
    };

    try {
      const response = await fetchComAutenticacao(`/api/funcionario/${funcionarioId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
      });

      const resultado = await response.json();

      if (resultado.success) {
        mostrarToast("Funcionário atualizado com sucesso!", "success");

        fecharModalEditarFuncionario();

        // Recarregar a lista de funcionários da área
        await carregarFuncionariosArea(areaId);

        // ====== ATUALIZAR CONTADOR DA ÁREA ======
        await atualizarContadorArea(areaId);

        // Garantir que o card da área continue selecionado
        document.querySelectorAll(".area-card").forEach((card) => {
          if (card.getAttribute("data-id") == areaId) {
            card.classList.add("selected");
          }
        });
      } else {
        mostrarToast("Erro ao atualizar funcionário.", "error");
      }
    } catch (error) {
      console.error("Erro:", error);
      mostrarToast("Erro de conexão.", "error");
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.classList.remove("btn-loading");
      btnSubmit.innerHTML = textoOriginal;
    }
  });
}

// ====== BUSCA DE ÁREAS ======
const searchInput = document.getElementById("searchAreaInput");
const clearSearchBtn = document.getElementById("clearSearchBtn");
let todasAreas = []; // Armazenar todas as áreas para filtro

// Modificar a função carregarAreas para salvar os dados originais
async function carregarAreas() {
  try {
    const response = await fetchComAutenticacao("/api/areas");
    const areas = await response.json();

    todasAreas = areas;

    console.log("Dados recebidos:", areas);

    if (!areas || areas.length === 0) {
      document.getElementById("areasContainer").innerHTML =
        '<p class="text-muted">Nenhuma área cadastrada</p>';
      document.getElementById("pagination-container").style.display = "none";
      return;
    }

    paginaAtual = 1; // Resetar para primeira página

    // Aplicar ordenação
    const areasOrdenadas = ordenarAreas(areas, ordemAtual);
    todasAreas = areasOrdenadas;

    renderizarCards(areasOrdenadas);
  } catch (error) {
    console.error("Erro ao carregar áreas:", error);
    document.getElementById("areasContainer").innerHTML =
      '<p class="text-muted">Erro ao carregar áreas</p>';
  }
}

function aplicarFiltroOuPagina() {
  const termo = searchInput?.value.toLowerCase() || "";

  let areasBase = todasAreas;

  // Aplicar filtro se houver termo
  if (termo) {
    areasBase = todasAreas.filter((area) => {
      return (
        (area.nome_area && area.nome_area.toLowerCase().includes(termo)) ||
        (area.gestor && area.gestor.toLowerCase().includes(termo)) ||
        (area.email && area.email.toLowerCase().includes(termo))
      );
    });
  }

  // Ordenar as áreas
  const areasOrdenadas = ordenarAreas(areasBase, ordemAtual);
  renderizarCards(areasOrdenadas);
}

function renderizarPaginacao(totalItens, totalPaginas) {
  const pagContainer = document.getElementById("pagination-container");
  const pagInfo = document.getElementById("pagination-info");
  const pagButtons = document.getElementById("pagination-buttons");

  if (!pagContainer || totalPaginas <= 1) {
    if (pagContainer) pagContainer.style.display = "none";
    return;
  }

  pagContainer.style.display = "flex";

  // Informação: Mostrando X a Y de Z áreas
  const inicio = (paginaAtual - 1) * itensPorPagina + 1;
  const fim = Math.min(paginaAtual * itensPorPagina, totalItens);
  pagInfo.innerHTML = `Mostrando ${inicio} a ${fim} de ${totalItens} áreas`;

  // Botões de paginação
  let botoesHtml = "";

  // Botão Anterior
  botoesHtml += `<button class="pagination-btn" id="btn-pagina-anterior" ${paginaAtual === 1 ? "disabled" : ""}>◀ Anterior</button>`;

  // Números das páginas
  const maxBotoes = 5;
  let inicioPaginas = Math.max(1, paginaAtual - Math.floor(maxBotoes / 2));
  let fimPaginas = Math.min(totalPaginas, inicioPaginas + maxBotoes - 1);

  if (fimPaginas - inicioPaginas + 1 < maxBotoes) {
    inicioPaginas = Math.max(1, fimPaginas - maxBotoes + 1);
  }

  for (let i = inicioPaginas; i <= fimPaginas; i++) {
    botoesHtml += `<button class="pagination-btn ${i === paginaAtual ? "active" : ""}" data-pagina="${i}">${i}</button>`;
  }

  // Botão Próximo
  botoesHtml += `<button class="pagination-btn" id="btn-pagina-proxima" ${paginaAtual === totalPaginas ? "disabled" : ""}>Próximo ▶</button>`;

  pagButtons.innerHTML = botoesHtml;

  // Adicionar eventos
  document
    .getElementById("btn-pagina-anterior")
    ?.addEventListener("click", () => {
      if (paginaAtual > 1) {
        paginaAtual--;
        aplicarFiltroOuPagina();
      }
    });

  document
    .getElementById("btn-pagina-proxima")
    ?.addEventListener("click", () => {
      if (paginaAtual < totalPaginas) {
        paginaAtual++;
        aplicarFiltroOuPagina();
      }
    });

  document.querySelectorAll(".pagination-btn[data-pagina]").forEach((btn) => {
    btn.addEventListener("click", () => {
      paginaAtual = parseInt(btn.getAttribute("data-pagina"));
      aplicarFiltroOuPagina();
    });
  });
}

// Função para renderizar os cards (extraída da carregarAreas)
function renderizarCards(areas) {
  const container = document.getElementById("areasContainer");
  const pagContainer = document.getElementById("pagination-container");

  if (!areas || areas.length === 0) {
    container.innerHTML = '<p class="text-muted">Nenhuma área cadastrada</p>';
    if (pagContainer) pagContainer.style.display = "none";
    return;
  }

  // Salvar todas as áreas para paginação
  todasAreasLista = areas;

  // Calcular total de páginas
  const totalPaginas = Math.ceil(areas.length / itensPorPagina);

  // Garantir que página atual seja válida
  if (paginaAtual > totalPaginas) paginaAtual = totalPaginas;
  if (paginaAtual < 1) paginaAtual = 1;

  // Pegar apenas as áreas da página atual
  const inicio = (paginaAtual - 1) * itensPorPagina;
  const fim = inicio + itensPorPagina;
  const areasPagina = areas.slice(inicio, fim);

  // Renderizar cards da página atual
  container.innerHTML = areasPagina
    .map((area) => {
      const nome = area.nome_area || "Sem nome";
      const locUnidade = area.loc_unidade || "Não informado";
      const gestor = area.gestor || "Não informado";
      const superintendente = area.superintendente || "Não informado";
      const diretor = area.diretor || "Não informado";
      const id = area.id_area;
      const status = area.status || "Ativo";
      const isAtivo = status === "Ativo";
      const statusBadge = isAtivo
        ? '<span class="badge-status badge-ativo">ATIVA</span>'
        : '<span class="badge-status badge-inativo">INATIVA</span>';

      return `
        <div class="area-card ${!isAtivo ? "inativa" : ""}" data-id="${id}">
            <h4 style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span><i class="fas fa-building"></i> ${nome} - ${locUnidade}</span>
                ${statusBadge}
                <span class="funcionarios-count" id="func-count-${id}" style="margin-left: auto;">
                    <i class="fas fa-users"></i> <span class="count-number">...</span>
                </span>
            </h4>
            <p><i class="fas fa-map-marker-alt"></i> <strong>${area.loc_unidade || "Não informada"}</strong></p>
            <p><i class="fas fa-user"></i> <strong>Gestor</strong>: ${gestor}</p>
            <p><i class="fas fa-user-tie"></i> <strong>Superintendente:</strong> ${superintendente}</p>
            <p><i class="fas fa-user-tie"></i> <strong>Diretor:</strong> ${diretor}</p>
            <p><i class="fas fa-envelope"></i> ${area.email || "Sem e-mail"}</p>
            <p><i class="fas fa-phone"></i> ${formatarTelefoneExibicao(area.telefone) || "Sem telefone"}</p>
    
            <div class="area-actions">
                ${
                  isAtivo
                    ? `
                    <button class="btn-edit-icon btn-edit-area" data-id="${id}" data-nome="${nome}" title="Editar Área">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                    <button class="btn-delete-icon btn-delete-area" data-id="${id}" data-nome="${nome}" title="Excluir Área">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                `
                    : `
                    <button class="btn-reativar-area" data-id="${id}" data-nome="${nome}">
                        <i class="fas fa-sync-alt"></i> Reativar
                    </button>
                `
                }
            </div>

        </div>
    `;
    })
    .join("");

  // Buscar contagem de funcionários para cada área
  areasPagina.forEach(async (area) => {
    const count = await buscarContagemFuncionarios(area.id_area);
    const countSpan = document.querySelector(
      `#func-count-${area.id_area} .count-number`,
    );
    if (countSpan) {
      countSpan.textContent = count;
    }
  });

  // Renderizar controles de paginação
  renderizarPaginacao(areas.length, totalPaginas);

  // Adicionar eventos após renderizar
  adicionarEventosCards();
}

// Função para filtrar áreas
function filtrarAreas() {
  const termo = searchInput.value.toLowerCase();
  paginaAtual = 1; // Resetar para primeira página

  if (!termo) {
    renderizarCards(todasAreas);
    return;
  }

  clearSearchBtn.style.display = "block";

  const areasFiltradas = todasAreas.filter((area) => {
    return (
      (area.nome_area && area.nome_area.toLowerCase().includes(termo)) ||
      (area.gestor && area.gestor.toLowerCase().includes(termo)) ||
      (area.email && area.email.toLowerCase().includes(termo))
    );
  });

  renderizarCards(areasFiltradas);

  if (areasFiltradas.length === 0) {
    document.getElementById("areasContainer").innerHTML =
      '<p class="text-muted">Nenhuma área encontrada para "<strong>' +
      termo +
      '</strong>"</p>';
    document.getElementById("pagination-container").style.display = "none";
  }
}

// Função para adicionar eventos aos cards (extraída)
function adicionarEventosCards() {
  document.querySelectorAll(".area-card").forEach((card) => {
    card.addEventListener("click", () => {
      const areaId = card.getAttribute("data-id");
      console.log("Card clicado, ID:", areaId);

      document.querySelectorAll(".area-card").forEach((c) => {
        c.classList.remove("selected");
      });
      card.classList.add("selected");
      carregarDetalhesArea(areaId);
    });
  });

  document.querySelectorAll(".btn-delete-area").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const areaId = btn.getAttribute("data-id");
      const areaNome = btn.getAttribute("data-nome");

      const confirmado = await mostrarConfirmacao(
        `Tem certeza que deseja desativar a área "${areaNome}"?`,
      );
      if (confirmado) {
        await excluirArea(areaId, areaNome, btn);
      }
    });
  });

  document.querySelectorAll(".btn-edit-area").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const areaId = btn.getAttribute("data-id");
      await abrirModalEditarArea(areaId);
    });
  });

  document.querySelectorAll(".btn-reativar-area").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const areaId = btn.getAttribute("data-id");
      const areaNome = btn.getAttribute("data-nome");

      const confirmado = await mostrarConfirmacao(
        `Tem certeza que deseja reativar a área "${areaNome}"?`,
      );
      if (confirmado) {
        await reativarArea(areaId, areaNome, btn);
      }
    });
  });
}

// Eventos da busca
if (searchInput) {
  searchInput.addEventListener("input", filtrarAreas);
}

if (clearSearchBtn) {
  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    filtrarAreas();
    searchInput.focus();
  });
}

// ====== REATIVAR ÁREA ======
async function reativarArea(areaId, areaNome, btnElement) {
  try {
    const textoOriginal = btnElement.innerHTML;
    btnElement.disabled = true;
    btnElement.classList.add("btn-loading");
    btnElement.innerHTML = '<i class="fas fa-spinner"></i> Reativando...';

    const response = await fetchComAutenticacao(`/api/area/${areaId}/reativar`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
    });

    const resultado = await response.json();

    if (resultado.success) {
      mostrarToast(`✅ Área "${areaNome}" reativada com sucesso!`, "success");

      // Recarregar a lista de áreas
      await carregarAreas();

      // Recarregar os detalhes da área reativada
      await carregarDetalhesArea(areaId);

      // Garantir que o card da área reativada fique selecionado
      document.querySelectorAll(".area-card").forEach((card) => {
        if (card.getAttribute("data-id") == areaId) {
          card.classList.add("selected");
        }
      });
    } else if (resultado.error === "Permissão negada") {
      mostrarToast("❌ Você não tem permissão para reativar áreas.", "error");
    } else {
      mostrarToast("❌ Erro ao reativar área. Tente novamente.", "error");
    }
  } catch (error) {
    console.error("Erro:", error);
    mostrarToast("❌ Erro de conexão.", "error");
  } finally {
    btnElement.disabled = false;
    btnElement.classList.remove("btn-loading");
    btnElement.innerHTML = textoOriginal;
  }
}

// ====== BAIXAR ORGANOGRAMA (COM URL ASSINADA) ======
window.baixarOrganograma = async function (areaId) {
  try {
    const response = await fetchComAutenticacao(`/api/area/${areaId}/organograma-url`);
    const data = await response.json();

    if (data.success) {
      // Baixar o arquivo
      fetchComAutenticacao(data.url)
        .then((res) => res.blob())
        .then((blob) => {
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = data.nome || "organograma";
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(link.href);
        });
    } else {
      mostrarToast("Organograma não encontrado", "error");
    }
  } catch (error) {
    console.error("Erro:", error);
    mostrarToast("Erro ao baixar organograma", "error");
  }
};

// ====== VISUALIZAR ORGANOGRAMA (COM URL ASSINADA) ======
window.visualizarOrganograma = async function (areaId) {
  try {
    const response = await fetchComAutenticacao(`/api/area/${areaId}/organograma-url`);
    const data = await response.json();

    if (data.success) {
      // Abrir a URL assinada em nova aba
      window.open(data.url, "_blank");
    } else {
      mostrarToast("Organograma não encontrado", "error");
    }
  } catch (error) {
    console.error("Erro:", error);
    mostrarToast("Erro ao visualizar organograma", "error");
  }
};
