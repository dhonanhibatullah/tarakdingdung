import pytest

from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.infrastructure.llm.validation import PydanticDecisionValidator


def _validate(raw):
    return PydanticDecisionValidator().validate(raw)


def test_valid_decision():
    draft = _validate(
        '{"weights": [{"symbol_id": "s1", "weight": 0.5}], "reasoning": "r", "confidence": 0.8}'
    )
    assert draft.weights[0].symbol_id == "s1"
    assert draft.weights[0].weight == 0.5
    assert draft.reasoning == "r"
    assert draft.confidence == 0.8


def test_invalid_json_rejected():
    with pytest.raises(DomainError):
        _validate("not json")


def test_negative_weight_rejected():
    with pytest.raises(DomainError):
        _validate('{"weights": [{"symbol_id": "s1", "weight": -0.1}]}')


def test_sum_over_one_rejected():
    with pytest.raises(DomainError):
        _validate(
            '{"weights": [{"symbol_id": "s1", "weight": 0.7}, {"symbol_id": "s2", "weight": 0.5}]}'
        )


def test_missing_weights_defaults_to_empty():
    draft = _validate("{}")
    assert draft.weights == []
    assert draft.confidence == 0.5
