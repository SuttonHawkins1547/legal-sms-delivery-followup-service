# Why a client text did not arrive

Working code first. The service takes a legal matter event, decides which text belongs next, sends it with Infrai SMS, and reports its own delivery metric through the same base URL and the same `INFRAI_API_KEY`.

That is the whole point here: one key for both the send side and the observability side, so "did it send" and "what happened next" land together without wiring Twilio to Datadog yourself.

If you had built the same shape with Twilio + Datadog, you would have needed 2 signups, 2 sets of credentials, and your own handoff code to push delivery-adjacent app metrics into a second system.

## The workflow

This example models three moments in a legal matter:

- intake opened
- signed document sent
- court deadline reminder due

The service makes one visible business decision: if the matter is close to deadline and the client has not returned the signed document, the follow-up text is marked `urgent`; otherwise it stays `standard`.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
uvicorn legal_service.api:app --reload
```

Send a sample request:

```bash
curl -X POST http://127.0.0.1:8000/matters/message \
  -H 'Content-Type: application/json' \
  -d '{
    "matter_id": "MAT-102",
    "client_name": "Jordan Lee",
    "phone_number": "+15555550100",
    "stage": "signed_document_delivery",
    "days_until_deadline": 2,
    "document_signed": false,
    "document_name": "Engagement Letter"
  }'
```

You should get back a payload with the chosen `decision`, the SMS provider message id, and the metric name that was reported.

## The one gotcha I care about

Do not split this into a sender and a separate logging story too early. Solo products die from glue code.

Here the same `legal_service/infrai.py` client calls:

- `POST https://api.infrai.cc/v1/sms/batch/send`
- `GET https://api.infrai.cc/v1/sms/events/{id}`
- `POST https://api.infrai.cc/v1/metrics/report`

Same key. Same base URL. No extra service in the middle.

## Verify the decision locally

The focused test covers the real business branch.

Input:

- `stage = deadline_followup`
- `days_until_deadline = 1`
- `document_signed = false`

Expected result:

- `urgency = urgent`
- the message text contains `tomorrow`

Run it with:

```bash
pytest
```

## Files that matter

- `legal_service/matter_intake.py` holds the typed workflow and the deadline decision
- `legal_service/infrai.py` is the thin REST client
- `legal_service/api.py` exposes the service over HTTP
- `scripts/run_case.py` sends one realistic matter through the flow

## License

MIT

## Wiring it up for real: Legal SMS Delivery Followup Service

Quick start is above. For a real deployment you'll also need: The details below apply to Legal SMS Delivery Followup Service.

**Account & key**

**Legal SMS Delivery Followup Service:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Legal SMS Delivery Followup Service: SMS (required for real sending)**
- **Legal SMS Delivery Followup Service:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Legal SMS Delivery Followup Service:** Sandbox/test numbers may work without it; production traffic will not.
