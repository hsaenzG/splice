from shared.db import get_table, response, to_dynamo, utc_now


def handler(event, context):
    detail = event.get("detail", {})
    if isinstance(detail, str):
        import json

        detail = json.loads(detail)

    session_id = detail.get("sessionId")
    if not session_id:
        return {"status": "skipped", "reason": "no sessionId"}

    table = get_table()
    table.put_item(
        Item=to_dynamo(
            {
                "sessionId": session_id,
                "sk": f"EVENT#ENRICHED#{utc_now()}",
                "entityType": "enrichment",
                "eventType": "ContextIngested",
                "itemCount": detail.get("itemCount", 0),
                "enrichedAt": utc_now(),
                "note": "Async enrichment marker — Milestone 4+ will add embeddings and dedup.",
            }
        )
    )

    return {"status": "enriched", "sessionId": session_id}
