"""Tests for SystemConfigService."""

from unittest.mock import MagicMock

from app.models.system_config import SystemConfig
from app.schemas.system_config import SystemConfigCreate, SystemConfigUpdate
from app.services.system_config import SystemConfigService


def _make_config_mock(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "key": "site.name",
        "value": {"title": "EasyOrder"},
        "description": "Site title",
    }
    defaults.update(overrides)
    mock = MagicMock(spec=SystemConfig)
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestSystemConfigServiceCreateConfig:
    def test_delegates_to_repo(self, mock_system_config_repository) -> None:
        mock_system_config_repository.create.side_effect = lambda e: e
        service = SystemConfigService(mock_system_config_repository)
        config = service.create_config(SystemConfigCreate(key="site.name", value={"title": "EO"}, description="Title"))
        assert config.key == "site.name"
        assert config.value == {"title": "EO"}
        mock_system_config_repository.create.assert_called_once()


class TestSystemConfigServiceUpdateConfig:
    def test_success(self, mock_system_config_repository) -> None:
        existing = _make_config_mock()
        mock_system_config_repository.get_by_id.return_value = existing
        mock_system_config_repository.update.side_effect = lambda e: e
        service = SystemConfigService(mock_system_config_repository)
        result = service.update_config(1, SystemConfigUpdate(value={"title": "New"}))
        assert result is not None
        assert result.value == {"title": "New"}

    def test_not_found(self, mock_system_config_repository) -> None:
        mock_system_config_repository.get_by_id.return_value = None
        service = SystemConfigService(mock_system_config_repository)
        result = service.update_config(999, SystemConfigUpdate(value={"v": 1}))
        assert result is None

    def test_partial_update(self, mock_system_config_repository) -> None:
        existing = _make_config_mock(description="Original")
        mock_system_config_repository.get_by_id.return_value = existing
        mock_system_config_repository.update.side_effect = lambda e: e
        service = SystemConfigService(mock_system_config_repository)
        result = service.update_config(1, SystemConfigUpdate(value={"title": "Updated"}))
        assert result is not None
        assert result.description == "Original"


class TestSystemConfigServiceGetValue:
    def test_found(self, mock_system_config_repository) -> None:
        config = _make_config_mock()
        mock_system_config_repository.get_by_key.return_value = config
        service = SystemConfigService(mock_system_config_repository)
        result = service.get_value("site.name")
        assert result == {"title": "EasyOrder"}

    def test_not_found(self, mock_system_config_repository) -> None:
        mock_system_config_repository.get_by_key.return_value = None
        service = SystemConfigService(mock_system_config_repository)
        result = service.get_value("nonexistent")
        assert result is None
