#!/usr/bin/env python3
"""UWorld to Anki: one-command extraction and deck generation."""

import json
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

from playwright.sync_api import sync_playwright

from generate_deck import generate_all_decks
from summarize import summarize_new_questions

EXTRACT_JS_PATH = os.path.join(os.path.dirname(__file__), "extract_all_questions.js")
QUESTION_BANK_PATH = os.path.join(os.path.dirname(__file__), "data", "question_bank.json")

UWORLD_REVIEW_URL_PATTERN = "apps.uworld.com"


def load_question_bank():
    """Load existing question bank from disk, returning (list, set of IDs)."""
    if os.path.exists(QUESTION_BANK_PATH):
        with open(QUESTION_BANK_PATH) as f:
            questions = json.load(f)
        seen_ids = {q["questionId"] for q in questions if q.get("questionId")}
        return questions, seen_ids
    return [], set()


def save_question_bank(questions):
    """Save question bank to disk."""
    os.makedirs(os.path.dirname(QUESTION_BANK_PATH), exist_ok=True)
    with open(QUESTION_BANK_PATH, "w") as f:
        json.dump(questions, f, indent=2)


def load_extraction_script():
    with open(EXTRACT_JS_PATH) as f:
        js = f.read()
    # Remove the console.log at the end and the extractAllQuestions() call instructions
    # We'll call extractAllQuestions() ourselves
    return js


def extract_from_page(page):
    """Inject the extraction script and run it, returning the question data."""
    js_code = load_extraction_script()
    # Inject the script functions, then call extractAllQuestions()
    result = page.evaluate(f"""
        async () => {{
            {js_code}
            return await extractAllQuestions();
        }}
    """)
    return result or []


def ensure_chromium():
    """Install Playwright Chromium if not already present."""
    try:
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
    except Exception:
        print("Installing Chromium browser (first run only)...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )
        print()


def main():
    all_questions, seen_ids = load_question_bank()

    print("UWorld to Anki Extractor")
    print("=" * 40)
    if all_questions:
        print(f"Question bank loaded: {len(all_questions)} existing questions")
    print()

    ensure_chromium()

    new_this_session = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.goto("https://uworld.com/app/index.html#/login/")

        print("Browser opened. Log in to UWorld and navigate to a test review page.")
        print()

        while True:
            print("[e] Extract current review page")
            print("[d] Done, generate deck")
            choice = input("> ").strip().lower()

            if choice == "e":
                if UWORLD_REVIEW_URL_PATTERN not in page.url:
                    print(f"  Current URL: {page.url}")
                    print("  Does not look like a UWorld page. Navigate to a test review page first.")
                    print()
                    continue

                print("  Extracting questions...", end="", flush=True)
                try:
                    questions = extract_from_page(page)
                except Exception as e:
                    print(f"\n  Error during extraction: {e}")
                    print("  Make sure you are on a test review page (not the test list).")
                    print()
                    continue

                if not questions:
                    print("\n  No questions found. Make sure you are on a test review page.")
                    print()
                    continue

                new_count = 0
                for q in questions:
                    qid = q.get("questionId", "")
                    if qid and qid not in seen_ids:
                        seen_ids.add(qid)
                        all_questions.append(q)
                        new_count += 1

                skipped = len(questions) - new_count
                new_this_session += new_count
                print(f" {len(questions)} found, {new_count} new.")
                if skipped > 0:
                    print(f"  ({skipped} duplicates skipped)")
                print(f"  Total in bank: {len(all_questions)} ({new_this_session} new this session)")

                save_question_bank(all_questions)
                print()

            elif choice == "d":
                if not all_questions:
                    print("  No questions in the bank. Extract some first.")
                    print()
                    continue
                break

            else:
                print("  Invalid choice. Enter 'e' or 'd'.")
                print()

        browser.close()

    # AI summarization (if API key is set)
    print()
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("Running AI summarization...")
        summarized_count = summarize_new_questions(all_questions)
        if summarized_count > 0:
            save_question_bank(all_questions)
    else:
        print("ANTHROPIC_API_KEY not set. Skipping AI summarization.")
        print("  Set it to generate condensed cards: export ANTHROPIC_API_KEY=your-key")

    # Generate decks
    print()
    print("Generating decks...")
    generate_all_decks(all_questions)

    print()
    print(f"Done! {len(all_questions)} questions ({new_this_session} new this session).")
    print()
    print("Import into Anki: File > Import > select the .apkg files in output/")


if __name__ == "__main__":
    main()
