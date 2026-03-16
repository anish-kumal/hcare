from pydantic import BaseModel, Field


class DoctorSchema(BaseModel):
    name: str | None = Field(
        description="The medical specialty that matches the user's query."
    )

