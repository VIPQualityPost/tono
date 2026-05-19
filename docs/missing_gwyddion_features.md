# Missing Gwyddion Features

Gwyddion 2D image/surface processing features not yet implemented in tono. Excludes force curves, force volume, spectroscopy, volume data, XYZ data, graph operations, and file I/O.

## Leveling / Background Removal

- [x] **Arc Revolve** — Subtract cylindrical arc background fitted by revolving an arc under the data
- [x] **Sphere Revolve** — Subtract spherical cap background
- [x] **Unrotate** — Auto-detect and correct in-plane scan rotation by finding dominant feature directions
- [x] **Level Rotate** — Level by physically rotating the data plane rather than subtracting a polynomial
- [x] **Zero Mean Value** — Shift all values so the mean is exactly zero (pure offset, no plane fit)
- [x] **Zero Maximum Value** — Shift all values so the maximum is exactly zero

## Filtering / Signal Processing

- [ ] **2D CWT** — Continuous Wavelet Transform for scale-space analysis
- [ ] **XY Denoise** — Denoise by combining two orthogonal scans (forward/backward or horizontal/vertical)
- [ ] **Rank Presentation** — Rank transform image for local contrast enhancement
- [ ] **Radial Smoothing** — Smooth data in polar coordinates, averaging along radial or angular direction
- [ ] **Convolve Two Images** — Convolve two separate data channels together

## Line Correction / Scan Artifacts

- [ ] **Step Block Correction** — Correct vertical step offsets between scan lines by block-matching
- [ ] **Good Mean Profile** — Compute a high-quality average scan line from repeated scans
- [ ] **Align Rows (extended methods)** — Modus and Gaussian-weighted row alignment beyond tono's current set

## Correction / Restoration

- [ ] **Fractal Correction** — Fill masked/bad pixels using fractal interpolation (alternative to Laplace)
- [ ] **Correlation Averaging** — Average repeated similar structures using autocorrelation alignment
- [ ] **Coerce** — Force data to match the histogram distribution of another dataset
- [ ] **Periodic Translate** — Translate image data treating the field as periodic (wrap-around shift)
- [ ] **Reorder** — Reorder pixel rows/columns (interleaved to sequential, reverse scan, etc.)

## Statistical Analysis

- [ ] **Transfer Function Fit** — Fit PSF from a known reference image and a measured blurred image
- [ ] **Transfer Function Guess** — Estimate PSF from a single image without a reference
- [ ] **Angle Distribution** — Distribution of surface normal angles (distinct from slope distribution)

## Grain Operations

- [ ] **Otsu Threshold** — Automated grain/mask threshold using Otsu's method
- [ ] **Remove Edge-Touching Grains** — Remove all grains touching the image border from a mask
- [ ] **Grain Selection Shapes** — Create geometric selections (bounding boxes, inscribed discs, etc.) from grain masks

## Mask Operations

- [ ] **Mask Thin** — Morphological thinning to single-pixel-wide skeletons
- [ ] **Mask Distribute** — Copy/distribute a mask to multiple channels simultaneously
- [ ] **Mark With** — Create or modify a mask using arithmetic conditions on other channels

## Basic Operations

- [ ] **Invert Value** — Flip heights (z to -z)
- [ ] **Log Scale Presentation** — Log-scaled presentation layer without modifying source data
- [ ] **Limit Range** — Clamp data values to a specified min/max range
- [ ] **Square Samples** — Resample so pixels are physically square (equal x/y size)
- [ ] **Null Offsets** — Zero out the lateral (XY) origin offsets

## SPM-Specific Modes

- [ ] **MFM Field Simulation** — Simulate magnetic stray field above perpendicular media
- [ ] **MFM Parallel Media** — Simulate MFM signal for in-plane magnetic media
- [ ] **MFM Lift Shift** — Simulate MFM signal change when lift height changes
- [ ] **MFM Lift Estimate** — Estimate lift height difference from data blur
- [ ] **MFM Force Gradient** — Convert MFM raw data to force gradient units
- [ ] **SMM Apply Calibration** — Apply Scanning Microwave Microscopy calibration coefficients

## Synthetic Surface Generators

Tono has one generic Synthetic Surface node. Gwyddion has ~20+ specialized generators:

- [ ] **Fractional Brownian Motion** — fBm rough surfaces with controlled Hurst exponent
- [ ] **Spectral Synthesis** — PSD-specified random rough surfaces
- [ ] **Lattice** — Crystalline lattice surface with defects
- [ ] **Objects** — Randomly placed 3D objects (spheres, pyramids, etc.)
- [ ] **Patterns** — Geometric patterns (staircase, gratings, etc.)
- [ ] **Waves** — Sinusoidal/wave patterns
- [ ] **Noise** — Uncorrelated random noise with configurable distribution
- [ ] **Line Noise** — Synthetic scan-line noise/steps/scars for testing
- [ ] **Fibres** — Random fibre network surfaces
- [ ] **Domain Walls** — Phase-separated domain structures
- [ ] **Columnar Growth** — Columnar thin-film growth simulation
- [ ] **Ball Deposition** — Random ballistic deposition growth
- [ ] **Particle Deposition** — Dynamical particle deposition model
- [ ] **Rod Deposition** — Rod-like particle deposition
- [ ] **Diffusion** — Diffusion-limited aggregation surfaces
- [ ] **Discs** — Random overlapping disc surfaces
- [ ] **CPDE / Turing** — Reaction-diffusion / Turing pattern surfaces
- [ ] **Sand Dunes** — Aeolian sand transport simulation
- [ ] **Annealing Lattice Gas** — Annealed lattice-gas model textures
- [ ] **Phase Separation** — Spinodal decomposition textures
- [ ] **Pileup** — Piled-up ellipsoids or bars
- [ ] **Plateaus** — Stacked random plateau/terrace structures
- [ ] **Film Residue** — Residue left after simulated film removal
- [ ] **Wetting Front** — Propagating wetting front simulation
