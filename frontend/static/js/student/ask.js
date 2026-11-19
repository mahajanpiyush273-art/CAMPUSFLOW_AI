/**
 * CampusFlow AI - Student Ask (Chat) View
 * Interactive grounded chat with animated confidence ring, source drawer,
 * next-step action buttons, not-verified office fallback cards, and feedback.
 */

import { apiGet, apiPost } from "/static/js/api.js";
import { renderConfidenceRing, showModal, showToast } from "/static/js/ui.js";

let currentChatId = null;

export async function renderAskView(args = []) {
    const container = document.createElement("div");
    container.style.display = "grid";
    container.style.gridTemplateColumns = "260px 1fr";
    container.style.gap = "20px";
    container.style.minHeight = "calc(100vh - 140px)";

    container.innerHTML = `
        <!-- Left: Chat History Sessions Sidebar -->
        <div class="card" style="padding: 16px; display: flex; flex-direction: column; gap: 12px; height: calc(100vh - 140px); overflow-y: auto;">
            <button id="new-chat-btn" class="btn btn-accent" style="width: 100%; justify-content: center;">
                + New Chat
            </button>
            <div style="font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase; margin-top: 8px;">Recent Chats</div>
            <div id="chat-sessions-list" style="display: flex; flex-direction: column; gap: 6px; overflow-y: auto; flex: 1;"></div>
        </div>

        <!-- Right: Active Chat Conversation View -->
        <div class="card student-card" style="display: flex; flex-direction: column; height: calc(100vh - 140px); padding: 0; overflow: hidden;">
            <!-- Chat Header -->
            <div style="padding: 14px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--surface-2);">
                <div>
                    <h3 id="active-chat-title" style="font-size: 16px; margin: 0;">Campus Query Assistant</h3>
                    <div style="font-size: 12px; color: var(--muted);">Grounded strictly in approved campus notices</div>
                </div>
                <div class="badge badge-category" style="font-size: 11px;">Ask. Verify. Act.</div>
            </div>

            <!-- Messages Thread -->
            <div id="chat-messages-thread" style="flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 18px;">
                <!-- Initial Welcome & Suggested Chips -->
                <div id="chat-welcome-box" style="text-align: center; margin: auto 0; padding: 20px;">
                    <div style="font-size: 38px; margin-bottom: 12px;">💬</div>
                    <h2 style="font-size: 22px; margin-bottom: 6px;">Ask CampusFlow AI</h2>
                    <p class="text-muted" style="max-width: 520px; margin: 0 auto 20px auto; font-size: 14px;">
                        Ask in English or conversational Hinglish. Every answer cites verified notices with confidence scores.
                    </p>
                    <div style="font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase; margin-bottom: 10px;">Suggested Questions</div>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; max-width: 650px; margin: 0 auto;">
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">when is the ppt submission last date?</button>
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">ppt submission ki last date kab hai</button>
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">last date for fee payment</button>
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">what is the late fine for fees?</button>
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">how can I get a bonafide certificate</button>
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">hostel curfew time</button>
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">mid term exam late admission form kaha hai</button>
                        <button class="badge badge-category sample-chip" style="cursor: pointer; border: none; padding: 6px 12px; font-size: 12.5px;">who is the vice chancellor</button>
                    </div>
                </div>
            </div>

            <!-- Input Box Area -->
            <div style="padding: 16px 20px; border-top: 1px solid var(--border); background: var(--surface);">
                <form id="chat-input-form" style="display: flex; gap: 12px; align-items: flex-end;">
                    <textarea id="chat-input-textarea" class="form-textarea" placeholder="Ask a question about fees, dates, rules, or forms... (Enter to send, Shift+Enter for newline)"
                              style="min-height: 44px; max-height: 120px; resize: none; padding: 10px 14px; font-size: 14px; border-radius: 22px; flex: 1;"></textarea>
                    <button type="submit" id="chat-send-btn" class="btn btn-accent" style="border-radius: 22px; padding: 10px 22px; height: 44px;">
                        Send ➔
                    </button>
                </form>
            </div>
        </div>
    `;

    // Hook events
    setupAskEvents(container);

    // If query was passed via query parameter (e.g. ?q=...), prefill and send
    const urlParams = new URLSearchParams(window.location.hash.split("?")[1] || "");
    const initialQ = urlParams.get("q");
    if (initialQ) {
        setTimeout(() => {
            const textarea = container.querySelector("#chat-input-textarea");
            textarea.value = decodeURIComponent(initialQ);
            container.querySelector("#chat-send-btn").click();
        }, 150);
    }

    return container;
}

async function setupAskEvents(container) {
    const thread = container.querySelector("#chat-messages-thread");
    const textarea = container.querySelector("#chat-input-textarea");
    const sendBtn = container.querySelector("#chat-send-btn");
    const form = container.querySelector("#chat-input-form");
    const newChatBtn = container.querySelector("#new-chat-btn");
    const welcomeBox = container.querySelector("#chat-welcome-box");

    // Load Sessions
    await loadChatSessions(container);

    // New Chat Click
    newChatBtn.addEventListener("click", () => {
        currentChatId = null;
        thread.innerHTML = "";
        thread.appendChild(welcomeBox);
        welcomeBox.style.display = "block";
        container.querySelector("#active-chat-title").textContent = "New Conversation";
        textarea.focus();
    });

    // Suggested Chips Clicks
    container.querySelectorAll(".sample-chip").forEach(btn => {
        btn.addEventListener("click", () => {
            textarea.value = btn.textContent;
            form.dispatchEvent(new Event("submit"));
        });
    });

    // Enter to send, Shift+Enter for newline
    textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event("submit"));
        }
    });

    // Form Submit
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = textarea.value.trim();
        if (!text) return;

        textarea.value = "";
        if (welcomeBox) welcomeBox.style.display = "none";

        // 1. Append Student Bubble
        appendStudentMessage(thread, text);

        // 2. Append Typing Indicator
        const typingEl = appendTypingIndicator(thread);
        sendBtn.disabled = true;

        try {
            const data = await apiPost("/ask", {
                question: text,
                chat_id: currentChatId
            });

            typingEl.remove();

            if (!currentChatId && data.chat_id) {
                currentChatId = data.chat_id;
                loadChatSessions(container);
            }

            // 3. Append Assistant Card
            appendAssistantMessage(thread, data);

        } catch (err) {
            typingEl.remove();
            showToast("Failed to get answer: " + err.message, "error");
        } finally {
            sendBtn.disabled = false;
            textarea.focus();
        }
    });
}

function appendStudentMessage(thread, text) {
    const el = document.createElement("div");
    el.style.alignSelf = "flex-end";
    el.style.maxWidth = "75%";
    el.style.backgroundColor = "var(--brand-tint)";
    el.style.color = "var(--text)";
    el.style.padding = "12px 18px";
    el.style.borderRadius = "16px 16px 4px 16px";
    el.style.fontSize = "14.5px";
    el.style.lineHeight = "1.45";
    el.textContent = text;
    thread.appendChild(el);
    thread.scrollTop = thread.scrollHeight;
}

function appendTypingIndicator(thread) {
    const el = document.createElement("div");
    el.style.alignSelf = "flex-start";
    el.className = "card";
    el.style.padding = "10px 16px";
    el.style.fontSize = "13.5px";
    el.style.color = "var(--muted)";
    el.innerHTML = `<span>CampusFlow AI is searching approved notices...</span>`;
    thread.appendChild(el);
    thread.scrollTop = thread.scrollHeight;
    return el;
}

function appendAssistantMessage(thread, data) {
    const card = document.createElement("div");
    card.style.alignSelf = "flex-start";
    card.style.maxWidth = "85%";
    card.className = data.status === "not_verified" ? "card" : "card";
    card.style.padding = "20px";
    card.style.boxShadow = "var(--shadow)";

    if (data.status === "not_verified") {
        card.style.borderLeft = "4px solid var(--accent)";
        card.style.backgroundColor = "var(--accent-tint)";

        const office = data.office;
        card.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; color: var(--accent); font-weight: 700; font-size: 13.5px;">
                <span>⚠️ NOT VERIFIED</span>
                <span class="badge" style="background: rgba(255,88,65,0.15); color: var(--accent-dark);">Confidence: ${data.confidence}%</span>
            </div>
            <p style="font-size: 14.5px; color: var(--text); margin-bottom: 14px; line-height: 1.5;">${data.answer}</p>

            ${office ? `
                <div style="background: #FFFFFF; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 12px;">
                    <div style="font-weight: 700; font-size: 13.5px; margin-bottom: 4px;">🏢 Designated Office Contact: ${office.name}</div>
                    <div style="font-size: 12.5px; color: var(--text-2); margin-bottom: 2px;">📍 Location: ${office.location}</div>
                    <div style="font-size: 12.5px; color: var(--text-2); margin-bottom: 2px;">📞 Phone: <a href="tel:${office.phone}">${office.phone}</a></div>
                    <div style="font-size: 12.5px; color: var(--text-2); margin-bottom: 2px;">✉️ Email: <a href="mailto:${office.email}">${office.email}</a></div>
                    <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">🕒 Hours: ${office.hours}</div>
                </div>
            ` : ''}

            <div style="font-size: 12.5px; color: var(--muted);">
                📋 Your question has joined the admin review queue. You will see verified updates under <strong><a href="#/my-questions">My Questions</a></strong>.
            </div>
        `;
    } else {
        // Verified or greeting
        card.style.borderLeft = "4px solid var(--success)";
        card.style.backgroundColor = "#FFFFFF";

        card.innerHTML = `
            <!-- Top Verified Notice Header -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                <span class="badge badge-new" style="font-size: 12.5px; font-weight: 700; padding: 4px 10px;">✓ Verified by Official Notice</span>
                ${data.mode === 'offline' ? '<span class="badge badge-sample">AI Offline: Exact Notice Excerpt</span>' : ''}
            </div>

            <!-- Answer Content with Word-by-Word Reveal -->
            <div id="answer-text-body" style="font-size: 15px; color: var(--text); line-height: 1.6; margin-bottom: 16px;"></div>

            <!-- Source Notice Card -->
            ${data.source ? `
                <div style="background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px 16px; margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-weight: 700; font-size: 13.5px; color: var(--brand);">Source: ${data.source.title}</span>
                        ${data.source.old ? '<span class="badge badge-old">EXPIRED / OLD</span>' : '<span class="badge badge-new">Verified Notice</span>'}
                    </div>
                    <div style="font-size: 12px; color: var(--muted); margin-bottom: 8px;">
                        ${data.source.department} • Published: ${data.source.publish_date}
                    </div>
                    ${data.source.highlight ? `
                        <div style="font-size: 13px; font-style: italic; background: #FFFBEB; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #F59E0B; margin-bottom: 8px;">
                            "${data.source.highlight}"
                        </div>
                    ` : ''}
                    <button class="btn btn-secondary btn-sm view-source-btn" style="padding: 4px 10px; font-size: 12px;">View Full Notice Document</button>
                </div>
            ` : ''}

            <!-- Actionable Next Steps -->
            ${data.next_steps && data.next_steps.length > 0 ? `
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
                    ${data.next_steps.map(step => {
                        if (step.type === 'form') {
                            return `<a href="${step.url}" class="btn btn-accent btn-sm">📝 ${step.label}</a>`;
                        } else if (step.type === 'event_register') {
                            return `<a href="${step.url}" target="_blank" class="btn btn-primary btn-sm">🎟️ ${step.label} ↗</a>`;
                        } else {
                            return '';
                        }
                    }).join('')}
                </div>
            ` : ''}

            <!-- Was this helpful Thumbs up/down -->
            <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 10px; font-size: 12px; color: var(--muted);">
                <span>Was this verified answer helpful?</span>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-secondary btn-sm thumb-up-btn" style="padding: 2px 8px;">👍 Yes</button>
                    <button class="btn btn-secondary btn-sm thumb-down-btn" style="padding: 2px 8px;">👎 No</button>
                </div>
            </div>
        `;

        // Word-by-word reveal
        const answerBody = card.querySelector("#answer-text-body");
        revealTextWordByWord(answerBody, data.answer);

        // View full notice modal
        const viewSourceBtn = card.querySelector(".view-source-btn");
        if (viewSourceBtn && data.source) {
            viewSourceBtn.addEventListener("click", () => {
                showModal({
                    title: data.source.title,
                    content: `<pre style="white-space: pre-wrap; font-family: inherit; line-height: 1.6; font-size: 14px;">${data.source.full_text}</pre>`,
                    confirmText: "Close",
                    cancelText: "Done",
                });
            });
        }

        // Feedback buttons
        const qId = data.question_id;
        const upBtn = card.querySelector(".thumb-up-btn");
        const downBtn = card.querySelector(".thumb-down-btn");
        if (upBtn && qId) {
            upBtn.addEventListener("click", async () => {
                await apiPost(`/questions/${qId}/feedback`, { helpful: 1 });
                upBtn.style.background = "var(--success-bg)";
                upBtn.textContent = "👍 Thank you!";
                downBtn.style.display = "none";
            });
        }
        if (downBtn && qId) {
            downBtn.addEventListener("click", async () => {
                await apiPost(`/questions/${qId}/feedback`, { helpful: -1 });
                downBtn.textContent = "👎 Feedback noted";
                upBtn.style.display = "none";
            });
        }
    }

    thread.appendChild(card);
    thread.scrollTop = thread.scrollHeight;
}

function revealTextWordByWord(element, fullText, speed = 25) {
    if (!element) return;
    const words = fullText.split(" ");
    let idx = 0;
    element.textContent = "";

    const timer = setInterval(() => {
        if (idx < words.length) {
            element.textContent += (idx === 0 ? "" : " ") + words[idx];
            idx++;
        } else {
            clearInterval(timer);
        }
    }, speed);
}

async function loadChatSessions(container) {
    const listEl = container.querySelector("#chat-sessions-list");
    if (!listEl) return;

    try {
        const data = await apiGet("/chats");
        if (!data.chats || data.chats.length === 0) {
            listEl.innerHTML = `<div style="color: var(--muted); font-size: 12px; text-align: center; padding: 12px;">No past conversations.</div>`;
            return;
        }

        listEl.innerHTML = data.chats.map(c => `
            <div class="chat-session-item" data-id="${c.id}" style="padding: 8px 12px; border-radius: var(--radius-sm); cursor: pointer; font-size: 13px; color: var(--text-2); transition: var(--transition); background: ${c.id === currentChatId ? 'var(--brand-tint)' : 'transparent'};">
                <div style="font-weight: 600; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${c.title}</div>
                <div style="font-size: 11px; color: var(--muted);">${c.question_count} question${c.question_count === 1 ? '' : 's'}</div>
            </div>
        `).join("");

        listEl.querySelectorAll(".chat-session-item").forEach(item => {
            item.addEventListener("click", () => {
                const id = parseInt(item.getAttribute("data-id"));
                loadChatThread(container, id);
            });
        });
    } catch (e) {
        // Ignore silent session list errors
    }
}

async function loadChatThread(container, chatId) {
    currentChatId = chatId;
    const thread = container.querySelector("#chat-messages-thread");
    const welcomeBox = container.querySelector("#chat-welcome-box");
    if (welcomeBox) welcomeBox.style.display = "none";
    thread.innerHTML = `<div class="card" style="padding: 14px; text-align: center; color: var(--muted);">Loading conversation...</div>`;

    try {
        const data = await apiGet(`/chats/${chatId}`);
        container.querySelector("#active-chat-title").textContent = data.chat.title;
        thread.innerHTML = "";

        data.turns.forEach(turn => {
            appendStudentMessage(thread, turn.question);
            appendAssistantMessage(thread, {
                question_id: turn.id,
                status: turn.status,
                answer: turn.answer,
                confidence: turn.confidence,
                level: turn.level,
                source: turn.source,
                mode: "ai",
                next_steps: [],
            });
        });

        loadChatSessions(container);
    } catch (err) {
        showToast(err.message, "error");
    }
}
