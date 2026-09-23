from pathlib import Path

from .config import DEFAULT_TOP_N, RESUME_FOLDER
from .file_readers import read_resume
from .pipeline import evaluate_candidates
from .reporting import print_rankings


def get_top_n() -> int:
    while True:
        raw = input(f"How many top candidates to report? [default {DEFAULT_TOP_N}]: ").strip()
        if not raw:
            return DEFAULT_TOP_N
        try:
            n = int(raw)
        except ValueError:
            n = 0
        if n >= 1:
            return n
        print("Please enter a positive integer.")


def main() -> None:
    top_n = get_top_n()

    if not RESUME_FOLDER.is_dir():
        raise SystemExit(f"Resume folder not found: {RESUME_FOLDER}")

    resumes = []
    for file_path in sorted(RESUME_FOLDER.iterdir()):
        if file_path.suffix.lower() in [".pdf", ".docx"]:
            print(f"Reading {file_path.name}...")
            resumes.append((file_path.name, read_resume(str(file_path))))

    if not resumes:
        raise SystemExit(f"No PDF/DOCX resumes found in {RESUME_FOLDER}")

    def progress(index: int, total: int, name: str) -> None:
        print(f"Evaluating {index}/{total}: {name}")

    top, all_results, errors = evaluate_candidates(resumes, "", top_n, progress=progress)

    for result in all_results:
        print("Score: ", result["score"])

    print_rankings(all_results, top_n)

    for error in errors:
        print(f"Error evaluating {error['name']}: {error['error']}")


if __name__ == "__main__":
    main()
