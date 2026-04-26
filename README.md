# AI Skill Assessment & Personalized Learning Plan Agent

An AI-powered skill assessment product that turns a **resume + job description** into:

- **Skill extraction** (resume vs JD)
- **Skill gap analysis** (what’s missing)
- **Interview questions** (3 per skill)
- **Skill scoring** (0–10 + level)
- **Personalized learning roadmap** (free-first resources + timelines)

### Tech

- **LLM**: Groq API — `llama3-70b-8192`
- **Deployed UI**: Streamlit (`app_local/streamlit_app.py`)
- **Web UI (included)**: Vanilla JS + Tailwind (`frontend/`)
- **Serverless API (included)**: Python handlers (`api/`)

---

## Architecture (high-level)

- **Streamlit (recommended deployment)**
  - Entrypoint: `app_local/streamlit_app.py`
  - Uses shared Groq client + prompts under `utils/`
  - Reads `GROQ_API_KEY` from Streamlit Secrets (recommended) or environment variables

- **Optional web frontend + API (kept in repo)**
  - `frontend/`: premium UI (chat experience, radar chart, markdown viewer)
  - `api/`: JSON-only serverless-style endpoints for the web UI

---

## Project structure

```
AI-Skill-Agent/
│
├── api/
│   ├── parse_resume.py
│   ├── extract_skills.py
│   ├── generate_questions.py
│   ├── evaluate_answers.py
│   ├── learning_plan.py
│   └── chat.py
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│
├── app_local/
│   └── streamlit_app.py
│
├── utils/
│   ├── groq_client.py
│   ├── skill_parser.py
│   ├── prompts.py
│   ├── embeddings.py
│   └── vector_store.py
│
├── requirements.txt
├── README.md
└── .env.example
```

---

## Environment variables

### Local `.env` (optional)

Create `.env` (for local dev) based on `.env.example`:

```bash
cp .env.example .env
```

Set:

```bash
GROQ_API_KEY=your_key_here
```

---

## Local development

### 1) Install dependencies

```bash
cd AI-Skill-Agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run locally with Streamlit

```bash
streamlit run app_local/streamlit_app.py
```

---

## Deploy to Streamlit Community Cloud

1. Go to Streamlit Community Cloud → **New app**
2. Select your GitHub repo and branch (`main`)
3. **Main file path**: `app_local/streamlit_app.py`
4. Add **Secrets**:

```toml
GROQ_API_KEY="your_key_here"
```

5. Click **Deploy**

---

## Troubleshooting (Streamlit)

### “Groq request failed”

Common causes:

- **Missing key**: ensure `GROQ_API_KEY` exists in **Streamlit Secrets**
- **Invalid/revoked key**: generate a new key in Groq and update Secrets
- **Rate limit / transient network**: reboot the app and try again

### Resume parsing returns empty text

- Some resumes are image-scans. `pypdf` extracts **text**, not OCR.
- Export your resume as a text-based PDF if possible.

---

## API reference (JSON only)

> Note: Streamlit deployment does not require these endpoints. They’re kept for the optional web UI.

### `POST /api/parse_resume`

Input:

```json
{ "resume_pdf_base64": "<base64>" }
```

Output:

```json
{ "resume_text": "..." }
```

### `POST /api/extract_skills`

Input:

```json
{ "resume_text": "...", "job_description": "..." }
```

Output:

```json
{ "resume_skills": [], "jd_skills": [], "missing_skills": [] }
```

### `POST /api/generate_questions`

Input:

```json
{ "skills": ["Python", "SQL"] }
```

Output:

```json
{ "questions_by_skill": { "Python": ["...","...","..."] } }
```

### `POST /api/chat`

Input:

```json
{
  "conversation": [{"role":"user|assistant","content":"..."}],
  "active_skill": "Python",
  "current_question": "..."
}
```

Output:

```json
{ "assistant_message": "..." }
```

### `POST /api/evaluate_answers`

Input:

```json
{
  "job_description": "...",
  "qa_by_skill": {
    "Python": [{"q":"...","a":"..."}]
  }
}
```

Output:

```json
{
  "skills": [
    { "skill": "Python", "score": 7, "level": "Intermediate", "rationale": "..." }
  ]
}
```

### `POST /api/learning_plan`

Input:

```json
{
  "job_description": "...",
  "missing_skills": ["Docker"],
  "scored_skills": [{ "skill": "Python", "score": 7, "level": "Intermediate" }]
}
```

Output:

```json
{ "learning_plan_markdown": "# Roadmap\n..." }
```

---

## Sample inputs

- **Job description**: paste any SWE/ML/Full-stack role JD (recommended: 6–20 bullet points)
- **Resume**: upload a PDF resume (text-based PDF works best)

---

## Sample outputs (expected)

- **Missing skills**: short list of skills present in the JD but not in the resume
- **Scores**: objects like `{ skill, score, level, rationale }`
- **Learning roadmap**: Markdown plan with priorities, time estimates, and free resources

---

## Notes

- Do **not** commit real API keys. Use Streamlit Secrets or a local `.env`.
- Keep resumes under ~8MB for reliability.
