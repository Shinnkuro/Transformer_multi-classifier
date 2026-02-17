#!/usr/bin/env python3
"""Merge parquet parts for CMS samples.

Given an input root directory that contains one subdirectory per sample, this script
finds all `.parquet` files in each sample folder and merges them into one output
file per sample.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def ensure_pyarrow_installed() -> None:
    """Validate pyarrow dependency and print actionable guidance when missing."""
    try:
        import pyarrow  # noqa: F401
    except ModuleNotFoundError:
        print(
            "Error: missing required dependency 'pyarrow'.\n"
            "Please install it before running this script, for example:\n"
            "  pip install pyarrow\n"
            "or (recommended on clusters with conda/mamba):\n"
            "  conda install -c conda-forge pyarrow",
            file=sys.stderr,
        )
        raise SystemExit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge .parquet files per sample directory. "
            "Each direct child folder under --samples-path is treated as one sample."
        )
    )
    parser.add_argument(
        "--samples-path",
        required=True,
        type=Path,
        help="Path containing sample directories (e.g. dy_M-50_MiNNLO, ttjets_dl, ...).",
    )
    parser.add_argument(
        "--output-path",
        required=True,
        type=Path,
        help="Output directory where merged parquet files will be written.",
    )
    parser.add_argument(
        "--pattern",
        default="*.parquet",
        help="Glob pattern for parquet part files inside each sample directory.",
    )
    parser.add_argument(
        "--suffix",
        default="_merged.parquet",
        help="Suffix to append to each sample folder name for output file naming.",
    )
    return parser.parse_args()


def ask_overwrite(path: Path) -> bool:
    while True:
        reply = input(f"Output file already exists: {path}\nOverwrite? [y/N]: ").strip().lower()
        if reply in {"y", "yes"}:
            return True
        if reply in {"", "n", "no"}:
            return False
        print("Please answer 'y' (yes) or 'n' (no).")


def merge_one_sample(sample_dir: Path, output_file: Path, pattern: str) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    parquet_files = sorted(sample_dir.glob(pattern))
    if not parquet_files:
        print(f"[skip] {sample_dir.name}: no files matching '{pattern}'")
        return

    writer = None
    total_rows = 0

    try:
        for parquet_file in parquet_files:
            parquet_obj = pq.ParquetFile(parquet_file)
            for batch in parquet_obj.iter_batches():
                table = pa.Table.from_batches([batch])
                if writer is None:
                    writer = pq.ParquetWriter(output_file, table.schema)
                writer.write_table(table)
                total_rows += table.num_rows
    finally:
        if writer is not None:
            writer.close()

    print(
        f"[ok] {sample_dir.name}: merged {len(parquet_files)} files, "
        f"{total_rows} rows -> {output_file}"
    )


def main() -> int:
    args = parse_args()
    ensure_pyarrow_installed()

    samples_path = args.samples_path.expanduser().resolve()
    output_path = args.output_path.expanduser().resolve()

    if not samples_path.exists() or not samples_path.is_dir():
        print(f"Error: samples path is not a valid directory: {samples_path}", file=sys.stderr)
        return 1

    output_path.mkdir(parents=True, exist_ok=True)

    sample_dirs = sorted(d for d in samples_path.iterdir() if d.is_dir())
    if not sample_dirs:
        print(f"Error: no sample folders found in {samples_path}", file=sys.stderr)
        return 1

    for sample_dir in sample_dirs:
        output_file = output_path / f"{sample_dir.name}{args.suffix}"
        if output_file.exists() and not ask_overwrite(output_file):
            print(f"Stopped: output exists and overwrite declined: {output_file}")
            return 0
        merge_one_sample(sample_dir, output_file, args.pattern)

    print("All done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
