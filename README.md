# NZ Holiday Payment Report

Private Streamlit review app for the New Zealand holiday WeChat Pay analysis.

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

## Deployment Notes

- Deploy as a private or controlled-access Streamlit app.
- Do not commit `.streamlit/secrets.toml`.
- This repository includes only reviewed aggregate report outputs under `data/processed`.
- Raw cloud exports, local workbooks, and merchant-level activation detail are excluded.
