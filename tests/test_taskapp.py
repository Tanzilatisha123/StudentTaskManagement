import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from app import app


def login(client, name="Tanzila", password="pass1234"):
    return client.post("/login", data={"name": name, "password": password},
                       follow_redirects=True)


def test_health_and_login_page_are_public():
    c = app.test_client()
    assert c.get("/health").status_code == 200
    assert c.get("/login").status_code == 200


def test_pages_require_login():
    c = app.test_client()
    for url in ["/", "/tasks", "/add"]:
        r = c.get(url)
        assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_login_shows_welcome_with_name():
    c = app.test_client()
    r = login(c, "Tanzila")
    assert b"Welcome, Tanzila" in r.data


def test_wrong_password_rejected():
    c = app.test_client()
    login(c, "Anita", "rightpass")
    c2 = app.test_client()
    r = login(c2, "Anita", "wrongpass")
    assert b"Incorrect password" in r.data


def test_add_task_after_login():
    c = app.test_client()
    login(c)
    r = c.post("/add", data={"title": "Finish case study", "subject": "DevOps"},
               follow_redirects=True)
    assert b"Finish case study" in r.data