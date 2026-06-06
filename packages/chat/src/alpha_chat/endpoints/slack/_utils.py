from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import HTTPException
from slack_sdk.signature import SignatureVerifier


def verify_slack_signature(
    signing_secret: str, request_body: bytes, headers: dict
) -> None:
    verifier = SignatureVerifier(signing_secret)
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    if not verifier.is_valid(request_body.decode(), timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")


def parse_slack_form(body: bytes) -> dict[str, str]:
    return {key: values[-1] for key, values in parse_qs(body.decode()).items()}


__all__ = ["verify_slack_signature", "parse_slack_form"]
