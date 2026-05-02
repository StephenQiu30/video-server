from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models import User
from app.schemas import ParseRequest, ParseResponse
from app.services.download_adapter import DownloadEngineAdapter

router = APIRouter(prefix="/api/parse", tags=["parse"])


@router.post("", response_model=ParseResponse)
def parse_video(_: Annotated[User, Depends(get_current_user)], payload: ParseRequest) -> ParseResponse:
    return DownloadEngineAdapter().parse(str(payload.url))

