/**
 * CampusFlow AI - API Client Wrapper
 * Handles JSON serialization, credential passing, error parsing,
 * and automatic redirection to /login on 401 Unauthorized responses.
 */

export async function apiFetch(endpoint, options = {}) {
    const url = endpoint.startsWith("/api") ? endpoint : `/api${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    
    const headers = options.headers || {};
    
    // Auto-set Content-Type for JSON payloads if not a FormData upload
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
        if (typeof options.body !== "string") {
            options.body = JSON.stringify(options.body);
        }
    }

    const config = {
        credentials: "include",
        ...options,
        headers,
    };

    try {
        const response = await fetch(url, config);

        // Handle Session Expiration / Unauthorized
        if (response.status === 401) {
            const currentPath = window.location.pathname;
            if (!currentPath.includes("login")) {
                const targetRole = currentPath.includes("admin") ? "admin" : "student";
                window.location.href = `/login?role=${targetRole}`;
            }
            throw new Error("Session expired. Please log in again.");
        }

        // Parse JSON payload or handle empty content
        const contentType = response.headers.get("content-type") || "";
        let data = {};
        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            const text = await response.text();
            data = { text };
        }

        if (!response.ok) {
            const errorMsg = data.detail || data.message || `Request failed with HTTP ${response.status}`;
            throw new Error(errorMsg);
        }

        return data;
    } catch (err) {
        console.error(`API Error [${endpoint}]:`, err.message);
        throw err;
    }
}

export function apiGet(endpoint) {
    return apiFetch(endpoint, { method: "GET" });
}

export function apiPost(endpoint, data) {
    return apiFetch(endpoint, { method: "POST", body: data });
}

export function apiPut(endpoint, data) {
    return apiFetch(endpoint, { method: "PUT", body: data });
}

export function apiPatch(endpoint, data) {
    return apiFetch(endpoint, { method: "PATCH", body: data });
}

export function apiDelete(endpoint) {
    return apiFetch(endpoint, { method: "DELETE" });
}
