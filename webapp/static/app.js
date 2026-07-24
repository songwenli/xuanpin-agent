const runButton = document.querySelector("#run-button");
const refreshButton = document.querySelector("#refresh-button");
const statusBadge = document.querySelector("#status-badge");
const statusTitle = document.querySelector("#status-title");
const statusDetail = document.querySelector("#status-detail");
const totalCount = document.querySelector("#total-count");
const productGrid = document.querySelector("#product-grid");
const productEmpty = document.querySelector("#product-empty");
const productPaginationTop = document.querySelector("#product-pagination-top");
const productPaginationBottom = document.querySelector("#product-pagination-bottom");
const categoryFilters = document.querySelector("#category-filters");
const reportList = document.querySelector("#report-list");
const reportEmpty = document.querySelector("#report-empty");
const toast = document.querySelector("#toast");
const siteOptions = document.querySelector("#site-options");
const selectAllSites = document.querySelector("#select-all-sites");

let pollTimer = null;
const productsPerPage = 30;
let currentProductPage = 1;
let currentCategory = "";
const productCategories = ["Prom", "Evening", "Cocktail", "Wedding Guest", "Bridesmaid", "Homecoming", "Party"];

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `请求失败 (${response.status})`);
  }
  return response.json();
}

async function startRun() {
  const selectedSites = [...siteOptions.querySelectorAll("input:checked")]
    .map((input) => input.value);
  if (selectedSites.length === 0) {
    showToast("请至少选择一个网站");
    return;
  }
  runButton.disabled = true;
  try {
    const state = await api("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sites: selectedSites }),
    });
    renderStatus(state);
    startPolling();
    showToast("抓取任务已启动");
  } catch (error) {
    runButton.disabled = false;
    showToast(error.message);
  }
}

async function loadSites() {
  try {
    const payload = await api("/api/sites");
    siteOptions.innerHTML = payload.items.map((site) => `
      <label class="site-option" title="${escapeHtml(site.base_url)}">
        <input type="checkbox" value="${escapeHtml(site.name)}" checked>
        <span>${escapeHtml(site.name)}</span>
      </label>`).join("");
    syncSelectAllSites();
  } catch (error) {
    showToast(error.message);
  }
}

function syncSelectAllSites() {
  const checkboxes = [...siteOptions.querySelectorAll("input[type='checkbox']")];
  const checkedCount = checkboxes.filter((input) => input.checked).length;
  selectAllSites.checked = checkboxes.length > 0 && checkedCount === checkboxes.length;
  selectAllSites.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
}

function startPolling() {
  clearInterval(pollTimer);
  pollTimer = setInterval(loadStatus, 2000);
}

async function loadStatus() {
  try {
    const state = await api("/api/runs/current");
    renderStatus(state);
    if (["completed", "failed"].includes(state.status)) {
      clearInterval(pollTimer);
      await Promise.all([loadProducts(), loadReports()]);
    } else if (state.status === "running") {
      startPolling();
    }
  } catch (error) {
    showToast(error.message);
  }
}

function renderStatus(state) {
  const labels = {
    idle: ["等待运行", "Agent 已就绪", "点击右上角按钮，抓取 19 个 Prom Dress 站点。"],
    running: ["正在抓取", "Agent 正在工作", "正在遵守站点限速规则抓取并计算候选商品，请稍候。"],
    completed: ["运行完成", "今日选品已更新", "SQLite 数据和 Markdown/JSON 日报已生成。"],
    failed: ["运行失败", "本次任务未完成", state.error || "请查看后端日志了解详情。"],
  };
  const content = labels[state.status] || labels.idle;
  statusBadge.className = `status-badge ${state.status}`;
  statusBadge.textContent = content[0];
  statusTitle.textContent = content[1];
  statusDetail.textContent = content[2];
  runButton.disabled = state.status === "running";
}

async function loadProducts() {
  try {
    const offset = (currentProductPage - 1) * productsPerPage;
    const categoryQuery = currentCategory
      ? `&category=${encodeURIComponent(currentCategory)}`
      : "";
    const payload = await api(`/api/products?limit=${productsPerPage}&offset=${offset}${categoryQuery}`);
    const totalPages = Math.max(1, Math.ceil(payload.total / productsPerPage));
    if (currentProductPage > totalPages) {
      currentProductPage = totalPages;
      return loadProducts();
    }
    totalCount.textContent = payload.total;
    productGrid.innerHTML = payload.items.map(productCard).join("");
    productEmpty.hidden = payload.items.length > 0;
    renderProductPagination(totalPages, payload.total);
  } catch (error) {
    showToast(error.message);
  }
}

function renderCategoryFilters() {
  const categories = [{ value: "", label: "全部" }].concat(
    productCategories.map((category) => ({ value: category, label: category }))
  );
  categoryFilters.innerHTML = categories.map(({ value, label }) => `
    <button class="category-filter${value === currentCategory ? " active" : ""}"
      type="button" data-category="${escapeHtml(value)}">
      ${escapeHtml(label)}
    </button>`).join("");
}

function renderProductPagination(totalPages, totalProducts) {
  const containers = [productPaginationTop, productPaginationBottom];
  if (totalProducts <= productsPerPage) {
    containers.forEach((container) => container.replaceChildren());
    return;
  }

  const visiblePages = new Set([1, totalPages]);
  for (let page = currentProductPage - 2; page <= currentProductPage + 2; page += 1) {
    if (page >= 1 && page <= totalPages) visiblePages.add(page);
  }
  const pages = [...visiblePages].sort((a, b) => a - b);
  const parts = [pageButton("上一页", currentProductPage - 1, currentProductPage === 1)];
  pages.forEach((page, index) => {
    if (index > 0 && page - pages[index - 1] > 1) {
      parts.push('<span class="page-ellipsis" aria-hidden="true">…</span>');
    }
    parts.push(pageButton(String(page), page, false, page === currentProductPage));
  });
  parts.push(pageButton("下一页", currentProductPage + 1, currentProductPage === totalPages));
  parts.push(`<span class="page-status">共 ${totalProducts} 个，每页 ${productsPerPage} 个</span>`);
  containers.forEach((container) => { container.innerHTML = parts.join(""); });
}

function pageButton(label, page, disabled = false, active = false) {
  return `<button class="page-button${active ? " active" : ""}" type="button" data-page="${page}"${disabled ? " disabled" : ""}${active ? ' aria-current="page"' : ""}>${label}</button>`;
}

function changeProductPage(event) {
  const button = event.target.closest("[data-page]");
  if (!button || button.disabled) return;
  currentProductPage = Number(button.dataset.page);
  loadProducts().then(() => {
    document.querySelector("#products-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function productCard(product) {
  const image = product.product_image_urls[0];
  const imageContent = image
    ? `<img src="${escapeHtml(image)}" alt="${escapeHtml(product.product_title)}" loading="lazy">`
    : `<div class="image-placeholder">暂无图片</div>`;
  const price = product.price == null
    ? "价格暂无"
    : `${escapeHtml(product.currency || "")} ${Number(product.price).toFixed(2)}`;
  return `
    <article class="product-card">
      <div class="image-wrap">
        ${imageContent}
        <span class="score">${Number(product.score || 0).toFixed(3)}</span>
      </div>
      <div class="product-content">
        <div class="product-labels">
          <span class="site">${escapeHtml(product.source_site)}</span>
          <span class="category">${escapeHtml(product.source_category)}</span>
        </div>
        <h3><a href="${escapeHtml(product.product_url)}" target="_blank" rel="noopener">${escapeHtml(product.product_title)}</a></h3>
        <div class="product-meta"><span>${price}</span><span>榜单 #${product.rank_position || "—"}</span></div>
        <p class="reason">${escapeHtml(product.score_reason || "基于当前可用信号入选。")}</p>
      </div>
    </article>`;
}

async function loadReports() {
  try {
    const payload = await api("/api/reports");
    reportList.innerHTML = payload.items.map((report) => `
      <a class="report-item" href="/api/reports/${report.date}" target="_blank">
        <span><strong>${report.date}</strong> · 每日选品报告</span>
        <span class="report-arrow">↗</span>
      </a>`).join("");
    reportEmpty.hidden = payload.items.length > 0;
  } catch (error) {
    showToast(error.message);
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab, .panel").forEach((element) => element.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`#${tab.dataset.panel}-panel`).classList.add("active");
  });
});

runButton.addEventListener("click", startRun);
selectAllSites.addEventListener("change", () => {
  siteOptions.querySelectorAll("input[type='checkbox']").forEach((input) => {
    input.checked = selectAllSites.checked;
  });
  syncSelectAllSites();
});
siteOptions.addEventListener("change", syncSelectAllSites);
refreshButton.addEventListener("click", () => Promise.all([loadProducts(), loadReports()]));
productPaginationTop.addEventListener("click", changeProductPage);
productPaginationBottom.addEventListener("click", changeProductPage);
categoryFilters.addEventListener("click", (event) => {
  const button = event.target.closest("[data-category]");
  if (!button || button.dataset.category === currentCategory) return;
  currentCategory = button.dataset.category;
  currentProductPage = 1;
  renderCategoryFilters();
  loadProducts();
});
renderCategoryFilters();
Promise.all([loadStatus(), loadProducts(), loadReports(), loadSites()]);
