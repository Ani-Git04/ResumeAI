import re
from typing import Iterable, List, Set


def normalize_skill(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    # Basic canonicalization
    s = s.replace("Java Script", "JavaScript")
    s = s.replace("Node js", "Node.js").replace("NodeJs", "Node.js").replace("NodeJS", "Node.js")
    s = s.replace("PostgreSQL", "Postgres")
    s = s.replace("Amazon Web Services", "AWS")
    return s


def uniq_skills(skills: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for sk in skills or []:
        n = normalize_skill(sk)
        key = n.lower()
        if not n or key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def compute_missing(jd_skills: List[str], resume_skills: List[str]) -> List[str]:
    resume_set = {s.lower() for s in resume_skills or []}
    missing = [s for s in (jd_skills or []) if s.lower() not in resume_set]
    return uniq_skills(missing)
