#!/usr/bin/env python3
"""Merge parquet parts for CMS samples."""

from __future__ import annotations

import argparse
import sys
import time
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
    parser.add_argument("--samples-path", required=True, type=Path)
    parser.add_argument("--output-path", required=True, type=Path)
    parser.add_argument("--pattern", default="*.parquet")
    parser.add_argument("--suffix", default="_merged.parquet")
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry count for opening/reading each parquet file after transient I/O errors.",
    )
    parser.add_argument(
        "--retry-wait",
        type=float,
        default=1.0,
        help="Seconds to wait between retries for a failed parquet file read.",
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


def read_parquet_with_retry(parquet_file: Path, retries: int, retry_wait: float):
    """Return a ParquetFile object with retries for transient I/O failures."""
    import pyarrow.parquet as pq

    attempts = retries + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return pq.ParquetFile(parquet_file)
        except OSError as err:
            last_error = err
            if attempt < attempts:
                print(
                    f"[warn] failed to read {parquet_file} (attempt {attempt}/{attempts}): {err}. "
                    f"Retrying in {retry_wait:.1f}s..."
                )
                time.sleep(retry_wait)

    raise RuntimeError(f"Failed to read parquet file {parquet_file}: {last_error}")


def merge_one_sample(sample_dir: Path, output_file: Path, pattern: str, retries: int, retry_wait: float) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    parquet_files = sorted(sample_dir.glob(pattern))
    if not parquet_files:
        raise RuntimeError(f"No parquet files matching '{pattern}' under {sample_dir}")

    writer = None
    total_rows = 0

    try:
        for parquet_file in parquet_files:
            parquet_obj = read_parquet_with_retry(parquet_file, retries=retries, retry_wait=retry_wait)
            for batch in parquet_obj.iter_batches():
                table = pa.Table.from_batches([batch])
                if writer is None:
                    writer = pq.ParquetWriter(output_file, table.schema)
                writer.write_table(table)
                total_rows += table.num_rows
    except Exception:
        if writer is not None:
            writer.close()
        if output_file.exists():
            output_file.unlink()
        raise
    else:
        if writer is not None:
            writer.close()

    print(
        f"[done] {sample_dir.name}: merged {len(parquet_files)} files, "
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

    print(f"[info] detected {len(sample_dirs)} sample folders under {samples_path}")

    for idx, sample_dir in enumerate(sample_dirs, start=1):
        print(f"[info] ({idx}/{len(sample_dirs)}) start merging: {sample_dir.name}")
        output_file = output_path / f"{sample_dir.name}{args.suffix}"
        if output_file.exists() and not ask_overwrite(output_file):
            print(f"Stopped: output exists and overwrite declined: {output_file}")
            return 0

        try:
            merge_one_sample(
                sample_dir,
                output_file,
                args.pattern,
                args.retries,
                args.retry_wait,
            )
        except RuntimeError as err:
            print(f"Error while merging {sample_dir.name}: {err}", file=sys.stderr)
            return 1

    print("All done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
