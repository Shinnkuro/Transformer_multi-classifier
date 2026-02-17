# Transformer multi-classifier helpers

## Merge CMS sample parquet files

`merge_parquet_samples.py` merges parquet part-files for each sample folder.

### What it does
- Treats each subfolder under `--samples-path` as one sample.
- Merges all matching parquet files in that subfolder into one output parquet.
- Does **not** skip any parquet file: any unreadable/missing input causes the run to stop.
- Creates `--output-path` automatically if it does not exist.
- If target output file already exists, asks whether to overwrite.
  - `y/yes`: overwrite.
  - `n/no` (or Enter): stop the program.
- Prints runtime logs:
  - How many sample subfolders were detected.
  - Start message for each sample.
  - Completion message for each sample.

### Dependency
This script requires `pyarrow`:
```bash
pip install pyarrow
```
(Or on many HPC environments:)
```bash
conda install -c conda-forge pyarrow
```

### Example
```bash
python merge_parquet_samples.py \
  --samples-path /path/to/CMS_samples \
  --output-path /path/to/merged_output
```

Output files are named:
- `<sample_folder_name>_merged.parquet`

### For unstable filesystems
If you hit temporary I/O issues, you can increase retries (still no skipping):
```bash
python merge_parquet_samples.py \
  --samples-path /depot/cms/.../2017 \
  --output-path /depot/cms/.../2017_merged \
  --retries 5 \
  --retry-wait 2
```

### Optional arguments
- `--pattern 'part*.parquet'` : only match specific part-file names.
- `--suffix '_all.parquet'` : customize output naming.
- `--retries N` : retry times after first read failure for each file.
- `--retry-wait SECONDS` : waiting time between retries.
