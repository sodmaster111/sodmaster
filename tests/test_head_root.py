def test_get_root_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title" in response.text


def test_head_root_ok(client):
    response = client.head("/")
    assert response.status_code == 200
    assert response.text == ""
