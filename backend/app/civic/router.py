from fastapi import APIRouter

from app.civic.languages import LanguageRegistry, load_languages

router = APIRouter(prefix="/v1", tags=["civic"])


@router.get("/meta/languages", response_model=LanguageRegistry)
async def language_support() -> LanguageRegistry:
    """Support matrix for the 22 Scheduled Languages. Never claims parity between languages."""
    return load_languages()
