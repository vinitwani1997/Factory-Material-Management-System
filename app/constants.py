"""
Fixed/static lists used across the app.

These are NOT database tables (unlike Roles) because they are small, fixed
sets of values that are part of the application's core logic, not data the
user manages. Defined here once so the Pydantic schema (validation) and the
API endpoint (for frontend dropdowns) always stay in sync -- change a value
here and it updates everywhere.
"""

ITEM_CATEGORIES = [
    {"value": "raw_material", "label": "Raw Material"},
    {"value": "semi_finished", "label": "Semi-Finished"},
    {"value": "finished_good", "label": "Finished Good"},
]

# Used by Pydantic's Literal[] type for request validation
ITEM_CATEGORY_VALUES = [c["value"] for c in ITEM_CATEGORIES]
