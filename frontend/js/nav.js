document.addEventListener("DOMContentLoaded", renderNavbar);

async function renderNavbar() {
    const navbar = document.querySelector("[data-navbar]");
    if (!navbar) return;

    let sessionInfo = { authenticated: false, role: null };
    try {
        const result = await API.get("/me");
        sessionInfo = result.data;
    } catch (_) {
        sessionInfo = { authenticated: false, role: null };
    }

    const currentPath = window.location.pathname;
    const links = getNavLinks(sessionInfo);
    navbar.innerHTML = `
        <a class="brand" href="${sessionInfo.role === "admin" ? "/pages/admin.html" : sessionInfo.role === "student" ? "/pages/dashboard.html" : "/"}">
            <span class="brand-mark">S</span>
            <span>SecureVote</span>
        </a>
        <button class="nav-toggle" type="button" aria-label="Toggle navigation">Menu</button>
        <div class="nav-links">
            ${links
                .map((link) =>
                    link.action === "logout"
                        ? '<button class="secondary compact" onclick="logout()">Logout</button>'
                        : `<a class="${currentPath === link.href ? "active" : ""}" href="${link.href}">${link.label}</a>`
                )
                .join("")}
        </div>
    `;

    navbar.querySelector(".nav-toggle").addEventListener("click", () => {
        navbar.querySelector(".nav-links").classList.toggle("open");
    });
}

function getNavLinks(sessionInfo) {
    if (!sessionInfo.authenticated) {
        return [
            { label: "Login", href: "/" },
            { label: "Register", href: "/pages/register.html" },
        ];
    }

    if (sessionInfo.role === "admin") {
        return [
            { label: "Dashboard", href: "/pages/admin.html" },
            { label: "Results", href: "/pages/admin.html#results" },
            { label: "Audit Logs", href: "/pages/admin.html#audit-logs" },
            { label: "Voters", href: "/pages/admin.html#voters" },
            { action: "logout" },
        ];
    }

    return [
        { label: "Dashboard", href: "/pages/dashboard.html" },
        { label: "Vote", href: "/pages/vote.html" },
        { label: "Profile", href: "/pages/profile.html" },
        { label: "Verify Vote", href: "/pages/verify.html" },
        { action: "logout" },
    ];
}
