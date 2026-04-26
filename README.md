# AI Skill Assessment & Personalized Learning Plan Agent

A production-style AI SaaS web app that:

- Parses a resume (PDF) → extracts text
- Extracts skills from resume + job description
- Interviews the user conversationally (ChatGPT-style UI)
- Scores proficiency per skill (0–10 + level)
- Detects skill gaps (JD vs resume)
- Generates a personalized learning roadmap with free resources

**LLM**: Groq API (`llama3-70b-8192`)  
**Backend**: Vercel Python Serverless Functions  
**Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` + FAISS (in-memory)  
**Frontend**: Vanilla JS + TailwindCSS (glassmorphism, gradients, animations)

---

## Architecture (high-level)

- **Frontend** (`frontend/`)
  - Uploads a PDF resume (converted to Base64 in-browser)
  - Sends Base64 PDF to `POST /api/parse_resume`
  - Sends extracted resume text + job description to `POST /api/extract_skills`
  - Requests 3 questions per skill from `POST /api/generate_questions`
  - Runs an interview loop; after each answer calls `POST /api/chat` for a short interviewer response
  - Sends all Q/A to `POST /api/evaluate_answers`
  - Generates a Markdown roadmap via `POST /api/learning_plan`
  - Renders a radar chart (Chart.js) and roadmap Markdown (`marked`)

- **Backend** (`api/`)
  - Each file exports `handler(request)` and returns **JSON only**
  - Uses a small Groq wrapper in `utils/groq_client.py`
  - Uses prompts in `utils/prompts.py`

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
├── vercel.json
├── README.md
└── .env.example
```

---

## Environment variables

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

### 2) Run locally with Vercel dev (recommended)

Install the Vercel CLI and run:

```bash
vercel dev
```

Then open the app in your browser (Vercel dev prints the local URL).

### Optional: Run the local Streamlit runner

This is a lightweight local UI for testing prompts without the premium frontend.

```bash
pip install streamlit
streamlit run app_local/streamlit_app.py
```

---

## Deploy to Vercel

1. Push the `AI-Skill-Agent/` folder to a GitHub repo (or import it directly).
2. In Vercel:
   - **Framework Preset**: Other
   - **Root Directory**: `AI-Skill-Agent`
   - Add environment variable:
     - `GROQ_API_KEY`
3. Deploy.

The app routes:

- Frontend: `/`
- API: `/api/*`

---

## API reference (JSON only)

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

- **Job description**: paste any SWE/ML/Full-stack role JD.
- **Resume**: upload a PDF resume.

---

## Notes

- This project is designed for **serverless** usage: the app does not store persistent session state on the backend.
- For best UX and reliability, keep resumes under ~8MB.
