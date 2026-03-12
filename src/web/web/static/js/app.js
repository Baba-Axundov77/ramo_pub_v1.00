// web/static/js/app.js — Ramo Pub Web Panel JS
// Python 3.10 + Flask + Vanilla JS

"use strict";

/* ── Yardımçı funksiyalar ─────────────────────────────────── */

/**
 * Fetch wrapper — JSON qaytarır
 * @param {string} url
 * @param {Object} opts
 */
async function apiFetch(url, opts = {}) {
    try {
        const resp = await fetch(url, {
            headers: { "Content-Type": "application/json", ...opts.headers },
            ...opts,
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } catch (err) {
        console.error("[API] Xəta:", url, err);
        return null;
    }
}

/* ── Pagination Helper ───────────────────────────────────── */

class PaginationManager {
    constructor(endpoint, containerId, options = {}) {
        this.endpoint = endpoint;
        this.container = document.getElementById(containerId);
        this.currentPage = 1;
        this.perPage = options.perPage || 20;
        this.filters = options.filters || {};
        this.totalPages = 1;
        this.totalItems = 0;
    }

    async loadPage(page = 1) {
        this.currentPage = page;
        const params = new URLSearchParams({
            page: page.toString(),
            per_page: this.perPage.toString(),
            ...this.filters
        });

        const response = await apiFetch(`${this.endpoint}?${params}`);
        if (response && response.success) {
            this.totalPages = response.pagination.pages;
            this.totalItems = response.pagination.total;
            this.renderData(response.data);
            this.renderPagination(response.pagination);
            return response;
        }
        return null;
    }

    renderPagination(pagination) {
        const paginationHtml = `
            <div class="pagination-controls" style="display: flex; justify-content: center; gap: 10px; margin: 20px 0;">
                <button ${!pagination.has_prev ? 'disabled' : ''} 
                        onclick="paginationManager.loadPage(${pagination.page - 1})"
                        style="background: #c6a659; color: #020617; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer;">
                    Əvvəlki
                </button>
                <span style="color: #c6a659; padding: 8px;">
                    Səhifə ${pagination.page} / ${pagination.pages} (${pagination.total} məhsul)
                </span>
                <button ${!pagination.has_next ? 'disabled' : ''} 
                        onclick="paginationManager.loadPage(${pagination.page + 1})"
                        style="background: #c6a659; color: #020617; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer;">
                    Növbəti
                </button>
            </div>
        `;
        
        let paginationContainer = document.getElementById('pagination-container');
        if (!paginationContainer) {
            paginationContainer = document.createElement('div');
            paginationContainer.id = 'pagination-container';
            this.container.parentNode.insertBefore(paginationContainer, this.container.nextSibling);
        }
        paginationContainer.innerHTML = paginationHtml;
    }

    renderData(data) {
        // Override in specific implementation
        console.log('Render data:', data);
    }
}

/* ── Masa API-si ──────────────────────────────────────────── */

/**
 * Bütün masaları yüklə
 * Endpoint: GET /tables/api/all
 */
async function loadTables() {
    return await apiFetch("/tables/api/all");
}

/**
 * Masa statusunu dəyiş
 * Endpoint: POST /tables/api/status/:id
 */
async function setTableStatus(tableId, status) {
    return await apiFetch(`/tables/api/status/${tableId}`, {
        method: "POST",
        body: JSON.stringify({ status }),
    });
}

/* ── Menu API with Pagination ───────────────────────────────── */

class MenuPaginationManager extends PaginationManager {
    constructor(containerId, options = {}) {
        super('/api/menu', containerId, options);
    }

    renderData(menuData) {
        let html = '';
        for (const [category, items] of Object.entries(menuData)) {
            html += `
                <div class="menu-category" style="margin-bottom: 30px;">
                    <h3 style="color: #c6a659; margin-bottom: 15px;">${category}</h3>
                    <div class="menu-items" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px;">
            `;
            
            items.forEach(item => {
                html += `
                    <div class="menu-item" style="background: rgba(198, 166, 89, 0.1); border: 1px solid rgba(198, 166, 89, 0.3); border-radius: 12px; padding: 15px;">
                        <h4 style="color: #c6a659; margin: 0 0 8px 0;">${item.name}</h4>
                        <p style="color: #94a3b8; margin: 0 0 8px 0; font-size: 0.9em;">${item.description || ''}</p>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #c6a659; font-weight: bold;">${item.price} AZN</span>
                            <span style="color: ${item.stock > item.min_stock ? '#10b981' : '#ef4444'}; font-size: 0.8em;">
                                Stok: ${item.stock}
                            </span>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        }
        
        this.container.innerHTML = html;
    }
}

/* ── Orders API with Pagination ───────────────────────────────── */

class OrdersPaginationManager extends PaginationManager {
    constructor(containerId, options = {}) {
        super('/orders/history', containerId, options);
    }

    renderData(ordersData) {
        let html = `
            <div class="orders-list" style="display: grid; gap: 15px;">
        `;
        
        ordersData.forEach(order => {
            html += `
                <div class="order-card" style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(198, 166, 89, 0.2); border-radius: 12px; padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                        <div>
                            <h4 style="color: #c6a659; margin: 0;">Sifariş #${order.id}</h4>
                            <p style="color: #94a3b8; margin: 5px 0;">Masa: ${order.table_number || 'N/A'} | Ofisiant: ${order.waiter_name || 'N/A'}</p>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #c6a659; font-weight: bold; font-size: 1.2em;">${order.total_amount} AZN</span>
                            <p style="color: ${order.status === 'completed' ? '#10b981' : '#f59e0b'}; margin: 5px 0; font-size: 0.9em;">
                                ${order.status}
                            </p>
                        </div>
                    </div>
                    <div style="color: #64748b; font-size: 0.9em;">
                        ${order.created_at ? new Date(order.created_at).toLocaleString('az-AZ') : ''}
                    </div>
                </div>
            `;
        });
        
        html += `
            </div>
        `;
        
        this.container.innerHTML = html;
    }
}

/* ── Global pagination managers ───────────────────────────── */

let menuPaginationManager;
let ordersPaginationManager;

/* ── Hesabat API ──────────────────────────────────────────── */

async function loadHourly() {
    return await apiFetch("/reports/api/hourly");
}

async function loadMonthly(year, month) {
    return await apiFetch(`/reports/api/monthly?year=${year}&month=${month}`);
}

async function loadTopItems() {
    return await apiFetch("/reports/api/top_items");
}

/* ── Flash mesaj auto-hide ────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    // Flash mesajlar 5 saniyə sonra avtomatik bağlanır
    document.querySelectorAll(".flash").forEach(flash => {
        setTimeout(() => {
            flash.style.transition = "opacity 0.5s";
            flash.style.opacity = "0";
            setTimeout(() => flash.remove(), 500);
        }, 5000);
    });

    // Aktiv nav itemini highlight et (URL-ə görə)
    const path = window.location.pathname;
    document.querySelectorAll(".nav-item").forEach(item => {
        if (item.getAttribute("href") === path) {
            item.classList.add("active");
        }
    });
});

/* ── Qlobal dışarı açılan funksiyalar ────────────────────── */
window.apiFetch   = apiFetch;
window.loadTables = loadTables;
window.loadHourly = loadHourly;
window.loadMonthly = loadMonthly;
window.loadTopItems = loadTopItems;
