from gcc_intelligence.research.evidence import validate_evidence


def test_validation_keeps_valid_urls_and_marks_unverified():
    result = validate_evidence([{
        "title": "A market update", "url": "https://example.com/story",
        "content": "ignored", "snippet": "A short source excerpt",
    }])
    assert len(result) == 1
    assert result[0]["evidence_status"] == "UNVERIFIED"
    assert result[0]["source_domain"] == "example.com"


def test_validation_rejects_malformed_records_and_deduplicates_paths():
    result = validate_evidence([
        {"title": "bad", "url": "javascript:alert(1)", "snippet": "x"},
        {"title": "One", "url": "https://example.com/story?utm_source=a", "snippet": "First"},
        {"title": "Duplicate", "url": "https://example.com/story?utm_source=b", "snippet": "Second"},
    ])
    assert len(result) == 1
    assert result[0]["title"] == "One"
