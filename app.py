import json
import os
import sqlite3
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, send_file, url_for


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "instance", "interviews.db")

load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

JOB_ROLES = [
    "Python Developer",
    "Java Developer",
    "Web Developer",
    "Data Analyst",
    "Django Developer",
    "Frontend Developer",
    "Software Tester",
]

EXPERIENCE_LEVELS = ["Fresher", "0-1 Year", "1-2 Years", "2+ Years"]
QUESTION_TYPES = ["Technical", "HR", "Mixed", "Scenario Based"]
QUESTION_COUNTS = [5, 10, 15]


def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interview_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_role TEXT NOT NULL,
                experience_level TEXT NOT NULL,
                question_type TEXT NOT NULL,
                question_count INTEGER NOT NULL,
                questions_json TEXT NOT NULL,
                provider TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def build_prompt(data):
    return f"""
Generate interview preparation questions.

Job role: {data['job_role']}
Experience level: {data['experience_level']}
Question type: {data['question_type']}
Number of questions: {data['question_count']}
Skills/notes: {data.get('skills') or 'Not provided'}

Return only valid JSON in this exact format:
[
  {{
    "category": "Technical or HR or Scenario",
    "difficulty": "Easy or Medium or Hard",
    "question": "Interview question",
    "sample_answer": "Simple fresher-friendly answer",
    "tip": "Short interview tip"
  }}
]

Rules:
- Questions must match the job role and experience level.
- Answers must be simple, practical, and interview-ready.
- Do not include markdown, comments, or extra text.
""".strip()


def clean_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def normalize_questions(raw_questions, expected_count):
    normalized = []
    for item in raw_questions[:expected_count]:
        question = str(item.get("question", "")).strip()
        sample_answer = str(item.get("sample_answer", "")).strip()
        if not question:
            continue
        normalized.append(
            {
                "category": str(item.get("category", "Interview")).strip() or "Interview",
                "difficulty": str(item.get("difficulty", "Easy")).strip() or "Easy",
                "question": question,
                "sample_answer": sample_answer or "Give a clear answer with one practical example.",
                "tip": str(item.get("tip", "Keep your answer short and confident.")).strip()
                or "Keep your answer short and confident.",
            }
        )
    return normalized


def generate_with_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate_with_openai(prompt):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key:
        return None

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": prompt},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("output_text"):
        return result["output_text"].strip()

    parts = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def fallback_questions(data):
    role = data["job_role"]
    qtype = data["question_type"]
    skills = data.get("skills", "").strip() or role
    base = [
        {
            "category": "HR",
            "difficulty": "Easy",
            "question": "Tell me about yourself.",
            "sample_answer": (
                f"I am a motivated fresher interested in {role}. I have learned {skills} "
                "and completed academic or practice projects to improve my practical skills."
            ),
            "tip": "Keep it under one minute and connect your answer to the role.",
        },
        {
            "category": "Technical",
            "difficulty": "Easy",
            "question": f"What are the basic skills required for a {role}?",
            "sample_answer": (
                f"A {role} should understand programming fundamentals, problem solving, "
                "database basics, debugging, and project development."
            ),
            "tip": "Mention skills you can explain with examples.",
        },
        {
            "category": "Technical",
            "difficulty": "Medium",
            "question": "How do you debug an error in your project?",
            "sample_answer": (
                "I first read the error message, identify the file or line causing the issue, "
                "check inputs and logic, test small parts, and then verify the fix."
            ),
            "tip": "Show a step-by-step method, not only the final answer.",
        },
        {
            "category": "Scenario",
            "difficulty": "Medium",
            "question": "What will you do if you are assigned a task you do not know?",
            "sample_answer": (
                "I will understand the requirement, break it into smaller parts, research the topic, "
                "try a basic solution, and ask for guidance if needed."
            ),
            "tip": "This shows learning attitude and ownership.",
        },
        {
            "category": "HR",
            "difficulty": "Easy",
            "question": "Why should we hire you?",
            "sample_answer": (
                f"As a fresher, I am ready to learn, adapt, and work sincerely. My knowledge of "
                f"{skills} and my project practice can help me contribute as a {role}."
            ),
            "tip": "Be confident but realistic.",
        },
    ]

    if qtype == "Technical":
        base = [item for item in base if item["category"] == "Technical"] + base
    elif qtype == "HR":
        base = [item for item in base if item["category"] == "HR"] + base
    elif qtype == "Scenario Based":
        base = [item for item in base if item["category"] == "Scenario"] + base

    output = []
    for index in range(data["question_count"]):
        item = dict(base[index % len(base)])
        output.append(item)
    return output


def generate_questions(data):
    prompt = build_prompt(data)
    preferred = os.environ.get("AI_PROVIDER", "fallback").lower()

    if preferred == "gemini":
        providers = [("Gemini", generate_with_gemini), ("OpenAI", generate_with_openai)]
    elif preferred == "openai":
        providers = [("OpenAI", generate_with_openai), ("Gemini", generate_with_gemini)]
    else:
        providers = [("Gemini", generate_with_gemini), ("OpenAI", generate_with_openai)]

    for name, generator in providers:
        try:
            raw = generator(prompt)
            if raw:
                questions = normalize_questions(clean_json_response(raw), data["question_count"])
                if questions:
                    return questions, name
        except Exception as exc:
            print(f"{name} generation failed: {exc}")

    return fallback_questions(data), "Local Demo Generator"


def save_set(data, questions, provider):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            """
            INSERT INTO interview_sets
            (job_role, experience_level, question_type, question_count, questions_json, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["job_role"],
                data["experience_level"],
                data["question_type"],
                len(questions),
                json.dumps(questions),
                provider,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        return cursor.lastrowid


def get_set(set_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM interview_sets WHERE id = ?", (set_id,)).fetchone()
        if row:
            row = dict(row)
            row["questions"] = json.loads(row["questions_json"])
        return row


def get_history():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            """
            SELECT id, job_role, experience_level, question_type, question_count, provider, created_at
            FROM interview_sets
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()


@app.route("/")
def index():
    return render_template(
        "index.html",
        job_roles=JOB_ROLES,
        experience_levels=EXPERIENCE_LEVELS,
        question_types=QUESTION_TYPES,
        question_counts=QUESTION_COUNTS,
        history=get_history(),
        form={},
    )


@app.route("/generate", methods=["POST"])
def generate():
    data = {
        "job_role": request.form.get("job_role", "").strip(),
        "experience_level": request.form.get("experience_level", "").strip(),
        "question_type": request.form.get("question_type", "").strip(),
        "question_count": int(request.form.get("question_count", 5)),
        "skills": request.form.get("skills", "").strip(),
    }

    errors = []
    if data["job_role"] not in JOB_ROLES:
        errors.append("Please select a valid job role.")
    if data["experience_level"] not in EXPERIENCE_LEVELS:
        errors.append("Please select a valid experience level.")
    if data["question_type"] not in QUESTION_TYPES:
        errors.append("Please select a valid question type.")
    if data["question_count"] not in QUESTION_COUNTS:
        errors.append("Please select a valid question count.")

    if errors:
        return render_template(
            "index.html",
            job_roles=JOB_ROLES,
            experience_levels=EXPERIENCE_LEVELS,
            question_types=QUESTION_TYPES,
            question_counts=QUESTION_COUNTS,
            history=get_history(),
            form=data,
            errors=errors,
        )

    questions, provider = generate_questions(data)
    set_id = save_set(data, questions, provider)
    return redirect(url_for("interview_set", set_id=set_id))


@app.route("/set/<int:set_id>")
def interview_set(set_id):
    item = get_set(set_id)
    if not item:
        return redirect(url_for("index"))
    return render_template("set.html", item=item)


@app.route("/download/<int:set_id>")
def download_set(set_id):
    item = get_set(set_id)
    if not item:
        return redirect(url_for("index"))

    lines = [
        "AI Interview Question Generator",
        f"Role: {item['job_role']}",
        f"Experience: {item['experience_level']}",
        f"Question Type: {item['question_type']}",
        "",
    ]
    for index, question in enumerate(item["questions"], start=1):
        lines.append(f"{index}. {question['question']}")
        lines.append(f"Category: {question['category']} | Difficulty: {question['difficulty']}")
        lines.append(f"Sample Answer: {question['sample_answer']}")
        lines.append(f"Tip: {question['tip']}")
        lines.append("")

    filename = os.path.join(BASE_DIR, "instance", f"interview_set_{set_id}.txt")
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    return send_file(filename, as_attachment=True, download_name=f"interview_set_{set_id}.txt")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5003)
