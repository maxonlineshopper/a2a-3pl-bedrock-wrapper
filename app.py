import os
import uuid

import boto3
from flask import Flask, jsonify, request


app = Flask(__name__)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_AGENT_ID = os.getenv("BEDROCK_AGENT_ID", "")
BEDROCK_AGENT_ALIAS_ID = os.getenv("BEDROCK_AGENT_ALIAS_ID", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)


def json_rpc_error(request_id, code, message, status_code=400):
    return (
        jsonify(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        ),
        status_code,
    )


def extract_message_text(params):
    message = params.get("message", {})
    parts = message.get("parts", [])

    text_parts = []
    for part in parts:
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            text_parts.append(text.strip())

    return "\n".join(text_parts)


def invoke_bedrock_agent(input_text, session_id):
    response = bedrock_runtime.invoke_agent(
        agentId=BEDROCK_AGENT_ID,
        agentAliasId=BEDROCK_AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=input_text,
    )

    chunks = []
    for event in response.get("completion", []):
        chunk = event.get("chunk")
        if chunk and "bytes" in chunk:
            chunks.append(chunk["bytes"].decode("utf-8"))

    return "".join(chunks)


@app.get("/.well-known/agent-card.json")
def agent_card():
    return jsonify(
        {
            "name": "Shipment Tracking Bedrock Agent",
            "description": "An A2A-compatible endpoint backed by an Amazon Bedrock Agent for shipment tracking questions.",
            "url": f"{PUBLIC_BASE_URL}/rpc",
            "skills": [
                {
                    "name": "shipment_tracking",
                    "description": "Answer shipment tracking and delivery status questions.",
                    "examples": [
                        "Track shipment SHIP-12345",
                        "Where is my package?",
                        "When will order ORD-98765 arrive?",
                    ],
                }
            ],
        }
    )


@app.post("/rpc")
def rpc():
    payload = request.get_json(silent=True) or {}
    request_id = payload.get("id")

    if payload.get("jsonrpc") != "2.0":
        return json_rpc_error(request_id, -32600, "Invalid JSON-RPC version")

    params = payload.get("params")
    if not isinstance(params, dict):
        return json_rpc_error(request_id, -32602, "Missing or invalid params")

    input_text = extract_message_text(params)
    if not input_text:
        return json_rpc_error(request_id, -32602, "Missing message text")

    if not BEDROCK_AGENT_ID or not BEDROCK_AGENT_ALIAS_ID:
        return json_rpc_error(
            request_id,
            -32000,
            "Bedrock Agent configuration is missing",
            status_code=500,
        )

    task_id = params.get("id") or str(uuid.uuid4())
    session_id = params.get("sessionId") or str(task_id)

    try:
        output_text = invoke_bedrock_agent(input_text, session_id)
    except Exception as exc:
        app.logger.exception("Bedrock Agent invocation failed")
        return json_rpc_error(request_id, -32000, str(exc), status_code=502)

    return jsonify(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "id": task_id,
                "status": {"state": "completed"},
                "artifacts": [
                    {
                        "parts": [
                            {
                                "kind": "text",
                                "text": output_text,
                            }
                        ]
                    }
                ],
            },
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})
