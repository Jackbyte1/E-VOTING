const API = {
    async request(path, options = {}) {
        const response = await fetch(path, {
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {}),
            },
            ...options,
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            throw new Error(payload.message || "Request failed");
        }
        return payload;
    },

    get(path) {
        return this.request(path);
    },

    post(path, body) {
        return this.request(path, {
            method: "POST",
            body: JSON.stringify(body || {}),
        });
    },
};

function showMessage(elementId, text, type = "success") {
    const element = document.getElementById(elementId);
    if (!element) return;
    element.className = `message show ${type}`;
    element.textContent = text;
}

function clearMessage(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    element.className = "message";
    element.textContent = "";
}

function setLoading(button, isLoading, label = "Processing...") {
    if (!button) return;
    if (isLoading) {
        button.dataset.originalText = button.textContent;
        button.textContent = label;
        button.disabled = true;
    } else {
        button.textContent = button.dataset.originalText || button.textContent;
        button.disabled = false;
    }
}

async function logout() {
    try {
        await API.post("/logout");
    } finally {
        window.location.href = "/";
    }
}
