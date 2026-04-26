import json
import os
import sys
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
import io


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT, "utils"))

from groq_client import best_effort_json, groq_chat  # noqa: E402
from prompts import (  # noqa: E402
    EVAL_SYSTEM,
    EVAL_USER,
    LEARNING_PLAN_SYSTEM,
    LEARNING_PLAN_USER,
    QUESTION_GEN_SYSTEM,
    QUESTION_GEN_USER,
    SKILL_EXTRACTION_SYSTEM,
    SKILL_EXTRACTION_USER,
)
from skill_parser import compute_missing, uniq_skills  # noqa: E402


load_dotenv(os.path.join(ROOT, ".env"))

st.set_page_config(page_title="AI Skill Agent", page_icon="🧠", layout="wide")


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: List[str] = []
    for p in reader.pages:
        parts.append(p.extract_text() or "")
    return "\n".join(parts).strip()


st.title("AI Skill Assessment & Learning Plan")
st.caption("Upload a resume + paste a job description. Get skill gaps, an interview, scores, and a learning roadmap.")

with st.sidebar:
    st.subheader("Setup")
    st.write("Add `GROQ_API_KEY` in Streamlit Secrets or your environment.")
    st.code('GROQ_API_KEY="..."', language="toml")
    st.divider()
    st.subheader("Controls")
    max_skills = st.slider("Max skills to interview", min_value=3, max_value=10, value=8)
    st.caption("Fewer skills = faster + more focused.")

col1, col2 = st.columns(2)
with col1:
    resume = st.file_uploader("Resume (PDF)", type=["pdf"])
with col2:
    jd = st.text_area("Job description", height=220, placeholder="Paste the job description here…")

run = st.button("Run assessment", type="primary", use_container_width=True)

if resume and jd and run:
    if not os.environ.get("GROQ_API_KEY"):
        st.error("Missing GROQ_API_KEY. Add it to Streamlit Secrets or your environment.")
        st.stop()

    with st.spinner("Parsing resume…"):
        resume_bytes = resume.read()
        resume_text = extract_pdf_text(resume_bytes)

    with st.spinner("Extracting skills…"):
        raw = groq_chat(
            messages=[
                {"role": "system", "content": SKILL_EXTRACTION_SYSTEM},
                {
                    "role": "user",
                    "content": SKILL_EXTRACTION_USER.format(
                        resume_text=resume_text[:12000], job_description=jd[:12000]
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        data = best_effort_json(raw) or {}
        resume_skills = uniq_skills(data.get("resume_skills") or [])
        jd_skills = uniq_skills(data.get("jd_skills") or [])
        missing = compute_missing(jd_skills, resume_skills)

    st.subheader("Skills")
    c1, c2, c3 = st.columns(3)
    c1.metric("Resume skills", len(resume_skills))
    c2.metric("JD skills", len(jd_skills))
    c3.metric("Missing skills", len(missing))
    st.write("**Missing skills**:", ", ".join(missing[:24]) or "None")

    interview_skills = (missing + jd_skills)[: max_skills]

    with st.spinner("Generating questions…"):
        raw = groq_chat(
            messages=[
                {"role": "system", "content": QUESTION_GEN_SYSTEM},
                {"role": "user", "content": QUESTION_GEN_USER.format(skills_json=json.dumps(interview_skills))},
            ],
            temperature=0.25,
            max_tokens=1400,
        )
        qdata = best_effort_json(raw) or {}
        questions_by_skill: Dict[str, List[str]] = qdata.get("questions_by_skill") or {}

    st.subheader("Interview")
    st.info("Answer what you can. Then click “Evaluate” to get scores + roadmap.")

    qa_by_skill = {}
    for sk in interview_skills:
        st.markdown(f"### {sk}")
        qs = questions_by_skill.get(sk) or []
        qa_by_skill[sk] = []
        for i in range(3):
            q = (qs[i] if i < len(qs) else f"Explain your experience with {sk}.").strip()
            a = st.text_area(f"Q{i+1}: {q}", key=f"{sk}-{i}", height=90)
            if a.strip():
                qa_by_skill[sk].append({"q": q, "a": a.strip()})

    if st.button("Evaluate", type="primary"):
        with st.spinner("Scoring answers…"):
            raw = groq_chat(
                messages=[
                    {"role": "system", "content": EVAL_SYSTEM},
                    {"role": "user", "content": EVAL_USER.format(job_description=jd[:12000], qa_json=json.dumps(qa_by_skill)[:16000])},
                ],
                temperature=0.15,
                max_tokens=1400,
            )
            scored = best_effort_json(raw) or {}
            skills = scored.get("skills") or []

        st.subheader("Scores")
        st.json(skills)

        with st.spinner("Generating learning plan…"):
            md = groq_chat(
                messages=[
                    {"role": "system", "content": LEARNING_PLAN_SYSTEM},
                    {
                        "role": "user",
                        "content": LEARNING_PLAN_USER.format(
                            job_description=jd[:12000],
                            missing_skills_json=json.dumps(missing),
                            scored_skills_json=json.dumps(skills)[:12000],
                        ),
                    },
                ],
                temperature=0.25,
                max_tokens=1900,
            ).strip()

        st.subheader("Learning roadmap")
        st.markdown(md)

st.divider()
st.caption("Deployed with Streamlit. The `frontend/` + `api/` folders are kept in the repo for reference.")

