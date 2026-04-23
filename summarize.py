#!/usr/bin/env python3
"""AI summarization of UWorld questions using Claude API."""

import json
import os
import time

import anthropic

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "summarize.md")
MODEL = "claude-haiku-4-5"
MAX_RETRIES = 3


def load_prompt():
    with open(PROMPT_PATH) as f:
        return f.read()


def build_user_message(question):
    """Build the user message from a question object."""
    choices_text = "\n".join(
        f"  {c['letter']}. {c['text']}" for c in question.get("choices", [])
    )

    # Use HTML versions to preserve tables and image references
    question_content = question.get("questionHtml", "") or question.get(
        "questionPlain", ""
    )
    explanation_content = question.get("explanationHtml", "") or question.get(
        "explanationPlain", ""
    )

    return f"""## Question
{question_content}

## Answer Choices
{choices_text}

## Correct Answer
{question.get("correctAnswer", "")}

## Educational Objective
{question.get("educationalObjective", "")}

## Explanation
{explanation_content}"""


def parse_response(text):
    """Parse JSON from Claude's response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def summarize_question(client, question, system_prompt):
    """Call Claude API to summarize a single question, with retry on rate limit."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": build_user_message(question)}],
            )
            return parse_response(response.content[0].text)
        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES - 1:
                wait = 15 * (attempt + 1)
                print(f" rate limited, waiting {wait}s...", end="", flush=True)
                time.sleep(wait)
            else:
                raise


def summarize_new_questions(questions):
    """Summarize questions that don't have aiSummary yet. Returns count of newly summarized."""
    to_summarize = [q for q in questions if q.get("aiSummary") is None]

    if not to_summarize:
        print("  All questions already summarized.")
        return 0

    print(f"  Summarizing {len(to_summarize)} new questions...")

    client = anthropic.Anthropic()
    system_prompt = load_prompt()

    count = 0
    for i, q in enumerate(to_summarize):
        qid = q.get("questionId", "?")
        topic = q.get("topic", "?")
        print(
            f"    [{i + 1}/{len(to_summarize)}] Q{qid} ({topic})...", end="", flush=True
        )
        try:
            summary = summarize_question(client, q, system_prompt)
            q["aiSummary"] = summary
            count += 1
            print(" done.")
        except Exception as e:
            print(f" error: {e}")

    print(f"  Summarized {count} of {len(to_summarize)} questions.")
    return count


if __name__ == "__main__":
    import argparse
    from run import load_dotenv, load_question_bank, save_question_bank

    parser = argparse.ArgumentParser(
        description="Summarize UWorld questions with Claude AI"
    )
    parser.add_argument(
        "--resummarize",
        action="store_true",
        help="Clear existing summaries and re-summarize all questions",
    )
    args = parser.parse_args()

    load_dotenv()
    questions, _ = load_question_bank()

    if args.resummarize:
        cleared = sum(1 for q in questions if q.get("aiSummary") is not None)
        for q in questions:
            q["aiSummary"] = None
        print(f"  Cleared {cleared} existing summaries.")

    count = summarize_new_questions(questions)
    if count > 0:
        save_question_bank(questions)
        print("Question bank saved.")
    print(
        f"Total: {len(questions)} questions, {sum(1 for q in questions if q.get('aiSummary'))} with AI summaries."
    )
