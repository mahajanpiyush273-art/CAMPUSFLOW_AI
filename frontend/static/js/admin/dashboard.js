/**
 * CampusFlow AI - Admin Insights Dashboard
 * Renders KPI cards with count-up animations, custom hand-written SVG charts
 * for daily question volume and category distribution, top repeated questions, and feedback.
 */

import { apiGet } from "/static/js/api.js";
import { animateCountUp, showToast, renderSkeleton } from "/static/js/ui.js";

export async function renderAdminDashboardView() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div style="margin-bottom: 24px;">
            <h1>📊 Administrative Insights Dashboard</h1>
            <p class="text-muted">Live metrics on campus queries, verification confidence rates, unanswered topics, and deadline compliance.</p>
        </div>

        <!-- KPI Summary Cards Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px;">
            <div class="card admin-card" style="padding: 18px;">
                <div class="text-muted" style="font-size: 12px; font-weight: 700; text-transform: uppercase;">Total Questions</div>
                <div id="kpi-total-q" style="font-size: 32px; font-weight: 800; color: var(--text); margin-top: 4px;">0</div>
                <div class="text-muted" style="font-size: 11.5px; margin-top: 2px;">Campus student inquiries</div>
            </div>

            <div class="card" style="padding: 18px; border-top: 4px solid var(--success);">
                <div class="text-muted" style="font-size: 12px; font-weight: 700; text-transform: uppercase;">Verified Rate</div>
                <div id="kpi-verified-rate" style="font-size: 32px; font-weight: 800; color: var(--success); margin-top: 4px;">0%</div>
                <div class="text-muted" style="font-size: 11.5px; margin-top: 2px;">Answered from notice</div>
            </div>

            <div class="card" style="padding: 18px; border-top: 4px solid var(--accent);">
                <div class="text-muted" style="font-size: 12px; font-weight: 700; text-transform: uppercase;">Pending Review</div>
                <div id="kpi-pending-q" style="font-size: 32px; font-weight: 800; color: var(--accent); margin-top: 4px;">0</div>
                <div class="text-muted" style="font-size: 11.5px; margin-top: 2px;">Awaiting official reply</div>
            </div>

            <div class="card" style="padding: 18px; border-top: 4px solid #3B82F6;">
                <div class="text-muted" style="font-size: 12px; font-weight: 700; text-transform: uppercase;">Deadlines Completed</div>
                <div id="kpi-deadlines-done" style="font-size: 32px; font-weight: 800; color: #2563EB; margin-top: 4px;">0</div>
                <div class="text-muted" style="font-size: 11.5px; margin-top: 2px;">Student compliance actions</div>
            </div>
        </div>

        <!-- Charts Section (Custom SVG) -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; margin-bottom: 32px;">
            <!-- Questions Volume (7 Days) -->
            <div class="card" style="padding: 24px;">
                <h3 style="margin-bottom: 6px;">Questions Volume (Last 7 Days)</h3>
                <p class="text-muted" style="font-size: 13px; margin-bottom: 20px;">Student activity trend over the past week.</p>
                <div id="chart-daily-slot" style="min-height: 200px; display: flex; align-items: center; justify-content: center;"></div>
            </div>

            <!-- Category Topics Breakdown -->
            <div class="card" style="padding: 24px;">
                <h3 style="margin-bottom: 6px;">Topics Where Students Ask Most</h3>
                <p class="text-muted" style="font-size: 13px; margin-bottom: 20px;">Distribution of student questions by category.</p>
                <div id="chart-categories-slot" style="min-height: 200px;"></div>
            </div>
        </div>

        <!-- Repeated Questions & Review Queue Shortcut -->
        <div class="card" style="padding: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <div>
                    <h3 style="margin-bottom: 2px;">Most Repeated Inquiries</h3>
                    <p class="text-muted" style="font-size: 13px;">Grouped by keywords. Publishing a verified reply answers all students at once.</p>
                </div>
                <a href="#/review-queue" class="btn btn-primary btn-sm">Open Review Queue →</a>
            </div>

            <div id="repeated-questions-slot"></div>
        </div>
    `;

    loadAdminInsights(container);
    return container;
}

async function loadAdminInsights(container) {
    try {
        const stats = await apiGet("/admin/stats");

        // 1. Animate KPIs
        animateCountUp(container.querySelector("#kpi-total-q"), stats.total_questions || 0);
        animateCountUp(container.querySelector("#kpi-verified-rate"), stats.answered_pct || 0);
        container.querySelector("#kpi-verified-rate").textContent = `${stats.answered_pct || 0}%`;
        animateCountUp(container.querySelector("#kpi-pending-q"), stats.pending_review_count || 0);
        animateCountUp(container.querySelector("#kpi-deadlines-done"), stats.deadlines_marked_done || 0);

        // 2. Render Daily SVG Bar Chart
        renderDailySvgChart(container.querySelector("#chart-daily-slot"), stats.daily_questions || []);

        // 3. Render Categories Distribution Bars
        renderCategoriesBars(container.querySelector("#chart-categories-slot"), stats.categories || []);

        // 4. Render Top Repeated Inquiries Table
        renderRepeatedQuestionsTable(container.querySelector("#repeated-questions-slot"), stats.top_repeated || []);

    } catch (e) {
        showToast("Error loading stats: " + e.message, "error");
    }
}

function renderDailySvgChart(slot, dailyData) {
    if (!dailyData || dailyData.length === 0) {
        slot.innerHTML = `<div style="color: var(--muted); font-size: 13px;">No daily inquiry data yet.</div>`;
        return;
    }

    const width = 420;
    const height = 180;
    const padding = 28;
    const maxVal = Math.max(...dailyData.map(d => d.count), 5);
    const barWidth = 32;
    const spacing = (width - padding * 2) / dailyData.length;

    let barsHtml = "";
    dailyData.forEach((d, idx) => {
        const x = padding + idx * spacing + (spacing - barWidth) / 2;
        const barHeight = Math.round((d.count / maxVal) * (height - padding * 2));
        const y = height - padding - barHeight;
        const dayLabel = d.day.slice(5); // MM-DD

        barsHtml += `
            <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="4"
                  fill="var(--brand)" style="transition: height 0.5s ease;">
                <title>${d.day}: ${d.count} questions</title>
            </rect>
            <text x="${x + barWidth/2}" y="${y - 6}" font-size="11" font-weight="700" fill="var(--text)" text-anchor="middle">${d.count}</text>
            <text x="${x + barWidth/2}" y="${height - 8}" font-size="10.5" fill="var(--muted)" text-anchor="middle">${dayLabel}</text>
        `;
    });

    slot.innerHTML = `
        <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="overflow: visible;">
            <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="var(--border)" stroke-width="1.5" />
            ${barsHtml}
        </svg>
    `;
}

function renderCategoriesBars(slot, categories) {
    if (!categories || categories.length === 0) {
        slot.innerHTML = `<div style="color: var(--muted); font-size: 13px;">No category activity recorded yet.</div>`;
        return;
    }

    const maxCount = Math.max(...categories.map(c => c.count), 1);

    slot.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
            ${categories.map(c => {
                const pct = Math.round((c.count / maxCount) * 100);
                return `
                    <div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; margin-bottom: 4px;">
                            <span>${c.topic || 'General'}</span>
                            <span class="text-muted">${c.count} queries</span>
                        </div>
                        <div style="background: var(--surface-2); border: 1px solid var(--border); height: 10px; border-radius: 5px; overflow: hidden;">
                            <div style="background: var(--accent); height: 100%; width: ${pct}%; border-radius: 5px; transition: width 0.6s ease;"></div>
                        </div>
                    </div>
                `;
            }).join("")}
        </div>
    `;
}

function renderRepeatedQuestionsTable(slot, repeated) {
    if (!repeated || repeated.length === 0) {
        slot.innerHTML = `<div style="color: var(--muted); font-size: 13px; text-align: center; padding: 18px;">No repeated queries logged yet.</div>`;
        return;
    }

    slot.innerHTML = `
        <table style="width: 100%; border-collapse: collapse; font-size: 13.5px;">
            <thead style="background: var(--surface-2); border-bottom: 1px solid var(--border); text-align: left;">
                <tr>
                    <th style="padding: 10px 14px;">Question Keywords</th>
                    <th style="padding: 10px 14px;">Sample Inquiry</th>
                    <th style="padding: 10px 14px; text-align: center;">Times Asked</th>
                    <th style="padding: 10px 14px;">Action</th>
                </tr>
            </thead>
            <tbody>
                ${repeated.map(r => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 14px; font-family: monospace; font-size: 12px; color: var(--brand); font-weight: 700;">
                            ${r.group_key}
                        </td>
                        <td style="padding: 12px 14px; color: var(--text);">"${r.sample_question}"</td>
                        <td style="padding: 12px 14px; text-align: center;">
                            <span class="badge badge-sample" style="font-size: 12px;">${r.count}x</span>
                        </td>
                        <td style="padding: 12px 14px;">
                            <a href="#/review-queue" class="btn btn-secondary btn-sm" style="padding: 4px 10px; font-size: 12px;">
                                Review & Reply
                            </a>
                        </td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}
