from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_broker_topology_uses_mutable_policies_and_bounded_queues() -> None:
    script = (ROOT / "backend/config/rabbitmq/init.sh").read_text(encoding="utf-8")

    assert "RABBITMQ_QUEUE_TYPE:=classic" in script
    assert "dead-letter-strategy" in script and "at-least-once" in script
    assert "delivery-limit" in script
    assert "max-length-bytes" in script
    assert "video-dead-letter-retention" in script
    assert "x-queue-type" in script
    assert '"x-dead-letter-exchange"' not in script
    assert '"x-message-ttl"' not in script


def test_import_queue_is_quorum_scoped_and_replay_is_bounded() -> None:
    script = (ROOT / "backend/config/rabbitmq/init.sh").read_text(encoding="utf-8")

    assert 'create_user "$RABBITMQ_IMPORT_USER"' in script
    assert "source_policy video-import-reliability" in script
    assert "declare_queue video.import content.import.verify.requested quorum" in script
    assert r"content\\.import\\.verify\\.requested" in script
    assert r"video\\.(download|import|analysis|analysis-report)\\.dead" in script


def test_broker_runtime_bounds_heartbeats_payloads_and_ack_deadline() -> None:
    config = (ROOT / "backend/config/rabbitmq/rabbitmq.conf").read_text(
        encoding="utf-8"
    )

    assert "heartbeat = 60" in config
    assert "consumer_timeout = 3600000" in config
    assert "max_message_size = 1048576" in config
