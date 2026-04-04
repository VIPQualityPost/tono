# Gwyddion Feature Gap — tono

Comprehensive comparison against Gwyddion r29630. Excludes force curves, force volumes, and spectroscopic measurements. Grouped by priority for typical SPM workflows.

---

## Completed

All features from the original gap analysis are implemented:

| # | Feature | Gwyddion Source | tono Node |
|---|---------|---------------|-----------|
| 1 | Line Correction | linecorrect.c, linematch.c | LineCorrection |
| 2 | Scar Removal | scars.c | ScarRemoval |
| 3 | Facet Leveling | facet-level.c | FacetLevelField |
| 4 | Morphological Mask Ops | mask_morph.c | MaskMorphology |
| 5 | 1D FFT Filter | fft_filter_1d.c | FFTFilter |
| 6 | 2D FFT Filter | fft_filter_2d.c | FFTFilter |
| 7 | Autocorrelation (ACF) | acf2d.c | ACF2D |
| 8 | PSDF | psdf2d.c | PSDF |
| 9 | Fractal Dimension | fractal.c | FractalDimension |
| 10 | Curvature | curvature.c | Curvature |
| 11 | Grain Distance Transform | mask_edt.c | GrainDistanceTransform |
| 12 | Watershed Segmentation | grain_wshed.c | WatershedSegmentation |
| 13 | Rotate / Flip | rotate.c, basicops.c | RotateField, FlipField |
| 14 | Crop | crop.c | CropResizeField |
| 15 | Correlation / Pattern Matching | crosscor.c, maskcor.c | CrossCorrelate, TemplateMatch |
| 16 | Slope Distribution | slope_dist.c | SlopeDistribution |
| 17 | Grain Filtering | grain_filter.c | GrainFilter |
| 18 | Field Arithmetic | arithmetic.c | FieldArithmetic |
| 19 | Spot Removal | spotremove.c | SpotRemoval |
| 20 | Tip Modeling / Deconvolution | tip_blind.c, tip_model.c | TipModel, TipDeconvolution, BlindTipEstimate |
| 21 | Radial Profile | rprofile tool | RadialProfile |
| 22 | Wavelet Transform | dwt.c, cwt.c | WaveletDenoise |
| 23 | Scale / Resample | scale.c, resample.c | Resample |
| 24 | Gradient | gradient.c | Gradient |
| 25 | Custom Convolution | convolution_filter.c | CustomConvolution |
| 26 | Local Contrast Enhancement | local_contrast.c | LocalContrast |
| 27 | Drift Correction | drift.c | DriftCorrection |
| 28 | Affine Correction | correct_affine.c | AffineCorrection |
| 29 | MFM Analysis | mfm_*.c | MFMAnalysis |
| 30 | Lattice Measurement | measure_lattice.c | LatticeMeasurement |
| 31 | Hough Transform | hough.c | HoughTransform |
| 32 | Image Stitching | merge.c, stitch.c | ImageStitch |
| 33 | Facet Analysis | facet_analysis.c | FacetAnalysis |
| 34 | Shape Fitting | fit-shape.c | ShapeFitting |
| 35 | Synthetic Surface Generation | *_synth.c | SyntheticSurface |
| 36 | Entropy | entropy.c | Entropy |
| 38 | Deconvolution | deconvolve.c | Deconvolution |
| 39 | Canny / Harris Detection | filters.c | FeatureDetection |
| 40 | Kuwahara Filter | filters.c | KuwaharaFilter |

---

## Remaining Gaps

### High Value — Core SPM workflow features

| # | Feature | Gwyddion Source | tono Node | Status |
|---|---------|---------------|-----------|--------|
| 41 | Terrace Fitting | terracefit.c | TerraceFit | **DONE** |
| 42 | Laplace Interpolation | laplace.c | LaplaceInterpolation | **DONE** |
| 43 | Fractal Interpolation | fraccor.c | FractalInterpolation | **DONE** |
| 44 | Median Background Subtraction | median-bg.c | MedianBackground | **DONE** |
| 45 | Flatten Base | flatten_base.c | FlattenBase | **DONE** |
| 46 | Level Individual Grains | level_grains.c | LevelGrains | **DONE** |
| 47 | Grain Marking by Criteria | grain_mark.c | GrainMark | **DONE** |
| 48 | Grain Property Distributions | grain_dist.c | GrainDistributions | **DONE** |
| 49 | Grain Summary Statistics | grain_summary.c | GrainSummary | **DONE** |
| 50 | Outlier Masking | outliers.c | OutlierMask | **DONE** |
| 51 | Scan Line Reordering | reorder.c | ScanLineReorder | **DONE** |

### Medium Value — Analysis and correction

| # | Feature | Gwyddion Source | tono Node | Status |
|---|---------|---------------|-----------|--------|
| 52 | Perspective Correction | correct_perspective.c | PerspectiveCorrection | **DONE** |
| 53 | Polynomial Distortion | polydistort.c | PolynomialDistortion | **DONE** |
| 54 | Frequency Splitting | freq_split.c | FrequencySplit | **DONE** |
| 55 | Phase/Value Wrapping | wrapvalue.c | WrapValue | **DONE** |
| 56 | Shaded Presentation | shade.c | Shade | **DONE** |
| 57 | Pixel Binning | binning.c | PixelBinning | **DONE** |
| 58 | Extend / Pad | extend.c | ExtendPad | **DONE** |
| 59 | Tilt | tilt.c | Tilt | **DONE** |
| 60 | Trimmed Mean Filter | trimmed-mean.c | TrimmedMean | **DONE** |
| 61 | Rank Filter | rank-filter.c | RankFilter | **DONE** |
| 62 | Zero Crossing Detection | zero_crossing.c | ZeroCrossing | **DONE** |
| 63 | Log-Polar PSDF | psdf_logphi.c | LogPolarPSDF | **DONE** |
| 64 | Grain Edge Detection | grain_edge.c | GrainEdge | **DONE** |
| 65 | Grain Cross-Correlation | grain_cross.c | GrainCross | **DONE** |
| 66 | Mutual Crop | mcrop.c | MutualCrop | **DONE** |
| 67 | Immerse Detail | immerse.c | ImmerseDetail | **DONE** |
| 68 | Multiple Profiles | multiprofile.c | MultipleProfiles | **DONE** |
| 69 | Straighten Path | straighten_path.c | StraightenPath | **DONE** |
| 70 | Relate Two Fields | relate.c | RelateFields | **DONE** |

### SPM Mode-Specific

| # | Feature | Gwyddion Source | Description |
|---|---------|---------------|-------------|
| 71 | PFM Analysis | pfm.c | Piezoresponse Force Microscopy: compute in-plane and 3D polarization vectors from VPFM/LPFM amplitude and phase at multiple rotations. |
| 72 | Lateral Force Simulation | latsim.c | Simulate topography artifacts in lateral force (friction) channels given friction coefficient, adhesion, and normal load parameters. |
| 73 | SEM Simulation | semsim.c | Simulate Scanning Electron Microscopy signal from topography data using integration or Monte Carlo methods. |
| 74 | Scanning Microwave Microscopy | smm.c, smm_apply.c | Fit complex reflection coefficients from SMM impedance measurements to extract capacitance and material properties. |
| 75 | MFM Current Simulation | mfm_current.c | Simulate current distribution from magnetization for MFM. Extends existing MFMAnalysis node. |
| 76 | MFM Domain Generation | mfm_parallel.c | Generate parallel magnetic domain patterns for MFM simulation and testing. |

### Lower Priority — Specialized or niche

| # | Feature | Gwyddion Source | Description |
|---|---------|---------------|-------------|
| 77 | Mark Disconnected Regions | mark_disconn.c | Mask topologically isolated surface regions using threshold and radius criteria. |
| 78 | Mask Shift | mask_shift.c | Translate mask by pixel offset in any direction. |
| 79 | Mask Noisify | mask_noisify.c | Add random perturbation to mask boundaries. Useful for testing mask sensitivity. |
| 80 | DWT Anisotropy | dwtanisotropy.c | Quantify surface anisotropy using discrete wavelet transform decomposition. |
| 81 | Displacement Field | displfield.c | Distort images using displacement fields (Gaussian, tear, image-based). Simulates scanning artifacts. |
| 82 | Pixel Classification | classify.c | Classify pixels into categories using decision trees on height, slope, and curvature criteria. |
| 83 | Neural Network Classification | neural.c | Train and apply neural networks for pixel-level feature classification. |
| 84 | Logistic Classification | logistic.c | Classify features using logistic regression on Gaussian derivative features. |
| 85 | Super-Resolution | superresolution.c | Combine multiple aligned low-resolution scans to produce a higher-resolution image. |
| 86 | PSF Estimation | psf.c, psf-fit.c | Estimate and fit point spread functions from image features for deconvolution. |
| 87 | Tip Shape from Features | tipshape.c | Estimate SPM tip shape from known calibration feature convolutions. |
| 88 | Presentation Ops | presentationops.c | Manage presentation overlays (extract, attach, remove presentation layers). |
| 89 | Calibration Coefficients | calcoefs_*.c, calibrate.c | Load, create, and apply lateral/height calibration corrections. |
| 90 | Distribution Coercion | coerce.c | Transform data distribution to match target (uniform, Gaussian, custom). |
| 91 | Grain Selection Visualization | grain_makesel.c | Visualize grains as discs, circles, or bounding boxes for selection. |

### Synthesis — Additional surface generation patterns

tono's SyntheticSurface node covers fbm, white_noise, lattice, steps, particles, and flat. Gwyddion has 24 separate synthesis modules. These could be added as patterns to the existing SyntheticSurface node:

| # | Pattern | Gwyddion Source | Description |
|---|---------|---------------|-------------|
| 92 | Columnar | col_synth.c | Columnar/stripe growth patterns. |
| 93 | Objects | obj_synth.c | Random spheres, pyramids, boxes, cylinders on flat surface. |
| 94 | Fibres | fibre_synth.c | Randomly oriented fibre/line features. |
| 95 | Waves | wave_synth.c | Directional wave/ripple patterns. |
| 96 | Dunes | dune_synth.c | Dune-like rippled surfaces. |
| 97 | Domains | domain_synth.c | Phase-separated domain/island patterns. |
| 98 | Ballistic Deposition | bdep_synth.c | Ballistic deposition growth simulation. |
| 99 | Particle Deposition | deposit_synth.c | Particle deposition simulation. |
| 100 | Rod Deposition | roddeposit_synth.c | Wire/rod deposition on surfaces. |
| 101 | Diffusion Aggregation | diff_synth.c | Diffusion-limited aggregation patterns. |
| 102 | Discs | disc_synth.c | Randomly distributed disc features. |
| 103 | Plateaus | plateau_synth.c | Flat-topped feature patterns. |
| 104 | Pileups | pileup_synth.c | Rounded rectangle pileup structures. |
| 105 | Annealing | anneal_synth.c | Simulated annealing surface relaxation. |
| 106 | Lattice (Voronoi) | lat_synth.c | Regular lattice with Voronoi-based variations. |
| 107 | Phase Separation | phase_synth.c | Spinodal decomposition domain patterns. |
| 108 | PDE Patterns | cpde_synth.c | Coupled partial differential equation patterns. |
| 109 | Spectral (FFT) | fft_synth.c | Surfaces with customizable power spectrum. |
| 110 | Residues | residue_synth.c | Irregular particle/residue deposits. |
| 111 | Noise Distributions | lno_synth.c, noise_synth.c | Gaussian, Poisson, exponential, and other noise types. |
| 112 | Periodic Patterns | pat_synth.c | Various periodic/modulated tiling patterns. |
| 113 | WFR Patterns | wfr_synth.c | Wave-front-related surface patterns. |

### File Format Support

Gwyddion supports 155+ file format modules. tono currently handles a smaller set. Major format gaps (not exhaustive):

| Format | Gwyddion Source | Vendor/Description |
|--------|---------------|-------------------|
| Bruker Nanoscope | nanoscope.c, nanoscope-ii.c | Bruker/Veeco/DI SPM files |
| Park Systems | parkafm.c | Park Systems SPM files |
| RHK | rhk-sm4.c, rhk-spm32.c | RHK Technology SPM files |
| Omicron | omicron.c, omicronflat.c | Omicron/Scienta SPM files |
| Asylum Research | asylum.c | Asylum Research (Igor Pro) |
| WITec | witec-asc.c | WITec SPM/Raman files |
| JEOL | jeol.c | JEOL SPM files |
| ISO 28600 | iso28600.c | Standard SPM exchange format |
| Zygo | zygo.c | Zygo surface profiler |
| ASCII matrix | asciiexport.c | Generic ASCII grid import/export |

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| Originally tracked (1–40) | 40 | 39 done, 1 excluded (force curves) |
| High Value (41–51) | 11 | **All 11 done** |
| Medium Value (52–70) | 19 | **All 19 done** |
| SPM Mode-Specific (71–76) | 6 | Pending |
| Lower Priority (77–91) | 15 | Pending |
| Synthesis Patterns (92–113) | 22 | Pending (extend SyntheticSurface) |
| File Formats | 10+ | Pending |

**69 of 70 tracked features implemented.** 43 remaining gaps identified.
