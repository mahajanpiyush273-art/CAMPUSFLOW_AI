/**
 * CampusFlow AI - Student Info Hub, Events & Deadlines Views
 * Renders Notices Feed, Handbooks & Rules, Events, and Grouped Deadlines.
 */

import { apiGet, apiPost } from "/static/js/api.js";
import { showModal, showToast, renderSkeleton } from "/static/js/ui.js";

// ==========================================
// 1. NOTICES FEED VIEW
// ==========================================
export async function renderNoticesView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>📢 Campus Notices Feed</h1>
            <p class="text-muted">Official circulars and announcements published by university departments, newest first.</p>
        </div>

        <!-- Filter Controls -->
        <div class="card" style="margin-bottom: 24px; padding: 18px;">
            <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center; justify-content: space-between;">
                <input type="text" id="notices-search" class="form-input" placeholder="Search notices by title or content..." style="max-width: 380px;">
                <label style="display: flex; align-items: center; gap: 8px; font-size: 13.5px; cursor: pointer; color: var(--text-2);">
                    <input type="checkbox" id="show-old-toggle">
                    <span>Show expired notices (OLD)</span>
                </label>
            </div>
            <!-- Category Chips -->
            <div id="notice-category-chips" style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px;">
                <button class="badge badge-category active-cat" data-cat="" style="cursor: pointer; border: none; padding: 6px 12px;">All Categories</button>
                <button class="badge badge-category" data-cat="Academic" style="cursor: pointer; border: none; padding: 6px 12px;">Academic</button>
                <button class="badge badge-category" data-cat="Exam" style="cursor: pointer; border: none; padding: 6px 12px;">Exam</button>
                <button class="badge badge-category" data-cat="Fees" style="cursor: pointer; border: none; padding: 6px 12px;">Fees</button>
                <button class="badge badge-category" data-cat="Hostel" style="cursor: pointer; border: none; padding: 6px 12px;">Hostel</button>
                <button class="badge badge-category" data-cat="General" style="cursor: pointer; border: none; padding: 6px 12px;">General</button>
            </div>
        </div>

        <!-- Notices List Container -->
        <div id="notices-list-container" style="display: flex; flex-direction: column; gap: 16px;"></div>
    `;

    setupNoticesList(container);
    return container;
}

async function setupNoticesList(container) {
    const listEl = container.querySelector("#notices-list-container");
    const searchInput = container.querySelector("#notices-search");
    const oldToggle = container.querySelector("#show-old-toggle");
    const catButtons = container.querySelectorAll("#notice-category-chips button");

    let currentCat = "";
    let searchQuery = "";
    let includeOld = false;

    async function fetchAndRender() {
        listEl.innerHTML = "";
        listEl.appendChild(renderSkeleton(3, 80));

        try {
            let url = `/documents?include_old=${includeOld ? 'true' : 'false'}`;
            if (currentCat) url += `&category=${encodeURIComponent(currentCat)}`;
            if (searchQuery) url += `&q=${encodeURIComponent(searchQuery)}`;

            const data = await apiGet(url);
            listEl.innerHTML = "";

            if (!data.documents || data.documents.length === 0) {
                listEl.innerHTML = `<div class="card" style="text-align: center; padding: 32px; color: var(--muted);">No matching notices found.</div>`;
                return;
            }

            data.documents.forEach(doc => {
                const card = document.createElement("div");
                card.className = "card";
                card.style.padding = "20px";

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 6px;">
                        <h3 style="font-size: 17px; color: var(--text);">${doc.title}</h3>
                        <div style="display: flex; gap: 6px; flex-shrink: 0;">
                            ${doc.is_sample ? '<span class="badge badge-sample">Sample Data</span>' : ''}
                            ${doc.old ? '<span class="badge badge-old">OLD / Expired</span>' : '<span class="badge badge-new">New</span>'}
                        </div>
                    </div>
                    <div style="font-size: 13px; color: var(--muted); margin-bottom: 12px;">
                        <span class="badge badge-category" style="margin-right: 8px;">${doc.category}</span>
                        ${doc.department || 'Campus Office'} • Published: ${doc.publish_date}
                        ${doc.expiry_date ? ` • Expired: ${doc.expiry_date}` : ''}
                    </div>
                    <p style="font-size: 14.5px; color: var(--text-2); margin-bottom: 16px; line-height: 1.5;">
                        ${doc.summary || doc.raw_text}
                    </p>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-secondary btn-sm read-btn">Read Full Notice</button>
                        ${doc.stored_path ? `<a href="/api/documents/${doc.id}/file" class="btn btn-secondary btn-sm" download>📥 Download File</a>` : ''}
                    </div>
                `;

                card.querySelector(".read-btn").addEventListener("click", () => {
                    showModal({
                        title: doc.title,
                        content: `<pre style="white-space: pre-wrap; font-family: inherit; font-size: 14px; line-height: 1.6;">${doc.raw_text}</pre>`,
                        confirmText: "Close",
                    });
                });

                listEl.appendChild(card);
            });
        } catch (e) {
            listEl.innerHTML = `<div class="card" style="color: var(--danger);">${e.message}</div>`;
        }
    }

    searchInput.addEventListener("input", (e) => {
        searchQuery = e.target.value.trim();
        fetchAndRender();
    });

    oldToggle.addEventListener("change", (e) => {
        includeOld = e.target.checked;
        fetchAndRender();
    });

    catButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            catButtons.forEach(b => b.style.opacity = "0.7");
            btn.style.opacity = "1";
            currentCat = btn.getAttribute("data-cat");
            fetchAndRender();
        });
    });

    fetchAndRender();
}

// ==========================================
// 2. HANDBOOKS & RULES VIEW
// ==========================================
export async function renderHandbooksView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>📖 Handbooks, Rules & Process Guides</h1>
            <p class="text-muted">Permanent campus academic guidelines, attendance bylaws, hostel rules, and procedure guides.</p>
        </div>
        <div id="handbooks-list" style="display: flex; flex-direction: column; gap: 20px;"></div>
    `;

    const listEl = container.querySelector("#handbooks-list");
    listEl.appendChild(renderSkeleton(3, 100));

    try {
        const data = await apiGet("/documents");
        listEl.innerHTML = "";

        const guideDocs = (data.documents || []).filter(d => 
            ["handbook", "rules", "process_guide"].includes(d.doc_type)
        );

        if (guideDocs.length === 0) {
            listEl.innerHTML = `<div class="card" style="text-align: center; padding: 32px; color: var(--muted);">No handbooks found.</div>`;
            return;
        }

        guideDocs.forEach(doc => {
            const card = document.createElement("div");
            card.className = "card";
            card.style.padding = "24px";
            card.style.borderLeft = "4px solid var(--brand)";

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <h3 style="font-size: 18px;">${doc.title}</h3>
                    <div style="display: flex; gap: 6px;">
                        <span class="badge badge-category">${doc.doc_type.replace('_', ' ')}</span>
                        ${doc.is_sample ? '<span class="badge badge-sample">Sample Data</span>' : ''}
                    </div>
                </div>
                <div style="font-size: 13px; color: var(--muted); margin-bottom: 14px;">
                    ${doc.department || 'Academic Administration'} • Category: ${doc.category}
                </div>
                <div style="font-size: 14.5px; color: var(--text-2); line-height: 1.6; white-space: pre-wrap; background: var(--surface-2); padding: 16px; border-radius: var(--radius-sm); border: 1px solid var(--border);">
${doc.raw_text}
                </div>
            `;
            listEl.appendChild(card);
        });

    } catch (err) {
        listEl.innerHTML = `<div class="card" style="color: var(--danger);">${err.message}</div>`;
    }

    return container;
}

// ==========================================
// 3. CAMPUS EVENTS VIEW
// ==========================================
export async function renderEventsView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>🎉 Upcoming Campus Events</h1>
            <p class="text-muted">Workshops, hackathon sessions, orientation drives, and cultural activities.</p>
        </div>
        <div id="events-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;"></div>
    `;

    const gridEl = container.querySelector("#events-grid");
    gridEl.appendChild(renderSkeleton(2, 140));

    try {
        const data = await apiGet("/events");
        gridEl.innerHTML = "";

        if (!data.events || data.events.length === 0) {
            gridEl.innerHTML = `<div class="card" style="grid-column: 1/-1; text-align: center; padding: 32px; color: var(--muted);">No upcoming events scheduled.</div>`;
            return;
        }

        data.events.forEach(ev => {
            const card = document.createElement("div");
            card.className = "card student-card";
            card.style.display = "flex";
            card.style.flexDirection = "column";
            card.style.justifyContent = "space-between";
            card.style.padding = "22px";

            card.innerHTML = `
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <h3 style="font-size: 17px; line-height: 1.3;">${ev.title}</h3>
                        ${ev.is_sample ? '<span class="badge badge-sample" style="flex-shrink: 0;">Sample Data</span>' : ''}
                    </div>
                    <div style="font-size: 13px; color: var(--muted); margin-bottom: 12px;">
                        ${ev.department || 'Student Affairs'}
                    </div>
                    <div style="background: var(--brand-tint); padding: 10px 14px; border-radius: var(--radius-sm); margin-bottom: 14px; font-size: 13.5px;">
                        <div>📍 <strong>Venue:</strong> ${ev.venue || 'Campus Central Hall'}</div>
                        <div style="margin-top: 4px;">🗓️ <strong>Date & Time:</strong> ${ev.event_start || ev.publish_date}</div>
                    </div>
                    <p style="font-size: 14px; color: var(--text-2); margin-bottom: 18px; line-height: 1.45;">
                        ${ev.summary || ev.raw_text}
                    </p>
                </div>
                ${ev.registration_url ? `
                    <a href="${ev.registration_url}" target="_blank" class="btn btn-accent" style="width: 100%;">
                        Register for Event ↗
                    </a>
                ` : '<button class="btn btn-secondary" disabled style="width: 100%;">On-Spot Entry</button>'}
            `;
            gridEl.appendChild(card);
        });

    } catch (err) {
        gridEl.innerHTML = `<div class="card" style="color: var(--danger);">${err.message}</div>`;
    }

    return container;
}

// ==========================================
// 4. DEADLINES TRACKER VIEW
// ==========================================
export async function renderDeadlinesView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>⏰ Campus Deadlines Tracker</h1>
            <p class="text-muted">Proactive deadline alerts with 2-day reminder windows. Mark deadlines done to stop further alerts.</p>
        </div>

        <div id="deadlines-progress-card" class="card" style="margin-bottom: 24px; padding: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 700; font-size: 14px;">Your Deadlines Progress</span>
                <span id="deadlines-pct" style="font-weight: 700; color: var(--brand);">0%</span>
            </div>
            <div style="background: var(--border); height: 8px; border-radius: 4px; overflow: hidden;">
                <div id="deadlines-progress-bar" style="background: var(--brand); height: 100%; width: 0%; transition: width 0.4s ease;"></div>
            </div>
        </div>

        <div id="deadlines-sections" style="display: flex; flex-direction: column; gap: 24px;"></div>
    `;

    setupDeadlinesView(container);
    return container;
}

async function setupDeadlinesView(container) {
    const sectionsEl = container.querySelector("#deadlines-sections");
    const pctEl = container.querySelector("#deadlines-pct");
    const barEl = container.querySelector("#deadlines-progress-bar");

    sectionsEl.appendChild(renderSkeleton(3, 70));

    try {
        const data = await apiGet("/deadlines");
        sectionsEl.innerHTML = "";

        const all = data.deadlines || [];
        if (all.length === 0) {
            sectionsEl.innerHTML = `<div class="card" style="text-align: center; padding: 32px; color: var(--muted);">No active deadlines. You are all caught up!</div>`;
            return;
        }

        // Calculate progress
        const doneCount = all.filter(d => Boolean(d.is_done)).length;
        const pct = Math.round((doneCount / all.length) * 100);
        pctEl.textContent = `${doneCount} of ${all.length} Done (${pct}%)`;
        barEl.style.width = `${pct}%`;

        // Group deadlines: Overdue, Today, Next 2 Days, This Month, Later
        const groups = {
            "🚨 Overdue": [],
            "⚡ Due Today": [],
            "⏳ Due in Next 2 Days": [],
            "📅 This Month": [],
            "🗓️ Later": [],
        };

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        all.forEach(dl => {
            const dDate = new Date(dl.due_date);
            dDate.setHours(0, 0, 0, 0);
            const diffDays = Math.round((dDate - today) / (1000 * 60 * 60 * 24));

            if (diffDays < 0) groups["🚨 Overdue"].push(dl);
            else if (diffDays === 0) groups["⚡ Due Today"].push(dl);
            else if (diffDays <= 2) groups["⏳ Due in Next 2 Days"].push(dl);
            else if (diffDays <= 30) groups["📅 This Month"].push(dl);
            else groups["🗓️ Later"].push(dl);
        });

        for (const [groupName, items] of Object.entries(groups)) {
            if (items.length === 0) continue;

            const groupSec = document.createElement("div");
            groupSec.innerHTML = `<h3 style="margin-bottom: 12px; font-size: 16px;">${groupName} (${items.length})</h3>`;
            const list = document.createElement("div");
            list.style.display = "flex";
            list.style.flexDirection = "column";
            list.style.gap = "10px";

            items.forEach(dl => {
                const item = document.createElement("div");
                item.className = "card";
                item.style.padding = "16px 20px";
                item.style.display = "flex";
                item.style.alignItems = "center";
                item.style.justifyContent = "space-between";
                item.style.gap = "16px";

                const isDone = Boolean(dl.is_done);
                if (groupName.includes("Next 2 Days") || groupName.includes("Today")) {
                    item.style.borderLeft = "4px solid var(--accent)";
                }

                item.innerHTML = `
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                            <span style="font-weight: 700; font-size: 15px; text-decoration: ${isDone ? 'line-through' : 'none'}; color: ${isDone ? 'var(--muted)' : 'var(--text)'};">
                                ${dl.label}
                            </span>
                            <span class="badge badge-category" style="font-size: 11px;">${dl.category}</span>
                        </div>
                        <div class="text-muted" style="font-size: 13px;">
                            From: <strong>${dl.doc_title}</strong> • Due: <strong>${dl.due_date} ${dl.due_time || ''}</strong>
                        </div>
                    </div>
                    <button class="btn btn-sm ${isDone ? 'btn-secondary' : 'btn-accent'}" style="white-space: nowrap;">
                        ${isDone ? 'Completed ✓' : 'Mark Done'}
                    </button>
                `;

                const btn = item.querySelector("button");
                btn.addEventListener("click", async () => {
                    btn.disabled = true;
                    try {
                        const res = await apiPost(`/deadlines/${dl.id}/done`);
                        showToast(res.is_done ? "Deadline completed!" : "Deadline unmarked.", "success");
                        setupDeadlinesView(container);
                    } catch (e) {
                        showToast(e.message, "error");
                    }
                });

                list.appendChild(item);
            });

            groupSec.appendChild(list);
            sectionsEl.appendChild(groupSec);
        }

    } catch (err) {
        sectionsEl.innerHTML = `<div class="card" style="color: var(--danger);">${err.message}</div>`;
    }
}
