from typing import Protocol

from .models import MatterMessageRequest, MessageDecision, MatterMessageResponse
from .infrai import infrai


class SmsGateway(Protocol):
    def send_case_message(self, request: MatterMessageRequest, decision: MessageDecision) -> str:
        ...

    def report_case_metric(self, request: MatterMessageRequest, decision: MessageDecision, message_id: str) -> bool:
        ...


class InfraiSmsGateway:
    def send_case_message(self, request: MatterMessageRequest, decision: MessageDecision) -> str:
        payload = {
            "messages": [
                {
                    "to": request.phone_number,
                    "text": decision.body,
                }
            ]
        }
        result = infrai.sms.batch.send(payload)
        if isinstance(result, dict):
            for key in ("message_id", "id"):
                if key in result and isinstance(result[key], str):
                    return result[key]
            if "messages" in result and isinstance(result["messages"], list) and result["messages"]:
                first = result["messages"][0]
                if isinstance(first, dict):
                    for key in ("message_id", "id"):
                        if key in first and isinstance(first[key], str):
                            return first[key]
        raise ValueError("SMS response did not include a message id")

    def report_case_metric(self, request: MatterMessageRequest, decision: MessageDecision, message_id: str) -> bool:
        payload = {
            "name": decision.metric_name,
            "value": 1,
            "type": "counter",
            "tags": {
                "matter_id": request.matter_id,
                "stage": request.stage,
                "urgency": decision.urgency,
                "message_id": message_id,
            },
        }
        infrai.metrics.report(payload)
        return True


class MatterMessenger:
    def __init__(self, gateway: SmsGateway | None = None):
        self.gateway = gateway or InfraiSmsGateway()

    def decide(self, request: MatterMessageRequest) -> MessageDecision:
        urgency = "urgent" if request.stage == "deadline_followup" and request.days_until_deadline <= 1 and not request.document_signed else "standard"

        if request.stage == "matter_intake":
            body = (
                f"Hi {request.client_name}, we opened matter {request.matter_id}. "
                f"Please review and sign {request.document_name}."
            )
            metric_name = "legal.matter_intake.sms_sent"
        elif request.stage == "signed_document_delivery":
            body = (
                f"Hi {request.client_name}, your {request.document_name} is ready for signature "
                f"for matter {request.matter_id}."
            )
            metric_name = "legal.signed_document.sms_sent"
        else:
            timing = "tomorrow" if request.days_until_deadline <= 1 else f"in {request.days_until_deadline} days"
            prefix = "Urgent: " if urgency == "urgent" else "Reminder: "
            body = (
                f"{prefix}{request.document_name} for matter {request.matter_id} is still unsigned. "
                f"Your deadline is {timing}."
            )
            metric_name = "legal.deadline_followup.sms_sent"

        return MessageDecision(
            matter_id=request.matter_id,
            stage=request.stage,
            urgency=urgency,
            body=body,
            metric_name=metric_name,
        )

    def process(self, request: MatterMessageRequest) -> MatterMessageResponse:
        decision = self.decide(request)
        message_id = self.gateway.send_case_message(request, decision)
        metric_reported = self.gateway.report_case_metric(request, decision, message_id)
        return MatterMessageResponse(
            decision=decision,
            message_id=message_id,
            metric_reported=metric_reported,
        )
