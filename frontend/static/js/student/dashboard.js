/**
 * CampusFlow AI - Student Dashboard View
 * Renders greeting, due-soon deadlines with countdowns, latest notices,
 * upcoming events, and unverified question status cards.
 */

import { apiGet, apiPost } from "/static/js/api.js";
import { showToast, renderSkeleton } from "/static/js/ui.js";

export async function renderDashboardView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1 id="dashboard-greeting">Welcome back!</h1>
            <p class="text-muted">Stay ahead of deadlines and verified campus announcements.</p>
        </div>

        <!-- Big Quick Ask Box -->
        <div class="card student-card" style="margin-bottom: 28px; padding: 24px;">
            <h3 style="margin-bottom: 8px;">Ask CampusFlow AI</h3>
            <p class="text-muted" style="margin-bottom: 16px; font-size: 14px;">Ask in plain words (English or Hinglish) about fee dates, exams, rules, or events:</p>
            <form id="dashboard-quick-ask" style="display: flex; gap: 10px;">
                <input type="text" id="dashboard-ask-input" class="form-input" placeholder="e.g., ppt submission ki last date kab hai" style="font-size: 15px;" required>
                <button type="submit" class="btn btn-accent" style="white-space: nowrap; padding: 10px 24px;">Ask AI</button>
            </form>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; font-size: 12.5px;">
                <span class="text-muted">Try:</span>
                <button type="button" class="badge badge-category" style="cursor: pointer; border: none;" onclick="document.getElementById('dashboard-ask-input').value='ppt submission ki last date kab hai'">PPT last date</button>
                <button type="button" class="badge badge-category" style="cursor: pointer; border: none;" onclick="document.getElementById('dashboard-ask-input').value='semester fee payment last date'">Fee payment deadline</button>
                <button type="button" class="badge badge-category" style="cursor: pointer; border: none;" onclick="document.getElementById('dashboard-ask-input').value='minimum attendance required'">Attendance rules</button>
                <button type="button" class="badge badge-category" style="cursor: pointer; border: none;" onclick="document.getElementById('dashboard-ask-input').value='hostel curfew time'">Hostel curfew</button>
            </div>
        </div>

        <!-- Main Dashboard Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px;">
            
            <!-- Due Soon Deadlines Section -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3>⚠️ Due Soon</h3>
                    <a href="#/deadlines" style="font-size: 13px; font-weight: 600;">View All →</a>
                </div>
                <div id="dashboard-deadlines" style="display: flex; flex-direction: column; gap: 12px;"></div>
            </div>

            <!-- Latest Notices Section -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3>📢 Latest Notices</h3>
                    <a href="#/notices" style="font-size: 13px; font-weight: 600;">View Hub →</a>
                </div>
                <div id="dashboard-notices" style="display: flex; flex-direction: column; gap: 12px;"></div>
            </div>

        </div>

        <!-- Upcoming Events & Questions Tracker -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px; margin-top: 28px;">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3>🎉 Upcoming Events</h3>
                    <a href="#/events" style="font-size: 13px; font-weight: 600;">View All →</a>
                </div>
                <div id="dashboard-events" style="display: flex; flex-direction: column; gap: 12px;"></div>
            </div>

            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3>❓ My Review Questions</h3>
                    <a href="#/my-questions" style="font-size: 13px; font-weight: 600;">Check Replies →</a>
                </div>
                <div id="dashboard-pending-card" class="card" style="padding: 20px;"></div>
            </div>
        </div>
    `;

    // Hook quick ask submit
    const askForm = container.querySelector("#dashboard-quick-ask");
    askForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const input = container.querySelector("#dashboard-ask-input");
        const query = encodeURIComponent(input.value.trim());
        if (query) {
            window.location.hash = `#/ask?q=${query}`;
        }
    });

    // Populate dynamic data
    loadDashboardData(container);

    return container;
}

async function loadDashboardData(container) {
    const deadlinesList = container.querySelector("#dashboard-deadlines");
    const noticesList = container.querySelector("#dashboard-notices");
    const eventsList = container.querySelector("#dashboard-events");
    const pendingCard = container.querySelector("#dashboard-pending-card");

    deadlinesList.appendChild(renderSkeleton(2, 60));
    noticesList.appendChild(renderSkeleton(2, 60));

    try {
        const data = await apiGet("/student/dashboard");

        container.querySelector("#dashboard-greeting").textContent = data.greeting;

        // 1. Render Deadlines
        deadlinesList.innerHTML = "";
        if (!data.due_soon || data.due_soon.length === 0) {
            deadlinesList.innerHTML = `<div class="card" style="padding: 16px; text-align: center; color: var(--muted); font-size: 13.5px;">No active deadlines due this week.</div>`;
        } else {
            data.due_soon.forEach(dl => {
                const item = document.createElement("div");
                item.className = "card";
                item.style.padding = "14px 18px";
                item.style.display = "flex";
                item.style.alignItems = "center";
                item.style.justifyContent = "space-between";
                item.style.gap = "12px";

                const isDone = Boolean(dl.is_done);
                const dueText = formatDaysRemaining(dl.due_date);

                item.innerHTML = `
                    <div style="flex: 1; min-width: 0;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span style="font-weight: 600; font-size: 14px; text-decoration: ${isDone ? 'line-through' : 'none'}; color: ${isDone ? 'var(--muted)' : 'var(--text)'};">
                                ${dl.label}
                            </span>
                            <span class="badge ${dueText.isUrgent ? 'badge-sample' : 'badge-category'}" style="font-size: 11px;">
                                ${dueText.label}
                            </span>
                        </div>
                        <div class="text-muted" style="font-size: 12.5px;">${dl.doc_title} • Due: ${dl.due_date}</div>
                    </div>
                    <button class="btn btn-sm ${isDone ? 'btn-secondary' : 'btn-accent'}" style="white-space: nowrap;">
                        ${isDone ? 'Done ✓' : 'Mark Done'}
                    </button>
                `;

                const doneBtn = item.querySelector("button");
                doneBtn.addEventListener("click", async () => {
                    doneBtn.disabled = true;
                    try {
                        const res = await apiPost(`/deadlines/${dl.id}/done`);
                        showToast(res.is_done ? "Deadline marked done!" : "Deadline unmarked.", "success");
                        loadDashboardData(container);
                    } catch (e) {
                        showToast(e.message, "error");
                    }
                });

                deadlinesList.appendChild(item);
            });
        }

        // 2. Render Latest Notices
        noticesList.innerHTML = "";
        if (!data.latest_notices || data.latest_notices.length === 0) {
            noticesList.innerHTML = `<div class="card" style="padding: 16px; text-align: center; color: var(--muted); font-size: 13.5px;">No notices published yet.</div>`;
        } else {
            data.latest_notices.slice(0, 4).forEach(n => {
                const item = document.createElement("div");
                item.className = "card";
                item.style.padding = "14px 18px";
                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 4px;">
                        <span style="font-weight: 600; font-size: 14px; color: var(--text);">${n.title}</span>
                        ${n.is_sample ? '<span class="badge badge-sample">Sample Data</span>' : ''}
                        ${n.old ? '<span class="badge badge-old">OLD</span>' : ''}
                    </div>
                    <div class="text-muted" style="font-size: 12.5px; margin-bottom: 6px;">
                        ${n.category} • ${n.department || 'Campus Office'} • ${n.publish_date}
                    </div>
                    <p style="font-size: 13px; color: var(--text-2); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        ${n.summary || n.raw_text}
                    </p>
                `;
                noticesList.appendChild(item);
            });
        }

        // 3. Render Events
        eventsList.innerHTML = "";
        if (!data.upcoming_events || data.upcoming_events.length === 0) {
            eventsList.innerHTML = `<div class="card" style="padding: 16px; text-align: center; color: var(--muted); font-size: 13.5px;">No upcoming events scheduled.</div>`;
        } else {
            data.upcoming_events.forEach(ev => {
                const item = document.createElement("div");
                item.className = "card";
                item.style.padding = "14px 18px";
                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <strong style="font-size: 14px;">${ev.title}</strong>
                        ${ev.is_sample ? '<span class="badge badge-sample">Sample Data</span>' : ''}
                    </div>
                    <div class="text-muted" style="font-size: 12.5px; margin-bottom: 6px;">
                        📍 ${ev.venue || 'Campus'} • 🗓️ ${ev.event_start || ev.publish_date}
                    </div>
                    ${ev.registration_url ? `<a href="${ev.registration_url}" target="_blank" class="btn btn-secondary btn-sm" style="display: inline-block; margin-top: 4px;">Register Now ↗</a>` : ''}
                `;
                eventsList.appendChild(item);
            });
        }

        // 4. Render Pending Questions Card
        const pendingCount = data.pending_questions_count || 0;
        pendingCard.innerHTML = `
            <div style="display: flex; align-items: center; gap: 14px;">
                <div style="font-size: 32px;">${pendingCount > 0 ? '⏳' : '✅'}</div>
                <div>
                    <h4 style="margin-bottom: 2px;">${pendingCount} Question${pendingCount === 1 ? '' : 's'} Pending Review</h4>
                    <p class="text-muted" style="font-size: 13px; margin-bottom: 8px;">
                        ${pendingCount > 0
                            ? 'Questions with no confirmed notice answer were forwarded to the admin office.'
                            : 'All your questions have verified notice answers or admin replies.'}
                    </p>
                    <a href="#/my-questions" class="btn btn-secondary btn-sm">View Status & Replies</a>
                </div>
            </div>
        `;

    } catch (err) {
        showToast("Failed to load dashboard data: " + err.message, "error");
    }
}

function formatDaysRemaining(dueDateStr) {
    if (!dueDateStr) return { label: "Upcoming", isUrgent: false };
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(dueDateStr);
    due.setHours(0, 0, 0, 0);

    const diffDays = Math.round((due - today) / (1000 * 60 * 60 * 24));

    if (diffDays < 0) return { label: "Overdue", isUrgent: true };
    if (diffDays === 0) return { label: "Due Today!", isUrgent: true };
    if (diffDays === 1) return { label: "Due Tomorrow!", isUrgent: true };
    if (diffDays <= 2) return { label: `Due in ${diffDays} days`, isUrgent: true };
    return { label: `Due in ${diffDays} days`, isUrgent: false };
}
