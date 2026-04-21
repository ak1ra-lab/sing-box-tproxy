"""
Pydantic models for validating external JSON configuration files.

Two entry points are validated at CLI startup:
- ``base.json``  → :class:`BaseConfig`
- ``subscriptions.json`` → ``dict[str, SubscriptionConfig]``

``SubscriptionConfig`` is a discriminated union keyed on the ``type`` field.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)


class SelfhostDetourEntry(BaseModel):
    """One entry in the ``_selfhost_detour`` list embedded in ``base.json``."""

    model_config = ConfigDict(populate_by_name=True)

    tag_filter: str = Field(alias="filter")
    detour: str

    @field_validator("tag_filter")
    @classmethod
    def _validate_tag_filter_regex(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regex in 'filter': {exc}") from exc
        return v


class _BaseSubscription(BaseModel):
    """Fields shared by all subscription types."""

    model_config = ConfigDict(populate_by_name=True)

    sub_format: Literal["clash", "sing-box", "sip002"] = Field(
        default="sing-box", alias="format"
    )
    enabled: bool = True
    exclude: str = ""

    @field_validator("exclude")
    @classmethod
    def _validate_exclude_regex(cls, v: str) -> str:
        if v:
            try:
                re.compile(v)
            except re.error as exc:
                raise ValueError(f"Invalid regex in 'exclude': {exc}") from exc
        return v


class RemoteSubscription(_BaseSubscription):
    """Subscription fetched from one or more HTTP(S) URLs."""

    type: Literal["remote"] = "remote"
    urls: list[str] = Field(default_factory=list)
    url: str | None = None

    @model_validator(mode="after")
    def _require_at_least_one_url(self) -> RemoteSubscription:
        if not self.urls and self.url is None:
            raise ValueError("Remote subscription requires 'url' or 'urls'")
        return self


class LocalSubscription(_BaseSubscription):
    """Subscription loaded from one or more local files."""

    type: Literal["local"] = "local"
    paths: list[Path] = Field(default_factory=list)
    path: Path | None = None

    @model_validator(mode="after")
    def _require_at_least_one_path(self) -> LocalSubscription:
        if not self.paths and self.path is None:
            raise ValueError("Local subscription requires 'path' or 'paths'")
        return self


class InlineSubscription(_BaseSubscription):
    """Subscription embedded directly in the config (outbounds list or raw content)."""

    type: Literal["inline"] = "inline"
    outbounds: list[dict[str, Any]] = Field(default_factory=list)
    content: str | None = None

    @model_validator(mode="after")
    def _require_content(self) -> InlineSubscription:
        if not self.outbounds and self.content is None:
            raise ValueError("Inline subscription requires 'outbounds' or 'content'")
        return self


#: Discriminated union of all subscription variants, keyed on the ``type`` field.
SubscriptionConfig = Annotated[
    RemoteSubscription | LocalSubscription | InlineSubscription,
    Field(discriminator="type"),
]

#: TypeAdapter for validating a single ``SubscriptionConfig`` value.
subscription_adapter: TypeAdapter[SubscriptionConfig] = TypeAdapter(SubscriptionConfig)


class BaseConfig(BaseModel):
    """
    Partial model for ``base.json``.

    All sing-box fields not explicitly declared are preserved via ``extra="allow"``
    and round-trip through :meth:`model_dump`.  Internal metadata keys
    (``_selfhost_tag_pattern``, ``_selfhost_detour``) are mapped to Python-friendly
    attribute names via ``alias``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    outbounds: list[dict[str, Any]]
    selfhost_tag_pattern: str = Field(
        default=r"selfhost|自建", alias="_selfhost_tag_pattern"
    )
    selfhost_detour: list[SelfhostDetourEntry] = Field(
        default_factory=list, alias="_selfhost_detour"
    )
