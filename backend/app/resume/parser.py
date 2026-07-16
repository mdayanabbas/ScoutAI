from dataclasses import dataclass, field
import re


SECTION_HEADINGS = {
    "summary": ("summary", "profile", "professional summary"),
    "skills": ("skills", "technical skills", "core skills"),
    "projects": ("projects", "selected projects"),
    "experience": ("experience", "work experience", "employment"),
    "education": ("education",),
    "certifications": ("certifications", "certificates"),
    "links": ("links", "publications", "achievements"),
}

TECH_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript", "ts"),
    "FastAPI": ("fastapi",),
    "Flask": ("flask",),
    "Django": ("django",),
    "React": ("react",),
    "Next.js": ("next.js", "nextjs"),
    "Node.js": ("node.js", "nodejs"),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "MongoDB": ("mongodb",),
    "Redis": ("redis",),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure",),
    "GCP": ("gcp", "google cloud"),
    "Git": ("git",),
    "GitHub": ("github",),
    "SQLAlchemy": ("sqlalchemy",),
    "Pydantic": ("pydantic",),
    "LangChain": ("langchain",),
    "LlamaIndex": ("llamaindex", "llama index"),
    "OpenAI": ("openai",),
    "Gemini": ("gemini",),
    "Claude": ("claude",),
    "Groq": ("groq",),
    "LLMs": ("llm", "llms", "large language model", "large language models"),
    "Machine Learning": ("machine learning", "ml"),
    "Deep Learning": ("deep learning",),
    "NLP": ("nlp", "natural language processing"),
    "RAG": ("rag", "retrieval augmented generation"),
    "Vector Databases": ("vector database", "vector databases"),
    "Pinecone": ("pinecone",),
    "FAISS": ("faiss",),
    "Chroma": ("chroma",),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "PyTorch": ("pytorch",),
    "TensorFlow": ("tensorflow",),
}


@dataclass
class ResumeParsedData:
    summary: dict | None = None
    skills: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    certifications: list[dict] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ResumeParser:
    def parse(self, raw_text: str) -> ResumeParsedData:
        text = normalize_resume_text(raw_text)
        sections = split_sections(text)
        technologies = detect_technologies(text)
        skills = sorted(set(extract_list_items(sections.get("skills", "")) + technologies))
        links = extract_links(text) + extract_list_items(sections.get("links", ""))
        return ResumeParsedData(
            summary={"text": first_nonempty(sections.get("summary"), text[:700])},
            skills=skills,
            technologies=technologies,
            projects=section_entries(sections.get("projects", "")),
            experience=section_entries(sections.get("experience", "")),
            education=section_entries(sections.get("education", "")),
            certifications=section_entries(sections.get("certifications", "")),
            links=dedupe([item for item in links if item]),
        )


def normalize_resume_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def split_sections(text: str) -> dict[str, str]:
    heading_to_key = {
        heading: key for key, headings in SECTION_HEADINGS.items() for heading in headings
    }
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        cleaned = line.strip().strip(":").lower()
        if cleaned in heading_to_key:
            current = heading_to_key[cleaned]
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def detect_technologies(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for label, aliases in TECH_ALIASES.items():
        if any(has_token(lowered, alias) for alias in aliases):
            found.append(label)
    return found


def has_token(text: str, token: str) -> bool:
    escaped = re.escape(token.lower())
    if token.lower() in {"c", "c++", "java", "javascript", "react"}:
        return bool(re.search(rf"(?<![\w+#.-]){escaped}(?![\w+#.-])", text))
    return bool(re.search(rf"(?<![\w+#]){escaped}(?![\w+#])", text))


def extract_list_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        for part in re.split(r"[,\u2022;|]", line):
            item = part.strip(" -\t")
            if 1 < len(item) <= 80:
                items.append(item)
    return dedupe(items)


def section_entries(text: str) -> list[dict]:
    entries = []
    for item in extract_list_items(text):
        entries.append({"title": item, "text": item})
    return entries[:20]


def extract_links(text: str) -> list[str]:
    return re.findall(r"https?://[^\s)]+|(?:github|linkedin)\.com/[^\s)]+", text, flags=re.I)


def first_nonempty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
