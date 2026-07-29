
"""
Edit volume segmentation labels.
"""

import numpy as np
import H5Gizmos as gz
from numpy.strings import index
from . import layer
from scipy.ndimage import zoom

MIN_LABELS = 10

class SegmentEditor:
    
    def __init__(self, intensities, labels=None, scaling=(1,1,1), width=500):
        self.zoom_factor = 1.0
        self.width = width
        self.layer_offset = 0
        self.scaling = np.array(scaling, dtype=float)
        self.voxels_per_width = (width / self.scaling).astype(int)
        self.corner_index = np.array([0, 0, 0], dtype=int)
        if labels is None:
            labels = np.zeros_like(intensities, dtype=np.int32)
            maxlabel = MIN_LABELS
        else:
            maxlabel = max(labels.max(), MIN_LABELS)
        self.maxlabel = maxlabel
        self.labels = labels
        self.intensities = intensities
        (self.sliced_labels, self.sliced_intensities) = self.sliced_arrays()
        self.focus = (np.array(labels.shape) / self.scaling / 2).astype(int)
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
            max_label=self.maxlabel)
        self.zoom = layer.ZoomView(
            self.get_zoomed_labels(0), #labels[fI, :, :],
            self.get_zoomed_intensities(0), #intensities[fI, :, :],
            editor=self,
            width=width,
            height=width,
            index=0,
        )
        self.view1 = layer.LayerView(
            self.get_labels(1), #labels[:, fJ, :],
            self.get_intensities(1), #intensities[:, fJ, :],
            width=int(zoom * K),
            height=int(zoom * I),
            editor=self,
            index=1,
        )
        self.view2 = layer.LayerView(
            self.get_labels(2), #labels[:, :, fK],
            self.get_intensities(2), #intensities[:, :, fK],
            width=int(zoom * J),
            height=int(zoom * I),
            editor=self,
            index=2,
        )
        self.info = gz.Text("Click on a view to change the focus slice. Use the layer view to edit labels.")
        self.dash = gz.Shelf([
            self.layer_slider,
            [
                self.layer.dash,
                self.zoom.dash,
            ],
            [
                self.info,
                self.view1.dash,
                self.view2.dash,            ]
        ])

    def set_corner_index(self, corner_index):
        self.corner_index = np.array(corner_index, dtype=int)
        (self.sliced_labels, self.sliced_intensities) = self.sliced_arrays()
        self.set_focus(self.focus)

    def set_corner_index_from_pixel(self, pixel_indices, position):
        """
        set corner_index so that pixel_indices is in the view of position
        """
        print("set_corner_index", pixel_indices, position, self.zoom_factor)
        unzoomed_pixel_indices = (np.array(pixel_indices) / self.zoom_factor).astype(int)
        print(" ... unzoomed_pixel_indices", unzoomed_pixel_indices)
        [A, B] = self.view_indices(position)
        [Ai, Bi] = unzoomed_pixel_indices
        corner_index = self.corner_index.copy()
        print(" ... corner_index before", corner_index)
        corner_index[A] = Ai# + self.voxels_per_width[A] // 2
        corner_index[B] = Bi# + self.voxels_per_width[B] // 2
        print(" ... corner_index after 1", corner_index)
        corner_index = np.clip(corner_index, 0, np.array(self.labels.shape) - self.voxels_per_width)
        print(" ... corner_index after 2", corner_index)
        self.set_corner_index(corner_index)

    def sliced_arrays(self):
        (I, J, K) = self.corner_index
        (dI, dJ, dK) = self.voxels_per_width
        self.sliced_labels = self.labels[I:I+dI, J:J+dJ, K:K+dK]
        self.sliced_intensities = self.intensities[I:I+dI, J:J+dJ, K:K+dK]
        return (self.sliced_labels, self.sliced_intensities)

    def layer_index(self, position, focus_indices):
        position = position % 3
        indexer = [slice(None), slice(None), slice(None)]
        indexer[position] = focus_indices[position]
        return tuple(indexer)

    def view_indices(self, position):
        [A, B] = sorted([self.pos(position + 1), self.pos(position + 2)])
        return (A, B)

    def zoom_array(self, position, from_array):
        """
        fit layer view from from_array so maximum dimension fits in self.width
        """
        width = self.width
        layer = self.get_layer(from_array, position)
        [A, B] = self.view_indices(position)
        shape = np.array(layer.shape) * self.scaling[[A, B]]
        zoomfactor = width / shape.max()
        self.zoom_factor = zoomfactor
        print("zoomfactor", zoomfactor, "layer shape", layer.shape, "width", width)
        zoomed = zoom(layer, zoomfactor, order=0)
        print("zoomed shape", zoomed.shape)
        return zoomed

    def zoomed_focus(self, position):
        focus = self.focus
        [A, B] = self.view_indices(position)
        unzoomed_focus = self.focus2d(position)
        shifted_focus = unzoomed_focus + self.corner_index[[A, B]]
        zoomed_focus = (shifted_focus * self.zoom_factor).astype(int)
        print(f"zoomed_focus: position {position}, AB {A}, {B}, unzoomed_focus {unzoomed_focus},"
              f" corner_index {self.corner_index[[A, B]]}, shifted_focus {shifted_focus}, zoom_factor {self.zoom_factor}, zoomed_focus {zoomed_focus}")
        return zoomed_focus

    def focus2d(self, position):
        focus = self.focus
        [A, B] = self.view_indices(position)
        result = np.array([focus[A], focus[B]], dtype=int)
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
        return self.get_layer(self.sliced_intensities, position)

    def get_labels(self, position):
        return self.get_layer(self.sliced_labels, position)

    def get_zoomed_intensities(self, position):
        return self.zoom_array(position, self.intensities)

    def get_zoomed_labels(self, position):
        return self.zoom_array(position, self.labels)

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
        modified = self.layer.modified()
        self.message(f"Focus set to {self.focus} from {old_focus}.")
        for (position, layer) in [(0, self.layer), (1, self.view1), (2, self.view2)]:
            pos = self.pos(position)
            new_value = self.focus[pos]
            old_value = old_focus[pos]
            focus2d = self.focus2d(position)
            if (not modified)or new_value != old_value or position != 0:
                indexer = self.layer_index(pos, self.focus)
                layer.update_image(
                    labels=self.get_labels(position),
                    intensities=self.get_intensities(position),
                    focus=focus2d,
                )
                if position == 0:
                    self.zoom.update_image(
                        labels=self.get_zoomed_labels(0),
                        intensities=self.get_zoomed_intensities(0),
                        focus=self.zoomed_focus(0),
                    )
            else:
                layer.update_image(focus=focus2d)
        # set the slider value to position 0 of the new focus
        self.layer_slider.set_value(self.focus[self.pos(0)])

    def commit_labels_layer0(self, labels, index=0):
        focus = self.focus
        indexer = self.layer_index(self.pos(index), focus)
        self.labels[indexer] = labels

    def commit_labels_layer(self, labels, index=0):
        labels_view = self.get_labels(index)
        labels_view[:] = labels

    def label_colors(self):
        return self.layer.label_colors
    
    def mix_level(self):
        return self.layer.img_mix
    