// UWorld Full Test Block Extractor
// Run this in the browser console while reviewing a completed test.
// It will navigate through ALL questions and collect them.
//
// Usage: paste this entire script into the console, then run:
//   extractAllQuestions()

function cleanInternalLinks(html) {
  // Replace javascript:void(0) links with bold text
  return html.replace(
    /<a\s+[^>]*href\s*=\s*["']javascript:void\(0\)["'][^>]*>([\s\S]*?)<\/a>/gi,
    '<strong>$1</strong>'
  );
}

function extractCurrentQuestion() {
  const detailsEl = document.querySelector('.question-details');
  const questionId = detailsEl
    ? detailsEl.textContent.match(/Question Id:\s*(\d+)/)?.[1] || ''
    : '';

  const itemMatch = detailsEl
    ? detailsEl.textContent.match(/Item\s+(\d+)\s+of\s+(\d+)/)
    : null;
  const itemNumber = itemMatch ? parseInt(itemMatch[1]) : null;
  const totalItems = itemMatch ? parseInt(itemMatch[2]) : null;

  const questionTextEl = document.querySelector('#questionText');
  let questionHtml = questionTextEl ? questionTextEl.innerHTML.trim() : '';
  const questionPlain = questionTextEl ? questionTextEl.innerText.trim() : '';
  questionHtml = cleanInternalLinks(questionHtml);

  const choices = [];
  const radioInputs = document.querySelectorAll(
    '#answerContainer input[type="radio"]'
  );
  radioInputs.forEach((input, idx) => {
    const ariaLabel = input.getAttribute('aria-label') || '';
    // aria-label format: "option1Alcoholic hepatitis"
    const textMatch = ariaLabel.match(/^option\d+(.+)$/);
    const answerText = textMatch ? textMatch[1] : '';
    const letter = String.fromCharCode(65 + idx); // A, B, C, ...

    const row = input.closest('tr');
    const isCorrect = row ? !!row.querySelector('.fa-check') : false;
    const isSelected = row ? !!row.querySelector('.mat-radio-checked') : false;

    const contentTd = row ? row.querySelector('.answer-choice-content') : null;
    const pctMatch = contentTd ? contentTd.textContent.match(/\((\d+)%\)/) : null;
    const percentage = pctMatch ? parseInt(pctMatch[1]) : null;

    if (answerText) {
      choices.push({ letter, text: answerText, percentage, isCorrect, isSelected });
    }
  });

  const correctChoice = choices.find((c) => c.isCorrect);
  const selectedChoice = choices.find((c) => c.isSelected);

  const explanationEl = document.querySelector('#first-explanation');
  let explanationHtml = explanationEl ? explanationEl.innerHTML.trim() : '';
  const explanationPlain = explanationEl ? explanationEl.innerText.trim() : '';
  explanationHtml = cleanInternalLinks(explanationHtml);

  const eduMatch = explanationPlain.match(
    /Educational objective:\s*([\s\S]*?)(?:$|References|Copyright)/
  );
  const educationalObjective = eduMatch ? eduMatch[1].trim() : '';

  const standards = {};
  document.querySelectorAll('.standard').forEach((el) => {
    const header = el.querySelector('.standard-header')?.textContent.trim();
    const desc = el.querySelector('.standard-description')?.textContent.trim();
    if (header && desc) standards[header.toLowerCase()] = desc;
  });

  const statsBar = document.querySelector('.stats-bar');
  const pctCorrectMatch = statsBar
    ? statsBar.textContent.match(/(\d+)%\s*Answered correctly/)
    : null;
  const timeMatch = statsBar
    ? statsBar.textContent.match(/(\d+)\s*secs?\s*Time Spent/)
    : null;
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

function clickNextButton() {
  const nextBtn = document.querySelector('a[aria-label="Navigate to Next Question"]');
  if (nextBtn) {
    nextBtn.click();
    return true;
  }
  return false;
}

function clickPreviousButton() {
  const prevBtn = document.querySelector(
    'a[aria-label="Navigate to Previous Question"]'
  );
  if (prevBtn) {
    prevBtn.click();
    return true;
  }
  return false;
}

function clickQuestionInNav(index) {
  // Click a specific question in the left navigator (1-based index)
  const rows = document.querySelectorAll(
    '#leftNavigator .mat-row'
  );
  if (rows[index - 1]) {
    rows[index - 1].click();
    return true;
  }
  return false;
}

function waitForQuestionLoad(expectedItem, maxWait = 5000) {
  return new Promise((resolve) => {
    const start = Date.now();
    const check = () => {
      const detailsEl = document.querySelector('.question-details');
      const currentItem = detailsEl
        ? detailsEl.textContent.match(/Item\s+(\d+)/)?.[1]
        : null;
      if (currentItem && parseInt(currentItem) === expectedItem) {
        // Wait a bit more for content to render
        setTimeout(resolve, 500);
      } else if (Date.now() - start > maxWait) {
        console.warn(`Timeout waiting for question ${expectedItem}`);
        resolve();
      } else {
        setTimeout(check, 200);
      }
    };
    check();
  });
}

async function extractAllQuestions() {
  const allQuestions = [];

  // First, figure out total questions from current page
  const detailsEl = document.querySelector('.question-details');
  const totalMatch = detailsEl
    ? detailsEl.textContent.match(/Item\s+\d+\s+of\s+(\d+)/)
    : null;
  const total = totalMatch ? parseInt(totalMatch[1]) : 0;

  if (!total) {
    console.error('Could not determine total number of questions.');
    return;
  }

  console.log(`Found ${total} questions. Starting extraction...`);

  // Navigate to question 1 first
  clickQuestionInNav(1);
  await waitForQuestionLoad(1);

  for (let i = 1; i <= total; i++) {
    console.log(`Extracting question ${i} of ${total}...`);

    const q = extractCurrentQuestion();
    allQuestions.push(q);

    if (i < total) {
      clickNextButton();
      await waitForQuestionLoad(i + 1);
    }
  }

  console.log(`\nExtraction complete! ${allQuestions.length} questions collected.`);
  console.log('Data stored in window.__uworldData');
  console.log('Run: copy(JSON.stringify(window.__uworldData, null, 2))');
  console.log('Then paste into a .json file.');

  window.__uworldData = allQuestions;

  // Also try to auto-copy
  try {
    copy(JSON.stringify(allQuestions, null, 2));
    console.log('JSON automatically copied to clipboard!');
  } catch (e) {
    console.log('Auto-copy failed. Use the copy() command above.');
  }

  return allQuestions;
}

console.log('UWorld Extractor loaded. Run: extractAllQuestions()');
