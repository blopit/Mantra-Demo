# N8N Integration Guide

This guide explains how to integrate with N8N workflow automation in the Mantra Demo application.

## Overview

The application integrates with [N8N Cloud](https://n8n.io/cloud/), a workflow automation tool, to create and manage workflows. N8N allows you to connect various services and automate tasks between them.

## N8N Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Mantra Demo    │────▶│  N8N Service    │────▶│  N8N Cloud      │
│  Application    │     │  Adapter        │     │  Instance       │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Setting Up N8N Cloud

### Step 1: Create an N8N Cloud Account

1. Sign up for [N8N Cloud](https://www.n8n.cloud/)
2. Create a new workspace
3. Get your API key from the workspace settings

### Step 2: Configure Environment Variables

Add the following to your `.env` file:

```
N8N_API_URL=https://your-instance.app.n8n.cloud/api/v1
N8N_WEBHOOK_URL=https://your-instance.app.n8n.cloud
N8N_API_KEY=your_n8n_api_key
N8N_API_TIMEOUT=30.0
N8N_MAX_RETRIES=3
N8N_RETRY_DELAY=1.0
```

## N8N Service

The application provides an N8N service adapter to interact with the N8N API:

```python
from src.services.n8n_service import N8nService

# Create N8N service instance
n8n_service = N8nService(
    api_url=os.getenv("N8N_API_URL"),
    api_key=os.getenv("N8N_API_KEY")
)
```

## Creating Workflows

### Basic Workflow Creation

```python
# Define a simple workflow
workflow = {
    "name": "Simple Workflow",
    "nodes": [
        {
            "parameters": {
                "rule": {
                    "interval": [
                        {
                            "field": "hours",
                            "expression": "*/1"
                        }
                    ]
                }
            },
            "name": "Schedule Trigger",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1,
            "position": [250, 300]
        },
        {
            "parameters": {},
            "name": "NoOp",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [460, 300]
        }
    ],
    "connections": {
        "Schedule Trigger": {
            "main": [
                [
                    {
                        "node": "NoOp",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }
    },
    "settings": {}
}

# Create the workflow
created_workflow = await n8n_service.create_workflow(workflow)
workflow_id = created_workflow.get("id")
```

### Activating Workflows

```python
# Activate a workflow
await n8n_service.activate_workflow(workflow_id)

# Deactivate a workflow
await n8n_service.deactivate_workflow(workflow_id)
```

### Executing Workflows

```python
# Execute a workflow
execution_result = await n8n_service.execute_workflow(workflow_id)
```

### Deleting Workflows

```python
# Delete a workflow
await n8n_service.delete_workflow(workflow_id)
```

## Mantra Workflow Management

The application provides a higher-level Mantra service to manage workflows:

```python
from src.services.mantra_service import MantraService

# Create Mantra service instance
mantra_service = MantraService(
    n8n_service=n8n_service,
    db_session=db_session
)

# Install a mantra for a user
installation = await mantra_service.install_mantra(
    mantra_id="mantra-id",
    user_id="user-id"
)

# Uninstall a mantra
await mantra_service.uninstall_mantra(installation.id)
```

## Workflow Templates

The application uses workflow templates (mantras) that can be customized and installed for users:

```python
# Create a mantra (workflow template)
mantra = Mantra(
    name="Email Notification",
    description="Send email notifications for new messages",
    workflow_json={
        "nodes": [...],
        "connections": {...}
    },
    user_id="creator-user-id"
)
db_session.add(mantra)
await db_session.commit()
```

## Dynamic Workflow Generation

The application can generate workflows dynamically based on user data:

```python
from src.providers.google.transformers.workflow_transformer import transform_workflow

# Get user credentials
credentials = await get_credentials_from_database(db_session, user_id)

# Transform workflow template with user data
transformed_workflow = transform_workflow(
    workflow_template=mantra.workflow_json,
    user_data={
        "email": user.email,
        "name": user.name,
        "credentials": credentials
    }
)

# Create the workflow in N8N
created_workflow = await n8n_service.create_workflow(transformed_workflow)
```

## Error Handling

When working with N8N API, it's important to handle errors properly:

```python
try:
    # Call N8N API
    workflow = await n8n_service.create_workflow(workflow_data)
except N8nApiError as error:
    if error.status_code == 401:
        # Handle authentication errors
        pass
    elif error.status_code == 400:
        # Handle validation errors
        pass
    else:
        # Handle other errors
        pass
```

## Webhooks

N8N workflows can trigger webhooks back to the application:

```python
# Define a webhook endpoint
@router.post("/webhooks/n8n/{workflow_id}")
async def n8n_webhook(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle N8N webhook."""
    # Get the webhook data
    data = await request.json()

    # Process the webhook data
    # ...

    return {"status": "success"}
```

## Working with Webhooks

### Webhook Activation Process

When creating workflows with webhooks, the activation process is crucial:

1. **Workflow Creation**: Create the workflow with webhook nodes
2. **Activation**: The workflow must be activated for webhooks to work
3. **Registration**: Webhooks are automatically registered upon activation
4. **Verification**: The system verifies webhook accessibility

### Webhook URL Structure

Webhook URLs for n8n cloud follow this pattern:
```
https://your-workspace.app.n8n.cloud/webhook/{workflow_id}/{path}
```

Where:
- `your-workspace`: Your n8n cloud workspace name
- `workflow_id`: The ID of your workflow
- `path`: The path configured in your webhook node

### Important Notes

1. **Activation Timing**:
   - Webhooks take a few seconds to register after activation
   - The system automatically retries if registration fails
   - Default wait time is 3 seconds after activation

2. **URL Availability**:
   - Production webhook URLs only work when workflow is active
   - Test webhook URLs work regardless of activation status
   - Always use production URLs in production environment

## Troubleshooting

### Common Issues

1. **404 Not Found Errors**:
   - **Cause**: Webhook not yet registered after activation
   - **Solution**:
     - Wait a few seconds after activation
     - Ensure workflow is actually active
     - Check webhook path configuration

2. **Authentication Errors**:
   - Check that your N8N API key is correct
   - Verify API key has necessary permissions
   - Ensure headers are properly set

3. **Webhook Registration Failures**:
   - Verify workflow is properly activated
   - Check webhook node configuration
   - Ensure webhook path is valid
   - Look for conflicting webhook paths

### Debugging Steps

If webhooks aren't working:

1. Check workflow status:
   ```python
   workflow = await n8n_service.get_workflow(workflow_id)
   print(f"Active status: {workflow.get('active')}")
   ```

2. Verify webhook URL:
   ```python
   webhook_url = await n8n_service.get_webhook_url(workflow_id)
   print(f"Webhook URL: {webhook_url}")
   ```

3. Test webhook manually:
   ```bash
   curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}' \
     https://your-workspace.app.n8n.cloud/webhook/{workflow_id}/{path}
   ```

## Best Practices

1. **Error Handling**:
   - Implement proper error handling for N8N API calls
   - Use exponential backoff for retries
   - Log all webhook-related errors

2. **Activation Management**:
   - Always verify activation status
   - Wait for webhook registration
   - Test webhooks after activation

3. **Monitoring**:
   - Monitor workflow executions
   - Track webhook success rates
   - Set up alerts for failures

4. **Security**:
   - Secure webhook endpoints
   - Use HTTPS for all URLs
   - Validate webhook payloads

## Further Reading

- [N8N Documentation](https://docs.n8n.io/)
- [N8N API Reference](https://docs.n8n.io/api/)
- [N8N Webhook Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)
