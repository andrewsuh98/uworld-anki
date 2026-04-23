#!/usr/bin/env python3
"""Convert UWorld extracted JSON into an Anki .apkg deck."""

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.request

import genanki

# Stable IDs (generated once, never change these)
MODEL_ID = 1607392319
DECK_ID = 2044571848

CSS = """\
.uworld-card {
  font-family: -apple-system, system-ui, "Segoe UI", sans-serif;
  max-width: 720px;
  margin: 0 auto;
  line-height: 1.6;
  font-size: 15px;
  color: #1a1a1a;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 14px;
}
td, th {
  border: 1px solid #ccc;
  padding: 6px 10px;
  vertical-align: top;
}
tr:first-child td {
  background: #eef2ff;
  font-weight: bold;
  text-align: center;
}
.topic-tag {
  display: inline-block;
  background: #e8eaf6;
  color: #283593;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
  margin-bottom: 10px;
}
.choices {
  margin: 14px 0;
}
.choice-item {
  padding: 4px 0;
}
.choice-correct {
  color: #2e7d32;
  font-weight: bold;
}
.correct-answer {
  color: #2e7d32;
  font-size: 1.2em;
  font-weight: bold;
  margin: 12px 0;
}
.your-answer {
  margin: 6px 0;
  font-size: 0.95em;
}
.your-answer.incorrect {
  color: #c62828;
}
.your-answer.correct {
  color: #2e7d32;
}
.edu-objective {
  background: #f5f5f5;
  padding: 12px;
  border-left: 3px solid #1976d2;
  margin: 14px 0;
}
.explanation {
  margin-top: 10px;
  line-height: 1.6;
}
.topic-name {
  font-size: 1.4em;
  font-weight: bold;
  color: #1565c0;
  text-align: center;
  margin: 24px 0;
}
.topic-prompt {
  text-align: center;
  color: #666;
  font-style: italic;
  margin-top: 20px;
}
details summary {
  cursor: pointer;
  color: #1976d2;
  font-weight: bold;
  margin: 12px 0;
}
img {
  max-width: 100%;
  height: auto;
}

/* Dark mode */
.night_mode .uworld-card {
  color: #e0e0e0;
}
.night_mode tr:first-child td {
  background: #2a3050;
}
.night_mode td, .night_mode th {
  border-color: #555;
}
.night_mode .topic-tag {
  background: #2a3050;
  color: #90a4f8;
}
.night_mode .choice-correct {
  color: #66bb6a;
}
.night_mode .correct-answer {
  color: #66bb6a;
}
.night_mode .your-answer.incorrect {
  color: #ef5350;
}
.night_mode .your-answer.correct {
  color: #66bb6a;
}
.night_mode .edu-objective {
  background: #1e1e2e;
  border-left-color: #5c8fd6;
}
.night_mode .topic-name {
  color: #64b5f6;
}
.night_mode .topic-prompt {
  color: #aaa;
}
"""

CARD1_FRONT = """\
<div class="uworld-card">
  <div class="question-stem">{{QuestionHTML}}</div>
  <div class="choices">{{ChoicesFront}}</div>
</div>
"""

CARD1_BACK = """\
<div class="uworld-card">
  <div><span class="topic-tag">{{Topic}}</span></div>
  <div class="question-stem">{{QuestionHTML}}</div>
  <div class="choices">{{ChoicesBack}}</div>
  <hr>
  <div class="correct-answer">{{CorrectAnswer}}</div>
  <div class="your-answer {{WasCorrectClass}}">You answered: {{YourAnswer}}</div>
  <div class="edu-objective">
    <strong>Educational Objective:</strong><br>{{EducationalObjective}}
  </div>
  <div class="explanation-header"><strong>Full Explanation</strong></div>
  <div class="explanation">{{ExplanationHTML}}</div>
</div>
"""

CARD2_FRONT = """\
<div class="uworld-card">
  <div class="topic-prompt">What are the key features of:</div>
  <div class="topic-name">{{Topic}}</div>
</div>
"""

CARD2_BACK = """\
<div class="uworld-card">
  <div class="topic-prompt">What are the key features of:</div>
  <div class="topic-name">{{Topic}}</div>
  <hr>
  <div>{{SummaryTable}}</div>
  <div class="edu-objective">{{EducationalObjective}}</div>
</div>
"""


def create_model():
    return genanki.Model(
        MODEL_ID,
        "UWorld USMLE",
        fields=[
            {"name": "QuestionID"},
            {"name": "QuestionHTML"},
            {"name": "ChoicesFront"},
            {"name": "ChoicesBack"},
            {"name": "CorrectAnswer"},
            {"name": "EducationalObjective"},
            {"name": "ExplanationHTML"},
            {"name": "SummaryTable"},
            {"name": "Topic"},
            {"name": "YourAnswer"},
            {"name": "WasCorrectClass"},
        ],
        templates=[
            {
                "name": "Question -> Answer",
                "qfmt": CARD1_FRONT,
                "afmt": CARD1_BACK,
            },
            {
                "name": "Topic Review",
                "qfmt": CARD2_FRONT,
                "afmt": CARD2_BACK,
            },
        ],
        css=CSS,
    )


class UWorldNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for("uworld", self.fields[0])


def process_images(html, media_files, media_dir):
    """Extract images from HTML (base64 or URL), save to files, rewrite src attributes."""

    def save_image(image_bytes, ext):
        """Save image bytes to media dir, return filename."""
        if ext == "jpeg":
            ext = "jpg"
        content_hash = hashlib.md5(image_bytes).hexdigest()[:12]
        filename = f"uworld_{content_hash}.{ext}"
        filepath = os.path.join(media_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "wb") as f:
                f.write(image_bytes)
        media_files.add(filepath)
        return filename

    def replace_data_uri(match):
        full_tag = match.group(0)
        data_uri = match.group(1)
        uri_match = re.match(r"data:image/(\w+);base64,(.+)", data_uri, re.DOTALL)
        if not uri_match:
            return full_tag
        try:
            image_bytes = base64.b64decode(uri_match.group(2))
        except Exception:
            return full_tag
        filename = save_image(image_bytes, uri_match.group(1))
        return full_tag.replace(data_uri, filename)

    def replace_url(match):
        full_tag = match.group(0)
        url = match.group(1)
        if url.startswith("data:") or not url.startswith("http"):
            return full_tag
        ext = url.rsplit(".", 1)[-1].lower() if "." in url else "jpg"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                image_bytes = resp.read()
            filename = save_image(image_bytes, ext)
            return full_tag.replace(url, filename)
        except Exception as e:
            print(f"  Warning: could not download {url}: {e}")
            return full_tag

    # First pass: handle base64 data URIs
    html = re.sub(r'<img[^>]+src="(data:image/[^"]+)"', replace_data_uri, html)
    # Second pass: handle remote URLs
    html = re.sub(r'<img[^>]+src="(https?://[^"]+)"', replace_url, html)
    return html


def extract_summary_table(explanation_html):
    """Extract the first table from the explanation (usually the summary table)."""
    match = re.search(r"<table[^>]*>.*?</table>", explanation_html, re.DOTALL)
    return match.group(0) if match else ""


def format_choices_front(choices):
    """Format answer choices for the card front (no hints)."""
    lines = []
    for c in choices:
        lines.append(
            f'<div class="choice-item"><b>{c["letter"]}.</b> {c["text"]}</div>'
        )
    return "\n".join(lines)


def format_choices_back(choices):
    """Format answer choices for the card back (with percentages and correct marker)."""
    lines = []
    for c in choices:
        pct = f" ({c['percentage']}%)" if c.get("percentage") is not None else ""
        css_class = "choice-item choice-correct" if c["isCorrect"] else "choice-item"
        mark = " [correct]" if c["isCorrect"] else ""
        lines.append(
            f'<div class="{css_class}"><b>{c["letter"]}.</b> {c["text"]}{pct}{mark}</div>'
        )
    return "\n".join(lines)


def build_tags(question):
    """Build Anki tags from question metadata."""
    tags = []
    for field, prefix in [("subject", "Subject"), ("system", "System"), ("topic", "Topic")]:
        value = question.get(field, "")
        if value:
            sanitized = value.replace(" ", "_").replace("/", "::")
            tags.append(f"{prefix}::{sanitized}")
    if not question.get("wasCorrect", True):
        tags.append("Missed")
    return tags


def main():
    parser = argparse.ArgumentParser(description="Generate Anki deck from UWorld JSON")
    parser.add_argument(
        "--input", default="questions.json", help="Path to extracted JSON"
    )
    parser.add_argument(
        "--output", default="output/uworld_deck.apkg", help="Output .apkg path"
    )
    parser.add_argument(
        "--deck-name", default="UWorld USMLE", help="Anki deck name"
    )
    args = parser.parse_args()

    with open(args.input) as f:
        questions = json.load(f)

    model = create_model()
    deck = genanki.Deck(DECK_ID, args.deck_name)
    media_files = set()
    media_dir = "media"
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    for q in questions:
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
    package.write_to_file(args.output)

    print(f"Generated {len(questions)} notes ({len(questions)} Question cards + topic review cards where summary tables exist)")
    print(f"Images embedded: {len(media_files)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
