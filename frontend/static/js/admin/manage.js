/**
 * CampusFlow AI - Admin Management Views
 * Implements:
 * 1. Notices Manager (filter, status badges, sample badge, unpublish, delete modal)
 * 2. Review Queue (unanswered questions grouped, publish verified answer once for all)
 * 3. Campus Offices Editor (CRUD, locations, hours, contact, keyword matching)
 * 4. Form Submissions (read-only view with parsed fields and reviewed toggle)
 * 5. AI Engine Status (Groq, Gemini, Custom LLM health, active models, test now)
 */

import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from "/static/js/api.js";
import { showToast, showModal, hideModal } from "/static/js/ui.js";

// =========================================================================
// 1. NOTICES MANAGER
// =========================================================================
export async function renderNoticesManagerView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
            <div>
                <h1>📁 Notices & Documents Manager</h1>
                <p class="text-muted">Manage published university circulars, handbooks, forms, and drafts.</p>
            </div>
            <a href="#/upload" class="btn btn-primary" style="padding: 9px 18px;">+ Upload New Notice</a>
        </div>

        <!-- Filter & Search Toolbar -->
        <div class="card" style="padding: 16px; margin-bottom: 24px;">
            <div style="display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 14px;">
                <input type="text" id="notices-search" class="form-input" placeholder="Search notices by title, department...">
                <select id="notices-status-filter" class="form-input">
                    <option value="">All Statuses</option>
                    <option value="published">Published</option>
                    <option value="draft">Drafts</option>
                    <option value="unpublished">Unpublished</option>
                </select>
                <select id="notices-category-filter" class="form-input">
                    <option value="">All Categories</option>
                    <option value="Fees">Fees</option>
                    <option value="Exams">Exams</option>
                    <option value="Forms">Forms</option>
                    <option value="Events">Events</option>
                    <option value="Admissions">Admissions</option>
                    <option value="Other">Other</option>
                </select>
            </div>
        </div>

        <!-- Notices Table -->
        <div class="card" style="padding: 20px;">
            <div id="notices-table-slot">
                <p class="text-muted">Loading notices...</p>
            </div>
        </div>
    `;

    loadNoticesTable(container);

    const searchInput = container.querySelector("#notices-search");
    const statusFilter = container.querySelector("#notices-status-filter");
    const catFilter = container.querySelector("#notices-category-filter");

    const refresh = () => loadNoticesTable(container, searchInput.value.trim(), statusFilter.value, catFilter.value);
    searchInput.addEventListener("input", debounce(refresh, 250));
    statusFilter.addEventListener("change", refresh);
    catFilter.addEventListener("change", refresh);

    return container;
}

async function loadNoticesTable(container, q = "", status = "", category = "") {
    const slot = container.querySelector("#notices-table-slot");
    try {
        let url = `/admin/documents?`;
        if (q) url += `q=${encodeURIComponent(q)}&`;
        if (status) url += `status=${encodeURIComponent(status)}&`;
        if (category) url += `category=${encodeURIComponent(category)}&`;

        const data = await apiGet(url);
        const docs = data.documents || [];

        if (docs.length === 0) {
            slot.innerHTML = `<div class="empty-state"><h3>No documents found</h3><p class="text-muted">Try adjusting your filters or upload a new notice.</p></div>`;
            return;
        }

        slot.innerHTML = `
            <div style="overflow-x: auto;">
                <table class="table" style="width: 100%; font-size: 13.5px;">
                    <thead>
                        <tr>
                            <th>Document Title</th>
                            <th>Category</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Published</th>
                            <th style="text-align: right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${docs.map(doc => {
                            const isOld = doc.expiry_date && new Date(doc.expiry_date) < new Date();
                            const statusBadge = isOld && doc.status === 'published'
                                ? `<span class="badge badge-warning">OLD</span>`
                                : doc.status === 'published'
                                ? `<span class="badge badge-success">Published</span>`
                                : doc.status === 'draft'
                                ? `<span class="badge badge-accent">Draft</span>`
                                : `<span class="badge" style="background: var(--surface-2); color: var(--text-muted);">Unpublished</span>`;

                            const sampleBadge = doc.is_sample ? `<span class="badge badge-primary" style="font-size: 10px; margin-left: 4px;">Sample</span>` : '';

                            return `
                                <tr data-id="${doc.id}">
                                    <td>
                                        <div style="font-weight: 600; color: var(--text);">${escapeHtml(doc.title)} ${sampleBadge}</div>
                                        <div class="text-muted" style="font-size: 11.5px;">${escapeHtml(doc.department || 'University Official')}</div>
                                    </td>
                                    <td><span class="badge badge-primary">${escapeHtml(doc.category)}</span></td>
                                    <td>${escapeHtml(doc.doc_type)}</td>
                                    <td>${statusBadge}</td>
                                    <td class="text-muted" style="font-size: 12.5px;">${doc.publish_date || '—'}</td>
                                    <td style="text-align: right; white-space: nowrap;">
                                        ${doc.status === 'published' ? `
                                            <button class="btn btn-secondary btn-sm btn-unpublish" style="padding: 4px 10px; margin-right: 6px;">Unpublish</button>
                                        ` : ''}
                                        <button class="btn btn-secondary btn-sm btn-delete-doc text-danger" style="padding: 4px 10px; border-color: rgba(255,88,65,0.3);">Delete</button>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;

        // Wire Action Listeners
        slot.querySelectorAll("tr").forEach(tr => {
            const docId = tr.getAttribute("data-id");

            const unpubBtn = tr.querySelector(".btn-unpublish");
            if (unpubBtn) {
                unpubBtn.addEventListener("click", async () => {
                    try {
                        await apiPost(`/admin/documents/${docId}/unpublish`);
                        showToast("Document unpublished and removed from search.", "success");
                        loadNoticesTable(container, q, status, category);
                    } catch (err) {
                        showToast(err.message || "Failed to unpublish.", "error");
                    }
                });
            }

            const delBtn = tr.querySelector(".btn-delete-doc");
            if (delBtn) {
                delBtn.addEventListener("click", () => {
                    showModal({
                        title: "Confirm Deletion",
                        content: `
                            <p>Are you sure you want to permanently delete this notice?</p>
                            <p class="text-muted" style="font-size: 13px;">This will remove its text chunks from the search index and cancel any associated deadlines.</p>
                            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
                                <button id="modal-cancel-del" class="btn btn-secondary">Cancel</button>
                                <button id="modal-confirm-del" class="btn btn-primary" style="background: var(--accent);">Yes, Delete</button>
                            </div>
                        `
                    });

                    document.getElementById("modal-cancel-del").onclick = hideModal;
                    document.getElementById("modal-confirm-del").onclick = async () => {
                        hideModal();
                        try {
                            await apiDelete(`/admin/documents/${docId}`);
                            showToast("Document deleted successfully.", "success");
                            loadNoticesTable(container, q, status, category);
                        } catch (err) {
                            showToast(err.message || "Failed to delete document.", "error");
                        }
                    };
                });
            }
        });

    } catch (e) {
        slot.innerHTML = `<div class="card-error" style="padding: 16px;">Failed to load notices: ${e.message}</div>`;
    }
}

// =========================================================================
// 2. REVIEW QUEUE
// =========================================================================
export async function renderReviewQueueView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>❓ Unanswered Questions Review Queue</h1>
            <p class="text-muted">Student inquiries where the AI was not verified. Answer once here to publish an official verified FAQ that answers all students at once.</p>
        </div>

        <div id="review-queue-slot">
            <p class="text-muted">Loading review queue...</p>
        </div>
    `;

    loadReviewQueue(container);
    return container;
}

async function loadReviewQueue(container) {
    const slot = container.querySelector("#review-queue-slot");
    try {
        const data = await apiGet("/admin/review-queue");
        const queue = data.queue || [];

        if (queue.length === 0) {
            slot.innerHTML = `
                <div class="card empty-state" style="padding: 48px 24px; text-align: center;">
                    <div style="font-size: 40px; margin-bottom: 12px;">✅</div>
                    <h3>All Questions Verified!</h3>
                    <p class="text-muted">There are no pending or unanswered student inquiries right now.</p>
                </div>
            `;
            return;
        }

        slot.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 18px;">
                ${queue.map(item => `
                    <div class="card review-card" data-key="${escapeHtml(item.group_key)}" style="padding: 24px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                            <div>
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                                    <span class="badge badge-accent">Asked ${item.count} ${item.count === 1 ? 'time' : 'times'}</span>
                                    <span class="text-muted" style="font-size: 12px;">by ${item.students_count} unique student(s)</span>
                                </div>
                                <h3 style="font-size: 17px; color: var(--text);">${escapeHtml(item.sample_question)}</h3>
                            </div>
                            <button type="button" class="btn btn-primary btn-sm btn-toggle-reply">Write Official Reply</button>
                        </div>

                        <!-- Suggested notices match -->
                        ${item.suggested_notices && item.suggested_notices.length > 0 ? `
                            <div style="margin-bottom: 14px; padding: 10px 14px; background: var(--surface-2); border-radius: var(--radius-sm); font-size: 12.5px;">
                                <span class="text-muted">Similar existing notices:</span>
                                <strong>${escapeHtml(item.suggested_notices[0].title)}</strong>
                            </div>
                        ` : ''}

                        <!-- Inline Reply Panel (Collapsed by default) -->
                        <div class="reply-panel" style="display: none; border-top: 1px solid var(--border); padding-top: 18px; margin-top: 14px;">
                            <h4 style="font-size: 14px; margin-bottom: 8px;">Official Verified Answer</h4>
                            <p class="text-muted" style="font-size: 12.5px; margin-bottom: 10px;">
                                Submitting this creates a published FAQ notice and sends a notification to all ${item.students_count} students.
                            </p>
                            <textarea class="form-input reply-text" rows="4" placeholder="Type the accurate official answer, deadline, and instructions..."></textarea>
                            
                            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px;">
                                <button type="button" class="btn btn-secondary btn-cancel-reply">Cancel</button>
                                <button type="button" class="btn btn-primary btn-publish-reply">Publish as Verified Answer</button>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        slot.querySelectorAll(".review-card").forEach(card => {
            const groupKey = card.getAttribute("data-key");
            const toggleBtn = card.querySelector(".btn-toggle-reply");
            const replyPanel = card.querySelector(".reply-panel");
            const cancelBtn = card.querySelector(".btn-cancel-reply");
            const pubBtn = card.querySelector(".btn-publish-reply");
            const textarea = card.querySelector(".reply-text");

            toggleBtn.addEventListener("click", () => {
                replyPanel.style.display = replyPanel.style.display === "none" ? "block" : "none";
                if (replyPanel.style.display === "block") textarea.focus();
            });

            cancelBtn.addEventListener("click", () => {
                replyPanel.style.display = "none";
            });

            pubBtn.addEventListener("click", async () => {
                const answer = textarea.value.trim();
                if (!answer) {
                    showToast("Answer cannot be empty.", "error");
                    return;
                }

                pubBtn.disabled = true;
                pubBtn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> Publishing...`;

                try {
                    await apiPost("/admin/review-queue/reply", {
                        group_key: groupKey,
                        answer: answer
                    });
                    showToast("Verified answer published! Student notifications dispatched.", "success");
                    loadReviewQueue(container);
                } catch (err) {
                    showToast(err.message || "Failed to publish answer.", "error");
                    pubBtn.disabled = false;
                    pubBtn.textContent = "Publish as Verified Answer";
                }
            });
        });

    } catch (e) {
        slot.innerHTML = `<div class="card-error" style="padding: 16px;">Failed to load review queue: ${e.message}</div>`;
    }
}

// =========================================================================
// 3. CAMPUS OFFICES EDITOR
// =========================================================================
export async function renderOfficesView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
            <div>
                <h1>🏢 Campus Offices Directory</h1>
                <p class="text-muted">Offices shown to students when queries are not verified or require in-person action.</p>
            </div>
            <button id="btn-add-office" class="btn btn-primary" style="padding: 9px 18px;">+ Add New Office</button>
        </div>

        <div class="card" style="padding: 20px;">
            <div id="offices-table-slot">
                <p class="text-muted">Loading offices...</p>
            </div>
        </div>
    `;

    loadOffices(container);

    container.querySelector("#btn-add-office").addEventListener("click", () => {
        openOfficeModal(null, () => loadOffices(container));
    });

    return container;
}

async function loadOffices(container) {
    const slot = container.querySelector("#offices-table-slot");
    try {
        const data = await apiGet("/admin/offices");
        const offices = data.offices || [];

        slot.innerHTML = `
            <div style="overflow-x: auto;">
                <table class="table" style="width: 100%; font-size: 13.5px;">
                    <thead>
                        <tr>
                            <th>Office Name</th>
                            <th>Location</th>
                            <th>Hours</th>
                            <th>Contact</th>
                            <th>Keywords Match</th>
                            <th style="text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${offices.map(o => `
                            <tr data-id="${o.id}">
                                <td><strong>${escapeHtml(o.name)}</strong></td>
                                <td>${escapeHtml(o.location)}</td>
                                <td class="text-muted">${escapeHtml(o.hours)}</td>
                                <td>
                                    <div>📞 ${escapeHtml(o.phone)}</div>
                                    <div class="text-muted" style="font-size: 12px;">✉️ ${escapeHtml(o.email)}</div>
                                </td>
                                <td>
                                    <span class="badge" style="background: var(--surface-2); font-size: 11.5px;">
                                        ${escapeHtml(o.keywords || 'none')}
                                    </span>
                                </td>
                                <td style="text-align: right;">
                                    <button class="btn btn-secondary btn-sm btn-edit-office" style="padding: 4px 10px;">Edit</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        slot.querySelectorAll(".btn-edit-office").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = parseInt(btn.closest("tr").getAttribute("data-id"));
                const off = offices.find(x => x.id === id);
                if (off) openOfficeModal(off, () => loadOffices(container));
            });
        });

    } catch (e) {
        slot.innerHTML = `<div class="card-error" style="padding: 16px;">Failed to load offices: ${e.message}</div>`;
    }
}

function openOfficeModal(office, onSave) {
    const isEdit = Boolean(office);
    showModal({
        title: isEdit ? "Edit Campus Office" : "Add Campus Office",
        content: `
            <form id="office-form" style="display: flex; flex-direction: column; gap: 12px;">
                <div class="form-group">
                    <label class="form-label" for="off-name">Office Name</label>
                    <input type="text" id="off-name" class="form-input" value="${escapeHtml(office?.name || '')}" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="off-loc">Location</label>
                    <input type="text" id="off-loc" class="form-input" value="${escapeHtml(office?.location || '')}" required>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div class="form-group">
                        <label class="form-label" for="off-phone">Phone</label>
                        <input type="text" id="off-phone" class="form-input" value="${escapeHtml(office?.phone || '')}" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="off-email">Email</label>
                        <input type="email" id="off-email" class="form-input" value="${escapeHtml(office?.email || '')}" required>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label" for="off-hours">Working Hours</label>
                    <input type="text" id="off-hours" class="form-input" value="${escapeHtml(office?.hours || 'Mon-Fri 09:30 AM - 05:00 PM')}" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="off-kw">Matching Keywords (comma-separated)</label>
                    <input type="text" id="off-kw" class="form-input" placeholder="e.g. fees, dues, challan, payment" value="${escapeHtml(office?.keywords || '')}">
                </div>

                <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px;">
                    <button type="button" id="office-cancel-btn" class="btn btn-secondary">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Save Changes' : 'Create Office'}</button>
                </div>
            </form>
        `
    });

    document.getElementById("office-cancel-btn").onclick = hideModal;

    document.getElementById("office-form").onsubmit = async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById("off-name").value.trim(),
            location: document.getElementById("off-loc").value.trim(),
            phone: document.getElementById("off-phone").value.trim(),
            email: document.getElementById("off-email").value.trim(),
            hours: document.getElementById("off-hours").value.trim(),
            keywords: document.getElementById("off-kw").value.trim()
        };

        try {
            if (isEdit) {
                await apiPut(`/admin/offices/${office.id}`, payload);
                showToast("Office updated successfully.", "success");
            } else {
                await apiPost("/admin/offices", payload);
                showToast("Office created successfully.", "success");
            }
            hideModal();
            onSave();
        } catch (err) {
            showToast(err.message || "Failed to save office.", "error");
        }
    };
}

// =========================================================================
// 4. FORM SUBMISSIONS TABLE
// =========================================================================
export async function renderSubmissionsView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>📋 Student Form Submissions</h1>
            <p class="text-muted">Review submitted student applications, view autofilled values, and toggle reviewed status.</p>
        </div>

        <div class="card" style="padding: 20px;">
            <div id="submissions-table-slot">
                <p class="text-muted">Loading submissions...</p>
            </div>
        </div>
    `;

    loadSubmissions(container);
    return container;
}

async function loadSubmissions(container) {
    const slot = container.querySelector("#submissions-table-slot");
    try {
        const data = await apiGet("/admin/submissions");
        const subs = data.submissions || [];

        if (subs.length === 0) {
            slot.innerHTML = `<div class="empty-state"><h3>No submissions yet</h3><p class="text-muted">When students submit official forms, they will appear here.</p></div>`;
            return;
        }

        slot.innerHTML = `
            <div style="overflow-x: auto;">
                <table class="table" style="width: 100%; font-size: 13.5px;">
                    <thead>
                        <tr>
                            <th>Receipt Ref</th>
                            <th>Student</th>
                            <th>Form Title</th>
                            <th>Submitted At</th>
                            <th>Status</th>
                            <th style="text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${subs.map(s => `
                            <tr data-id="${s.id}">
                                <td><strong style="color: var(--brand);">${s.ref_number}</strong></td>
                                <td>
                                    <div><strong>${escapeHtml(s.student_name)}</strong></div>
                                    <div class="text-muted" style="font-size: 12px;">${escapeHtml(s.student_email)}</div>
                                </td>
                                <td>${escapeHtml(s.form_title)}</td>
                                <td class="text-muted" style="font-size: 12.5px;">${s.submitted_at}</td>
                                <td>
                                    <span class="badge ${s.status === 'reviewed' ? 'badge-success' : 'badge-accent'}">
                                        ${escapeHtml(s.status)}
                                    </span>
                                </td>
                                <td style="text-align: right; white-space: nowrap;">
                                    <button class="btn btn-secondary btn-sm btn-view-vals" style="padding: 4px 10px; margin-right: 6px;">View Data</button>
                                    <button class="btn btn-secondary btn-sm btn-toggle-status" style="padding: 4px 10px;">
                                        ${s.status === 'reviewed' ? 'Mark Pending' : 'Mark Reviewed'}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        slot.querySelectorAll("tr").forEach(tr => {
            const id = parseInt(tr.getAttribute("data-id"));
            const s = subs.find(x => x.id === id);

            const viewBtn = tr.querySelector(".btn-view-vals");
            if (viewBtn && s) {
                viewBtn.addEventListener("click", () => {
                    const entries = Object.entries(s.values || {});
                    showModal({
                        title: `Submission: ${s.ref_number}`,
                        content: `
                            <div style="margin-bottom: 14px;">
                                <strong>${escapeHtml(s.form_title)}</strong>
                                <div class="text-muted" style="font-size: 12.5px;">Submitted by ${escapeHtml(s.student_name)} on ${s.submitted_at}</div>
                            </div>
                            <div style="background: var(--surface-2); border-radius: var(--radius-sm); padding: 14px; border: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px;">
                                ${entries.map(([k, v]) => `
                                    <div style="font-size: 13px;">
                                        <span class="text-muted" style="font-weight: 600;">${escapeHtml(k)}:</span>
                                        <span style="color: var(--text); margin-left: 6px;">${escapeHtml(String(v))}</span>
                                    </div>
                                `).join('')}
                            </div>
                            <div style="display: flex; justify-content: flex-end; margin-top: 20px;">
                                <button class="btn btn-primary" onclick="window.CF_HIDE_MODAL ? window.CF_HIDE_MODAL() : null" id="close-sub-modal">Close</button>
                            </div>
                        `
                    });
                    document.getElementById("close-sub-modal").onclick = hideModal;
                });
            }

            const toggleBtn = tr.querySelector(".btn-toggle-status");
            if (toggleBtn && s) {
                toggleBtn.addEventListener("click", async () => {
                    const nextStatus = s.status === 'reviewed' ? 'submitted' : 'reviewed';
                    try {
                        await apiPatch(`/admin/submissions/${s.id}`, { status: nextStatus });
                        showToast(`Status updated to ${nextStatus}.`, "success");
                        loadSubmissions(container);
                    } catch (err) {
                        showToast(err.message || "Failed to update status.", "error");
                    }
                });
            }
        });

    } catch (e) {
        slot.innerHTML = `<div class="card-error" style="padding: 16px;">Failed to load submissions: ${e.message}</div>`;
    }
}

// =========================================================================
// 5. AI ENGINE STATUS VIEW
// =========================================================================
export async function renderAiStatusView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
            <div>
                <h1>⚡ AI Engine & Multi-Provider Status</h1>
                <p class="text-muted">Live monitoring of LLM providers (Groq, Gemini, Custom), active model lists, and circuit breakers.</p>
            </div>
            <button id="btn-test-ai" class="btn btn-primary" style="padding: 9px 18px;">🔄 Test AI Providers Now</button>
        </div>

        <div id="ai-health-slot">
            <p class="text-muted">Checking AI engines...</p>
        </div>
    `;

    loadAiHealth(container);

    const testBtn = container.querySelector("#btn-test-ai");
    testBtn.addEventListener("click", () => {
        testBtn.disabled = true;
        testBtn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> Pinging...`;
        loadAiHealth(container).then(() => {
            testBtn.disabled = false;
            testBtn.innerHTML = `🔄 Test AI Providers Now`;
            showToast("AI provider health check completed.", "success");
        });
    });

    return container;
}

async function loadAiHealth(container) {
    const slot = container.querySelector("#ai-health-slot");
    try {
        const health = await apiGet("/admin/health");
        const isOnline = health.status === "online";

        slot.innerHTML = `
            <!-- Overall Status Banner -->
            <div class="card" style="padding: 20px; margin-bottom: 24px; border-left: 6px solid ${isOnline ? 'var(--success)' : 'var(--accent)'};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 18px; font-weight: 700;">
                            Overall Engine Status: 
                            <span style="color: ${isOnline ? 'var(--success)' : 'var(--accent)'};">${isOnline ? 'ONLINE & READY' : 'OFFLINE MODE (SAFE GROUNDED)'}</span>
                        </div>
                        <div class="text-muted" style="font-size: 13px; margin-top: 4px;">
                            ${isOnline ? 'At least one configured LLM provider is active.' : 'Operating without external LLMs using grounded sentence match.'}
                        </div>
                    </div>
                    <span class="badge ${isOnline ? 'badge-success' : 'badge-warning'}" style="font-size: 13px; padding: 6px 14px;">
                        ${isOnline ? 'Active' : 'Offline'}
                    </span>
                </div>
            </div>

            <!-- Provider Cards Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                ${(health.providers || []).map(p => `
                    <div class="card" style="padding: 24px; display: flex; flex-direction: column;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 17px; margin-bottom: 2px;">${escapeHtml(p.name)}</h3>
                                <div class="text-muted" style="font-size: 12px;">Provider Service</div>
                            </div>
                            <span class="badge ${p.status === 'active' ? 'badge-success' : p.status === 'circuit_open' ? 'badge-danger' : ''}" style="${p.status === 'unconfigured' ? 'background: var(--surface-2); color: var(--text-muted);' : ''}">
                                ${escapeHtml(p.status)}
                            </span>
                        </div>

                        <div style="font-size: 13px; margin-bottom: 12px;">
                            <strong>Configured:</strong> ${p.configured ? '✅ Key Present' : '❌ Not Configured'}
                        </div>

                        ${p.models && p.models.length > 0 ? `
                            <div style="margin-top: auto; border-top: 1px solid var(--border); padding-top: 12px;">
                                <div class="text-muted" style="font-size: 11.5px; font-weight: 700; margin-bottom: 6px;">SUPPORTED MODELS</div>
                                <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                                    ${p.models.map(m => `
                                        <span class="badge" style="background: var(--surface-2); font-family: monospace; font-size: 11.5px;">${escapeHtml(m)}</span>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${p.vision_models && p.vision_models.length > 0 ? `
                            <div style="margin-top: 10px; border-top: 1px solid var(--border); padding-top: 10px;">
                                <div class="text-muted" style="font-size: 11.5px; font-weight: 700; margin-bottom: 6px;">VISION OCR MODELS</div>
                                <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                                    ${p.vision_models.map(m => `
                                        <span class="badge" style="background: rgba(197, 54, 120, 0.08); color: var(--brand); font-family: monospace; font-size: 11.5px;">${escapeHtml(m)}</span>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    } catch (e) {
        slot.innerHTML = `<div class="card-error" style="padding: 16px;">Failed to load AI health: ${e.message}</div>`;
    }
}

function debounce(fn, ms) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), ms);
    };
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
