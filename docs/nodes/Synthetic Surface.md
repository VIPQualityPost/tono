# Synthetic Surface

Generate synthetic test surfaces for development, calibration, and algorithm testing. 28 patterns covering noise, geometry, growth simulations, phase separation, reaction-diffusion, and tiling. Equivalent to Gwyddion's *_synth.c modules.

## Outputs

| Name | Type | Description |
|------|------|-------------|
| surface | DATA_FIELD | Generated synthetic surface |

## Controls

### Required

| Name | Type | Default | Description |
|------|------|---------|-------------|
| pattern | dropdown | fbm | Synthesis pattern (28 options, see Notes below) |
| xres | INT | 256 | Horizontal resolution in pixels (16--2048) |
| yres | INT | 256 | Vertical resolution in pixels (16--2048) |
| xreal | FLOAT | 1e-6 | Physical width in metres (1e-9--1.0) |
| yreal | FLOAT | 1e-6 | Physical height in metres (1e-9--1.0) |
| amplitude | FLOAT | 1e-9 | Peak-to-peak amplitude in metres (0--1e-3) |
| seed | INT | 42 | Random seed for reproducibility (0--999999) |

### Optional (pattern-specific)

| Name | Type | Default | Range | Used by |
|------|------|---------|-------|---------|
| hurst_exponent | FLOAT | 0.7 | 0.0--1.0 | fbm |
| lattice_spacing | FLOAT | 100e-9 | 1e-9--1e-3 | lattice |
| lattice_angle | FLOAT | 90.0 | 0--180 | lattice |
| n_steps | INT | 5 | 1--100 | steps |
| n_particles | INT | 20 | 1--500 | particles, objects, discs, plateaus, pileups, residues, fibres, rods, columnar, deposition, waves, wfr, voronoi |
| particle_radius_px | INT | 10 | 2--100 | particles, objects, discs, plateaus, pileups, residues, columnar, deposition, fibres (width), rods (width) |
| n_iterations | INT | 200 | 10--5000 | domains, ballistic, annealing, spinodal, pde, dla |
| direction_deg | FLOAT | 0.0 | 0--360 | dunes |
| feature_length_px | INT | 40 | 2--500 | fibres, rods |
| object_shape | dropdown | sphere | sphere, pyramid, box, cylinder, cone | objects |
| noise_type | dropdown | gaussian | gaussian, poisson, exponential, uniform, salt_pepper | noise |
| periodic_type | dropdown | checker | checker, hex, stripe, diamond, staircase, rings | periodic |
| spectral_exponent | FLOAT | 2.0 | 0.5--5.0 | spectral |
| frequency | FLOAT | 5.0 | 0.5--50.0 | waves, dunes, periodic, wfr |

## Notes

All 28 patterns are normalised to the specified amplitude range after generation and use the seed for reproducibility. Changing the seed produces a different random realisation of the same pattern type. Optional parameters that do not apply to the selected pattern are silently ignored.

---

### Random & Spectral

**fbm** -- Fractional Brownian motion via spectral synthesis. Generates a 2D FFT field whose power spectrum follows a power law controlled by the Hurst exponent. An exponent of 0 produces very rough, jagged surfaces; an exponent of 1 produces smooth, gently undulating terrain. This models naturally rough surfaces such as thin films, etched or polished substrates, and geological terrain. Use it whenever you need a statistically self-affine rough surface for testing roughness analysis or levelling algorithms.

- Controls: `hurst_exponent` (0.0--1.0, default 0.7)

**white_noise** -- Uncorrelated Gaussian random noise. Every pixel is drawn independently from a standard normal distribution. This models detector noise, thermal noise floors, or provides a baseline noise field for testing denoising algorithms and signal-to-noise ratio calculations. No additional parameters beyond the common required controls.

**noise** -- Various noise distributions beyond Gaussian. Selecting a distribution changes the statistical character of the noise field:

- *gaussian* (default): standard normal distribution, symmetric tails.
- *poisson*: integer-valued noise with lambda = 5; models photon counting statistics in optical or X-ray detection.
- *exponential*: one-sided distribution; models rare-event intervals or surface feature waiting times.
- *uniform*: flat distribution over [0, 1]; every value equally likely.
- *salt_pepper*: impulse noise where ~5% of pixels are set to +1 or -1, rest zero; models dead pixels or spike artefacts in detector arrays.

Use this pattern to test how processing algorithms handle non-Gaussian noise statistics.

- Controls: `noise_type`

**spectral** -- FFT-based surface with a power-law spectrum P(k) proportional to k^(-alpha). This is a generalisation of FBM where the spectral exponent directly sets how power is distributed across spatial frequencies. A low exponent (near 0.5) concentrates energy at high spatial frequencies, producing rough, fine-grained textures. A high exponent (near 5.0) concentrates energy at low frequencies, producing smooth surfaces with long-range correlations. Use it to create test surfaces with precisely controlled spatial frequency content for filter testing or PSDF validation.

- Controls: `spectral_exponent` (0.5--5.0, default 2.0)

---

### Geometric Features

**particles** -- Random spherical particles on a flat background. Each particle is a hemispherical cap whose height is determined by the radius and position. Later particles overlay earlier ones (maximum height rule). This models nanoparticle deposits on substrates as seen in AFM imaging of colloidal or catalytic nanoparticle samples. Use it to test grain detection, particle counting, and size distribution algorithms.

- Controls: `n_particles` (count), `particle_radius_px` (radius in pixels)

**objects** -- Various 3D geometric shapes placed at random positions. Five shapes are available:

- *sphere*: hemispherical bumps (same geometry as particles).
- *pyramid*: four-sided pyramid with linear slopes meeting at a point.
- *box*: flat-topped rectangular blocks with vertical walls.
- *cylinder*: flat-topped circular pillars.
- *cone*: circular cone with linear profile tapering to a point.

Heights are randomised per object and the maximum-height rule applies. This models calibration gratings, nanofabricated structure arrays, and MEMS features. Use it to test shape recognition, tip characterisation, and volume measurement algorithms.

- Controls: `n_particles` (count), `particle_radius_px` (size), `object_shape`

**discs** -- Flat-topped circular disc features at random positions with random heights. The disc boundary is a sharp step edge. This models thin film islands, lithographic dot arrays, and etched circular features. Use it to test edge detection, step height measurement, and area coverage analysis.

- Controls: `n_particles` (count), `particle_radius_px` (radius)

**plateaus** -- Flat-topped circular features with smooth (tanh-profile) edge transitions instead of sharp steps. The edge transition width is 20% of the radius. This models mesa structures, etched plateaus, and features where the imaging tip or physical process rounds the edges. Useful for testing algorithms that need to distinguish between sharp and gradual step edges.

- Controls: `n_particles` (count), `particle_radius_px` (radius)

**pileups** -- Rounded rectangle structures with random aspect ratio (0.5--2.0) and random orientation. The profile uses a superelliptic (quartic) distance function, producing smoothly rounded rectangular footprints. This models rectangular nanostructures, MEMS features, and lithographic pads with rounded corners. Use it for testing grain shape analysis on non-circular features.

- Controls: `n_particles` (count), `particle_radius_px` (size)

**residues** -- Irregular elliptical deposits with random orientation and random aspect ratio (0.3--3.0). Each deposit has a Gaussian height profile, producing smooth, blob-like features. This models contamination residues, biological particles (cells, proteins), and other irregular deposits commonly encountered in AFM imaging of soft matter. Useful for testing feature detection on non-uniform, non-circular objects.

- Controls: `n_particles` (count), `particle_radius_px` (size)

---

### Linear Features

**fibres** -- Randomly oriented rectangular line features (constant cross-section, flat top). Each fibre has random position, orientation, and height. This models polymer fibres, nanowires, surface scratches, and elongated crystallites. Use it to test line detection, orientation analysis, and fibre network characterisation. The `particle_radius_px` parameter controls fibre width (half-width in pixels) while `feature_length_px` controls length.

- Controls: `n_particles` (count), `feature_length_px` (length), `particle_radius_px` (width)

**rods** -- Like fibres but with a semicircular cross-section profile instead of a flat top. This produces a more physically realistic rounded wire shape. Models nanowires, carbon nanotubes, and other cylindrical structures imaged by AFM where the cross-section appears as a half-circle due to tip convolution. Use it for testing tip deconvolution and cross-section fitting algorithms.

- Controls: `n_particles` (count), `feature_length_px` (length), `particle_radius_px` (width)

---

### Periodic & Tiling

**lattice** -- Two-axis sinusoidal grid. Two cosine waves are superimposed along directions separated by the specified angle, both with the same spatial period. At 90 degrees this produces a square grid; at 60 degrees a hexagonal-like pattern. This models crystal surfaces, calibration gratings, and periodic nanostructure arrays. Use it for testing Fourier analysis, lattice measurement, and periodicity detection.

- Controls: `lattice_spacing` (period in metres), `lattice_angle` (angle between lattice vectors in degrees, 0--180)

**steps** -- Terraced step structure with equal step heights across the x-axis. The surface is a staircase function with the specified number of terraces. This models vicinal crystal surfaces and atomic step trains as seen in STM/AFM imaging of semiconductor or metal surfaces. Use it for testing step detection, terrace fitting, and step height measurement algorithms.

- Controls: `n_steps` (number of terraces, 1--100)

**periodic** -- Repeating tiling patterns. Six tiling types are available:

- *checker* (default): alternating black/white squares (checkerboard).
- *hex*: hexagonal array of circular dots.
- *stripe*: vertical stripes (binary, based on sine threshold).
- *diamond*: diamond/rhombus tiling pattern.
- *staircase*: stepped ramp repeating across x.
- *rings*: concentric ring pattern centred on the field.

This models lithographic patterns, photonic crystal layouts, and periodic test structures. Use it for testing spatial frequency analysis, periodicity detection, and pattern recognition. The `frequency` parameter controls the spatial frequency (number of pattern repeats across the field).

- Controls: `frequency` (spatial frequency, 0.5--50.0), `periodic_type`

**flat** -- Zero surface (all pixel values are zero before amplitude scaling; the output is identically zero regardless of amplitude). This serves as a baseline for testing, a null input for algorithm validation, or a starting point to be combined with other operations via Field Arithmetic. No additional parameters.

---

### Wave Patterns

**waves** -- Superposition of decaying circular waves from random source points. Each source emits a cosine wave that decays exponentially with distance (decay constant of 3.0 in normalised coordinates). Source amplitudes are randomised. This models surface acoustic wave interference, ripple patterns from localised impacts, and capillary wave superposition. Use it for testing wavelet analysis and source localisation algorithms.

- Controls: `n_particles` (number of wave sources), `frequency` (spatial frequency)

**dunes** -- Asymmetric sawtooth-like ripples along a specified direction. The profile ramps gradually over 70% of the period and drops sharply over the remaining 30%, mimicking wind-blown dune asymmetry. A small amount of Gaussian noise (3% amplitude) is added for realism. This models aeolian dune patterns, directional ion beam sputtering ripples, and other asymmetric periodic surface textures. Use it for testing directional analysis and asymmetry quantification.

- Controls: `frequency` (ripple frequency), `direction_deg` (propagation direction in degrees, 0--360)

**wfr** -- Concentric wavefronts from random sources without amplitude decay -- pure interference. Unlike `waves`, there is no exponential fall-off, so all sources contribute equally everywhere, producing complex moire-like interference patterns. The result is normalised by the number of sources. This models wave interference experiments, moire patterns, and standing wave fields. Use it for testing interference fringe analysis and phase extraction.

- Controls: `n_particles` (number of sources), `frequency` (spatial frequency)

---

### Growth & Deposition Simulations

**columnar** -- Gaussian pillar growth at random positions. Each column is a 2D Gaussian bump whose width is set by the radius parameter and whose height is randomised. Columns are summed (additive stacking), so overlapping columns produce taller features. This models columnar thin film growth as seen in PVD (physical vapour deposition) and CVD (chemical vapour deposition) processes. Use it for testing grain analysis on columnar microstructures.

- Controls: `n_particles` (number of columns), `particle_radius_px` (column width)

**deposition** -- Spherical particles deposited sequentially with gravity-like stacking. Each particle is a hemisphere; when it lands on existing material, it sits on top of the highest point within its footprint. This produces layered, stacked structures where later particles rest on earlier ones. Models sequential particle deposition, powder coatings, and colloidal stacking. Use it for testing height profile analysis of layered structures.

- Controls: `n_particles` (number of deposited particles), `particle_radius_px` (particle radius)

**ballistic** -- Ballistic deposition with neighbour adhesion. In each iteration, ~30% of randomly chosen sites receive a particle. The deposited height is one plus the maximum of the site's own height and its four nearest neighbours, producing lateral correlation and rough, porous growth fronts. This is a vectorised simulation of the classic ballistic deposition model. Models thin film growth with surface tension effects and produces surfaces with characteristic scaling exponents. Use it for testing roughness scaling analysis and growth exponent estimation.

- Controls: `n_iterations` (10--5000)

**dla** -- Diffusion-limited aggregation via iterative boundary growth from a central seed. At each iteration the cluster boundary is dilated, and a fraction (~12.5%) of boundary pixels are randomly added to the aggregate with random heights. This produces fractal, dendritic structures characteristic of DLA. Models electrodeposition, frost formation, mineral dendrites, and crystallisation from solution. Use it for testing fractal dimension analysis and morphological characterisation.

- Controls: `n_iterations` (10--5000)

---

### Phase Separation & PDE

**domains** -- Phase-separated domain patterns via a 2D Ising model using the checkerboard Metropolis algorithm. The surface is initialised with random +/-1 spins and evolved at inverse temperature beta = 0.55 (above the critical temperature for ordering). More iterations produce larger, more coarsened domains. This models magnetic domain patterns, block copolymer self-assembly, and binary alloy phase separation. The output is a binary +/-1 field that is normalised to the amplitude range. Use it for testing domain size analysis, boundary detection, and correlation length measurement.

- Controls: `n_iterations` (10--5000)

**spinodal** -- Spinodal decomposition via the Cahn-Hilliard equation solved with an FFT-based semi-implicit scheme. The initial condition is a near-uniform concentration (0.5) with small random perturbations. The system phase-separates into interconnected, bicontinuous domain structures whose characteristic length scale grows with iteration count. This models spinodal decomposition in alloys, polymer blends, and lipid membranes. Use it for testing structure factor analysis, domain coarsening kinetics, and bicontinuous morphology characterisation.

- Controls: `n_iterations` (10--5000)

**pde** -- Gray-Scott reaction-diffusion system producing Turing patterns. Two chemical species (u, v) react and diffuse with parameters F = 0.035, k = 0.065, which lies in the spots/stripes regime. The reaction is seeded in a central square region and grows outward. With few iterations (< 200) the pattern is sparse; with many iterations (500--2000) the pattern fills most of the field with well-developed spots and labyrinthine stripes. This models biological pattern formation (animal coat patterns, morphogenesis), chemical self-organisation (Belousov-Zhabotinsky reaction), and provides complex test patterns for segmentation algorithms.

- Controls: `n_iterations` (10--5000; recommend 500--2000 for fully developed patterns)

**annealing** -- Simulated annealing surface relaxation. Starts with a random Gaussian noise surface and progressively smooths it by averaging with nearest neighbours while adding decreasing amounts of thermal noise. The temperature decreases linearly from 1.0 to 0.01 over the iteration count. This models thermal relaxation, surface diffusion at elevated temperature, and produces surfaces with controlled correlation lengths. More iterations yield smoother surfaces. Use it for testing smoothness quantification and correlation analysis.

- Controls: `n_iterations` (10--5000)

---

### Tessellation

**voronoi** -- Voronoi tessellation with random heights per cell. Random seed points are placed in the field and each pixel is assigned to its nearest seed point. Every cell receives a uniform random height, producing a mosaic of flat-topped polygonal grains separated by sharp boundaries. This models grain boundaries in polycrystalline thin films, biological cell boundaries, and territorial partitioning. Use it for testing grain boundary detection, grain size distribution analysis, and watershed segmentation algorithms.

- Controls: `n_particles` (number of Voronoi sites)
