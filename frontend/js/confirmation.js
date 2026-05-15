document.addEventListener("DOMContentLoaded", () => {
    const hashes = JSON.parse(sessionStorage.getItem("voteHashes") || "[]");
    const singleHash = sessionStorage.getItem("voteHash");
    const container = document.getElementById("vote-hash");

    if (hashes.length) {
        container.innerHTML = hashes
            .map(
                (receipt) => `
                <div class="receipt-row">
                    <strong>${receipt.position}</strong>
                    <span>${receipt.candidate_name}</span>
                    <code>${receipt.vote_hash}</code>
                </div>
            `
            )
            .join("");
        return;
    }

    container.textContent = singleHash || "No vote hash found in this browser session.";
});
