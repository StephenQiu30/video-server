import pytest
from app.domain.downloads import MediaKind
from app.services.downloads.errors import ApplicationError, ApplicationErrorCode
from app.services.downloads.validation import media_kind_from_metadata


@pytest.mark.parametrize("kind", list(MediaKind))
def test_known_media_kind(kind):
    assert media_kind_from_metadata({"media_kind": kind.value}) is kind


def test_missing_media_kind_defaults_to_video():
    assert media_kind_from_metadata({}) is MediaKind.VIDEO


@pytest.mark.parametrize("value", [None, True, 1, [], {}, "unknown", ""])
def test_invalid_media_kind_fails_closed(value):
    with pytest.raises(ApplicationError) as failure:
        media_kind_from_metadata({"media_kind": value})
    assert failure.value.code is ApplicationErrorCode.INTERNAL_ERROR
