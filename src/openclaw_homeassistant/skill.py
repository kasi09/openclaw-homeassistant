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
    - get_entities_by_domain: List entities filtered by domain
    - fire_event: Fire an event on the HA event bus
    - get_logbook: Get logbook entries
    - render_template: Render a Jinja2 template
    - get_automations: List or control automations
    - device_summary: Human-readable summary of all devices
    - health_check: Check Home Assistant reachability
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

    def _request_text(
        self,
        method: str,
        path: str,
        json: Optional[dict[str, Any]] = None,
    ) -> str:
        """Make an authenticated request that returns plain text."""
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

        return response.text

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
        elif action == "get_entities_by_domain":
            return self._get_entities_by_domain(parameters)
        elif action == "fire_event":
            return self._fire_event(parameters)
        elif action == "get_logbook":
            return self._get_logbook(parameters)
        elif action == "render_template":
            return self._render_template(parameters)
        elif action == "get_automations":
            return self._get_automations(parameters)
        elif action == "device_summary":
            return self._device_summary()
        elif action == "health_check":
            return self._health_check()
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

    def _get_entities_by_domain(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """List entities filtered by domain prefix."""
        domain = parameters.get("domain")
        if not domain:
            raise ValueError("Missing required parameter: domain")

        states = self._request("GET", "states")
        prefix = f"{domain}."
        filtered = [s for s in states if s.get("entity_id", "").startswith(prefix)]
        return {
            "domain": domain,
            "states": [
                {
                    "entity_id": s["entity_id"],
                    "state": s["state"],
                    "attributes": s.get("attributes", {}),
                    "last_changed": s.get("last_changed", ""),
                }
                for s in filtered
            ],
            "count": len(filtered),
        }

    def _fire_event(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Fire an event on the Home Assistant event bus."""
        event_type = parameters.get("event_type")
        if not event_type:
            raise ValueError("Missing required parameter: event_type")

        event_data = parameters.get("event_data")
        body = event_data if isinstance(event_data, dict) else None

        result = self._request("POST", f"events/{event_type}", json=body)
        return {
            "event_type": event_type,
            "message": result.get("message", ""),
        }

    def _get_logbook(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get logbook entries."""
        start = parameters.get("start", "")
        path = f"logbook/{start}" if start else "logbook"

        query_parts: list[str] = []
        entity = parameters.get("entity")
        if entity:
            query_parts.append(f"entity={entity}")
        end = parameters.get("end")
        if end:
            query_parts.append(f"end_time={end}")

        if query_parts:
            path += "?" + "&".join(query_parts)

        result = self._request("GET", path)
        entries = result if isinstance(result, list) else []
        return {
            "entries": [
                {
                    "when": e.get("when", ""),
                    "name": e.get("name", ""),
                    "message": e.get("message", ""),
                    "entity_id": e.get("entity_id", ""),
                    "state": e.get("state", ""),
                }
                for e in entries
            ],
            "count": len(entries),
        }

    def _render_template(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Render a Jinja2 template using Home Assistant."""
        template = parameters.get("template")
        if not template:
            raise ValueError("Missing required parameter: template")

        result = self._request_text("POST", "template", json={"template": template})
        return {
            "template": template,
            "result": result,
        }

    def _get_automations(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """List automations or control them (enable/disable/trigger)."""
        service = parameters.get("service")

        if service:
            entity_id = parameters.get("entity_id")
            if not entity_id:
                raise ValueError("Missing required parameter: entity_id")
            if service not in ("trigger", "turn_on", "turn_off"):
                raise ValueError(
                    f"Invalid automation service: {service}. "
                    "Must be 'trigger', 'turn_on', or 'turn_off'"
                )
            result = self._request(
                "POST",
                f"services/automation/{service}",
                json={"entity_id": entity_id},
            )
            return {
                "entity_id": entity_id,
                "service": service,
                "result": result if isinstance(result, list) else [],
            }

        states = self._request("GET", "states")
        automations = [s for s in states if s.get("entity_id", "").startswith("automation.")]
        return {
            "automations": [
                {
                    "entity_id": a["entity_id"],
                    "state": a["state"],
                    "attributes": a.get("attributes", {}),
                    "last_changed": a.get("last_changed", ""),
                }
                for a in automations
            ],
            "count": len(automations),
        }

    def _device_summary(self) -> dict[str, Any]:
        """Human-readable summary of all devices grouped by domain."""
        states = self._request("GET", "states")
        domains: dict[str, dict[str, int]] = {}
        for s in states:
            entity_id = s.get("entity_id", "")
            if "." not in entity_id:
                continue
            domain = entity_id.split(".", 1)[0]
            state = s.get("state", "unknown")
            if domain not in domains:
                domains[domain] = {}
            domains[domain][state] = domains[domain].get(state, 0) + 1

        summary: list[dict[str, Any]] = []
        for domain, state_counts in sorted(domains.items()):
            total = sum(state_counts.values())
            summary.append(
                {
                    "domain": domain,
                    "total": total,
                    "states": state_counts,
                }
            )

        return {
            "summary": summary,
            "total_entities": len(states),
            "total_domains": len(domains),
        }

    def _health_check(self) -> dict[str, Any]:
        """Check Home Assistant reachability and status."""
        api_status = self._request("GET", "")
        config = self._request("GET", "config")
        return {
            "reachable": True,
            "message": api_status.get("message", ""),
            "version": config.get("version", ""),
            "location_name": config.get("location_name", ""),
        }
