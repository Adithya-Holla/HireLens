def top_candidates(all_results: list[dict], n: int) -> list[dict]:
    """Return the n best candidates, sorted by score (descending)."""
    ranked = sorted(all_results, key=lambda x: x["score"], reverse=True)
    return ranked[:n]


def print_rankings(all_results: list[dict], n: int) -> None:
    print(f"\nTop {n} Candidates:")
    for candidate in top_candidates(all_results, n):
        print(f"Name: {candidate['name']}, Score: {candidate['score']}")
        print(f"Details: {candidate['details']}\n")
