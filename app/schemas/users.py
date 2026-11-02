from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Role = Literal["admin", "executive", "company_exec"]


class MeSchema(BaseModel):
    id: str
    email: str | None = None
    role: Role
    categories: list[str] = []


class AppUserSchema(BaseModel):
    id: str
    email: str | None = None
    created_at: datetime | None = None
    last_sign_in_at: datetime | None = None
    role: Role | None = None
    categories: list[str] = []


class UserAccessSchema(BaseModel):
    role: Role
    categories: list[str] = []

    @model_validator(mode="after")
    def check_categories(self):
        if self.role == "company_exec":
            if not self.categories:
                raise ValueError("A company exec needs at least one category")
        else:
            # Categories only scope company execs; drop stale assignments.
            self.categories = []
        return self


class UserCreateSchema(UserAccessSchema):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
