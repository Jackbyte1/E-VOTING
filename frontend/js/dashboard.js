let dashboardElection = null;
let dashboardTimer = null;
let selectedClosedElectionId = "";

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("closed-results-picker")?.addEventListener("change", (event) => {
        if (event.target.id === "closed-election-select") {
            selectedClosedElectionId = event.target.value;
            loadDashboard();
        }
    });
    loadDashboard();
    dashboardTimer = window.setInterval(loadDashboard, 4000);
});

window.addEventListener("beforeunload", () => {
    if (dashboardTimer) window.clearInterval(dashboardTimer);
});

async function loadDashboard() {
    const electionTarget = document.getElementById("dashboard-election");
    const statsTarget = document.getElementById("dashboard-stats");
    const resultsTarget = document.getElementById("dashboard-results");
    const breakdownTarget = document.getElementById("dashboard-breakdown");
    const pickerTarget = document.getElementById("closed-results-picker");

    try {
        const [election, elections] = await Promise.all([
            API.get("/election"),
            API.get("/elections"),
        ]);
        dashboardElection = election.data.election;
        const closedElections = elections.data.closed_elections || [];
        renderClosedResultsPicker(pickerTarget, closedElections);

        if (selectedClosedElectionId) {
            const selectedElection = closedElections.find((item) => String(item.id) === String(selectedClosedElectionId));
            const archived = await API.get(`/results?election_id=${selectedClosedElectionId}`);
            renderDashboardStats(statsTarget, archived.data.stats);
            renderDashboardResults(resultsTarget, archived.data.results);
            renderDashboardBreakdown(
                breakdownTarget,
                archived.data.results,
                archived.data.stats,
                "Closed",
                0,
                0,
                selectedElection,
                true
            );
            electionTarget.innerHTML = `
                <section class="hero-strip dashboard-hero">
                    <div>
                        <span class="eyebrow">Archived Election</span>
                        <h2>${selectedElection?.title || "Selected election"}</h2>
                        <p>${selectedElection ? `${selectedElection.start_date} to ${selectedElection.end_date}` : "Closed results"}</p>
                    </div>
                    <span class="status-pill">Closed results</span>
                </section>
            `;
            return;
        }

        if (!dashboardElection) {
            electionTarget.innerHTML = `
                <section class="hero-strip">
                    <div>
                        <h2>No Active Election</h2>
                        <p>Check back when the administrator opens an election.</p>
                    </div>
                </section>
            `;
            const stats = await API.get("/stats");
            renderDashboardStats(statsTarget, stats.data.stats);
            resultsTarget.innerHTML = "";
            if (breakdownTarget) {
                breakdownTarget.innerHTML = `
                    <section class="breakdown-card">
                        <span class="eyebrow">Archived Results</span>
                        <h3>Choose a closed election</h3>
                        <p>Select a closed election from the dropdown to view its final results.</p>
                    </section>
                `;
            }
            return;
        }

        const voted = election.data.voted_positions || [];
        const positions = [...new Set(election.data.candidates.map((candidate) => candidate.position))];
        const status = positions.length && voted.length === positions.length ? "Complete" : "Pending";
        electionTarget.innerHTML = `
            <section class="hero-strip dashboard-hero">
                <div>
                    <span class="eyebrow">Active Election</span>
                    <h2>${dashboardElection.title}</h2>
                    <p>${dashboardElection.start_date} to ${dashboardElection.end_date}</p>
                </div>
                <div class="quick-actions">
                    <span class="status-pill ${status === "Complete" ? "success" : ""}">${status}</span>
                    <a class="button-link" href="/pages/vote.html">Vote</a>
                    <a class="button-link secondary-link" href="/pages/verify.html">Verify Vote</a>
                </div>
            </section>
        `;

        const live = await API.get(`/results?election_id=${dashboardElection.id}`);
        renderDashboardStats(statsTarget, live.data.stats);
        renderDashboardResults(resultsTarget, live.data.results);
        renderDashboardBreakdown(breakdownTarget, live.data.results, live.data.stats, status, positions.length, voted.length);
    } catch (error) {
        electionTarget.innerHTML = `<div class="message show error">${error.message}</div>`;
    }
}

function renderClosedResultsPicker(target, closedElections) {
    if (!target) return;
    if (!closedElections.length) {
        target.innerHTML = "";
        selectedClosedElectionId = "";
        return;
    }
    target.innerHTML = `
        <label for="closed-election-select">View closed election results</label>
        <select id="closed-election-select">
            <option value="">${dashboardElection ? "Showing active election" : "Select a closed election"}</option>
            ${closedElections
                .map((election) => `<option value="${election.id}" ${String(selectedClosedElectionId) === String(election.id) ? "selected" : ""}>${election.title}</option>`)
                .join("")}
        </select>
    `;
}

function renderDashboardStats(target, stats) {
    target.innerHTML = `
        <article class="stat-card stat-voters"><span>Total Registered Voters</span><strong>${stats.total_registered_voters}</strong></article>
        <article class="stat-card stat-votes"><span>Votes Cast</span><strong>${stats.votes_cast}</strong></article>
        <article class="stat-card stat-turnout"><span>Turnout</span><strong>${stats.turnout_percentage}%</strong></article>
        <article class="stat-card stat-candidates"><span>Total Candidates</span><strong>${stats.number_of_candidates}</strong></article>
    `;
}

function groupResultsByPosition(results) {
    return results.reduce((groups, row) => {
        groups[row.position] = groups[row.position] || [];
        groups[row.position].push(row);
        return groups;
    }, {});
}

function positionPriority(position) {
    const value = String(position || "").toLowerCase();
    if (value.includes("president")) return 0;
    if (value.includes("finance") || value.includes("treasurer")) return 1;
    if (value.includes("academic")) return 2;
    return 10;
}

function positionTheme(position) {
    const value = String(position || "").toLowerCase();
    if (value.includes("president")) return "category-president";
    if (value.includes("finance") || value.includes("treasurer")) return "category-finance";
    if (value.includes("academic")) return "category-academics";
    return "category-default";
}

function sortedPositionEntries(grouped) {
    return Object.entries(grouped).sort(([left], [right]) => {
        const priorityDiff = positionPriority(left) - positionPriority(right);
        return priorityDiff || left.localeCompare(right);
    });
}

function renderDashboardResults(target, results) {
    const grouped = groupResultsByPosition(results);

    target.innerHTML = sortedPositionEntries(grouped)
        .map(([position, rows]) => {
            const maxVotes = Math.max(...rows.map((row) => row.vote_count));
            const totalVotes = rows[0]?.total_votes || 0;
            return `
                <section class="result-group compact-result ${positionTheme(position)}">
                    <div class="compact-result-head">
                        <div>
                            <h3>${position}</h3>
                            <p>Total votes: ${totalVotes}</p>
                        </div>
                        <span class="status-pill">${rows.length} candidates</span>
                    </div>
                    ${rows
                        .map(
                            (row) => `
                            <div class="candidate-progress ${row.vote_count === maxVotes && maxVotes > 0 ? "leading" : ""}">
                                <div class="candidate-progress-meta">
                                    <strong>${row.candidate_name}</strong>
                                    ${row.vote_count === maxVotes && maxVotes > 0 ? '<span class="leader-badge">Leading</span>' : '<span class="leader-badge ghost">Contender</span>'}
                                    <span>${row.vote_count} votes</span>
                                    <b>${row.percentage}%</b>
                                </div>
                                <div class="bar-track"><div class="bar-fill" style="width:${row.percentage}%"></div></div>
                            </div>
                        `
                        )
                        .join("")}
                </section>
            `;
        })
        .join("");
}

function renderDashboardBreakdown(target, results, stats, status, positionCount, votedCount, election = null, archived = false) {
    if (!target) return;
    const grouped = groupResultsByPosition(results);
    const categoryTotals = sortedPositionEntries(grouped)
        .map(([position, rows]) => {
            const total = rows[0]?.total_votes || 0;
            return `<div class="breakdown-row"><span>${position}</span><strong>${total} votes</strong></div>`;
        })
        .join("");

    target.innerHTML = `
        <section class="breakdown-card">
            <span class="eyebrow">Participation Breakdown</span>
            <h3>Voting coverage</h3>
            <div class="participation-ring">
                <strong>${stats.turnout_percentage}%</strong>
                <span>turnout</span>
            </div>
            <div class="breakdown-list">
                ${categoryTotals || '<p>No category totals yet.</p>'}
                ${archived ? "" : `<div class="breakdown-row"><span>Your completed positions</span><strong>${votedCount}/${positionCount}</strong></div>`}
                ${election ? `<div class="breakdown-row"><span>Election</span><strong>${election.title}</strong></div>` : ""}
                <div class="breakdown-row"><span>Status</span><strong>${status}</strong></div>
            </div>
            <div class="quick-actions" ${archived ? "hidden" : ""}>
                <a class="button-link" href="/pages/vote.html">Vote</a>
                <a class="button-link secondary-link" href="/pages/verify.html">Verify</a>
            </div>
        </section>
    `;
}
