"""Tests for OAuth Client API endpoints."""


class TestCreateOAuthClient:
    def test_create_client_success(self, client, super_admin_token_headers) -> None:
        resp = client.post(
            "/api/v1/oauth-clients/",
            json={"name": "My App"},
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "client_id" in data
        assert "client_secret" in data
        assert len(data["client_secret"]) > 0

    def test_create_client_requires_super_admin(self, client, admin_token_headers) -> None:
        resp = client.post("/api/v1/oauth-clients/", json={"name": "App"}, headers=admin_token_headers)
        assert resp.status_code == 403

    def test_create_client_requires_auth(self, client) -> None:
        resp = client.post("/api/v1/oauth-clients/", json={"name": "App"})
        assert resp.status_code == 401


class TestListClients:
    def test_list_clients_success(self, client, super_admin_token_headers) -> None:
        resp = client.get("/api/v1/oauth-clients/", headers=super_admin_token_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_clients_requires_super_admin(self, client, admin_token_headers) -> None:
        resp = client.get("/api/v1/oauth-clients/", headers=admin_token_headers)
        assert resp.status_code == 403


class TestUpdateStatus:
    def test_update_status_success(self, client, super_admin_token_headers, db_session) -> None:
        # Create a client first
        resp = client.post(
            "/api/v1/oauth-clients/",
            json={"name": "App"},
            headers=super_admin_token_headers,
        )
        string_client_id = resp.json()["client_id"]
        # Look up DB id from the list endpoint
        resp = client.get("/api/v1/oauth-clients/", headers=super_admin_token_headers)
        db_id = next(c["id"] for c in resp.json() if c["client_id"] == string_client_id)

        resp = client.put(
            f"/api/v1/oauth-clients/{db_id}/status?new_status=inactive",
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "inactive"

    def test_update_status_not_found(self, client, super_admin_token_headers) -> None:
        resp = client.put(
            "/api/v1/oauth-clients/999/status?new_status=inactive",
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 404


class TestRegenerateSecret:
    def test_regenerate_secret_success(self, client, super_admin_token_headers) -> None:
        # Create a client first
        resp = client.post(
            "/api/v1/oauth-clients/",
            json={"name": "App"},
            headers=super_admin_token_headers,
        )
        string_client_id = resp.json()["client_id"]
        original_secret = resp.json()["client_secret"]
        # Look up DB id from list
        resp = client.get("/api/v1/oauth-clients/", headers=super_admin_token_headers)
        db_id = next(c["id"] for c in resp.json() if c["client_id"] == string_client_id)

        resp = client.post(
            f"/api/v1/oauth-clients/{db_id}/regenerate",
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 200
        new_secret = resp.json()["client_secret"]
        assert new_secret != original_secret

    def test_regenerate_secret_not_found(self, client, super_admin_token_headers) -> None:
        resp = client.post("/api/v1/oauth-clients/999/regenerate", headers=super_admin_token_headers)
        assert resp.status_code == 404
