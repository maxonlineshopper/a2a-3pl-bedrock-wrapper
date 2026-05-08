# ECS Fargate Bedrock Agent A2A Wrapper

This project is a minimal Flask HTTP service that exposes an Amazon Bedrock Agent as an A2A-compatible endpoint. It is packaged as a Docker container for deployment to AWS ECS Fargate behind an Application Load Balancer.

The service provides:

- `GET /.well-known/agent-card.json` for the A2A Agent Card
- `POST /rpc` for A2A JSON-RPC messages
- `GET /health` for load balancer health checks

Incoming message text is extracted from `params.message.parts[].text`, sent to Amazon Bedrock Agent Runtime with `boto3` `invoke_agent`, and returned in an A2A-compatible JSON-RPC response.

## Architecture

```text
Agent Fabric -> ALB -> ECS Fargate A2A Wrapper -> Bedrock Agent -> Lambda
```

## Environment Variables

Configure these variables on the ECS task definition:

| Name | Value |
| --- | --- |
| `AWS_REGION` | `us-east-1` |
| `BEDROCK_AGENT_ID` | `CFP6HKU4VJ` |
| `BEDROCK_AGENT_ALIAS_ID` | `TSTALIASID` |
| `PUBLIC_BASE_URL` | `https://your-public-alb-domain` |

## Local Run

```bash
pip install -r requirements.txt
AWS_REGION=us-east-1 \
BEDROCK_AGENT_ID=CFP6HKU4VJ \
BEDROCK_AGENT_ALIAS_ID=TSTALIASID \
PUBLIC_BASE_URL=http://localhost:8000 \
gunicorn --bind 0.0.0.0:8000 app:app
```

Health check:

```bash
curl http://localhost:8000/health
```

Example shipment prompts:

```text
Track DHL123456789
Track UPS987654321
```

## Docker Build

```bash
docker build -t a2a-3pl-bedrock-wrapper .
docker run --rm -p 8000:8000 \
  -e AWS_REGION=us-east-1 \
  -e BEDROCK_AGENT_ID=CFP6HKU4VJ \
  -e BEDROCK_AGENT_ALIAS_ID=TSTALIASID \
  -e PUBLIC_BASE_URL=http://localhost:8000 \
  a2a-3pl-bedrock-wrapper
```

## Push to Amazon ECR

Set your AWS account and region:

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
export ECR_REPOSITORY=a2a-3pl-bedrock-wrapper
```

Create the ECR repository:

```bash
aws ecr create-repository \
  --repository-name $ECR_REPOSITORY \
  --region $AWS_REGION
```

Authenticate Docker to ECR:

```bash
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

Tag and push the image:

```bash
docker tag a2a-3pl-bedrock-wrapper:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
```

## ECS Fargate Deployment

1. Create or choose an ECS cluster.
2. Create an ECR repository and push the Docker image.
3. Create an ECS task execution role for pulling the image and writing logs.
4. Create an ECS task role with permission to invoke the Bedrock Agent.
5. Create a Fargate task definition using the ECR image.
6. Set container port `8000`.
7. Add the required environment variables to the container definition.
8. Create an Application Load Balancer.
9. Create an ALB target group for IP targets on port `8000`.
10. Set the target group health check path to `/health`.
11. Create an ECS service using Fargate and attach it to the ALB target group.
12. Set `PUBLIC_BASE_URL` to the public ALB URL or your custom domain.

## Required ECS Task Role IAM Policy

Attach this policy to the ECS task role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": "*"
    }
  ]
}
```

For production, scope `Resource` to the specific Bedrock Agent alias ARN.

## Agent Card URL

```text
https://your-public-alb-domain/.well-known/agent-card.json
```

## JSON-RPC Request

```bash
curl -X POST https://your-public-alb-domain/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Track UPS987654321"
          }
        ]
      }
    }
  }'
```
