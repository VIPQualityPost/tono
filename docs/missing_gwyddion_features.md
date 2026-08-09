# Missing Gwyddion Features

Gwyddion 2D image/surface processing features not yet implemented in tono. Excludes force curves, force volume, spectroscopy, volume data, XYZ data, graph operations, and file I/O.

Status key: `[x]` = implemented in tono (with the node(s) providing it), `[ ]` = still missing. Ports follow the Gwyddion source (`modules/process/*.c` + `libprocess/*.c`) where available.

## Leveling / Background Removal

- [x] **Arc Revolve** — Subtract cylindrical arc background fitted by revolving an arc under the data
- [x] **Sphere Revolve** — Subtract spherical cap background
- [x] **Unrotate** — Auto-detect and correct in-plane scan rotation by finding dominant feature directions
- [x] **Level Rotate** — Level by physically rotating the data plane rather than subtracting a polynomial
- [x] **Zero Mean Value** — Shift all values so the mean is exactly zero (pure offset, no plane fit)
- [x] **Zero Maximum Value** — Shift all values so the maximum is exactly zero

## Filtering / Signal Processing

- [x] **2D CWT** — Continuous Wavelet Transform for scale-space analysis — `2D CWT` (FFT-based, Gaussian/Mexican-hat wavelets, max-over-scales output; ports `libprocess/cwt.c gwy_data_field_cwt`)
- [x] **XY Denoise** — Denoise by combining two orthogonal scans — `XY Denoise` (ports `xydenoise.c`)
- [x] **Rank Presentation** — Rank transform image for local contrast enhancement — `Rank` (exact port of `rank.c` local_rank: inscribed-ellipse window, tie weights, edge truncation)
- [x] **Radial Smoothing** — Smooth data in polar coordinates, averaging along radial or angular direction — `Radial Smoothing` (ports `raveraging.c` polar remapping)
- [x] **Convolve Two Images** — Convolve two separate data channels together — `Convolve` (ports `convolve.c` + `filters-convdeconv.c`; full/same/valid modes, z-unit product)

## Line Correction / Scan Artifacts

- [x] **Step Block Correction** — Correct vertical step offsets between scan lines by block-matching — `Step Block Correction` (ports `blockstep.c`: block construction, scan-split scoring, trimmed-mean step estimation)
- [x] **Good Mean Profile** — Compute a high-quality average scan line from repeated scans — `Good Mean Profile` (ports `good_profile.c` single/multiple modes; outputs corrected field + mean profile LINE)
- [x] **Align Rows (extended methods)** — Modus and Gaussian-weighted (Matching) row alignment added to `Line Correction` alongside median/trimmed/polynomial/step (ports `linematch.c` LINE_MATCH_MODUS / LINE_MATCH_MATCH)

## Correction / Restoration

- [x] **Coerce** — Force data to match a target value distribution (uniform, Gaussian, or levels) — `Distribution Coercion`
- [x] **Fractal Correction** — Fill masked/bad pixels using fractal interpolation (alternative to Laplace) — `Fractal Interpolation`
- [x] **Reorder** — Fix scan-line ordering artifacts, including interleaved-to-sequential deinterlacing and reverse-scan rows — `Scan Line Reorder` (reverse_odd/reverse_even, deinterlace_odd/even, flip_vertical)
- [x] **Correlation Averaging** — Average repeated similar structures using autocorrelation alignment — `Correlation Averaging` (ports `averaging.c` find_local_maxima + `correlation.c` normalised score; reports per-repeat shifts)
- [x] **Periodic Translate** — Translate image data treating the field as periodic (wrap-around shift) — `Periodic Translate` (ports `ptranslate.c`, optional origin-offset update)

## Statistical Analysis

- [x] **Transfer Function Fit** — Fit PSF from a known reference image and a measured blurred image — `PSF Estimation` (wiener / least_squares / gaussian_fit; also reports sigma/amplitude parameters)
- [x] **Transfer Function Guess** — Estimate the transfer function from a measured image and an ideal response — `Transfer Function Guess` (ports `psf.c` regularized/wiener/least-squares deconvolution + region estimation; note: like the C module it requires both measured and ideal inputs)
- [x] **Angle Distribution** — Distribution of surface normal angles — `Angle Distribution` (ports `angle_dist.c` slope computation + local-plane fitting; LINE distribution + mean/std/max rows)

## Grain Operations

- [x] **Otsu Threshold** — Automated grain/mask threshold using Otsu's method — `Threshold Mask` (method = otsu, reports the effective threshold value)
- [x] **Remove Edge-Touching Grains** — Remove all grains touching the image border from a mask — `Grain Filter` (remove_border)
- [x] **Grain Selection Shapes** — Create geometric selections (bounding boxes, inscribed discs, etc.) from grain masks — `Grain Selection Shapes` (inscribed discs via distance transform, circumscribed circles via convex hull; ports `grain_makesel.c`)

## Mask Operations

- [x] **Mark With** — Create or modify a mask using arithmetic/relational conditions on two channels — `Mark With` (ports `mark_with.c` operations)
- [ ] **Mask Distribute** — Copy/distribute a mask to multiple channels simultaneously — skipped: Gwyddion's module operates on a multi-channel file container (distributes one channel's mask to all channels); tono's graph model has no per-channel mask storage, so there is no meaningful port. Save already writes masks per channel.
- [ ] **Mask Thin** — Morphological thinning to single-pixel-wide skeletons — not present in the referenced Gwyddion source (`mask_morph.c` exposes erosion/dilation/open/close/ASF with disc/octagon/square/diamond/user kernels; no thinning operation exists upstream), so no reference port is available.

## Basic Operations

- [x] **Log Scale Presentation** — Log-scaled presentation layer without modifying source data — `Presentation Ops` (logscale)
- [x] **Invert Value** — Flip heights (z to -z) — `Invert Value` (ports `basicops.c` invert_value → `gwy_data_field_invert`: z reflects about the mean, x/y mirror the axes; equal to plain negation for zero-mean data)
- [x] **Limit Range** — Clamp data values to a specified min/max range — `Limit Range` (ports `threshold.c` range mode → `gwy_data_field_clamp`, plus a scale-to-[0,1] mode as documented extension)
- [x] **Square Samples** — Resample so pixels are physically square (equal x/y size) — `Square Samples` (ports `basicops.c` square_samples: gains pixels on the deficient axis, preserving physical extents)
- [x] **Null Offsets** — Zero out the lateral (XY) origin offsets — `Null Offsets` (ports `basicops.c` null_offsets)

## SPM-Specific Modes

- [x] **MFM Field Simulation** — Simulate magnetic stray field above perpendicular media — `MFM Domain Generation` (parallel stripe domains with alternating up/down magnetization; outputs Hz and dHz/dz)
- [x] **MFM Parallel Media** — Simulate MFM signal for in-plane magnetic media — `MFM Parallel Media` (ports `mfm_parallel.c` + `gwy_data_field_mfm_parallel_medium`: Biot-Savart wall-boundary sums; HX/HZ/force-gradient components)
- [x] **MFM Lift Shift** — Rescale an MFM field to a different lift height — `MFM Lift Shift` (ports `gwy_data_field_mfm_shift_z`: FFT × exp(-2π|k|Δz))
- [x] **MFM Lift Estimate** — Estimate the lift height difference between two MFM images — `MFM Lift Estimate` (ports `gwy_data_field_mfm_find_shift_z` residual scan + parabolic minimum)
- [x] **MFM Force Gradient** — Convert MFM raw data to force gradient units — `MFM Analysis` (phase_to_force_gradient, plus force_gradient_to_field, charge_density, magnetisation)
- [x] **SMM Apply Calibration** — Apply Scanning Microwave Microscopy calibration coefficients — `SMM Analysis` (3-point calibration → capacitance and real impedance maps)
- [x] **MFM Current Simulation** — Infinite current strip simulation (`MFM Current Simulation`, outputs Hx, Hz, and force)

## Synthetic Surface Generators

tono's single `Synthetic Surface` node covers nearly all of Gwyddion's specialized generators via its `pattern` selector:

- [x] **Fractional Brownian Motion** — fBm rough surfaces with controlled Hurst exponent (`pattern = fbm`)
- [x] **Spectral Synthesis** — PSD-specified random rough surfaces (`pattern = spectral`)
- [x] **Lattice** — Crystalline lattice surface with defects (periodic lattice with spacing/angle controls, `pattern = lattice` / `periodic`)
- [x] **Objects** — Randomly placed 3D objects (spheres, pyramids, boxes, cylinders, cones, `pattern = objects`)
- [x] **Patterns** — Geometric patterns (staircase, gratings, checker, hex, stripe, diamonds, rings, `pattern = periodic` / `steps`)
- [x] **Waves** — Sinusoidal/wave patterns (`pattern = waves`)
- [x] **Noise** — Uncorrelated random noise with configurable distribution (gaussian/poisson/exponential/uniform/salt_pepper, `pattern = noise` / `white_noise`)
- [x] **Line Noise** — Synthetic scan-line noise/steps/scars for testing — `pattern = line_noise` (ports `lno_synth.c`)
- [x] **Fibres** — Random fibre network surfaces (`pattern = fibres`)
- [x] **Domain Walls** — Phase-separated domain structures (`pattern = domains`)
- [x] **Columnar Growth** — Columnar thin-film growth simulation (`pattern = columnar`)
- [x] **Ball Deposition** — Random ballistic deposition growth (`pattern = ballistic`)
- [x] **Particle Deposition** — Dynamical particle deposition model (`pattern = deposition` / `particles`)
- [x] **Rod Deposition** — Rod-like particle deposition (`pattern = rods`)
- [x] **Diffusion** — Diffusion-limited aggregation surfaces (`pattern = dla`)
- [x] **Discs** — Random overlapping disc surfaces (`pattern = discs`)
- [x] **CPDE / Turing** — Reaction-diffusion / Turing pattern surfaces (`pattern = pde`)
- [x] **Sand Dunes** — Aeolian sand transport simulation (`pattern = dunes`)
- [x] **Annealing Lattice Gas** — Annealed lattice-gas model textures (`pattern = annealing`)
- [x] **Phase Separation** — Spinodal decomposition textures (`pattern = spinodal`)
- [x] **Pileup** — Piled-up ellipsoids or bars (`pattern = pileups`)
- [x] **Plateaus** — Stacked random plateau/terrace structures (`pattern = plateaus`)
- [x] **Film Residue** — Residue left after simulated film removal (`pattern = residues`)
- [x] **Wetting Front** — Propagating wetting front simulation (`pattern = wfr`)

## Colour Operations

Distinct from colormap/pseudocolour selection (Gwyddion's *Color scale* / tono's `Color Map` and
`Colormap Adjust` nodes, which tono already has); these operate on multi-channel colour *images*:

- [x] **Composite** — Combine multiple fields into the colour channels of one image — `Merge` (R/G/B inputs, auto or manual per-channel scaling)
- [ ] **Extract Channel** — Extract an R/G/B/alpha channel from an image as a field — not present as a process module in the referenced Gwyddion source, so no reference port is available; `Merge` covers the inverse direction only
- [ ] **Change Colour Space** — Convert between RGB/HSV/HSL representations — not present as a process module in the referenced Gwyddion source

## Implemented Gwyddion counterparts (kept out of the missing list)

Already implemented elsewhere in tono and intentionally absent from this list: plane/polynomial/facet/terrace levelling, line correction, drift correction, scar/spot removal, Laplace/fractal inpainting, FFT + inverse FFT + filtering + PSDF/log-polar PSDF, cross-correlation, template matching, feature detection, grain analysis/summary/distributions/distance transform, watershed segmentation, MFM/PFM/SMM/lateral-force/SEM simulation and analysis, super-resolution, tip model/blind estimation/shape estimation/deconvolution, 3D view, and the measure set (statistics, histogram, curvature, shape fitting, lattice measurement, fractal dimension, slope distribution, radial profile, relate fields, cross-section, angle distribution, correlation averaging).
