"""Tests for the root endpoint."""


def test_root_get(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sodmaster",
        "docs": "/docs",
    }


def test_root_head(client):
    response = client.head("/")

    assert response.status_code == 200
    assert response.text == ""
