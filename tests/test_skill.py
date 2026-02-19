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
