"""Tests for SystemConfigRepository."""

from app.models.system_config import SystemConfig


class TestSystemConfigRepositoryCreate:
    def test_create_config_success(self, system_config_repository) -> None:
        config = SystemConfig(key="site.name", value={"title": "EasyOrder"})
        created = system_config_repository.create(config)
        assert created.id is not None
        assert created.key == "site.name"
        assert created.value == {"title": "EasyOrder"}


class TestSystemConfigRepositoryGetById:
    def test_get_by_id_found(self, system_config_repository) -> None:
        config = system_config_repository.create(SystemConfig(key="k", value={"v": 1}))
        result = system_config_repository.get_by_id(config.id)
        assert result is not None
        assert result.key == "k"

    def test_get_by_id_not_found(self, system_config_repository) -> None:
        assert system_config_repository.get_by_id(999) is None


class TestSystemConfigRepositoryGetByKey:
    def test_get_by_key_found(self, system_config_repository) -> None:
        system_config_repository.create(SystemConfig(key="site.name", value={"title": "EO"}))
        result = system_config_repository.get_by_key("site.name")
        assert result is not None
        assert result.value == {"title": "EO"}

    def test_get_by_key_not_found(self, system_config_repository) -> None:
        assert system_config_repository.get_by_key("nonexistent") is None


class TestSystemConfigRepositoryListAll:
    def test_list_all_with_data(self, system_config_repository) -> None:
        system_config_repository.create(SystemConfig(key="k1", value={"a": 1}))
        system_config_repository.create(SystemConfig(key="k2", value={"b": 2}))
        result = system_config_repository.list_all()
        assert len(result) == 2
