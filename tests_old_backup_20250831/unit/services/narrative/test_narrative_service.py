from fastapi.testclient import TestClient
from src.services.narrative.main import app
from src.services.narrative.narrative_models import NarrativeContent

client = TestClient(app)

def test_get_narrative_state_success():
    """
    Tests the GET /narrative/state endpoint for a successful response.
    """
    # Arrange
    headers = {"X-User-ID": "test-user", "X-Tenant-ID": "test-tenant"}

    # Act
    response = client.get("/narrative/state", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == "CHAPTER_1_CHOICE_1"
    assert data["character"] == "Lucien"
    assert "choices" in data
    assert len(data["choices"]) == 2

def test_post_choice_forest_success():
    """
    Tests the POST /narrative/choice endpoint with the 'GOTO_FOREST' option.
    """
    # Arrange
    headers = {"X-User-ID": "test-user", "X-Tenant-ID": "test-tenant"}
    payload = {"node_id": "CHAPTER_1_CHOICE_1", "choice_id": "GOTO_FOREST"}

    # Act
    response = client.post("/narrative/choice", headers=headers, json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == "CHAPTER_1_FOREST_ENTRY"
    assert data["character"] == "Diana"
    assert "choices" not in data or data["choices"] is None

def test_post_choice_city_success():
    """
    Tests the POST /narrative/choice endpoint with a different option.
    """
    # Arrange
    headers = {"X-User-ID": "test-user", "X-Tenant-ID": "test-tenant"}
    payload = {"node_id": "CHAPTER_1_CHOICE_1", "choice_id": "GOTO_CITY"}

    # Act
    response = client.post("/narrative/choice", headers=headers, json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == "CHAPTER_1_CITY_GATES"
    assert data["character"] == "Lucien"

def test_model_instantiation_sanity_check():
    """
    A simple sanity check to ensure the SQLAlchemy models can be instantiated.
    This is not a database test.
    """
    # Arrange & Act
    instance = NarrativeContent(
        node_id="test_node",
        node_type="SCENE",
        content={"text": "This is a test."}
    )
    # Assert
    assert instance.node_id == "test_node"
    assert instance.content["text"] == "This is a test."
