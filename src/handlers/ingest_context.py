import json
import os
import uuid

import boto3

from shared.db import get_session_id, get_table, parse_body, response, to_dynamo, utc_now


def handler(event, context):
    session_id = get_session_id(event)
    if not session_id:
        return response(400, {"error": "sessionId is required"})

    body = parse_body(event)
    items = body.get("items", [])
    if not items:
        return response(400, {"error": "items array is required"})

    table = get_table()
    ingested = []

    for raw in items:
        item_id = raw.get("id") or str(uuid.uuid4())
        record = {
            "sessionId": session_id,
            "sk": f"CTX#{item_id}",
            "entityType": "context",
            "id": item_id,
            "type": raw.get("type", "note"),
            "content": raw.get("content", ""),
            "metadata": raw.get("metadata", {}),
            "timestamp": raw.get("timestamp") or utc_now(),
        }
        table.put_item(Item=to_dynamo(record))
        ingested.append({"id": item_id, "type": record["type"]})

    table.update_item(
        Key={"sessionId": session_id, "sk": "METADATA"},
        UpdateExpression="SET contextItemCount = contextItemCount + :n, updatedAt = :u",
        ExpressionAttributeValues={":n": len(ingested), ":u": utc_now()},
    )

    bus_name = os.environ.get("EVENT_BUS_NAME")
    if bus_name:
        events = boto3.client("events")
        events.put_events(
            Entries=[
                {
                    "Source": "context.harness",
                    "DetailType": "ContextIngested",
                    "Detail": json.dumps(
                        {"sessionId": session_id, "itemCount": len(ingested)}
                    ),
                    "EventBusName": bus_name,
                }
            ]
        )

    return response(
        200,
        {
            "sessionId": session_id,
            "ingested": ingested,
            "count": len(ingested),
        },
    )
