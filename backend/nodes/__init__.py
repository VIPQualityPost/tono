# Import all node modules to trigger @register_node decorators.
from backend.nodes import (
    # IO
    image,
    image_demo,
    folder,
    coordinate,
    coordinate_pair,
    number,
    range_slider,
    save,
    save_image,
    # Filters
    gaussian_filter,
    median_filter,
    edge_detect,
    fft_filter_1d,
    fft_filter_2d,
    # Modify
    colormap_adjust,
    crop_resize_field,
    rotate_field,
    flip_field,
    # Level
    plane_level_field,
    facet_level_field,
    poly_level_field,
    fix_zero,
    line_correction,
    # Mask
    draw_mask,
    threshold_mask,
    mask_morphology,
    mask_invert,
    mask_combine,
    grain_distance_transform,
    # Correction
    scar_removal,
    # Display
    color_map,
    font_node,
    annotations,
    angle_measure,
    markup,
    preview_image,
    view_3d,
    print_table,
    value_display,
    # Analysis
    curvature,
    fractal_dimension,
    statistics_node,
    histogram,
    acf,
    cursors,
    fft_2d,
    psdf,
    inverse_fft_2d,
    cross_section,
    stats,
    watershed_segmentation,
)

try:
    from backend.nodes import particle_analysis
except ImportError:
    pass
