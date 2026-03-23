# Gwyddion Features Not Yet in Argonode

Reference for future implementation. Grouped by value to typical SPM workflows.

---

## High Value

| # | Feature | Gwyddion Source | Description |
|---|---------|---------------|-------------|
| 1 | Line Correction | linecorrect.c, linematch.c | Row-by-row median/polynomial alignment. Essential for raw SPM data with scan-line artifacts. |
| 2 | Scar Removal | scars.c | Detect and interpolate scan-line defects (horizontal streaks). |
| 3 | Facet Leveling | facet-level.c | Orient the dominant surface facet to horizontal. Better than plane level for terraced/stepped surfaces. |
| 4 | Morphological Mask Ops | mask_morph.c | Erode, dilate, open, close on grain masks. Needed to clean up thresholded masks. |
| 5 | 1D FFT Filter | fft_filter_1d.c | Bandpass/lowpass/highpass filtering of LINE profiles. |
| 6 | 2D FFT Filter | fft_filter_2d.c | Frequency-domain filtering of DATA_FIELDs (remove periodic noise, etc.). |
| 7 | Autocorrelation (ACF) | acf2d.c | 2D autocorrelation function. Reveals periodic structures and correlation lengths. |
| 8 | PSDF | psdf2d.c | Radial/2D power spectral density function. Complementary to ACF for roughness characterization. |
| 9 | Fractal Dimension | fractal.c | Multiple methods: partitioning, cube counting, triangulation, PSDF, HHCF. Quantifies surface complexity. |
| 10 | Curvature | curvature.c | Local mean/Gaussian curvature maps. Useful for feature identification. |
| 11 | Grain Distance Transform | mask_edt.c | Euclidean distance from grain boundaries. Useful for spatial distribution analysis. |
| 12 | Watershed Segmentation | grain_wshed.c | Automatic grain detection without manual threshold. More robust than simple thresholding. |
| 13 | Rotate / Flip | rotate.c, basicops.c | Basic geometric transforms (90°, arbitrary angle, mirror). |
| 14 | Crop | crop.c | Extract sub-region of a field. |

## Medium Value

| # | Feature | Gwyddion Source | Description |
|---|---------|---------------|-------------|
| 15 | Correlation / Pattern Matching | crosscor.c, maskcor.c | Find repeated features or align images via cross-correlation. |
| 16 | Slope Distribution | slope_dist.c | Angular histogram of surface slopes. Characterizes surface texture directionality. |
| 17 | Grain Filtering | grain_filter.c | Remove grains by size, height, or border contact. Refine grain masks post-detection. |
| 18 | Field Arithmetic | arithmetic.c | Add/subtract/multiply/divide two DATA_FIELDs. Useful for difference maps, normalization. |
| 19 | Spot Removal | spotremove.c | Interpolate over selected point defects (dust, spikes). |
| 20 | Tip Modeling / Deconvolution | tip_blind.c, tip_model.c | Estimate tip shape from image, deconvolve to recover true surface. |
| 21 | Radial Profile | rprofile tool | Azimuthally averaged profile from a center point. Good for circular features. |
| 22 | Wavelet Transform | dwt.c, cwt.c | Discrete/continuous wavelet analysis. Multi-scale roughness decomposition. |
| 23 | Scale / Resample | scale.c, resample.c | Resize fields with interpolation. |
| 24 | Gradient | gradient.c | Compute x/y gradient magnitude maps. |
| 25 | Custom Convolution | convolution_filter.c | User-defined kernel convolution. |
| 26 | Local Contrast Enhancement | local_contrast.c | Enhance visibility of local features in images. |

## Lower Priority

| # | Feature | Gwyddion Source | Description |
|---|---------|---------------|-------------|
| 27 | Drift Correction | drift.c | Compensate for thermal/piezo drift between scan lines. |
| 28 | Affine / Perspective Correction | correct_affine.c, correct_perspective.c | Fix geometric distortions from scanner nonlinearity. |
| 29 | MFM Analysis | mfm_*.c | Magnetic force microscopy: field calculation, shift finding. |
| 30 | Lattice Measurement | measure_lattice.c | Detect and measure periodic lattice structures from ACF/FFT. |
| 31 | Hough Transform | hough.c | Detect lines and circles in images. |
| 32 | Image Stitching / Merging | merge.c, stitch.c | Combine multiple overlapping scans into one image. |
| 33 | Facet Analysis | facet_analysis.c | Orientation distribution of surface facets (stereographic projection). |
| 34 | Shape Fitting | fit-shape.c | Fit geometric primitives: sphere, paraboloid, cylinder, etc. |
| 35 | Synthetic Surface Generation | *_synth.c (~20 modules) | Generate test surfaces: FBM, noise, lattice, waves, particles, fibers, etc. |
| 36 | Entropy | entropy.c | Information entropy of height distribution. |
| 37 | Indentation Analysis | indent_analyze.c, hertz.c | Nanoindentation curve fitting (Hertz model). |
| 38 | Deconvolution | deconvolve.c | Blind/regularized deconvolution for image restoration. |
| 39 | Canny / Harris Detection | filters.c | Corner and edge feature detection beyond basic Sobel/Prewitt. |
| 40 | Kuwahara Filter | filters.c | Edge-preserving smoothing filter. |

---

## Already Implemented in Argonode

For reference, these Gwyddion equivalents are already covered:

| Argonode Node | Category | Gwyddion Equivalent |
|--------------|----------|-------------------|
| Load Image / Load SPM File | io | File import (gwy, sxm, ibw) |
| Save Image | io | File export |
| Coordinate | io | — |
| Plane Level | level | level.c |
| Polynomial Level | level | polylevel.c |
| Fix Zero | level | level.c (fix_zero) |
| Gaussian Filter | filters | filters.c (gaussian) |
| Median Filter | filters | filters.c (median) |
| Edge Detect | filters | edge.c (sobel, prewitt, laplacian, LoG) |
| Statistics | analysis | stats.c |
| Height Histogram | analysis | linestats.c (dh) |
| 2D FFT | analysis | fft.c |
| Cross Section | analysis | profile tool |
| Profile Roughness | analysis | roughness.c (Ra, Rq, Rsk, Rku, Rp, Rv, Rt) |
| Line Math | analysis | linestats.c |
| Threshold Mask | grains | threshold.c, otsu_threshold.c |
| Grain Analysis | grains | grain_stat.c |
| Preview / 3D View / Print Table | display | Presentation, 3D view |
