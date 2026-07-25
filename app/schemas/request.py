from pydantic import BaseModel, AnyHttpUrl, field_validator

from app.core.config import settings


class AuditRequest(BaseModel):
    url: AnyHttpUrl

    @field_validator("url")
    @classmethod
    def check_url_length(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if len(str(value)) > settings.max_url_length:
            raise ValueError(
                f"url exceeds maximum length of {settings.max_url_length} characters"
            )
        return value
