// web/static/js/app.js — Ramo Pub Web Panel JS
// Python 3.10 + Flask + Vanilla JS

"use strict";

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
}

/* ── Yardımçı funksiyalar ─────────────────────────────────── */

/**
 * Fetch wrapper — JSON qaytarır
 * @param {string} url
 * @param {Object} opts
 */
async function apiFetch(url, opts = {}) {
    try {
        const method = (opts.method || "GET").toUpperCase();
        const headers = {
            "Content-Type": "application/json",
            ...opts.headers,
        };
        if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
            headers["X-CSRF-Token"] = getCsrfToken();
        }

        const resp = await fetch(url, {
            ...opts,
            method,
            headers,
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } catch (err) {
        console.error("[API] Xəta:", url, err);
        return null;
    }
}

/* ── Masa API-si ──────────────────────────────────────────── */

async function loadTables() {
    return await apiFetch("/tables/api/all");
}

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
    document.querySelectorAll(".flash").forEach(flash => {
        setTimeout(() => {
            flash.style.transition = "opacity 0.5s";
            flash.style.opacity = "0";
            setTimeout(() => flash.remove(), 500);
        }, 5000);
    });

    const path = window.location.pathname;
    document.querySelectorAll(".nav-item").forEach(item => {
        if (item.getAttribute("href") === path) {
            item.classList.add("active");
        }
    });

    // CSRF tokenu bütün POST formlara əlavə et
    const csrf = getCsrfToken();
    if (csrf) {
        document.querySelectorAll("form[method='post'], form[method='POST']").forEach(form => {
            if (!form.querySelector("input[name='csrf_token']")) {
                const hidden = document.createElement("input");
                hidden.type = "hidden";
                hidden.name = "csrf_token";
                hidden.value = csrf;
                form.appendChild(hidden);
            }
        });
    }
});

window.apiFetch = apiFetch;
window.loadTables = loadTables;
window.loadHourly = loadHourly;
window.loadMonthly = loadMonthly;
window.loadTopItems = loadTopItems;
window.setTableStatus = setTableStatus;
