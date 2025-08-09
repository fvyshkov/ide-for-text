import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_open_directory():
    # Use the test-directory for this test
    response = client.post("/api/open-directory", json={"path": "test-directory"})
    assert response.status_code == 200
    data = response.json()
    assert "tree" in data
    assert "root_path" in data
    assert len(data["tree"]) > 0

def test_get_file_content():
    # Use a file from the test-directory
    response = client.get("/api/file-content?path=test-directory/planets.xlsx")
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "test-directory/planets.xlsx"
    assert "content" in data

def test_write_file():
    test_content = "Hello from the API test!"
    test_path = "test-directory/api_test_file.txt"
    response = client.post("/api/write-file", json={"path": test_path, "content": test_content})
    assert response.status_code == 200

    # Verify the file was written
    response = client.get(f"/api/file-content?path={test_path}")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == test_content

def test_ai_analyze(mocker):
    # Mock the AI agent to avoid real API calls
    mock_agent = mocker.MagicMock()
    async def mock_analyze(*args, **kwargs):
        yield {"type": "final_result", "content": "mocked response"}

    mock_agent.analyze = mock_analyze
    mocker.patch('backend.main.get_ai_agent', return_value=mock_agent)

    with client.stream("POST", "/api/ai/analyze", json={"query": "hello"}) as response:
        assert response.status_code == 200
        # Check if we receive some data
        for chunk in response.iter_bytes():
            assert len(chunk) > 0
            break
