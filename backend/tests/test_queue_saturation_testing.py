import pytest
from collector.backpressure import BackpressureController, BackpressureExceededError

def test_TRC_134_queue_saturation_testing():
    # Configure a bounded queue with max capacity of 500 items
    max_cap = 500
    controller = BackpressureController(max_capacity=max_cap, default_retry_after=2)

    # Fill up to capacity
    controller.acquire(300)
    assert controller.current_depth == 300
    assert controller.rejected_count == 0

    controller.acquire(200)
    assert controller.current_depth == 500
    assert controller.rejected_count == 0

    # Next acquisition exceeds saturation limit
    with pytest.raises(BackpressureExceededError) as exc_info:
        controller.acquire(1)

    assert "Queue saturated" in str(exc_info.value)
    assert exc_info.value.retry_after_seconds == 2
    assert controller.rejected_count == 1
    assert controller.current_depth == 500  # Memory bounded at 500

    # Drain queue
    controller.release(250)
    assert controller.current_depth == 250

    # Acquisition now succeeds after drain
    controller.acquire(100)
    assert controller.current_depth == 350
    assert controller.rejected_count == 1
