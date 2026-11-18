/**
 * CampusFlow AI - Hash Router
 * Provides instantaneous SPA navigation without full page reload.
 */

export class HashRouter {
    constructor(viewContainerId, defaultRoute = "#/dashboard") {
        this.container = document.getElementById(viewContainerId);
        this.defaultRoute = defaultRoute;
        this.routes = new Map();
        
        window.addEventListener("hashchange", () => this.handleRoute());
    }

    register(routeHash, handler) {
        this.routes.set(routeHash, handler);
        return this;
    }

    navigate(routeHash) {
        window.location.hash = routeHash;
    }

    async handleRoute() {
        let hash = window.location.hash || this.defaultRoute;
        
        // Extract base route (e.g., #/forms/bonafide -> #/forms)
        const parts = hash.split("/");
        const baseRoute = parts.length > 2 ? `#/${parts[1]}` : hash;
        
        const handler = this.routes.get(hash) || this.routes.get(baseRoute);

        // Update active navigation link in sidebar and mobile tabs
        document.querySelectorAll(".nav-link, .mobile-tab-item").forEach(link => {
            const linkHref = link.getAttribute("href");
            if (linkHref === hash || linkHref === baseRoute) {
                link.classList.add("active");
            } else {
                link.classList.remove("active");
            }
        });

        if (this.container) {
            // Smooth 150ms transition
            this.container.style.opacity = "0";
            this.container.style.transform = "translateY(4px)";
            this.container.style.transition = "opacity 0.15s ease, transform 0.15s ease";

            setTimeout(async () => {
                this.container.innerHTML = "";
                if (handler) {
                    try {
                        const content = await handler(parts.slice(2));
                        if (content instanceof HTMLElement) {
                            this.container.appendChild(content);
                        } else if (typeof content === "string") {
                            this.container.innerHTML = content;
                        }
                    } catch (err) {
                        console.error("Route error:", err);
                        this.container.innerHTML = `
                            <div class="card" style="border-top: 4px solid var(--danger);">
                                <h3 style="color: var(--danger);">Error loading view</h3>
                                <p class="text-muted">${err.message}</p>
                            </div>
                        `;
                    }
                } else {
                    this.container.innerHTML = `
                        <div class="card">
                            <h3>Page Not Found</h3>
                            <p class="text-muted">The requested section '${hash}' does not exist.</p>
                            <a href="${this.defaultRoute}" class="btn btn-primary" style="margin-top: 14px;">Return to Dashboard</a>
                        </div>
                    `;
                }
                this.container.style.opacity = "1";
                this.container.style.transform = "translateY(0)";
            }, 100);
        }
    }

    init() {
        if (!window.location.hash) {
            window.location.hash = this.defaultRoute;
        } else {
            this.handleRoute();
        }
    }
}
