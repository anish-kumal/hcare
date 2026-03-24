from pydantic import BaseModel, Field


class DoctorSchema(BaseModel):


    name: str = Field(
        description="The medical specialty that matches the user's query, or 'Only use English language' if not in English, or 'No valid medical concern detected.' if invalid."
    )