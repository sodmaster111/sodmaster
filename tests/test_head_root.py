def test_get_root_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "sodmaster"


def test_head_root_ok(client):
    response = client.head("/")
    assert response.status_code == 200
    assert response.text == ""
