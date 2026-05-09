// AMBOSS Question Extractor for Review Sessions
// Injected via Playwright into AMBOSS review pages.
// Navigates through all questions and extracts data.
//
// Usage: paste this entire script into the console, then run:
//   extractAllQuestions()

function cleanAmbossLinks(html) {
  return html
    .replace(/<a\s+[^>]*data-type\s*=\s*["']link["'][^>]*>([\s\S]*?)<\/a>/gi, '<strong>$1</strong>')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
}

function extractCurrentQuestion() {
  // Question ID from notes-editor button
  const notesBtn = document.querySelector('button[aria-controls^="notes-editor-"]');
  const questionId = notesBtn
    ? notesBtn.getAttribute('aria-controls').replace('notes-editor-', '')
    : '';

  // Item number from URL
  const urlMatch = window.location.pathname.match(/\/(\d+)$/);
  const itemNumber = urlMatch ? parseInt(urlMatch[1]) : null;

  // Total items from session count
  const countEl = document.querySelector('[data-e2e-test-id="sessionQuestionCount"]');
  const countMatch = countEl ? countEl.textContent.match(/(\d+)\/(\d+)/) : null;
  const totalItems = countMatch ? parseInt(countMatch[2]) : null;

  // Question text: first article not inside hint or answer explanation
  const primarySpace = document.querySelector('[data-e2e-test-id="primary-space"]');
  const articles = primarySpace ? primarySpace.querySelectorAll('article') : document.querySelectorAll('article');
  const questionArticle = Array.from(articles).find(a =>
    !a.closest('[data-e2e-test-id="hint"]') &&
    !a.closest('[data-e2e-test-id="answerExplanation"]')
  );
  let questionHtml = questionArticle ? questionArticle.innerHTML.trim() : '';
  const questionPlain = questionArticle ? questionArticle.innerText.trim() : '';
  questionHtml = cleanAmbossLinks(questionHtml);

  // Extract choices from answer rows
  const choices = [];
  const answerRows = document.querySelectorAll('[data-e2e-test-id="answer-row"]');

  answerRows.forEach(row => {
    const themeContainer = row.closest('[data-e2e-test-id^="answer-theme-"]');
    const theme = themeContainer ? themeContainer.getAttribute('data-e2e-test-id') : '';

    const letterEl = row.querySelector('[data-testid="answer-letter"]');
    const letter = letterEl ? letterEl.textContent.trim() : '';

    const btn = row.querySelector('button[data-testid^="answer-"]');
    const textEl = btn ? btn.querySelector('p') : null;
    const text = textEl ? textEl.innerText.trim() : '';

    const statsEl = row.querySelector('[data-testid="answer-stats"]');
    const statsText = statsEl ? statsEl.textContent : '';
    const pctMatch = statsText.match(/(\d+)%/);
    const percentage = pctMatch ? parseInt(pctMatch[1]) : null;

    // 'Correct' (capital C) appears in userFirstAttemptCorrect and answerOptionCorrect
    // but NOT in answerOptionIncorrect or userFirstAttemptIncorrect
    const isCorrect = theme.includes('Correct');
    const isSelected = theme.includes('userFirstAttempt');

    if (letter) {
      choices.push({ letter, text, percentage, isCorrect, isSelected });
    }
  });

  const correctChoice = choices.find(c => c.isCorrect);
  const selectedChoice = choices.find(c => c.isSelected);
  const wasCorrect = !!choices.find(c => c.isCorrect && c.isSelected);

  // Extract explanations from each answer container
  const allThemeContainers = document.querySelectorAll('[data-e2e-test-id^="answer-theme-"]');
  let correctExplanation = '';
  const otherExplanations = [];

  allThemeContainers.forEach(container => {
    const theme = container.getAttribute('data-e2e-test-id');
    const contentEl = container.querySelector('[data-e2e-test-id="answerExplanation"] div[data-intutorial="false"]');
    const html = contentEl ? contentEl.innerHTML.trim() : '';
    if (!html) return;

    const letterEl = container.querySelector('[data-testid="answer-letter"]');
    const letter = letterEl ? letterEl.textContent.trim() : '';

    if (theme.includes('Correct')) {
      correctExplanation = cleanAmbossLinks(html);
    } else if (html.length > 0) {
      otherExplanations.push({ letter, html: cleanAmbossLinks(html) });
    }
  });

  let explanationHtml = correctExplanation;
  for (const oe of otherExplanations) {
    if (oe.html) {
      explanationHtml += `<hr><p><strong>Why not ${oe.letter}:</strong></p>${oe.html}`;
    }
  }

  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = explanationHtml;
  const explanationPlain = tempDiv.textContent.trim();

  // Attending tip (AMBOSS equivalent of educational objective)
  const hintArticle = document.querySelector('[data-e2e-test-id="hint"] article');
  const attendingTip = hintArticle ? hintArticle.innerText.trim() : '';

  // Topic from linked article button in the correct answer's explanation area
  const linkedArticle = document.querySelector('a[data-e2e-test-id="linked-article"]');
  const topic = linkedArticle ? linkedArticle.textContent.trim() : '';

  // Difficulty from sidebar hammers for this question
  const sidebarItem = document.querySelector(`[data-e2e-test-id="question-${itemNumber}"]`);
  const hammersEl = sidebarItem
    ? sidebarItem.querySelector('[data-e2e-test-id^="difficulty-hammers-"]')
    : null;
  const difficultyStr = hammersEl
    ? hammersEl.getAttribute('data-e2e-test-id').replace('difficulty-hammers-', '')
    : null;
  const difficulty = difficultyStr ? parseInt(difficultyStr) : null;

  return {
    questionId,
    source: 'amboss',
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
    wasCorrect,
    educationalObjective: attendingTip,
    explanationHtml,
    explanationPlain,
    subject: null,
    system: null,
    topic,
    percentCorrect: correctChoice?.percentage || null,
    timeSpentSecs: null,
    difficulty,
    attendingTip,
    aiSummary: null,
  };
}

function clickNextButton() {
  const nextBtn = document.querySelector('[data-e2e-test-id="next-button"]');
  if (nextBtn && !nextBtn.hasAttribute('disabled')) {
    nextBtn.click();
    return true;
  }
  return false;
}

function clickSidebarQuestion(n) {
  const item = document.querySelector(`[data-e2e-test-id="question-${n}"]`);
  if (item) {
    item.click();
    return true;
  }
  return false;
}

function waitForQuestionLoad(expectedN, maxWait = 5000) {
  return new Promise((resolve) => {
    const start = Date.now();
    const check = () => {
      const urlMatch = window.location.pathname.match(/\/(\d+)$/);
      const currentN = urlMatch ? parseInt(urlMatch[1]) : null;
      if (currentN === expectedN) {
        setTimeout(resolve, 500);
      } else if (Date.now() - start > maxWait) {
        console.warn(`Timeout waiting for question ${expectedN}`);
        resolve();
      } else {
        setTimeout(check, 200);
      }
    };
    check();
  });
}

async function expandAllExplanations() {
  const expandIcon = document.querySelector('[data-e2e-test-id="expand"]');
  if (!expandIcon) return;

  const expandBtn = expandIcon.closest('button');
  if (!expandBtn) return;

  const btnText = expandBtn.textContent.trim();
  if (!btnText.toLowerCase().includes('show all')) return;

  expandBtn.click();

  // Wait for collapsed sections to expand
  await new Promise((resolve) => {
    const start = Date.now();
    const check = () => {
      const wrappers = document.querySelectorAll('[data-e2e-test-id="answerExplanation"]');
      const allExpanded = Array.from(wrappers).every(el => {
        const rah = el.closest('.rah-static');
        return !rah || !rah.classList.contains('rah-static--height-zero');
      });
      if (allExpanded || Date.now() - start > 3000) {
        setTimeout(resolve, 300);
      } else {
        setTimeout(check, 200);
      }
    };
    setTimeout(check, 300);
  });
}

async function extractAllQuestions() {
  const allQuestions = [];

  const countEl = document.querySelector('[data-e2e-test-id="sessionQuestionCount"]');
  const countMatch = countEl ? countEl.textContent.match(/(\d+)\/(\d+)/) : null;
  const total = countMatch ? parseInt(countMatch[2]) : 0;

  if (!total) {
    console.error('Could not determine total number of questions.');
    return [];
  }

  console.log(`Found ${total} questions. Starting extraction...`);

  clickSidebarQuestion(1);
  await waitForQuestionLoad(1);

  for (let i = 1; i <= total; i++) {
    console.log(`Extracting question ${i} of ${total}...`);

    await expandAllExplanations();

    const q = extractCurrentQuestion();
    allQuestions.push(q);

    if (i < total) {
      clickNextButton();
      await waitForQuestionLoad(i + 1);
    }
  }

  console.log(`\nExtraction complete! ${allQuestions.length} questions collected.`);
  window.__ambossData = allQuestions;

  try {
    copy(JSON.stringify(allQuestions, null, 2));
    console.log('JSON automatically copied to clipboard!');
  } catch (e) {
    console.log('Data stored in window.__ambossData');
    console.log('Run: copy(JSON.stringify(window.__ambossData, null, 2))');
  }

  return allQuestions;
}

console.log('AMBOSS Extractor loaded. Run: extractAllQuestions()');
