"""HireLens entry point.

Web app (default):   python main.py      then open http://127.0.0.1:8000
CLI:                 python -m backend.cli
"""

import uvicorn


def main() -> None:
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
