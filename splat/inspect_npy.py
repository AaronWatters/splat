from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def inspect(path: str | Path) -> None:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".npy":
        array = np.load(file_path, allow_pickle=False)
        print(f"{file_path.name}: shape={array.shape}, dtype={array.dtype}")
        return

    if suffix == ".npz":
        with np.load(file_path, allow_pickle=False) as arrays:
            for key in arrays.files:
                array = arrays[key]
                print(f"{key}: shape={array.shape}, dtype={array.dtype}")
        return

    raise ValueError("path must point to a .npy or .npz file")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args(argv)
    inspect(args.path)
