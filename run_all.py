"""
Ejecuta todos los scrapers + scoring en secuencia.
Uso: python run_all.py
"""
import importlib
import sys
import traceback


SCRAPERS = [
    "scraper_toyota",
    "scraper_renault",
    "scraper_nissan",
    "scraper_ford",
    "scraper_honda",
    "scraper_vw",
    "scraper_scania",
    "scraper_stellantis",
]


def main() -> None:
    failed: list[str] = []

    for name in SCRAPERS:
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print(f"{'=' * 60}")
        try:
            mod = importlib.import_module(name)
            mod.main()
        except Exception:
            traceback.print_exc()
            failed.append(name)

    print(f"\n{'=' * 60}")
    print("  scoring")
    print(f"{'=' * 60}")
    try:
        import scoring
        scoring.main()
    except Exception:
        traceback.print_exc()
        failed.append("scoring")

    print(f"\n{'=' * 60}")
    if failed:
        print(f"  ERRORES en: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("  Todo OK")


if __name__ == "__main__":
    main()
