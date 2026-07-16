"""
Layer of a volume with interactive image and history.
Contains a label array and an intensity array, and allows the user 
to edit the label array with a lasso tool. 
The history of changes is stored in a list, and can be undone.
"""

import numpy as np
import H5Gizmos as gz
from array_gizmos import colorizers, color_list
from . import layer_interaction

class Layer:

    def __init__(self, labels, intensities, commit_callback=None, width=None, height=None, max_label=None):
        print("Layer.__init__")
        self.original_labels = labels
        self.current_labels = labels.copy()
        if max_label is None:
            self.max_label = int(labels.max())
        else:
            self.max_label = max_label
        self.interaction_modes = {
            "pick": layer_interaction.PickInteraction(self),
            "scribble": layer_interaction.ScribbleInteraction(self),
            "lasso": layer_interaction.LassoInteraction(self),
            "fill": layer_interaction.FillInteraction(self),
            "replace": layer_interaction.ReplaceInteraction(self),
        }
        self.interaction_dropdown = gz.DropDownSelect(
            list(self.interaction_modes.keys()),
            selected_value="pick",
            on_click=self.interaction_click,
        )
        self.img_mix = 0.5
        self.mix_slider = gz.Slider(0.0, 1.0, value=self.img_mix, step=0.01, on_change=self.set_mix)
        label_colors = color_list.get_colors(self.max_label)
        self.label_colors = np.array([(0,0,0)] + list(label_colors), dtype=int)
        self.intensities = intensities
        self.commit_callback = commit_callback
        self.undo_labels_history = []
        if height is None:
            if width is None:
                height, width = labels.shape
            else:
                height = int(labels.shape[0] * (width / labels.shape[1]))
        elif width is None:
            width = int(labels.shape[1] * (height / labels.shape[0]))
        self.mix_slider.css(width=width)
        self.image = gz.Image(array=self.intensities, width=width, height=height, scale=True)
        self.info = gz.Text("Layer info")
        self.selected_label = self.max_label
        self.label_input = gz.Input(initial_value=str(self.selected_label), change_callback=self.set_label)
        self.label_div = gz.Html("<div style='display:inline-block; width: 4em; height: 4em; background-color: red;'></div>")
        self.commit_button = gz.Button("Commit", on_click=self.commit)
        self.undo_button = gz.Button("Undo", on_click=self.undo)
        self.checkpoint_button = gz.Button("Checkpoint", on_click=self.checkpoint)
        self.revert_button = gz.Button("Revert", on_click=self.revert)
        self.dash = gz.Stack([
            self.info,
            self.mix_slider,
            self.image,
            [
                self.label_input, 
                self.label_div,
                self.interaction_dropdown,
                ],
            [
                self.checkpoint_button,
                self.undo_button,
                self.revert_button,
                self.commit_button,
            ]
            ])
        self.dash.call_when_started(self.init_image)
        print ("Layer.__init__ done")

    def checkpoint(self, *ignored):
        self.undo_labels_history.append(self.current_labels.copy())
        self.update_image()
        self.info.text(f"Checkpoint created. History length: {len(self.undo_labels_history)}")

    def undo(self, *ignored):
        if len(self.undo_labels_history) == 0:
            self.info.text("No history to undo.")
            return
        self.current_labels = self.undo_labels_history.pop()
        self.update_image()
        self.info.text(f"Undo performed. History length: {len(self.undo_labels_history)}")

    def revert(self, *ignored):
        labels = self.original_labels
        intensities = self.intensities
        self.change_arrays(labels, intensities)

    def commit(self, *ignored):
        labels = self.current_labels
        intensities = self.intensities
        if self.commit_callback is not None:
            self.commit_callback(self.current_labels)
        self.change_arrays(labels, intensities)
        self.info.text("Changes committed.")

    def interaction_click(self, *ignored):
        [mode] = self.interaction_dropdown.selected_values
        return self.set_mode(mode)
    
    def set_mode(self, mode="pick"):
        if mode not in self.interaction_modes:
            self.info.text(f"Unknown interaction mode {mode}")
            return
        self.info.text(f"Interaction mode changed to {mode}")
        mode_id = None
        for (identity, value) in self.interaction_dropdown.id2value.items():
            if value == mode:
                mode_id = identity
                break
        if mode_id is None:
            self.info.text(f"Could not find mode {mode} in dropdown")
            return
        self.interaction = self.interaction_modes[mode]
        # this should be a method in gz
        #log = self.interaction_dropdown.window.console.log
        sel = self.interaction_dropdown.select
        gz.do(sel.val(mode_id).selectmenu("refresh").trigger("change"))
        #gz.do(log("selected value:", sel.val()))
        #gz.do(log("selected text:", sel.find("option:selected").text()))
        print("id 2 value", self.interaction_dropdown.id2value)

    def change_arrays(self, labels, intensities):
        self.original_labels = labels
        self.current_labels = labels.copy()
        self.intensities = intensities
        self.undo_labels_history = []
        self.update_image()

    def set_pixel(self, ij):
        self.current_labels[ij] = self.selected_label

    def connect_pixels(self, ij1, ij2):
        # draw a line between two pixels and set the label along the line
        x1, y1 = ij1[1], ij1[0]
        x2, y2 = ij2[1], ij2[0]
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            self.set_pixel(ij1)
            return
        for i in range(steps + 1):
            t = i / steps
            x = int(round(x1 + t * dx))
            y = int(round(y1 + t * dy))
            self.set_pixel((y, x))

    def init_image(self):
        print("Layer.init_image")
        #return
        im = self.image
        im.css({"image-rendering": "pixelated"})
        gz.do(im.element.attr("draggable", False))
        self.update_image()
        im.on_pixel(self.down_callback, type="pointerdown")
        im.on_pixel(self.up_callback, type="pointerup")
        im.on_pixel(self.move_callback, type="pointermove")
        im.on_pixel(self.leave_callback, type="pointerleave")
        im.on_pixel(self.click_callback, type="click")
        self.select_label(self.selected_label)
        self.interaction = layer_interaction.PickInteraction(self)
        print("Layer.init_image done")

    def set_mix(self, *ignored):
        self.img_mix = self.mix_slider.value
        self.update_image()

    def update_image(self, *ignored):
        carray = self.color_mix_array()
        self.image.change_array(carray, scale=False)
        if len(self.undo_labels_history) > 0:
            self.undo_button.set_enabled(True)
            #self.commit_button.set_enabled(True)
            #self.revert_button.set_enabled(True)
        else:
            self.undo_button.set_enabled(False)
            #self.commit_button.set_enabled(False)
            #self.revert_button.set_enabled(False)

    def color_mix_array(self):
        mix = self.img_mix
        mix1 = 1.0 - mix
        carray = colorizers.colorize_array(self.current_labels, self.label_colors).astype(float)
        iarray = self.intensities.astype(float)
        M = iarray.max()
        m = iarray.min()
        if M == m:
            iarray255 = np.zeros_like(iarray)
        else:
            iarray255 = (iarray - m) * (255.0 / (M - m))
        ciarray255 = iarray255.reshape(iarray255.shape + (1,))
        cmix = mix * carray + mix1 * ciarray255
        return np.clip(cmix, 0.0, 255.0).astype(int)

    def set_label(self, ignored):
        value = self.label_input.value
        try:
            label = int(value)
            if label < 0 or label > self.max_label:
                self.info.text(f"Label must be between 0 and {self.max_label} not {label}")
                return
            self.select_label(label)
        except ValueError as e:
            self.info.text(f"Invalid label: {e}.  Should be an integer between 0 and {self.max_label}.")
            print(f"Invalid label: {value} : {e}")

    def select_label(self, label):
        self.selected_label = label
        self.label_input.set_value(str(label))
        color = color_list.rgbhtml(self.label_colors[label])
        self.label_div.css({"background-color": color})
        self.info.text(f"Selected label {label}")

    def leave_callback(self, event):
        self.info.text("Mouse left the image.")
        return self.up_callback(event)
    
    def down_callback(self, event):
        self.info.text(f"Mouse down at {event['pixel_row']}, {event['pixel_column']}")
        return self.interaction.on_pointerdown(event)
    
    def up_callback(self, event):
        self.info.text(f"Mouse up at {event['pixel_row']}, {event['pixel_column']}")
        return self.interaction.on_pointerup(event)
    
    def move_callback(self, event):
        self.info.text(f"Mouse move at {event['pixel_row']}, {event['pixel_column']}")
        return self.interaction.on_pointermove(event)
    
    def click_callback(self, event):
        self.info.text(f"Mouse click at {event['pixel_row']}, {event['pixel_column']}")
        return self.interaction.on_click(event)
    
    def fill_from(self, start_point=None, to_target=255):
        self.current_labels = fill_from_point(self.current_labels, start_point=start_point, to_target=to_target)
        self.update_image()

    def replace_at(self, start_point=None, to_value=255):
        self.current_labels = replace_from_point(self.current_labels, start_point=start_point, to_value=to_value)
        self.update_image()


def fill_from_point(array, start_point=None, to_target=255):
    if start_point is None:
        start_point = (array.shape[0] // 2, array.shape[1] // 2)
    filled = np.copy(array)
    to_fill = [start_point]
    while to_fill:
        point = to_fill.pop()
        i, j = point
        if filled[i, j] != to_target:
            filled[i, j] = to_target
            neighbors = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]
            for ni, nj in neighbors:
                if 0 <= ni < filled.shape[0] and 0 <= nj < filled.shape[1]:
                    to_fill.append((ni, nj))
    return filled


def replace_from_point(array, start_point=None, to_value=255):
    if start_point is None:
        start_point = (array.shape[0] // 2, array.shape[1] // 2)
    from_value = array[start_point]
    replaced = np.copy(array)
    to_replace = [start_point]
    while to_replace:
        point = to_replace.pop()
        i, j = point
        if replaced[i, j] == from_value:
            replaced[i, j] = to_value
            neighbors = [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]
            for ni, nj in neighbors:
                if 0 <= ni < replaced.shape[0] and 0 <= nj < replaced.shape[1]:
                    to_replace.append((ni, nj))
    return replaced
