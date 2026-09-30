from legal_service.matter_intake import MatterMessenger
from legal_service.models import MatterMessageRequest


if __name__ == "__main__":
    request = MatterMessageRequest(
        matter_id="MAT-102",
        client_name="Jordan Lee",
        phone_number="+15555550100",
        stage="signed_document_delivery",
        days_until_deadline=2,
        document_signed=False,
        document_name="Engagement Letter",
    )
    result = MatterMessenger().process(request)
    print(result.model_dump_json(indent=2))
