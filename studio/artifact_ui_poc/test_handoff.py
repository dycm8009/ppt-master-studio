from __future__ import annotations

from studio.artifact_ui_poc.handoff import (
    canonical_payload_sha256,
    delivered_handoff,
    may_invoke_validator,
    require_delivered,
    unavailable_handoff,
)


def expect_value_error(fn) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def main() -> None:
    payload = {
        "schema": "ppt-master-static-deck-review-response/v1",
        "surface": "deck-review",
        "status": "user-confirmed",
        "svg_roster_sha256": "c" * 64,
        "changes": [
            {
                "slide": "slide-02.svg",
                "element_id": "subtitle",
                "replace_text": "输入、约束、工具、输出形成稳定边界哈哈",
            }
        ],
    }

    digest = canonical_payload_sha256(payload)
    assert len(digest) == 64

    unavailable = unavailable_handoff()
    assert unavailable["status"] == "unavailable"
    assert unavailable["can_create_accepted_receipt"] is False
    expect_value_error(lambda: require_delivered(payload, unavailable))

    # Human-visible evidence alone is not a machine Gate handoff.
    screenshot_only = {
        "schema": "ppt-master-artifact-handoff/v1",
        "status": "captured",
        "transport": "screenshot",
    }
    expect_value_error(lambda: require_delivered(payload, screenshot_only))

    # A short hash/token without a state store cannot reconstruct canonical state.
    token_only = {
        "schema": "ppt-master-artifact-handoff/v1",
        "status": "delivered",
        "transport": "short-token",
        "payload_sha256": digest,
    }
    expect_value_error(lambda: require_delivered(payload, token_only))

    delivered = delivered_handoff(
        payload=payload,
        transport="host-native",
        evidence="host-event:test-only",
    )
    assert delivered["status"] == "delivered"
    assert delivered["payload_sha256"] == digest
    assert may_invoke_validator(payload, delivered) is True

    tampered = dict(delivered)
    tampered["payload_sha256"] = "0" * 64
    expect_value_error(lambda: require_delivered(payload, tampered))

    expect_value_error(
        lambda: delivered_handoff(payload=payload, transport="short-token", evidence="x")
    )
    expect_value_error(
        lambda: delivered_handoff(payload=payload, transport="host-native", evidence="")
    )

    print("artifact Gate handoff contract: PASS")


if __name__ == "__main__":
    main()
