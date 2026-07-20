// ============================================================
// HOME - JAVASCRIPT (CÓPIA EXATA DO QUE FUNCIONAVA NO INLINE)
// ============================================================

// ===== TOGGLE ORGANOGRAMA =====
window.toggleOrganograma = function () {
  const body = document.getElementById("organograma-body");
  const icon = document.getElementById("organograma-icon");

  if (body && icon) {
    if (body.style.display === "none") {
      body.style.display = "block";
      icon.classList.add("rotated");
    } else {
      body.style.display = "none";
      icon.classList.remove("rotated");
    }
  }
};

// Adiciona tooltips com imagens para cada ponto da timeline
document.addEventListener("DOMContentLoaded", () => {
  // ========== FUNÇÃO PARA ABRIR MODAL DE IMAGEM ==========
  function openImageModal(images, captions, currentIndex) {
    // Remove modal existente
    const existingModal = document.querySelector(".image-modal");
    if (existingModal) existingModal.remove();

    // Cria o modal
    const modal = document.createElement("div");
    modal.className = "image-modal";

    let currentIdx = currentIndex;
    const total = images.length;
    const temMultiplas = total > 1;

    modal.innerHTML = `
            <div class="image-modal-content">
                <button class="image-modal-close">✕</button>
                ${temMultiplas ? '<button class="image-modal-prev">◀</button>' : ""}
                <img id="modal-image" src="${images[currentIdx]}" alt="${captions[currentIdx]}">
                ${temMultiplas ? '<button class="image-modal-next">▶</button>' : ""}
                <div class="image-modal-caption">${captions[currentIdx]}</div>
                ${temMultiplas ? `<div class="image-modal-counter">${currentIdx + 1} / ${total}</div>` : ""}
            </div>
        `;

    document.body.appendChild(modal);

    // Função para atualizar a imagem
    function updateModalImage(newIndex) {
      currentIdx = newIndex;
      const imgElement = modal.querySelector("#modal-image");
      const captionElement = modal.querySelector(".image-modal-caption");
      const counterElement = modal.querySelector(".image-modal-counter");

      imgElement.src = images[currentIdx];
      captionElement.textContent = captions[currentIdx];
      if (counterElement)
        counterElement.textContent = `${currentIdx + 1} / ${total}`;
    }

    // Evento do botão anterior
    const prevBtn = modal.querySelector(".image-modal-prev");
    if (prevBtn) {
      prevBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        let newIndex = currentIdx - 1;
        if (newIndex < 0) newIndex = total - 1;
        updateModalImage(newIndex);
      });
    }

    // Evento do botão próximo
    const nextBtn = modal.querySelector(".image-modal-next");
    if (nextBtn) {
      nextBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        let newIndex = currentIdx + 1;
        if (newIndex >= total) newIndex = 0;
        updateModalImage(newIndex);
      });
    }

    // Fecha o modal ao clicar fora da imagem
    modal.addEventListener("click", (e) => {
      if (
        e.target === modal ||
        e.target.classList.contains("image-modal-close")
      ) {
        modal.classList.remove("active");
        setTimeout(() => modal.remove(), 300);
      }
    });

    // Teclado: setas esquerda/direita
    function handleKeydown(e) {
      if (!modal.classList.contains("active")) return;
      if (e.key === "ArrowLeft") {
        let newIndex = currentIdx - 1;
        if (newIndex < 0) newIndex = total - 1;
        updateModalImage(newIndex);
      } else if (e.key === "ArrowRight") {
        let newIndex = currentIdx + 1;
        if (newIndex >= total) newIndex = 0;
        updateModalImage(newIndex);
      } else if (e.key === "Escape") {
        modal.classList.remove("active");
        setTimeout(() => modal.remove(), 300);
        document.removeEventListener("keydown", handleKeydown);
      }
    }

    document.addEventListener("keydown", handleKeydown);

    // Abre o modal com animação
    setTimeout(() => modal.classList.add("active"), 10);
  }

  const timelineNodes = document.querySelectorAll(".timeline-node");

  // Dados das imagens para cada ponto
  const slidesData = [
    {
      // PONTO 1 - TEM IMAGENS
      images: [
        "/static/images/construcao_area2.jpg",
        "/static/images/construcao_area.jpg",
      ],
      captions: ["Construção da área HMK", "Construção da área HMK"],
    },
    {
      // PONTO 2 - SEM IMAGENS (vazio)
      images: [],
      captions: [],
    },
    {
      // PONTO 3 - SEM IMAGENS (vazio)
      images: [],
      captions: [],
    },
    {
      // PONTO 4 - SEM IMAGENS (vazio)
      images: [],
      captions: [],
    },
    {
      // PONTO 5 - TEM IMAGENS
      images: ["/static/images/metodologias_internas.jpg"],
      captions: [""],
    },
    {
      // PONTO 6 - SEM IMAGENS
      images: [],
      captions: [],
    },
    {
      // PONTO 7 - SEM IMAGENS
      images: [],
      captions: [],
    },
    {
      // PONTO 8 - TEM IMAGENS
      images: ["/static/images/rotina_vassouras.jpg"],
      captions: ["Rotina em Vassouras"],
    },
    {
      // PONTO 9 - SEM IMAGENS
      images: [],
      captions: [],
    },
    {
      // PONTO 10 - TEM IMAGENS
      images: [
        "/static/images/estruturacao_fisica_equipe3.jpg",
        "/static/images/estruturacao_fisica_equipe.jpg",
        "/static/images/estruturacao_fisica_equipe2.jpg",
      ],
      captions: ["Nomeação do Téofilo para Gerente da área", "", ""],
    },
    {
      // PONTO 11 - SEM IMAGENS
      images: [],
      captions: [],
    },
    {
      // PONTO 12 - SEM IMAGENS
      images: [],
      captions: [],
    },
    {
      // PONTO 13 - TEM IMAGENS
      images: ["/static/images/execucao_planejamento.jpg"],
      captions: [""],
    },
    {
      // PONTO 14 - TEM IMAGENS
      images: [
        "/static/images/sistema-v1.jpg",
        "/static/images/sistema-v1-powerautomate.jpg",
      ],
      captions: [
        "Desenho inicial - Criação do microsoft forms",
        "Desenho inicial - Automação do formulário com PowerAutomate",
      ],
    },
    {
      // PONTO 15 - TEM IMAGENS
      images: [
        "/static/images/streamlitlogin-v1.jpg",
        "/static/images/streamlitlogado-v1.jpg",
      ],
      captions: [
        "Tela de login da primeira versão",
        "Tela de diagnóstico dos processos na primeira versão",
      ],
    },
    {
      // PONTO 16 - TEM IMAGENS
      images: ["/static/images/aprimoramentov1.jpg"],
      captions: [
        "Ambiente de desenvolvimento da versão 1, atribuindo uso de novas tecnologias.",
      ],
    },
    {
      // PONTO 17 - TEM IMAGENS
      images: ["/static/images/criacaoambienteflaskbackendv2.jpg"],
      captions: ["Ambiente de desenvolvimento utilizando o framework Flask"],
    },
    {
      // PONTO 18 - TEM IMAGENS
      images: [
        "/static/images/paginaloginnovainterfacev2.jpg",
        "/static/images/paginaqualquerv2.jpg",
      ],
      captions: [
        "Página de login replicada e desenvolvida com outra tecnologia",
        "Página do sistema evidenciando a melhora na interface",
      ],
    },
    {
      // PONTO 19 - SEM IMAGENS
      images: [],
      captions: [],
    },
  ];

  timelineNodes.forEach((node, index) => {
    // ⭐ VERIFICAÇÃO: Só cria tooltip se tiver imagens válidas
    const hasValidImages =
      slidesData[index] &&
      slidesData[index].images &&
      slidesData[index].images.length > 0 &&
      slidesData[index].images[0] !== "..." &&
      slidesData[index].images[0] !== "";

    if (!hasValidImages) {
      return; // Não cria tooltip para pontos sem imagens
    }

    // Cria o elemento da tooltip
    const tooltip = document.createElement("div");
    tooltip.className = "image-tooltip";

    const totalImagens = slidesData[index].images.length;
    const temMultiplasImagens = totalImagens > 1;

    if (temMultiplasImagens) {
      // ========== ESTRUTURA COM CARROSSEL ==========
      tooltip.innerHTML = `
                <div class="tooltip-carousel">
                    <div class="carousel-container">
                        <div class="carousel-slides" id="carousel-slides-${index}">
                        </div>
                    </div>
                    <button class="carousel-prev carousel-btn" data-idx="${index}">‹</button>
                    <button class="carousel-next carousel-btn" data-idx="${index}">›</button>
                </div>
                <div class="tooltip-caption" id="tooltip-caption-${index}"></div>
                <div class="carousel-dots" id="carousel-dots-${index}"></div>
            `;
      const slidesContainer = tooltip.querySelector(
        `#carousel-slides-${index}`,
      );

      // Legenda inicial
      const captionEl = tooltip.querySelector(`#tooltip-caption-${index}`);
      captionEl.textContent = slidesData[index].captions[0];

      // Cria os dots (indicadores)
      const dotsContainer = tooltip.querySelector(`#carousel-dots-${index}`);
      slidesData[index].images.forEach((_, imgIdx) => {
        const dot = document.createElement("span");
        dot.className = "carousel-dot";
        if (imgIdx === 0) dot.classList.add("active");
        dot.setAttribute("data-slide", imgIdx);
        dot.setAttribute("data-point", index);
        dotsContainer.appendChild(dot);
      });

      // ========== LÓGICA DE NAVEGAÇÃO DO CARROSSEL ==========
      let currentSlide = 0;

      function updateSlide(newIndex) {
        if (newIndex < 0) newIndex = 0;
        if (newIndex >= totalImagens) newIndex = totalImagens - 1;
        currentSlide = newIndex;

        const allSlides = slidesContainer.querySelectorAll(".carousel-slide");
        allSlides.forEach((slide, i) => {
          slide.style.display = i === currentSlide ? "block" : "none";
        });

        captionEl.textContent = slidesData[index].captions[currentSlide];

        const dots = dotsContainer.querySelectorAll(".carousel-dot");
        dots.forEach((dot, i) => {
          if (i === currentSlide) {
            dot.classList.add("active");
          } else {
            dot.classList.remove("active");
          }
        });
      }

      // Botão próximo
      const nextBtn = tooltip.querySelector(".carousel-next");
      nextBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        updateSlide(currentSlide + 1);
      });

      // Botão anterior
      const prevBtn = tooltip.querySelector(".carousel-prev");
      prevBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        updateSlide(currentSlide - 1);
      });

      // Clique nos dots
      const dots = dotsContainer.querySelectorAll(".carousel-dot");
      dots.forEach((dot, dotIndex) => {
        dot.addEventListener("click", (e) => {
          e.stopPropagation();
          updateSlide(dotIndex);
        });
      });

      // Após inserir as imagens, adicione evento de clique para ampliar
      slidesData[index].images.forEach((imgSrc, imgIdx) => {
        const img = document.createElement("img");
        img.src = imgSrc;
        img.className = "carousel-slide";
        img.style.width = "100%";
        img.style.display = imgIdx === 0 ? "block" : "none";
        img.style.cursor = "pointer"; // Indica que é clicável
        img.setAttribute("data-img-index", imgIdx);
        img.setAttribute("data-caption", slidesData[index].captions[imgIdx]);

        // Evento de clique para ampliar
        img.addEventListener("click", (e) => {
          e.stopPropagation();
          openImageModal(
            slidesData[index].images,
            slidesData[index].captions,
            imgIdx,
          );
        });

        slidesContainer.appendChild(img);
      });
    } else {
      // ========== ESTRUTURA SIMPLES (UMA IMAGEM) ==========
      const simpleImg = document.createElement("img");
      simpleImg.src = slidesData[index].images[0];
      simpleImg.style.width = "100%";
      simpleImg.style.maxHeight = "150px";
      simpleImg.style.objectFit = "cover";
      simpleImg.style.cursor = "pointer";
      simpleImg.style.borderRadius = "10px 10px 0 0";

      simpleImg.addEventListener("click", (e) => {
        e.stopPropagation();
        openImageModal(slidesData[index].images, slidesData[index].captions, 0);
      });

      tooltip.innerHTML = `
                <div class="tooltip-caption">${slidesData[index].captions[0]}</div>
            `;

      tooltip.insertBefore(simpleImg, tooltip.firstChild);
    }

    // Adiciona a tooltip ao ponto
    node.appendChild(tooltip);

    // ========== VARIÁVEL DE TIMEOUT ESPECÍFICA PARA ESTA TOOLTIP ==========
    let hoverTimeout;

    // ========== EVENTOS (EXATAMENTE COMO FUNCIONAVA) ==========

    node.addEventListener("mouseenter", () => {
      clearTimeout(hoverTimeout);

      const rect = node.getBoundingClientRect();
      const tooltipWidth = 260;
      const tooltipHeight = tooltip.offsetHeight;

      let leftPos = rect.left + rect.width / 2 - tooltipWidth / 2;
      if (leftPos < 10) leftPos = 10;
      if (leftPos + tooltipWidth > window.innerWidth - 10) {
        leftPos = window.innerWidth - tooltipWidth - 10;
      }

      let topPos = rect.top - tooltipHeight - 10;
      if (topPos < 10) {
        topPos = rect.bottom + 10;
      }

      tooltip.style.left = leftPos + "px";
      tooltip.style.top = topPos + "px";
      tooltip.classList.add("active");
    });

    let isOnTooltip = false;

    node.addEventListener("mouseleave", () => {
      hoverTimeout = setTimeout(() => {
        if (!isOnTooltip) {
          // ← SÓ FECHA SE NÃO ESTIVER NA TOOLTIP
          tooltip.classList.remove("active");
        }
      }, 300);
    });

    tooltip.addEventListener("mouseenter", () => {
      clearTimeout(hoverTimeout);
      isOnTooltip = true; // ← MARCA QUE ESTÁ NA TOOLTIP
    });

    tooltip.addEventListener("mouseleave", () => {
      isOnTooltip = false;
      // ← FECHA APÓS SAIR DA TOOLTIP
      hoverTimeout = setTimeout(() => {
        tooltip.classList.remove("active");
      }, 300);
    });
  });

  // ========== ANIMAÇÕES DOS CARDS ==========
  const cards = document.querySelectorAll(".feature-card");
  cards.forEach((card, index) => {
    card.style.opacity = "0";
    card.style.transform = "translateY(20px)";
    card.style.transition = `opacity 0.4s ease ${index * 0.05}s, transform 0.4s ease ${index * 0.05}s`;
    setTimeout(() => {
      card.style.opacity = "1";
      card.style.transform = "translateY(0)";
    }, 100);
  });
});
