/**
 * CampusFlow AI - Student App Orchestrator
 * Session verification, notification polling, bell dropdown, hash router, and shortcuts.
 */

import { apiGet, apiPost } from "/static/js/api.js";
import { HashRouter } from "/static/js/router.js";
import { showToast } from "/static/js/ui.js";
import { renderDashboardView } from "/static/js/student/dashboard.js";

let currentUser = null;
let router = null;
let lastKnownNotifIds = new Set();

export async function initStudentApp() {
    // 1. Verify Authentication & Load Identity
    try {
        const meData = await apiGet("/me");
        if (meData.user.role !== "student") {
            window.location.href = "/admin";
            return;
        }
        currentUser = meData.user;
        const nameEl = document.getElementById("student-full-name");
        if (nameEl) nameEl.textContent = currentUser.full_name;
    } catch (e) {
        window.location.href = "/login?role=student";
        return;
    }

    // 2. Setup Hash Router
    router = new HashRouter("student-view-container", "#/dashboard");

    router.register("#/dashboard", async () => renderDashboardView());
    
    // Stubs for next modules (will be replaced in steps 22, 23, 24)
    router.register("#/ask", async (args) => {
        const mod = await import("/static/js/student/ask.js").catch(() => null);
        return mod ? mod.renderAskView(args) : `<div class="card"><h3>Ask Assistant</h3><p class="text-muted">Loading Ask interface...</p></div>`;
    });

    router.register("#/notices", async () => {
        const mod = await import("/static/js/student/info.js").catch(() => null);
        return mod ? mod.renderNoticesView() : `<div class="card"><h3>Notices Hub</h3></div>`;
    });

    router.register("#/handbooks", async () => {
        const mod = await import("/static/js/student/info.js").catch(() => null);
        return mod ? mod.renderHandbooksView() : `<div class="card"><h3>Handbooks & Rules</h3></div>`;
    });

    router.register("#/events", async () => {
        const mod = await import("/static/js/student/info.js").catch(() => null);
        return mod ? mod.renderEventsView() : `<div class="card"><h3>Campus Events</h3></div>`;
    });

    router.register("#/deadlines", async () => {
        const mod = await import("/static/js/student/info.js").catch(() => null);
        return mod ? mod.renderDeadlinesView() : `<div class="card"><h3>Deadlines Tracker</h3></div>`;
    });

    router.register("#/forms", async (args) => {
        const mod = await import("/static/js/student/forms.js").catch(() => null);
        return mod ? mod.renderFormsView(args) : `<div class="card"><h3>Official Forms</h3></div>`;
    });

    router.register("#/my-questions", async () => {
        const mod = await import("/static/js/student/forms.js").catch(() => null);
        return mod ? mod.renderMyQuestionsView() : `<div class="card"><h3>My Questions</h3></div>`;
    });

    router.register("#/profile", async () => {
        const mod = await import("/static/js/student/forms.js").catch(() => null);
        return mod ? mod.renderProfileView() : `<div class="card"><h3>Profile</h3></div>`;
    });

    router.init();

    // 3. Setup Notification Bell & Polling
    setupNotificationBell();
    pollNotifications(true);
    setInterval(() => pollNotifications(false), 30000);

    // 4. Global Search Keyboard Shortcut ("/" focuses search)
    window.addEventListener("keydown", (e) => {
        if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
            e.preventDefault();
            const topSearch = document.getElementById("top-search-input");
            if (topSearch) topSearch.focus();
        }
    });

    const topSearchForm = document.getElementById("top-search-form");
    if (topSearchForm) {
        topSearchForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const val = document.getElementById("top-search-input").value.trim();
            if (val) {
                window.location.hash = `#/ask?q=${encodeURIComponent(val)}`;
            }
        });
    }

    // 5. Logout Handler
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            await apiPost("/auth/logout");
            window.location.href = "/login?role=student";
        });
    }
}

function setupNotificationBell() {
    const bellBtn = document.getElementById("notif-bell-btn");
    const dropdown = document.getElementById("notif-dropdown");
    const markReadBtn = document.getElementById("notif-mark-read");

    if (!bellBtn || !dropdown) return;

    bellBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("open");
    });

    document.addEventListener("click", (e) => {
        if (!dropdown.contains(e.target) && !bellBtn.contains(e.target)) {
            dropdown.classList.remove("open");
        }
    });

    if (markReadBtn) {
        markReadBtn.addEventListener("click", async () => {
            try {
                await apiPost("/notifications/read");
                pollNotifications(true);
            } catch (e) {
                showToast(e.message, "error");
            }
        });
    }
}

async function pollNotifications(isInitial = false) {
    try {
        const data = await apiGet("/notifications");
        const badge = document.getElementById("notif-badge");
        const listEl = document.getElementById("notif-list");

        if (badge) {
            badge.textContent = data.unread_count;
            badge.style.display = data.unread_count > 0 ? "inline-block" : "none";
        }

        // Show toast alert for newly arrived notifications (not on initial load)
        if (!isInitial && data.notifications) {
            data.notifications.forEach(n => {
                if (!lastKnownNotifIds.has(n.id) && !n.read_at) {
                    showToast(`🚨 ${n.title}: ${n.body}`, "accent", 5000);
                }
            });
        }

        // Update known IDs
        if (data.notifications) {
            lastKnownNotifIds = new Set(data.notifications.map(n => n.id));
        }

        // Render Dropdown List
        if (listEl) {
            if (!data.notifications || data.notifications.length === 0) {
                listEl.innerHTML = `<div style="text-align: center; color: var(--muted); padding: 16px; font-size: 13px;">No notifications.</div>`;
            } else {
                listEl.innerHTML = data.notifications.slice(0, 8).map(n => `
                    <div class="notif-item ${!n.read_at ? 'unread' : ''}" onclick="window.location.hash='${n.link || '#/dashboard'}'">
                        <div style="font-weight: 600; font-size: 13px; color: var(--text);">${n.title}</div>
                        <div style="font-size: 12px; color: var(--text-2); margin-top: 2px;">${n.body}</div>
                        <div style="font-size: 11px; color: var(--muted); margin-top: 4px;">${n.created_at}</div>
                    </div>
                `).join("");
            }
        }
    } catch (e) {
        // Silently ignore background polling network errors
    }
}

// Bootstrap on DOMContentLoaded
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initStudentApp);
} else {
    initStudentApp();
}
