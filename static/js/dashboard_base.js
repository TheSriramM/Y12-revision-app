document.addEventListener("DOMContentLoaded", () => {
    const toasts = document.querySelectorAll(".toast-message");

    toasts.forEach((toast) => {
        setTimeout(() => {
            toast.style.transition = "opacity 0.4s ease";
            toast.style.opacity = "0";

            setTimeout(() => toast.remove(), 400);
        }, 3000);
    });
});