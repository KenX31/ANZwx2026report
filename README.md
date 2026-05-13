# ANZ Holiday Payment Report

Private Streamlit review app for the ANZ holiday WeChat Pay analysis.

## Run Locally

```powershell
streamlit run app.py
```

The app requires an access key. Configure one of these Streamlit secrets before use:

```toml
NZ_REPORT_ACCESS = "your-access-key"
```

or:

```toml
NZ_REPORT_ACCESS_DIGEST = "sha256-hash"
```

For Monica review, prefer the SHA256 digest secret value shared separately. The app still accepts the earlier deployment secret names for compatibility, but new deployments should use the neutral access-key names above.

## Data In This Review Build

- `data/processed/`: reviewed NZ aggregate report outputs.
- `data/processed_au_partial/`: AU aggregate preview outputs from 01a, 02, and 03 only.

The AU page is a partial preview. It supports period overview, daily trend, active-user signal, and material signal. City, industry, top merchant, same-store, and merchant activation views require the complete AU merchant-day detail export before they are enabled.

## Deployment Notes

- Deploy as a private or controlled-access Streamlit app.
- Do not commit `.streamlit/secrets.toml`.
- Do not deploy raw exports, local workbooks, or merchant-day detail files.
