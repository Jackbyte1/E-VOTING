document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
    bindPasswordToggles();

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const button = loginForm.querySelector("button[type='submit']");
            setLoading(button, true, "Sending OTP...");
            clearMessage("auth-message");
            const form = new FormData(loginForm);
            try {
                const result = await API.post("/login", {
                    email: form.get("email"),
                    password: form.get("password"),
                });
                sessionStorage.setItem("pendingRole", result.data.role);
                sessionStorage.setItem("devOtp", result.data.dev_otp);
                window.location.href = "/pages/otp.html";
            } catch (error) {
                showMessage("auth-message", error.message, "error");
            } finally {
                setLoading(button, false);
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const button = registerForm.querySelector("button[type='submit']");
            setLoading(button, true, "Creating...");
            clearMessage("register-message");
            const form = new FormData(registerForm);
            try {
                await API.post("/register", {
                    name: form.get("name"),
                    email: form.get("email"),
                    password: form.get("password"),
                    reg_number: form.get("reg_number"),
                    course: form.get("course"),
                });
                showMessage("register-message", "Account created. You can sign in now.", "success");
                registerForm.reset();
            } catch (error) {
                showMessage("register-message", error.message, "error");
            } finally {
                setLoading(button, false);
            }
        });
    }
});

function bindPasswordToggles() {
    document.querySelectorAll("[data-toggle-password]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.togglePassword);
            if (!input) return;
            const isHidden = input.type === "password";
            input.type = isHidden ? "text" : "password";
            button.classList.toggle("is-visible", isHidden);
            button.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
        });
    });
}
