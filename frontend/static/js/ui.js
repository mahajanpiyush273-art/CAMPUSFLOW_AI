/**
 * CampusFlow AI - UI Utilities & Micro-Interactions
 * Toasts, Modals, Animated Confidence Ring, Count-Up, Skeletons, and States.
 */

// 1. Toast Notification Service
export function showToast(message, type = "info", duration = 4000) {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");

    const icon = type === "success" ? "✓" : (type === "error" ? "⚠" : (type === "accent" ? "⚡" : "ℹ"));
    toast.innerHTML = `
        <span style="font-size: 16px; font-weight: 700;">${icon}</span>
        <span style="flex: 1; line-height: 1.4;">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        toast.style.transition = "all 0.25s ease";
        setTimeout(() => toast.remove(), 250);
    }, duration);
}

// 2. Animated Confidence Ring Generator
export function renderConfidenceRing(score, level, size = 54) {
    const strokeWidth = 4;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    let colorClass = "conf-high";
    if (level === "Medium") colorClass = "conf-medium";
    else if (level === "Low") colorClass = "conf-low";
    else if (level === "Not verified") colorClass = "conf-not-verified";

    const tooltip = `Confidence: ${score}%\nLevel: ${level}\nCalculated from exact notice coverage, BM25 keyword rank, and AI grounded verification.`;

    const wrapper = document.createElement("div");
    wrapper.className = "confidence-wrapper";
    wrapper.title = tooltip;

    wrapper.innerHTML = `
        <div class="confidence-ring-container" style="width: ${size}px; height: ${size}px;">
            <svg class="confidence-ring-svg" width="${size}" height="${size}">
                <circle class="confidence-ring-bg" cx="${size/2}" cy="${size/2}" r="${radius}" />
                <circle class="confidence-ring-progress ${colorClass}"
                        cx="${size/2}" cy="${size/2}" r="${radius}"
                        style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${circumference};" />
            </svg>
            <div class="confidence-number">${score}%</div>
        </div>
        <div>
            <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--muted);">Confidence</div>
            <div style="font-size: 13.5px; font-weight: 700; color: var(--text);">${level}</div>
        </div>
    `;

    // Trigger animation
    setTimeout(() => {
        const circle = wrapper.querySelector(".confidence-ring-progress");
        if (circle) circle.style.strokeDashoffset = offset;
    }, 50);

    return wrapper;
}

// 3. Count-up Number Animation
export function animateCountUp(element, target, duration = 800) {
    if (!element) return;
    const start = 0;
    const startTime = performance.now();

    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOutQuad = progress * (2 - progress);
        const current = Math.floor(start + (target - start) * easeOutQuad);
        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = target;
        }
    }
    requestAnimationFrame(update);
}

// 4. Modal Dialog Service
export function showModal({ title, content, confirmText = "Confirm", cancelText = "Cancel", onConfirm }) {
    let overlay = document.getElementById("app-modal-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "app-modal-overlay";
        overlay.className = "modal-overlay";
        overlay.innerHTML = `
            <div class="modal-box">
                <h3 id="modal-title" style="margin-bottom: 12px;"></h3>
                <div id="modal-content" style="color: var(--text-2); font-size: 14.5px; margin-bottom: 24px; line-height: 1.5;"></div>
                <div style="display: flex; justify-content: flex-end; gap: 12px;">
                    <button id="modal-cancel-btn" class="btn btn-secondary"></button>
                    <button id="modal-confirm-btn" class="btn btn-primary"></button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    const titleEl = document.getElementById("modal-title");
    const contentEl = document.getElementById("modal-content");
    const confirmBtn = document.getElementById("modal-confirm-btn");
    const cancelBtn = document.getElementById("modal-cancel-btn");

    titleEl.textContent = title;
    if (typeof content === "string") {
        contentEl.innerHTML = content;
    } else {
        contentEl.innerHTML = "";
        contentEl.appendChild(content);
    }

    confirmBtn.textContent = confirmText;
    cancelBtn.textContent = cancelText;

    overlay.classList.add("open");

    const close = () => {
        overlay.classList.remove("open");
        cleanup();
    };

    const handleConfirm = async () => {
        if (onConfirm) {
            await onConfirm();
        }
        close();
    };

    const cleanup = () => {
        confirmBtn.removeEventListener("click", handleConfirm);
        cancelBtn.removeEventListener("click", close);
    };

    confirmBtn.addEventListener("click", handleConfirm);
    cancelBtn.addEventListener("click", close);
}

// Global modal close function
export function hideModal() {
    const overlay = document.getElementById("app-modal-overlay");
    if (overlay) {
        overlay.classList.remove("open");
    }
}
window.CF_HIDE_MODAL = hideModal;

// Close modals on Escape key
window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        hideModal();
    }
});

// 5. Skeleton Loaders
export function renderSkeleton(lines = 3, height = 24) {
    const wrapper = document.createElement("div");
    wrapper.style.display = "flex";
    wrapper.style.flexDirection = "column";
    wrapper.style.gap = "12px";
    wrapper.style.width = "100%";

    for (let i = 0; i < lines; i++) {
        const skel = document.createElement("div");
        skel.className = "skeleton";
        skel.style.height = `${height}px`;
        skel.style.width = i === lines - 1 ? "60%" : "100%";
        wrapper.appendChild(skel);
    }
    return wrapper;
}

// 6. Empty State Component
export function renderEmptyState(title, message, actionBtn = null) {
    const card = document.createElement("div");
    card.className = "card";
    card.style.textAlign = "center";
    card.style.padding = "40px 24px";

    card.innerHTML = `
        <div style="font-size: 36px; margin-bottom: 12px;">📋</div>
        <h3 style="margin-bottom: 8px;">${title}</h3>
        <p class="text-muted" style="max-width: 440px; margin: 0 auto 16px auto;">${message}</p>
    `;

    if (actionBtn) {
        card.appendChild(actionBtn);
    }
    return card;
}
