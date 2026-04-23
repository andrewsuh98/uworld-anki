// UWorld Question Extractor - Console Script
// Run this in the browser console while on a UWorld question review page.
// It extracts the current question and copies JSON to clipboard.

function extractCurrentQuestion() {
  // Question ID
  const detailsEl = document.querySelector('.question-details');
  const questionId = detailsEl
    ? detailsEl.textContent.match(/Question Id:\s*(\d+)/)?.[1] || ''
    : '';

  // Item number (e.g., "Item 3 of 10")
  const itemMatch = detailsEl
    ? detailsEl.textContent.match(/Item\s+(\d+)\s+of\s+(\d+)/)
    : null;
  const itemNumber = itemMatch ? parseInt(itemMatch[1]) : null;
  const totalItems = itemMatch ? parseInt(itemMatch[2]) : null;

  // Question text (HTML preserved for tables/formatting)
  const questionTextEl = document.querySelector('#questionText');
  const questionHtml = questionTextEl ? questionTextEl.innerHTML.trim() : '';
  const questionPlain = questionTextEl ? questionTextEl.innerText.trim() : '';

  // Answer choices
  const choices = [];
  const answerRows = document.querySelectorAll('#answerContainer tr');
  answerRows.forEach((row) => {
    const letterEl = row.querySelector('.left-td span:last-child');
    const letter = letterEl ? letterEl.textContent.trim().replace('.', '') : '';

    const answerEl = row.querySelector('.answer-choice-content span[id^="answerhighlight"] span');
    const answerText = answerEl ? answerEl.textContent.trim() : '';

    // Percentage chosen
    const contentTd = row.querySelector('.answer-choice-content');
    const pctMatch = contentTd ? contentTd.textContent.match(/\((\d+)%\)/) : null;
    const percentage = pctMatch ? parseInt(pctMatch[1]) : null;

    // Is this the correct answer? (has check icon)
    const isCorrect = !!row.querySelector('.fa-check');

    // Is this the user's selected answer? (has radio checked)
    const isSelected = !!row.querySelector('.mat-radio-checked');

    // Is this wrong? (has X icon)
    const isWrong = !!row.querySelector('.fa-times');

    if (letter && answerText) {
      choices.push({
        letter,
        text: answerText,
        percentage,
        isCorrect,
        isSelected,
      });
    }
  });

  const correctChoice = choices.find((c) => c.isCorrect);
  const selectedChoice = choices.find((c) => c.isSelected);

  // Explanation (HTML preserved)
  const explanationEl = document.querySelector('#first-explanation');
  const explanationHtml = explanationEl ? explanationEl.innerHTML.trim() : '';
  const explanationPlain = explanationEl ? explanationEl.innerText.trim() : '';

  // Educational objective
  const eduMatch = explanationPlain.match(
    /Educational objective:\s*([\s\S]*?)(?:$|References|Copyright)/
  );
  const educationalObjective = eduMatch ? eduMatch[1].trim() : '';

  // Subject, System, Topic
  const standards = {};
  document.querySelectorAll('.standard').forEach((el) => {
    const header = el.querySelector('.standard-header')?.textContent.trim();
    const desc = el.querySelector('.standard-description')?.textContent.trim();
    if (header && desc) {
      standards[header.toLowerCase()] = desc;
    }
  });

  // Stats
  const statsBar = document.querySelector('.stats-bar');
  const pctCorrectMatch = statsBar
    ? statsBar.textContent.match(/(\d+)%\s*Answered correctly/)
    : null;
  const timeMatch = statsBar
    ? statsBar.textContent.match(/(\d+)\s*secs?\s*Time Spent/)
    : null;
  const wasCorrect = !!statsBar?.querySelector('.correct-answer');
  const wasIncorrect = !!statsBar?.querySelector('.incorrect-answer');

  return {
    questionId,
    itemNumber,
    totalItems,
    questionPlain,
    questionHtml,
    choices,
    correctAnswer: correctChoice
      ? `${correctChoice.letter}. ${correctChoice.text}`
      : '',
    correctLetter: correctChoice?.letter || '',
    selectedAnswer: selectedChoice
      ? `${selectedChoice.letter}. ${selectedChoice.text}`
      : '',
    selectedLetter: selectedChoice?.letter || '',
    wasCorrect: !wasIncorrect,
    educationalObjective,
    explanationHtml,
    explanationPlain,
    subject: standards.subject || '',
    system: standards.system || '',
    topic: standards.topic || '',
    percentCorrect: pctCorrectMatch ? parseInt(pctCorrectMatch[1]) : null,
    timeSpentSecs: timeMatch ? parseInt(timeMatch[1]) : null,
  };
}

// Extract and copy to clipboard
const data = extractCurrentQuestion();
console.log('Extracted question:', data.questionId, '-', data.topic);
console.log(JSON.stringify(data, null, 2));
copy(JSON.stringify(data, null, 2));
console.log('JSON copied to clipboard!');
