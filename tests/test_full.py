# # tests/test_full.py
# import json
# import pytest
# from src import app as app_module
# from src.app import generate_policy_text

# @pytest.fixture
# def client():
#     app = app_module.app
#     app.config['TESTING'] = True
#     with app.test_client() as client:
#         yield client

# def test_generate_policy_text_basic():
#     answers = {
#         "company_name": "TestCorp",
#         "contact_email": "admin@test.com",
#         "collects_personal_data": True,
#         "uses_cookies": False,
#         "jurisdiction": "USA"
#     }
#     txt = generate_policy_text(answers, template_id="default")
#     assert "Privacy Policy for TestCorp" in txt
#     assert "We do not use cookies." in txt or "do not use cookies" in txt or "We use cookies" not in txt

# def test_health(client):
#     rv = client.get("/health")
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert data.get("status") == "ok"

# def test_get_questions(client):
#     rv = client.get("/api/questions")
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert "questions" in data
#     assert "categorized" in data

# def test_login_and_question_crud(client):
#     # login (default credentials admin/admin)
#     rv = client.post("/api/login", json={"username": "admin", "password": "admin"})
#     assert rv.status_code == 200
#     body = rv.get_json()
#     token = body.get("token")
#     assert token

#     headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

#     # add a new question
#     new_q = {
#         "id": "test_q_123",
#         "category": "Test",
#         "label": "Test question?",
#         "key": "test_question_key",
#         "type": "text",
#         "required": False
#     }
#     rv = client.post("/api/questions", json=new_q, headers=headers)
#     assert rv.status_code == 201

#     # fetch and ensure it exists
#     rv = client.get("/api/questions")
#     data = rv.get_json()
#     found = any(q.get("id") == "test_q_123" for q in data.get("questions", []))
#     assert found

#     # delete it
#     rv = client.delete("/api/questions/test_q_123", headers=headers)
#     assert rv.status_code == 200

# def test_templates_crud_with_auth(client):
#     # login
#     rv = client.post("/api/login", json={"username": "admin", "password": "admin"})
#     token = rv.get_json().get("token")
#     headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

#     # add template (minimal)
#     tpl = {"id": "tpl_test_1", "name": "TestTpl", "clauses": {"default_footer": "Footer"}}
#     rv = client.post("/api/templates", json=tpl, headers=headers)
#     assert rv.status_code == 201

#     # delete template
#     rv = client.delete("/api/templates/tpl_test_1", headers=headers)
#     # delete may respond 200 (ok) or 204 depending on implementation; accept 200
#     assert rv.status_code in (200, 204)

# def test_preview_and_generate_endpoints(client):
#     answers = {"company_name": "PreviewCo", "contact_email": "a@b.com", "collects_personal_data": True, "uses_cookies": True}
#     rv = client.post("/api/preview", json={"answers": answers})
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert "policy" in data

#     rv = client.post("/api/generate", json={"answers": answers})
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert "policy" in data

# def test_export_pdf_docx(client):
#     answers = {"company_name": "ExportCo"}
#     rv = client.post("/api/export/pdf", json={"answers": answers})
#     assert rv.status_code == 200
#     # Content-Type will be application/pdf (or similar)
#     ct = rv.headers.get("Content-Type", "")
#     assert "pdf" in ct.lower()

#     rv = client.post("/api/export/docx", json={"answers": answers})
#     assert rv.status_code == 200
#     ct = rv.headers.get("Content-Type", "")
#     assert "wordprocessingml" in ct or "docx" in ct.lower()



#testing for categorized questions
import pytest
from src.app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_get_questions(client):
    rv = client.get("/api/questions")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "categorized" in data
    assert isinstance(data["categorized"], dict)
