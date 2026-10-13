"""Selected-source, freshness, and single-use capture contract checks."""

import time

from measurement_sources.device_session import DeviceSession, DeviceSessionState


def test_unverified_stream_can_be_shown_but_not_captured():
    session = DeviceSession()
    session.select_source("usb", connected=True)

    sample = session.update_sample("usb", 450.0, received_at=10.0)

    assert sample is not None
    assert session.state == DeviceSessionState.UNSUPPORTED
    assert session.capture_sample(now=10.1) is None


def test_capture_requires_selected_supported_fresh_source_and_consumes_once():
    session = DeviceSession()
    session.select_source(
        "usb",
        profile_id="meter-profile-v1",
        supported=True,
        connected=True,
        freshness_seconds=1.0,
    )

    now = time.monotonic()
    assert session.update_sample("bluetooth", 300.0, received_at=now) is None
    sample = session.update_sample("usb", 450.0, received_at=now)
    assert sample is not None
    assert session.state == DeviceSessionState.RECEIVING
    assert session.capture_sample(now=now + 0.5) == sample
    assert session.consume_sample(sample.sample_id)
    assert session.capture_sample(now=now + 0.5) is None
    assert not session.consume_sample(sample.sample_id)


def test_stale_disconnect_and_practice_states_are_explicit():
    session = DeviceSession()
    session.select_source(
        "usb",
        profile_id="meter-profile-v1",
        supported=True,
        connected=True,
        freshness_seconds=0.5,
    )
    session.update_sample("usb", 450.0, received_at=10.0)
    assert session.state == DeviceSessionState.STALE
    assert session.capture_sample(now=10.6) is None

    session.set_transport_connected(False)
    assert session.state == DeviceSessionState.DISCONNECTED
    assert session.latest_sample is None

    session.select_source(
        "practice",
        simulated=True,
        connected=True,
        freshness_seconds=1.0,
    )
    assert session.state == DeviceSessionState.WAITING
    now = time.monotonic()
    practice_sample = session.update_sample("practice", 0.0, received_at=now)
    assert practice_sample is not None and practice_sample.simulated
    assert session.state == DeviceSessionState.PRACTICE
    assert session.capture_sample(now=now + 0.1) == practice_sample
