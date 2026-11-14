from app.main import create_app
from app.schemas import ERROR_MESSAGES, ErrorCode


def test_app_creation():
    app = create_app()
    assert app.title == "TimeSliceIQ API"
    assert app.version == "0.1.0"

def test_error_codes_defined():
    assert len(ErrorCode) == 6
    assert len(ERROR_MESSAGES) == 6
    assert ErrorCode.INVALID_URL in ERROR_MESSAGES

