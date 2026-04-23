#!/usr/bin/env python3
"""UWorld to Anki: one-command extraction and deck generation."""

import os
import subprocess
import sys

from playwright.sync_api import sync_playwright

from generate_deck import (
    DECK_ID,
    UWorldNote,
    build_tags,
    create_model,
    extract_summary_table,
    format_choices_back,
    format_choices_front,
    process_images,
)
import genanki

EXTRACT_JS_PATH = os.path.join(os.path.dirname(__file__), "extract_all_questions.js")

UWORLD_REVIEW_URL_PATTERN = "apps.uworld.com"


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


def generate_deck(all_questions, output_path="output/uworld_deck.apkg", deck_name="UWorld USMLE"):
    """Generate an Anki .apkg from collected questions."""
    model = create_model()
    deck = genanki.Deck(DECK_ID, deck_name)
    media_files = set()
    media_dir = "media"
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    for q in all_questions:
        question_html = process_images(q.get("questionHtml", ""), media_files, media_dir)
        explanation_html = process_images(q.get("explanationHtml", ""), media_files, media_dir)
        summary_table = extract_summary_table(explanation_html)
        choices_front = format_choices_front(q.get("choices", []))
        choices_back = format_choices_back(q.get("choices", []))
        tags = build_tags(q)

        correct_answer = q.get("correctAnswer", "")
        your_answer = q.get("selectedAnswer", "") or "N/A"
        was_correct_class = "correct" if q.get("wasCorrect", True) else "incorrect"

        note = UWorldNote(
            model=model,
            fields=[
                q.get("questionId", ""),
                question_html,
                choices_front,
                choices_back,
                correct_answer,
                q.get("educationalObjective", ""),
                explanation_html,
                summary_table,
                q.get("topic", ""),
                your_answer,
                was_correct_class,
            ],
            tags=tags,
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    package.media_files = list(media_files)
    package.write_to_file(output_path)

    return len(media_files)


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
    all_questions = []
    seen_ids = set()

    print("UWorld to Anki Extractor")
    print("=" * 40)
    print()

    ensure_chromium()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.goto("https://apps.uworld.com")

        print("Browser opened. Log in to UWorld and navigate to a test review page.")
        print()

        while True:
            print("[r] Extract current review page")
            print("[d] Done, generate deck")
            choice = input("> ").strip().lower()

            if choice == "r":
                # Check that the page is on UWorld
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

                # Deduplicate by question ID
                new_count = 0
                for q in questions:
                    qid = q.get("questionId", "")
                    if qid and qid not in seen_ids:
                        seen_ids.add(qid)
                        all_questions.append(q)
                        new_count += 1

                skipped = len(questions) - new_count
                print(f" {len(questions)} found, {new_count} new.")
                if skipped > 0:
                    print(f"  ({skipped} duplicates skipped)")
                print(f"  Total questions collected: {len(all_questions)}")
                print()

            elif choice == "d":
                if not all_questions:
                    print("  No questions collected yet. Extract some first.")
                    print()
                    continue
                break

            else:
                print("  Invalid choice. Enter 'r' or 'd'.")
                print()

        browser.close()

    # Generate the deck
    print()
    print("Downloading images and generating deck...")
    output_path = "output/uworld_deck.apkg"
    image_count = generate_deck(all_questions, output_path)

    print()
    print(f"Done! {len(all_questions)} notes created, {image_count} images embedded.")
    print(f"Saved to: {output_path}")
    print()
    print("Import into Anki: File > Import > select the .apkg file")


if __name__ == "__main__":
    main()
