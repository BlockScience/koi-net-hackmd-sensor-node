from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


def unix_ms_to_datetime(value: Union[int, datetime, None]) -> Union[datetime, None]:
    """Convert Unix timestamp in milliseconds to datetime object."""
    if value is None or value == 0:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, int):
        return datetime.fromtimestamp(value / 1000)
    return value  # Leave as is if not int/datetime


def datetime_to_unix_ms(value: Union[datetime, int, None]) -> Union[int, None]:
    """Convert datetime object to Unix timestamp in milliseconds."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    return value


class HackMDUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    name: str
    user_path: Optional[str] = Field(alias="userPath", default=None)
    photo: str
    biography: Optional[str] = None


class HackMDNoteObject(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    note_id: str = Field(alias="id")
    title: str
    tags: Optional[list[str]] = Field(default_factory=list)
    created_at: Optional[int] = Field(default=None, alias="createdAt")
    title_updated_at: Optional[int] = Field(default=None, alias="titleUpdatedAt")
    tags_updated_at: Optional[int] = Field(default=None, alias="tagsUpdatedAt")
    publish_type: str = Field(alias="publishType")
    published_at: Optional[int] = Field(default=None, alias="publishedAt")
    permalink: Optional[str] = Field(default=None)
    publish_link: Optional[str] = Field(default=None, alias="publishLink")
    short_id: Optional[str] = Field(default=None, alias="shortId")
    content: Optional[str] = Field(default=None)
    last_changed_at: Optional[int] = Field(default=None, alias="lastChangedAt")
    last_change_user: Optional[HackMDUser] = Field(default=None, alias="lastChangeUser")
    user_path: Optional[str] = Field(default=None, alias="userPath")
    team_path: Optional[str] = Field(default=None, alias="teamPath")

    @field_validator('created_at', mode='before')
    @classmethod
    def validate_created_at(cls, value):
        if isinstance(value, datetime):
            return datetime_to_unix_ms(value)
        return value

    @field_validator('last_changed_at', mode='before')
    @classmethod
    def validate_last_changed_at(cls, value):
        if isinstance(value, datetime):
            return datetime_to_unix_ms(value)
        return value
    
    @property
    def workspace_id(self) -> Optional[str]:
        """Alias for team_path for backward compatibility."""
        return self.team_path
