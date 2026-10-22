import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from app import app


def test_pages_load():
    client = app.test_client()
    for url in ["/", "/tasks", "/add", "/health"]:
        assert client.get(url).status_code == 200


def test_add_task():
    client = app.test_client()
    r = client.post("/add", data={"title": "Finish case study", "subject": "DevOps"},
                    follow_redirects=True)
    assert b"Finish case study" in r.data
