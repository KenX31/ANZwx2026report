# ANZ Holiday Payment Report

Private Streamlit review app for the ANZ holiday WeChat Pay analysis.

The public app repository contains code and synthetic sample data only. Real
processed report data is loaded server-side from the private data repository:

```text
https://github.com/KenX31/anzdata.git
```

## Run Locally

For a UI smoke test without real data:

```powershell
$env:DATA_BACKEND = "sample"
$env:NZ_REPORT_ACCESS = "local-dev"
streamlit run app.py
```

For real data, configure `.streamlit/secrets.toml` locally or Streamlit Cloud
secrets:

```toml
NZ_REPORT_ACCESS_DIGEST = "sha256-hash"

DATA_BACKEND = "github_private"
DATA_GITHUB_TOKEN = "github_pat_read_only"
DATA_GITHUB_REPO = "KenX31/anzdata"
DATA_GITHUB_REF = "main"
DATA_PROJECT = "anz-labour-day-2026"
DATA_VERSION = "2026-05-13-au-core-v3"
```

The app also accepts `NZ_REPORT_ACCESS = "plain-access-key"` for local testing,
but deployments should prefer `NZ_REPORT_ACCESS_DIGEST`.

## Private Data Layout

The private data repository is organized by project:

```text
projects/
  anz-labour-day-2026/
    manifest.json
    processed/
      summary_kpis.csv
      daily_trend.csv
      region_summary.csv
      industry_summary.csv
      industry_period_summary.csv
      period_catalog.csv
      period_daily.csv
      period_summary.csv
      merchant_activation_summary.csv
      top_merchants.csv
      top_merchants_by_txn.csv
      top_merchants_by_frequency.csv
    processed_au/
      summary_kpis.csv
      daily_trend.csv
      region_summary.csv
      industry_summary.csv
      industry_period_summary.csv
      period_catalog.csv
      period_daily.csv
      period_summary.csv
      merchant_activation_summary.csv
      merchant_activation_detail.csv
      top_merchants.csv
      top_merchants_by_txn.csv
      top_merchants_by_frequency.csv
    processed_au_partial/
      summary_kpis.csv
      daily_trend.csv
      period_catalog.csv
      period_daily.csv
      period_summary.csv
      material_summary.csv
      material_period_summary.csv
      partial_status.csv
```

To reuse the app for another project with the same schema, add a new
`projects/{project_id}/` directory to the private data repo and change
`DATA_PROJECT` in Streamlit secrets.

## Data Safety Rules

- Do not commit real `data/processed/`, `data/processed_au_partial/`,
  `data/raw/`, workbooks, or cloud exports to this public repository.
- Do not commit `.streamlit/secrets.toml`.
- Keep real top merchant outputs only in the private data repository.
- Keep `data/sample/` synthetic; it is only for UI smoke tests.
- Removing data from the latest commit is not enough if it was already committed.
  Rewrite Git history before treating the public repo as clean.

## Deployment Notes

1. Push code changes to the public app repository.
2. Push real data to the private `KenX31/anzdata` repository.
3. In Streamlit Cloud, set the secrets shown above.
4. Share the Streamlit URL and report password. Viewers do not need GitHub
   access, tokens, local files, or setup steps.
