from pydantic import BaseModel


class JobD(BaseModel):
    role: str
    required_skills: list[str]
    preferred_skills: list[str]
    education_requirement: list[str]
    experience_level: float | None
    responsibilities: list[str]


class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    duration: float | None = None
    description: str | None = None
    skills: list[str] | None = None


class Resume(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    total_experience: float | None = None

    education: list[str] = []
    experience: list[Experience] = []
    skills: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []


class MatchResult(BaseModel):
    score: float
    details: dict
