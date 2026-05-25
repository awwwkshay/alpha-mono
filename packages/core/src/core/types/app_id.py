from typing import Annotated
from pydantic import StringConstraints

AppId = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

__all__ = ["AppId"]
