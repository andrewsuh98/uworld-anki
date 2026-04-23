# UWorld to Anki

Extract questions from UWorld USMLE test reviews and generate Anki flashcard decks.

## Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/):

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

That's the only prerequisite. `uv` handles Python, dependencies, and browser installation automatically.

## Usage

```
git clone <repo>
cd uworld-anki
uv run run.py
```

On first run, this will:
1. Install Python (if needed)
2. Install dependencies (genanki, playwright)
3. Download Chromium browser

Then the interactive workflow starts:

1. A browser window opens. Log in to your UWorld account.
2. Navigate to a completed test review page.
3. In the terminal, press `e` to extract the current test block.
4. Navigate to another review page and press `e` again. Repeat as many times as you want.
5. Press `d` when done. The script downloads images, generates the deck, and saves it.

```
[e] Extract current review page
[d] Done, generate deck
> e

  Extracting questions... 10 found, 10 new.
  Total in bank: 10 (10 new this session)

[e] Extract current review page
[d] Done, generate deck
> d

Downloading images and generating deck...

Done! 10 notes in deck (10 new this session), 1 images embedded.
Saved to: output/uworld_deck.apkg
```

Import `output/uworld_deck.apkg` into Anki via File > Import.

## What Gets Extracted

- Question stem (full clinical vignette with lab tables)
- All answer choices
- Correct answer and your selected answer
- Full explanation with summary tables and images
- Educational objective
- Metadata: subject, system, topic

## Flashcard Structure

Each question generates one card:

- Front: clinical vignette + answer choices (no hints)
- Back: correct answer, your answer, educational objective, full explanation

## Tags

Cards are tagged for filtering in Anki:
- `Subject::Surgery`, `Subject::Internal_Medicine`, etc.
- `System::Gastrointestinal_&_Nutrition`, etc.
- `Topic::Autoimmune_hepatitis`, etc.
- `Missed` for questions you got wrong

## Question Bank

Questions are saved to `data/question_bank.json` and accumulate across sessions. Each run only extracts new questions. The deck is always generated from the full bank.

To regenerate the deck without opening a browser:

```
uv run python generate_deck.py
```

## Re-importing

Questions are deduplicated by their UWorld question ID. Re-importing the same test block updates existing cards rather than creating duplicates.
