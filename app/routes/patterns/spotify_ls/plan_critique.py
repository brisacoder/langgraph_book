from typing import List, Optional
from pydantic import BaseModel, Field


class SubStepCritique(BaseModel):
    """
    Represents the critique for an individual sub-step.
    """

    step_number: int = Field(..., description="The sequential number of the sub-step.")
    notes: Optional[str] = Field(
        None,
        description="A summary of any issues, strengths, or observations about the sub-step.",
    )
    recommendations: Optional[List[str]] = Field(
        None,
        description="Actionable improvements or adjustments suggested for this sub-step.",
    )

    is_perfect: bool = Field(..., description="True if the sub-step needs no improvements.")


class StepCritique(BaseModel):
    """
    Represents the critique for a single step, potentially containing sub-step critiques.
    """

    step_number: int = Field(..., description="The sequential number of the step.")
    notes: Optional[str] = Field(
        None,
        description="A summary of any issues, strengths, or observations about the step.",
    )
    recommendations: Optional[List[str]] = Field(
        None,
        description="Actionable improvements or adjustments suggested for this step.",
    )
    is_perfect: bool = Field(..., description="True if the step is already optimal and requires no changes.")

    substeps: List[SubStepCritique] = Field(
        default_factory=list,
        description="Critiques of any sub-steps that belong to this step.",
    )


class PlanCritique(BaseModel):
    """
    Represents the overall critique of the plan, including per-step critiques and general recommendations.
    """

    summary: str = Field(
        ...,
        description="High-level summary of the plan's critique, noting major strengths and weaknesses.",
    )
    steps: List[StepCritique] = Field(
        ..., description="A list of critiques for each step of the plan."
    )
    overall_recommendations: Optional[List[str]] = Field(
        None,
        description="General improvements or guidance applicable to the entire plan.",
    )
    is_optimal: bool = Field(
        ...,
        description="True if the entire plan is considered optimal and requires no further improvements.",
    )
