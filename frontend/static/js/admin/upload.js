/**
 * CampusFlow AI - Admin Upload Document Wizard
 * 4-Step interactive upload flow:
 * Step 1: Upload file (PDF/Word/Text/Image) or paste text
 * Step 2: Animated AI reading stepper
 * Step 3: Split-screen review & fix (raw text + entities + AI flags + re-check)
 * Step 4: Confirm & publish with strict blocking flags gate
 */

import { apiGet, apiPost, apiPut } from "/static/js/api.js";
import { showToast } from "/static/js/ui.js";

let currentStep = 1;
let currentDraft = null;
let officesList = [];

export async function renderUploadView() {
    currentStep = 1;
    currentDraft = null;

    const container = document.createElement("div");
    container.className = "upload-wizard-container";

    // Load offices for dropdowns
    try {
        const offRes = await apiGet("/admin/offices");
        officesList = offRes.offices || [];
    } catch (e) {
        officesList = [];
    }

    renderWizard(container);
    return container;
}

function renderWizard(container) {
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>📤 Upload Campus Document</h1>
            <p class="text-muted">Ingest official university circulars, exam schedules, fee notices, and forms with AI extraction and conflict checks.</p>
        </div>

        <!-- Wizard Progress Steps Indicator -->
        <div class="wizard-stepper" style="display: flex; justify-content: space-between; position: relative; margin-bottom: 32px; max-width: 760px;">
            <div class="wizard-step ${currentStep >= 1 ? 'active' : ''}" data-step="1">
                <div class="step-bubble ${currentStep === 1 ? 'current' : ''}">1</div>
                <div class="step-label">Upload Source</div>
            </div>
            <div class="wizard-step ${currentStep >= 2 ? 'active' : ''}" data-step="2">
                <div class="step-bubble ${currentStep === 2 ? 'current' : ''}">2</div>
                <div class="step-label">AI Extraction</div>
            </div>
            <div class="wizard-step ${currentStep >= 3 ? 'active' : ''}" data-step="3">
                <div class="step-bubble ${currentStep === 3 ? 'current' : ''}">3</div>
                <div class="step-label">Review & Fix</div>
            </div>
            <div class="wizard-step ${currentStep >= 4 ? 'active' : ''}" data-step="4">
                <div class="step-bubble ${currentStep === 4 ? 'current' : ''}">4</div>
                <div class="step-label">Publish</div>
            </div>
        </div>

        <!-- Step Views Slot -->
        <div id="wizard-step-slot"></div>
    `;

    const slot = container.querySelector("#wizard-step-slot");

    if (currentStep === 1) {
        renderStep1Upload(container, slot);
    } else if (currentStep === 2) {
        renderStep2AiReading(container, slot);
    } else if (currentStep === 3) {
        renderStep3Review(container, slot);
    } else if (currentStep === 4) {
        renderStep4Publish(container, slot);
    }
}

// -------------------------------------------------------------
// STEP 1: UPLOAD SOURCE
// -------------------------------------------------------------
function renderStep1Upload(container, slot) {
    let uploadMode = "file"; // 'file' or 'text'

    slot.innerHTML = `
        <div class="card" style="max-width: 760px; padding: 28px;">
            <div style="display: flex; gap: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <button type="button" id="tab-file" class="btn btn-primary btn-sm">📄 File Upload (PDF, Word, Image, Text)</button>
                <button type="button" id="tab-paste" class="btn btn-secondary btn-sm">✏️ Type or Paste Notice</button>
            </div>

            <form id="wizard-upload-form">
                <div class="form-group">
                    <label class="form-label" for="wizard-doc-type">Document Type</label>
                    <select id="wizard-doc-type" class="form-input">
                        <option value="Notice" selected>Notice (Standard Circular / Announcement)</option>
                        <option value="Event">Event (Workshop, Fest, Seminar, Hackathon)</option>
                        <option value="Form">Form (Official Student Application)</option>
                        <option value="Handbook">Handbook (Ordinance, Syllabus, Policy)</option>
                    </select>
                </div>

                <!-- Form Link Input (Asked when Document Type is Form) -->
                <div id="wizard-form-link-group" class="form-group" style="display: none;">
                    <label class="form-label" for="wizard-form-link">Form Link / Application URL <span class="text-danger">*</span></label>
                    <input type="url" id="wizard-form-link" class="form-input" placeholder="https://forms.google.com/... or campus portal application link">
                    <div class="text-muted" style="font-size: 12px; margin-top: 4px;">Direct link for students to fill or download this application.</div>
                </div>

                <!-- File Drag & Drop Zone -->
                <div id="file-drop-area" class="dropzone" style="border: 2px dashed var(--border); border-radius: var(--radius-md); padding: 36px 20px; text-align: center; cursor: pointer; background: var(--surface-2); margin-bottom: 20px; transition: border-color 0.2s;">
                    <div style="font-size: 38px; margin-bottom: 8px;">📑</div>
                    <div style="font-weight: 600; font-size: 15px; margin-bottom: 4px;">Drag and drop file here, or click to browse</div>
                    <div class="text-muted" style="font-size: 12.5px;">Supports PDF, DOCX, TXT, MD, JPG, PNG (Max 15MB)</div>
                    <input type="file" id="wizard-file-input" accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg" style="display: none;">
                    <div id="selected-file-name" style="margin-top: 14px; font-weight: 700; color: var(--brand); display: none;"></div>
                </div>

                <!-- Text Area for Paste Mode -->
                <div id="paste-text-area" class="form-group" style="display: none;">
                    <label class="form-label" for="wizard-pasted-text">Notice Content</label>
                    <textarea id="wizard-pasted-text" class="form-input" rows="10" placeholder="Paste the official notice text here..."></textarea>
                </div>

                <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px;">
                    <button type="submit" id="btn-submit-upload" class="btn btn-primary" style="padding: 10px 24px;">
                        Continue to AI Extraction →
                    </button>
                </div>
            </form>
        </div>
    `;

    const tabFile = slot.querySelector("#tab-file");
    const tabPaste = slot.querySelector("#tab-paste");
    const dropArea = slot.querySelector("#file-drop-area");
    const pasteArea = slot.querySelector("#paste-text-area");
    const fileInput = slot.querySelector("#wizard-file-input");
    const fileNameDisplay = slot.querySelector("#selected-file-name");
    const form = slot.querySelector("#wizard-upload-form");
    const docTypeSelect = slot.querySelector("#wizard-doc-type");
    const formLinkGroup = slot.querySelector("#wizard-form-link-group");
    const formLinkInput = slot.querySelector("#wizard-form-link");

    docTypeSelect.addEventListener("change", () => {
        if (docTypeSelect.value === "Form") {
            formLinkGroup.style.display = "block";
            formLinkInput.required = true;
        } else {
            formLinkGroup.style.display = "none";
            formLinkInput.required = false;
        }
    });

    tabFile.addEventListener("click", () => {
        uploadMode = "file";
        tabFile.className = "btn btn-primary btn-sm";
        tabPaste.className = "btn btn-secondary btn-sm";
        dropArea.style.display = "block";
        pasteArea.style.display = "none";
    });

    tabPaste.addEventListener("click", () => {
        uploadMode = "text";
        tabPaste.className = "btn btn-primary btn-sm";
        tabFile.className = "btn btn-secondary btn-sm";
        dropArea.style.display = "none";
        pasteArea.style.display = "block";
    });

    dropArea.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            const f = fileInput.files[0];
            fileNameDisplay.textContent = `Selected: ${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
            fileNameDisplay.style.display = "block";
            dropArea.style.borderColor = "var(--brand)";
        }
    });

    // Drag and Drop listeners
    ["dragenter", "dragover"].forEach(evt => {
        dropArea.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.style.borderColor = "var(--brand)";
            dropArea.style.background = "rgba(197, 54, 120, 0.05)";
        });
    });

    ["dragleave", "drop"].forEach(evt => {
        dropArea.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.style.background = "var(--surface-2)";
        });
    });

    dropArea.addEventListener("drop", (e) => {
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            const f = fileInput.files[0];
            fileNameDisplay.textContent = `Selected: ${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
            fileNameDisplay.style.display = "block";
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const docType = slot.querySelector("#wizard-doc-type").value;
        const pastedText = slot.querySelector("#wizard-pasted-text").value.trim();
        const formLink = formLinkInput ? formLinkInput.value.trim() : "";
        const hasFile = fileInput.files && fileInput.files.length > 0;

        if (uploadMode === "file" && !hasFile) {
            showToast("Please choose a file to upload or switch to typing text.", "error");
            return;
        }
        if (uploadMode === "text" && !pastedText) {
            showToast("Please paste the notice text.", "error");
            return;
        }
        if (docType === "Form" && !formLink) {
            showToast("Please enter the Form link or Application URL.", "error");
            return;
        }

        // Store upload payload and transition to step 2
        container._uploadData = {
            docType,
            uploadMode,
            file: hasFile ? fileInput.files[0] : null,
            pastedText: pastedText,
            formLink: formLink
        };

        currentStep = 2;
        renderWizard(container);
    });
}

// -------------------------------------------------------------
// STEP 2: ANIMATED AI READING STEPPER
// -------------------------------------------------------------
async function renderStep2AiReading(container, slot) {
    slot.innerHTML = `
        <div class="card" style="max-width: 600px; margin: 0 auto; padding: 36px 28px; text-align: center;">
            <div style="font-size: 40px; margin-bottom: 12px; animation: pulse 1.5s infinite;">🤖</div>
            <h3 style="margin-bottom: 8px;">AI Reading & Extraction Engine</h3>
            <p class="text-muted" style="font-size: 13.5px; margin-bottom: 28px;">Parsing document text, extracting dates, and running conflict validation...</p>

            <div style="text-align: left; max-width: 420px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px;">
                <div id="ai-step-ocr" style="display: flex; align-items: center; gap: 12px;">
                    <span class="spinner" style="width: 18px; height: 18px; border-width: 2px;"></span>
                    <span style="font-size: 13.5px; font-weight: 600;">1. Reading file & extracting text...</span>
                </div>
                <div id="ai-step-dates" style="display: flex; align-items: center; gap: 12px; opacity: 0.5;">
                    <span style="width: 18px; text-align: center;">⏳</span>
                    <span style="font-size: 13.5px; font-weight: 500;">2. Identifying deadlines & entities...</span>
                </div>
                <div id="ai-step-conflicts" style="display: flex; align-items: center; gap: 12px; opacity: 0.5;">
                    <span style="width: 18px; text-align: center;">⏳</span>
                    <span style="font-size: 13.5px; font-weight: 500;">3. Checking calendar & conflicts...</span>
                </div>
            </div>
        </div>
    `;

    const stepOcr = slot.querySelector("#ai-step-ocr");
    const stepDates = slot.querySelector("#ai-step-dates");
    const stepConflicts = slot.querySelector("#ai-step-conflicts");

    // Perform actual API upload call
    const formData = new FormData();
    const data = container._uploadData;
    if (data.file) {
        formData.append("file", data.file);
    }
    if (data.pastedText) {
        formData.append("pasted_text", data.pastedText);
    }
    formData.append("doc_type", data.docType);
    if (data.formLink) {
        formData.append("registration_url", data.formLink);
    }

    try {
        // Step 1 complete simulation visually
        setTimeout(() => {
            if (stepOcr) stepOcr.innerHTML = `<span style="color: var(--success); font-weight: 700;">✓</span> <span style="font-size: 13.5px; font-weight: 600;">1. Text extracted successfully</span>`;
            if (stepDates) {
                stepDates.style.opacity = "1";
                stepDates.innerHTML = `<span class="spinner" style="width: 18px; height: 18px; border-width: 2px;"></span> <span style="font-size: 13.5px; font-weight: 600;">2. Identifying deadlines & entities...</span>`;
            }
        }, 600);

        setTimeout(() => {
            if (stepDates) stepDates.innerHTML = `<span style="color: var(--success); font-weight: 700;">✓</span> <span style="font-size: 13.5px; font-weight: 600;">2. Deadlines extracted</span>`;
            if (stepConflicts) {
                stepConflicts.style.opacity = "1";
                stepConflicts.innerHTML = `<span class="spinner" style="width: 18px; height: 18px; border-width: 2px;"></span> <span style="font-size: 13.5px; font-weight: 600;">3. Checking calendar & conflicts...</span>`;
            }
        }, 1200);

        const resp = await fetch("/api/admin/documents/upload", {
            method: "POST",
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: "Upload failed" }));
            throw new Error(err.detail || "Upload extraction failed.");
        }

        const draft = await resp.json();
        currentDraft = draft;

        setTimeout(() => {
            currentStep = 3;
            renderWizard(container);
        }, 1600);

    } catch (err) {
        slot.innerHTML = `
            <div class="card" style="max-width: 500px; margin: 0 auto; padding: 28px; text-align: center;">
                <div style="font-size: 36px; margin-bottom: 8px;">❌</div>
                <h3>Extraction Error</h3>
                <p class="text-danger" style="margin: 12px 0;">${err.message || 'Error processing document.'}</p>
                <button id="btn-retry-step1" class="btn btn-secondary">← Back to Upload</button>
            </div>
        `;
        slot.querySelector("#btn-retry-step1").addEventListener("click", () => {
            currentStep = 1;
            renderWizard(container);
        });
    }
}

// -------------------------------------------------------------
// STEP 3: REVIEW & FIX (SPLIT-SCREEN EDITOR)
// -------------------------------------------------------------
function renderStep3Review(container, slot) {
    if (!currentDraft) {
        currentStep = 1;
        renderWizard(container);
        return;
    }

    const d = currentDraft;

    slot.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;">
            <!-- Left Column: Raw Text Editor & Highlight Preview -->
            <div class="card" style="padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="font-size: 16px;">📄 Notice Content</h3>
                    <button type="button" id="btn-recheck-ai" class="btn btn-secondary btn-sm" style="display: flex; align-items: center; gap: 6px;">
                        <span>🔄</span><span>Re-check with AI</span>
                    </button>
                </div>

                <div class="form-group">
                    <label class="form-label" for="edit-raw-text">Full Text (Edit freely — AI will re-extract dates on Re-check)</label>
                    <textarea id="edit-raw-text" class="form-input" rows="18" style="font-family: monospace; font-size: 13px; line-height: 1.5;">${escapeHtml(d.raw_text || '')}</textarea>
                </div>

                <!-- AI Extraction Summary Snippet -->
                <div style="margin-top: 14px; padding: 12px; background: var(--surface-2); border-radius: var(--radius-sm); border: 1px solid var(--border); font-size: 12.5px;">
                    <strong>AI Summary:</strong>
                    <div id="preview-summary" class="text-muted" style="margin-top: 4px;">${escapeHtml(d.summary || 'No summary generated.')}</div>
                </div>
            </div>

            <!-- Right Column: Form Fields, Deadlines Table & Flags Panel -->
            <div style="display: flex; flex-direction: column; gap: 20px;">
                <!-- AI Validation Flags Panel -->
                <div class="card" style="padding: 18px;" id="flags-container">
                    ${renderFlagsPanel(d.flags || [])}
                </div>

                <!-- Notice Metadata Form -->
                <div class="card" style="padding: 20px;">
                    <h3 style="font-size: 16px; margin-bottom: 16px;">📋 Metadata & Category</h3>

                    <div class="form-group">
                        <label class="form-label" for="edit-title">Notice Title <span class="text-danger">*</span></label>
                        <input type="text" id="edit-title" class="form-input" value="${escapeHtml(d.title || '')}" required>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div class="form-group">
                            <label class="form-label" for="edit-category">Category</label>
                            <select id="edit-category" class="form-input">
                                ${['Fees', 'Exams', 'Forms', 'Events', 'Admissions', 'Other'].map(cat => `
                                    <option value="${cat}" ${d.category === cat ? 'selected' : ''}>${cat}</option>
                                `).join('')}
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-doc-type">Document Type</label>
                            <select id="edit-doc-type" class="form-input">
                                ${['Notice', 'Event', 'Form', 'Handbook', 'Policy'].map(dt => `
                                    <option value="${dt}" ${d.doc_type === dt ? 'selected' : ''}>${dt}</option>
                                `).join('')}
                            </select>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div class="form-group">
                            <label class="form-label" for="edit-department">Department / Issuer</label>
                            <input type="text" id="edit-department" class="form-input" value="${escapeHtml(d.department || '')}">
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-office-id">Campus Office</label>
                            <select id="edit-office-id" class="form-input">
                                <option value="">None / Unassigned</option>
                                ${officesList.map(o => `
                                    <option value="${o.id}" ${d.office_id === o.id ? 'selected' : ''}>${escapeHtml(o.name)}</option>
                                `).join('')}
                            </select>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div class="form-group">
                            <label class="form-label" for="edit-publish-date">Publish Date</label>
                            <input type="date" id="edit-publish-date" class="form-input" value="${d.publish_date || ''}">
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-expiry-date">Expiry Date (Optional)</label>
                            <input type="date" id="edit-expiry-date" class="form-input" value="${d.expiry_date || ''}">
                        </div>
                    </div>

                    <!-- Event specific fields -->
                    <div id="event-fields-block" style="${d.doc_type === 'Event' ? '' : 'display: none;'} margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);">
                        <div class="form-group">
                            <label class="form-label" for="edit-event-start">Event Date & Time</label>
                            <input type="text" id="edit-event-start" class="form-input" placeholder="e.g. 2026-11-20 10:00 AM" value="${escapeHtml(d.event_start || '')}">
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="edit-venue">Venue</label>
                            <input type="text" id="edit-venue" class="form-input" placeholder="e.g. Auditorium Hall B" value="${escapeHtml(d.venue || '')}">
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="edit-reg-url">Registration URL</label>
                            <input type="url" id="edit-reg-url" class="form-input" placeholder="https://..." value="${escapeHtml(d.registration_url || '')}">
                        </div>
                    </div>

                    <!-- Form specific fields -->
                    <div id="form-fields-block" style="${d.doc_type === 'Form' ? '' : 'display: none;'} margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);">
                        <div class="form-group">
                            <label class="form-label" for="edit-form-link">Form Link / Application URL <span class="text-danger">*</span></label>
                            <input type="url" id="edit-form-link" class="form-input" placeholder="https://forms.google.com/... or campus portal application link" value="${escapeHtml(d.registration_url || '')}">
                            <div class="text-muted" style="font-size: 12px; margin-top: 4px;">Direct link for students to fill or download this application.</div>
                        </div>
                    </div>
                </div>

                <!-- Detected Deadlines Table -->
                <div class="card" style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h3 style="font-size: 16px;">⏰ Extracted Deadlines</h3>
                        <button type="button" id="btn-add-deadline" class="btn btn-secondary btn-sm">+ Add Deadline</button>
                    </div>

                    <div style="overflow-x: auto;">
                        <table class="table" style="width: 100%; font-size: 13px;">
                            <thead>
                                <tr>
                                    <th>Label</th>
                                    <th>Date</th>
                                    <th>Time</th>
                                    <th style="width: 40px;"></th>
                                </tr>
                            </thead>
                            <tbody id="deadlines-table-body">
                                ${(d.deadlines || []).map((dl, idx) => `
                                    <tr data-dl-idx="${idx}">
                                        <td><input type="text" class="form-input dl-label" value="${escapeHtml(dl.label || '')}" style="padding: 4px 8px; font-size: 12.5px;"></td>
                                        <td><input type="date" class="form-input dl-date" value="${dl.date || ''}" style="padding: 4px 8px; font-size: 12.5px;"></td>
                                        <td><input type="time" class="form-input dl-time" value="${dl.time || '17:00'}" style="padding: 4px 8px; font-size: 12.5px;"></td>
                                        <td><button type="button" class="btn btn-secondary btn-sm btn-del-dl" style="padding: 2px 6px;">✕</button></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Footer Navigation Buttons -->
                <div style="display: flex; justify-content: space-between; gap: 12px; margin-top: 8px;">
                    <button type="button" id="btn-save-draft" class="btn btn-secondary">💾 Save Draft</button>
                    <button type="button" id="btn-proceed-publish" class="btn btn-primary" style="padding: 10px 24px;">Continue to Publish →</button>
                </div>
            </div>
        </div>
    `;

    // Dynamic show/hide for event and form fields
    const docTypeSelect = slot.querySelector("#edit-doc-type");
    const eventBlock = slot.querySelector("#event-fields-block");
    const formBlock = slot.querySelector("#form-fields-block");
    docTypeSelect.addEventListener("change", () => {
        eventBlock.style.display = docTypeSelect.value === "Event" ? "block" : "none";
        formBlock.style.display = docTypeSelect.value === "Form" ? "block" : "none";
    });

    // Add Deadline button listener
    const dlTableBody = slot.querySelector("#deadlines-table-body");
    slot.querySelector("#btn-add-deadline").addEventListener("click", () => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><input type="text" class="form-input dl-label" value="Deadline" style="padding: 4px 8px; font-size: 12.5px;"></td>
            <td><input type="date" class="form-input dl-date" value="${new Date().toISOString().substring(0, 10)}" style="padding: 4px 8px; font-size: 12.5px;"></td>
            <td><input type="time" class="form-input dl-time" value="17:00" style="padding: 4px 8px; font-size: 12.5px;"></td>
            <td><button type="button" class="btn btn-secondary btn-sm btn-del-dl" style="padding: 2px 6px;">✕</button></td>
        `;
        dlTableBody.appendChild(tr);
        wireDeleteButtons(dlTableBody);
    });
    wireDeleteButtons(dlTableBody);

    // Re-check with AI Button Listener
    const btnRecheck = slot.querySelector("#btn-recheck-ai");
    btnRecheck.addEventListener("click", async () => {
        const rawText = slot.querySelector("#edit-raw-text").value.trim();
        if (!rawText) {
            showToast("Notice text cannot be empty to re-check.", "error");
            return;
        }

        btnRecheck.disabled = true;
        btnRecheck.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> Re-checking...`;

        try {
            const recheckRes = await apiPost(`/admin/documents/${d.id}/recheck`, { raw_text: rawText });
            currentDraft = recheckRes.document;
            showToast("AI re-check completed. Metadata and flags updated.", "success");
            renderWizard(container);
        } catch (err) {
            showToast(err.message || "Failed to re-check with AI.", "error");
            btnRecheck.disabled = false;
            btnRecheck.innerHTML = `<span>🔄</span><span>Re-check with AI</span>`;
        }
    });

    // Save Draft Button Listener
    slot.querySelector("#btn-save-draft").addEventListener("click", async () => {
        const payload = collectFormData(slot);
        try {
            const updated = await apiPut(`/admin/documents/${d.id}`, payload);
            currentDraft = updated.document;
            slot.querySelector("#flags-container").innerHTML = renderFlagsPanel(currentDraft.flags || []);
            showToast("Draft saved successfully.", "success");
        } catch (err) {
            showToast(err.message || "Failed to save draft.", "error");
        }
    });

    // Proceed to Step 4 Listener
    slot.querySelector("#btn-proceed-publish").addEventListener("click", async () => {
        const payload = collectFormData(slot);
        if (!payload.title) {
            showToast("Please enter a title for this notice.", "error");
            return;
        }

        try {
            const updated = await apiPut(`/admin/documents/${d.id}`, payload);
            currentDraft = updated.document;
            currentStep = 4;
            renderWizard(container);
        } catch (err) {
            showToast(err.message || "Failed to update notice.", "error");
        }
    });
}

function wireDeleteButtons(tbody) {
    tbody.querySelectorAll(".btn-del-dl").forEach(btn => {
        btn.onclick = () => btn.closest("tr").remove();
    });
}

function collectFormData(slot) {
    const deadlines = [];
    slot.querySelectorAll("#deadlines-table-body tr").forEach(tr => {
        const label = tr.querySelector(".dl-label").value.trim();
        const date = tr.querySelector(".dl-date").value.trim();
        const time = tr.querySelector(".dl-time").value.trim();
        if (label && date) {
            deadlines.push({ label, date, time });
        }
    });

    const docTypeVal = slot.querySelector("#edit-doc-type").value;
    let regUrl = null;
    if (docTypeVal === "Form") {
        regUrl = slot.querySelector("#edit-form-link")?.value.trim() || null;
    } else if (docTypeVal === "Event") {
        regUrl = slot.querySelector("#edit-reg-url")?.value.trim() || null;
    }

    return {
        title: slot.querySelector("#edit-title").value.trim(),
        category: slot.querySelector("#edit-category").value,
        doc_type: docTypeVal,
        department: slot.querySelector("#edit-department").value.trim() || null,
        office_id: parseInt(slot.querySelector("#edit-office-id").value) || null,
        publish_date: slot.querySelector("#edit-publish-date").value || null,
        expiry_date: slot.querySelector("#edit-expiry-date").value || null,
        raw_text: slot.querySelector("#edit-raw-text").value.trim(),
        event_start: slot.querySelector("#edit-event-start")?.value.trim() || null,
        venue: slot.querySelector("#edit-venue")?.value.trim() || null,
        registration_url: regUrl,
        deadlines: deadlines
    };
}

function renderFlagsPanel(flags) {
    if (!flags || flags.length === 0) {
        return `
            <div style="display: flex; align-items: center; gap: 8px; color: var(--success); font-weight: 600; font-size: 13.5px;">
                <span>✓</span><span>No validation conflicts detected. Notice is ready for review.</span>
            </div>
        `;
    }

    const hasBlocking = flags.some(f => f.blocking);

    return `
        <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <h4 style="margin: 0; font-size: 14px;">🚩 AI Quality & Conflict Checks</h4>
            <span class="badge ${hasBlocking ? 'badge-danger' : 'badge-warning'}">
                ${flags.length} ${flags.length === 1 ? 'Check' : 'Checks'}
            </span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 8px;">
            ${flags.map(f => `
                <div style="padding: 10px; border-radius: var(--radius-sm); border-left: 4px solid ${f.blocking ? 'var(--accent)' : '#EAB308'}; background: ${f.blocking ? 'var(--surface-error)' : 'rgba(234, 179, 8, 0.08)'}; font-size: 12.5px;">
                    <div style="font-weight: 700; color: ${f.blocking ? 'var(--accent)' : '#B45309'}; margin-bottom: 2px;">
                        ${f.blocking ? '🛑 BLOCKING FLAG' : '⚠️ WARNING'}
                    </div>
                    <div>${escapeHtml(f.message || '')}</div>
                </div>
            `).join('')}
        </div>
    `;
}

// -------------------------------------------------------------
// STEP 4: CONFIRM & PUBLISH
// -------------------------------------------------------------
function renderStep4Publish(container, slot) {
    if (!currentDraft) {
        currentStep = 1;
        renderWizard(container);
        return;
    }

    const d = currentDraft;
    const blockingFlags = (d.flags || []).filter(f => f.blocking);
    const hasBlocking = blockingFlags.length > 0;

    slot.innerHTML = `
        <div class="card" style="max-width: 720px; margin: 0 auto; padding: 28px;">
            <h3 style="margin-bottom: 4px;">Confirm & Publish Notice</h3>
            <p class="text-muted" style="font-size: 13.5px; margin-bottom: 20px;">Review the finalized details before publishing to students and indexing for AI answers.</p>

            <!-- Summary Card -->
            <div style="background: var(--surface-2); border-radius: var(--radius-sm); padding: 18px; margin-bottom: 24px; border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <div style="font-size: 18px; font-weight: 700; color: var(--text);">${escapeHtml(d.title)}</div>
                        <div class="text-muted" style="font-size: 13px; margin-top: 2px;">
                            ${escapeHtml(d.category)} • ${escapeHtml(d.doc_type)} • Published: ${d.publish_date || 'Today'}
                        </div>
                    </div>
                    <span class="badge badge-accent">Draft</span>
                </div>

                ${d.registration_url ? `
                    <div style="margin-top: 6px; font-size: 13px;">
                        <strong>${d.doc_type === 'Form' ? 'Form Link' : 'Registration URL'}:</strong>
                        <a href="${escapeHtml(d.registration_url)}" target="_blank" rel="noopener" style="color: var(--brand); word-break: break-all; margin-left: 6px;">
                            ${escapeHtml(d.registration_url)}
                        </a>
                    </div>
                ` : ''}

                ${d.deadlines && d.deadlines.length > 0 ? `
                    <div style="margin-top: 14px; border-top: 1px solid var(--border); padding-top: 10px;">
                        <strong style="font-size: 13px;">Extracted Deadlines (${d.deadlines.length}):</strong>
                        <ul style="margin: 6px 0 0 20px; font-size: 12.5px; line-height: 1.6;">
                            ${d.deadlines.map(dl => `
                                <li><strong>${escapeHtml(dl.label)}:</strong> ${dl.date} ${dl.time ? 'at ' + dl.time : ''}</li>
                            `).join('')}
                        </ul>
                    </div>
                ` : '<div class="text-muted" style="font-size: 12.5px; margin-top: 8px;">No explicit deadlines found in this notice.</div>'}
            </div>

            <!-- Blocking Flags Warning Alert -->
            ${hasBlocking ? `
                <div class="card-error" style="padding: 16px; margin-bottom: 24px; border-radius: var(--radius-sm);">
                    <div style="font-weight: 700; margin-bottom: 4px;">🛑 Cannot Publish: Blocking Flags Detected</div>
                    <div style="font-size: 13px; margin-bottom: 12px;">
                        This document contains ${blockingFlags.length} blocking quality flag(s). Please return to Step 3 and fix the conflicting dates or missing data.
                    </div>
                    <button type="button" id="btn-return-step3" class="btn btn-secondary btn-sm">← Return to Review & Fix</button>
                </div>
            ` : `
                <!-- Confirmation Checkbox -->
                <div style="margin-bottom: 24px; padding: 14px; background: rgba(197, 54, 120, 0.05); border: 1px solid var(--brand); border-radius: var(--radius-sm);">
                    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13.5px; font-weight: 600;">
                        <input type="checkbox" id="confirm-publish-checkbox" style="width: 18px; height: 18px; accent-color: var(--brand);">
                        <span>I confirm that these notice details, dates, and instructions are accurate and approved for campus publication.</span>
                    </label>
                </div>
            `}

            <div style="display: flex; justify-content: space-between; align-items: center;">
                <button type="button" id="btn-back-step3" class="btn btn-secondary">← Back to Review</button>
                ${!hasBlocking ? `
                    <button type="button" id="btn-publish-final" class="btn btn-primary" style="padding: 10px 28px;" disabled>
                        📢 Publish Notice Now
                    </button>
                ` : ''}
            </div>
        </div>
    `;

    slot.querySelector("#btn-back-step3").addEventListener("click", () => {
        currentStep = 3;
        renderWizard(container);
    });

    if (hasBlocking) {
        slot.querySelector("#btn-return-step3").addEventListener("click", () => {
            currentStep = 3;
            renderWizard(container);
        });
        return;
    }

    const chk = slot.querySelector("#confirm-publish-checkbox");
    const btnPub = slot.querySelector("#btn-publish-final");

    chk.addEventListener("change", () => {
        btnPub.disabled = !chk.checked;
    });

    btnPub.addEventListener("click", async () => {
        btnPub.disabled = true;
        btnPub.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> Publishing...`;

        try {
            const pubRes = await apiPost(`/admin/documents/${d.id}/publish`, { confirmed: true });

            // Render Success Splash
            slot.innerHTML = `
                <div class="card" style="max-width: 600px; margin: 0 auto; padding: 36px 28px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 12px;">🎉</div>
                    <h2 style="margin-bottom: 8px;">Notice Published Successfully!</h2>
                    <p class="text-muted" style="margin-bottom: 24px;">The notice is now live on the Student Portal and indexed for instant AI answers.</p>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 28px; text-align: left;">
                        <div style="padding: 14px; background: var(--surface-2); border-radius: var(--radius-sm); border: 1px solid var(--border);">
                            <div class="text-muted" style="font-size: 11.5px; font-weight: 700;">SEARCH INDEX</div>
                            <div style="font-size: 20px; font-weight: 800; color: var(--brand); margin-top: 2px;">
                                ${pubRes.chunk_count || 1} Chunks
                            </div>
                            <div class="text-muted" style="font-size: 11px;">FTS5 BM25 indexed</div>
                        </div>

                        <div style="padding: 14px; background: var(--surface-2); border-radius: var(--radius-sm); border: 1px solid var(--border);">
                            <div class="text-muted" style="font-size: 11.5px; font-weight: 700;">ACTIVE REMINDERS</div>
                            <div style="font-size: 20px; font-weight: 800; color: var(--success); margin-top: 2px;">
                                ${pubRes.scheduled_reminders || 0} Scheduled
                            </div>
                            <div class="text-muted" style="font-size: 11px;">2-day & 1-day alerts</div>
                        </div>
                    </div>

                    <div style="display: flex; justify-content: center; gap: 14px;">
                        <button type="button" id="btn-view-notices" class="btn btn-primary">Go to Notices Manager →</button>
                        <button type="button" id="btn-upload-more" class="btn btn-secondary">Upload Another Notice</button>
                    </div>
                </div>
            `;

            slot.querySelector("#btn-view-notices").addEventListener("click", () => {
                window.location.hash = "#/notices";
            });

            slot.querySelector("#btn-upload-more").addEventListener("click", () => {
                currentStep = 1;
                currentDraft = null;
                renderWizard(container);
            });

        } catch (err) {
            showToast(err.message || "Failed to publish notice.", "error");
            btnPub.disabled = false;
            btnPub.textContent = "📢 Publish Notice Now";
        }
    });
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
