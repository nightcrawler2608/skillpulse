"""Tech-stack check: does the job's core stack overlap with yours at all?

Why: in the Precision@5 trial a Python/Django fresher was shown Java Spring jobs and a
Node.js developer was shown Java jobs. The text is about the same thing ("backend
developer"), so meaning-similarity likes them, but you couldn't apply.

Rule, in plain language:
- "Core stack" = programming languages and main frameworks (Python, Java, React,
  Django, .NET, ...). Generic items (REST APIs, HTML, Microservices, ...) don't count.
- Frameworks imply their language (Django -> Python, Spring Boot -> Java,
  React -> JavaScript), and JavaScript/TypeScript count as one family.
- If the job lists core-stack skills, you have a core stack, and the two share
  NOTHING, the fit is multiplied by 0.6. If either side lists no stack, no change.
"""

from __future__ import annotations

from functools import lru_cache

from skillpulse.nlp.taxonomy import default_skills

STACK_CATEGORIES = {"language", "web_backend", "web_frontend", "mobile"}
GENERIC = {"REST APIs", "Microservices", "Responsive Design", "HTML", "CSS", "GraphQL", "gRPC",
           "RabbitMQ", "Webpack", "Sass", "Bootstrap", "Tailwind CSS", "jQuery", "Redux"}
IMPLIES = {
    "Django": "Python", "Flask": "Python", "FastAPI": "Python",
    "Spring Boot": "Java", "Spring Framework": "Java", "Hibernate": "Java", "Kotlin": "Java",
    "React": "JavaScript", "Angular": "JavaScript", "Vue.js": "JavaScript",
    "Next.js": "JavaScript", "Node.js": "JavaScript", "Express.js": "JavaScript",
    "TypeScript": "JavaScript", "React Native": "JavaScript",
    ".NET": "C#", "ASP.NET": "C#", "Laravel": "PHP", "Ruby on Rails": "Ruby",
    "Flutter": "Dart",
}
MISMATCH_FACTOR = 0.6


@lru_cache(maxsize=1)
def stack_skills() -> frozenset[str]:
    return frozenset(s.name for s in default_skills()
                     if s.category in STACK_CATEGORIES and s.name not in GENERIC)


def core_stack(skills: set[str]) -> set[str]:
    core = set(skills) & stack_skills()
    return core | {IMPLIES[s] for s in core if s in IMPLIES}


def stack_factor(job_skills: set[str], user_skills: set[str]) -> float:
    job, user = core_stack(job_skills), core_stack(user_skills)
    if not job or not user or job & user:
        return 1.0
    return MISMATCH_FACTOR
