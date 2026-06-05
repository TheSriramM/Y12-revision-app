const cardElement = document.getElementById('flashcard');
const cardTextElement = document.getElementById('card-text');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const flipBtn = document.getElementById('flip-btn');
const counterElement = document.getElementById('card-counter');

async function sendAction(action) {
    try {
        // This data (which button the user clicked) is sent through the POST method
        // It contains the action header which Flask uses
        const response = await fetch('/flashcards', {
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

flipBtn.addEventListener('click', (e) => {
    // When the user clicks the flip button on the screen
    // The flip animation is played
    e.preventDefault();
    sendAction('flip');
});

prevBtn.addEventListener('click', (e) => {
    e.preventDefault();
    if (!prevBtn.disabled) sendAction('prev');
});

nextBtn.addEventListener('click', (e) => {
    e.preventDefault();
    if (!nextBtn.disabled) sendAction('next');
});

// Initialising buttons
document.addEventListener('DOMContentLoaded', () => {
    const currentIndex = parseInt(cardElement.dataset.index);
    const totalCards = parseInt(cardElement.dataset.total);
    
    prevBtn.disabled = currentIndex === 0;
    nextBtn.disabled = currentIndex === totalCards - 1;
});