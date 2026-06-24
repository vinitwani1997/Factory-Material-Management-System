from pydantic import BaseModel


class ItemCategoryResponse(BaseModel):
    value: str   # the actual value to send in API requests, e.g. "raw_material"
    label: str   # the human-friendly text to show in a dropdown, e.g. "Raw Material"
