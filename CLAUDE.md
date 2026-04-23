# CLAUDE.md

## Project Overview

Extract UWorld USMLE test review questions and generate Anki flashcard decks. Users run `uv run run.py`, log into UWorld in the Playwright browser, navigate to review pages, and extract questions interactively. The question bank accumulates across sessions.

## Tech Stack

- Python 3.10+, managed by uv (pyproject.toml, not requirements.txt)
- Playwright for browser automation
- genanki for Anki .apkg generation
- Anthropic SDK for AI summarization (optional, requires ANTHROPIC_API_KEY in .env)
- Browser-side extraction via injected JavaScript

## Project Structure

- `run.py` - Main entry point. Interactive loop: browser launch, extraction, AI summarization, deck generation. Loads `.env` for API key.
- `generate_deck.py` - Anki deck generation. Full deck and condensed deck models, card templates, CSS, image processing, tag building. Also runnable standalone: `uv run python generate_deck.py`
- `summarize.py` - AI summarization using Claude API. Loads prompt from `prompts/summarize.md`, processes only questions without existing `aiSummary` field.
- `prompts/summarize.md` - Editable prompt template for Claude. Controls the condensed card format.
- `extract_all_questions.js` - Injected into UWorld pages via Playwright. Navigates through questions and extracts DOM content.
- `data/question_bank.json` - Persistent question bank. Accumulates across sessions, deduplicated by question ID. Stores AI summaries alongside raw data.
- `output/` - Generated .apkg files (full deck and condensed deck).
- `media/` - Downloaded images, deduplicated by content hash.

## Key Design Decisions

- Question bank is the single source of truth. New extractions append to it; deck generation always reads the full bank.
- AI summaries are stored in the question bank (`aiSummary` field). Only questions with `aiSummary: null` are sent to the API, so re-runs don't re-summarize.
- Images are downloaded in Python (not browser JS) because CORS blocks cross-subdomain fetches on UWorld.
- Stable model/deck IDs are hardcoded so re-importing into Anki updates cards instead of creating duplicates. Full deck and condensed deck use separate IDs.
- Card front has no hints (no percentages, no correct markers, no topic). Topic is a tag only.

## Running

- `uv run run.py` - Full workflow (browser + extraction + deck generation)
- `uv run python generate_deck.py` - Regenerate deck from existing question bank without opening a browser

## Conventions

- No emojis
- Use straight quotes, never curly quotes
- Don't touch pyproject.toml dependencies directly; use `uv add` / `uv remove`
