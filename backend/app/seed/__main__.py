"""Command line: `python -m app.seed [--reset] [--seed N] [--allow-production]`."""
import argparse
import sys

from app.core.database import SessionLocal
from app.seed.generator import DEMO_ORG_NAME, DEMO_PASSWORD, DEMO_USERS
from app.seed.runner import DEFAULT_SEED, SeedError, seed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.seed", description="Create demo data for FleetMind.")
    p.add_argument("--reset", action="store_true", help="delete and recreate the demo organization (never touches other organizations)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed; the same seed gives the same data")
    p.add_argument("--allow-production", action="store_true", help="allow running when ENVIRONMENT=production")
    a = p.parse_args(argv)
    with SessionLocal() as db:
        try:
            result = seed(db, reset=a.reset, seed_number=a.seed, allow_production=a.allow_production)
        except SeedError as e:
            print(f"seed: {e}", file=sys.stderr)
            return 1
    if result["status"] == "exists":
        print(f"seed: '{DEMO_ORG_NAME}' already exists, nothing changed (use --reset to rebuild it).")
        return 0
    print(f"seed: {result['status']} '{DEMO_ORG_NAME}': " + ", ".join(f"{v} {k}" for k, v in result["counts"].items()))
    print("seed: sign in with any of these (password: " + DEMO_PASSWORD + ")")
    for u in DEMO_USERS:
        print(f"  {u['role_name']:<11} {u['email']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
