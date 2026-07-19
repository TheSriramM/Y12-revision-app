document.addEventListener("DOMContentLoaded", () => {
    // Every element with class toast message and storing them in a list (NodeList)
    const toasts = document.querySelectorAll(".toast-message");

    // Looping through each notification
    toasts.forEach((toast) => {
        
        // 3 second timer
        // The code inside the block will trigger once the 3 seconds are over
        setTimeout(() => {
            // These two lines work together to decrease the opacity of the toast notification to zero over 0.4 seconds
            toast.style.transition = "opacity 0.4s ease";
            toast.style.opacity = "0";

            // Once the 0.4 seconds are over, the toast notification is deleted
            setTimeout(() => toast.remove(), 400);
        }, 3000);

    });

});