// Character count for username and password

document.addEventListener("DOMContentLoaded", () => {
    const usernameInput = document.getElementById("username");
    const usernameCount = document.getElementById("username-count");

    // If the elements in the const variables above exist
    if (usernameInput && usernameCount) {
        usernameInput.addEventListener("input", () => {

            // Get the length of the current username
            const length = usernameInput.value.length;

            // Display the length of the current username
            usernameCount.textContent = `${length} / 30`;

        });
    }

    // If the elements in the const variables above exist
    const passwordInput = document.getElementById("password");
    const passwordCount = document.getElementById("password-count");

    if (passwordInput && passwordCount) {
        passwordInput.addEventListener("input", () => {

            // Get the length of the current password
            const length = passwordInput.value.length;

            // Display the length of the current password
            passwordCount.textContent = `${length} / 64`;

        });
    }
});