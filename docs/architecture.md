# Architecture

The MVP separates HTTP concerns from the financial domain:

`React + TypeScript → API client → FastAPI/Pydantic → financial domain`

`backend/app/financial` owns deterministic Decimal calculations and contains no FastAPI dependencies. `app/schemas.py` defines the external contracts and `app/main.py` maps requests to the domain engine. This keeps a future database, authentication layer and AI explanation provider from becoming calculation authorities.

The domain uses a `LoanType` enum with `car` and `home` values, while the UI exposes only the supported car-loan workflow. This allows home-loan inputs to be added later without replacing core loan models.

The app has no database in this MVP because it has no authentication or persistence requirement yet. When persistence is introduced, SQLAlchemy repositories should sit behind a service layer; migrations should be Alembic-managed and sensitive documents should be encrypted at rest.
