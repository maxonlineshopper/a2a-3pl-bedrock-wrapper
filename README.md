# AWS App Runner Bedrock Agent A2A Endpoint

This project is a minimal Python Flask service for AWS App Runner that exposes an Amazon Bedrock Agent through an A2A-compatible HTTP interface.

It provides:

- `GET /.well-known/agent-card.json` for the A2A Agent Card
- `POST /rpc` for A2A JSON-RPC messages
- `GET /health` for health checks

Incoming message text is extracted from `params.message.parts[].text`, forwarded to Amazon Bedrock Agent Runtime with `boto3` `invoke_agent`, and returned as an A2A-compatible JSON-RPC response.

## Environment Variables

Set these values in AWS App Runner:

| Name | Example |
| --- | --- |
| `AWS_REGION` | `us-east-1` |
| `BEDROCK_AGENT_ID` | `placeholder` |
| `BEDROCK_AGENT_ALIAS_ID` | `placeholder` |
| `PUBLIC_BASE_URL` | `https://your-app-runner-url.awsapprunner.com` |

## Deploy to AWS App Runner

1. Push this project to a GitHub repository.
2. Open the AWS Console.
3. Go to AWS App Runner.
4. Choose **Create service**.
5. Select **Source code repository**.
6. Connect your GitHub account and choose this repository.
7. Choose the branch to deploy.
8. Select **Use a configuration file** so App Runner uses `apprunner.yaml`.
9. Configure the service instance role with permission to invoke your Bedrock Agent.
10. Set the required environment variables.
11. Create and deploy the service.

## Required IAM Policy

Attach this policy to the App Runner service instance role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeAgent",
      "Resource": "*"
    }
  ]
}
```

For production, scope `Resource` to the specific Bedrock Agent alias ARN.

## Local Run

```bash
pip install -r requirements.txt
AWS_REGION=us-east-1 \
BEDROCK_AGENT_ID=placeholder \
BEDROCK_AGENT_ALIAS_ID=placeholder \
PUBLIC_BASE_URL=http://localhost:8000 \
gunicorn --bind 0.0.0.0:8000 app:app
```

## Test Agent Card

```bash
curl http://localhost:8000/.well-known/agent-card.json
```

## Test JSON-RPC Endpoint

```bash
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-1",
    "method": "message/send",
    "params": {
      "id": "task-1",
      "sessionId": "demo-session",
      "message": {
        "parts": [
          {
            "kind": "text",
            "text": "Track shipment SHIP-12345"
          }
        ]
      }
    }
  }'
```
