// Character count for username and password

document.addEventListener("DOMContentLoaded", () => {
    const usernameInput = document.getElementById("username");
    const usernameCount = document.getElementById("username-count");

    if (usernameInput && usernameCount) {
        usernameInput.addEventListener("input", () => {

            const length = usernameInput.value.length;
            usernameCount.textContent = `${length} / 30`;

        });
    }

    const passwordInput = document.getElementById("password");
    const passwordCount = document.getElementById("password-count");

    if (passwordInput && passwordCount) {
        passwordInput.addEventListener("input", () => {

            const length = passwordInput.value.length;
            passwordCount.textContent = `${length} / 64`;

        });
    }
});