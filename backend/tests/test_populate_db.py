import pytest
from unittest.mock import MagicMock, patch
import populate_db
from models import Post, Connection

# -----------------------------
# Test populate_data with mocked session passed
# -----------------------------
def test_populate_data_with_mock_session(capsys):
    # Create a mock session
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()

    # Call populate_data with mock session
    populate_db.populate_data(session=mock_session)

    # Assertions: check that add/commit were called
    assert mock_session.add.call_count >= 3
    assert mock_session.commit.call_count >= 3

    # Ensure Post and Connection objects were added
    added_objs = [call[0][0] for call in mock_session.add.call_args_list]
    assert any(isinstance(obj, Post) for obj in added_objs)
    assert any(isinstance(obj, Connection) for obj in added_objs)

    captured = capsys.readouterr()
    assert "Populating test data..." in captured.out
    assert "Created 20 users." in captured.out
    assert "Created" in captured.out and "posts." in captured.out
    assert "Created" in captured.out and "connections." in captured.out
    assert "Test data population complete." in captured.out

# -----------------------------
# Test populate_data WITHOUT passing a session (covers lines 18-19)
# -----------------------------
@patch('populate_db.create_engine')
@patch('populate_db.sessionmaker')
def test_populate_data_creates_real_session(mock_sessionmaker, mock_create_engine, capsys):
    # Create a MagicMock session to be returned by Session()
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.delete = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = None

    # Patch sessionmaker so calling Session() returns our mock session
    mock_sessionmaker.return_value = mock_session

    # Call populate_data WITHOUT passing a session
    populate_db.populate_data(session=None)

    # Assert that sessionmaker was called (branch executed)
    assert mock_sessionmaker.called, "sessionmaker should have been called to create a new session"

    captured = capsys.readouterr()
    assert "Populating test data..." in captured.out

# -----------------------------
# Test main block
# -----------------------------
@patch('populate_db.populate_data')
def test_main_block(mock_populate):
    populate_db.main()
    mock_populate.assert_called_once()