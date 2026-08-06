import uuid

from shared.db import get_table, parse_body, response, to_dynamo, utc_now


def handler(event, context):
    body = parse_body(event)
    session_id = body.get("sessionId") or str(uuid.uuid4())
    project = body.get("project", "unnamed-project")
    assistant = body.get("assistant", "cursor")

    item = {
        "sessionId": session_id,
        "sk": "METADATA",
        "entityType": "session",
        "project": project,
        "assistant": assistant,
        "status": "active",
        "contextItemCount": 0,
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
    }

    get_table().put_item(Item=to_dynamo(item))

    return response(
        201,
        {
            "sessionId": session_id,
            "project": project,
            "assistant": assistant,
            "status": "active",
            "message": "Session created. Ingest context, then call /orchestrate.",
        },
    )
