from legal_service.matter_intake import InfraiSmsGateway, MatterMessenger
from legal_service.models import MatterMessageRequest, MessageDecision


class FakeGateway:
    def __init__(self) -> None:
        self.sent: MessageDecision | None = None

    def send_case_message(self, request: MatterMessageRequest, decision: MessageDecision) -> str:
        self.sent = decision
        return "msg_123"

    def report_case_metric(self, request: MatterMessageRequest, decision: MessageDecision, message_id: str) -> bool:
        return True


def test_deadline_followup_becomes_urgent_when_due_tomorrow_and_unsigned() -> None:
    gateway = FakeGateway()
    service = MatterMessenger(gateway=gateway)
    request = MatterMessageRequest(
        matter_id="MAT-77",
        client_name="Casey Nguyen",
        phone_number="+15555550199",
        stage="deadline_followup",
        days_until_deadline=1,
        document_signed=False,
        document_name="Settlement Approval",
    )

    result = service.process(request)

    assert result.decision.urgency == "urgent"
    assert "tomorrow" in result.decision.body
    assert result.message_id == "msg_123"
    assert gateway.sent is not None
    assert gateway.sent.metric_name == "legal.deadline_followup.sms_sent"


def test_metric_payload_includes_required_type(monkeypatch) -> None:
    reported = []
    monkeypatch.setattr("legal_service.matter_intake.infrai.metrics.report", reported.append)
    request = MatterMessageRequest(
        matter_id="MAT-77",
        client_name="Casey Nguyen",
        phone_number="+15555550199",
        stage="deadline_followup",
        days_until_deadline=1,
        document_signed=False,
        document_name="Settlement Approval",
    )
    decision = MatterMessenger().decide(request)

    assert InfraiSmsGateway().report_case_metric(request, decision, "msg_123") is True
    assert reported[0]["type"] == "counter"
