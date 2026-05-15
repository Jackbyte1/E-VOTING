let activeElection = null;
let resultsTimer = null;

function groupByPosition(candidates) {
    return candidates.reduce((groups, candidate) => {
        groups[candidate.position] = groups[candidate.position] || [];
        groups[candidate.position].push(candidate);
        return groups;
    }, {});
}

async function loadElection() {
    const container = document.getElementById("election-container");
    try {
        const result = await API.get("/election");
        activeElection = result.data.election;

        if (!activeElection) {
            container.innerHTML = "<p>No active election is currently open.</p>";
            await loadLiveResults();
            return;
        }

        const grouped = groupByPosition(result.data.candidates);
        const votedPositions = new Set(result.data.voted_positions || []);
        const positionEntries = Object.entries(grouped);
        const canVote = positionEntries.some(([position]) => !votedPositions.has(position));
        const sections = positionEntries
            .map(([position, candidates]) => {
                const locked = votedPositions.has(position);
                const options = candidates
                    .map(
                        (candidate) => `
                        <label class="candidate-option ${locked ? "disabled" : ""}">
                            <input type="radio" name="position_${position}" value="${candidate.id}" ${locked ? "disabled" : "required"}>
                            <span>
                                <strong>${candidate.name}</strong>
                                <span class="small">${candidate.position}</span>
                            </span>
                        </label>
                    `
                    )
                    .join("");
                return `
                    <section class="position-card">
                        <div class="section-title">
                            <h3>${position}</h3>
                            ${locked ? '<span class="status-pill success">Voted</span>' : '<span class="status-pill">Open</span>'}
                        </div>
                        <div class="candidate-list">${options}</div>
                    </section>
                `;
            })
            .join("");

        container.innerHTML = `
            <div class="hero-strip">
                <div>
                    <h2>${activeElection.title}</h2>
                    <p>${activeElection.start_date} to ${activeElection.end_date}</p>
                </div>
                <span class="status-pill success">Active</span>
            </div>
            <form id="vote-form">
                ${sections}
                <div class="button-row">
                    ${canVote ? '<button type="submit">Submit Ballot</button>' : '<span class="status-pill success">All positions completed</span>'}
                </div>
            </form>
            <div id="vote-message" class="message"></div>
        `;

        document.getElementById("vote-form").addEventListener("submit", submitVote);
        await loadLiveResults();
        resultsTimer = window.setInterval(loadLiveResults, 4000);
    } catch (error) {
        container.innerHTML = `<div class="message show error">${error.message}</div>`;
    }
}

async function submitVote(event) {
    event.preventDefault();
    const button = event.target.querySelector("button[type='submit']");
    setLoading(button, true, "Encrypting ballot...");

    const selections = Array.from(event.target.querySelectorAll("input[type='radio']:checked")).map((input) => ({
        candidate_id: input.value,
    }));

    try {
        const result = await API.post("/vote", {
            election_id: activeElection.id,
            selections,
        });
        sessionStorage.setItem("voteHash", result.data.vote_hash);
        sessionStorage.setItem("voteHashes", JSON.stringify(result.data.vote_hashes || []));
        window.location.href = "/pages/confirmation.html";
    } catch (error) {
        showMessage("vote-message", error.message, "error");
    } finally {
        setLoading(button, false);
    }
}

async function loadLiveResults() {
    const statsTarget = document.getElementById("student-stats");
    const resultsTarget = document.getElementById("live-results");
    if (!statsTarget || !resultsTarget) return;

    try {
        const query = activeElection ? `?election_id=${activeElection.id}` : "";
        const result = await API.get(`/results${query}`);
        renderStats(statsTarget, result.data.stats);
        renderResults(resultsTarget, result.data.results);
    } catch (error) {
        resultsTarget.innerHTML = `<div class="message show error">${error.message}</div>`;
    }
}

function renderStats(target, stats) {
    target.innerHTML = `
        <article class="stat-card stat-voters"><span>Total Registered Voters</span><strong>${stats.total_registered_voters}</strong></article>
        <article class="stat-card stat-votes"><span>Votes Cast</span><strong>${stats.votes_cast}</strong></article>
        <article class="stat-card stat-turnout"><span>Turnout</span><strong>${stats.turnout_percentage}%</strong></article>
        <article class="stat-card stat-candidates"><span>Candidates</span><strong>${stats.number_of_candidates}</strong></article>
    `;
}

function renderResults(target, results) {
    const grouped = results.reduce((groups, row) => {
        groups[row.position] = groups[row.position] || [];
        groups[row.position].push(row);
        return groups;
    }, {});

    const sortedEntries = Object.entries(grouped).sort(([left], [right]) => {
        const priority = (position) => {
            const value = String(position || "").toLowerCase();
            if (value.includes("president")) return 0;
            if (value.includes("finance") || value.includes("treasurer")) return 1;
            if (value.includes("academic")) return 2;
            return 10;
        };
        return priority(left) - priority(right) || left.localeCompare(right);
    });

    const themeFor = (position) => {
        const value = String(position || "").toLowerCase();
        if (value.includes("president")) return "category-president";
        if (value.includes("finance") || value.includes("treasurer")) return "category-finance";
        if (value.includes("academic")) return "category-academics";
        return "category-default";
    };

    target.innerHTML = sortedEntries
        .map(
            ([position, rows]) => `
            <section class="result-group compact-result ${themeFor(position)}">
                <div class="compact-result-head">
                    <div>
                        <h3>${position}</h3>
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

window.addEventListener("beforeunload", () => {
    if (resultsTimer) window.clearInterval(resultsTimer);
});

document.addEventListener("DOMContentLoaded", loadElection);
