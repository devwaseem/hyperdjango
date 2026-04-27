from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    website_dir = script_dir.parent
    source_dir = website_dir.parent / "docs"
    target_dir = website_dir / "docs"

    if not source_dir.exists():
        raise FileNotFoundError(
            f"Source docs directory not found: {source_dir}"
        )

    if target_dir.exists():
        shutil.rmtree(target_dir)

    shutil.copytree(source_dir, target_dir)
    print(f"Synced docs from {source_dir} to {target_dir}")


if __name__ == "__main__":
    main()
