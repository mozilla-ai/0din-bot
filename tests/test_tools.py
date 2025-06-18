import pytest
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from odinbot.tools.odin import (
    check_submission,
    SCANNED_MSG,
    NOT_SCANNED_MSG,
    API_KEY_NOT_CONFIGURED_MSG,
    INVALID_UUID_MSG,
    is_valid_uuid,
    parse_scan_result
)

# Test is_valid_uuid function
def test_is_valid_uuid():
    # Test valid UUID
    valid_uuid = str(uuid.uuid4())
    assert is_valid_uuid(valid_uuid) is True
    
    # Test invalid UUID formats
    assert is_valid_uuid("not-a-uuid") is False
    assert is_valid_uuid("12345") is False
    assert is_valid_uuid("") is False
    assert is_valid_uuid(None) is False

# Test parse_scan_result function
def test_parse_scan_result():
    # Test scanned result
    scanned_data = {
        "metadata": [
            {
                "type": "ScannerModule",
                "result": 1
            }
        ]
    }
    assert parse_scan_result(scanned_data) == SCANNED_MSG
    
    # Test not scanned result
    not_scanned_data = {
        "metadata": [
            {
                "type": "ScannerModule",
                "result": 0
            }
        ]
    }
    assert parse_scan_result(not_scanned_data) == NOT_SCANNED_MSG
    
    # Test missing ScannerModule
    missing_module_data = {
        "metadata": [
            {
                "type": "OtherModule",
                "result": 1
            }
        ]
    }
    assert "json" in parse_scan_result(missing_module_data).lower()

# Test check_submission function
@pytest.mark.asyncio
async def test_check_submission():
    # Test invalid UUID
    assert await check_submission("invalid-uuid") == INVALID_UUID_MSG
    
    # Test missing API key
    with patch.dict('os.environ', {}, clear=True):
        assert await check_submission(str(uuid.uuid4())) == API_KEY_NOT_CONFIGURED_MSG
    
    # Test successful API call
    test_uuid = str(uuid.uuid4())
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "metadata": [
            {
                "type": "ScannerModule",
                "result": 1
            }
        ]
    }
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    
    with patch.dict('os.environ', {'ODIN_API_KEY': 'test-key'}), \
         patch('httpx.AsyncClient') as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        assert await check_submission(test_uuid) == SCANNED_MSG
    
    # Test API error
    mock_error_response = MagicMock()
    mock_error_response.status_code = 404
    mock_error_response.text = "Not Found"
    mock_client.get.return_value = mock_error_response
    
    with patch.dict('os.environ', {'ODIN_API_KEY': 'test-key'}), \
         patch('httpx.AsyncClient') as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        result = await check_submission(test_uuid)
        assert "404" in result
        assert "Not Found" in result 