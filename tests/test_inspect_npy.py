import numpy as np

from splat import inspect_npy


def test_inspect_npy_lists_shape_and_dtype(tmp_path, capsys):
    path = tmp_path / "sample.npy"
    np.save(path, np.arange(6, dtype=np.int16).reshape(2, 3))

    inspect_npy.inspect(path)

    output = capsys.readouterr().out
    assert "sample.npy" in output
    assert "shape=(2, 3)" in output
    assert "dtype=int16" in output


def test_inspect_npz_lists_keys_shape_and_dtype(tmp_path, capsys):
    path = tmp_path / "bundle.npz"
    np.savez(path, first=np.arange(3, dtype=np.float32), second=np.zeros((1, 2)))

    inspect_npy.inspect(path)

    output = capsys.readouterr().out
    assert "first: shape=(3,), dtype=float32" in output
    assert "second: shape=(1, 2), dtype=float64" in output
