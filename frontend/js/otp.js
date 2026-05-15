document.addEventListener("DOMContentLoaded", () => {
    const otpForm = document.getElementById("otp-form");
    const devOtp = sessionStorage.getItem("devOtp");
    const devOtpElement = document.getElementById("dev-otp");
    if (devOtpElement && devOtp) {
        devOtpElement.textContent = `Development OTP: ${devOtp}`;
    }

    otpForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = otpForm.querySelector("button[type='submit']");
        setLoading(button, true, "Verifying...");
        clearMessage("otp-message");
        const form = new FormData(otpForm);
        try {
            const result = await API.post("/verify-otp", {
                otp_code: form.get("otp_code"),
            });
            sessionStorage.setItem("role", result.data.role);
            sessionStorage.removeItem("devOtp");
            window.location.href =
                result.data.role === "admin" ? "/pages/admin.html" : "/pages/dashboard.html";
        } catch (error) {
            showMessage("otp-message", error.message, "error");
        } finally {
            setLoading(button, false);
        }
    });
});
