from gcc_intelligence.research.graph import route_after_guardrail, stop_after_guardrail


def test_allow_routes_to_research():
    assert route_after_guardrail({"guardrail_status": "allow"}) == "plan"


def test_warn_and_block_stop_before_search():
    assert route_after_guardrail({"guardrail_status": "warn"}) == "stop"
    assert route_after_guardrail({"guardrail_status": "block"}) == "stop"


def test_stop_node_clears_search_evidence():
    state = {
        "guardrail_status": "block",
        "evidence": [{"title": "should not persist"}],
        "raw_results": [{"url": "https://example.com"}],
        "queries": ["unsafe query"],
    }
    result = stop_after_guardrail(state)
    assert result["evidence"] == []
    assert result["raw_results"] == []
    assert result["queries"] == []
    assert result["status"] == "guardrail_block"


def test_guardrail_unavailable_does_not_route_to_search():
    assert route_after_guardrail({"guardrail_status": "unavailable"}) == "stop"
