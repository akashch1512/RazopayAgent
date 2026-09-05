import pydantic
from pydantic import ConfigDict

from src.utilities.text import format_dict_key_to_camel_case


class BaseSchemaModel(pydantic.BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        populate_by_name=True,
        alias_generator=format_dict_key_to_camel_case,
    )
