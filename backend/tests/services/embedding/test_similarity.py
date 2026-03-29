import pytest
from app.utils.similarity import cosine_similarity


def test_identical_vectors_return_1():
    a = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(a, a) - 1.0) < 1e-6


def test_orthogonal_vectors_return_0():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_opposite_vectors_return_minus_1():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6


def test_zero_vector_returns_0():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_dimension_mismatch_raises():
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])