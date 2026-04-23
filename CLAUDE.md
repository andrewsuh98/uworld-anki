# CLAUDE.md

## Project Overview

Extract UWorld USMLE test review questions and generate Anki flashcard decks. Users run `uv run run.py`, log into UWorld in the Playwright browser, navigate to review pages, and extract questions interactively. The question bank accumulates across sessions.

## Tech Stack

- Python 3.10+, managed by uv (pyproject.toml, not requirements.txt)
- Playwright for browser automation
- genanki for Anki .apkg generation
- Browser-side extraction via injected JavaScript

## Project Structure

- `run.py` - Main entry point. Interactive loop: browser launch, extraction, deck generation.
- `generate_deck.py` - Anki deck generation. Card templates, CSS, image processing, tag building. Also runnable standalone: `uv run python generate_deck.py`
- `extract_all_questions.js` - Injected into UWorld pages via Playwright. Navigates through questions and extracts DOM content.
- `data/question_bank.json` - Persistent question bank. Accumulates across sessions, deduplicated by question ID.
- `output/` - Generated .apkg files.
- `media/` - Downloaded images, deduplicated by content hash.

## Key Design Decisions

- Question bank is the single source of truth. New extractions append to it; deck generation always reads the full bank.
- Images are downloaded in Python (not browser JS) because CORS blocks cross-subdomain fetches on UWorld.
- Stable model/deck IDs are hardcoded so re-importing into Anki updates cards instead of creating duplicates.
- Card front has no hints (no percentages, no correct markers, no topic). Topic is a tag only.

## Running

- `uv run run.py` - Full workflow (browser + extraction + deck generation)
- `uv run python generate_deck.py` - Regenerate deck from existing question bank without opening a browser

## Conventions

- No emojis
- Use straight quotes, never curly quotes
- Don't touch pyproject.toml dependencies directly; use `uv add` / `uv remove`
