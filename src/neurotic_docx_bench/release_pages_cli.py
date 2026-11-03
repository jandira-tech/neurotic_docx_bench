"""The release-page staging worker used by ``bench release-pages``.

The plain ndb environment does not carry the bench-ops contract package
(#134).  The CLI therefore launches this module in a small overlay with the
reviewed bench-ops commit.  The module itself is also useful on its own:

    uv run --with 'bench-ops @ git+https://github.com/arthrod/bench-ops@<sha>' \\
        python -m neurotic_docx_bench.release_pages_cli 1.2.3 --root .
"""

from __future__ import annotations

import argparse
from pathlib import Path

from neurotic_docx_bench.release_pages import (
    DEFAULT_FILES_BASE,
    ReleasePageError,
    stage_release_pages,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release-pages",
        description="stage a release's shown pages and write its R2 upload plan (no upload)",
    )
    parser.add_argument("version", help="the jubarte release version, x.y.z")
    parser.add_argument("--root", type=Path, default=Path("."), help="the bench repository root")
    parser.add_argument("--out", type=Path, help="the staging root")
    parser.add_argument("--kind", choices=("convert", "redline", "both"), default="both")
    parser.add_argument("--limit", type=int, help="stage only the first N rows of each set")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument(
        "--vendor-root", type=Path, help="the vendor-refresh work directories' root"
    )
    parser.add_argument("--files-base", default=DEFAULT_FILES_BASE)
    args = parser.parse_args(argv)

    kinds = ("convert", "redline") if args.kind == "both" else (args.kind,)
    try:
        report = stage_release_pages(
            args.root,
            args.version,
            out=args.out,
            files_base=args.files_base,
            vendor_root=args.vendor_root,
            kinds=kinds,  # type: ignore[arg-type]
            limit=args.limit,
            jobs=args.jobs,
        )
    except (ReleasePageError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    print(
        f"release {args.version}: {report.rendered} lane(s), {report.pages} shown page(s), "
        f"{report.bytes / 1024 / 1024:.1f} MB"
    )
    print(f"  R2 plan: {report.plan_path} ({len(report.plan)} files; nothing uploaded)")
    print(f"  per-page scores: {report.page_scores.get('message', 'not recorded')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
