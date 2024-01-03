import os

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from utilities import logger as logger


@pytest.fixture
def mock_ipc_node():
    mock = Mock()
    mock.send = Mock()
    return mock


@pytest.fixture
def logger_obj(mock_ipc_node):
    return logger.Logger(mock_ipc_node)


@pytest.fixture
def log_data():
    return {
        "message": "Test message",
        "level": logger.Logger.DEBUG,
        "label": "TestLabel",
        "timestamp": None
    }


@pytest.fixture
def log(log_data):
    return logger.Log(
        message=log_data["message"],
        level=log_data["level"],
        label=log_data["label"],
    )


def test_log_properties(log, log_data):
    assert log._message == log_data["message"]
    assert log._level == log_data["level"]
    assert log._label == log_data["label"]
    assert log._timestamp is not None


def test_log_dumps_and_loads(log):
    dumps = log.dumps()
    loaded_log = logger.Log.loads(dumps)

    assert loaded_log._message == log._message
    assert loaded_log._level == log.level
    assert loaded_log._label == log._label
    assert loaded_log._timestamp == log._timestamp


def test_log_str(log):
    formatted_time = datetime.fromtimestamp(log.timestamp).strftime('%Y-%m-%d %H:%M:%S')
    expected_str = (
        f"{logger.Colors.RESET}{formatted_time} "
        f"{logger.Colors.PURPLE + logger.Colors.BOLD + logger.Colors.UNDERLINE}{log.label}{logger.Colors.RESET + logger.Colors.WHITE + logger.Colors.BOLD}"
        f" {log.level}{logger.Colors.RESET}{logger.Colors.WHITE}: {log.message}{logger.Colors.RESET}\n"
    )
    assert str(log) == expected_str


def test_logger_log(logger_obj, mock_ipc_node):
    with patch('builtins.print') as mock_print:
        logger_obj.log("Test message", "TestLabel", logger.Logger.INFO, extra_channel="extra")

    mock_ipc_node.send.assert_called_once()
    mock_print.assert_called_once()


def test_logger_debug(logger_obj, mock_ipc_node):
    with patch('builtins.print') as mock_print:
        logger_obj.debug("Test message", "TestLabel", extra_channel="extra")

    mock_ipc_node.send.assert_called_once()
    if os.environ.get("DEBUG") == "1":
        mock_print.assert_called_once()
    else:
        mock_print.assert_not_called()


def test_logger_info(logger_obj, mock_ipc_node):
    with patch('builtins.print') as mock_print:
        logger_obj.info("Test message", "TestLabel", extra_channel="extra")

    mock_ipc_node.send.assert_called_once()
    mock_print.assert_called_once()


def test_logger_warning(logger_obj, mock_ipc_node):
    with patch('builtins.print') as mock_print:
        logger_obj.warning("Test message", "TestLabel", extra_channel="extra")

    mock_ipc_node.send.assert_called_once()
    mock_print.assert_called_once()


def test_logger_error(logger_obj, mock_ipc_node):
    with patch('builtins.print') as mock_print:
        logger_obj.error("Test message", "TestLabel", extra_channel="extra")

    mock_ipc_node.send.assert_called_once()
    mock_print.assert_called_once()


def test_logger_critical(logger_obj, mock_ipc_node):
    with patch('builtins.print') as mock_print:
        logger_obj.critical("Test message", "TestLabel", extra_channel="extra")

    mock_ipc_node.send.assert_called_once()
    mock_print.assert_called_once()


if __name__ == "__main__":
    pytest.main()
