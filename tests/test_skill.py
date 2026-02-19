"""Tests for HomeAssistantSkill."""

from unittest.mock import patch

import httpx
import pytest
from openclaw_python_skill import SkillInput

from openclaw_homeassistant import HomeAssistantSkill

BASE_URL = "http://homeassistant.local:8123"
TOKEN = "test-token-abc123"


@pytest.fixture
def skill():
    return HomeAssistantSkill(base_url=BASE_URL, token=TOKEN)


# --- get_states ---


@pytest.mark.asyncio
async def test_get_states(skill):
    mock_response = [
        {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"brightness": 255},
            "last_changed": "2024-01-01T12:00:00+00:00",
        },
        {
            "entity_id": "sensor.temperature",
            "state": "21.5",
            "attributes": {"unit_of_measurement": "°C"},
            "last_changed": "2024-01-01T12:05:00+00:00",
        },
    ]

    with patch.object(skill, "_request", return_value=mock_response):
        input_data = SkillInput(action="get_states", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["count"] == 2
    assert output.result["states"][0]["entity_id"] == "light.living_room"
    assert output.result["states"][0]["state"] == "on"
    assert output.result["states"][1]["entity_id"] == "sensor.temperature"


@pytest.mark.asyncio
async def test_get_states_empty(skill):
    with patch.object(skill, "_request", return_value=[]):
        input_data = SkillInput(action="get_states", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["count"] == 0
    assert output.result["states"] == []


# --- get_state ---


@pytest.mark.asyncio
async def test_get_state(skill):
    mock_response = {
        "entity_id": "light.living_room",
        "state": "on",
        "attributes": {"brightness": 200, "friendly_name": "Living Room"},
        "last_changed": "2024-01-01T12:00:00+00:00",
    }

    with patch.object(skill, "_request", return_value=mock_response) as mock_req:
        input_data = SkillInput(action="get_state", parameters={"entity_id": "light.living_room"})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["entity_id"] == "light.living_room"
    assert output.result["state"] == "on"
    assert output.result["attributes"]["brightness"] == 200
    mock_req.assert_called_once_with("GET", "states/light.living_room")


@pytest.mark.asyncio
async def test_get_state_missing_entity_id(skill):
    input_data = SkillInput(action="get_state", parameters={})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "entity_id" in output.error.lower()


@pytest.mark.asyncio
async def test_get_state_not_found(skill):
    with patch.object(skill, "_request", side_effect=ValueError("Not found: states/fake.entity")):
        input_data = SkillInput(action="get_state", parameters={"entity_id": "fake.entity"})
        output = await skill.execute(input_data)

    assert output.success is False
    assert "not found" in output.error.lower()


# --- call_service ---


@pytest.mark.asyncio
async def test_call_service_light_on(skill):
    mock_response = [
        {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {"brightness": 255},
        }
    ]

    with patch.object(skill, "_request", return_value=mock_response) as mock_req:
        input_data = SkillInput(
            action="call_service",
            parameters={
                "domain": "light",
                "service": "turn_on",
                "entity_id": "light.living_room",
            },
        )
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["domain"] == "light"
    assert output.result["service"] == "turn_on"
    assert len(output.result["result"]) == 1
    mock_req.assert_called_once_with(
        "POST",
        "services/light/turn_on",
        json={"entity_id": "light.living_room"},
    )


@pytest.mark.asyncio
async def test_call_service_with_data(skill):
    with patch.object(skill, "_request", return_value=[]) as mock_req:
        input_data = SkillInput(
            action="call_service",
            parameters={
                "domain": "light",
                "service": "turn_on",
                "entity_id": "light.bedroom",
                "data": {"brightness": 128, "color_name": "blue"},
            },
        )
        output = await skill.execute(input_data)

    assert output.success is True
    mock_req.assert_called_once_with(
        "POST",
        "services/light/turn_on",
        json={
            "entity_id": "light.bedroom",
            "brightness": 128,
            "color_name": "blue",
        },
    )


@pytest.mark.asyncio
async def test_call_service_missing_domain(skill):
    input_data = SkillInput(action="call_service", parameters={"service": "turn_on"})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "domain" in output.error.lower()


@pytest.mark.asyncio
async def test_call_service_missing_service(skill):
    input_data = SkillInput(action="call_service", parameters={"domain": "light"})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "service" in output.error.lower()


# --- get_history ---


@pytest.mark.asyncio
async def test_get_history(skill):
    mock_response = [
        [
            {
                "state": "on",
                "last_changed": "2024-01-01T10:00:00+00:00",
                "attributes": {},
            },
            {
                "state": "off",
                "last_changed": "2024-01-01T11:00:00+00:00",
                "attributes": {},
            },
        ]
    ]

    with patch.object(skill, "_request", return_value=mock_response) as mock_req:
        input_data = SkillInput(action="get_history", parameters={"entity_id": "light.living_room"})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["entity_id"] == "light.living_room"
    assert output.result["count"] == 2
    assert output.result["history"][0]["state"] == "on"
    assert output.result["history"][1]["state"] == "off"
    mock_req.assert_called_once()
    call_path = mock_req.call_args[0][1]
    assert "filter_entity_id=light.living_room" in call_path


@pytest.mark.asyncio
async def test_get_history_with_time_range(skill):
    with patch.object(skill, "_request", return_value=[[]]) as mock_req:
        input_data = SkillInput(
            action="get_history",
            parameters={
                "entity_id": "sensor.temp",
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-02T00:00:00",
            },
        )
        output = await skill.execute(input_data)

    assert output.success is True
    call_path = mock_req.call_args[0][1]
    assert "2024-01-01T00:00:00" in call_path
    assert "end_time=2024-01-02T00:00:00" in call_path


@pytest.mark.asyncio
async def test_get_history_missing_entity_id(skill):
    input_data = SkillInput(action="get_history", parameters={})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "entity_id" in output.error.lower()


# --- get_config ---


@pytest.mark.asyncio
async def test_get_config(skill):
    mock_response = {
        "location_name": "Home",
        "latitude": 52.52,
        "longitude": 13.405,
        "elevation": 34,
        "unit_system": {"temperature": "°C", "length": "km"},
        "time_zone": "Europe/Berlin",
        "version": "2024.1.0",
        "components": ["light", "sensor", "automation"],
    }

    with patch.object(skill, "_request", return_value=mock_response):
        input_data = SkillInput(action="get_config", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["location_name"] == "Home"
    assert output.result["version"] == "2024.1.0"
    assert output.result["time_zone"] == "Europe/Berlin"
    assert "light" in output.result["components"]


# --- Error handling ---


@pytest.mark.asyncio
async def test_unknown_action(skill):
    input_data = SkillInput(action="invalid", parameters={})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "Unknown action" in output.error


@pytest.mark.asyncio
async def test_auth_error(skill):
    with patch.object(
        skill, "_request", side_effect=ValueError("Authentication failed: invalid or expired token")
    ):
        input_data = SkillInput(action="get_states", parameters={})
        output = await skill.execute(input_data)

    assert output.success is False
    assert "authentication" in output.error.lower()


@pytest.mark.asyncio
async def test_network_error(skill):
    with patch.object(skill, "_request", side_effect=httpx.ConnectError("Connection refused")):
        input_data = SkillInput(action="get_states", parameters={})
        output = await skill.execute(input_data)

    assert output.success is False
    assert output.error is not None


# --- _request integration ---


def test_request_builds_correct_url(skill):
    """Verify that _request builds the correct URL with auth headers."""
    import unittest.mock as mock

    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"key": "value"}

    mock_client = mock.MagicMock()
    mock_client.__enter__ = mock.MagicMock(return_value=mock_client)
    mock_client.__exit__ = mock.MagicMock(return_value=False)
    mock_client.request.return_value = mock_response

    with mock.patch("httpx.Client", return_value=mock_client) as mock_cls:
        result = skill._request("GET", "states")

    assert result == {"key": "value"}
    mock_cls.assert_called_once()
    call_kwargs = mock_cls.call_args[1]
    assert call_kwargs["headers"]["Authorization"] == f"Bearer {TOKEN}"
    mock_client.request.assert_called_once_with("GET", f"{BASE_URL}/api/states", json=None)


def test_request_raises_on_401(skill):
    import unittest.mock as mock

    mock_response = mock.MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_client = mock.MagicMock()
    mock_client.__enter__ = mock.MagicMock(return_value=mock_client)
    mock_client.__exit__ = mock.MagicMock(return_value=False)
    mock_client.request.return_value = mock_response

    with mock.patch("httpx.Client", return_value=mock_client):
        with pytest.raises(ValueError, match="Authentication failed"):
            skill._request("GET", "states")


def test_request_raises_on_404(skill):
    import unittest.mock as mock

    mock_response = mock.MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not found"

    mock_client = mock.MagicMock()
    mock_client.__enter__ = mock.MagicMock(return_value=mock_client)
    mock_client.__exit__ = mock.MagicMock(return_value=False)
    mock_client.request.return_value = mock_response

    with mock.patch("httpx.Client", return_value=mock_client):
        with pytest.raises(ValueError, match="Not found"):
            skill._request("GET", "states/fake.entity")


# --- describe ---


def test_describe(skill):
    meta = skill.describe()
    assert meta["name"] == "homeassistant"
    assert meta["version"] == "1.0.0"


def test_constructor_strips_trailing_slash():
    s = HomeAssistantSkill(base_url="http://ha.local:8123/", token="tok")
    assert s.base_url == "http://ha.local:8123"


# --- get_entities_by_domain ---


MIXED_STATES = [
    {"entity_id": "light.living_room", "state": "on", "attributes": {}, "last_changed": ""},
    {"entity_id": "light.bedroom", "state": "off", "attributes": {}, "last_changed": ""},
    {"entity_id": "sensor.temperature", "state": "21.5", "attributes": {}, "last_changed": ""},
    {"entity_id": "light_strip.hall", "state": "on", "attributes": {}, "last_changed": ""},
    {"entity_id": "automation.morning", "state": "on", "attributes": {}, "last_changed": ""},
    {"entity_id": "automation.night", "state": "off", "attributes": {}, "last_changed": ""},
]


@pytest.mark.asyncio
async def test_get_entities_by_domain(skill):
    with patch.object(skill, "_request", return_value=MIXED_STATES):
        input_data = SkillInput(action="get_entities_by_domain", parameters={"domain": "light"})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["domain"] == "light"
    assert output.result["count"] == 2
    ids = [s["entity_id"] for s in output.result["states"]]
    assert "light.living_room" in ids
    assert "light.bedroom" in ids


@pytest.mark.asyncio
async def test_get_entities_by_domain_empty(skill):
    with patch.object(skill, "_request", return_value=MIXED_STATES):
        input_data = SkillInput(action="get_entities_by_domain", parameters={"domain": "climate"})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["count"] == 0


@pytest.mark.asyncio
async def test_get_entities_by_domain_missing_domain(skill):
    input_data = SkillInput(action="get_entities_by_domain", parameters={})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "domain" in output.error.lower()


@pytest.mark.asyncio
async def test_get_entities_by_domain_no_partial_match(skill):
    """Ensure 'light_strip.hall' does NOT match domain 'light'."""
    with patch.object(skill, "_request", return_value=MIXED_STATES):
        input_data = SkillInput(action="get_entities_by_domain", parameters={"domain": "light"})
        output = await skill.execute(input_data)

    ids = [s["entity_id"] for s in output.result["states"]]
    assert "light_strip.hall" not in ids


# --- fire_event ---


@pytest.mark.asyncio
async def test_fire_event(skill):
    mock_response = {"message": "Event my_event fired."}
    with patch.object(skill, "_request", return_value=mock_response) as mock_req:
        input_data = SkillInput(
            action="fire_event",
            parameters={"event_type": "my_event", "event_data": {"key": "value"}},
        )
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["event_type"] == "my_event"
    assert "fired" in output.result["message"]
    mock_req.assert_called_once_with("POST", "events/my_event", json={"key": "value"})


@pytest.mark.asyncio
async def test_fire_event_without_data(skill):
    mock_response = {"message": "Event test fired."}
    with patch.object(skill, "_request", return_value=mock_response) as mock_req:
        input_data = SkillInput(action="fire_event", parameters={"event_type": "test"})
        output = await skill.execute(input_data)

    assert output.success is True
    mock_req.assert_called_once_with("POST", "events/test", json=None)


@pytest.mark.asyncio
async def test_fire_event_missing_event_type(skill):
    input_data = SkillInput(action="fire_event", parameters={})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "event_type" in output.error.lower()


@pytest.mark.asyncio
async def test_fire_event_api_error(skill):
    with patch.object(skill, "_request", side_effect=ValueError("HTTP 500: Internal")):
        input_data = SkillInput(action="fire_event", parameters={"event_type": "bad_event"})
        output = await skill.execute(input_data)

    assert output.success is False


# --- get_logbook ---


@pytest.mark.asyncio
async def test_get_logbook(skill):
    mock_response = [
        {
            "when": "2024-01-01T10:00:00",
            "name": "Light",
            "message": "turned on",
            "entity_id": "light.living_room",
            "state": "on",
        },
    ]
    with patch.object(skill, "_request", return_value=mock_response):
        input_data = SkillInput(action="get_logbook", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["count"] == 1
    assert output.result["entries"][0]["name"] == "Light"


@pytest.mark.asyncio
async def test_get_logbook_with_entity(skill):
    with patch.object(skill, "_request", return_value=[]) as mock_req:
        input_data = SkillInput(action="get_logbook", parameters={"entity": "light.living_room"})
        output = await skill.execute(input_data)

    assert output.success is True
    call_path = mock_req.call_args[0][1]
    assert "entity=light.living_room" in call_path


@pytest.mark.asyncio
async def test_get_logbook_with_time_range(skill):
    with patch.object(skill, "_request", return_value=[]) as mock_req:
        input_data = SkillInput(
            action="get_logbook",
            parameters={"start": "2024-01-01T00:00:00", "end": "2024-01-02T00:00:00"},
        )
        output = await skill.execute(input_data)

    assert output.success is True
    call_path = mock_req.call_args[0][1]
    assert "logbook/2024-01-01T00:00:00" in call_path
    assert "end_time=2024-01-02T00:00:00" in call_path


@pytest.mark.asyncio
async def test_get_logbook_empty(skill):
    with patch.object(skill, "_request", return_value=[]):
        input_data = SkillInput(action="get_logbook", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["count"] == 0


@pytest.mark.asyncio
async def test_get_logbook_with_all_params(skill):
    with patch.object(skill, "_request", return_value=[]) as mock_req:
        input_data = SkillInput(
            action="get_logbook",
            parameters={
                "entity": "sensor.temp",
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-02T00:00:00",
            },
        )
        await skill.execute(input_data)

    call_path = mock_req.call_args[0][1]
    assert "entity=sensor.temp" in call_path
    assert "end_time=2024-01-02T00:00:00" in call_path
    assert "logbook/2024-01-01T00:00:00" in call_path


# --- render_template ---


@pytest.mark.asyncio
async def test_render_template(skill):
    with patch.object(skill, "_request_text", return_value="21.5") as mock_req:
        input_data = SkillInput(
            action="render_template",
            parameters={"template": "{{ states('sensor.temp') }}"},
        )
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["result"] == "21.5"
    assert output.result["template"] == "{{ states('sensor.temp') }}"
    mock_req.assert_called_once_with(
        "POST", "template", json={"template": "{{ states('sensor.temp') }}"}
    )


@pytest.mark.asyncio
async def test_render_template_missing_template(skill):
    input_data = SkillInput(action="render_template", parameters={})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "template" in output.error.lower()


@pytest.mark.asyncio
async def test_render_template_empty_result(skill):
    with patch.object(skill, "_request_text", return_value=""):
        input_data = SkillInput(action="render_template", parameters={"template": "{{ none }}"})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["result"] == ""


# --- _request_text ---


def test_request_text_returns_text(skill):
    import unittest.mock as mock

    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.text = "rendered output"

    mock_client = mock.MagicMock()
    mock_client.__enter__ = mock.MagicMock(return_value=mock_client)
    mock_client.__exit__ = mock.MagicMock(return_value=False)
    mock_client.request.return_value = mock_response

    with mock.patch("httpx.Client", return_value=mock_client):
        result = skill._request_text("POST", "template", json={"template": "test"})

    assert result == "rendered output"


def test_request_text_raises_on_401(skill):
    import unittest.mock as mock

    mock_response = mock.MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_client = mock.MagicMock()
    mock_client.__enter__ = mock.MagicMock(return_value=mock_client)
    mock_client.__exit__ = mock.MagicMock(return_value=False)
    mock_client.request.return_value = mock_response

    with mock.patch("httpx.Client", return_value=mock_client):
        with pytest.raises(ValueError, match="Authentication failed"):
            skill._request_text("POST", "template")


# --- get_automations ---


@pytest.mark.asyncio
async def test_get_automations_list(skill):
    with patch.object(skill, "_request", return_value=MIXED_STATES):
        input_data = SkillInput(action="get_automations", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["count"] == 2
    ids = [a["entity_id"] for a in output.result["automations"]]
    assert "automation.morning" in ids
    assert "automation.night" in ids


@pytest.mark.asyncio
async def test_get_automations_list_empty(skill):
    states = [{"entity_id": "light.x", "state": "on", "attributes": {}, "last_changed": ""}]
    with patch.object(skill, "_request", return_value=states):
        input_data = SkillInput(action="get_automations", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["count"] == 0


@pytest.mark.asyncio
async def test_get_automations_trigger(skill):
    with patch.object(skill, "_request", return_value=[]) as mock_req:
        input_data = SkillInput(
            action="get_automations",
            parameters={"service": "trigger", "entity_id": "automation.morning"},
        )
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["service"] == "trigger"
    mock_req.assert_called_once_with(
        "POST", "services/automation/trigger", json={"entity_id": "automation.morning"}
    )


@pytest.mark.asyncio
async def test_get_automations_turn_on(skill):
    with patch.object(skill, "_request", return_value=[]):
        input_data = SkillInput(
            action="get_automations",
            parameters={"service": "turn_on", "entity_id": "automation.night"},
        )
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["service"] == "turn_on"


@pytest.mark.asyncio
async def test_get_automations_turn_off(skill):
    with patch.object(skill, "_request", return_value=[]):
        input_data = SkillInput(
            action="get_automations",
            parameters={"service": "turn_off", "entity_id": "automation.night"},
        )
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["service"] == "turn_off"


@pytest.mark.asyncio
async def test_get_automations_service_missing_entity_id(skill):
    input_data = SkillInput(action="get_automations", parameters={"service": "trigger"})
    output = await skill.execute(input_data)

    assert output.success is False
    assert "entity_id" in output.error.lower()


@pytest.mark.asyncio
async def test_get_automations_invalid_service(skill):
    input_data = SkillInput(
        action="get_automations",
        parameters={"service": "delete", "entity_id": "automation.x"},
    )
    output = await skill.execute(input_data)

    assert output.success is False
    assert "invalid automation service" in output.error.lower()


# --- device_summary ---


@pytest.mark.asyncio
async def test_device_summary(skill):
    with patch.object(skill, "_request", return_value=MIXED_STATES):
        input_data = SkillInput(action="device_summary", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["total_entities"] == 6
    domains = {s["domain"]: s for s in output.result["summary"]}
    assert domains["light"]["total"] == 2
    assert domains["light"]["states"]["on"] == 1
    assert domains["light"]["states"]["off"] == 1


@pytest.mark.asyncio
async def test_device_summary_empty(skill):
    with patch.object(skill, "_request", return_value=[]):
        input_data = SkillInput(action="device_summary", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["total_entities"] == 0
    assert output.result["total_domains"] == 0


@pytest.mark.asyncio
async def test_device_summary_multiple_domains(skill):
    with patch.object(skill, "_request", return_value=MIXED_STATES):
        input_data = SkillInput(action="device_summary", parameters={})
        output = await skill.execute(input_data)

    domain_names = [s["domain"] for s in output.result["summary"]]
    assert "light" in domain_names
    assert "sensor" in domain_names
    assert "automation" in domain_names
    assert domain_names == sorted(domain_names)


# --- health_check ---


@pytest.mark.asyncio
async def test_health_check(skill):
    def mock_request(method, path, **kwargs):
        if path == "":
            return {"message": "API running."}
        elif path == "config":
            return {"version": "2024.1.0", "location_name": "Home"}
        return {}

    with patch.object(skill, "_request", side_effect=mock_request):
        input_data = SkillInput(action="health_check", parameters={})
        output = await skill.execute(input_data)

    assert output.success is True
    assert output.result["reachable"] is True
    assert output.result["version"] == "2024.1.0"
    assert output.result["message"] == "API running."


@pytest.mark.asyncio
async def test_health_check_api_down(skill):
    with patch.object(skill, "_request", side_effect=httpx.ConnectError("Connection refused")):
        input_data = SkillInput(action="health_check", parameters={})
        output = await skill.execute(input_data)

    assert output.success is False


@pytest.mark.asyncio
async def test_health_check_partial(skill):
    call_count = 0

    def mock_request(method, path, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"message": "API running."}
        raise ValueError("Config endpoint failed")

    with patch.object(skill, "_request", side_effect=mock_request):
        input_data = SkillInput(action="health_check", parameters={})
        output = await skill.execute(input_data)

    assert output.success is False
