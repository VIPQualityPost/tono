"""
Inspect DimScaling and DimExtents metadata in an Asylum Research HDF5 file.

Usage:
    python scripts/inspect_h5.py /path/to/your/file.h5
"""
import sys
import numpy as np

try:
    import h5py
except ImportError:
    print("pip install h5py")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python scripts/inspect_h5.py <file.h5>")
    sys.exit(1)

path = sys.argv[1]

with h5py.File(path, "r") as f:
    channels_path = "Image/DataSetInfo/Global/Channels"
    grp = f.get(channels_path)
    if grp is None:
        print("No Image/DataSetInfo/Global/Channels group found")
        sys.exit(1)

    for ch_name in grp:
        dims_path = f"{channels_path}/{ch_name}/ImageDims"
        dims_grp = f.get(dims_path)
        if dims_grp is None:
            print(f"{ch_name}: no ImageDims group")
            continue

        print(f"\n=== Channel: {ch_name} ===")

        scaling = dims_grp.attrs.get("DimScaling")
        if scaling is not None:
            s = np.asarray(scaling, dtype=float)
            print(f"  DimScaling shape:   {s.shape}")
            print(f"  DimScaling[0,:]:    {s[0]}  (row 0)")
            print(f"  DimScaling[1,:]:    {s[1]}  (row 1)")
            print(f"  --- If [start, end] interpretation ---")
            print(f"    xreal (row1 range) = {abs(s[1,1] - s[1,0])}")
            print(f"    yreal (row0 range) = {abs(s[0,1] - s[0,0])}")
            print(f"  --- If [step, offset] interpretation ---")
            print(f"    row0: step={s[0,0]}  offset={s[0,1]}")
            print(f"    row1: step={s[1,0]}  offset={s[1,1]}")
        else:
            print("  DimScaling: not found")

        dim_units = dims_grp.attrs.get("DimUnits")
        print(f"  DimUnits:           {dim_units}")

        data_units = dims_grp.attrs.get("DataUnits")
        print(f"  DataUnits:          {data_units}")

        for child_name in dims_grp:
            child = dims_grp[child_name]
            if isinstance(child, h5py.Group) and "DimExtents" in child.attrs:
                ext = np.asarray(child.attrs["DimExtents"])
                print(f"  DimExtents ('{child_name}'): {ext}")

    print("\n=== 2D dataset shapes ===")
    def _visit(name, obj):
        if isinstance(obj, h5py.Dataset) and obj.ndim == 2:
            print(f"  {name}  shape={obj.shape}")
    f.visititems(_visit)
