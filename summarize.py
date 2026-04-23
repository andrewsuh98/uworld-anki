#!/usr/bin/env python3
"""AI summarization of UWorld questions using Claude API."""

import json
import os

import anthropic

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "summarize.md")
MODEL = "claude-sonnet-4-6"


def load_prompt():
    with open(PROMPT_PATH) as f:
        return f.read()


def build_user_message(question):
    """Build the user message from a question object."""
    choices_text = "\n".join(
        f"  {c['letter']}. {c['text']}" for c in question.get("choices", [])
    )
    return f"""## Question
{question.get("questionPlain", "")}

## Answer Choices
{choices_text}

## Correct Answer
{question.get("correctAnswer", "")}

## Educational Objective
{question.get("educationalObjective", "")}

## Explanation
{question.get("explanationPlain", "")}"""


def summarize_question(client, question, system_prompt):
    """Call Claude API to summarize a single question."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": build_user_message(question)}],
    )

    text = response.content[0].text.strip()

    # Parse JSON from response (handle markdown code blocks)
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(text)


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
    for q in to_summarize:
        qid = q.get("questionId", "?")
        topic = q.get("topic", "?")
        print(f"    [{count + 1}/{len(to_summarize)}] Q{qid} ({topic})...", end="", flush=True)
        try:
            summary = summarize_question(client, q, system_prompt)
            q["aiSummary"] = summary
            count += 1
            print(" done.")
        except Exception as e:
            print(f" error: {e}")
            q["aiSummary"] = None

    print(f"  Summarized {count} of {len(to_summarize)} questions.")
    return count
