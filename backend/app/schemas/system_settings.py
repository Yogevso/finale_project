"""System settings schemas"""

from typing import Any, Dict

from pydantic import BaseModel


class SystemSettingsUpdate(BaseModel):
    """Update system settings"""

    settings: Dict[str, Any]


class SystemSettingsResponse(BaseModel):
    """System settings response"""

    settings: Dict[str, Any]
