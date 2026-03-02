from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DocumentCreate(BaseModel):
    title: str
    content: Optional[dict] = None
    metadata: Optional[dict] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[dict] = None
    metadata: Optional[dict] = None


class ComponentCreate(BaseModel):
    name: str
    component_schema: dict = Field(alias="schema")
    template: str
    style_contract: Optional[dict] = None
    default_styles: Optional[dict] = None

    model_config = {"populate_by_name": True}


class ComponentUpdate(BaseModel):
    component_schema: Optional[dict] = Field(default=None, alias="schema")
    template: Optional[str] = None
    style_contract: Optional[dict] = None
    default_styles: Optional[dict] = None

    model_config = {"populate_by_name": True}


class ThemeCreate(BaseModel):
    name: str
    variables: dict
    is_default: bool = False


class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    variables: Optional[dict] = None
    is_default: Optional[bool] = None
