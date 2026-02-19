# OpenClaw Home Assistant Skill

[![Tests](https://github.com/kasi09/openclaw-homeassistant/actions/workflows/tests.yml/badge.svg)](https://github.com/kasi09/openclaw-homeassistant/actions/workflows/tests.yml)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Home Assistant integration skill for [OpenClaw](https://openclaw.ai) - Control your smart home via the Home Assistant REST API.

## Installation

```bash
git clone https://github.com/kasi09/openclaw-homeassistant.git
cd openclaw-homeassistant
pip install -e ".[dev]"
```

### Requirements

- Python 3.9+
- [openclaw-python-skill](https://github.com/kasi09/openclaw-python) >= 0.1.0
- httpx >= 0.24.0
- A running Home Assistant instance with a Long-Lived Access Token

### Getting a Home Assistant Token

1. Open your Home Assistant instance
2. Go to your **Profile** (bottom left)
3. Scroll down to **Long-Lived Access Tokens**
4. Click **Create Token** and give it a name
5. Copy the token (it's only shown once)

## Quick Start

```python
import asyncio
from openclaw_python_skill import SkillInput
from openclaw_homeassistant import HomeAssistantSkill

async def main():
    skill = HomeAssistantSkill(
        base_url="http://homeassistant.local:8123",
        token="YOUR_LONG_LIVED_ACCESS_TOKEN",
    )

    # Get all entity states
    result = await skill.execute(SkillInput(
        action="get_states", parameters={}
    ))
    for entity in result.result["states"][:5]:
        print(f"{entity['entity_id']}: {entity['state']}")

    # Turn on a light
    result = await skill.execute(SkillInput(
        action="call_service",
        parameters={
            "domain": "light",
            "service": "turn_on",
            "entity_id": "light.living_room",
            "data": {"brightness": 200},
        },
    ))
    print(f"Service called: {result.result}")

asyncio.run(main())
```

## Available Actions

| Action | Parameters | Description |
|--------|-----------|-------------|
| `get_states` | - | List all entities and their current states |
| `get_state` | `entity_id` | Get the state of a single entity |
| `call_service` | `domain`, `service`, `entity_id?`, `data?` | Call a HA service (e.g. turn on light, activate scene) |
| `get_history` | `entity_id`, `start?`, `end?` | Get state history for an entity |
| `get_config` | - | Get Home Assistant configuration |

### Examples

```python
# Get a specific entity's state
result = await skill.execute(SkillInput(
    action="get_state",
    parameters={"entity_id": "sensor.living_room_temperature"},
))
# result.result: {"entity_id": "sensor.living_room_temperature", "state": "21.5", ...}

# Set thermostat temperature
result = await skill.execute(SkillInput(
    action="call_service",
    parameters={
        "domain": "climate",
        "service": "set_temperature",
        "entity_id": "climate.living_room",
        "data": {"temperature": 22},
    },
))

# Get history for the last day
result = await skill.execute(SkillInput(
    action="get_history",
    parameters={
        "entity_id": "sensor.temperature",
        "start": "2024-01-01T00:00:00",
        "end": "2024-01-02T00:00:00",
    },
))

# Get HA configuration
result = await skill.execute(SkillInput(
    action="get_config", parameters={}
))
# result.result: {"location_name": "Home", "version": "2024.1.0", ...}
```

## Development

```bash
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format and lint
ruff format src tests
ruff check src tests

# Type checking
mypy src
```

## Project Structure

```
openclaw-homeassistant/
├── src/openclaw_homeassistant/
│   ├── __init__.py          # Package exports
│   └── skill.py             # HomeAssistantSkill
├── tests/
│   ├── conftest.py
│   └── test_skill.py        # 24 tests, all HTTP mocked
├── .github/workflows/
│   └── tests.yml            # CI: Python 3.9-3.12
├── pyproject.toml
└── LICENSE
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

<a href="https://www.buymeacoffee.com/kasi09" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

## Links

- [OpenClaw Python Skills](https://github.com/kasi09/openclaw-python) - Core skill framework
- [Home Assistant REST API Docs](https://developers.home-assistant.io/docs/api/rest/)
- [Report Issues](https://github.com/kasi09/openclaw-homeassistant/issues)
