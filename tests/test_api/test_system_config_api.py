"""Tests for System Config API endpoints."""


class TestCreateConfig:
    def test_create_config_success(self, client, super_admin_token_headers) -> None:
        resp = client.post(
            "/api/v1/system-configs/",
            json={"key": "site.name", "value": {"title": "EasyOrder"}, "description": "Site title"},
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"] == "site.name"
        assert data["value"] == {"title": "EasyOrder"}

    def test_create_config_requires_super_admin(self, client, admin_token_headers) -> None:
        resp = client.post(
            "/api/v1/system-configs/",
            json={"key": "k", "value": {"v": 1}},
            headers=admin_token_headers,
        )
        assert resp.status_code == 403

    def test_create_config_requires_auth(self, client) -> None:
        resp = client.post("/api/v1/system-configs/", json={"key": "k", "value": {"v": 1}})
        assert resp.status_code == 401


class TestListConfigs:
    def test_list_configs_success(self, client, super_admin_token_headers) -> None:
        resp = client.get("/api/v1/system-configs/", headers=super_admin_token_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_configs_requires_super_admin(self, client, admin_token_headers) -> None:
        resp = client.get("/api/v1/system-configs/", headers=admin_token_headers)
        assert resp.status_code == 403


class TestGetConfig:
    def test_get_config_found(self, client, super_admin_token_headers) -> None:
        resp = client.post(
            "/api/v1/system-configs/",
            json={"key": "site.name", "value": {"title": "EO"}},
            headers=super_admin_token_headers,
        )
        config_id = resp.json()["id"]
        resp = client.get(f"/api/v1/system-configs/{config_id}", headers=super_admin_token_headers)
        assert resp.status_code == 200
        assert resp.json()["key"] == "site.name"

    def test_get_config_not_found(self, client, super_admin_token_headers) -> None:
        resp = client.get("/api/v1/system-configs/999", headers=super_admin_token_headers)
        assert resp.status_code == 404


class TestUpdateConfig:
    def test_update_config_success(self, client, super_admin_token_headers) -> None:
        resp = client.post(
            "/api/v1/system-configs/",
            json={"key": "site.name", "value": {"title": "Old"}, "description": "desc"},
            headers=super_admin_token_headers,
        )
        config_id = resp.json()["id"]
        resp = client.put(
            f"/api/v1/system-configs/{config_id}",
            json={"value": {"title": "New"}},
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["value"] == {"title": "New"}
        assert resp.json()["description"] == "desc"

    def test_update_config_not_found(self, client, super_admin_token_headers) -> None:
        resp = client.put(
            "/api/v1/system-configs/999",
            json={"value": {"v": 1}},
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 404

    def test_update_config_requires_super_admin(self, client, admin_token_headers) -> None:
        resp = client.put("/api/v1/system-configs/1", json={"value": {"v": 1}}, headers=admin_token_headers)
        assert resp.status_code == 403
