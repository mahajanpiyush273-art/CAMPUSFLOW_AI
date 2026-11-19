/**
 * CampusFlow AI - Admin App Orchestrator
 * Session verification, admin hash router, navigation state, and logout handler.
 */

import { apiGet, apiPost } from "/static/js/api.js";
import { HashRouter } from "/static/js/router.js";
import { showToast } from "/static/js/ui.js";
import { renderAdminDashboardView } from "/static/js/admin/dashboard.js";

let currentUser = null;
let router = null;

export async function initAdminApp() {
    // 1. Verify Authentication & Admin Role
    try {
        const meData = await apiGet("/me");
        if (meData.user.role !== "admin") {
            window.location.href = "/student";
            return;
        }
        currentUser = meData.user;
        const nameEl = document.getElementById("admin-full-name");
        if (nameEl) nameEl.textContent = currentUser.full_name;
    } catch (e) {
        window.location.href = "/login?role=admin";
        return;
    }

    // 2. Setup Hash Router
    router = new HashRouter("admin-view-container", "#/dashboard");

    router.register("#/dashboard", async () => renderAdminDashboardView());

    router.register("#/upload", async () => {
        const mod = await import("/static/js/admin/upload.js?v=37").catch(err => {
            console.error("Failed to load upload.js:", err);
            return null;
        });
        return mod ? mod.renderUploadView() : `<div class="card"><h3>Upload Document</h3><p class="text-muted">Loading wizard...</p></div>`;
    });

    router.register("#/notices", async () => {
        const mod = await import("/static/js/admin/manage.js?v=37").catch(err => {
            console.error("Failed to load manage.js:", err);
            return null;
        });
        return mod ? mod.renderNoticesManagerView() : `<div class="card"><h3>Notices Manager</h3><p class="text-muted">Loading notices...</p></div>`;
    });

    router.register("#/review-queue", async () => {
        const mod = await import("/static/js/admin/manage.js?v=37").catch(err => {
            console.error("Failed to load manage.js:", err);
            return null;
        });
        return mod ? mod.renderReviewQueueView() : `<div class="card"><h3>Review Queue</h3><p class="text-muted">Loading review queue...</p></div>`;
    });

    router.register("#/submissions", async () => {
        window.location.hash = "#/dashboard";
        return renderAdminDashboardView();
    });

    router.register("#/offices", async () => {
        const mod = await import("/static/js/admin/manage.js?v=37").catch(err => {
            console.error("Failed to load manage.js:", err);
            return null;
        });
        return mod ? mod.renderOfficesView() : `<div class="card"><h3>Campus Offices</h3><p class="text-muted">Loading offices...</p></div>`;
    });

    router.register("#/ai-status", async () => {
        window.location.hash = "#/dashboard";
        return renderAdminDashboardView();
    });

    router.init();

    // 3. Update Review Queue Badge
    updateReviewBadge();

    // 4. Logout Button Listener
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            try {
                await apiPost("/auth/logout");
            } catch (err) {
                // Ignore failure on logout
            }
            window.location.href = "/login";
        });
    }
}

async function updateReviewBadge() {
    try {
        const stats = await apiGet("/admin/stats");
        const badge = document.getElementById("sidebar-review-badge");
        if (badge && stats.pending_review_count > 0) {
            badge.textContent = stats.pending_review_count;
            badge.style.display = "inline-block";
        }
    } catch (e) {
        // Silent fail
    }
}

// Auto-run on DOMContentLoaded
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdminApp);
} else {
    initAdminApp();
}
