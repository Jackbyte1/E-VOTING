document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("verify-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = event.target.querySelector("button[type='submit']");
        setLoading(button, true, "Checking...");
        clearMessage("verify-message");
        const voteHash = new FormData(event.target).get("vote_hash").trim();

        try {
            const result = await API.get(`/verify-vote?hash=${encodeURIComponent(voteHash)}`);
            if (result.data.verified) {
                showMessage("verify-message", "Vote Verified", "success");
            } else {
                showMessage("verify-message", "Invalid vote hash", "error");
            }
        } catch (error) {
            showMessage("verify-message", error.message, "error");
        } finally {
            setLoading(button, false);
        }
    });
});
