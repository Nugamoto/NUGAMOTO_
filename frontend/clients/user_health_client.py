"""API client for User Health management."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class UserHealthClient(BaseClient):
    """Client for /v1/users/{user_id}/health-profile endpoints."""

    BASE_PATH = "/v1/users"

    # ---------- CRUD -------------------------------------------------
    def create_user_health_profile(self, user_id: int, profile_data: dict[str, Any]) -> dict[str, Any]:
        return self.post(f"{self.BASE_PATH}/{user_id}/health-profile", json_data=profile_data)

    def get_user_health_profile(self, user_id: int) -> dict[str, Any]:
        return self.get(f"{self.BASE_PATH}/{user_id}/health-profile")

    def update_user_health_profile(self, user_id: int, profile_data: dict[str, Any]) -> dict[str, Any]:
        return self.patch(f"{self.BASE_PATH}/{user_id}/health-profile", json_data=profile_data)

    def get_all_health_profiles_summary(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        return self.get(f"{self.BASE_PATH}/health-profiles/summary", params={"skip": skip, "limit": limit})

    def search_health_profiles(
            self,
            min_age: int | None = None,
            max_age: int | None = None,
            gender: str | None = None,
            activity_level: str | None = None,
            min_bmi: float | None = None,
            max_bmi: float | None = None
    ) -> list[dict[str, Any]]:
        params = {}
        if min_age is not None:
            params["min_age"] = min_age
        if max_age is not None:
            params["max_age"] = max_age
        if gender is not None:
            params["gender"] = gender
        if activity_level is not None:
            params["activity_level"] = activity_level
        if min_bmi is not None:
            params["min_bmi"] = min_bmi
        if max_bmi is not None:
            params["max_bmi"] = max_bmi

        return self.get(f"{self.BASE_PATH}/health-profiles/search", params=params)