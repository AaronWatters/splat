"""Utilities for reading and writing volumes on disk."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from tifffile import imread, imwrite


SUPPORTED_EXTENSIONS = {".npy", ".npz", ".tif", ".tiff"}


def infer_format(path: str | Path) -> str:
	"""Infer the volume file format from the filename extension."""

	suffix = Path(path).suffix.lower()
	if suffix == ".tif" or suffix == ".tiff":
		return "tiff"
	if suffix == ".npy":
		return "npy"
	if suffix == ".npz":
		return "npz"
	raise ValueError(f"unsupported volume format for path: {path}")


def read_volume(path: str | Path) -> np.ndarray:
	"""Read a single 3D or 2D volume from disk."""

	file_path = Path(path)
	file_format = infer_format(file_path)

	if file_format == "npy":
		return np.load(file_path, allow_pickle=False)

	if file_format == "npz":
		with np.load(file_path, allow_pickle=False) as arrays:
			if not arrays.files:
				raise ValueError(f"no arrays found in archive: {file_path}")
			return arrays[arrays.files[0]]

	return imread(file_path)


def write_volume(path: str | Path, volume: np.ndarray) -> None:
	"""Write a single volume to disk, inferring the file format from the path."""

	file_path = Path(path)
	file_format = infer_format(file_path)
	array = np.asarray(volume)

	if file_format == "npy":
		np.save(file_path, array)
		return

	if file_format == "npz":
		np.savez(file_path, volume=array)
		return

	imwrite(file_path, array)

