from fastapi import FastAPI

app = FastAPI(
    title="LoanWise AI",
    description="AI-powered loan decision support platform",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "LoanWise AI API is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }