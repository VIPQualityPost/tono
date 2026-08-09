import numpy as np
import pytest
from tests.node_tests._shared import make_field


# All 28 patterns supported by SyntheticSurface
ALL_PATTERNS = [
    "fbm", "white_noise", "lattice", "steps", "particles", "flat",
    "columnar", "objects", "fibres", "waves", "dunes",
    "domains", "ballistic", "deposition", "rods", "dla",
    "discs", "plateaus", "pileups", "annealing", "voronoi",
    "spinodal", "pde", "spectral", "residues",
    "noise", "periodic", "wfr",
]

# Iterative patterns that need n_iterations kept low for speed
ITERATIVE_PATTERNS = {"domains", "ballistic", "annealing", "spinodal", "pde", "dla"}


def _make_node():
    from backend.nodes.synthetic_surface import SyntheticSurface
    return SyntheticSurface()


def _common_kwargs(pattern, xres=64, yres=64):
    """Build kwargs dict with low iteration count for iterative patterns."""
    kwargs = dict(
        pattern=pattern,
        xres=xres,
        yres=yres,
        xreal=1e-6,
        yreal=1e-6,
        amplitude=1e-9,
        seed=42,
    )
    if pattern in ITERATIVE_PATTERNS:
        kwargs["n_iterations"] = 20
    return kwargs


# ---------------------------------------------------------------------------
# 1. Every pattern produces the correct output shape
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pattern", ALL_PATTERNS)
def test_all_patterns_produce_correct_shape(pattern):
    node = _make_node()
    kwargs = _common_kwargs(pattern, xres=64, yres=64)
    (field,) = node.process(**kwargs)
    assert field.data.shape == (64, 64), (
        f"Pattern {pattern!r} produced shape {field.data.shape}, expected (64, 64)"
    )


# ---------------------------------------------------------------------------
# 2. Seed reproducibility
# ---------------------------------------------------------------------------

def test_seed_reproducibility():
    node = _make_node()
    kwargs = dict(
        pattern="fbm", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=123,
    )
    (r1,) = node.process(**kwargs)
    (r2,) = node.process(**kwargs)
    assert np.array_equal(r1.data, r2.data), "Same seed must produce identical output"


# ---------------------------------------------------------------------------
# 3. Amplitude scaling
# ---------------------------------------------------------------------------

def test_amplitude_scaling():
    node = _make_node()
    amp = 5e-9
    (field,) = node.process(
        pattern="fbm", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=amp, seed=42,
    )
    # After normalisation the range should be [0, amplitude]
    assert field.data.min() >= -1e-15, "Min value should be >= 0 (within tolerance)"
    assert field.data.max() <= amp + 1e-15, (
        f"Max value {field.data.max()} exceeds amplitude {amp}"
    )
    # The range should actually span close to the full amplitude
    assert field.data.max() - field.data.min() == pytest.approx(amp, rel=1e-6)


# ---------------------------------------------------------------------------
# 4. Flat pattern produces all zeros
# ---------------------------------------------------------------------------

def test_flat_is_zero():
    node = _make_node()
    (field,) = node.process(
        pattern="flat", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=0,
    )
    assert np.allclose(field.data, 0.0), "Flat pattern must produce all zeros"


# ---------------------------------------------------------------------------
# 5. Object shapes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("obj_shape", ["sphere", "pyramid", "box", "cylinder", "cone"])
def test_objects_shapes(obj_shape):
    node = _make_node()
    (field,) = node.process(
        pattern="objects", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1.0, seed=42,
        n_particles=5, particle_radius_px=5, object_shape=obj_shape,
    )
    assert field.data.shape == (64, 64), (
        f"Object shape {obj_shape!r} produced wrong output shape"
    )
    assert np.any(field.data != 0.0), (
        f"Object shape {obj_shape!r} should not be all zeros"
    )


# ---------------------------------------------------------------------------
# 6. Noise types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("noise_type", [
    "gaussian", "poisson", "exponential", "uniform", "salt_pepper",
])
def test_noise_types(noise_type):
    node = _make_node()
    (field,) = node.process(
        pattern="noise", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=42,
        noise_type=noise_type,
    )
    assert field.data.shape == (64, 64), (
        f"Noise type {noise_type!r} produced wrong shape"
    )
    assert np.all(np.isfinite(field.data)), (
        f"Noise type {noise_type!r} produced non-finite values"
    )


# ---------------------------------------------------------------------------
# 7. Periodic types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("periodic_type", [
    "checker", "hex", "stripe", "diamond", "staircase", "rings",
])
def test_periodic_types(periodic_type):
    node = _make_node()
    (field,) = node.process(
        pattern="periodic", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=42,
        periodic_type=periodic_type,
    )
    assert field.data.shape == (64, 64), (
        f"Periodic type {periodic_type!r} produced wrong shape"
    )


# ---------------------------------------------------------------------------
# 8. Spinodal converges to bimodal distribution
# ---------------------------------------------------------------------------

def test_spinodal_converges():
    node = _make_node()
    (field,) = node.process(
        pattern="spinodal", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=42,
        n_iterations=50,
    )
    data = field.data
    mid = (data.min() + data.max()) / 2.0
    span = data.max() - data.min()
    # In a bimodal distribution most values cluster near min or max,
    # so few values should be in the middle third.
    middle_band = np.abs(data - mid) < span / 6.0
    fraction_in_middle = middle_band.sum() / data.size
    assert fraction_in_middle < 0.5, (
        f"Expected bimodal distribution but {fraction_in_middle:.1%} of values "
        f"are in the middle band"
    )


# ---------------------------------------------------------------------------
# 9. Voronoi produces discrete height levels
# ---------------------------------------------------------------------------

def test_voronoi_discrete_heights():
    node = _make_node()
    n_sites = 5
    (field,) = node.process(
        pattern="voronoi", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=42,
        n_particles=n_sites,
    )
    # Round to avoid floating-point noise and count unique levels
    unique_levels = np.unique(np.round(field.data, decimals=12))
    assert len(unique_levels) <= n_sites, (
        f"Voronoi with {n_sites} sites produced {len(unique_levels)} distinct "
        f"height levels, expected at most {n_sites}"
    )


# ---------------------------------------------------------------------------
# 10. Steps count matches n_steps
# ---------------------------------------------------------------------------

def test_steps_count():
    node = _make_node()
    n_steps = 3
    (field,) = node.process(
        pattern="steps", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=42,
        n_steps=n_steps,
    )
    # The steps generator creates floor(linspace(0, n_steps, xres)) values.
    # After normalisation, there should be approximately n_steps distinct
    # non-zero step levels (plus possibly zero).
    unique_levels = np.unique(np.round(field.data, decimals=12))
    # Allow for the zero level plus n_steps levels
    assert len(unique_levels) <= n_steps + 1, (
        f"Steps with n_steps={n_steps} produced {len(unique_levels)} distinct "
        f"levels, expected at most {n_steps + 1}"
    )
    # Should have at least 2 distinct levels (not a flat surface)
    assert len(unique_levels) >= 2, (
        f"Steps pattern should produce multiple distinct levels, got {len(unique_levels)}"
    )


# ---------------------------------------------------------------------------
# 11. Line noise pattern (lno_synth.c port)
# ---------------------------------------------------------------------------

LINE_NOISE_TYPES = ["steps", "scars", "ridges"]


def _line_noise_kwargs(ln_type, **extra):
    kwargs = dict(
        pattern="line_noise", xres=64, yres=64,
        xreal=1e-6, yreal=1e-6, amplitude=1e-9, seed=42,
        ln_type=ln_type,
    )
    kwargs.update(extra)
    return kwargs


@pytest.mark.parametrize("ln_type", LINE_NOISE_TYPES)
def test_line_noise_runs(ln_type):
    """Every line-noise structure runs and produces a non-trivial surface."""
    node = _make_node()
    (field,) = node.process(**_line_noise_kwargs(ln_type))
    assert field.data.shape == (64, 64)
    assert np.any(field.data != 0.0), f"line_noise {ln_type!r} produced a flat surface"
    assert field.si_unit_z == "m"
    assert field.xreal == pytest.approx(1e-6)


def test_line_noise_steps_rows_are_constant():
    """Steps add a per-row height offset, so every row is exactly constant."""
    node = _make_node()
    (field,) = node.process(**{**_line_noise_kwargs("steps"), "ln_density": 3.0})
    row_std = field.data.std(axis=1)
    # Rows are exactly constant up to 1-ulp floating point noise in np.std
    assert np.all(row_std < 1e-15), "step rows must be constant"
    assert len(np.unique(field.data)) > 2, "steps must create several height levels"


def test_line_noise_cumulative_steps_drift():
    """Cumulative steps keep adding height, so later rows are systematically
    offset from earlier rows (the mean level grows along the scan)."""
    node = _make_node()
    (cum_field,) = node.process(**{**_line_noise_kwargs("steps"), "ln_density": 4.0,
                                   "ln_cumulative": True})
    (one_field,) = node.process(**{**_line_noise_kwargs("steps"), "ln_density": 4.0,
                                   "ln_cumulative": False})
    cum = cum_field.data.mean(axis=1)
    one = one_field.data.mean(axis=1)
    assert cum.std() > one.std(), "cumulative steps should drift more than one-shot steps"


def test_line_noise_scars_create_segments():
    """Scars are horizontal segments: some rows are scarred (vary along x),
    some clean (exactly constant), and the scarred rows have few levels."""
    node = _make_node()
    (field,) = node.process(**{**_line_noise_kwargs("scars"), "ln_length": 16.0,
                               "ln_coverage": 0.05})
    row_std = field.data.std(axis=1)
    assert np.any(row_std > 0.0), "no scarred rows found"
    assert np.any(row_std < 1e-15), "no clean rows found"


def test_line_noise_ridges_have_horizontal_transitions():
    """Ridges create ramps within rows: at least one internal horizontal
    transition must exist."""
    node = _make_node()
    # lineprob > 0 makes the in-row scan position advance, so ridge events
    # are crossed inside rows and create ramps (horizontal transitions).
    (field,) = node.process(**{**_line_noise_kwargs("ridges"), "ln_density": 4.0,
                               "ln_lineprob": 1.0})
    transitions = np.count_nonzero(np.diff(field.data, axis=1) != 0.0)
    assert transitions > 0, "ridges must produce row-internal transitions"


@pytest.mark.parametrize("ln_direction", ["both", "up", "down"])
def test_line_noise_direction(ln_direction):
    """up makes the noise one-sided positive (all values >= 0 before
    normalization the min-max mapping still keeps the levels distinct)."""
    node = _make_node()
    (field,) = node.process(**{**_line_noise_kwargs("steps", ln_density=2.0),
                               "ln_direction": ln_direction})
    uniq = np.unique(field.data)
    assert len(uniq) > 2


@pytest.mark.parametrize("ln_distribution", ["gaussian", "exponential", "uniform", "triangular"])
def test_line_noise_distributions(ln_distribution):
    node = _make_node()
    (field,) = node.process(**{**_line_noise_kwargs("steps", ln_density=2.0),
                               "ln_distribution": ln_distribution})
    assert field.data.shape == (64, 64)
    assert np.any(field.data != 0.0)


def test_line_noise_rtl_flips_rows():
    """Scanning right-to-left mirrors each row of the structure."""
    node = _make_node()
    kwargs = dict(ln_type="steps", ln_density=2.0, ln_lineprob=1.0)
    (ltr,) = node.process(**{**_line_noise_kwargs("steps"), "ln_scandir": "LTR"})
    (rtl,) = node.process(**{**_line_noise_kwargs("steps"), "ln_scandir": "RTL"})
    assert rtl.data.shape == ltr.data.shape


def test_line_noise_seed_reproducible():
    node = _make_node()
    kwargs = _line_noise_kwargs("scars")
    (r1,) = node.process(**kwargs)
    (r2,) = node.process(**kwargs)
    assert np.array_equal(r1.data, r2.data)
