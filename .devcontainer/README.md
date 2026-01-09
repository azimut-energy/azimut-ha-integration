# Dev Container for Azimut Energy Integration

This dev container provides a complete Home Assistant development environment for the Azimut Energy integration using Docker Compose.

## Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine + Docker Compose (Linux)
- Visual Studio Code with the "Dev Containers" extension

## Getting Started

1. Open this project in VS Code
2. When prompted, click "Reopen in Container" (or press `F1` and select `Dev Containers: Reopen in Container`)
3. Wait for the containers to build and start (first time takes a few minutes)
4. Access Home Assistant at http://localhost:8123

## Architecture

The devcontainer uses Docker Compose with two services:
- **devcontainer**: Python development environment with all tools for coding and testing
- **homeassistant**: Running Home Assistant instance with your integration mounted

Both containers share the same network, so you can access HA at `localhost:8123` from both your host and the devcontainer.

## Features

- Full Home Assistant instance running in a separate container
- Your integration automatically mounted at `/config/custom_components/azimut_energy`
- Debug logging enabled for the Azimut Energy integration
- Python 3.12 development environment with all test dependencies
- Auto-formatting on save with Black
- Linting with Pylint and Ruff
- VS Code tasks for common operations

## Development Workflow

1. Make changes to your integration code in `custom_components/azimut_energy/`
2. Restart Home Assistant to load changes:
   - Use VS Code task: `Tasks: Run Task` → `Restart Home Assistant`
   - Or from terminal: `docker restart $(docker ps -q -f name=homeassistant)`
   - Or in HA UI: Settings → System → Restart
3. View logs:
   - Use VS Code task: `Tasks: Run Task` → `Follow HA Logs`
   - Or from terminal: `docker logs -f $(docker ps -q -f name=homeassistant)`

## Testing the Integration

1. After Home Assistant starts, open http://localhost:8123 in your browser
2. Complete the initial Home Assistant onboarding
3. Go to Settings → Devices & Services
4. Click "Add Integration"
5. Search for "Azimut Energy"
6. Follow the configuration flow

## Running Tests

From the terminal in VS Code:
```bash
pytest                           # Run all tests
pytest -v                        # Verbose output
pytest --cov                     # With coverage report
```

Or use VS Code tasks: `Tasks: Run Task` → `Run Tests`

## Useful VS Code Tasks

- **Restart Home Assistant** - Restart the HA container
- **Follow HA Logs** - Stream Home Assistant logs
- **Check HA Config** - Validate Home Assistant configuration
- **Run Tests** - Execute pytest
- **Run Tests with Coverage** - Execute pytest with coverage report

## Configuration

The Home Assistant configuration is stored in `.devcontainer/configuration.yaml`. You can modify it to:
- Add MQTT brokers for testing
- Configure additional integrations
- Adjust logging levels

After modifying configuration, restart Home Assistant for changes to take effect.

## Troubleshooting

**Integration doesn't appear:**
- Check that the container is running: `docker ps`
- Verify the mount is working: `docker exec $(docker ps -q -f name=homeassistant) ls -la /config/custom_components/`
- Restart Home Assistant

**Configuration errors:**
- Check logs: Use the "Follow HA Logs" task
- Validate config: Use the "Check HA Config" task
- Verify manifest.json is valid JSON

**Container won't start:**
- Check Docker Desktop is running
- View docker compose logs: `docker compose -f .devcontainer/docker-compose.yml logs`
- Rebuild containers: `Dev Containers: Rebuild Container` from Command Palette

**Can't access Home Assistant:**
- Ensure port 8123 isn't already in use
- Check the homeassistant container is running: `docker ps | grep homeassistant`
- Try accessing http://localhost:8123 directly
