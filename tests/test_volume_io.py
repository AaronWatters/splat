import numpy as np
import pytest

from splat import volume_io


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("sample.npy", "npy"),
        ("sample.npz", "npz"),
        ("sample.tif", "tiff"),
        ("sample.tiff", "tiff"),
        ("sample.TIFF", "tiff"),
    ],
)
def test_infer_format(path, expected):
    assert volume_io.infer_format(path) == expected


def test_infer_format_rejects_unknown_extension():
    with pytest.raises(ValueError, match="unsupported volume format"):
        volume_io.infer_format("sample.png")


@pytest.mark.parametrize("suffix", [".npy", ".npz", ".tif", ".tiff"])
def test_read_write_volume_round_trip(tmp_path, suffix):
    path = tmp_path / f"volume{suffix}"
    array = np.arange(24, dtype=np.uint16).reshape(2, 3, 4)

    volume_io.write_volume(path, array)

    loaded = volume_io.read_volume(path)

    np.testing.assert_array_equal(loaded, array)


def test_read_volume_uses_first_array_from_npz(tmp_path):
    path = tmp_path / "bundle.npz"
    np.savez(path, second=np.zeros((1, 2)), first=np.arange(3, dtype=np.float32))

    loaded = volume_io.read_volume(path)

    np.testing.assert_array_equal(loaded, np.zeros((1, 2)))