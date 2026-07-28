
"""
Edit volume segmentation labels.
"""

import numpy as np
import H5Gizmos as gz
from numpy.strings import index
from . import layer

class SegmentEditor:
    
    def __init__(self, labels, intensities, width=500):
        self.layer_offset = 0
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
            self.get_labels(0), #labels[fI, :, :],
            self.get_intensities(0), #intensities[fI, :, :],
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

    def layer_index(self, position, focus_indices):
        position = position % 3
        indexer = [slice(None), slice(None), slice(None)]
        indexer[position] = focus_indices[position]
        return tuple(indexer)

    def focus2d(self, position):
        focus = self.focus
        [A, B] = sorted([self.pos(position + 1), self.pos(position + 2)])
        result = (focus[A], focus[B])
        #print(f"focus2d: position {position}, AB {A}, {B}, input focus {focus}, output focus {result}")
        return result

    def pos(self, base_position):
        return (base_position + self.layer_offset) % 3

    def set_layer_offset(self, offset):
        pos = self.pos(offset)
        self.layer_offset = pos
        self.set_focus(self.focus) # update the views with the new offset

    def get_layer(self, from_array, position):
        focus = self.focus
        indexer = self.layer_index(self.pos(position), focus)
        result = from_array[indexer]
        #print(f"get_layer: position {position}, input shape {from_array.shape},"
        #      f" offset {self.layer_offset}, focus {focus}, indexer {indexer},"
        #      f" result shape {result.shape}")
        return result

    def get_intensities(self, position):
        return self.get_layer(self.intensities, position)

    def get_labels(self, position):
        return self.get_layer(self.labels, position)

    def warning(self, text):
        self.info.text(text)
        self.info.css({"background-color": "yellow", "color": "red", "font-weight": "bold"})

    def message(self, text):
        self.info.text(text)
        self.info.css({"background-color": "white", "color": "black", "font-weight": "normal"})

    def slide_layer(self, *ignored):
        layerI = int(self.layer_slider.value)
        focus = self.focus.copy()
        pos0 = self.pos(0)
        #print (f"slide_layer: layerI {layerI}, focus {focus}, pos0 {pos0}")
        current_layer_index = focus[pos0]
        if self.layer.modified() and layerI != current_layer_index:
            self.warning("Commit or revert changes before leaving the current layer.")
            self.layer_slider.set_value(current_layer_index)
            return
        if layerI == current_layer_index:
            #self.message(f"Slide layer to {layerI} (no change).")
            return
        #self.message(f"Slide layer from {current_layer_index} to {layerI}.")
        focus[pos0] = layerI
        self.set_focus(focus)

    def change_layer(self, A, B, base_index):
        #index = self.pos(base_index)
        if base_index > 0:
            if self.layer.modified():
                self.warning("Commit or revert changes before leaving the current layer.")
                return
        focus = self.focus.copy()
        [Ai, Bi] = sorted([self.pos(base_index + 1), self.pos(base_index + 2)])
        focus[Ai] = A
        focus[Bi] = B
        self.set_focus(focus)

    def set_focus(self, focus): # remove this method after testing
        old_focus = self.focus # old focus
        self.focus = np.array(focus)
        #[fI, fJ, fK] = self.focus
        self.message(f"Focus set to {self.focus} from {old_focus}.")
        for (position, layer) in [(0, self.layer), (1, self.view1), (2, self.view2)]:
            pos = self.pos(position)
            new_value = self.focus[pos]
            old_value = old_focus[pos]
            focus2d = self.focus2d(position)
            if new_value != old_value or position != 0:
                indexer = self.layer_index(pos, self.focus)
                layer.update_image(
                    labels=self.labels[indexer],
                    intensities=self.intensities[indexer],
                    focus=focus2d,
                )
            else:
                layer.update_image(focus=focus2d)
        # set the slider value to position 0 of the new focus
        self.layer_slider.set_value(self.focus[self.pos(0)])

    def commit_labels_layer(self, labels, index=0):
        focus = self.focus
        indexer = self.layer_index(self.pos(index), focus)
        self.labels[indexer] = labels

    def label_colors(self):
        return self.layer.label_colors
    
    def mix_level(self):
        return self.layer.img_mix
    