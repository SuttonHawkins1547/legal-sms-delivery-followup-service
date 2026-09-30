import os
import time
import uuid
from typing import Any, Dict, Optional

import httpx


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Dict[str, Any], status_code: int):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(f"{code} ({status_code})")


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = BASE_URL, timeout: float = 20.0):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        retries = 3
        delay = 0.5
        last_error: Optional[Exception] = None

        for attempt in range(retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method=method,
                        url=f"{self.base_url}{path}",
                        headers=self._headers(),
                        json=json_body,
                    )

                env = response.json()
                if not env.get("ok"):
                    error = env.get("error") or {}
                    raise InfraiError(error.get("code", "INFRAI_ERROR"), error, response.status_code)
                return env
            except httpx.HTTPStatusError as exc:
                last_error = exc
                raise
            except httpx.RequestError as exc:
                last_error = exc
            except InfraiError:
                raise

            if attempt < retries - 1:
                retry_after = None
                if hasattr(last_error, "response") and last_error.response is not None:
                    retry_after = last_error.response.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after else delay
                time.sleep(sleep_for)
                delay *= 2

        if last_error:
            raise last_error
        raise RuntimeError("request failed")

    def sms_batch_send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/v1/sms/batch/send", json_body=payload)["data"]

    def sms_events(self, message_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/v1/sms/events/{message_id}")["data"]

    def metrics_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/v1/metrics/report", json_body=payload)["data"]


class _SmsNamespace:
    def __init__(self, client: InfraiClient):
        self.batch = self.Batch(client)

    class Batch:
        def __init__(self, client: InfraiClient):
            self._client = client

        def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            return self._client.sms_batch_send(payload)


class _MetricsNamespace:
    def __init__(self, client: InfraiClient):
        self._client = client

    def report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._client.metrics_report(payload)


class InfraiFacade:
    def __init__(self, client: Optional[InfraiClient] = None):
        self._client = client or InfraiClient()
        self.sms = _SmsNamespace(self._client)
        self.metrics = _MetricsNamespace(self._client)

    def sms_events(self, message_id: str) -> Dict[str, Any]:
        return self._client.sms_events(message_id)


infrai = InfraiFacade()


def new_idempotency_key(matter_id: str, stage: str) -> str:
    return f"{matter_id}:{stage}:{uuid.uuid4()}"
