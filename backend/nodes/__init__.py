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
    poly_level_field,
    fix_zero,
    # Mask
    draw_mask,
    threshold_mask,
    mask_morphology,
    mask_invert,
    mask_combine,
    # Display
    color_map,
    font_node,
    annotations,
    markup,
    preview_image,
    view_3d,
    print_table,
    value_display,
    # Analysis
    statistics_node,
    histogram,
    cursors,
    fft_2d,
    inverse_fft_2d,
    cross_section,
    stats,
)

try:
    from backend.nodes import particle_analysis
except ImportError:
    pass
