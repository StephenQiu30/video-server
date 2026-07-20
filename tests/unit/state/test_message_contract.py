import uuid

import pytest
from src.rabbitmq import DownloadMessage


def test_message_has_only_job_id() -> None:
    job_id = uuid.uuid4()
    message = DownloadMessage(job_id)
    assert message.to_bytes() == ('{"job_id":"' + str(job_id) + '"}').encode()
    assert DownloadMessage.from_bytes(message.to_bytes()) == message


@pytest.mark.parametrize("body", [b"{}", b'{"job_id":"x","extra":1}', b"not-json"])
def test_message_rejects_non_contract_payload(body: bytes) -> None:
    with pytest.raises(ValueError):
        DownloadMessage.from_bytes(body)
