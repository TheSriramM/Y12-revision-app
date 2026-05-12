const flashcards = [
  { question: "What is H2O?", answer: "Water" },
  { question: "pH of neutral solution?", answer: "7" }
];

let index = 0;
let showingAnswer = false;

function updateCard() {
  const card = document.getElementById("cardText");
  card.innerText = showingAnswer
    ? flashcards[index].answer
    : flashcards[index].question;
}

function flipCard() {
  showingAnswer = !showingAnswer;
  updateCard();
}

function nextCard() {
  index = (index + 1) % flashcards.length;
  showingAnswer = false;
  updateCard();
}

function prevCard() {
  index = (index - 1 + flashcards.length) % flashcards.length;
  showingAnswer = false;
  updateCard();
}

updateCard();