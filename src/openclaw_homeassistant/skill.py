"""Home Assistant Skill - Control your smart home via REST API."""

from typing import Any, Optional

import httpx
from openclaw_python_skill.skill import Skill


class HomeAssistantSkill(Skill):
    """Interact with Home Assistant via its REST API.

    Provides actions for:
    - get_states: List all entities and their current states
    - get_state: Get the state of a single entity
    - call_service: Call a Home Assistant service (e.g. turn on a light)
    - get_history: Get state history for an entity
    - get_config: Get Home Assistant configuration
    """

    def __init__(self, base_url: str, token: str, timeout: int = 10) -> None:
        super().__init__(name="homeassistant", version="1.0.0")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated request to the Home Assistant API."""
        url = f"{self.base_url}/api/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        with httpx.Client(headers=headers, timeout=self.timeout) as client:
            response = client.request(method, url, json=json)

        if response.status_code == 401:
            raise ValueError("Authentication failed: invalid or expired token")
        if response.status_code == 404:
            raise ValueError(f"Not found: {path}")
        if response.status_code >= 400:
            raise ValueError(f"HTTP {response.status_code}: {response.text}")

        return response.json()

    def process(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if action == "get_states":
            return self._get_states()
        elif action == "get_state":
            return self._get_state(parameters)
        elif action == "call_service":
            return self._call_service(parameters)
        elif action == "get_history":
            return self._get_history(parameters)
        elif action == "get_config":
            return self._get_config()
        else:
            raise ValueError(f"Unknown action: {action}")

    def _get_states(self) -> dict[str, Any]:
        """List all entities and their states."""
        states = self._request("GET", "states")
        return {
            "states": [
                {
                    "entity_id": s["entity_id"],
                    "state": s["state"],
                    "attributes": s.get("attributes", {}),
                    "last_changed": s.get("last_changed", ""),
                }
                for s in states
            ],
            "count": len(states),
        }

    def _get_state(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get the state of a single entity."""
        entity_id = parameters.get("entity_id")
        if not entity_id:
            raise ValueError("Missing required parameter: entity_id")

        state = self._request("GET", f"states/{entity_id}")
        return {
            "entity_id": state["entity_id"],
            "state": state["state"],
            "attributes": state.get("attributes", {}),
            "last_changed": state.get("last_changed", ""),
        }

    def _call_service(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Call a Home Assistant service."""
        domain = parameters.get("domain")
        if not domain:
            raise ValueError("Missing required parameter: domain")
        service = parameters.get("service")
        if not service:
            raise ValueError("Missing required parameter: service")

        body: dict[str, Any] = {}
        entity_id = parameters.get("entity_id")
        if entity_id:
            body["entity_id"] = entity_id

        data = parameters.get("data")
        if data and isinstance(data, dict):
            body.update(data)

        result = self._request("POST", f"services/{domain}/{service}", json=body)
        return {
            "domain": domain,
            "service": service,
            "result": result if isinstance(result, list) else [],
        }

    def _get_history(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get state history for an entity."""
        entity_id = parameters.get("entity_id")
        if not entity_id:
            raise ValueError("Missing required parameter: entity_id")

        start = parameters.get("start", "")
        path = f"history/period/{start}" if start else "history/period"
        path += f"?filter_entity_id={entity_id}"

        end = parameters.get("end")
        if end:
            path += f"&end_time={end}"

        result = self._request("GET", path)
        # HA returns a list of lists; first list is for the requested entity
        history = result[0] if isinstance(result, list) and len(result) > 0 else []

        return {
            "entity_id": entity_id,
            "history": [
                {
                    "state": entry.get("state", ""),
                    "last_changed": entry.get("last_changed", ""),
                    "attributes": entry.get("attributes", {}),
                }
                for entry in history
            ],
            "count": len(history),
        }

    def _get_config(self) -> dict[str, Any]:
        """Get Home Assistant configuration."""
        config = self._request("GET", "config")
        return {
            "location_name": config.get("location_name", ""),
            "latitude": config.get("latitude"),
            "longitude": config.get("longitude"),
            "elevation": config.get("elevation"),
            "unit_system": config.get("unit_system", {}),
            "time_zone": config.get("time_zone", ""),
            "version": config.get("version", ""),
            "components": config.get("components", []),
        }
