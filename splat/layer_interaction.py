"""
Interaction mode for layers -- determines interpretation of mouse events and how layers respond to them.
"""

class NullInteraction:
    """
    Interaction mode for doing nothing.
    """

    def __init__(self, layer):
        self.layer = layer

    def on_pointerdown(self, event):
        pass

    def on_pointerup(self, event):
        pass

    def on_pointermove(self, event):
        pass

    def location(self, event):
        # return the pixel location of the event
        return (event["pixel_row"], event["pixel_column"])

class PickInteraction(NullInteraction):
    """
    Interaction mode for picking labels in a layer.
    """

    tracking = False

    def __init__(self, layer):
        self.layer = layer

    def on_pointerdown(self, event):
        self.tracking = True
        return self.on_pointermove(event)

    def on_pointerup(self, event):
        self.tracking = False
        pass # ignore pointer up events in pick mode

    def on_pointermove(self, event):
        if not self.tracking:
            return
        ij = self.location(event)
        label = self.layer.current_labels[ij]
        return self.on_click(event)

    def on_click(self, event):
        # pick the label at the clicked pixel
        ij = self.location(event)
        self.layer.locate_at(ij)
        label = self.layer.current_labels[ij]
        self.layer.info.text(f"Picked label {label} at {ij}")
        #pr(f"Picked label {label} at {ij}")
        self.layer.select_label(label)
    
class ScribbleInteraction(NullInteraction):
    """
    Interaction mode for scribbling on a layer.
    """

    close_loop = False

    def __init__(self, layer):
        self.layer = layer
        self.drawing = False
        self.last_pixel = None
        self.draw_start = None
        #self.close_loop = False

    def on_click(self, event):
        # ignore click events in scribble mode
        pass

    def on_pointerdown(self, event):
        ij = self.location(event)
        self.layer.info.text(f"Mouse down at {ij}")
        #pr(f"Mouse down at {ij}")
        im = self.layer.image
        im.css({"cursor": "crosshair"})
        self.drawing = True
        self.draw_start = ij
        self.last_pixel = ij
        self.layer.set_pixel(ij)
        self.layer.update_image()

    def on_pointermove(self, event):
        ij = self.location(event)
        arrayvalue = self.layer.current_labels[ij]
        self.layer.info.text(f"Mouse move at {ij} : label {arrayvalue}")
        #pr(f"Mouse move at {ij}")
        if self.drawing:
            self.layer.set_pixel(ij)
            if self.last_pixel is not None:
                self.layer.connect_pixels(self.last_pixel, ij)
            self.last_pixel = ij
            self.layer.update_image()

    def on_pointerup(self, event):
        ij = self.location(event)
        self.layer.info.text(f"Mouse up at {ij}")
        #pr(f"Mouse up at {ij}")
        im = self.layer.image
        im.css({"cursor": "default"})
        if self.drawing:
            self.layer.set_pixel(ij)
            self.drawing = False
            self.last_pixel = None
            if self.close_loop and self.draw_start is not None:
                start = self.draw_start
                self.layer.connect_pixels(start, ij)
            start = self.draw_start
            #self.layer.connect_pixels(start, ij)
            self.draw_start = None
            self.layer.update_image()
            #self.layer.set_mode("pick") # switch back to pick mode after drawing

class LassoInteraction(ScribbleInteraction):
    """
    Interaction mode for lassoing on a layer.
    """
    close_loop = True

class FillInteraction(NullInteraction):
    """
    Interaction mode for filling a region in a layer.
    """
    def on_click(self, event):
        ij = self.location(event)
        label = self.layer.selected_label
        self.layer.info.text(f"Fill from {ij} with label {label}")
        #pr(f"Fill from {ij} with label {label}")
        self.layer.fill_from(ij, label)
        self.layer.set_mode("pick") # switch back to pick mode after filling

class ReplaceInteraction(NullInteraction):
    """
    Interaction mode for replacing a label in a layer.
    """
    def on_click(self, event):
        ij = self.location(event)
        old_label = self.layer.current_labels[ij]
        new_label = self.layer.selected_label
        self.layer.info.text(f"Replace label {old_label} with {new_label} at {ij}")
        #pr(f"Replace label {old_label} with {new_label} at {ij}")
        self.layer.replace_at(ij, to_value=new_label)
        self.layer.set_mode("pick") # switch back to pick mode after replacing
        