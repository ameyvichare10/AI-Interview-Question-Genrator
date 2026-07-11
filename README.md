# AI Interview Question Generator

AI Interview Question Generator is a beginner-friendly Python Flask project that creates interview questions, sample answers, and preparation tips based on job role, experience level, and question type.

## Features

- Generate HR, technical, mixed, and scenario-based interview questions
- Select job role and experience level
- Generate sample answers and interview tips
- Save generated question sets in SQLite
- View practice history
- Download question set as `.txt`
- Works in demo mode without an API key
- Optional Gemini API or OpenAI API support

## Tools Used

- Python
- Flask
- SQLite
- HTML
- CSS
- Bootstrap
- JavaScript
- Gemini API or OpenAI API optional

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional: create a `.env` file from `.env.example` and add your API key.

```bash
copy .env.example .env
```

For demo mode, keep:

```env
AI_PROVIDER=fallback
```

4. Run the project:

```bash
python app.py
```

5. Open:

```text
http://127.0.0.1:5003
```

## Resume Description

**AI Interview Question Generator | Python, Flask, SQLite, Bootstrap, Generative AI**

Developed a Flask-based AI Interview Question Generator that creates HR, technical, mixed, and scenario-based interview questions based on selected job role and experience level. Implemented sample answers, interview tips, SQLite history, download feature, and optional Gemini/OpenAI API integration with local demo fallback.
