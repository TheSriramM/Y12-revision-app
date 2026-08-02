const cardElement = document.getElementById('flashcard');
const cardTextElement = document.getElementById('card-text');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const flipBtn = document.getElementById('flip-btn');
const finishBtn = document.getElementById('finish-btn');
const counterElement = document.getElementById('card-counter');

// Initialise buttons
document.addEventListener('DOMContentLoaded', () => {
    const currentIndex = parseInt(cardElement.dataset.index);
    const totalCards = parseInt(cardElement.dataset.total);
    
    prevBtn.disabled = currentIndex === 0;
    nextBtn.disabled = currentIndex === totalCards - 1;
});

// This function is triggered when the user clicks one of the action buttons
async function sendAction(action) {
    try {
        // Check if an AJAX request is made
        const response = await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: `action=${action}`
        });

        if (!response.ok) throw new Error('Network response failed');

        // Parse the JSON
        const data = await response.json();

        // If the page is being redirected
        if (data.redirect) {
            window.location.href = data.redirect;
            return;
        }

        // Add flip-out class to the HTML flashcard element
        cardElement.classList.add('flip-out');

        // Making a built in timer for the animation
        setTimeout(() => {
            cardTextElement.textContent = data.card_text;
            counterElement.textContent = `Card ${data.current_index + 1} of ${data.total_cards}`;

            prevBtn.disabled = data.current_index === 0;
            nextBtn.disabled = data.current_index === data.total_cards - 1;

            // Remove the flip-out animation and add the flip-in animation
            cardElement.classList.remove('flip-out');
            cardElement.classList.add('flip-in');

            // Flip out takes 150ms
            // Flip in takes 150ms

            // Remove the flip out animation
            // This resets the card to its original state, ready to flip again
            setTimeout(() => {
                cardElement.classList.remove('flip-in');
            }, 300);

        }, 150);

    } catch (error) {
        console.error('Error:', error);
    }
}

flipBtn.addEventListener("click", () => {
    // When the user clicks the flip button on the screen
    // The flip animation is played
    sendAction("flip");
});

prevBtn.addEventListener("click", () => {
    if (!prevBtn.disabled)
        sendAction("prev");
});

nextBtn.addEventListener("click", () => {
    if (!nextBtn.disabled)
        sendAction("next");
});

finishBtn.addEventListener("click", () => {
    // The finish action is sent to the flask
    sendAction("finish");
});