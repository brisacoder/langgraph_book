from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class Step(BaseModel):
    """
    The `Step` class represents an atomic unit of work within a plan. Each task must be focused on a single, clear objective and should not encompass multiple, unrelated activities.

    Key Points:
    - A task should perform one specific function and should not combine different activities. 
    - Each task should have a clear, verifiable success criterion that is achievable through the task's activities alone.
    - Steps must be URL-friendly, without spaces or special characters in their names.
    
    **Examples of What a Task Should NOT Do:**
    - "Create a playlist and add tracks" (This task mixes playlist creation with track management.)
    - "Search new artists and apply filtering." (This task combines artist search with its management, which should be separated.)
    - "Collect all relevant information about the playlist Spotify and User" (This task has two action items)

    Attributes:
    - `name` (str): URL-friendly name for the task, e.g., 'deploy-application'. Must not contain spaces or special characters.
    - `description` (str): A detailed description of the task, e.g., 'Deploy the application to the Kubernetes cluster using Helm.'
    - `success_criteria` (str): Clear and verifiable criteria for task completion, e.g., 'Application is successfully deployed and running in the Kubernetes cluster, as verified by checking the deployment status with 'kubectl get deployments'.' Each task must be atomic and focus on one thing only.
    - `tool` (str): "A `Tool` instance required for the task".
    - `action`: str = Field(..., description="Action decription in plain english. It should be one of Tool Calling or Knowledge base")


    """
    name: str = Field(..., description="URL-friendly name for the task, e.g., 'deploy-application'. Must not contain spaces or special characters.")
    description: str = Field(..., description="A detailed description of the task, e.g., 'Deploy the application to the Kubernetes cluster using Helm.'")
    success_criteria: str = Field(..., description="Clear and verifiable criteria for task completion, e.g., 'Application is successfully deployed and running in the Kubernetes cluster, as verified by checking the deployment status with 'kubectl get deployments'.' Each task must be atomic and focus on one thing only.")
    tool: str = Field(..., description="A `Tool` instance required for the task")
    action: str = Field(..., description="Action decription in plain english. It should be one of Tool Calling or Knowledge base")

    class Config:
        """Configuration for the Task model."""
        json_schema_extra = {
            "description": "The `Task` class represents an atomic unit of work that involves using specific tools to achieve a clear goal."
            # Removed 'examples' as it is now handled at the field level
        }


class Plan(BaseModel):
    steps: List[Step] = Field(
        ..., 
        description=(
            "A list of `Steps` that constitute the plan. Each step must be atomic, "
            "focused on a specific goal, and the entire plan must be complete, verifiable, "
            "and reproducible."
        )
    )
    Reasoning: str = Field(
        ..., 
        description=(
            "OpenAI should capture here the entire reasoning sequence used to create "
            " the plan"
        )
    )


@tool
def validate_plan(plan: Plan) -> bool:

    """
    Validates a step-by-step plan to solve a problem

    Args:
        plan (Plan): a step-by-step plan to solve a problem

    Returns:
        bool: whether plan is okay or not
    """
    return True
