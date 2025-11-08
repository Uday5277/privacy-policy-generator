# import json
# import pytest
# from src.app import app


# @pytest.fixture
# def client():
#     app.config['TESTING'] = True
#     with app.test_client() as client:
#         yield client


# def test_health(client):
#     """Basic health check (for CI/CD)."""
#     rv = client.get("/api/health")
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert data.get("status") == "ok"


# def test_admin_login(client):
#     """Test admin login with default credentials."""
#     rv = client.post("/api/login", json={"username": "admin", "password": "admin"})
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert "token" in data or "message" in data


# def test_add_and_get_questions(client):
#     """Test adding and retrieving questions."""
#     # login to get token
#     login = client.post("/api/login", json={"username": "admin", "password": "admin"})
#     token = login.get_json().get("token")
#     headers = {"Authorization": token, "Content-Type": "application/json"}

#     # add question
#     q = {
#         "category": "Testing",
#         "question": "Is this a test question?",
#         "type": "text"
#     }
#     rv = client.post("/api/questions", json=q, headers=headers)
#     assert rv.status_code in (201, 200)

#     # fetch questions
#     rv = client.get("/api/questions")
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert "categorized" in data


# def test_add_template(client):
#     """Test adding a template."""
#     login = client.post("/api/login", json={"username": "admin", "password": "admin"})
#     token = login.get_json().get("token")
#     headers = {"Authorization": token, "Content-Type": "application/json"}

#     tpl = {
#         "title": "Sample Template",
#         "content": "This is a test privacy template."
#     }
#     rv = client.post("/api/templates", json=tpl, headers=headers)
#     assert rv.status_code in (201, 200)


# def test_preview_and_exports(client):
#     """Test preview, PDF export, and DOCX export."""
#     # preview
#     rv = client.post("/api/preview", json={"company": "PreviewCo"})
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert "preview" in data

#     # export PDF
#     rv = client.post("/api/export/pdf", json={"content": "Sample content"})
#     assert rv.status_code == 200
#     assert "pdf" in rv.headers.get("Content-Type", "").lower()

#     # export DOCX
#     rv = client.post("/api/export/docx", json={"content": "Sample content"})
#     assert rv.status_code == 200
#     assert "wordprocessingml" in rv.headers.get("Content-Type", "").lower() or "docx" in rv.headers.get("Content-Type", "").lower()




# # #testing for categorized questions
# # import pytest
# # from src.app import app

# # @pytest.fixture
# # def client():
# #     with app.test_client() as client:
# #         yield client

# # def test_get_questions(client):
# #     rv = client.get("/api/questions")
# #     assert rv.status_code == 200
# #     data = rv.get_json()
# #     assert "categorized" in data
# #     assert isinstance(data["categorized"], dict)



import json
import pytest
from src.app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def admin_token(client):
    """Get admin authentication token."""
    rv = client.post("/api/login", json={"username": "admin", "password": "admin"})
    data = rv.get_json()
    return data.get("token")


# ===========================
# Health & Basic Tests
# ===========================

def test_health(client):
    """Test health check endpoint (CI/CD requirement)."""
    rv = client.get("/api/health")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("status") == "ok"
    assert "time" in data


def test_home_page(client):
    """Test that home page loads."""
    rv = client.get("/")
    assert rv.status_code == 200


# ===========================
# Authentication Tests (IM-19, IM-20)
# ===========================

def test_admin_login_success(client):
    """Test admin login with correct credentials."""
    rv = client.post("/api/login", json={"username": "admin", "password": "admin"})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "token" in data
    assert "message" in data
    assert data["message"] == "Login successful"


def test_admin_login_failure(client):
    """Test admin login with incorrect credentials."""
    rv = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert rv.status_code == 403
    data = rv.get_json()
    assert "error" in data


def test_logout(client, admin_token):
    """Test logout functionality."""
    rv = client.post("/api/logout", headers={"Authorization": admin_token})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "message" in data


# ===========================
# Questions API Tests (IM-2, IM-15)
# ===========================

def test_get_questions(client):
    """Test retrieving questions (IM-2)."""
    rv = client.get("/api/questions")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "questions" in data
    assert "categorized" in data
    assert isinstance(data["questions"], list)
    assert isinstance(data["categorized"], dict)


def test_add_question_without_auth(client):
    """Test that adding question requires authentication."""
    q = {
        "key": "test_key",
        "category": "Test",
        "question": "Test question?",
        "type": "text"
    }
    rv = client.post("/api/questions", json=q)
    assert rv.status_code == 401


def test_add_question_with_auth(client, admin_token):
    """Test adding a new question with authentication (IM-15)."""
    q = {
        "key": f"test_question_{pytest.__version__}",
        "category": "Testing",
        "question": "Is this a test question?",
        "type": "text",
        "required": True,
        "order": 999
    }
    headers = {"Authorization": admin_token, "Content-Type": "application/json"}
    rv = client.post("/api/questions", json=q, headers=headers)
    assert rv.status_code in (201, 409)  # 201 created or 409 if already exists


def test_add_question_missing_fields(client, admin_token):
    """Test adding question with missing fields."""
    q = {"key": "incomplete"}
    headers = {"Authorization": admin_token, "Content-Type": "application/json"}
    rv = client.post("/api/questions", json=q, headers=headers)
    assert rv.status_code == 400


def test_delete_question(client, admin_token):
    """Test deleting a question (IM-15)."""
    # First add a question to delete
    q = {
        "key": "test_delete_question",
        "category": "Test",
        "question": "Delete me",
        "type": "text"
    }
    headers = {"Authorization": admin_token}
    client.post("/api/questions", json=q, headers=headers)
    
    # Now delete it
    rv = client.delete("/api/questions/test_delete_question", headers=headers)
    assert rv.status_code in (200, 404)  # 200 if deleted, 404 if not found


# ===========================
# Templates API Tests (IM-6, IM-16)
# ===========================

def test_get_templates(client):
    """Test retrieving templates (IM-6)."""
    rv = client.get("/api/templates")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "templates" in data
    assert isinstance(data["templates"], list)


def test_add_template_without_auth(client):
    """Test that adding template requires authentication."""
    tpl = {
        "title": "Test Template",
        "content": "Test content"
    }
    rv = client.post("/api/templates", json=tpl)
    assert rv.status_code == 401


def test_add_template_with_auth(client, admin_token):
    """Test adding a new template with authentication (IM-16)."""
    tpl = {
        "title": f"Test Template {pytest.__version__}",
        "content": "This is a test privacy template with {company_name}.",
        "description": "Test template"
    }
    headers = {"Authorization": admin_token, "Content-Type": "application/json"}
    rv = client.post("/api/templates", json=tpl, headers=headers)
    assert rv.status_code in (201, 409)  # 201 created or 409 if already exists


def test_delete_template(client, admin_token):
    """Test deleting a template (IM-16)."""
    # First add a template to delete
    tpl = {
        "title": "Test Delete Template",
        "content": "Delete this template",
        "description": "For testing deletion"
    }
    headers = {"Authorization": admin_token}
    client.post("/api/templates", json=tpl, headers=headers)
    
    # Now delete it
    rv = client.delete("/api/templates/Test%20Delete%20Template", headers=headers)
    assert rv.status_code in (200, 404)


# ===========================
# Preview Tests (IM-9)
# ===========================

def test_preview_policy(client):
    """Test generating preview of privacy policy (IM-9)."""
    answers = {
        "company_name": "Test Company",
        "contact_email": "test@example.com",
        "uses_cookies": "true",
        "jurisdiction": "Test Jurisdiction"
    }
    rv = client.post("/api/preview", json={"answers": answers})
    assert rv.status_code == 200
    data = rv.get_json()
    assert "preview" in data
    assert "Test Company" in data["preview"]


def test_preview_with_template_selection(client):
    """Test preview with specific template (IM-6, IM-7)."""
    answers = {
        "company_name": "ACME Corp",
        "contact_email": "privacy@acme.com",
        "uses_cookies": "false"
    }
    rv = client.post("/api/preview", json={
        "answers": answers,
        "template": "Default Template"
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert "preview" in data


def test_preview_conditional_clauses(client):
    """Test clause logic works correctly (IM-7)."""
    # Test with cookies enabled
    answers_with_cookies = {
        "company_name": "Cookie Co",
        "uses_cookies": "true",
        "collects_personal_data": "true"
    }
    rv = client.post("/api/preview", json={"answers": answers_with_cookies})
    data = rv.get_json()
    assert "use cookies" in data["preview"].lower()
    
    # Test without cookies
    answers_no_cookies = {
        "company_name": "No Cookie Co",
        "uses_cookies": "false"
    }
    rv = client.post("/api/preview", json={"answers": answers_no_cookies})
    data = rv.get_json()
    assert "do not use cookies" in data["preview"].lower()


# ===========================
# Export Tests (IM-12, IM-13)
# ===========================

def test_export_pdf(client):
    """Test PDF export functionality (IM-12)."""
    content = "Sample privacy policy content for PDF export."
    rv = client.post("/api/export/pdf", json={"content": content})
    assert rv.status_code == 200
    assert "application/pdf" in rv.headers.get("Content-Type", "")


def test_export_pdf_empty_content(client):
    """Test PDF export with empty content."""
    rv = client.post("/api/export/pdf", json={"content": ""})
    assert rv.status_code == 400


def test_export_docx(client):
    """Test DOCX export functionality (IM-13)."""
    content = "Sample privacy policy content for DOCX export."
    rv = client.post("/api/export/docx", json={"content": content})
    assert rv.status_code == 200
    content_type = rv.headers.get("Content-Type", "")
    assert "wordprocessingml" in content_type or "officedocument" in content_type


def test_export_docx_empty_content(client):
    """Test DOCX export with empty content."""
    rv = client.post("/api/export/docx", json={"content": ""})
    assert rv.status_code == 400


def test_export_with_formatted_content(client):
    """Test exports with formatted content."""
    content = """PRIVACY POLICY

1. INTRODUCTION
This is the introduction.

2. DATA COLLECTION
We collect the following data:
- Name
- Email
- Address

3. CONCLUSION
Thank you for reading."""
    
    # Test PDF
    rv = client.post("/api/export/pdf", json={"content": content})
    assert rv.status_code == 200
    
    # Test DOCX
    rv = client.post("/api/export/docx", json={"content": content})
    assert rv.status_code == 200


# ===========================
# Integration Tests
# ===========================

def test_full_workflow(client):
    """Test complete workflow from questions to export."""
    # 1. Get questions
    rv = client.get("/api/questions")
    assert rv.status_code == 200
    
    # 2. Get templates
    rv = client.get("/api/templates")
    assert rv.status_code == 200
    
    # 3. Generate preview
    answers = {
        "company_name": "Workflow Test Inc",
        "contact_email": "workflow@test.com",
        "uses_cookies": "true",
        "jurisdiction": "USA"
    }
    rv = client.post("/api/preview", json={"answers": answers})
    assert rv.status_code == 200
    preview_data = rv.get_json()
    policy_text = preview_data["preview"]
    
    # 4. Export PDF
    rv = client.post("/api/export/pdf", json={"content": policy_text})
    assert rv.status_code == 200
    
    # 5. Export DOCX
    rv = client.post("/api/export/docx", json={"content": policy_text})
    assert rv.status_code == 200


def test_admin_workflow(client, admin_token):
    """Test admin workflow (IM-15, IM-16)."""
    headers = {"Authorization": admin_token, "Content-Type": "application/json"}
    
    # 1. Add question
    q = {
        "key": "admin_workflow_test",
        "category": "Admin Test",
        "question": "Admin workflow question?",
        "type": "text",
        "required": False,
        "order": 1000
    }
    rv = client.post("/api/questions", json=q, headers=headers)
    assert rv.status_code in (201, 409)
    
    # 2. Get questions to verify
    rv = client.get("/api/questions")
    assert rv.status_code == 200
    
    # 3. Delete question
    rv = client.delete("/api/questions/admin_workflow_test", headers=headers)
    assert rv.status_code in (200, 404)


# ===========================
# Performance Tests (IM-22)
# ===========================

def test_response_time_questions(client):
    """Test that questions endpoint responds quickly (IM-22)."""
    import time
    start = time.time()
    rv = client.get("/api/questions")
    elapsed = time.time() - start
    assert rv.status_code == 200
    assert elapsed < 2.0  # Should respond in less than 2 seconds


def test_response_time_preview(client):
    """Test that preview generation is fast (IM-22)."""
    import time
    answers = {
        "company_name": "Performance Test",
        "contact_email": "perf@test.com"
    }
    start = time.time()
    rv = client.post("/api/preview", json={"answers": answers})
    elapsed = time.time() - start
    assert rv.status_code == 200
    assert elapsed < 3.0  # Should respond in less than 3 seconds


# ===========================
# Error Handling Tests
# ===========================

def test_invalid_endpoint(client):
    """Test accessing invalid endpoint."""
    rv = client.get("/api/invalid")
    assert rv.status_code == 404


def test_invalid_json(client):
    """Test sending invalid JSON."""
    rv = client.post("/api/preview", 
                     data="invalid json",
                     headers={"Content-Type": "application/json"})
    assert rv.status_code in (400, 500)


def test_missing_required_fields(client, admin_token):
    """Test validation of required fields."""
    headers = {"Authorization": admin_token, "Content-Type": "application/json"}
    
    # Missing question field
    rv = client.post("/api/questions", json={"key": "test"}, headers=headers)
    assert rv.status_code == 400
    
    # Missing template content
    rv = client.post("/api/templates", json={"title": "Test"}, headers=headers)
    assert rv.status_code == 400
