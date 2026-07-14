
from splat import layer
import H5Gizmos as gz
import numpy as np

intensities = np.load("i24.npz")["arr"]
print("loaded intensities volume", intensities.shape, intensities.min(), intensities.max(), intensities.dtype)
labels = np.load("l24.npz")["arr"]
print("loaded labels volume", labels.shape, labels.min(), labels.max(), labels.dtype)

middle = labels.shape[0] // 2

layer = layer.Layer(labels[middle], intensities[middle], width=500)

if __name__ == "__main__":
    #gz.serve(gz.Text("hello world").link())
    gz.serve(layer.dash.link())
