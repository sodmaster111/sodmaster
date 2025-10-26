"""Tests for the root endpoint."""


def test_root_get(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "<!DOCTYPE html>" in body
    assert "Sodmaster" in body


def test_root_head(client):
    response = client.head("/")

    assert response.status_code == 200
    assert response.text == ""
