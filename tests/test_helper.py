import pytest
from cps.helper import save_cover_from_url

def test_save_cover_from_url_invalid_url():
    # Test with invalid URL
    result = save_cover_from_url("http://invalid.url", "/tmp")
    assert result[0] == False
    assert "Error downloading cover" in result[1]