document.addEventListener("DOMContentLoaded", loadProfile);

async function loadProfile() {
    const target = document.getElementById("profile-details");
    try {
        const result = await API.get("/profile");
        const profile = result.data.profile;
        target.innerHTML = `
            <div class="profile-grid">
                <article><span>Full Name</span><strong>${profile.name}</strong></article>
                <article><span>Email</span><strong>${profile.email}</strong></article>
                <article><span>Institution ID</span><strong>${profile.institution_id || "Not provided"}</strong></article>
                <article><span>Registration Number</span><strong>${profile.reg_number || "Not provided"}</strong></article>
                <article><span>Course</span><strong>${profile.course || "Not provided"}</strong></article>
                <article><span>Voting Status</span><strong>${profile.voting_status}</strong></article>
                <article><span>Voted Positions</span><strong>${profile.voted_positions.join(", ") || "None yet"}</strong></article>
            </div>
        `;
    } catch (error) {
        target.innerHTML = `<div class="message show error">${error.message}</div>`;
    }
}
