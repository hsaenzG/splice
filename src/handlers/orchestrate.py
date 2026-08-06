from shared.orchestrator import orchestrate_context
from shared.db import from_dynamo, get_session_id, get_table, response, to_dynamo, utc_now


def handler(event, context):
    session_id = get_session_id(event)
    if not session_id:
        return response(400, {"error": "sessionId is required"})

    table = get_table()
    result = table.query(
        KeyConditionExpression="sessionId = :sid AND begins_with(sk, :prefix)",
        ExpressionAttributeValues={":sid": session_id, ":prefix": "CTX#"},
    )

    items = [from_dynamo(i) for i in result.get("Items", [])]
    if not items:
        return response(404, {"error": "No context items found. POST /ingest first."})

    orchestration = orchestrate_context(session_id, items)

    record = {
        "sessionId": session_id,
        "sk": "ORCHESTRATION#LATEST",
        "entityType": "orchestration",
        **orchestration,
        "createdAt": utc_now(),
    }
    table.put_item(Item=to_dynamo(record))

    table.update_item(
        Key={"sessionId": session_id, "sk": "METADATA"},
        UpdateExpression="SET #s = :s, updatedAt = :u, lastOrchestrationMs = :ms",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "orchestrated",
            ":u": utc_now(),
            ":ms": orchestration.get("latencyMs", 0),
        },
    )

    return response(200, orchestration)
