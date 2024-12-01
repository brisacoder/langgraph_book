from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class SubStep(BaseModel):
    """
    Represents a sub-step within a step, avoiding direct recursion.
    """
    step_number: int = Field(..., description="The sequential number of the sub-step in the plan.")
    name: str = Field(..., description="URL-friendly name for the sub-step. Must not contain spaces or special characters.")
    type: str = Field(..., description="Type of the sub-step. Possible values: 'action', 'branch', 'parallel'.")
    description: str = Field(..., description="A detailed description of the sub-step.")
    success_criteria: str = Field(..., description="Clear and verifiable criteria for sub-step completion.")
    tool: Optional[str] = Field(description="A `Tool` instance required for the sub-step, if applicable.")
    action: Optional[str] = Field(description="Action description in plain English.")
    condition: Optional[str] = Field(description="Condition expression for branches.")
    # Exclude substeps to avoid recursion

    # class Config:
    #     """Configuration for the SubStep model."""
    #     json_schema_extra = {
    #         "description": "The `SubStepStep` class represents an atomic unit of work that involves using specific tools to achieve a clear goal."
    #         # Removed 'examples' as it is now handled at the field level
    #     }

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "description": "Represents a unit of work that can be an action, loop, branch, or parallel execution."
        },
    }


class Step(BaseModel):
    """
    The `Step` class represents an atomic unit of work within a plan. Each task must be focused on a single, clear objective and should not encompass multiple, unrelated activities.

    Key Points:
    - A task should perform one specific function and should not combine different activities. 
    - Each task should have a clear, verifiable success criterion that is achievable through the task's activities alone.
    - Steps must be URL-friendly, without spaces or special characters in their names.

    **Examples of What a Step Should NOT Do:**
    - "Create a playlist and add tracks" (This task mixes playlist creation with track management.)
    - "Search new artists and apply filtering." (This task combines artist search with its management, which should be separated.)
    - "Collect all relevant information about the playlist Spotify and User" (This task has two action items)

    Attributes:
    - `step_number` (int): The sequential number of the step in the plan.
    - `name` (str): URL-friendly name for the step, e.g., 'deploy-application'. Must not contain spaces or special characters.
    - `type` (str): The type of step. Possible values are 'action', 'loop', 'branch', 'parallel'.
    - `description` (str): A detailed description of the step.
    - `success_criteria` (str): Clear and verifiable criteria for step completion.
    - `tool` (Optional[str]): A `Tool` instance required for the step, if applicable.
    - `action` (Optional[str]): Action description in plain English. Should be a tool call or knowledge base usage.
    - `condition` (Optional[str]): Condition expression for loops and branches.
    - `substeps` (Optional[List[SubStep]]): Nested steps for loops, branches, or parallel execution.
    """

    step_number: int = Field(..., description="The sequential number of the step in the plan.")
    name: str = Field(..., description="URL-friendly name for the task, e.g., 'deploy-application'. Must not contain spaces or special characters.")
    type: str = Field(..., description="Type of the step. Possible values: 'action', 'loop', 'branch', 'parallel'.")
    description: str = Field(..., description="A detailed description of the task")
    success_criteria: str = Field(..., description="Clear and verifiable criteria for task completion")    
    tool: Optional[str] = Field(description="A `Tool` instance required for the step, if applicable.")
    action: Optional[str] = Field(description="Action description in plain English.")
    condition: Optional[str] = Field(description="Condition expression for loops and branches.")
    substeps: Optional[List[SubStep]] = Field(description="Nested substeps for loops, branches, or parallel execution.")

    # class Config:
    #     """Configuration for the Step model."""
    #     json_schema_extra = {
    #         "description": "The `Step` class represents an atomic unit of work that involves using specific tools to achieve a clear goal."
    #         # Removed 'examples' as it is now handled at the field level
    #     }

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "description": "Represents a unit of work that can be an action, loop, branch, or parallel execution."
        },
    }


class Plan(BaseModel):
    steps: List[Step] = Field(
        ...,
        description=(
            "List of steps constituting the plan, supporting advanced planning structures. Each step (or sub-step as "
            " applicable) must be atomic, "
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

    model_config = {
        "extra": "forbid",
    } 


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


def get_plan_tools() -> List:
    return [validate_plan]
