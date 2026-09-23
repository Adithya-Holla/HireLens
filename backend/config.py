import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# Load .env from the project root, regardless of the working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Create a .env file in the project root with "
        "GROQ_API_KEY=your_key (local), or set it as an environment variable on your host."
    )

MODEL = "openai/gpt-oss-120b"
RESUME_FOLDER = PROJECT_ROOT / "resumes"
REQUEST_DELAY_SECONDS = 5

# Fallback number of top candidates when the user just presses Enter at the prompt.
DEFAULT_TOP_N = 2

client = Groq(api_key=API_KEY)
