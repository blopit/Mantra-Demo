# Current Task: Fix Node Type Validation for Google Service Nodes

## Status: In Progress

## Description
Fix the error "Invalid node type: gmail. Must start with 'n8n-nodes-base.'" by updating the workflow validation to correctly handle Google service node types (gmail, googleCalendar, etc.).

## Current Progress
- [x] Identify the root cause: n8n_service validation requiring all node types to start with 'n8n-nodes-base.'
- [x] Update n8n_service._validate_workflow_structure to recognize Google service node types
- [x] Update n8n_service.parse_workflow to handle Google service node types
- [x] Update mantra_service.create_mantra to transform Google service node workflows
- [x] Update mantra_service.install_mantra to transform Google service node workflows
- [ ] Test the fix by creating a mantra with Gmail nodes

## Next Steps
1. Restart the application to apply changes
2. Test creating a mantra with Gmail node
3. Verify successful creation in the database
4. Test installing the mantra for a user

## Related Files
- src/services/n8n_service.py
- src/services/mantra_service.py
- src/providers/google/transformers/workflow_transformer.py

## Notes
- The GoogleWorkflowTransformer already exists to handle Google-specific nodes
- We need to ensure both validation and transformation work together properly
