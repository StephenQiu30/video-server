from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Reject unknown fields at the public HTTP boundary."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)
