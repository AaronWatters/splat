
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
        #self.corner_index = np.array([0, 0, 0], dtype=int)
        if labels is None:
            labels = np.zeros_like(intensities, dtype=np.int32)
            maxlabel = MIN_LABELS
        else:
            maxlabel = max(labels.max(), MIN_LABELS)
        self.maxlabel = maxlabel
        self.labels = labels
        shape = self.shape = np.array(labels.shape)
        self.corner_index = np.clip((shape - self.voxels_per_width) // 2, 0, self.shape)
        #pr("corner_index", self.corner_index, "voxels_per_width", self.voxels_per_width, "shape", shape)
        #self.scaled_shape = (self.shape * self.scaling).astype(int)
        self.intensities = intensities
        (self.sliced_labels, self.sliced_intensities) = self.sliced_arrays()
        self.focus = shape // 2
        [I, J, K] = labels.shape
        [cI, cJ, cK] = self.corner_index
        [dI, dJ, dK] = self.voxels_per_width
        #zoom = max(1.0, width / shape.max())
        #pr ("SegmentEditor.__init__", labels.shape, intensities.shape)
        [fI, fJ, fK] = self.focus
        [sI, sJ, sK] = shape * self.scaling
        self.layer_slider = gz.Slider(
            minimum=cI, 
            maximum=min(cI + dI - 1, I - 1),
            value=fI, 
            step=1, 
            orientation="vertical",
            on_change=self.slide_layer)
        self.layer_slider.css({"height": f"{width}px"})
        self.layer = layer.Layer(
            self.get_labels(0), #labels[fI, :, :],
            self.get_intensities(0), #intensities[fI, :, :],
            editor=self,
            width=min(sJ, width),
            height=min(sK, width),
            max_label=self.maxlabel)
        self.zoom = layer.ZoomView(
            self.get_zoomed_labels(0), #labels[fI, :, :],
            self.get_zoomed_intensities(0), #intensities[fI, :, :],
            editor=self,
            width=min(sJ, width),
            height=min(sK, width),
            index=0,
        )
        self.view1 = layer.LayerView(
            self.get_labels(1), #labels[:, fJ, :],
            self.get_intensities(1), #intensities[:, fJ, :],
            width=min(sJ, width),
            height=min(sK, width),
            editor=self,
            index=1,
        )
        self.view2 = layer.LayerView(
            self.get_labels(2), #labels[:, :, fK],
            self.get_intensities(2), #intensities[:, :, fK],
            width=min(sJ, width),
            height=min(sK, width),
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
        unclipped_corner_index = np.array(corner_index, dtype=int)
        clipped_corner_index = np.clip(unclipped_corner_index, 0, np.maximum(0, self.shape - self.voxels_per_width))
        self.corner_index = clipped_corner_index
        (self.sliced_labels, self.sliced_intensities) = self.sliced_arrays()
        focus = self.focus
        # make sure focus is within the new corner_index and voxels_per_width
        focus = np.clip(focus, self.corner_index, self.corner_index + self.voxels_per_width)
        self.set_focus(focus)

    def set_corner_index_from_pixel(self, pixel_indices, position):
        """
        set corner_index so that pixel_indices is in the view of position
        """
        #pr("set_corner_index", pixel_indices, position, self.zoom_factor)
        unzoomed_pixel_indices = (np.array(pixel_indices) / self.zoom_factor).astype(int)
        #pr(" ... unzoomed_pixel_indices", unzoomed_pixel_indices)
        [A, B] = self.view_indices(position)
        [Ai, Bi] = unzoomed_pixel_indices
        Aextent = self.voxels_per_width[A]
        Bextent = self.voxels_per_width[B]
        Ai = np.clip(Ai - Aextent // 2, 0, self.shape[A] - Aextent)
        Bi = np.clip(Bi - Bextent // 2, 0, self.shape[B] - Bextent)
        corner_index = self.corner_index.copy()
        #pr(" ... corner_index before", corner_index)
        corner_index[A] = Ai# + self.voxels_per_width[A] // 2
        corner_index[B] = Bi# + self.voxels_per_width[B] // 2
        #pr(" ... corner_index after 1", corner_index)
        corner_index = np.clip(corner_index, 0, np.array(self.labels.shape) - self.voxels_per_width)
        #pr(" ... corner_index after 2", corner_index)
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
        #print(f"zoom_array: position {position}, from_array shape {from_array.shape}, width {width}")
        layer = self.get_layer(from_array, position, shift=False)
        [A, B] = self.view_indices(position)
        shape = np.array(layer.shape) * self.scaling[[A, B]]
        zoomfactor = width / shape.max()
        self.zoom_factor = zoomfactor
        #print(".  zoomfactor", zoomfactor, "layer shape", layer.shape, "width", width)
        zoomed = zoom(layer, zoomfactor, order=0)
        #print(".  zoomed shape", zoomed.shape)
        return zoomed

    def zoomed_focus(self, position, focus3d=None):
        [A, B] = self.view_indices(position)
        unzoomed_focus = self.focus2d(position, focus3d=focus3d)
        #shifted_focus = unzoomed_focus + self.corner_index[[A, B]]
        zoomed_focus = (unzoomed_focus * self.zoom_factor).astype(int)
        #print(f"zoomed_focus: position {position}, AB {A}, {B}, unzoomed_focus {unzoomed_focus},\n"
        #      f" corner_index {self.corner_index[[A, B]]}, zoom_factor {self.zoom_factor}, zoomed_focus {zoomed_focus}")
        return zoomed_focus

    def zoomed_corner_index(self, position):
        return self.zoomed_focus(position, focus3d=self.corner_index)

    def zoomed_voxels_per_width(self, position):
        return self.zoomed_focus(position, focus3d=self.voxels_per_width)

    def focus2d(self, position, focus3d=None):
        if focus3d is not None:
            focus = focus3d
        else:
            focus = self.focus
        [A, B] = self.view_indices(position)
        result = np.array([focus[A], focus[B]], dtype=int)
        #pr(f"focus2d: position {position}, AB {A}, {B}, input focus {focus}, output focus {result}")
        return result

    def shifted_focus3d(self, position):
        focus = self.focus
        corner_index = self.corner_index
        # DEBUG: Error if focus is not strictly larger than corner_index
        if np.any(focus < corner_index):
            raise ValueError(f"Focus {focus} is less than corner_index {corner_index}. Focus must be greater than or equal to corner_index.")
        shifted_focus = focus - corner_index
        clipped_shifted_focus = np.clip(shifted_focus, 0, self.voxels_per_width - 1)
        #pr(f"shifted_focus3d: position {position}, input focus {focus}, corner_index {self.corner_index}, output shifted_focus {clipped_shifted_focus}")
        ##pr(f"shifted_focus3d: position {position}, input focus {focus}, corner_index {self.corner_index}, output shifted_focus {shifted_focus}")
        return clipped_shifted_focus

    def shifted_focus2d(self, position):
        shifted_focus3d = self.shifted_focus3d(position)
        result = self.focus2d(position, focus3d=shifted_focus3d)
        #pr(f"shifted_focus2d: position {position}, output shifted_focus2d {result}")
        return result

    def pos(self, base_position):
        return (base_position + self.layer_offset) % 3

    def set_layer_offset(self, offset):
        # don't set layer offset if there are unsaved changes in the current layer
        if self.layer.modified():
            self.warning("Commit or revert changes before changing the layer offset.")
            return
        pos = self.pos(offset)
        self.layer_offset = pos
        self.set_focus(self.focus) # update the views with the new offset

    def get_layer(self, from_array, position, shift=True):
        focus = self.focus
        #print(f"get_layer: position {position}, input shape {from_array.shape},")
        # DEBUG: ERROR IF MIN LAYER SHAPE LESS THAN 10
        #if np.min(from_array.shape) < 10:
        #    raise ValueError(f"Layer shape {from_array.shape} is too small. Minimum dimension must be at least 10.")
        shifted_focus = focus
        if shift:
            shifted_focus = np.clip(focus - self.corner_index, 0, self.voxels_per_width - 1)
        #pr(f"focus {focus}, corner_index {self.corner_index}, shifted_focus {shifted_focus}")
        indexer = self.layer_index(self.pos(position), shifted_focus)
        #pr(f"indexer {indexer}, from_array shape {from_array.shape}")
        result = from_array[indexer]
        ##pr(f"get_layer: position {position}, input shape {from_array.shape},"
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
        ##pr (f"slide_layer: layerI {layerI}, focus {focus}, pos0 {pos0}")
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
        [Ai, Bi] = self.view_indices(base_index)
        #sorted([self.pos(base_index + 1), self.pos(base_index + 2)])
        corner_index = self.corner_index
        focus[Ai] = A + corner_index[Ai]
        focus[Bi] = B + corner_index[Bi]
        # error if focus not within corner_index and corner_index + voxels_per_width
        if np.any(focus < corner_index) or np.any(focus >= corner_index + self.voxels_per_width):
            raise ValueError(f"Focus {focus} is outside the bounds of corner_index {corner_index} and corner_index + voxels_per_width {corner_index + self.voxels_per_width}.")
        self.set_focus(focus)

    def set_focus(self, focus): # remove this method after testing
        old_focus = self.focus # old focus
        self.focus = np.array(focus)
        #[fI, fJ, fK] = self.focus
        modified = self.layer.modified()
        print(f"set_focus: old_focus {old_focus}, new focus {self.focus}, modified {modified}")
        self.message(f"Focus set to {self.focus} from {old_focus}.")
        for (position, layer) in [(0, self.layer), (1, self.view1), (2, self.view2)]:
            pos = self.pos(position)
            new_value = self.focus[pos]
            old_value = old_focus[pos]
            focus2d = self.shifted_focus2d(position)
            if (not modified)or new_value != old_value or position != 0:
                indexer = self.layer_index(pos, self.focus)
                layer.update_image(
                    labels=self.get_labels(position),
                    intensities=self.get_intensities(position),
                    focus=focus2d,
                )
                if position == 0:
                    labels = self.get_zoomed_labels(0)
                    intensities = self.get_zoomed_intensities(0)
                    corner_index = self.zoomed_corner_index(0)
                    voxels_per_width = self.zoomed_voxels_per_width(0)
                    self.zoom.update_image(
                        labels=self.get_zoomed_labels(0),
                        intensities=self.get_zoomed_intensities(0),
                        corner=corner_index,
                        extent=voxels_per_width,
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
    