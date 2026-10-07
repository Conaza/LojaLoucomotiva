(function () {
  function initCarousel(root) {
    const images = Array.from(root.querySelectorAll("img[data-index], img.is-active"));
    if (!images.length) return;
    let index = 0;
    const currentEl = root.querySelector("[data-carousel-current]");
    const show = (i) => {
      images.forEach((img, n) => img.classList.toggle("is-active", n === i));
      if (currentEl) currentEl.textContent = String(i + 1);
    };
    root.querySelector("[data-carousel-prev]")?.addEventListener("click", (e) => {
      e.stopPropagation();
      index = (index - 1 + images.length) % images.length;
      show(index);
    });
    root.querySelector("[data-carousel-next]")?.addEventListener("click", (e) => {
      e.stopPropagation();
      index = (index + 1) % images.length;
      show(index);
    });
  }

  document.querySelectorAll("[data-carousel]").forEach(initCarousel);

  const modal = document.getElementById("produtoModal");
  if (!modal) return;

  const modalCarousel = document.getElementById("modalCarousel");
  const modalNome = document.getElementById("modalNome");
  const modalDescricao = document.getElementById("modalDescricao");
  const modalPreco = document.getElementById("modalPreco");
  const modalTotal = document.getElementById("modalTotal");
  const modalProdutoId = document.getElementById("modalProdutoId");
  const modalTamanho = document.getElementById("modalTamanho");
  const modalQtd = document.getElementById("modalQtd");
  const modalTitle = document.getElementById("produtoModalLabel");

  function formatBRL(value) {
    return value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function updateTotal() {
    const preco = parseFloat(modal.dataset.unitPrice || "0");
    const qtd = Math.max(1, parseInt(modalQtd.value || "1", 10));
    modalQtd.value = String(qtd);
    modalTotal.textContent = formatBRL(preco * qtd);
  }

  modal.addEventListener("show.bs.modal", (event) => {
    const trigger = event.relatedTarget?.closest("[data-produto-id]") || event.relatedTarget;
    if (!trigger || !trigger.dataset.produtoId) return;

    const nome = trigger.dataset.nome || "";
    const descricao = trigger.dataset.descricao || "";
    const preco = parseFloat(trigger.dataset.preco || "0");
    const tamanhos = (trigger.dataset.tamanhos || "").split(",").filter(Boolean);
    let imagens = [];
    try {
      imagens = JSON.parse(trigger.dataset.imagens || "[]");
    } catch (_) {
      imagens = [];
    }

    modal.dataset.unitPrice = String(preco);
    modalProdutoId.value = trigger.dataset.produtoId;
    modalTitle.textContent = nome;
    modalNome.textContent = nome;
    modalDescricao.textContent = descricao;
    modalPreco.textContent = formatBRL(preco);
    modalQtd.value = "1";

    modalTamanho.innerHTML = '<option value="">Selecione</option>';
    tamanhos.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t === "Unico" ? "Único" : t;
      modalTamanho.appendChild(opt);
    });

    modalCarousel.innerHTML = "";
    if (!imagens.length) {
      const img = document.createElement("img");
      img.src = "/static/images/produtos/placeholder.svg";
      img.alt = nome;
      img.className = "is-active";
      modalCarousel.appendChild(img);
    } else {
      imagens.forEach((src, i) => {
        const img = document.createElement("img");
        img.src = src;
        img.alt = nome;
        img.dataset.index = String(i);
        if (i === 0) img.classList.add("is-active");
        modalCarousel.appendChild(img);
      });
      if (imagens.length > 1) {
        const nav = document.createElement("div");
        nav.className = "carousel-nav";
        nav.innerHTML =
          '<button type="button" data-carousel-prev aria-label="Anterior">&lt;</button>' +
          '<span class="carousel-counter"><span data-carousel-current>1</span> / ' +
          imagens.length +
          "</span>" +
          '<button type="button" data-carousel-next aria-label="Próxima">&gt;</button>';
        modalCarousel.appendChild(nav);
      }
      initCarousel(modalCarousel);
    }
    updateTotal();
  });

  document.getElementById("qtyMinus")?.addEventListener("click", () => {
    modalQtd.value = String(Math.max(1, parseInt(modalQtd.value || "1", 10) - 1));
    updateTotal();
  });
  document.getElementById("qtyPlus")?.addEventListener("click", () => {
    modalQtd.value = String(Math.min(20, parseInt(modalQtd.value || "1", 10) + 1));
    updateTotal();
  });
  modalQtd?.addEventListener("input", updateTotal);

  document.getElementById("formAddCarrinho")?.addEventListener("submit", (e) => {
    if (!modalTamanho.value) {
      e.preventDefault();
      modalTamanho.focus();
      alert("Selecione um tamanho.");
    }
  });
})();
