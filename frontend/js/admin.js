let adminActiveElectionId = null;
let adminSelectedResultsElectionId = "";

document.addEventListener("DOMContentLoaded", () => {
    bindTabs();
    bindForms();
    document.getElementById("admin-results-election")?.addEventListener("change", (event) => {
        adminSelectedResultsElectionId = event.target.value;
        refreshResultsOnly();
    });
    activateTabFromHash();
    refreshAdminData();
    window.setInterval(refreshResultsOnly, 5000);
});

window.addEventListener("hashchange", activateTabFromHash);

function bindTabs() {
    document.querySelectorAll(".tab-button").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
            document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            document.getElementById(button.dataset.target).classList.add("active");
        });
    });
}

function activateTabFromHash() {
    const target = window.location.hash === "#results"
        ? "results-panel"
        : window.location.hash === "#audit-logs"
            ? "logs-panel"
            : window.location.hash === "#voters"
                ? "users-panel"
                : "manage-panel";
    const button = document.querySelector(`.tab-button[data-target="${target}"]`);
    if (button) button.click();
}

function bindForms() {
    document.getElementById("create-election-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = event.target.querySelector("button[type='submit']");
        setLoading(button, true, "Creating...");
        const form = new FormData(event.target);
        try {
            await API.post("/admin/create-election", {
                title: form.get("title"),
                start_date: form.get("start_date"),
                end_date: form.get("end_date"),
            });
            event.target.reset();
            showMessage("admin-message", "Election created.", "success");
            refreshAdminData();
        } catch (error) {
            showMessage("admin-message", error.message, "error");
        } finally {
            setLoading(button, false);
        }
    });

    document.getElementById("add-candidate-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = event.target.querySelector("button[type='submit']");
        setLoading(button, true, "Adding...");
        const form = new FormData(event.target);
        try {
            await API.post("/admin/add-candidate", {
                election_id: form.get("election_id"),
                name: form.get("name"),
                position: form.get("position"),
            });
            event.target.reset();
            showMessage("admin-message", "Candidate added.", "success");
            refreshAdminData();
        } catch (error) {
            showMessage("admin-message", error.message, "error");
        } finally {
            setLoading(button, false);
        }
    });
}

async function refreshAdminData() {
    try {
        const [elections, logs, users] = await Promise.all([
            API.get("/admin/elections"),
            API.get("/admin/audit-logs"),
            API.get("/admin/users"),
        ]);
        const activeElection = elections.data.elections.find((election) => election.is_active);
        adminActiveElectionId = activeElection?.id || null;
        renderAdminResultsPicker(elections.data.elections);
        const resultElectionId = adminSelectedResultsElectionId || adminActiveElectionId;
        const electionQuery = resultElectionId ? `?election_id=${resultElectionId}` : "";
        const [results, integrity] = await Promise.all([
            API.get(`/admin/results${electionQuery}`),
            API.get(`/admin/integrity${electionQuery}`),
        ]);
        renderStats(document.getElementById("admin-stats"), results.data.stats);
        renderSetupState(elections.data.elections);
        renderElections(elections.data.elections);
        renderElectionSelects(elections.data.elections);
        renderResults(results.data.results);
        renderIntegrity(integrity.data.integrity);
        renderAdminBreakdown(results.data.results, results.data.stats);
        renderLogs(logs.data.audit_logs);
        renderUsers(users.data.users);
    } catch (error) {
        showMessage("admin-message", error.message, "error");
    }
}

function renderSetupState(elections) {
    const forms = document.getElementById("setup-forms");
    const notice = document.getElementById("setup-lock-notice");
    if (!forms || !notice) return;

    const activeElection = elections.find((election) => election.is_active);
    if (!activeElection) {
        forms.hidden = false;
        forms.style.display = "";
        notice.innerHTML = "";
        return;
    }

    forms.hidden = true;
    forms.style.display = "none";
    notice.innerHTML = `
        <section class="setup-lock-card">
            <div>
                <span class="eyebrow">Setup Locked</span>
                <h2>Election is open</h2>
                <p>${activeElection.title} is currently open. Candidate and election setup are locked until this election is closed.</p>
            </div>
            <span class="status-pill success">Voting in progress</span>
        </section>
    `;
}

async function refreshResultsOnly() {
    try {
        const elections = await API.get("/admin/elections");
        const activeElection = elections.data.elections.find((election) => election.is_active);
        adminActiveElectionId = activeElection?.id || null;
        renderAdminResultsPicker(elections.data.elections);
        const resultElectionId = adminSelectedResultsElectionId || adminActiveElectionId;
        const electionQuery = resultElectionId ? `?election_id=${resultElectionId}` : "";
        const [results, integrity] = await Promise.all([
            API.get(`/admin/results${electionQuery}`),
            API.get(`/admin/integrity${electionQuery}`),
        ]);
        renderStats(document.getElementById("admin-stats"), results.data.stats);
        renderSetupState(elections.data.elections);
        renderElections(elections.data.elections);
        renderElectionSelects(elections.data.elections);
        renderResults(results.data.results);
        renderIntegrity(integrity.data.integrity);
        renderAdminBreakdown(results.data.results, results.data.stats);
    } catch (_) {
        // The main refresh path shows errors; polling should stay quiet.
    }
}

function renderAdminResultsPicker(elections) {
    const select = document.getElementById("admin-results-election");
    if (!select) return;
    const closedElections = elections.filter((election) => !election.is_active);
    const selectedStillExists = closedElections.some((election) => String(election.id) === String(adminSelectedResultsElectionId));
    if (adminSelectedResultsElectionId && !selectedStillExists) {
        adminSelectedResultsElectionId = "";
    }
    select.innerHTML = `
        <option value="">${adminActiveElectionId ? "Showing current open election" : "Select closed election results"}</option>
        ${closedElections
            .map((election) => `<option value="${election.id}" ${String(adminSelectedResultsElectionId) === String(election.id) ? "selected" : ""}>${election.title}</option>`)
            .join("")}
    `;
}

function renderIntegrity(integrity) {
    const target = document.getElementById("integrity-status");
    if (!target || !integrity) return;
    const audit = integrity.audit_chain;
    const voteStorage = integrity.vote_storage || { protected: true };
    target.innerHTML = `
        <article class="integrity-card ${integrity.tamper_evident ? "ok" : "bad"}">
            <span>Election Integrity</span>
            <strong>${integrity.tamper_evident ? "No Tampering Detected" : "Review Required"}</strong>
            <p>${integrity.status || "Integrity checks completed."}</p>
        </article>
        <article class="integrity-card ${audit.valid ? "ok" : "bad"}">
            <span>Audit Trail</span>
            <strong>${audit.valid ? "Valid" : "Broken"}</strong>
            <p>${audit.message} ${audit.checked_logs} log entries checked.</p>
        </article>
        <article class="integrity-card ${voteStorage.protected ? "ok" : "bad"}">
            <span>Vote Storage</span>
            <strong>${voteStorage.protected ? "Protected" : "Review Needed"}</strong>
            <p>${voteStorage.message || "Votes are encrypted and append-only."}</p>
        </article>
    `;
}

function renderStats(target, stats) {
    target.innerHTML = `
        <article class="stat-card stat-voters"><span>Total Registered Voters</span><strong>${stats.total_registered_voters}</strong></article>
        <article class="stat-card stat-votes"><span>Votes Cast</span><strong>${stats.votes_cast}</strong></article>
        <article class="stat-card stat-turnout"><span>Turnout</span><strong>${stats.turnout_percentage}%</strong></article>
        <article class="stat-card stat-candidates"><span>Candidates</span><strong>${stats.number_of_candidates}</strong></article>
    `;
}

function renderElectionSelects(elections) {
    const selects = document.querySelectorAll(".election-select");
    const closedElections = elections.filter((election) => !election.is_active);
    selects.forEach((select) => {
        select.innerHTML = closedElections
            .map((election) => `<option value="${election.id}">${election.title}</option>`)
            .join("");
    });
}

function renderElections(elections) {
    const target = document.getElementById("elections-table");
    const hasActiveElection = elections.some((election) => election.is_active);
    target.innerHTML = elections
        .map(
            (election) => `
        <article class="glass-card p-5 transition-all duration-200 hover:-translate-y-1">
            <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <span class="eyebrow">Election</span>
                    <h3 class="text-xl font-black">${election.title}</h3>
                    <p class="mt-1 text-sm">${election.start_date} to ${election.end_date}</p>
                </div>
                ${election.is_active ? '<span class="status-pill success">Open</span>' : '<span class="status-pill">Closed</span>'}
            </div>
            <div class="mt-4 rounded-2xl bg-white/5 p-3 text-sm text-emerald-100/70">
                <strong class="text-emerald-50">Candidates:</strong>
                ${election.candidates.map((candidate) => `${candidate.name} (${candidate.position})`).join(", ") || "None"}
            </div>
            <div class="button-row">
                ${!hasActiveElection && !election.is_active ? `<button onclick="setElection(${election.id}, 'open')">Open</button>` : ""}
                ${election.is_active ? `<button class="secondary" onclick="setElection(${election.id}, 'close')">Close</button>` : ""}
                ${hasActiveElection && !election.is_active ? '<span class="status-pill">Open locked</span>' : ""}
            </div>
        </article>
    `
        )
        .join("");
}

function exportReport() {
    const resultElectionId = adminSelectedResultsElectionId || adminActiveElectionId;
    window.location.href = resultElectionId
        ? `/admin/export-report?election_id=${resultElectionId}`
        : "/admin/export-report";
}

async function setElection(electionId, action) {
    const path = action === "open" ? "/admin/open-election" : "/admin/close-election";
    try {
        const result = await API.post(path, { election_id: electionId });
        showMessage("admin-message", `Election ${action === "close" ? "closed" : "opened"}.`, "success");
        if (action === "close" && result.data?.merkle_root) {
            window.location.hash = "#results";
        }
        await refreshAdminData();
    } catch (error) {
        showMessage("admin-message", error.message, "error");
    }
}

function renderResults(results) {
    const target = document.getElementById("results-table");
    const grouped = results.reduce((groups, row) => {
        const key = row.position;
        groups[key] = groups[key] || [];
        groups[key].push(row);
        return groups;
    }, {});

    const priority = (position) => {
        const value = String(position || "").toLowerCase();
        if (value.includes("president")) return 0;
        if (value.includes("finance") || value.includes("treasurer")) return 1;
        if (value.includes("academic")) return 2;
        return 10;
    };
    const themeFor = (position) => {
        const value = String(position || "").toLowerCase();
        if (value.includes("president")) return "category-president";
        if (value.includes("finance") || value.includes("treasurer")) return "category-finance";
        if (value.includes("academic")) return "category-academics";
        return "category-default";
    };

    target.innerHTML = Object.entries(grouped)
        .sort(([left], [right]) => priority(left) - priority(right) || left.localeCompare(right))
        .map(
            ([label, rows]) => `
            <section class="result-group compact-result ${themeFor(label)}">
                <div class="compact-result-head">
                    <div>
                        <h3>${label}</h3>
                        <p>Total votes: ${rows[0]?.total_votes || 0}</p>
                    </div>
                    <span class="status-pill">${rows.length} candidates</span>
                </div>
                ${rows
                    .map(
                        (row) => `
                            <div class="candidate-progress ${row.vote_count === Math.max(...rows.map((item) => item.vote_count)) && row.vote_count > 0 ? "leading" : ""}">
                            <div class="candidate-progress-meta">
                                <strong>${row.candidate_name}</strong>
                                ${row.vote_count === Math.max(...rows.map((item) => item.vote_count)) && row.vote_count > 0 ? '<span class="leader-badge">Leading</span>' : '<span class="leader-badge ghost">Contender</span>'}
                                <span>${row.vote_count} votes</span>
                                <b>${row.percentage}%</b>
                            </div>
                            <div class="bar-track"><div class="bar-fill" style="width:${row.percentage}%"></div></div>
                        </div>
                    `
                    )
                    .join("")}
            </section>
        `
        )
        .join("");
}

function renderAdminBreakdown(results, stats) {
    const target = document.getElementById("admin-breakdown");
    if (!target) return;
    const grouped = results.reduce((groups, row) => {
        groups[row.position] = groups[row.position] || [];
        groups[row.position].push(row);
        return groups;
    }, {});
    const rows = Object.entries(grouped)
        .sort(([left], [right]) => {
            const priority = (position) => {
                const value = String(position || "").toLowerCase();
                if (value.includes("president")) return 0;
                if (value.includes("finance") || value.includes("treasurer")) return 1;
                if (value.includes("academic")) return 2;
                return 10;
            };
            return priority(left) - priority(right) || left.localeCompare(right);
        })
        .map(([position, items]) => `<div class="breakdown-row"><span>${position}</span><strong>${items[0]?.total_votes || 0} votes</strong></div>`)
        .join("");
    target.innerHTML = `
        <section class="breakdown-card">
            <span class="eyebrow">Category Totals</span>
            <h3>Participation by position</h3>
            <div class="breakdown-list">
                ${rows || '<p>No totals yet.</p>'}
                <div class="breakdown-row"><span>Overall votes cast</span><strong>${stats.votes_cast}</strong></div>
                <div class="breakdown-row"><span>Turnout</span><strong>${stats.turnout_percentage}%</strong></div>
            </div>
        </section>
    `;
}

function renderLogs(logs) {
    const target = document.getElementById("logs-table");
    target.innerHTML = `
        <div class="table-scroll admin-table">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Action</th>
                        <th>User</th>
                        <th>Time</th>
                        <th>Previous Hash</th>
                        <th>Current Hash</th>
                    </tr>
                </thead>
                <tbody>
                    ${logs
                        .map(
                            (log) => `
                            <tr>
                                <td><strong>#${log.id}</strong></td>
                                <td><strong>${log.action}</strong></td>
                                <td>${log.user_id || "System"}</td>
                                <td><time>${log.timestamp}</time></td>
                                <td><code class="hash-inline" title="${log.previous_hash}">${log.previous_hash}</code></td>
                                <td><code class="hash-inline" title="${log.current_hash}">${log.current_hash}</code></td>
                            </tr>
                        `
                        )
                        .join("")}
                </tbody>
            </table>
        </div>
    `;
}

function renderUsers(users) {
    const target = document.getElementById("users-table");
    target.innerHTML = `
        <div class="table-scroll admin-table">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Institution ID</th>
                        <th>Course</th>
                        <th>Status</th>
                        <th>Role</th>
                    </tr>
                </thead>
                <tbody>
                    ${users
                        .map(
                            (user) => `
                            <tr>
                                <td><strong>${user.name}</strong></td>
                                <td>${user.email}</td>
                                <td>${user.institution_id || user.reg_number || "N/A"}</td>
                                <td>${user.course || "N/A"}</td>
                                <td><span class="status-pill ${user.has_voted ? "success" : ""}">${user.has_voted ? "Voted" : "Not voted"}</span></td>
                                <td>
                                    <select id="role-${user.id}" onchange="updateRole(${user.id}, this.value)">
                                        <option value="student" ${user.role === "student" ? "selected" : ""}>Student</option>
                                        <option value="admin" ${user.role === "admin" ? "selected" : ""}>Admin</option>
                                    </select>
                                </td>
                            </tr>
                        `
                        )
                        .join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function updateRole(userId, role) {
    try {
        await API.post("/admin/update-user-role", { user_id: userId, role });
        showMessage("admin-message", "Role updated.", "success");
        refreshAdminData();
    } catch (error) {
        showMessage("admin-message", error.message, "error");
        refreshAdminData();
    }
}
