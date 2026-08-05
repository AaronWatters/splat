"""
Wrapper for SegmentEditor adding file I/O.
"""

from . import segment_editor
from . import volume_io
import H5Gizmos as gz
import numpy as np

class SegmentEditorIO:

    def __init__(self,
                 intensities_file=None, 
                 labels_file=None,
                 scaling=(1,1,1),
                 width=500,
    ):
        self.intensities_file = intensities_file
        self.labels_file = labels_file
        self.scaling = scaling
        self.width = width

        self.intensities = None
        self.labels = None
        self.editor = None

        self.info_text = gz.Text("SegmentEditorIO initialized.")
        self.intensities_loader = VolumeIO("intensities", path=intensities_file, for_saving=False)
        self.labels_loader = VolumeIO("labels", path=labels_file, for_saving=False)
        self.labels_saver = VolumeIO("labels", path=labels_file, for_saving=True, get_volume=self.get_labels)
        self.edit_button = gz.Button("Edit", on_click=self.edit)
        self.gizmo = gz.Stack([
            self.info_text,
            self.intensities_loader.gizmo,
            self.labels_loader.gizmo,
            self.edit_button,
        ])

    def edit(self, *args):
        intensities = self.intensities_loader.volume
        labels = self.labels_loader.volume
        if intensities is None:
            self.info_text.text("Please load intensities to edit.")
            return
        if labels is not None:
            if intensities.shape != labels.shape:
                self.info_text.text(f"Intensities shape {intensities.shape} does not match labels shape {labels.shape}.")
                return
        self.editor = segment_editor.SegmentEditor(intensities, labels, width=self.width, scaling=self.scaling)
        self.info_text.text("SegmentEditor initialized.")
        self.gizmo.attach_children([
            self.info_text,
            self.intensities_loader.gizmo,
            self.labels_loader.gizmo,
            self.edit_button,
            self.editor.dash,
            self.labels_saver.gizmo,
        ])
        self.labels_saver.set_file_path(self.labels_loader.file_path())

    def get_labels(self):
        if self.editor is not None:
            return self.editor.get_labels_volume()
        else:
            raise ValueError("SegmentEditor not initialized. Please load intensities and click Edit first.")

class VolumeIO:

    def __init__(self, description, path=None, for_saving=False, get_volume=None):
        self.description = description
        self.path = path
        self.volume = None
        self.info_text = gz.Text(f"enter path for {description}")
        self.input = gz.Input(size=50, title=description, initial_value=path)
        self.for_saving = for_saving
        self.get_volume = get_volume
        if for_saving:
            self.button = gz.Button(f"Save", on_click=self.save_volume)
        else:
            self.button = gz.Button(f"Load", on_click=self.load_volume)
        self.gizmo = gz.Stack([
            self.info_text,
            [description, self.input, self.button],
        ])

    def file_path(self):
        return self.input.value

    def set_file_path(self, path):
        self.input.set_value(path)

    def load_volume(self, *args):
        path = self.input.value
        if not path:
            self.info_text.text(f"no path entered for {self.description}")
            return
        try:
            format = volume_io.infer_format(path)
        except ValueError as e:
            self.info_text.text(f"error: {e}")
            return
        try:
            self.info_text.text(f"loading {self.description} ({format})")
            self.volume = volume_io.read_volume(path)
            self.info_text.text(f"loaded {self.volume.shape}")
        except Exception as e:
            self.info_text.text(f"error loading: {e}")
            return

    def save_volume(self, *args):
        if self.get_volume is not None:
            self.volume = self.get_volume()
        path = self.input.value
        if not path:
            self.info_text.text(f"no path entered for {self.description}")
            return
        try:
            format = volume_io.infer_format(path)
        except ValueError as e:
            self.info_text.text(f"error: {e}")
            return
        try:
            self.info_text.text(f"saving {self.description} ({format} with dtype {self.volume.dtype})")
            volume_io.write_volume(path, self.volume)
            self.info_text.text(f"saved {self.description} to {path}")
        except Exception as e:
            self.info_text.text(f"error saving: {e}")
            return
