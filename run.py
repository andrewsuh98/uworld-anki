#!/usr/bin/env python3
"""UWorld/AMBOSS to Anki: one-command extraction and deck generation."""

import json
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

from playwright.sync_api import sync_playwright

from generate_deck import generate_all_decks
from summarize import summarize_new_questions

BASE_DIR = os.path.dirname(__file__)

PLATFORMS = {
    "uworld": {
        "name": "UWorld",
        "login_url": "https://uworld.com/app/index.html#/login/",
        "url_pattern": "apps.uworld.com",
        "extract_js": os.path.join(BASE_DIR, "extract_uworld_questions.js"),
        "question_bank": os.path.join(BASE_DIR, "data", "uworld_question_bank.json"),
    },
    "amboss": {
        "name": "AMBOSS",
        "login_url": "https://next.amboss.com/us",
        "url_pattern": "next.amboss.com",
        "extract_js": os.path.join(BASE_DIR, "extract_amboss_questions.js"),
        "question_bank": os.path.join(BASE_DIR, "data", "amboss_question_bank.json"),
    },
}

QUESTION_BANK_PATH = PLATFORMS["uworld"]["question_bank"]


def load_question_bank(path=None):
    """Load existing question bank from disk, returning (list, set of IDs)."""
    path = path or QUESTION_BANK_PATH
    if os.path.exists(path):
        with open(path) as f:
            questions = json.load(f)
        seen_ids = {q["questionId"] for q in questions if q.get("questionId")}
        return questions, seen_ids
    return [], set()


def save_question_bank(questions, path=None):
    """Save question bank to disk."""
    path = path or QUESTION_BANK_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(questions, f, indent=2)


def load_extraction_script(path):
    with open(path) as f:
        return f.read()


def extract_from_page(page, extract_js_path):
    """Inject the extraction script and run it, returning the question data."""
    js_code = load_extraction_script(extract_js_path)
    # 5 min timeout: extraction navigates through all questions sequentially
    page.set_default_timeout(300_000)
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


def select_platform():
    """Prompt the user to choose a platform."""
    print("Select platform:")
    print("  [1] UWorld")
    print("  [2] AMBOSS")
    while True:
        choice = input("> ").strip()
        if choice == "1":
            return PLATFORMS["uworld"]
        if choice == "2":
            return PLATFORMS["amboss"]
        print("  Enter 1 or 2.")


def main():
    print("QBank to Anki Extractor")
    print("=" * 40)
    print()

    platform = select_platform()
    platform_name = platform["name"]
    bank_path = platform["question_bank"]

    all_questions, seen_ids = load_question_bank(bank_path)
    if all_questions:
        print(f"{platform_name} question bank: {len(all_questions)} existing questions")
    print()

    ensure_chromium()

    new_this_session = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.goto(platform["login_url"])

        print(f"Browser opened. Log in to {platform_name} and navigate to a review page.")
        print()

        while True:
            print("[e] Extract current review page")
            print("[d] Done, generate deck")
            choice = input("> ").strip().lower()

            if choice == "e":
                current_url = page.evaluate("window.location.href")
                if platform["url_pattern"] not in current_url:
                    print(f"  Current URL: {current_url}")
                    print(f"  Does not look like a {platform_name} page. Navigate to a review page first.")
                    print()
                    continue

                print("  Extracting questions...", end="", flush=True)
                try:
                    questions = extract_from_page(page, platform["extract_js"])
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

                save_question_bank(all_questions, bank_path)
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

    # Determine platform key for deck generation
    platform_key = "amboss" if platform_name == "AMBOSS" else "uworld"

    # AI summarization (if API key is set)
    print()
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("Running AI summarization...")
        summarized_count = summarize_new_questions(all_questions)
        if summarized_count > 0:
            save_question_bank(all_questions, bank_path)
    else:
        print("ANTHROPIC_API_KEY not set. Skipping AI summarization.")
        print("  Set it to generate condensed cards: export ANTHROPIC_API_KEY=your-key")

    # Generate decks
    print()
    print("Generating decks...")
    generate_all_decks(all_questions, platform=platform_key)

    print()
    print(f"Done! {len(all_questions)} questions ({new_this_session} new this session).")
    print()
    print("Import into Anki: File > Import > select the .apkg files in output/")


if __name__ == "__main__":
    main()
