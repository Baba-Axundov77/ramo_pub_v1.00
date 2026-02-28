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
