"""Tests for Admin API endpoints."""


class TestCreateAdmin:
    def test_create_admin_success(self, client, super_admin_token_headers) -> None:
        resp = client.post(
            "/api/v1/admins/",
            json={"username": "newadmin", "password": "pass123"},
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newadmin"
        assert data["role"] == "admin"

    def test_create_admin_requires_super_admin(self, client, admin_token_headers) -> None:
        resp = client.post(
            "/api/v1/admins/",
            json={"username": "newadmin", "password": "pass123"},
            headers=admin_token_headers,
        )
        assert resp.status_code == 403

    def test_create_admin_requires_auth(self, client) -> None:
        resp = client.post("/api/v1/admins/", json={"username": "newadmin", "password": "pass123"})
        assert resp.status_code == 401


class TestListAdmins:
    def test_list_admins_success(self, client, admin_token_headers) -> None:
        resp = client.get("/api/v1/admins/", headers=admin_token_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_admins_requires_auth(self, client) -> None:
        resp = client.get("/api/v1/admins/")
        assert resp.status_code == 401


class TestGetAdmin:
    def test_get_admin_found(self, client, admin_token_headers, super_admin_token_headers) -> None:
        # super_admin_token_headers already created a super_admin
        resp = client.post(
            "/api/v1/admins/",
            json={"username": "alice", "password": "pass123"},
            headers=super_admin_token_headers,
        )
        admin_id = resp.json()["id"]
        resp = client.get(f"/api/v1/admins/{admin_id}", headers=admin_token_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "alice"

    def test_get_admin_not_found(self, client, admin_token_headers) -> None:
        resp = client.get("/api/v1/admins/999", headers=admin_token_headers)
        assert resp.status_code == 404

    def test_get_admin_requires_auth(self, client) -> None:
        resp = client.get("/api/v1/admins/1")
        assert resp.status_code == 401


class TestUpdateAdmin:
    def test_update_admin_success(self, client, super_admin_token_headers) -> None:
        # Create an admin first
        resp = client.post(
            "/api/v1/admins/",
            json={"username": "bob", "password": "pass123"},
            headers=super_admin_token_headers,
        )
        admin_id = resp.json()["id"]
        resp = client.put(
            f"/api/v1/admins/{admin_id}",
            json={"display_name": "Bob Updated"},
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Bob Updated"

    def test_update_admin_not_found(self, client, super_admin_token_headers) -> None:
        resp = client.put(
            "/api/v1/admins/999",
            json={"display_name": "X"},
            headers=super_admin_token_headers,
        )
        assert resp.status_code == 404

    def test_update_admin_requires_super_admin(self, client, admin_token_headers) -> None:
        resp = client.put("/api/v1/admins/1", json={"display_name": "X"}, headers=admin_token_headers)
        assert resp.status_code == 403


class TestChangePassword:
    def test_change_password_own_success(self, client, admin_token_headers) -> None:
        # admin_token_headers created admin with id (via db insert)
        # Get the admin's id
        resp = client.get("/api/v1/admins/", headers=admin_token_headers)
        admin_id = resp.json()[0]["id"]
        resp = client.put(
            f"/api/v1/admins/{admin_id}/password",
            json={"old_password": "testpass123", "new_password": "newpass456"},
            headers=admin_token_headers,
        )
        assert resp.status_code == 200

    def test_change_password_other_forbidden(self, client, admin_token_headers, super_admin_token_headers) -> None:
        # Create a second admin
        resp = client.post(
            "/api/v1/admins/",
            json={"username": "other", "password": "pass123"},
            headers=super_admin_token_headers,
        )
        other_id = resp.json()["id"]
        # Regular admin tries to change other's password
        resp = client.put(
            f"/api/v1/admins/{other_id}/password",
            json={"old_password": "pass123", "new_password": "newpass"},
            headers=admin_token_headers,
        )
        assert resp.status_code == 403

    def test_change_password_wrong_old_password(self, client, admin_token_headers) -> None:
        resp = client.get("/api/v1/admins/", headers=admin_token_headers)
        admin_id = resp.json()[0]["id"]
        resp = client.put(
            f"/api/v1/admins/{admin_id}/password",
            json={"old_password": "wrongold", "new_password": "newpass"},
            headers=admin_token_headers,
        )
        assert resp.status_code == 400
