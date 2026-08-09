from __future__ import annotations

"""
Blind tip estimation from morphological image analysis.

Reference: J. S. Villarrubia, J. Res. Natl. Inst. Stand. Technol. 102 (1997) 425.

─── High-level algorithm ────────────────────────────────────────────────────

In AFM the measured image is NOT the true surface — it is the dilation of the
true surface by the tip shape.  Blind estimation works backwards from the
measured image to recover an upper bound on the tip shape, without knowing
the true surface in advance.

The key insight (Villarrubia 1997): wherever the measured image has a sharp
local maximum, the tip apex must have been in contact with the surface at that
point.  The shape of the image near that peak therefore constrains the tip
geometry.  Iterating over all such peaks and taking the intersection of all
constraints converges to the sharpest tip consistent with the measured data.

─── Integer quantisation ───────────────────────────────────────────────

All internal arithmetic uses int32 to avoid floating-point drift in
comparisons.  The conversion is:

  step    = (surface_max - surface_min) / 10 000     (MORPH_LIB_N = 10 000)
  isurf[y,x] = floor( (surf[y,x] - surf_min) / step )   → values in [0, 10000]
  itip[y,x]  = floor( (tip[y,x]  - tip_max)  / step )   → values in [-10000, 0]

Tips are stored max-zeroed: the apex pixel is always 0, all other pixels ≤ 0.
This is the convention used throughout the estimation.

─── Tip initialisation ──────────────────────────────────────────────────────

We start with itip0 = all zeros.  In the max-zeroed convention this means
every pixel has the same height as the apex — i.e. the tip is perfectly flat
(infinitely wide).  The estimation can only decrease pixel values, so the
flat start is the most conservative (widest) possible initial assumption.
Every iteration narrows the tip to fit the image data more tightly.

─── Two estimation modes ────────────────────────────────────────────────────

partial  (_itip_estimate_partial):
  Collects local maxima in the image and iterates refinement over those
  peaks only.  Fast; works well for images with sharp, isolated features.

full     (_itip_estimate_full):
  Each iteration computes the morphological opening of the image (erosion
  then re-dilation with the current tip).  All pixels where the measured
  image exceeds the opening by more than the threshold are processed.
  Slower; more robust for images without distinct isolated peaks.

─── Certainty map ───────────────────────────────────────────────────────────

After estimation the certainty map identifies which surface pixels are
reliably reconstructed.  A surface pixel (sy, sx) is "certain" if exactly
ONE scanning position (i, j) in the image could have produced it — i.e. only
one tip placement was consistent with the measured height at that point.
Pixels with two or more possible tip placements are ambiguous and are left
unmarked (0).
"""

import numpy as np
from scipy.ndimage import grey_erosion, grey_dilation

from backend.node_registry import register_node
from backend.data_types import DataField

# Number of quantisation levels, defined as MORPH_LIB_N = 10000.
_MORPH_LIB_N = 10000.0

# Sentinel for "no contribution yet" in the dilation accumulator.
_INT_MIN = np.iinfo(np.int32).min


# ---------------------------------------------------------------------------
# Quantisation helpers
# ---------------------------------------------------------------------------

def _quantize_surface(data: np.ndarray, surf_min: float, step: float) -> np.ndarray:
    """
    Convert a float surface to an integer array in [0, MORPH_LIB_N].

    Uses the maxzero=FALSE, min=surf_min, step quantisation.
    """
    return np.floor((data - surf_min) / step).astype(np.int32)


def _quantize_tip(tip_data: np.ndarray, tip_max: float, step: float) -> np.ndarray:
    """
    Convert a float tip to a max-zeroed integer array (values ≤ 0).

    Uses the maxzero=TRUE, min=tip_min, step quantisation.
    With tip_min = 0 (our tips are always shifted so min = 0) this simplifies to:
      itip[y,x] = floor( (tip[y,x] - tip_max) / step )
    """
    return np.floor((tip_data - tip_max) / step).astype(np.int32)


def _dequantize(idata: np.ndarray, offset: float, step: float) -> np.ndarray:
    """Reverse of quantisation: float = idata * step + offset."""
    return idata.astype(np.float64) * step + offset


# ---------------------------------------------------------------------------
# _useit — is pixel (x, y) a local maximum suitable for tip refinement?
# ---------------------------------------------------------------------------

def _useit(image: np.ndarray, x: int, y: int, delta: int) -> bool:
    """
    Return True if (x, y) should be used as a refinement point.

    A pixel qualifies when:
      1. It is the maximum value within a (2·delta + 1)² neighborhood.
      2. Fewer than 1/5 of the neighborhood pixels share that maximum
         (to exclude flat plateaux, which give no tip shape information).

    delta = max(max(txres, tyres) // 10, 1) so larger tips use a wider
    neighborhood.
    """
    yres, xres = image.shape
    xmin, xmax = max(x - delta, 0), min(x + delta, xres - 1)
    ymin, ymax = max(y - delta, 0), min(y + delta, yres - 1)
    region = image[ymin:ymax + 1, xmin:xmax + 1]
    max_val = int(region.max())
    if int(image[y, x]) < max_val:
        return False                                  # not the maximum
    count = int((region >= max_val).sum())
    return count <= (2 * delta + 1) ** 2 // 5        # not a flat plateau


# ---------------------------------------------------------------------------
# _estimate_point_interior — refine tip from a single interior image pixel
# ---------------------------------------------------------------------------

def _estimate_point_interior(
    ixp: int, jxp: int,
    image: np.ndarray,
    txres: int, tyres: int,
    xc: int, yc: int,
    tip0: np.ndarray,
    thresh: int,
) -> int:
    """
    Use the image pixel at (ixp, jxp) to narrow the tip estimate tip0.

    Returns the number of tip pixels that were updated (refined).

    ── Geometric meaning ──────────────────────────────────────────────────

    Imagine placing the tip so its apex (xc, yc) is directly above image
    pixel (ixp, jxp).  For each tip pixel (jd, id) offset from the apex:

      The tip "touches" the image at reference pixel (jxp+yc-jd, ixp+xc-id).
      For the tip to be inside the surface (physically valid), the image
      height at that reference pixel must be ≥ image_p - tip0[jd, id].

    Pixels that pass this check are called "good pixels" — they are the tip
    positions that are geometrically consistent with the apex sitting at
    (ixp, jxp).

    ── Computing the dilation at each tip pixel ───────────────────────────

    For each tip output pixel (jx, ix) we compute the maximum height that
    the tip could produce at any scanning position consistent with the good
    pixels.  This is:

      dil[jx, ix] = max over good (jd, id) of:
                      image[jxp + jx - jd, ixp + ix - id] + tip0[jd, id] - image_p

    Intuitively: if the tip pixel (jd, id) was in contact with the surface
    at the reference point, then the image at the laterally shifted position
    (jxp+jx-jd, ixp+ix-id) constrains how high tip pixel (jx, ix) can be.

    ── Updating the tip ───────────────────────────────────────────────────

    If dil[jx, ix] < tip0[jx, ix] - thresh, the new constraint is tighter
    than the current estimate, so we update:
      tip0[jx, ix] = dil[jx, ix] + thresh

    The +thresh prevents over-sharpening due to noise: we only accept a
    refinement if it exceeds the current estimate by more than the threshold.

    ── Vectorisation ──────────────────────────────────────────────────────

    For each good pixel (jd, id) we extract a (tyres x txres) window from
    the image, shifted so that image[jxp-jd, ixp-id] aligns with tip[0, 0].
    Taking the element-wise max across all good pixels yields dil efficiently
    without the O(tyres² x txres²) double loop of the original C code.
    """
    image_p = int(image[jxp, ixp])

    # Build image_at_ref[jd, id] = image[jxp+yc-jd, ixp+xc-id].
    # We want rows jxp+yc down to jxp+yc-tyres+1 (reversed), which numpy
    # gives as np.flip( image[jxp+yc-tyres+1 : jxp+yc+1, ...] ).
    image_at_ref = np.flip(
        image[jxp + yc - tyres + 1:jxp + yc + 1,
              ixp + xc - txres + 1:ixp + xc + 1],
        axis=(0, 1),
    )  # shape (tyres, txres); integer values

    # Good-pixel mask: image_p - image_at_ref[jd,id] <= tip0[jd,id]
    # Rearranged: image_at_ref[jd,id] >= image_p - tip0[jd,id]
    # Since tip0 ≤ 0, the right-hand side is ≥ image_p.
    # A good pixel is one where the reference height is high enough that
    # placing the tip apex at (ixp, jxp) is geometrically consistent.
    diff = image_p - image_at_ref   # positive where the reference is low
    good_mask = diff <= tip0        # True for geometrically valid placements
    good_jd, good_id = np.where(good_mask)

    if good_jd.size == 0:
        # No valid tip placement found at this image point; nothing to refine.
        return 0

    # Accumulate dil[jx, ix] = max over good (jd, id) of the window contribution.
    # Initialise to _INT_MIN so we can detect pixels with no contribution.
    dil = np.full((tyres, txres), _INT_MIN, dtype=np.int64)

    for k in range(good_jd.size):
        jd = int(good_jd[k])
        id_ = int(good_id[k])
        # For this good pixel (jd, id), the contribution to dil[jx, ix] is:
        #   image[jxp + jx - jd, ixp + ix - id] + tip0[jd, id] - image_p
        # Extracting the (tyres × txres) window starting at (jxp-jd, ixp-id)
        # gives all (jx, ix) contributions simultaneously.
        row0 = jxp - jd
        col0 = ixp - id_
        window = image[row0:row0 + tyres, col0:col0 + txres].astype(np.int64)
        contrib = window + int(tip0[jd, id_]) - image_p
        np.maximum(dil, contrib, out=dil)

    # Update tip0 where the new constraint is strictly tighter.
    # Only pixels with at least one good-pixel contribution are candidates.
    update = (dil > _INT_MIN) & (dil < tip0.astype(np.int64) - thresh)
    count = int(update.sum())
    if count:
        tip0[update] = (dil[update] + thresh).astype(np.int32)
    return count


# ---------------------------------------------------------------------------
# Partial estimation — iterate over local maxima only
# ---------------------------------------------------------------------------

def _itip_estimate_partial(
    image: np.ndarray,
    txres: int, tyres: int,
    xc: int, yc: int,
    tip0: np.ndarray,
    thresh: int,
    use_edges: bool,
) -> int:
    """
    Refine tip0 using the partial (local-maxima) method.

    Steps:
      1. Scan the image for pixels that are local maxima in a ±delta
         neighborhood and are not on a flat plateau (useit criterion).
         These are the image features most likely to have been produced by
         the tip apex — they constrain the tip shape most tightly.
      2. Iterate _estimate_point_interior over every qualifying pixel until
         either no pixel produces a refinement, or fewer than 20 pixels do
         (convergence criterion maxcount = 20).

    Returns the total number of tip-pixel updates across all iterations.
    """
    yres, xres = image.shape

    # delta: neighborhood radius for the local-maximum test.
    # Larger tips look over a wider window to avoid spurious maxima.
    delta = max(max(txres, tyres) // 10, 1)
    maxcount = 20  # convergence: stop when ≤ maxcount pixels updated per pass

    # Step 1: collect all valid local maxima in the interior.
    # Interior constraint: the full tip must fit inside the image at every
    # candidate point, so we stay ≥ (tip_half_size) from each edge.
    maxima_x, maxima_y = [], []
    for jxp in range(tyres - 1 - yc, yres - yc):
        for ixp in range(txres - 1 - xc, xres - xc):
            if _useit(image, ixp, jxp, delta):
                maxima_x.append(ixp)
                maxima_y.append(jxp)

    if not maxima_x:
        return 0  # no usable features found; tip stays flat

    # Step 2: iterate until convergence.
    sumcount = 0
    while True:
        count = 0
        for ixp, jxp in zip(maxima_x, maxima_y):
            # Restrict to strictly interior points (tip fits fully inside image).
            if (jxp >= tyres - 1 and jxp <= yres - tyres
                    and ixp >= txres - 1 and ixp <= xres - txres):
                count += _estimate_point_interior(
                    ixp, jxp, image, txres, tyres, xc, yc, tip0, thresh)
        sumcount += count
        if count == 0 or count <= maxcount:
            break   # converged

    return sumcount


# ---------------------------------------------------------------------------
# Full estimation — iterate over all points above the morphological opening
# ---------------------------------------------------------------------------

def _itip_estimate_full(
    image: np.ndarray,
    txres: int, tyres: int,
    xc: int, yc: int,
    tip0: np.ndarray,
    thresh: int,
    use_edges: bool,
) -> int:
    """
    Refine tip0 using the full estimation method.

    Each iteration:
      1. Computes the morphological opening of the image with the current tip
         estimate: opening = dilate(erode(image, tip0), tip0).
         The opening removes features narrower than the tip; any pixel where
         image > opening indicates that the tip apex was directly above a
         surface feature that is sharper than the current tip estimate.
      2. Calls _estimate_point_interior for every such pixel.
      3. Repeats until no pixel produces a refinement (count == 0).

    This is slower than the partial method but does not require isolated
    sharp peaks — it converges from any image with sufficient surface relief.
    """
    yres, xres = image.shape
    sumcount = 0

    while True:
        # Morphological opening with the current integer tip estimate.
        # scipy grey_erosion/dilation treat the structure as centered at
        # its middle pixel, with the apex at (yc, xc).
        tip_float = tip0.astype(np.float64)
        eroded = grey_erosion(image.astype(np.float64), structure=tip_float)
        opened = grey_dilation(eroded, structure=tip_float)
        opened_int = opened.astype(np.int64)

        count = 0
        for jxp in range(tyres - 1, yres - tyres + 1):
            for ixp in range(txres - 1, xres - txres + 1):
                # Only process pixels where the image exceeds its opening by
                # more than the noise threshold.  These are genuine sharp
                # features that cannot be explained by the current tip shape.
                if int(image[jxp, ixp]) - int(opened_int[jxp, ixp]) > thresh:
                    count += _estimate_point_interior(
                        ixp, jxp, image, txres, tyres, xc, yc, tip0, thresh)
        sumcount += count
        if count == 0:
            break   # no more refinements possible: converged

    return sumcount


# ---------------------------------------------------------------------------
# _certainty_map_fast — vectorised certainty map
# ---------------------------------------------------------------------------

def _certainty_map_fast(
    image: np.ndarray,
    tip: np.ndarray,
    rsurf: np.ndarray,
    xc: int, yc: int,
    cmap_thresh: float,
) -> np.ndarray:
    """
    Compute the certainty map for the reconstructed surface.

    A surface pixel (sy, sx) is marked certain (= 1) if there is exactly ONE
    scanning position (image pixel i, j) at which the tip was unambiguously
    in single-point contact with the surface at (sy, sx).

    ── Contact condition ────────────────────────────────────────────────────

    For tip pixel (ti, tj) and its reflected counterpart tip_flip[ti, tj]:

      image[i, j] - tip_flip[ti, tj] - rsurf[sy, sx] ≈ 0

    means that placing the tip so that tip pixel (ti, tj) touches the surface
    at (sy, sx) exactly accounts for the measured height at image pixel (i, j).
    The reflected tip is used because dilation/erosion use the tip flipped
    180°.  Coordinates:
      sy = ti + i - ryc,  sx = tj + j - rxc
    where ryc = tyres-1-yc and rxc = txres-1-xc are the reflected-apex
    offsets.

    ── Why "exactly one" contact? ───────────────────────────────────────────

    If two or more tip placements both satisfy the contact condition, the
    reconstruction is ambiguous — either placement could have produced the
    observed image value.  Only when a single tip placement is consistent is
    the surface height at (sy, sx) uniquely determined.

    ── Vectorisation strategy ───────────────────────────────────────────────

    Instead of looping over image pixels (O(yres × xres)) and for each one
    checking all tip pixels (O(tyres × txres)), we loop over tip pixels
    (typically much smaller than the image) and for each tip pixel accumulate
    a contact-count array over the surface.  This turns the O(N² × T²) scalar
    loop into an O(T² × N²/T²) = O(N²) numpy operation per tip pixel.
    """
    yres, xres = image.shape
    tyres, txres = tip.shape
    # Reflected-apex offsets: ryc = tyres-1-yc, rxc = txres-1-xc.
    # For a centerd tip (yc = tyres//2), ryc = tyres//2 as well.
    ryc = tyres - 1 - yc
    rxc = txres - 1 - xc

    # The certainty map algorithm uses the tip rotated 180° (reflected both
    # axes), because the erosion that produced rsurf used the flipped tip.
    tip_flip = np.flipud(np.fliplr(tip)).astype(np.float64)

    # count_arr[sy, sx] = number of tip placements that produce a contact at (sy, sx).
    count_arr = np.zeros((yres, xres), dtype=np.int32)

    for ti in range(tyres):
        for tj in range(txres):
            tf_val = tip_flip[ti, tj]

            # Determine which surface pixels (sy, sx) are reachable from valid
            # interior image pixels (i, j) when tip pixel (ti, tj) is in contact:
            #   sy = ti + i - ryc  →  sy in [ti, yres - tyres + ti]  (clipped to image)
            #   sx = tj + j - rxc  →  sx in [tj, xres - txres + tj]
            sy_lo = max(ti, 0)
            sy_hi = min(yres - tyres + ti, yres - 1)
            sx_lo = max(tj, 0)
            sx_hi = min(xres - txres + tj, xres - 1)
            if sy_lo > sy_hi or sx_lo > sx_hi:
                continue  # this tip pixel is entirely out of range

            sy_range = np.arange(sy_lo, sy_hi + 1)
            sx_range = np.arange(sx_lo, sx_hi + 1)

            # Corresponding image pixels for this tip placement:
            i_range = sy_range + ryc - ti
            j_range = sx_range + rxc - tj

            # Check the contact condition for every (sy, sx) / (i, j) pair:
            #   |image[i, j] - tip_flip[ti, tj] - rsurf[sy, sx]| <= cmap_thresh
            img_block = image[np.ix_(i_range, j_range)]
            rs_block  = rsurf[np.ix_(sy_range, sx_range)]
            contact = np.abs(img_block - tf_val - rs_block) <= cmap_thresh

            # Accumulate into the contact-count array.
            count_arr[np.ix_(sy_range, sx_range)] += contact.astype(np.int32)

    # Surface pixels with exactly one contact are certain; all others are not.
    return (count_arr == 1).astype(np.float64)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

@register_node(display_name="Blind Tip Estimate")
class BlindTipEstimate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_pixels": ("INT", {"default": 33, "min": 3, "max": 129, "step": 2}),
                "threshold": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1e-6, "step": 1e-10,
                }),
                "method": (["partial", "full"], {"default": "partial"}),
                "use_edges": ("BOOLEAN", {"default": False}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'tip'),
        ('IMAGE', 'certainty'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Blind tip estimation from a measured SPM image (Villarrubia algorithm). "
        "Iteratively refines the tip shape using only the sharpest image features. "
        "partial: uses local maxima only (faster, needs sharp isolated features). "
        "full: uses all points above morphological opening (slower, more robust). "
        "threshold: noise floor in metres — start at 0 and increase if tip is too sharp. "
        "Output tip has apex=max, edges=0 (same convention as TipModel). "
        "Certainty map marks surface pixels where the tip was in unambiguous single contact. "
    )

    KEYWORDS = ("villarrubia", "morphology", "cantilever", "apex", "dilation", "reconstruct")

    def process(
        self,
        field: DataField,
        n_pixels: int,
        threshold: float,
        method: str,
        use_edges: bool,
    ) -> tuple:
        # ── Tip grid setup ────────────────────────────────────────────────
        # Ensure odd size so the apex pixel is exactly centerd.
        n = n_pixels if n_pixels % 2 == 1 else n_pixels + 1
        txres = tyres = n
        xc = yc = n // 2   # apex is at the center pixel

        # ── Integer quantisation ──────────────────────────────────────────
        # All estimation arithmetic is performed in integer units.  step is
        # chosen so the full surface height range maps to MORPH_LIB_N = 10 000
        # integer levels.
        surf = field.data
        surf_min = float(surf.min())
        surf_max = float(surf.max())
        surf_range = surf_max - surf_min
        if surf_range == 0.0:
            surf_range = 1.0   # guard against featureless (flat) images

        step = surf_range / _MORPH_LIB_N
        isurf = _quantize_surface(surf, surf_min, step)  # int32 in [0, 10000]

        # ── Initial tip: flat (all zeros) ────────────────────────────────
        # In the max-zeroed convention, all zeros means every tip pixel is at
        # the same height as the apex — a perfectly flat (infinitely wide) tip.
        # This is the most conservative starting point; the algorithm can only
        # decrease tip values (narrow the tip), never increase them.
        itip0 = np.zeros((tyres, txres), dtype=np.int32)

        # ── Noise threshold in integer units ─────────────────────────────
        # A refinement is only accepted if the new constraint is more than
        # thresh_int quantisation levels below the current estimate.
        # The recommended start is 0; increase it if the result is
        # too sharp (noise is interpreted as sharp features).
        thresh_int = max(int(threshold / step), 0)

        # ── Run estimation ────────────────────────────────────────────────
        if method == "partial":
            _itip_estimate_partial(isurf, txres, tyres, xc, yc, itip0, thresh_int, use_edges)
        else:
            _itip_estimate_full(isurf, txres, tyres, xc, yc, itip0, thresh_int, use_edges)

        # ── Dequantise tip back to physical units ─────────────────────────
        #   tip_data[y,x] = itip0[y,x] * step  (offset = tipmin = 0 for flat start)
        # then shift so minimum = 0 (apex = maximum after shift).
        tip_data = itip0.astype(np.float64) * step
        tip_data -= tip_data.min()   # shift: minimum → 0, apex → maximum

        pixel_size = (field.dx + field.dy) * 0.5
        xreal = n * pixel_size

        tip_field = DataField(
            data=tip_data,
            xreal=xreal,
            yreal=xreal,
            si_unit_xy=field.si_unit_xy,
            si_unit_z=field.si_unit_z,
        )

        # ── Certainty map ─────────────────────────────────────────────────
        # Reconstruct the surface by eroding the measured image with the
        # estimated tip (this is the tip-erosion step used by Tip Deconvolution).
        # tip_max_zeroed converts back to the erosion convention (max = 0).
        tip_max_zeroed = tip_data - tip_data.max()   # values ≤ 0, apex = 0
        rsurf = grey_erosion(surf, structure=tip_max_zeroed)

        # cmap_thresh: tolerance for the "exact contact" comparison.
        # Uses 50 × step (the integer exact-contact branch uses equality,
        # which corresponds to ±0.5 step; 50 steps gives a looser float match).
        cmap_thresh = 50.0 * step
        cmap_data = _certainty_map_fast(surf, tip_data, rsurf, xc, yc, cmap_thresh)

        # Convert the binary 0/1 float map to a uint8 mask (0 = uncertain, 255 = certain).
        cmap_mask = (cmap_data * 255).astype(np.uint8)

        return (tip_field, cmap_mask)
