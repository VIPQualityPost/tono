"""Tests for the public ``tono`` library API surface."""

from __future__ import annotations

import inspect
from typing import Literal, get_args, get_origin

import numpy as np
import pytest

import tono
from backend.data_types import DataField, RecordTable


@pytest.fixture
def sample_field() -> DataField:
    """A small deterministic field for fast tests."""
    rng = np.random.default_rng(0)
    data = rng.standard_normal((32, 32)).astype(np.float64)
    return tono.field(data, xreal=1e-6, yreal=1e-6)


# ── Typed call syntax ───────────────────────────────────────────────────

def test_gaussian_filter_call(sample_field):
    result = tono.GaussianFilter(sample_field, sigma=2.0)
    assert isinstance(result, DataField)
    assert result.data.shape == sample_field.data.shape


def test_default_filling_from_metadata(sample_field):
    # sigma has a metadata default of 1.0 — call should succeed without it.
    result = tono.GaussianFilter(sample_field)
    assert isinstance(result, DataField)


def test_keyword_only_call(sample_field):
    result = tono.GaussianFilter(field=sample_field, sigma=0.5)
    assert isinstance(result, DataField)


def test_enum_input_call(sample_field):
    result = tono.EdgeDetect(sample_field, method="sobel", sigma=1.0)
    assert isinstance(result, DataField)


def test_multi_output_returns_tuple(sample_field):
    out = tono.FFT2D(sample_field, windowing="hann", level="mean")
    assert isinstance(out, tuple)
    assert len(out) == 4
    assert all(isinstance(x, DataField) for x in out)


def test_awkward_required_order(sample_field):
    # ThresholdMask has ``threshold`` (default 0.0) followed by ``direction``
    # (no default). The wrapper must handle this without raising, and the
    # metadata default for threshold must still fire at call time.
    mask, record = tono.ThresholdMask(
        sample_field, method="otsu", direction="above"
    )
    assert mask.shape == sample_field.data.shape
    assert isinstance(record, RecordTable)


# ── Signature introspection ─────────────────────────────────────────────

def test_signature_has_expected_params():
    sig = inspect.signature(tono.GaussianFilter)
    assert list(sig.parameters) == ["field", "sigma"]
    assert sig.parameters["sigma"].default == 1.0
    assert sig.parameters["field"].annotation is DataField


def test_signature_enum_uses_literal():
    sig = inspect.signature(tono.EdgeDetect)
    annotation = sig.parameters["method"].annotation
    assert get_origin(annotation) is Literal
    assert set(get_args(annotation)) == {"sobel", "prewitt", "laplacian", "log"}


def test_signature_return_annotation_single_output():
    sig = inspect.signature(tono.GaussianFilter)
    assert sig.return_annotation is DataField


def test_signature_return_annotation_multi_output():
    sig = inspect.signature(tono.FFT2D)
    assert sig.return_annotation is tuple


def test_docstring_contains_description_and_params():
    doc = tono.EdgeDetect.__doc__ or ""
    assert "Sobel" in doc or "sobel" in doc
    assert "field" in doc
    assert "method" in doc
    assert "sigma" in doc


# ── Module-level dunder behaviour ───────────────────────────────────────

def test_dir_lists_nodes():
    entries = dir(tono)
    assert "GaussianFilter" in entries
    assert "EdgeDetect" in entries
    assert "apply" in entries  # existing top-level export
    assert "describe" in entries


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError, match="NotARealNode"):
        tono.NotARealNode  # noqa: B018


def test_dunder_lookup_raises_immediately():
    # __getattr__ should short-circuit dunder lookups so that e.g. copy/pickle
    # machinery doesn't trigger registry loading.
    with pytest.raises(AttributeError):
        tono.__some_dunder__  # noqa: B018


def test_wrappers_are_cached():
    first = tono.GaussianFilter
    second = tono.GaussianFilter
    assert first is second


# ── describe() ──────────────────────────────────────────────────────────

def test_describe_returns_expected_keys():
    info = tono.describe("EdgeDetect")
    assert info["name"] == "EdgeDetect"
    assert "input" in info
    assert "output" in info
    assert "description" in info
    assert "field" in info["input"]["required"]


def test_describe_unknown_node_raises():
    with pytest.raises(KeyError):
        tono.describe("NotARealNode")


# ── apply() still works and matches wrapper semantics ───────────────────

def test_apply_default_filling(sample_field):
    # apply() should also fill metadata defaults now.
    result = tono.apply("GaussianFilter", sample_field)
    assert isinstance(result, DataField)


def test_apply_and_wrapper_are_equivalent(sample_field):
    via_apply = tono.apply("GaussianFilter", sample_field, sigma=1.5)
    via_wrapper = tono.GaussianFilter(sample_field, sigma=1.5)
    np.testing.assert_array_equal(via_apply.data, via_wrapper.data)
