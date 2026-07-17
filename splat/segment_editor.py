
"""
Edit volume segmentation labels.
"""

import numpy as np
import H5Gizmos as gz
from . import layer

class SegmentEditor:
    
    def __init__(self, labels, intensities, width=500):
        self.labels = labels
        self.intensities = intensities
        self.focus = np.array(labels.shape) // 2
        shape = np.array(labels.shape)
        [I, J, K] = labels.shape
        zoom = max(1.0, width / shape.max())
        print ("SegmentEditor.__init__", labels.shape, intensities.shape, zoom)
        self.zoom = zoom
        [fI, fJ, fK] = self.focus
        self.layer_slider = gz.Slider(
            minimum=0, maximum=I-1, value=fI, step=1, orientation="vertical",
            on_change=self.slide_layer)
        self.layer_slider.css({"height": f"{width}px"})
        self.layer = layer.Layer(
            labels[fI, :, :], 
            intensities[fI, :, :],
            editor=self,
            width=int(zoom * K), 
            height=int(zoom * J), 
            max_label=labels.max())
        self.view1 = layer.LayerView(
            labels[:, fJ, :],
            intensities[:, fJ, :],
            width=int(zoom * K),
            height=int(zoom * I),
            editor=self,
            index=1,
        )
        self.view2 = layer.LayerView(
            labels[:, :, fK],
            intensities[:, :, fK],
            width=int(zoom * J),
            height=int(zoom * I),
            editor=self,
            index=2,
        )
        self.info = gz.Text("Click on a view to change the focus slice. Use the layer view to edit labels.")
        self.dash = gz.Shelf([
            self.layer_slider,
            self.layer.dash,
            [
                self.info,
                self.view1.dash,
                self.view2.dash,
            ]
        ])

    def warning(self, text):
        self.info.text(text)
        self.info.css({"background-color": "yellow", "color": "red", "font-weight": "bold"})

    def message(self, text):
        self.info.text(text)
        self.info.css({"background-color": "white", "color": "black", "font-weight": "normal"})

    def slide_layer(self, *ignored):
        layerI = int(self.layer_slider.value)
        [fI, fJ, fK] = self.focus
        if self.layer.modified() and layerI != fI:
            self.warning("Commit or revert changes before leaving the current layer.")
            self.layer_slider.set_value(fI)
            return
        self.change_layer(layerI, fJ, 1)
        self.message(f"Slide layer from {fI} to {layerI}.")

    def change_layer(self, A, B, index):
        if index > 0:
            if self.layer.modified():
                self.warning("Commit or revert changes before leaving the current layer.")
                return
        focus = self.focus.copy()
        if index == 0:
            focus[1] = A
            focus[2] = B
        elif index == 1:
            focus[0] = A
            focus[2] = B
        elif index == 2:
            focus[0] = A
            focus[1] = B
        self.set_focus(focus)

    def set_focus(self, focus):
        [fI0, fJ0, fK0] = self.focus # old focus
        self.focus = np.array(focus)
        [fI, fJ, fK] = self.focus
        self.message(f"Focus set to {self.focus} from [{fI0}, {fJ0}, {fK0}].")
        # only update the views that have changed
        if fI != fI0:
            self.layer.update_image(
                labels=self.labels[fI, :, :],
                intensities=self.intensities[fI, :, :],
            )
        if fJ != fJ0:
            self.view1.update_image(
                labels=self.labels[:, fJ, :],
                intensities=self.intensities[:, fJ, :],
            )
        if fK != fK0:
            self.view2.update_image(
                labels=self.labels[:, :, fK],
                intensities=self.intensities[:, :, fK],
            )

    def commit_labels_layer(self, labels, index=0):
        [fI, fJ, fK] = self.focus
        if index == 0:
            self.labels[fI, :, :] = labels
        elif index == 1:
            self.labels[:, fJ, :] = labels
        elif index == 2:
            self.labels[:, :, fK] = labels
        self.message(f"Committed changes to layer {index} at focus {self.focus}.")

    def label_colors(self):
        return self.layer.label_colors
    
    def mix_level(self):
        return self.layer.img_mix
    