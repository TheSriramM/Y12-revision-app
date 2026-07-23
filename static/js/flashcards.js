const cardElement = document.getElementById('flashcard');
const cardTextElement = document.getElementById('card-text');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const flipBtn = document.getElementById('flip-btn');
const counterElement = document.getElementById('card-counter');

// Initialising buttons
document.addEventListener('DOMContentLoaded', () => {
    const currentIndex = parseInt(cardElement.dataset.index);
    const totalCards = parseInt(cardElement.dataset.total);
    
    prevBtn.disabled = currentIndex === 0;
    nextBtn.disabled = currentIndex === totalCards - 1;
});

// This function is triggered when the user clicks one of the action buttons
async function sendAction(action) {
    try {
        // This data (which button the user clicked) is sent through the POST method
        // It contains the action header which Flask uses
        const response = await fetch(window.location.pathname, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: `action=${action}`
        });

        // If a valid response is not received, the error message will be shown
        if (!response.ok) throw new Error('Network response failed');
        
        const data = await response.json(); // Parsing the json received from Flask (reading the json)
        
        // Animate the card flip
        cardElement.classList.add('flip-out');
        
        // Update text and state after half flip (smooth animation)
        setTimeout(() => {
            cardTextElement.textContent = data.card_text;
            counterElement.textContent = `Card ${data.current_index + 1} of ${data.total_cards}`;
            
            // Update button states
            prevBtn.disabled = data.current_index === 0;
            nextBtn.disabled = data.current_index === data.total_cards - 1;
            
            cardElement.classList.remove('flip-out');
            cardElement.classList.add('flip-in');
            
            // Animation tweaking with card flip time
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