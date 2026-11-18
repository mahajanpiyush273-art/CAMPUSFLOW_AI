/**
 * CampusFlow AI - Forms 3-Step Flow, My Questions & Profile Views
 * 1. Forms: Fill (with profile autofill chips) -> Review -> Confirm checkbox -> Submit receipt.
 * 2. My Questions: Status tracking (Answered, Pending Review, Admin Replied).
 * 3. Profile: View & update autofill data.
 */

import { apiGet, apiPost, apiPut } from "/static/js/api.js";
import { showToast, renderSkeleton } from "/static/js/ui.js";

// ==========================================
// 1. FORMS VIEW (LIST & 3-STEP FLOW)
// ==========================================
export async function renderFormsView(args = []) {
    const slug = args[0];
    if (slug) {
        return renderFormWizardView(slug);
    }

    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>📝 Official Campus Forms</h1>
            <p class="text-muted">Submit official applications with 3-step verification. Form fields are autofilled from your profile.</p>
        </div>

        <!-- Available Forms Grid -->
        <h3 style="margin-bottom: 14px;">Available Applications</h3>
        <div id="forms-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 40px;"></div>

        <!-- My Submissions Receipt History -->
        <div style="border-top: 1px solid var(--border); padding-top: 32px;">
            <h3 style="margin-bottom: 14px;">My Submitted Applications</h3>
            <div id="my-submissions-container"></div>
        </div>
    `;

    setupFormsDirectory(container);
    return container;
}

async function setupFormsDirectory(container) {
    const grid = container.querySelector("#forms-grid");
    const subContainer = container.querySelector("#my-submissions-container");

    grid.appendChild(renderSkeleton(2, 120));
    subContainer.appendChild(renderSkeleton(2, 60));

    try {
        const [formsData, subsData] = await Promise.all([
            apiGet("/forms"),
            apiGet("/my/submissions")
        ]);

        // Render Available Forms
        grid.innerHTML = "";
        if (!formsData.forms || formsData.forms.length === 0) {
            grid.innerHTML = `<div class="card" style="grid-column: 1/-1; text-align: center; color: var(--muted); padding: 24px;">No active forms available.</div>`;
        } else {
            formsData.forms.forEach(f => {
                const card = document.createElement("div");
                card.className = "card student-card";
                card.style.display = "flex";
                card.style.flexDirection = "column";
                card.style.justifyContent = "space-between";
                card.style.padding = "22px";

                card.innerHTML = `
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <h3 style="font-size: 17px;">${f.title}</h3>
                            <span class="badge badge-category">${f.office_name || 'Office'}</span>
                        </div>
                        <p class="text-muted" style="font-size: 13.5px; margin-bottom: 16px;">${f.description}</p>
                        <div style="font-size: 12.5px; color: var(--text-2); background: var(--surface-2); padding: 10px; border-radius: var(--radius-sm); margin-bottom: 18px;">
                            ℹ️ <em>${f.instructions}</em>
                        </div>
                    </div>
                    <a href="#/forms/${f.slug}" class="btn btn-accent" style="width: 100%;">
                        Open Application (3-Step Flow) →
                    </a>
                `;
                grid.appendChild(card);
            });
        }

        // Render Submissions History
        subContainer.innerHTML = "";
        const subs = subsData.submissions || [];
        if (subs.length === 0) {
            subContainer.innerHTML = `<div class="card" style="text-align: center; color: var(--muted); padding: 24px;">You have not submitted any forms yet.</div>`;
        } else {
            const tableCard = document.createElement("div");
            tableCard.className = "card";
            tableCard.style.padding = "0";
            tableCard.style.overflow = "hidden";

            tableCard.innerHTML = `
                <table style="width: 100%; border-collapse: collapse; font-size: 13.5px;">
                    <thead style="background: var(--surface-2); border-bottom: 1px solid var(--border); text-align: left;">
                        <tr>
                            <th style="padding: 12px 16px;">Reference</th>
                            <th style="padding: 12px 16px;">Form Title</th>
                            <th style="padding: 12px 16px;">Office</th>
                            <th style="padding: 12px 16px;">Submitted At</th>
                            <th style="padding: 12px 16px;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${subs.map(s => `
                            <tr style="border-bottom: 1px solid var(--border);">
                                <td style="padding: 12px 16px; font-weight: 700; color: var(--brand);">${s.ref_number}</td>
                                <td style="padding: 12px 16px; font-weight: 600;">${s.form_title}</td>
                                <td style="padding: 12px 16px; color: var(--muted);">${s.office_name || 'Admin'}</td>
                                <td style="padding: 12px 16px; color: var(--muted);">${s.confirmed_at}</td>
                                <td style="padding: 12px 16px;">
                                    <span class="badge ${s.status === 'reviewed' ? 'badge-new' : 'badge-sample'}">
                                        ${s.status}
                                    </span>
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
            subContainer.appendChild(tableCard);
        }

    } catch (e) {
        grid.innerHTML = `<div class="card" style="color: var(--danger);">${e.message}</div>`;
    }
}

// ------------------------------------------
// 3-STEP FORM WIZARD
// ------------------------------------------
async function renderFormWizardView(slug) {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 20px;">
            <a href="#/forms" style="font-size: 13.5px; font-weight: 600;">← Back to Forms Directory</a>
            <h1 id="form-wizard-title" style="margin-top: 10px;">Form Application</h1>
            <p id="form-wizard-desc" class="text-muted"></p>
        </div>

        <!-- Step Indicator Bar -->
        <div class="card" style="padding: 16px 24px; margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; max-width: 600px; margin: 0 auto; font-size: 13.5px; font-weight: 600;">
                <div id="step-ind-1" style="color: var(--brand); display: flex; align-items: center; gap: 6px;">
                    <span style="background: var(--brand); color: #fff; border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px;">1</span>
                    Fill Details
                </div>
                <div style="color: var(--border-2);">────────</div>
                <div id="step-ind-2" style="color: var(--muted); display: flex; align-items: center; gap: 6px;">
                    <span style="background: var(--border-2); color: #fff; border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px;">2</span>
                    Review Summary
                </div>
                <div style="color: var(--border-2);">────────</div>
                <div id="step-ind-3" style="color: var(--muted); display: flex; align-items: center; gap: 6px;">
                    <span style="background: var(--border-2); color: #fff; border-radius: 50%; width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px;">3</span>
                    Confirm & Submit
                </div>
            </div>
        </div>

        <!-- Wizard Step Containers -->
        <div id="wizard-content" class="card student-card" style="padding: 30px;"></div>
    `;

    setupFormWizard(container, slug);
    return container;
}

async function setupFormWizard(container, slug) {
    const contentEl = container.querySelector("#wizard-content");
    contentEl.appendChild(renderSkeleton(4, 40));

    try {
        const data = await apiGet(`/forms/${slug}`);
        const form = data.form;

        container.querySelector("#form-wizard-title").textContent = form.title;
        container.querySelector("#form-wizard-desc").textContent = form.description;

        let formData = {};
        // Initialize with default/autofilled values
        form.fields.forEach(f => {
            formData[f.name] = f.value || "";
        });

        // -----------------------------
        // STEP 1: FILL FORM
        // -----------------------------
        function renderStep1() {
            updateStepIndicators(container, 1);
            contentEl.innerHTML = `
                <h3 style="margin-bottom: 6px;">Step 1: Fill Application Details</h3>
                <p class="text-muted" style="margin-bottom: 22px; font-size: 13.5px;">
                    Fields marked with <span class="chip-autofill">autofilled from profile</span> were loaded from your student profile. Review or edit them before proceeding.
                </p>

                <form id="step-1-form">
                    ${form.fields.map(f => `
                        <div class="form-group">
                            <label class="form-label" for="field-${f.name}">
                                ${f.label} ${f.required ? '<span style="color: var(--accent);">*</span>' : ''}
                                ${f.autofilled ? '<span class="chip-autofill">autofilled from profile</span>' : ''}
                            </label>

                            ${f.type === 'select' ? `
                                <select id="field-${f.name}" class="form-select" ${f.required ? 'required' : ''}>
                                    <option value="">-- Select an option --</option>
                                    ${(f.options || []).map(opt => `
                                        <option value="${opt}" ${formData[f.name] === opt ? 'selected' : ''}>${opt}</option>
                                    `).join('')}
                                </select>
                            ` : f.type === 'textarea' ? `
                                <textarea id="field-${f.name}" class="form-textarea" placeholder="Enter details..." ${f.required ? 'required' : ''}>${formData[f.name] || ''}</textarea>
                            ` : `
                                <input type="${f.type === 'number' ? 'number' : 'text'}" id="field-${f.name}" class="form-input"
                                       value="${formData[f.name] || ''}" placeholder="Enter ${f.label}..." ${f.required ? 'required' : ''}>
                            `}
                        </div>
                    `).join('')}

                    <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
                        <button type="submit" class="btn btn-accent" style="padding: 10px 28px;">Continue to Review →</button>
                    </div>
                </form>
            `;

            container.querySelector("#step-1-form").addEventListener("submit", (e) => {
                e.preventDefault();
                form.fields.forEach(f => {
                    const el = container.querySelector(`#field-${f.name}`);
                    if (el) formData[f.name] = el.value.trim();
                });
                renderStep2();
            });
        }

        // -----------------------------
        // STEP 2: REVIEW SUMMARY
        // -----------------------------
        function renderStep2() {
            updateStepIndicators(container, 2);
            contentEl.innerHTML = `
                <h3 style="margin-bottom: 6px;">Step 2: Review Application Details</h3>
                <p class="text-muted" style="margin-bottom: 20px; font-size: 13.5px;">
                    Please carefully verify all details below. If anything needs correction, click "Edit Details".
                </p>

                <div style="background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-sm); overflow: hidden; margin-bottom: 24px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <tbody>
                            ${form.fields.map(f => `
                                <tr style="border-bottom: 1px solid var(--border);">
                                    <td style="padding: 12px 18px; font-weight: 600; width: 35%; color: var(--text-2);">${f.label}</td>
                                    <td style="padding: 12px 18px; color: var(--text);">
                                        ${formData[f.name] || '<em style="color: var(--muted);">Not provided</em>'}
                                        ${f.autofilled ? '<span class="chip-autofill">Profile verified</span>' : ''}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <button id="step-2-back-btn" class="btn btn-secondary">← Edit Details</button>
                    <button id="step-2-next-btn" class="btn btn-accent" style="padding: 10px 28px;">Proceed to Confirmation →</button>
                </div>
            `;

            container.querySelector("#step-2-back-btn").addEventListener("click", renderStep1);
            container.querySelector("#step-2-next-btn").addEventListener("click", renderStep3);
        }

        // -----------------------------
        // STEP 3: CONFIRM & SUBMIT
        // -----------------------------
        function renderStep3() {
            updateStepIndicators(container, 3);
            contentEl.innerHTML = `
                <h3 style="margin-bottom: 6px;">Step 3: Confirmation & Submission</h3>
                <p class="text-muted" style="margin-bottom: 24px; font-size: 13.5px;">
                    The university requires explicit student confirmation for all official applications.
                </p>

                <div style="background: #FFF1EE; border-left: 4px solid var(--accent); padding: 18px; border-radius: var(--radius-sm); margin-bottom: 24px;">
                    <label style="display: flex; align-items: flex-start; gap: 12px; cursor: pointer;">
                        <input type="checkbox" id="confirmation-checkbox" style="margin-top: 3px; transform: scale(1.2);">
                        <span style="font-size: 14.5px; font-weight: 600; color: var(--text); line-height: 1.45;">
                            I confirm that I have checked every detail and that all statements and information provided in this application are accurate and genuine.
                        </span>
                    </label>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <button id="step-3-back-btn" class="btn btn-secondary">← Back to Review</button>
                    <button id="step-3-submit-btn" class="btn btn-accent" disabled style="padding: 12px 32px; font-size: 15px;">
                        Submit Application
                    </button>
                </div>
            `;

            const checkbox = container.querySelector("#confirmation-checkbox");
            const submitBtn = container.querySelector("#step-3-submit-btn");

            checkbox.addEventListener("change", () => {
                submitBtn.disabled = !checkbox.checked;
            });

            container.querySelector("#step-3-back-btn").addEventListener("click", renderStep2);

            submitBtn.addEventListener("click", async () => {
                submitBtn.disabled = true;
                submitBtn.textContent = "Submitting...";

                try {
                    const res = await apiPost(`/forms/${slug}/submit`, {
                        values: formData,
                        confirmed: true
                    });

                    renderReceipt(res);
                } catch (err) {
                    showToast(err.message, "error");
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Submit Application";
                }
            });
        }

        // -----------------------------
        // SUBMISSION RECEIPT
        // -----------------------------
        function renderReceipt(res) {
            contentEl.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 48px; margin-bottom: 12px;">🎉</div>
                    <h2 style="color: var(--success); margin-bottom: 6px;">Application Submitted Successfully!</h2>
                    <p class="text-muted" style="margin-bottom: 24px;">Your official request has been logged and forwarded to the office.</p>

                    <div style="background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; max-width: 480px; margin: 0 auto 28px auto; text-align: left;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                            <span class="text-muted">Reference Number:</span>
                            <strong style="color: var(--brand); font-size: 16px;">${res.ref_number}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                            <span class="text-muted">Application Form:</span>
                            <strong>${res.form_title}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                            <span class="text-muted">Submission Date:</span>
                            <span>${res.confirmed_at}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span class="text-muted">Review Status:</span>
                            <span class="badge badge-sample">${res.status}</span>
                        </div>
                    </div>

                    <div style="display: flex; justify-content: center; gap: 14px;">
                        <a href="#/forms" class="btn btn-secondary">View All Forms</a>
                        <a href="#/dashboard" class="btn btn-primary">Return to Dashboard</a>
                    </div>
                </div>
            `;
        }

        renderStep1();

    } catch (err) {
        contentEl.innerHTML = `<div class="card" style="color: var(--danger);">${err.message}</div>`;
    }
}

function updateStepIndicators(container, activeStep) {
    [1, 2, 3].forEach(step => {
        const ind = container.querySelector(`#step-ind-${step}`);
        if (!ind) return;
        const circle = ind.querySelector("span");
        if (step === activeStep) {
            ind.style.color = "var(--brand)";
            circle.style.background = "var(--brand)";
        } else if (step < activeStep) {
            ind.style.color = "var(--success)";
            circle.style.background = "var(--success)";
            circle.textContent = "✓";
        } else {
            ind.style.color = "var(--muted)";
            circle.style.background = "var(--border-2)";
            circle.textContent = step;
        }
    });
}

// ==========================================
// 2. MY QUESTIONS VIEW
// ==========================================
export async function renderMyQuestionsView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>❓ My Questions & Verified Replies</h1>
            <p class="text-muted">Track all questions asked. Unverified questions are reviewed by administrative staff, and their official reply appears here.</p>
        </div>

        <div id="my-questions-list" style="display: flex; flex-direction: column; gap: 16px;"></div>
    `;

    const listEl = container.querySelector("#my-questions-list");
    listEl.appendChild(renderSkeleton(3, 80));

    try {
        const data = await apiGet("/questions");
        listEl.innerHTML = "";

        const questions = data.questions || [];
        if (questions.length === 0) {
            listEl.innerHTML = `<div class="card" style="text-align: center; padding: 32px; color: var(--muted);">You haven't asked any questions yet. Start in the <a href="#/ask">Ask Assistant</a>.</div>`;
            return;
        }

        questions.forEach(q => {
            const card = document.createElement("div");
            card.className = "card";
            card.style.padding = "20px";

            let badgeHtml = "";
            if (q.status === "answered") {
                badgeHtml = `<span class="badge badge-new">Answered by Notice (${q.confidence}%)</span>`;
            } else if (q.status === "admin_replied") {
                badgeHtml = `<span class="badge badge-category" style="background: var(--brand); color: #fff;">Admin Replied</span>`;
            } else {
                badgeHtml = `<span class="badge badge-sample" style="background: var(--accent-tint); color: var(--accent-dark); border-color: var(--accent);">Pending Admin Review</span>`;
            }

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 8px;">
                    <div style="font-weight: 700; font-size: 16px; color: var(--text);">Q: "${q.text}"</div>
                    <div>${badgeHtml}</div>
                </div>
                <div style="font-size: 12.5px; color: var(--muted); margin-bottom: 12px;">Asked on: ${q.created_at}</div>

                <div style="background: var(--surface-2); padding: 14px; border-radius: var(--radius-sm); border-left: 3px solid ${q.status === 'admin_replied' ? 'var(--brand)' : (q.status === 'answered' ? 'var(--success)' : 'var(--accent)')}; font-size: 14px; line-height: 1.5; color: var(--text-2);">
                    <strong>${q.status === 'admin_replied' ? 'Official Admin Reply:' : 'Assistant Answer:'}</strong>
                    <div style="margin-top: 4px;">${q.answer}</div>
                    ${q.doc_title ? `<div style="font-size: 12px; color: var(--muted); margin-top: 8px;">Verified source: ${q.doc_title}</div>` : ''}
                </div>
            `;
            listEl.appendChild(card);
        });

    } catch (e) {
        listEl.innerHTML = `<div class="card" style="color: var(--danger);">${e.message}</div>`;
    }

    return container;
}

// ==========================================
// 3. PROFILE VIEW
// ==========================================
export async function renderProfileView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>👤 Student Profile & Autofill Settings</h1>
            <p class="text-muted">These details fill your official forms automatically. You always confirm every detail before submitting.</p>
        </div>

        <div class="card student-card" style="padding: 28px; max-width: 680px;">
            <form id="profile-edit-form">
                <div id="profile-fields-slot"></div>
                <button type="submit" id="save-profile-btn" class="btn btn-accent" style="margin-top: 20px; padding: 10px 24px;">
                    Save Profile Settings
                </button>
            </form>
        </div>
    `;

    setupProfileView(container);
    return container;
}

async function setupProfileView(container) {
    const slot = container.querySelector("#profile-fields-slot");
    slot.appendChild(renderSkeleton(4, 40));

    try {
        const data = await apiGet("/student/profile");
        const p = data.profile || {};
        const u = data.user || {};

        slot.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                    <label class="form-label">Full Name</label>
                    <input type="text" class="form-input" value="${u.full_name || ''}" disabled style="background: var(--surface-2); color: var(--muted);">
                </div>
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="text" class="form-input" value="${u.email || ''}" disabled style="background: var(--surface-2); color: var(--muted);">
                </div>
                <div class="form-group">
                    <label class="form-label">Roll Number</label>
                    <input type="text" id="prof-roll" class="form-input" value="${p.roll_no || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">Enrollment Number</label>
                    <input type="text" id="prof-enroll" class="form-input" value="${p.enrollment_no || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">Programme / Degree</label>
                    <input type="text" id="prof-prog" class="form-input" value="${p.programme || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">Department</label>
                    <input type="text" id="prof-dept" class="form-input" value="${p.department || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">Semester</label>
                    <input type="text" id="prof-sem" class="form-input" value="${p.semester || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">Phone Number</label>
                    <input type="text" id="prof-phone" class="form-input" value="${p.phone || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">Hostel Block</label>
                    <input type="text" id="prof-block" class="form-input" value="${p.hostel_block || ''}" placeholder="e.g. Block C">
                </div>
                <div class="form-group">
                    <label class="form-label">Room Number</label>
                    <input type="text" id="prof-room" class="form-input" value="${p.room_no || ''}" placeholder="e.g. 304">
                </div>
                <div class="form-group">
                    <label class="form-label">Guardian Name</label>
                    <input type="text" id="prof-gname" class="form-input" value="${p.guardian_name || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">Guardian Phone</label>
                    <input type="text" id="prof-gphone" class="form-input" value="${p.guardian_phone || ''}">
                </div>
            </div>
        `;

        const form = container.querySelector("#profile-edit-form");
        const saveBtn = container.querySelector("#save-profile-btn");

        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            saveBtn.disabled = true;
            saveBtn.textContent = "Saving...";

            const payload = {
                roll_no: container.querySelector("#prof-roll").value.trim(),
                enrollment_no: container.querySelector("#prof-enroll").value.trim(),
                programme: container.querySelector("#prof-prog").value.trim(),
                department: container.querySelector("#prof-dept").value.trim(),
                semester: container.querySelector("#prof-sem").value.trim(),
                phone: container.querySelector("#prof-phone").value.trim(),
                hostel_block: container.querySelector("#prof-block").value.trim(),
                room_no: container.querySelector("#prof-room").value.trim(),
                guardian_name: container.querySelector("#prof-gname").value.trim(),
                guardian_phone: container.querySelector("#prof-gphone").value.trim(),
            };

            try {
                await apiPut("/student/profile", payload);
                showToast("Profile settings saved successfully!", "success");
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                saveBtn.disabled = false;
                saveBtn.textContent = "Save Profile Settings";
            }
        });

    } catch (err) {
        slot.innerHTML = `<div class="card" style="color: var(--danger);">${err.message}</div>`;
    }
}
