# Security notes

- Configuration is read from environment variables; `.env` is ignored and `.env.example` has no secrets.
- API models reject unknown fields and constrain amounts, rates and terms.
- PDF uploads require `application/pdf`, have an 8 MB ceiling and are processed in memory.
- Responses avoid sensitive logging and never ask for Aadhaar, PAN, banking passwords or API keys.
- CORS defaults to the local dashboard origin and is configurable with `CORS_ORIGINS`.

Authentication, persistent document storage, malware scanning and OCR sandboxing are deferred until the product needs persisted user data. They must be added before accepting production-sensitive documents.
