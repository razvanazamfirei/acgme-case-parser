# ML Training Workbench

Current ML workflow for procedure categorization.

Get interactive command overview and full CLI help:

```bash
python ml_training/workbench.py
```

## Install dependencies

```bash
uv sync --group ml
```

## One-command pipeline (recommended)

```bash
python ml_training/workbench.py run --total-sample 50000 --force
```

What this does:

- prepares data (unless `--skip-prepare`)
- splits into seen/unseen sets
- trains on seen split
- evaluates on unseen split

Default outputs:

- `ml_training_data/batch_prepared.csv`
- `ml_training_data/seen_train.csv`
- `ml_training_data/unseen_eval.csv`
- `ml_models/procedure_classifier.pkl`

## Review corrections

TUI mode (default):

```bash
python ml_training/workbench.py review --resume
```

Built-in review data path:

- `ml_training_data/unseen_eval_remaining.csv` (if it exists)
- otherwise `ml_training_data/unseen_eval.csv`

Classic prompt mode:

```bash
python ml_training/workbench.py review \
  --data ml_training_data/unseen_eval.csv \
  --ui classic
```

## Build airway/anesthesia review set

Generate a focused manual-review CSV for:

- double-lumen tube
- GA vs MAC
- oral vs nasal tube route

```bash
python ml_training/workbench.py airway-review-set --max-cases 600
```

Default output:

- `ml_training_data/airway_review_candidates.csv`

The generator scans the supervised CSV corpus, preserves available technique-level
airway note text, prioritizes likely thoracic/DLT cases, route-specific cases,
and GA/MAC inference cases, then emits blank label columns for manual review.

## Retrain with your overrides

After reviewing cases and writing `ml_training_data/review_labels.csv`, run:

```bash
python ml_training/workbench.py retrain --force
```

What this does:

- loads your overrides from `review_labels.csv`
- relabels matching rows in `seen_train.csv`
- promotes reviewed rows from `unseen_eval.csv` into retraining data
- upweights true correction overrides by a built-in `3x` multiplier
- writes:
  - `ml_training_data/seen_train_with_overrides.csv`
  - `ml_training_data/unseen_eval_remaining.csv`
- retrains the model and evaluates on the remaining unseen rows

## Common commands

Train only:

```bash
python ml_training/workbench.py train --force
```

Evaluate any CSV:

```bash
python ml_training/workbench.py evaluate \
  --model ml_models/procedure_classifier.pkl \
  --data ml_training_data/unseen_eval.csv
```

Evaluate against reviewed labels and report rule/ML/hybrid accuracy:

```bash
python ml_training/workbench.py evaluate \
  --data ml_training_data/review_labels.csv \
  --label-column human_category
```

Or use built-in default eval path:

```bash
python ml_training/workbench.py evaluate
```

Override the runtime hybrid threshold without editing code:

```bash
CASE_PARSER_ML_THRESHOLD=0.65 case-parser input.xlsx output.xlsx
```

Force inference-time sklearn estimators to use a specific `n_jobs` value:

```bash
CASE_PARSER_ML_INFERENCE_JOBS=1 case-parser input.xlsx output.xlsx
```

## Lower-level scripts (still supported)

- `ml_training/auto_train.py`: deterministic prepare/split/train/evaluate pipeline
- `ml_training/batch_prepare.py`: parallel data preparation + sampling
- `ml_training/train_optimized.py`: model training entrypoint
- `ml_training/evaluate.py`: batch evaluation entrypoint
