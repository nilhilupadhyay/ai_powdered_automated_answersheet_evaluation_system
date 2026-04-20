from fastapi import FastAPI

from app.api.capture import router as capture_router
from app.api.grading import router as grading_router
from app.api.sheets import router as sheets_router
from app.core.config import settings
from app.db.session import Base, engine


app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(sheets_router, prefix="/api/v1/sheets", tags=["sheets"])
app.include_router(capture_router, prefix="/api/v1/capture", tags=["capture"])
app.include_router(grading_router, prefix="/api/v1/grading", tags=["grading"])


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
