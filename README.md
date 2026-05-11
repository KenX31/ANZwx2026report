# NZ Holiday Payment Report

Private Streamlit review app for the New Zealand holiday WeChat Pay analysis.

## Run Locally

```powershell
streamlit run app.py
```

The app requires an access password. Configure one of these Streamlit secrets before use:

```toml
NZ_REPORT_PASSWORD = "your-password"
```

or:

```toml
NZ_REPORT_PASSWORD_SHA256 = "sha256-hash"
```

For the Monica review password, use the SHA256 secret value shared separately.

## Deployment Notes

- Deploy as a private or controlled-access Streamlit app.
- Do not commit `.streamlit/secrets.toml`.
- This repository includes only reviewed aggregate report outputs under `data/processed`.
- Raw cloud exports, local workbooks, and merchant-level activation detail are excluded.
