"""Tests for BaseRepository CRUD operations using Plan as a representative model."""

from app.models.plan import Plan
from app.repositories.base import BaseRepository


class TestBaseRepositoryCreate:
    def test_create_sets_autoincrement_id(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        plan = Plan(name="Basic", cycle="monthly", base_price=999)
        created = repo.create(plan)
        assert created.id is not None
        assert created.id == 1

    def test_create_persists_all_fields(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        plan = Plan(name="Pro", cycle="yearly", base_price=9999)
        created = repo.create(plan)
        assert created.name == "Pro"
        assert created.cycle == "yearly"
        assert created.base_price == 9999


class TestBaseRepositoryGetById:
    def test_get_by_id_found(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        plan = repo.create(Plan(name="Basic", cycle="monthly", base_price=999))
        result = repo.get_by_id(plan.id)
        assert result is not None
        assert result.name == "Basic"

    def test_get_by_id_not_found(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        assert repo.get_by_id(999) is None


class TestBaseRepositoryListAll:
    def test_list_all_empty(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        assert repo.list_all() == []

    def test_list_all_returns_ordered_by_id(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        repo.create(Plan(name="B", cycle="monthly", base_price=100))
        repo.create(Plan(name="A", cycle="monthly", base_price=200))
        result = repo.list_all()
        assert len(result) == 2
        assert result[0].name == "B"
        assert result[1].name == "A"


class TestBaseRepositoryUpdate:
    def test_update_persists_changes(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        plan = repo.create(Plan(name="Basic", cycle="monthly", base_price=999))
        plan.name = "Premium"
        updated = repo.update(plan)
        assert updated.name == "Premium"
        # Verify it's persisted
        assert repo.get_by_id(plan.id).name == "Premium"

    def test_update_refreshes_entity(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        plan = repo.create(Plan(name="Basic", cycle="monthly", base_price=999))
        plan.base_price = 1999
        updated = repo.update(plan)
        assert updated.base_price == 1999


class TestBaseRepositoryDelete:
    def test_delete_removes_entity(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        plan = repo.create(Plan(name="Basic", cycle="monthly", base_price=999))
        repo.delete(plan)
        assert repo.get_by_id(plan.id) is None

    def test_delete_does_not_affect_others(self, db_session) -> None:
        repo = BaseRepository(Plan, db_session)
        plan1 = repo.create(Plan(name="A", cycle="monthly", base_price=100))
        plan2 = repo.create(Plan(name="B", cycle="monthly", base_price=200))
        repo.delete(plan1)
        assert repo.get_by_id(plan1.id) is None
        assert repo.get_by_id(plan2.id) is not None
