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
3. In the terminal, press `r` to extract the current test block.
4. Navigate to another review page and press `r` again. Repeat as many times as you want.
5. Press `d` when done. The script downloads images, generates the deck, and saves it.

```
[r] Extract current review page
[d] Done, generate deck
> r

  Extracting questions... 10 found, 10 new.
  Total questions collected: 10

[r] Extract current review page
[d] Done, generate deck
> d

Downloading images and generating deck...

Done! 10 notes created, 1 images embedded.
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

Each question generates up to two cards:

**Card 1: Question -> Answer**
- Front: clinical vignette + answer choices (no hints)
- Back: correct answer, your answer, educational objective, full explanation

**Card 2: Topic Review** (only when a summary table exists)
- Front: "What are the key features of: [Topic]?"
- Back: summary table + educational objective

## Tags

Cards are tagged for filtering in Anki:
- `Subject::Surgery`, `Subject::Internal_Medicine`, etc.
- `System::Gastrointestinal_&_Nutrition`, etc.
- `Topic::Autoimmune_hepatitis`, etc.
- `Missed` for questions you got wrong

## Re-importing

Questions are deduplicated by their UWorld question ID. Re-importing the same test block updates existing cards rather than creating duplicates.
