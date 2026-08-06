import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

TABLE_NAME = os.environ.get("SESSIONS_TABLE", "splice-sessions")
_dynamodb = None


def get_table():
    global _dynamodb
    if _dynamodb is None:
        import boto3

        _dynamodb = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _dynamodb


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_dynamo(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_dynamo(v) for v in obj]
    return obj


def from_dynamo(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [from_dynamo(v) for v in obj]
    return obj


def response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def parse_body(event: dict) -> dict:
    body = event.get("body") or "{}"
    if isinstance(body, str):
        return json.loads(body) if body else {}
    return body


def get_session_id(event: dict) -> str:
    return event.get("pathParameters", {}).get("sessionId", "")
