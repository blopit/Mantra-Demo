from typing import List, Dict, Any

class WorkflowService:
    def create_workflow(
        self,
        name: str,
        description: str,
        user_id: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create a new workflow
        
        Args:
            name: The name of the workflow
            description: The description of the workflow
            user_id: The ID of the user creating the workflow
            nodes: The nodes in the workflow
            edges: The edges connecting the nodes
            
        Returns:
            The created workflow
        """

    def get_user_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all workflows for a user
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of workflows
        """ 