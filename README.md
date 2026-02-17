# Transformer multi-classifier helpers

## Merge CMS sample parquet files

Added `merge_parquet_samples.py` to merge parquet part-files for each sample folder.

### What it does
- Treats each subfolder under `--samples-path` as one sample.
- Merges all matching parquet files in that subfolder into one output parquet.
- Creates `--output-path` automatically if it does not exist.
- If target output file already exists, asks whether to overwrite.
  - `y/yes`: overwrite.
  - `n/no` (or Enter): stop the program.

### Example
```bash
python merge_parquet_samples.py \
  --samples-path /path/to/CMS_samples \
  --output-path /path/to/merged_output
```

Output files are named:
- `<sample_folder_name>_merged.parquet`

You can customize naming suffix and input file pattern:
```bash
python merge_parquet_samples.py \
  --samples-path /path/to/CMS_samples \
  --output-path /path/to/merged_output \
  --pattern 'part*.parquet' \
  --suffix '_all.parquet'
```
