from typing import Literal
from pydantic import BaseModel, Field


MatterStage = Literal[
    "matter_intake",
    "signed_document_delivery",
    "deadline_followup",
]
Urgency = Literal["standard", "urgent"]


class MatterMessageRequest(BaseModel):
    matter_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    phone_number: str = Field(min_length=8)
    stage: MatterStage
    days_until_deadline: int = Field(ge=0)
    document_signed: bool
    document_name: str = Field(min_length=1)


class MessageDecision(BaseModel):
    matter_id: str
    stage: MatterStage
    urgency: Urgency
    body: str
    metric_name: str


class MatterMessageResponse(BaseModel):
    decision: MessageDecision
    message_id: str
    metric_reported: bool
