from fastapi import FastAPI, HTTPException

from .infrai import InfraiError
from .matter_intake import MatterMessenger
from .models import MatterMessageRequest, MatterMessageResponse


app = FastAPI(title="Legal SMS delivery follow-up service")
messenger = MatterMessenger()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/matters/message", response_model=MatterMessageResponse)
def send_matter_message(request: MatterMessageRequest) -> MatterMessageResponse:
    try:
        return messenger.process(request)
    except InfraiError as exc:
        raise HTTPException(status_code=400 if exc.status_code < 500 else 502, detail=exc.detail)
