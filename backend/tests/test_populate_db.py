import pytest
from unittest.mock import MagicMock, patch
import populate_db

# -----------------------------
# Test populate_data with a mocked session passed
# -----------------------------
def test_populate_data_with_mock_session(capsys):
    from populate_db import populate_data

    mock_session = MagicMock()
    # Call the function with the mock session
    populate_data(session=mock_session)

    # Ensure session methods were used
    assert mock_session.add.called, "Expected session.add() to be called"
    assert mock_session.commit.called, "Expected session.commit() to be called"

    # Check that output was printed
    captured = capsys.readouterr()
    assert "Populating test data..." in captured.out
    assert "Created" in captured.out
    assert "Test data population complete." in captured.out

# -----------------------------
# Test populate_data WITHOUT passing a session (lines 18-19)
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
    mock_sessionmaker.return_value = lambda: mock_session

    # Call populate_data without passing session
    populate_db.populate_data(session=None)

    # Assert that sessionmaker was called and add/commit were invoked
    assert mock_sessionmaker.called, "sessionmaker should have been called"
    assert mock_session.add.called, "Expected session.add() to be called"
    assert mock_session.commit.called, "Expected session.commit() to be called"

    # Check output
    captured = capsys.readouterr()
    assert "Populating test data..." in captured.out
    assert "Created" in captured.out
    assert "Test data population complete." in captured.out

# -----------------------------
# Test main block
# -----------------------------
@patch('populate_db.populate_data')
def test_main_block(mock_populate):
    populate_db.main()
    mock_populate.assert_called_once()