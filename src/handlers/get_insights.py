from shared.db import from_dynamo, get_session_id, get_table, response


def handler(event, context):
    session_id = get_session_id(event)
    if not session_id:
        return response(400, {"error": "sessionId is required"})

    table = get_table()

    meta = table.get_item(Key={"sessionId": session_id, "sk": "METADATA"}).get("Item")
    if not meta:
        return response(404, {"error": "Session not found"})

    orch = table.get_item(
        Key={"sessionId": session_id, "sk": "ORCHESTRATION#LATEST"}
    ).get("Item")

    ctx = table.query(
        KeyConditionExpression="sessionId = :sid AND begins_with(sk, :prefix)",
        ExpressionAttributeValues={":sid": session_id, ":prefix": "CTX#"},
    )

    return response(
        200,
        {
            "session": from_dynamo(meta),
            "orchestration": from_dynamo(orch) if orch else None,
            "contextItems": [from_dynamo(i) for i in ctx.get("Items", [])],
        },
    )
