from sentieon_assist.state_machine import next_state


def test_missing_info_routes_to_need_info():
    assert next_state("EXTRACTED", has_missing_info=True) == "NEED_INFO"


def test_ready_routes_to_answered():
    assert next_state("READY", has_missing_info=False) == "ANSWERED"


def test_classified_routes_to_extracted():
    assert next_state("CLASSIFIED", has_missing_info=False) == "EXTRACTED"
