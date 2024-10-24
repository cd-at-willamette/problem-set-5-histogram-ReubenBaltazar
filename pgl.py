# File: pgl.py

"""
The pgl module implements the Portable Graphics Library (pgl) on top of
Tkinter, which is the most common graphics package for use with Python.
"""

import atexit
import importlib
import inspect
import io
import math
import ssl
import sys
import time
import urllib.request

# Version information

PGL_VERSION = 0.97
PGL_BUGFIX = 1
PGL_DATE = "14-Feb-23"

# Conditional imports

try:
    tkinter = importlib.import_module("tkinter")
    try:
        tk_font = importlib.import_module("tkinter.font")
    except Exception:
        tk_font = importlib.import_module("tk_font")
except Exception as e:
    print('Could not load tkinter: ' + str(e))

try:
    from PIL import ImageTk, Image
    _image_model = "PIL"
except Exception:
    _image_model = "PhotoImage"

spyder_flag = False

try:
    customize = importlib.import_module("spydercustomize")
    spyder_flag = True
except Exception:
    try:
        customize = importlib.import_module("sitecustomize")
        spyder_flag = True
    except Exception:
        pass

if spyder_flag:
    try:
        sys_clear_post_mortem = customize.clear_post_mortem
        def patched_clear_post_mortem():
            customize.clear_post_mortem = sys_clear_post_mortem
            try:
                if tkinter._root is not None:
                    tkinter._root.mainloop()
            except Exception:
                pass
            sys_clear_post_mortem()
        customize.clear_post_mortem = patched_clear_post_mortem
    except Exception:
        pass

# Class GWindow

class GWindow(object):
    """This class represents a window that can contain graphical objects."""

# Public constants

    DEFAULT_WIDTH = 500
    DEFAULT_HEIGHT = 300
    MIN_WAKEUP = 20

# Constructor: GWindow

    def __init__(self, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        """Creates a new GWindow with the specified size."""
        if not _is_number(width):
            raise TypeError("GWindow: width must be a number")
        if not _is_number(height):
            raise TypeError("GWindow: height must be a number")
        try:
            tk = tkinter._root
            tk.deiconify()
        except AttributeError:
            tk = tkinter.Tk()
            tkinter._root = tk
        self._window_width = width
        self._window_height = height
        self._tk = tk
        self._tk.protocol("WM_DELETE_WINDOW", self._delete_window)
        for w in tk.winfo_children():
            w.destroy()
        self._canvas = tkinter.Canvas(tk, width=width, height=height,
                                      background="white",
                                      highlightthickness=0)
        try:
            self._canvas.pack()
        except:
            pass
        if spyder_flag:
            def cancel_topmost():
                tk.attributes("-topmost", False)
            tk.attributes("-topmost", True)
            tk.focus_force()
            self._canvas.after(0, cancel_topmost)
        self._canvas.update()
        self._images = { }
        self._timers = [ ]
        self._base = GCompound()
        self._base._gw = self
        self._event_manager = _EventManager(self)
        self.set_window_title(_get_program_name())
        self._event_loop_started = False
        self._active = True
        if not spyder_flag:
            atexit.register(self._start_event_loop)

    def __eq__(self, other):
        if isinstance(other, GWindow):
            return self._canvas is other._canvas
        return False

# Public method: close

    def close(self):
        """Deletes the window from the screen."""
        self._delete_window()

# Public method: event_loop

    def event_loop(self):
        """Waits for events to happen in the window."""
        self._event_loop_started = True
        try:
            tkinter._root.mainloop()
        except KeyboardInterrupt:
            sys.exit(0)

# Public method: request_focus

    def request_focus(self):
        """Asks the system to assign the keyboard focus to the window."""
        tkinter._root.canvas.focus_set()

# Public method: clear

    def clear(self):
        """Clears the contents of the window."""
        self._base.remove_all()

# Public method: get_width

    def get_width(self):
        """Returns the width of the graphics window in pixels."""
        return self._window_width

# Public method: get_height

    def get_height(self):
        """Returns the height of the graphics window in pixels."""
        return self._window_height

# Public method: add_event_listener

    def add_event_listener(self, type, fn):
        """Adds an event listener of the specified type to the window."""
        if not isinstance(type, str):
            raise TypeError("add_event_listener: type must be a string")
        if not callable(fn):
            raise TypeError("add_event_listener: fn must be callable")
        self._event_manager.add_event_listener(type, fn)

# Public method: repaint

    def repaint(self):
        """Schedule a repaint on this window."""
        pass

# Public method: set_window_title

    def set_window_title(self, title):
        """Sets the title of the graphics window."""
        if not isinstance(title, str):
            raise TypeError("set_window_title: title must be a string")
        self._window_title = title
        self._tk.title(title)

# Public method: get_window_title

    def get_window_title(self):
        """Returns the title of the graphics window."""
        return self._window_title

# Public method: add

    def add(self, gobj, x=None, y=None):
        """Adds gobj to the window after moving it to (x, y), if specified."""
        self._base.add(gobj, x, y)

# Public method: remove

    def remove(self, gobj):
        """Removes the object from the window."""
        self._base.remove(gobj)

# Public method: get_element_at

    def get_element_at(self, x, y):
        """Returns the topmost GObject containing (x, y), or None."""
        return self._base.get_element_at(x, y)

# Public method: create_timer

    def create_timer(self, fn, delay):
        """Creates a GTimer object that calls fn after delay milliseconds."""
        if not callable(fn):
            raise TypeError("create_timer: fn must be callable")
        if not _is_number(delay):
            raise TypeError("create_timer: delay must be a number")
        return GTimer(self, fn, delay)

# Public method: set_timeout

    def set_timeout(self, fn, delay):
        """Starts a one-shot timer that calls fn after delay milliseconds."""
        if not callable(fn):
            raise TypeError("set_timeout: fn must be callable")
        if not _is_number(delay):
            raise TypeError("set_timeout: delay must be a number")
        timer = GTimer(self, fn, delay)
        timer.start()
        return timer

# Public method: set_interval

    def set_interval(self, fn, delay):
        """Starts an interval timer that calls fn every delay milliseconds."""
        if not callable(fn):
            raise TypeError("set_interval: fn must be callable")
        if not _is_number(delay):
            raise TypeError("set_interval: delay must be a number")
        timer = GTimer(self, fn, delay)
        timer.set_repeats(True)
        timer.start()
        return timer

# Public method: pause

    def pause(self, delay):
        """Pauses the current thread for delay milliseconds."""
        if not _is_number(delay):
            raise TypeError("pause: delay must be a number")
        n_cycles = delay // GWindow.MIN_WAKEUP
        for i in range(n_cycles):           # pylint: disable=unused-variable
            self._tk.update_idletasks()
            self._tk.update()
            time.sleep(delay / n_cycles / 1000)

# Public static method: exit

    @staticmethod
    def exit():
        """Closes all windows and exits from the application."""
        sys.exit()

# Public static method: get_program_name

    @staticmethod
    def get_program_name():
        """Returns the name of this program."""
        return _get_program_name()

# Public static method: get_screen_width

    @staticmethod
    def get_screen_width():
        """Returns the width in pixels of the entire display screen."""
        return _get_screen_width()

# Public static method: get_screen_height

    def get_screen_height():
        """Returns the height in pixels of the entire display screen."""
        return _get_screen_height()

# Public static method: convert_color_to_rgb

    @staticmethod
    def convert_color_to_rgb(name):
        """Converts a color name into an int that encodes the rgb values."""
        if not isinstance(name, str):
            raise TypeError("convert_color_to_rgb: name must be a string")
        return _convert_color_to_rgb(name)

# Public static method: convert_rgb_to_color

    @staticmethod
    def convert_rgb_to_color(rgb):
        """Converts an rgb value into a string in the form "#rrggbb"."""
        if not isinstance(rgb, int):
            raise TypeError("convert_rgb_to_color: rgb must be an integer")
        return _convert_rgb_to_color(rgb)

# Private method: _delete_window

    def _delete_window(self):
        """Closes the window and exits from the event loop."""
        try:
            self._active = False
            try:
                for timer in self._timers:
                    timer.stop()
            except:
                pass
            tkinter._root.destroy()
            del tkinter._root
        except:
            pass

# Private method: _start_event_loop

    def _start_event_loop(self):
        """Starts the event loop if it wasn't run explicitly."""
        if not self._event_loop_started:
            self.event_loop()

# Private method: _rebuild

    def _rebuild(self):
        """Rebuilds the tkinter data structure for the window."""
        self._canvas.delete("all")
        self._base._install(self, _GTransform())

# Class: GObject

class GObject(object):
    """
    This class is the common superclass of all graphical objects that can
    be displayed on a graphical window. For examples illustrating the use
    of the GObject class, see the descriptions of the individual subclasses.
    """

# Constructor: GObject

    def __init__(self):
        """Creates a new GObject (called only by subclasses)."""
        self._x = 0.0
        self._y = 0.0
        self._sf = 1
        self._angle = 0
        self._color = "Black"
        self._line_width = 1.0
        self._visible = True
        self._parent = None
        self._tkid = None
        self._gw = None
        self._ctm_base = _GTransform()

# Public method: get_x

    def get_x(self):
        """Returns the x-coordinate of the object."""
        return self._x

# Public method: get_y

    def get_y(self):
        """Returns the y-coordinate of the object."""
        return self._y

# Public method: get_location

    def get_location(self):
        """Returns the location of this object as a GPoint."""
        return GPoint(self._x, self._y)

# Public method: set_location

    def set_location(self, x, y):
        """Sets the location of this object to the specified point."""
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("set_location: x must be a number")
        if not _is_number(y):
            raise TypeError("set_location: y must be a number")
        self._x = x
        self._y = y
        self._update_location()

# Public method: move

    def move(self, dx, dy):
        """Moves the object using the displacements dx and dy."""
        if not _is_number(dx):
            raise TypeError("move: dx must be a number")
        if not _is_number(dy):
            raise TypeError("move: dy must be a number")
        self.set_location(self._x + dx, self._y + dy)

# Public method: move_polar

    def move_polar(self, r, theta):
        """Moves the object the distance r in the direction theta."""
        if not _is_number(r):
            raise TypeError("move_polar: r must be a number")
        if not _is_number(theta):
            raise TypeError("move_polar: theta must be a number")
        dx = r * math.cos(math.radians(theta))
        dy = -r * math.sin(math.radians(theta))
        self.move(dx, dy)

# Public method: get_width

    def get_width(self):
        """Returns the width of the bounding box of this object."""
        return self.get_bounds().get_width()

# Public method: get_height

    def get_height(self):
        """Returns the height of the bounding box of this object."""
        return self.get_bounds().get_height()

# Public method: get_size

    def get_size(self):
        """Returns the size of the object as a GDimension."""
        bounds = self.get_bounds()
        return GDimension(bounds.get_width(), bounds.get_height())

# Public method: set_line_width

    def set_line_width(self, line_width):
        """Sets the width of the line used to draw this object."""
        if not _is_number(line_width):
            raise TypeError("set_line_width: line_width must be a number")
        self._line_width = line_width
        self._update_properties(width=line_width)

# Public method: get_line_width

    def get_line_width(self):
        """Returns the width of the line used to draw this object."""
        return self._line_width

# Public method: set_color

    def set_color(self, color):
        """Sets the color used to display this object."""
        if not isinstance(color, str):
            raise TypeError("set_color: color must be a string")
        rgb = _convert_color_to_rgb(color)
        self._color = _convert_rgb_to_color(rgb)
        self._update_color()

# Public method: get_color

    def get_color(self):
        """Returns the object color as a string in the form "#rrggbb"."""
        return self._color

# Public method: scale

    def scale(self, sf):
        """Scales the object by the specified scale factor."""
        raise Exception("Not yet implemented")

# Public method: rotate

    def rotate(self, theta):
        """Rotates the object theta degrees counterclockwise."""
        if not _is_number(theta):
            raise TypeError("rotate: theta must be a number")
        self._angle += theta
        self._update_rotation()

# Public method: set_visible

    def set_visible(self, flag):
        """Sets whether this object is visible."""
        self._visible = flag
        self._update_visible()

# Public method: is_visible

    def is_visible(self):
        """Returns true if this object is visible."""
        return self._visible

# Public method: send_forward

    def send_forward(self):
        """Moves this object one step toward the front in the z dimension."""
        parent = self.get_parent()
        if parent is not None:
            parent._send_forward(self)

# Public method: send_to_front

    def send_to_front(self):
        """Moves this object to the front in the z dimension."""
        parent = self.get_parent()
        if parent is not None:
            parent._send_to_front(self)

# Public method: send_backward

    def send_backward(self):
        """Moves this object one step toward the back in the z dimension."""
        parent = self.get_parent()
        if parent is not None:
            parent._send_backward(self)

# Public method: send_to_back

    def send_to_back(self):
        """Moves this object to the back in the z dimension."""
        parent = self.get_parent()
        if parent is not None:
            parent._send_to_back(self)

# Public method: contains

    def contains(self, x, y):
        """Returns true if the specified point is inside the object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("contains: not defined after rotation")
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("contains: x must be a number")
        if not _is_number(y):
            raise TypeError("contains: y must be a number")
        bounds = self.get_bounds()
        if bounds is None:
            return False
        return bounds.contains(x, y)

# Public method: get_parent

# Implementation notes: get_parent
# --------------------------------
# Every GWindow is initialized to contain a single GCompound that
# is aligned with the window.  Adding objects to the window adds
# them to that GCompound, which means that every object you add
# to the window has a parent.  Calling get_parent on the top-level
# GCompound returns None.

    def get_parent(self):
        """Returns a pointer to the GCompound that contains this object."""
        return self._parent

# Abstract method: get_type

    def get_type(self):
        """Returns the concrete type of the object as a string."""
        raise Exception("get_type is not defined in the GObject class")

# Abstract method: get_bounds

    def get_bounds(self):
        """Returns the bounding box of this object."""
        raise Exception("get_bounds is not defined in the GObject class")

# Protected method: _update_properties

    def _update_properties(self, **options):
        """Updates the specified properties of the object."""
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        tkc.itemconfig(self._tkid, **options)

# Protected method: _update_location

    def _update_location(self):
        """Updates this object's location from the stored x and y values."""
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        try:
            coords = tkc.coords(self._tkid)
        except Exception:
            return
        offx = 0
        offy = 0
        gobj = self.get_parent()
        while gobj is not None:
            offx += gobj._x
            offy += gobj._y
            gobj = gobj.get_parent()
        dx = (self._x + offx) - coords[0]
        dy = (self._y + offy) - coords[1]
        tkc.move(self._tkid, dx, dy)

# Protected method: _update_color

    def _update_color(self):
        """Updates the color properties of this object."""
        self._update_properties(fill=self._color)

# Protected method: _update_visible

    def _update_visible(self):
        """Updates the visible property."""
        if self._visible:
            self._update_properties(state=tkinter.NORMAL)
        else:
            self._update_properties(state=tkinter.HIDDEN)

# Protected method: _update_rotation

    def _update_rotation(self):
        """Updates the rotation angle for this object."""
        raise Exception("Rotation not yet implemented for this class")

# Private method: _get_window

    def _get_window(self):
        """Returns the GWindow in which this object is installed."""
        gobj = self
        while gobj._parent is not None:
            gobj = gobj._parent
        return gobj._gw

# Private abstract method: _install

    def _install(self, target, ctm):
        """Installs the object in the target."""
        raise Exception("_install is not defined in the GObject class")


# Class: GFillableObject

class GFillableObject(GObject):
    """This abstract class is the superclass of all fillable objects."""

# Constructor: GFillableObject

    def __init__(self):
        """Initializes a GFillableObject (called only by subclasses)."""
        GObject.__init__(self)
        self._fill_flag = False
        self._fill_color = ""

# Public method: set_filled

    def set_filled(self, flag):
        """Sets the fill flag for the object (False=outlined, True=filled)."""
        self._fill_flag = flag
        self._update_color()

# Public method: is_filled

    def is_filled(self):
        """Returns True if the object is filled."""
        return self._fill_flag

# Public method: set_fill_color

    def set_fill_color(self, color):
        """Sets the color used to display the filled region of the object."""
        if not isinstance(color, str):
            raise TypeError("set_fill_color: color must be a string")
        rgb = _convert_color_to_rgb(color)
        self._fill_color = _convert_rgb_to_color(rgb)
        self._update_color()

# Public method: get_fill_color

    def get_fill_color(self):
        """Returns the color used to fill this object."""
        return self._fill_color

# Override method: _update_color

    def _update_color(self):
        """Updates the color properties for a GFillableObject."""
        outline = self._color
        if self._fill_flag:
            fill = self._fill_color
            if fill is None or fill == "":
                fill = outline
        else:
            fill = ""
        self._update_properties(outline=outline, fill=fill)


# Class: GRect

class GRect(GFillableObject):
    """This class implements a rectangular GObject."""

# Constructor: GRect

    def __init__(self, a1, a2, a3=None, a4=None):
        """Creates a GRect from (x,y,width,height) or (width,height)."""
        GFillableObject.__init__(self)
        if a3 is None:
            x = 0
            y = 0
            width = a1
            height = a2
        else:
            x = a1
            y = a2
            width = a3
            height = a4
        if not _is_number(x):
            raise TypeError("GRect: x must be a number")
        if not _is_number(y):
            raise TypeError("GRect: y must be a number")
        if not _is_number(width):
            raise TypeError("GRect: width must be a number")
        if not _is_number(height):
            raise TypeError("GRect: height must be a number")
        self._width = width
        self._height = height
        self.set_location(x, y)

# Public method: set_size

    def set_size(self, width, height=None):
        """Changes the size of this rectangle as specified."""
        if isinstance(width, GDimension):
            width, height = width.get_width(), width.get_height()
        if not _is_number(width):
            raise TypeError("set_size: width must be a number")
        if not _is_number(height):
            raise TypeError("set_size: height must be a number")
        self._width = width
        self._height = height
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        coords = tkc.coords(self._tkid)
        tkc.coords(self._tkid, coords[0], coords[1],
                   coords[0] + width, coords[1] + height)

# Public method: set_bounds

    def set_bounds(self, x, y=None, width=None, height=None):
        """Changes the bounds of this rectangle to the specified values."""
        if isinstance(x, GRectangle):
            width, height = x.get_width(), x.get_height()
            x, y = x.get_x(), x.get_y()
        if not _is_number(x):
            raise TypeError("set_bounds: x must be a number")
        if not _is_number(y):
            raise TypeError("set_bounds: y must be a number")
        if not _is_number(width):
            raise TypeError("set_bounds: width must be a number")
        if not _is_number(height):
            raise TypeError("set_bounds: height must be a number")
        self.set_location(x, y)
        self.set_size(width, height)

# Override method: get_bounds

    def get_bounds(self):
        """Returns the bounds of this GRect."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        p0 = lctm.transform(0, 0)
        bb = GRectangle(p0.get_x(), p0.get_y()) 
        bb.add(lctm.transform(self._width, 0))
        bb.add(lctm.transform(0, self._height))
        bb.add(lctm.transform(self._width, self._height))        
        return bb

# Override method: get_type

    def get_type(self):
        """Returns the type of this object."""
        return "GRect"

# Override method: _install

    def _install(self, target, ctm):
        """Installs the GRect in the canvas."""
        gw = target
        tkc = gw._canvas
        self._ctm_base = ctm
        lctm = _GTransform(rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        p0 = ctm.transform(self._x, self._y)
        if lctm._rotation == 0:
            self._rep = "Rectangle"
            p1 = ctm.transform(self._x + self._width, self._y + self._height)
            self._tkid = tkc.create_rectangle(p0._x, p0._y, p1._x, p1._y,
                                              width=self._line_width)
        else:
            self._rep = "Polygon"
            coords = self._create_rect_coords(p0._x, p0._y,
                                              self._width, self._height, lctm)
            self._tkid = tkc.create_polygon(*coords, width=self._line_width)
        self._update_color()
        self._update_visible()

# Override method: _update_rotation

    def _update_rotation(self):
        """Updates the points for this GRect after a rotation."""
        gw = self._get_window()
        if gw is not None:
            if self._rep == "Rectangle":
                gw._rebuild()
            else:
                tkc = gw._canvas
                ctm = self._ctm_base
                lctm = _GTransform(rotation=self._angle + ctm._rotation,
                                   sf=self._sf * ctm._sf)
                p0 = ctm.transform(self._x, self._y)
                coords = self._create_rect_coords(p0._x, p0._y,
                                                  self._width, self._height,
                                                  lctm)
                tkc.coords(self._tkid, *coords)

# Private method: _create_rect_coords

    def _create_rect_coords(self, x, y, width, height, ctm):
        p1 = ctm.transform(width, 0)
        p2 = ctm.transform(width, height)
        p3 = ctm.transform(0, height)
        return [ x, y,
                 x + p1._x, y + p1._y,
                 x + p2._x, y + p2._y,
                 x + p3._x, y + p3._y ]

# Override method: __str__

    def __str__(self):
        return ("GRect(" + str(self._x) + ", " + str(self._y) + ", " +
                str(self._width) + ", " + str(self._height) + ")")


# Class: GOval

class GOval(GFillableObject):
    """This class represents an oval inscribed in a rectangular box."""

# Constructor: GOval

    def __init__(self, a1, a2, a3=None, a4=None):
        """Creates a GOval from (x,y,width,height) or (width,height)."""
        GFillableObject.__init__(self)
        if a3 is None:
            x = 0
            y = 0
            width = a1
            height = a2
        else:
            x = a1
            y = a2
            width = a3
            height = a4
        if not _is_number(x):
            raise TypeError("GOval: x must be a number")
        if not _is_number(y):
            raise TypeError("GOval: y must be a number")
        if not _is_number(width):
            raise TypeError("GOval: width must be a number")
        if not _is_number(height):
            raise TypeError("GOval: height must be a number")
        self._width = width
        self._height = height
        self._rep = "Oval"
        self.set_location(x, y)

# Public method: set_size

    def set_size(self, width, height=None):
        """Changes the size of this oval as specified."""
        if isinstance(width, GDimension):
            width, height = width.get_width(), width.get_height()
        if not _is_number(width):
            raise TypeError("set_size: width must be a number")
        if not _is_number(height):
            raise TypeError("set_size: height must be a number")
        self._width = width
        self._height = height
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        coords = tkc.coords(self._tkid)
        tkc.coords(self._tkid, coords[0], coords[1],
                   coords[0] + width, coords[1] + height)

# Public method: set_bounds

    def set_bounds(self, x, y=None, width=None, height=None):
        """Changes the bounds of this rectangle to the specified values."""
        if isinstance(x, GRectangle):
            width, height = x.get_width(), x.get_height()
            x, y = x.get_x(), x.get_y()
        if not _is_number(x):
            raise TypeError("set_bounds: x must be a number")
        if not _is_number(y):
            raise TypeError("set_bounds: y must be a number")
        if not _is_number(width):
            raise TypeError("set_bounds: width must be a number")
        if not _is_number(height):
            raise TypeError("set_bounds: height must be a number")
        self.set_location(x, y)
        self.set_size(width, height)

# Override method: get_bounds

    def get_bounds(self):
        """Returns the bounds of this GOval."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        rx = self._width / 2
        ry = self._height / 2
        center = lctm.transform(rx, ry)
        ux = rx * math.cos(math.radians(lctm._rotation))
        uy = rx * math.sin(math.radians(lctm._rotation))
        vx = ry * math.cos(math.radians(lctm._rotation) + math.pi / 2)
        vy = ry * math.sin(math.radians(lctm._rotation) + math.pi / 2)
        hw = math.sqrt(ux * ux + vx * vx)
        hh = math.sqrt(uy * uy + vy * vy)
        return GRectangle(center._x - hw, center._y - hh, 2 * hw, 2 * hh)

# Override method: contains

    def contains(self, x, y):
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("contains: not defined after rotation")
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("contains: x must be a number")
        if not _is_number(y):
            raise TypeError("contains: y must be a number")
        rx = self._width / 2
        ry = self._height / 2
        tx = x - (self._x + rx)
        ty = y - (self._y + ry)
        return (tx * tx) / (rx * rx) + (ty * ty) / (ry * ry) <= 1.0

# Override method: get_type

    def get_type(self):
        """Returns the type of this object."""
        return "GOval"

# Override method: _install

    def _install(self, target, ctm):
        """Installs the GOval in the canvas."""
        gw = target
        tkc = gw._canvas
        self._ctm_base = ctm
        lctm = _GTransform(rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        p0 = ctm.transform(self._x, self._y)
        if lctm._rotation == 0:
            self._rep = "Oval"
            lctm = ctm.compose(_GTransform(sf=self._sf))
            p1 = ctm.transform(self._x + self._width, self._y + self._height)
            self._tkid = tkc.create_oval(p0._x, p0._y, p1._x, p1._y,
                                         width=self._line_width)
        else:
            self._rep = "Polygon"
            coords = self._create_oval_coords(p0._x, p0._y,
                                              self._width, self._height, lctm)
            self._tkid = tkc.create_polygon(*coords, width=self._line_width,
                                            smooth=1)
        self._update_color()
        self._update_visible()

# Override method: _update_rotation

    def _update_rotation(self):
        """Updates the points for this GOval after a rotation."""
        gw = self._get_window()
        if gw is not None:
            if self._rep == "Oval":
                gw._rebuild()
            else:
                tkc = gw._canvas
                ctm = self._ctm_base
                lctm = _GTransform(rotation=self._angle + ctm._rotation,
                                   sf=self._sf * ctm._sf)
                p0 = ctm.transform(self._x, self._y)
                coords = self._create_oval_coords(p0._x, p0._y,
                                                  self._width, self._height,
                                                  lctm)
                tkc.coords(self._tkid, *coords)

# Private method: _create_oval_coords

    def _create_oval_coords(self, x, y, width, height, ctm):
        n = 16
        dth = 360 / n
        r1 = width / 2
        r2 = height / 2
        coords = [ ]
        for i in range(0, n):
            theta = math.radians(i * dth)
            pt = ctm.transform(r1 + r1 * math.cos(theta),
                               r2 - r2 * math.sin(theta))
            coords.append(x + pt._x)
            coords.append(y + pt._y)
        return coords

# Override method: __str__

    def __str__(self):
        return ("GOval(" + str(self._x) + ", " + str(self._y) + ", " +
                str(self._width) + ", " + str(self._height) + ")")

# Class: GCompound

# Implementation notes: GCompound
# -------------------------------
# This GObject subclass consists of a collection of other
# graphical objects.  Once assembled, the internal objects can be
# manipulated as a unit.  The GCompound keeps track of its own
# position, and all items within it are drawn relative to that
# location.

class GCompound(GObject):
    """This class represents a collection of graphical objects."""

# Constructor: GCompound

    def __init__(self):
        """Creates a GCompound with no internal components."""
        GObject.__init__(self)
        self._contents = [ ]

# Public method: add

    def add(self, gobj, x=None, y=None):
        """Adds gobj to the GCompound, moving it to (x, y) if specified."""
        if not isinstance(gobj, GObject):
            raise TypeError("add: gobj must be a GObject")
        if gobj._parent is not None:
            raise ValueError("add: gobj has already been added")
        if x is not None:
            if not _is_number(x):
                raise TypeError("add: x must be a number")
            if not _is_number(y):
                raise TypeError("add: y must be a number")
            gobj.set_location(x, y)
        self._contents.append(gobj)
        gobj._parent = self
        if self._gw is None:
            gw = self._get_window()
            if gw is not None:
                gw._rebuild()
        else:
            gobj._install(self._gw, _GTransform())

# Public method: remove

    def remove(self, gobj):
        """Removes the specified object from the GCompound."""
        if not isinstance(gobj, GObject):
            raise TypeError("remove: gobj must be a GObject")
        index = self._find_gobject(gobj)
        if index != -1:
            self._remove_at(index)
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Public method: remove_all

    def remove_all(self):
        """Removes all graphical objects from the GCompound."""
        while len(self._contents) > 0:
            self._remove_at(0)
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Public method: get_element_at

    def get_element_at(self, x, y):
        """Returns the topmost GObject containing (x, y), or None."""
        if not _is_number(x):
            raise TypeError("get_element_at: x must be a number")
        if not _is_number(y):
            raise TypeError("get_element_at: y must be a number")
        for gobj in reversed(self._contents):
            if gobj.contains(x, y):
                return gobj
        return None

# Public method: get_element_count

    def get_element_count(self):
        """Returns the number of graphical objects in the GCompound."""
        return len(self._contents)

# Public method: get_element

    def get_element(self, index):
        """Returns the graphical object at the specified index."""
        if not isinstance(index, int):
            raise TypeError("get_element: index must be an integer")
        return self._contents[index]

# Override method: get_bounds

    def get_bounds(self):
        """Returns a bounding rectangle for this compound."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("get_bounds: not defined after rotation")
        if len(self._contents) == 0:
            origin = lctm.transform(0, 0)
            return GRectangle(origin._x, origin._y, 0, 0)
        x0 = self._x
        y0 = self._y
        x_min = sys.float_info.max
        y_min = sys.float_info.max
        x_max = sys.float_info.min
        y_max = sys.float_info.min
        for gobj in self._contents:
            bb = gobj.get_bounds()
            x_min = min(x_min, x0 + bb._x)
            y_min = min(y_min, y0 + bb._y)
            x_max = max(x_max, x0 + bb._x)
            y_max = max(y_max, y0 + bb._y)
            x_min = min(x_min, x0 + bb._x + bb.get_width())
            y_min = min(y_min, y0 + bb._y + bb.get_height())
            x_max = max(x_max, x0 + bb._x + bb.get_width())
            y_max = max(y_max, y0 + bb._y + bb.get_height())
        return GRectangle(x_min, y_min, x_max - x_min, y_max - y_min)

# Public method: contains

    def contains(self, x, y):
        """Returns True if the specified point is inside the object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("contains: not defined after rotation")
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("contains: x must be a number")
        if not _is_number(y):
            raise TypeError("contains: y must be a number")
#        refpt = self.get_location()
#        tx = x - refpt._x
#        ty = y - refpt._y
        tx = x
        ty = y
        for gobj in self._contents:
            if gobj.contains(tx, ty):
                return True
        return False

# Override method: get_type

    def get_type(self):
        """Returns the type of this object"""
        return "GCompound"

# Public method: __str__

    def __str__(self):
        return "GCompound(...)"

# Override method: _update_location

    def _update_location(self):
        """Updates the location for this GCompound."""
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Override method: _update_rotation

    def _update_rotation(self):
        """Redraws the window on rotation."""
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Override method: _update_visible

    def _update_visible(self):
        """Redraws the window on set_visible"""
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Override method: _install

    def _install(self, target, ctm):
        if self._visible:
            lctm = ctm.compose(_GTransform(self._x, self._y,
                                           rotation=self._angle, sf=self._sf))
            for gobj in self._contents:
                gobj._install(target, lctm)

# Internal method: _send_forward

    def _send_forward(self, gobj):
        index = self._find_gobject(gobj)
        if index == -1:
            return
        if index != len(self._contents) - 1:
            self._contents.pop(index)
            self._contents.insert(index + 1, gobj)
            gw = self._get_window()
            if gw is not None:
                gw._rebuild()

# Internal method: _send_to_front

    def _send_to_front(self, gobj):
        index = self._find_gobject(gobj)
        if index == -1:
            return
        if index != len(self._contents) - 1:
            self._contents.pop(index)
            self._contents.append(gobj)
            gw = self._get_window()
            if gw is not None:
                gw._rebuild()

# Internal method: _send_backward

    def _send_backward(self, gobj):
        index = self._find_gobject(gobj)
        if index == -1:
            return
        if index != 0:
            self._contents.pop(index)
            self._contents.insert(index - 1, gobj)
            gw = self._get_window()
            if gw is not None:
                gw._rebuild()

# Internal method: _send_to_back

    def _send_to_back(self, gobj):
        index = self._find_gobject(gobj)
        if index == -1:
            return
        if index != 0:
            self._contents.pop(index)
            self._contents.insert(0, gobj)
            gw = self._get_window()
            if gw is not None:
                gw._rebuild()

# Internal method: _find_gobject

    def _find_gobject(self, gobj):
        n = len(self._contents)
        for i in range(n):
            if self._contents[i] == gobj:
                return i
        return -1

# Internal method: _remove_at

    def _remove_at(self, index):
        gobj = self._contents[index]
        self._contents.pop(index)
        gobj._parent = None

# Class: GArc

# Implementation notes: GArc
# --------------------------
# This GObject subclass represents an elliptical arc defined
# by the following parameters:
#
# The coordinates of the bounding rectangle (x, y, width, height)
# The angle at which the arc starts (start)
# The number of degrees that the arc covers (sweep)
#
# All angles in a GArc description are measured in degrees moving
# counterclockwise from the +x axis.  Negative values for either start
# or sweep indicate motion in a clockwise direction.

class GArc(GFillableObject):
    """This GObject subclass represents an elliptical arc."""

# Constructor: GArc

    def __init__(self, a1, a2, a3=None, a4=None, a5=None, a6=None):
        """Creates a new GArc."""
        GFillableObject.__init__(self)
        if a5 is None:
            x = 0
            y = 0
            width = a1
            height = a2
            start = a3
            sweep = a4
        else:
            x = a1
            y = a2
            width = a3
            height = a4
            start = a5
            sweep = a6
        if not _is_number(x):
            raise TypeError("GArc: x must be a number")
        if not _is_number(y):
            raise TypeError("GArc: y must be a number")
        if not _is_number(width):
            raise TypeError("GArc: width must be a number")
        if not _is_number(height):
            raise TypeError("GArc: height must be a number")
        if not _is_number(start):
            raise TypeError("GArc: start must be a number")
        if not _is_number(sweep):
            raise TypeError("GArc: sweep must be a number")
        self._frame_width = width
        self._frame_height = height
        self._start = start
        self._sweep = sweep
        self._rep = "Oval"
        self.set_location(x, y)

# Public method: set_start_angle

    def set_start_angle(self, start):
        """Sets the starting angle for this GArc object."""
        if not _is_number(start):
            raise TypeError("set_start_angle: start must be a number")
        self._start = start
        self._update_properties(start=start)

# Public method: get_start_angle

    def get_start_angle(self):
        """Returns the starting angle for this GArc object."""
        return self._start

# Public method: set_sweep_angle

    def set_sweep_angle(self, sweep):
        """Sets the sweep angle for this GArc object."""
        if not _is_number(sweep):
            raise TypeError("set_sweep_angle: sweep must be a number")
        self._sweep = sweep
        self._update_properties(extent=sweep)

# Public method: get_sweep_angle

    def get_sweep_angle(self):
        """Returns the sweep angle for this GArc object."""
        return self._sweep

# Public method: get_start_point

    def get_start_point(self):
        """Returns the point at which the arc starts."""
        return self._get_arc_point(self._start)

# Public method: get_end_point

    def get_end_point(self):
        """Returns the point at which the arc ends."""
        return self._get_arc_point(self._start + self._sweep)

# Public method: set_frame_rectangle

    def set_frame_rectangle(self, x, y=None, width=None, height=None):
        """Changes the bounds of the rectangle used to frame the arc."""
        if isinstance(x, GRectangle):
            width, height = x.get_width(), x.get_height()
            x, y = x.get_x(), x.get_y()
        if not _is_number(x):
            raise TypeError("set_frame_rectangle: x must be a number")
        if not _is_number(y):
            raise TypeError("set_frame_rectangle: y must be a number")
        if not _is_number(width):
            raise TypeError("set_frame_rectangle: width must be a number")
        if not _is_number(height):
            raise TypeError("set_frame_rectangle: height must be a number")
        self.set_location(x, y)
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        coords = tkc.coords(self._tkid)
        tkc.coords(self._tkid, coords[0], coords[1],
                   coords[0] + width, coords[1] + height)

# Public method: get_frame_rectangle

    def get_frame_rectangle(self):
        """Returns the bounds of the rectangle used to frame the arc."""
        return GRectangle(self._x, self._y,
                          self._frame_width, self._frame_height)

# Override method: set_filled

    def set_filled(self, flag):
        """Sets the fill flag for the arc (False=outlined, True=filled)."""
        GFillableObject.set_filled(self, flag)
        style = tkinter.ARC
        if flag:
            style = tkinter.PIESLICE
        self._update_properties(style=style)

# Public method: get_bounds

    def get_bounds(self):
        """Gets the bounding rectangle for this object"""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("get_bounds: not defined after rotation")
        rx = self._frame_width / 2
        ry = self._frame_height / 2
        cx = self._x + rx
        cy = self._y + ry
        start_radians = self._start * math.pi / 180
        sweep_radians = self._sweep * math.pi / 180
        p1x = cx + math.cos(start_radians) * rx
        p1y = cy - math.sin(start_radians) * ry
        p2x = cx + math.cos(start_radians + sweep_radians) * rx
        p2y = cy - math.sin(start_radians + sweep_radians) * ry
        x_min = min(p1x, p2x)
        x_max = max(p1x, p2x)
        y_min = min(p1y, p2y)
        y_max = max(p1y, p2y)
        if self._contains_angle(0):
            x_max = cx + rx
        if self._contains_angle(90):
            y_min = cy - ry
        if self._contains_angle(180):
            x_min = cx - rx
        if self._contains_angle(270):
            y_max = cy + ry
        if self._fill_flag:
            x_min = min(x_min, cx)
            y_min = min(y_min, cy)
            x_max = max(x_max, cx)
            y_max = max(y_max, cy)
        return GRectangle(x_min, y_min, x_max - x_min, y_max - y_min)

# Public method: contains

    def contains(self, x, y):
        """Returns True if the specified point is inside the object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("contains: not defined after rotation")
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("contains: x must be a number")
        if not _is_number(y):
            raise TypeError("contains: y must be a number")
        rx = self._frame_width / 2
        ry = self._frame_height / 2
        if rx == 0 or ry == 0:
            return False
        dx = x - (self._x + rx)
        dy = y - (self._y + ry)
        r = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry)
        if self._fill_flag:
            if r > 1.0:
                return False
        else:
            t = __ARC_TOLERANCE__ / ((rx + ry) / 2)
            if abs(1.0 - r) > t:
                return False
        return self._contains_angle(math.atan2(-dy, dx) * 180 / math.pi)

# Override method: get_type

    def get_type(self):
        """Returns the type of this object"""
        return "GArc"

# Public method: __str__

    def __str__(self):
        return ("GArc(" + str(self._x) + ", " + str(self._y) + ", " +
                str(self._frame_width) + ", " +
                str(self._frame_height) + ", " +
                str(self._start) + ", " + str(self._sweep) + ")")

# Override method: _install

    def _install(self, target, ctm):
        """Installs the GArc in the canvas."""
        gw = target
        tkc = gw._canvas
        lctm = _GTransform(rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        p0 = ctm.transform(self._x, self._y)
        if lctm._rotation == 0:
            p1 = ctm.transform(self._x + self._frame_width,
                               self._y + self._frame_height)
            if abs(self._sweep) >= 360:
                self._rep = "Oval"
                self._tkid = tkc.create_oval(p0._x, p0._y, p1._x, p1._y,
                                             width=self._line_width)
            else:
                self._rep = "Arc"
                style = tkinter.ARC
                if self._fill_flag:
                    style = tkinter.PIESLICE
                self._tkid = tkc.create_arc(p0._x, p0._y, p1._x, p1._y,
                                            start=self._start,
                                            extent=self._sweep,
                                            width=self._line_width,
                                            style=style)
        else:
            self._rep = "Polygon"
            if self._fill_flag:
                coords = self._create_arc_coords(p0._x, p0._y,
                                                 self._frame_width,
                                                 self._frame_height,
                                                 self._start, self._sweep,
                                                 True, lctm)
                self._tkid = tkc.create_polygon(*coords,
                                                width=self._line_width,
                                                smooth=1)
            else:
                coords = self._create_arc_coords(p0._x, p0._y,
                                                 self._frame_width,
                                                 self._frame_height,
                                                 self._start, self._sweep,
                                                 False, lctm)
                self._tkid = tkc.create_line(*coords,
                                             width=self._line_width,
                                             smooth=1)
        self._update_color()
        self._update_visible()

# Override method: set_filled

    def set_filled(self, flag):
        GFillableObject.set_filled(self, flag)
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Override method: _update_rotation

    def _update_rotation(self):
        """Updates the points for this GArc after a rotation."""
        gw = self._get_window()
        if gw is not None:
            tkc = gw._canvas
            ctm = self._ctm_base
            p0 = ctm.transform(self._x, self._y)
            lctm = _GTransform(rotation=self._angle + ctm._rotation,
                               sf=self._sf * ctm._sf)
            coords = self._create_arc_coords(p0._x, p0._y,
                                             self._frame_width,
                                             self._frame_height,
                                             self._start, self._sweep,
                                             self._fill_flag, lctm)
            tkc.coords(self._tkid, *coords)

# Override method: _update_color

    def _update_color(self):
        """Updates the color properties for a GArc."""
        if self._fill_flag:
            outline = self._color
            fill = self._fill_color
            if fill is None or fill == "":
                fill = outline
            self._update_properties(outline=outline, fill=fill)
        elif self._rep == "Polygon":
            self._update_properties(fill=self._color)
        else:
            self._update_properties(outline=self._color, fill="")

# Private method: _create_arc_coords

    def _create_arc_coords(self, x, y, width, height, start, sweep, fill, ctm):
        """Creates an array of coordinates for an elliptical arc."""
        n = max(3, round(abs(sweep) / 30))
        dth = sweep / n
        r1 = width / 2
        r2 = height / 2
        coords = [ ]
        for i in range(0, n + 1):
            theta = math.radians(start + i * dth)
            pt = ctm.transform(r1 + r1 * math.cos(theta),
                               r2 - r2 * math.sin(theta))
            coords.append(x + pt._x)
            coords.append(y + pt._y)
        if fill:
            pt = ctm.transform(r1, r2)
            center = [ x + pt._x, y + pt._y ]
            coords = center + center + coords[0:2] + coords + coords[-2:]
        return coords
        
# Private method: _get_arc_point

    def _get_arc_point(self, theta):
        rx = self._frame_width / 2
        ry = self._frame_height / 2
        cx = self._x + rx
        cy = self._y + ry
        radians = theta * math.pi / 180
        return GPoint(cx + rx * math.cos(radians), cy - ry * math.sin(radians))

# Private method: _get_arc_point

    def _get_arc_point(self, theta):
        rx = self._frame_width / 2
        ry = self._frame_height / 2
        cx = self._x + rx
        cy = self._y + ry
        radians = theta * math.pi / 180
        return GPoint(cx + rx * math.cos(radians), cy - ry * math.sin(radians))

# Private method: _contains_angle

    def _contains_angle(self, theta):
        start = min(self._start, self._start + self._sweep)
        sweep = abs(self._sweep)
        if sweep >= 360:
            return True
        if theta < 0:
            theta = 360 - math.fmod(-theta, 360)
        else:
            theta = math.fmod(theta, 360)
        if start < 0:
            start = 360 - math.fmod(-start, 360)
        else:
            start = math.fmod(start, 360)
        if start + sweep > 360:
            return (theta >= start or theta <= start + sweep - 360)
        else:
            return (theta >= start and theta <= start + sweep)


# Class: GLine

class GLine(GObject):
    """This GObject subclass represents a line segment."""

# Constructor: GLine

    def __init__(self, x0, y0, x1, y1):
        """Initializes a line segment from its endpoints."""
        GObject.__init__(self)
        if not _is_number(x0):
            raise TypeError("GLine: x0 must be a number")
        if not _is_number(y0):
            raise TypeError("GLine: y0 must be a number")
        if not _is_number(x1):
            raise TypeError("GLine: x1 must be a number")
        if not _is_number(y1):
            raise TypeError("GLine: y1 must be a number")
        self._x = x0
        self._y = y0
        self._dx = x1 - x0
        self._dy = y1 - y0

# Public method: set_start_point

    def set_start_point(self, x, y):
        """Sets the initial point to (x, y), leaving the end unchanged."""
        if not _is_number(x):
            raise TypeError("set_start_point: x must be a number")
        if not _is_number(y):
            raise TypeError("set_start_point: y must be a number")
        self._dx += self._x - x
        self._dy += self._y - y
        self._x = x
        self._y = y
        self._update_points()

# Public method: get_start_point

    def get_start_point(self):
        """Returns the point at which the line starts."""
        return GPoint(self._x, self._y)

# Public method: set_end_point

    def set_end_point(self, x, y):
        """Sets the end point to (x, y), leaving the start unchanged."""
        if not _is_number(x):
            raise TypeError("set_end_point: x must be a number")
        if not _is_number(y):
            raise TypeError("set_end_point: y must be a number")
        self._dx = x - self._x
        self._dy = y - self._y
        self._update_points()

# Public method: get_end_point

    def get_end_point(self):
        """Returns the point at which the line ends."""
        return GPoint(self._x + self._dx, self._y + self._dy)

# Overload method: contains

    def contains(self, x, y):
        """Returns True if the specified point is inside the object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("contains: not defined after rotation")
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("contains: x must be a number")
        if not _is_number(y):
            raise TypeError("contains: y must be a number")
        x0 = self._x
        y0 = self._y
        x1 = x0 + self._dx
        y1 = y0 + self._dy
        t_squared = __LINE_TOLERANCE__ * __LINE_TOLERANCE__
        if _dsq(x, y, x0, y0) < t_squared:
            return True
        if _dsq(x, y, x1, y1) < t_squared:
            return True
        if x < min(x0, x1) - __LINE_TOLERANCE__:
            return False
        if x > max(x0, x1) + __LINE_TOLERANCE__:
            return False
        if y < min(y0, y1) - __LINE_TOLERANCE__:
            return False
        if y > max(y0, y1) + __LINE_TOLERANCE__:
            return False
        if (x0 - x1) == 0 and (y0 - y1) == 0:
            return False
        d = _dsq(x0, y0, x1, y1)
        u = ((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / d
        return _dsq(x, y, x0 + u * (x1 - x0), y0 + u * (y1 - y0)) < t_squared

# Override method: get_type

    def get_type(self):
        """Returns the type of this object"""
        return "GLine"

# Public method: __str__

    def __str__(self):
        return ("GLine(" + str(self._x) + ", " + str(self._y) + ", " +
                str(self._x + self._dx) + ", " + str(self._y + self._dy) + ")")

# Override method: get_bounds

    def get_bounds(self):
        """Returns the bounds of this GLine."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("get_bounds: not defined after rotation")
        p0 = lctm.transform(0, 0)
        p1 = lctm.transform(self._dx, self._dy)
        x0 = min(p0._x, p1._x)
        y0 = min(p0._y, p1._y)
        x1 = max(p0._x, p1._x)
        y1 = max(p0._y, p1._y)
        return GRectangle(x0, y0, x1 - x0, y1 - y0)

# Override method: _install

    def _install(self, target, ctm):
        """Installs the GLine in the canvas."""
        gw = target
        tkc = gw._canvas
        self._ctm_base = ctm
        p0 = ctm.transform(self._x, self._y)
        angle = ctm._rotation + self._angle
        ctm = _GTransform(rotation=angle, sf=ctm._sf)
        deltas = ctm.transform(self._dx, self._dy)
        x1 = p0._x + deltas._x
        y1 = p0._y + deltas._y
        dp = ctm.transform(self._dx, self._dy)
        self._tkid = tkc.create_line(p0._x, p0._y,
                                     p0._x + dp._x, p0._y + dp._y,
                                     width=self.get_line_width(),
                                     fill=self._color)
        self._update_visible()

# Override method: _update_points

    def _update_points(self):
        """Updates the points in the GLine."""
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        ctm = self._ctm_base
        p0 = ctm.transform(self._x, self._y)
        angle = ctm._rotation + self._angle
        ctm = _GTransform(rotation=angle, sf=ctm._sf)
        dp = ctm.transform(self._dx, self._dy)
        tkc.coords(self._tkid, p0._x, p0._y, p0._x + dp._x, p0._y + dp._y)

# Override method: _update_rotation

    def _update_rotation(self):
        """Updates the points for this GLine after a rotation."""
        self._update_points()


# Class: GImage

class GImage(GObject):
    """This GObject subclass represents an image from a file."""

    def __init__(self, source, x=0, y=0):
        """Initializes a new image loaded from the source."""
        GObject.__init__(self)
        self._source = source
        self._image_model = _image_model
        if _image_model == "PIL":
            if isinstance(source, str):
                if "://" in source or source.startswith("data:"):
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    with urllib.request.urlopen(source, context=ctx) as req:
                        self._image = Image.open(io.BytesIO(req.read()))
                else:
                    self._image = Image.open(source)
                self._image.load()
            else:
                width = len(source[0])
                height = len(source)
                ba = bytearray(4 * width * height)
                for i in range(height):
                    for j in range(width):
                        argb = source[i][j]
                        base = 4 * (i * width + j)
                        ba[base] = (argb >> 16) & 0xFF
                        ba[base + 1] = (argb >> 8) & 0xFF
                        ba[base + 2] = argb & 0xFF
                        ba[base + 3] = (argb >> 24) & 0xFF
                self._image = Image.frombytes("RGBA", (width, height),
                                              bytes(ba))
            self._photo = ImageTk.PhotoImage(self._image)
        else:
            if isinstance(source, str):
                self._photo = tkinter.PhotoImage(file=source)
            else:
                raise ImportError("get_pixel_array requires the " +
                                  "Pillow library")
        self.set_location(x, y)
        self._sf = 1

# Public method: get_bounds

    def get_bounds(self):
        """Returns the bounding rectangle for this object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("get_bounds: not defined after rotation")
        photo = self._photo
        return GRectangle(self._x, self._y, photo.width(), photo.height())

# Public method: get_pixel_array

    def get_pixel_array(self):
        """Returns an array of integers containing the pixel data."""
        if self._image_model == "PIL":
            image = self._image
            width = image.width
            height = image.height
        else:
            width = self._photo.width()
            height = self._photo.height()
        pixels = height * [ [ 0 ] ]
        for y in range(height):
            pixels[y] = width * [ 0 ]
        if self._image_model == "PIL":
            data = image.convert("RGBA").getdata()
            i = 0
            for i in range(height):
                for j in range(width):
                    rgba = data[i * width + j]
                    p = rgba[3] << 24 | rgba[0] << 16 | rgba[1] << 8 | rgba[2]
                    pixels[i][j] = p
        return pixels

# Public method: save

    def save(self, filename):
        """Saves the image to the specified file."""
        if not isinstance(filename, str):
            raise TypeError("save: filename must be a string")
        if self._image_model != "PIL":
            raise Exception("Image scaling is available only if PIL is loaded")
        self._image.save(filename)

# Override method: scale

    def scale(self, sf):
        """Scales the GImage by the specified scale factor."""
        if not _is_number(sf):
            raise TypeError("scale: sf must be a number")
        if self._image_model != "PIL":
            raise Exception("Image scaling is available only if PIL is loaded")
        self._sf *= sf
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Override method: get_type

    def get_type(self):
        """Returns the type of this object."""
        return "GImage"

# Override method: _install

    def _install(self, target, ctm):
        """Installs the GImage in the canvas."""
        gw = target
        tkc = gw._canvas
        pt = ctm.transform(self._x, self._y)
        x = pt._x
        y = pt._y
        ctm = ctm.compose(_GTransform(rotation=self._angle, sf=self._sf))
        img = self._image
        rotation = ctm._rotation % 360
        if ctm._sf != 1:
            w = round(img.width * ctm._sf)
            h = round(img.height * ctm._sf)
            img = img.resize((w, h), Image.LANCZOS)
        if rotation != 0:
            w = img.width 
            h = img.height
            img = img.rotate(rotation, expand=True)
            if rotation > 0 and rotation <= 90:
                theta = math.radians(rotation)
                y -= w * math.sin(theta)
            elif rotation > 90 and rotation <= 180:
                theta = math.radians(rotation - 90)
                x -= w * math.sin(theta)
                y -= h * math.sin(theta) + w * math.cos(theta)
            elif rotation > 180 and rotation <= 270:
                theta = math.radians(rotation - 180)
                x -= h * math.sin(theta) + w * math.cos(theta)
                y -= h * math.cos(theta)
            else:
                theta = math.radians(rotation - 270)
                x -= h * math.cos(theta)            
        self._photo = ImageTk.PhotoImage(img)
        self._tkid = tkc.create_image(x, y,
                                      anchor=tkinter.NW,
                                      image=self._photo)
        self._update_visible()

# Override method: _update_rotation

    def _update_rotation(self):
        """Updates this GImage after a rotation."""
        gw = self._get_window()
        if gw is not None:
            gw._rebuild()

# Static method: get_red

    @staticmethod
    def get_red(pixel):
        """Returns the red component of the pixel."""
        return pixel >> 16 & 0xFF

# Static method: get_green

    @staticmethod
    def get_green(pixel):
        """Returns the green component of the pixel."""
        return pixel >> 8 & 0xFF

# Static method: get_blue

    @staticmethod
    def get_blue(pixel):
        """Returns the blue component of the pixel."""
        return pixel & 0xFF

# Static method: get_alpha

    @staticmethod
    def get_alpha(pixel):
        """Returns the alpha component of the pixel."""
        return pixel >> 24 & 0xFF

# Static method: create_rgb_pixel

    @staticmethod
    def create_rgb_pixel(a1=None, a2=None, a3=None, a4=None, **kw):
        """Creates an rgb pixel from the arguments."""
        if a4 is None:
            a = 0xFF
            r = a1
            g = a2
            b = a3
        else:
            a = a1
            r = a2
            g = a3
            b = a4
        if "alpha" in kw:
            a = kw["alpha"]
        if "red" in kw:
            r = kw["red"]
        if "green" in kw:
            g = kw["green"]
        if "blue" in kw:
            b = kw["blue"]
        return a << 24 | (r & 0xFF) << 16 | (g & 0xFF) << 8 | (b & 0xFF)

# Public method: __str__

    def __str__(self):
        if isinstance(self._image, str):
            return "GImage(\"" + self._source + "\")"
        else:
            return "GImage(<data>)"


# Class: GLabel

class GLabel(GObject):
    """This GObject subclass represents a text string."""

# Constants

    DEFAULT_FONT = "13pt 'Helvetica Neue','Helvetica','Arial','Sans-Serif'"

# Constructor: GLabel

    def __init__(self, text, x=0, y=0):
        """Initializes a GLabel object containing the specified string."""
        if not isinstance(text, str):
            raise TypeError("GLabel: text must be a string")
        if not _is_number(x):
            raise TypeError("GLabel: x must be a number")
        if not _is_number(y):
            raise TypeError("GLabel: y must be a number")
        GObject.__init__(self)
        self._text = text
        self._font = self.DEFAULT_FONT
        self._tk_font = _decode_font(self._font)
        self.set_location(x, y)

# Public method: set_font

    def set_font(self, font):
        """Changes the font used to display the GLabel."""
        if not isinstance(font, str):
            raise TypeError("set_font: font must be a string")
        self._font = font
        self._tk_font = _decode_font(self._font)
        self._update_properties(font=self._tk_font)
        self._update_location()

# Public method: get_font

    def get_font(self):
        """Returns the current font for the GLabel."""
        return self._font

# Public method: set_label

    def set_label(self, text):
        """Changes the string stored within the GLabel object."""
        if not isinstance(text, str):
            raise TypeError("set_label: text must be a string")
        self._text = text
        self._update_properties(text=text)

# Public method: get_label

    def get_label(self):
        """Returns the string displayed by this object."""
        return self._text

# Public method: get_ascent

    def get_ascent(self):
        """Returns the maximum distance strings extend above the baseline."""
        return self._tk_font.metrics("ascent")

# Public method: get_descent

    def get_descent(self):
        """Returns the maximum distance strings descend below the baseline."""
        return self._tk_font.metrics("descent")

# Override method: get_width

    def get_width(self):
        """Returns the width for this GLabel."""
        return self._tk_font.measure(self._text)

# Override method: get_height

    def get_height(self):
        """Returns the height for this GLabel."""
        return self._tk_font.metrics("linespace")

# Override method: get_bounds

    def get_bounds(self):
        """Returns the bounding rectangle for this object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("get_bounds: not defined after rotation")
        return GRectangle(self._x, self._y - self.get_ascent(),
                          self.get_width(), self.get_height())

# Override method: get_type

    def get_type(self):
        """Returns the type of this object."""
        return "GLabel"

# Override method: _update_location

# Implementation notes: _update_location
# --------------------------------------
# This override is necessary to adjust for the baseline.

    def _update_location(self):
        """Updates the location for this GLabel."""
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        coords = tkc.coords(self._tkid)
        offx = 0
        offy = self.get_height() - self.get_ascent()
        gobj = self.get_parent()
        while gobj is not None:
            offx += gobj._x
            offy += gobj._y
            gobj = gobj.get_parent()
        dx = (self._x + offx) - coords[0]
        dy = (self._y + offy) - coords[1]
        tkc.move(self._tkid, dx, dy)

# Override method: _install

    def _install(self, target, ctm):
        """Installs the GLabel in the canvas."""
        gw = target
        tkc = gw._canvas
        self._ctm_base = ctm
        pt = ctm.transform(self._x, self._y)
        dtm = _GTransform(rotation=self._angle, sf=self._sf)
        ctm = ctm.compose(dtm)
        dp = dtm.transform(0, self.get_height() - self.get_ascent())
        x = pt._x + dp._x
        y = pt._y + dp._y
        baseline = y
        if ctm.get_rotation() == 0:
            self._tkid = tkc.create_text(x,
                                         baseline,
                                         text=self._text,
                                         font=self._tk_font,
                                         fill=self._color,
                                         anchor="sw")
        else:
            try:
                self._tkid = tkc.create_text(x,
                                             baseline,
                                             text=self._text,
                                             font=self._tk_font,
                                             fill=self._color,
                                             angle=ctm.get_rotation(),
                                             anchor="sw")
            except:
                raise Exception("GLabel rotation requires tkinter v6")
        self._update_visible()

# Override method: _update_rotation

    def _update_rotation(self):
        """Updates this GLabel after a rotation."""
        gw = self._get_window()
        if gw is None:
            return
        ctm = self._ctm_base
        ctm = ctm.compose(_GTransform(rotation=self._angle, sf=self._sf))
        self._update_properties(angle=ctm.get_rotation())

# Override method: __str__

    def __str__(self):
        return "GLabel(\"" + self._text + "\")"


# Class: GPolygon

class GPolygon(GFillableObject):
    """This GObject subclass represents a polygon bounded by line segments."""

# Constructor: GPolygon

    def __init__(self):
        """Initializes a new empty polygon at the origin."""
        GFillableObject.__init__(self)
        self._cx = None
        self._cy = None
        self._vertices = [ ]

# Public method: add_vertex

    def add_vertex(self, x, y):
        """Adds a vertex at (x, y) relative to the polygon origin."""
        if not _is_number(x):
            raise TypeError("add_vertex: x must be a number")
        if not _is_number(y):
            raise TypeError("add_vertex: y must be a number")
        self._cx = x
        self._cy = y
        self._vertices.append(GPoint(x, y))

# Public method: add_edge

    def add_edge(self, dx, dy):
        """Adds an edge to the polygon using the displacements dx and dy."""
        if not _is_number(dx):
            raise TypeError("add_edge: dx must be a number")
        if not _is_number(dy):
            raise TypeError("add_edge: dy must be a number")
        self.add_vertex(self._cx + dx, self._cy + dy)

# Public method: add_polar_edge

    def add_polar_edge(self, r, theta):
        """Adds an edge to the polygon specified in polar coordinates."""
        if not _is_number(r):
            raise TypeError("add_polar_edge: r must be a number")
        if not _is_number(theta):
            raise TypeError("add_polar_edge: theta must be a number")
        self.add_edge(r * math.cos(theta * math.pi / 180),
                      -r * math.sin(theta * math.pi / 180))

# Public method: get_vertices

    def get_vertices(self):
        """Returns a list of the points in the polygon."""
        return self._vertices

# Public method: get_bounds

    def get_bounds(self):
        """Returns the bounding rectangle for this object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        vertices = [ lctm.transform(v) for v in self._vertices ]
        return GPolygon._polygon_bounds(vertices)

# Public method: contains

    def contains(self, x, y):
        """Returns True if the specified point is inside the object."""
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        if lctm._rotation != 0:
            raise NotImplementedError("contains: not defined after rotation")
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("contains: x must be a number")
        if not _is_number(y):
            raise TypeError("contains: y must be a number")
        ctm = self._ctm_base
        lctm = _GTransform(tx=self._x + ctm._tx,
                           ty=self._y + ctm._ty,
                           rotation=self._angle + ctm._rotation,
                           sf=self._sf * ctm._sf)
        vertices = [ lctm.transform(v) for v in self._vertices ]
        return GPolygon._inside_polygon(x, y, vertices)

# Override method: get_type

    def get_type(self):
        """Returns the type of this object."""
        return "GPolygon"

# Override method: _update_location

    def _update_location(self):
        """Updates the location for this object."""
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        coords = tkc.coords(self._tkid)
        oldx = coords[0]
        oldy = coords[1]
        coords = self._create_coords()
        dx = coords[0] - oldx
        dy = coords[1] - oldy
        tkc.move(self._tkid, dx, dy)

# Override method: _update_rotation

    def _update_rotation(self):
        """Updates this GPolygon after a rotation."""
        gw = self._get_window()
        if gw is None:
            return
        tkc = gw._canvas
        coords = self._create_coords()
        tkc.coords(self._tkid, *coords)

# Override method: _install

    def _install(self, target, ctm):
        """Installs the GPolygon in the canvas."""
        gw = target
        tkc = gw._canvas
        self._ctm_base = ctm
        coords = self._create_coords()
        self._tkid = tkc.create_polygon(*coords, width=self._line_width)
        self._update_color()
        self._update_visible()

# Override method: __str__

    def __str__(self):
        return "GPolygon(" + str(len(self._vertices)) + " vertices)"

# Private method: _create_coords

    def _create_coords(self):
        ctm = self._ctm_base
        ctm = ctm.compose(_GTransform(self._x, self._y,
                                      rotation=self._angle, sf=self._sf))
        coords = [ ]
        for pt in self._vertices:
            tp = ctm.transform(pt)
            coords.append(tp._x)
            coords.append(tp._y)
        return coords

# Private static method: _polygon_bounds

    @staticmethod
    def _polygon_bounds(vertices):
        x_min = 0
        y_min = 0
        x_max = 0
        y_max = 0
        for i in range(len(vertices)):
            x = vertices[i]._x
            y = vertices[i]._y
            if i == 0 or x < x_min:
                x_min = x
            if i == 0 or y < y_min:
                y_min = y
            if i == 0 or x > x_max:
                x_max = x
            if i == 0 or y > y_max:
                y_max = y
        return GRectangle(x_min, y_min, x_max - x_min, y_max - y_min)

# Private static method: _inside_polygon

    @staticmethod
    def _inside_polygon(x, y, vertices):
        crossings = 0
        n = len(vertices)
        if n < 2:
            return False
        if vertices[0] == vertices[n - 1]:
            n = n - 1
        x0 = vertices[0]._x
        y0 = vertices[0]._y
        for i in range(1, n + 1):
            x1 = vertices[i % n]._x
            y1 = vertices[i % n]._y
            if (y0 > y) != (y1 > y):
                if x - x0 < (x1 - x0) * (y - y0) / (y1 - y0):
                    crossings = crossings + 1
            x0 = x1
            y0 = y1
        return (crossings % 2 == 1)

# Class: GPoint

class GPoint:
    """This class represents a location on the graphics plane."""

# Constructor: GPoint

    def __init__(self, x=0, y=0):
        """Initializes a point with the specified coordinates."""
        if not _is_number(x):
            raise TypeError("GPoint: x must be a number")
        if not _is_number(y):
            raise TypeError("GPoint: y must be a number")
        self._x = x
        self._y = y

# Public method: get_x

    def get_x(self):
        """Returns the x component of the point"""
        return self._x

# Public method: get_y

    def get_y(self):
        """Returns the y component of the point."""
        return self._y

# Public method: __str__

    def __str__(self):
        """Returns the string representation of a point."""
        return "(" + str(self._x) + ", " + str(self._y) + ")"

# Public method: __eq__

    def __eq__(self, other):
        """Returns a Boolean indicating whether two points are equal."""
        if isinstance(other, GPoint):
            return self._x == other._x and self._y == other._y
        return False


# Class: GDimension

class GDimension:
    """This class represents the size of a graphical object."""

# Constructor: GDimension

    def __init__(self, width=0.0, height=0.0):
        """Initializes a GDimension object with the specified size."""
        if not _is_number(width):
            raise TypeError("GDimension: width must be a number")
        if not _is_number(height):
            raise TypeError("GDimension: height must be a number")
        self._width = width
        self._height = height

# Public method: get_width

    def get_width(self):
        """Returns the width component of the GDimension."""
        return self._width

# Public method: get_height

    def get_height(self):
        """Returns the height component of the GDimension."""
        return self._height

# Public method: __str__

    def __str__(self):
        return "(" + str(self._width) + ", " + str(self._height) + ")"

# Public method: __eq__

    def __eq__(self, other):
        if isinstance(other, GDimension):
            return (self._width == other._width and
                    self._height == other._height)
        return False


# Class: GRectangle

class GRectangle:
    """This type represents the bounding box of a graphical object."""

# Constructor: GRectangle

    def __init__(self, x=0.0, y=0.0, width=0.0, height=0.0):
        """Initializes a GRectangle object with the specified fields."""
        if not _is_number(x):
            raise TypeError("GRectangle: x must be a number")
        if not _is_number(y):
            raise TypeError("GRectangle: y must be a number")
        if not _is_number(width):
            raise TypeError("GRectangle: width must be a number")
        if not _is_number(height):
            raise TypeError("GRectangle: height must be a number")
        self._x = x
        self._y = y
        self._width = width
        self._height = height

# Public method: get_x

    def get_x(self):
        """Returns the x component of the upper left corner."""
        return self._x

# Public method: get_y

    def get_y(self):
        """Returns the x component of the upper left corner."""
        return self._y

# Public method: get_width

    def get_width(self):
        """Returns the width component of the GRectangle."""
        return self._width

# Public method: get_height

    def get_height(self):
        """Returns the width component of the GRectangle."""
        return self._height

# Public method: is_empty

    def is_empty(self):
        """Returns True if the rectangle is empty."""
        return self._width <= 0 or self._height <= 0

# Public method: add

    def add(self, x, y=None):
        """Adds a GPoint or x/y pair to this GRectangle."""
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("add: x must be a number")
        if not _is_number(y):
            raise TypeError("add: y must be a number")
        if x < self._x:
            self._width += self._x - x
            self._x = x
        elif x > self._x + self._width:
            self._width = x - self._x
        if y < self._y:
            self._height += self._y - y
            self._y = y
        elif y > self._y + self._height:
            self._height = y - self._y
        
# Public method: contains

    def contains(self, x, y):
        """Returns True if the specified point is inside the rectangle."""
        if isinstance(x, GPoint):
            x, y = x.get_x(), x.get_y()
        elif isinstance(x, dict):
            x, y = x["x"], x["y"]
        elif isinstance(x, tuple):
            x, y = x
        if not _is_number(x):
            raise TypeError("contains: x must be a number")
        if not _is_number(y):
            raise TypeError("contains: y must be a number")
        return (x >= self._x and
                y >= self._y and
                x < self._x + self._width and
                y < self._y + self._height)

# Public method: __str__

    def __str__(self):
        return ("(" + str(self._x) + ", " + str(self._y) + ", " +
                str(self._width) + ", " + str(self._height) + ")")

# Public method: __eq__

    def __eq__(self, other):
        if isinstance(other, GRectangle):
            return (self._x == other._x and
                    self._y == other._y and
                    self._width == other._width and
                    self._height == other._height)
        return False


# Class: GTimer

class GTimer:
    """This type implements a timer running in the window."""

# Constructor: GTimer

    def __init__(self, gw, fn, delay):
        """Creates a new GTimer that calls fn after the specified delay."""
        if not isinstance(gw, GWindow):
            raise TypeError("GTimer: gw must be a GWindow")
        if not callable(fn):
            raise TypeError("GTimer: fn must be callable")
        if not _is_number(delay):
            raise TypeError("GTimer: delay must be a number")
        self._gw = gw
        self._fn = fn
        self._delay = delay
        self._repeats = False
        self._after_id = None
        gw._timers.append(self)

# Public method: set_repeats

    def set_repeats(self, flag):
        """Determines whether the timer should repeat."""
        self._repeats = flag

# Public method: set_delay

    def set_delay(self, delay):
        """Sets the delay time for this timer."""
        if not _is_number(delay):
            raise TypeError("set_delay: delay must be a number")
        self._delay = delay

# Public method: start

    def start(self):
        """Starts the timer."""
        tkc = self._gw._canvas
        self._after_id = tkc.after(self._delay, self._timer_ticked)

# Public method: stop

    def stop(self):
        """Stops the timer."""
        if self._after_id is not None:
            tkc = self._gw._canvas
            tkc.after_cancel(self._after_id)
            self._after_id = None

# Private method: _timer_ticked

    def _timer_ticked(self):
        self._fn()
        if self._repeats and self._after_id is not None:
            tkc = self._gw._canvas
            self._after_id = tkc.after(self._delay, self._timer_ticked)

# Class: GEvent

class GEvent(object):
    """This type is the abstract superclass for all graphical events."""

# Constructor: GEvent

    def __init__(self):
        """Creates a new GEvent object (called only by subclasses)."""

# Public abstract method: get_source

    def get_source(self):
        """Returns the source of this event."""
        raise Exception("get_source is not defined in the base class")

# Class: GMouseEvent

class GMouseEvent(GEvent):
    """This class maintains the data for a mouse event."""

# Constructor: GMouseEvent

    def __init__(self, tke):
        """Creates a new GMouseEvent from the corresponding tkinter event."""
        self._x = tke.x
        self._y = tke.y

# Public method: get_x

    def get_x(self):
        """Returns the x coordinate of the mouse event."""
        return self._x

# Public method: get_y

    def get_y(self):
        """Returns the y coordinate of the mouse event."""
        return self._y

# Override method: get_source

    def get_source(self):
        """Returns the source of the mouse event."""
        return tkinter._root


# Class: GKeyEvent

class GKeyEvent(GEvent):
    """This class maintains the data for a key event."""

# Constructor: GKeyEvent

    def __init__(self, tke):
        """Creates a new GKeyEvent from the corresponding tkinter event."""
        keysym = tke.keysym.upper()
        if len(keysym) > 1:
            underscore = keysym.find("_")
            if underscore > 0:
                self._key = "<" + keysym[0:underscore] + ">"
            else:
                self._key = "<" + keysym + ">"
        else:
            self._key = tke.char

# Public method: get_key

    def get_key(self):
        """Returns the character that triggered the event."""
        return self._key

# Override method: get_source

    def get_source(self):
        """Returns the source of the key event."""
        return tkinter._root


# Class: GState

# Implementation notes: GState
# ----------------------------
# This class implements a simple record type that allows clients to
# define and maintain attributes.  The purpose of this class it to
# allow callback functions to share state with the calling environment.
# Although the closure of the callback function makes it possible to
# read the contents of variables defined in the caller, Python's
# implicit declaration rule makes it impossible to reassign new
# values.  Having this class makes it possible to avoid introducing
# the nonlocal declaration.

class GState:
    """This class implements a simple record type for clients."""

# Constructor: GState

    def __init__(self):
        """Creates a new GState with no fields."""
        pass

# Override method: __str__

    def __str__(self):
        s = ""
        for key in sorted(self.__dict__):
            if not key.startswith("_"):
                if len(s) > 0:
                    s += ", "
                s += str(key) + ":" + repr(self.__dict__[key])
        return "GState(" + s + ")"

# Private function: _get_screen_width

def _get_screen_width():
    """Returns the width of the entire display screen."""
    return tkinter._root.winfo_screenwidth()

# Private function: _get_screen_height

def _get_screen_height():
    """Returns the height of the entire display screen."""
    return tkinter._root.winfo_screenheight()

# Private function: _convert_color_to_rgb

def _convert_color_to_rgb(color_name):
    """Converts a color name into an int that encodes the rgb components."""
    if color_name == "":
        return -1
    if color_name[0] == "#":
        color_name = "0x" + color_name[1:]
        return int(color_name, 16)
    name = _canonical_color_name(color_name)
    if name not in COLOR_TABLE:
        raise Exception("set_color: Illegal color - " + color_name)
    return COLOR_TABLE[name]

# Private function: _convert_rgb_to_color

def _convert_rgb_to_color(rgb):
    """Converts an rgb value into a name in the form "#rrggbb"."""
    hex_string = hex(0xFF000000 | rgb)
    return "#" + hex_string[4:].upper()

# Private function: _exit_graphics

def _exit_graphics():
    """Closes all graphics windows and exits from the application."""
    sys.exit()

# Private function: _get_program_name

def _get_program_name():
    """Returns the name of the program."""
    name = None
    try:
        stack = inspect.stack()
        i = len(stack) - 1
        while i >= 0 and name is None:
            code = stack[i].code_context[stack[i].index]
            rf = code.find("runfile(")
            if rf >= 0:
                start = rf + len("runfile('")
                finish = code.find("'", start)
                name = code[start:finish]
            else:
                i -= 1
        if name is None:
            i = len(stack) - 1
            while i >= 0 and name is None:
                if stack[i].filename:
                    name = stack[i].filename
                else:
                    i -= 1
    except Exception:
        return "Graphics Window"
    if name is None:
        return "Graphics Window"
    name = name[name.rfind("/") + 1:]
    dot = name.find(".")
    if dot != -1:
        name = name[:dot]
    return name

# Private function: _canonical_color_name

def _canonical_color_name(str):
    result = ""
    for char in str:
        if not char.isspace() and char != "_":
            result += char.lower()
    return result

# Private function: _is_number

def _is_number(x):
    """Returns True if x is an int or a float."""
    return isinstance(x, int) or isinstance(x, float)

# Private function: _dsq

def _dsq(x0, y0, x1, y1):
    """Returns the square of the distance between two points."""
    return (x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0)

# Private function: _decode_font

def _decode_font(name):
    """Parses a font string into a tkinter Font object."""
    font = _parse_js_font(name)
    if font is None:
        font = _parse_java_font(name)
    return font

def _parse_js_font(name):
    """Attempts to parse a font specification as a JavaScript font."""
    name = name.lower().strip()
    family = None
    size = -1
    weight = "normal"
    slant = "roman"
    start = 0
    while size == -1:
        sp = name.find(" ", start)
        if sp == -1:
            return None
        token = name[start:sp]
        start = sp + 1
        if token == "bold":
            weight = "bold"
        elif token == "italic":
            slant = "italic"
        elif token[0].isdigit():
            size = _parse_js_units(token)
            if size == -1:
                return None
        else:
            return None
    families = name[start:].split(",")
    if len(families) == 0:
        return None
    for family in families:
        if family.startswith("'") or family.startswith("\""):
            family = family[1:-1]
        # // Add code to test for existence of font family
        return tk_font.Font(family=family, size=-size,
                            weight=weight, slant=slant)
    return None

def _parse_java_font(name):
    """Attempts to parse a font specification as a Java font."""
    components = name.lower().strip().split("-")
    family = components[0]
    weight = "normal"
    slant = "roman"
    if components[1][0].isdigit():
        size = components[1]
    else:
        size = components[2]
        if "bold" in components[1]:
            weight = "bold"
        if "italic" in components[1]:
            slant = "italic"
    return tk_font.Font(family=family, size=-size,
                        weight=weight, slant=slant)

def _parse_js_units(spec):
    ux = len(spec)
    while ux > 0 and spec[ux - 1] >= "A":
        ux = ux - 1
    if ux == 0 or ux == len(spec):
        return -1
    value = float(spec[:ux])
    units = spec[ux:]
    if units == "em":
        return round(16 * value)
    elif units == "pt":
        return round(value / 0.75)
    else:
        return round(value)

# Private class: _GTransform

class _GTransform:

    def __init__(self, tx=0.0, ty=0.0, rotation=0.0, sf=1.0):
        self._tx = tx
        self._ty = ty
        self._rotation = rotation
        self._sf = sf

    def __str__(self):
       return "{{tx:{} ty:{} rot:{} sf:{}}}".format(self._tx, self._ty,
                                                    self._rotation, self._sf)

    def get_tx(self):
        return self._tx

    def get_ty(self):
        return self._ty

    def get_rotation(self):
        return self._rotation

    def get_sf(self):
        return self._sf

    def transform(self, a1, a2=None):
        if a2 is None:
            x0 = a1.get_x()
            y0 = a1.get_y()
        else:
            x0 = a1
            y0 = a2
        if self._rotation == 0:
            x1 = self._tx + self._sf * x0
            y1 = self._ty + self._sf * y0
        else:
            ct = math.cos(math.radians(self._rotation))
            st = math.sin(math.radians(self._rotation))
            x1 = self._tx + self._sf * (x0 * ct + y0 * st)
            y1 = self._ty + self._sf * (y0 * ct - x0 * st)
        return GPoint(x1, y1)

    def itransform(self, a1, a2=None):
        if a2 is None:
            x0 = a1.get_x()
            y0 = a1.get_y()
        else:
            x0 = a1
            y0 = a2
        if self._rotation == 0:
            x1 = (x0 - self._tx) / self._sf
            y1 = (y0 - self._ty) / self._sf
        else:
            ct = math.cos(math.radians(-self._rotation))
            st = math.sin(math.radians(-self._rotation))
            u1 = (x0 - self._tx) / self._sf
            v1 = (y0 - self._ty) / self._sf
            x1 = v1 * st + u1 * ct
            y1 = v1 * ct - u1 * st
        return GPoint(x1, y1)

    def compose(self, transform):
        return _GTransform(self._tx + transform.get_tx(),
                           self._ty + transform.get_ty(),
                           rotation=self._rotation + transform._rotation,
                           sf=self._sf * transform._sf)

# Private class: _EventManager

class _EventManager:

    CLICK_MAX_DISTANCE = 2
    CLICK_MAX_DELAY = 0.5
    DOUBLE_CLICK_TIME = 0.5

    def __init__(self, gw):
        self._gw = gw
        self._down_x = -1
        self._down_y = -1
        self._press_handler = None
        self._release_handler = None
        self._motion_handler = None
        self._drag_handler = None
        self._key_handler = None
        self._click_listeners = [ ]
        self._dblclick_listeners = [ ]
        self._mousedown_listeners = [ ]
        self._mouseup_listeners = [ ]
        self._mousemove_listeners = [ ]
        self._drag_listeners = [ ]
        self._key_listeners = [ ]
        self._down_x = None
        self._down_y = None
        self._down_time = None
        self._last_click_time = None

    def _press_action(self, tke):
        self._down_x = tke.x
        self._down_y = tke.y
        self._down_time = time.time()
        e = GMouseEvent(tke)
        for fn in self._mousedown_listeners:
            fn(e)

    def _release_action(self, tke):
        e = GMouseEvent(tke)
        for fn in self._mouseup_listeners:
            fn(e)
        if abs(self._down_x - e._x) <= self.CLICK_MAX_DISTANCE:
            if abs(self._down_y - e._y) <= self.CLICK_MAX_DISTANCE:
                t = time.time()
                if t - self._down_time < self.CLICK_MAX_DELAY:
                    for fn in self._click_listeners:
                        fn(e)
                    last_click = self._last_click_time
                    self._last_click_time = t
                    if last_click is not None:
                        if t - last_click < self.DOUBLE_CLICK_TIME:
                            for fn in self._dblclick_listeners:
                                fn(e)
                            self._last_click_time = None

    def _motion_action(self, tke):
        e = GMouseEvent(tke)
        for fn in self._mousemove_listeners:
            fn(e)

    def _drag_action(self, tke):
        e = GMouseEvent(tke)
        for fn in self._drag_listeners:
            fn(e)

    def _key_action(self, tke):
        e = GKeyEvent(tke)
        for fn in self._key_listeners:
            fn(e)

    def add_event_listener(self, type, fn):
        tkc = self._gw._canvas
        if type == "click":
            if self._press_handler is None:
                self._press_handler = self._press_action
                tkc.bind("<ButtonPress-1>", self._press_handler)
            if self._release_handler is None:
                self._release_handler = self._release_action
                tkc.bind("<ButtonRelease-1>", self._release_handler)
            if fn not in self._click_listeners:
                self._click_listeners.append(fn)
        elif type == "mousedown" or type == "press":
            if self._press_handler is None:
                self._press_handler = self._press_action
                tkc.bind("<ButtonPress-1>", self._press_handler)
            if fn not in self._mousedown_listeners:
                self._mousedown_listeners.append(fn)
        elif type == "mouseup" or type == "release":
            if self._release_handler is None:
                self._release_handler = self._release_action
                tkc.bind("<ButtonRelease-1>", self._release_handler)
            if fn not in self._mouseup_listeners:
                self._mouseup_listeners.append(fn)
        elif type == "dblclick":
            if self._press_handler is None:
                self._press_handler = self._press_action
                tkc.bind("<ButtonPress-1>", self._press_handler)
            if self._release_handler is None:
                self._release_handler = self._release_action
                tkc.bind("<ButtonRelease-1>", self._release_handler)
            if fn not in self._dblclick_listeners:
                self._dblclick_listeners.append(fn)
        elif type == "mousemove" or type == "move":
            if self._motion_handler is None:
                self._motion_handler = self._motion_action
                tkc.bind("<Motion>", self._motion_handler)
            if fn not in self._mousemove_listeners:
                self._mousemove_listeners.append(fn)
        elif type == "drag":
            if self._drag_handler is None:
                self._drag_handler = self._drag_action
                tkc.bind("<B1-Motion>", self._drag_handler)
            if fn not in self._drag_listeners:
                self._drag_listeners.append(fn)
        elif type == "key":
            if self._key_handler is None:
                self._key_handler = self._key_action
                tkc.bind("<Key>", self._key_handler)
                tkc.focus_set()
            if fn not in self._key_listeners:
                self._key_listeners.append(fn)
        else:
            raise Exception("Illegal event type: " + type)

# Constants

__LINE_TOLERANCE__ = 2
__ARC_TOLERANCE__ = 2

# Color table

COLOR_TABLE = {
    "aliceblue": 0xF0F8FF,
    "antiquewhite": 0xFAEBD7,
    "aqua": 0x00FFFF,
    "aquamarine": 0x7FFFD4,
    "azure": 0xF0FFFF,
    "beige": 0xF5F5DC,
    "bisque": 0xFFE4C4,
    "black": 0x000000,
    "blanchedalmond": 0xFFEBCD,
    "blue": 0x0000FF,
    "blueviolet": 0x8A2BE2,
    "brown": 0xA52A2A,
    "burlywood": 0xDEB887,
    "cadetblue": 0x5F9EA0,
    "chartreuse": 0x7FFF00,
    "chocolate": 0xD2691E,
    "coral": 0xFF7F50,
    "cornflowerblue": 0x6495ED,
    "cornsilk": 0xFFF8DC,
    "crimson": 0xDC143C,
    "cyan": 0x00FFFF,
    "darkblue": 0x00008B,
    "darkcyan": 0x008B8B,
    "darkgoldenrod": 0xB8860B,
    "darkgray": 0xA9A9A9,
    "darkgrey": 0xA9A9A9,
    "darkgreen": 0x006400,
    "darkkhaki": 0xBDB76B,
    "darkmagenta": 0x8B008B,
    "darkolivegreen": 0x556B2F,
    "darkorange": 0xFF8C00,
    "darkorchid": 0x9932CC,
    "darkred": 0x8B0000,
    "darksalmon": 0xE9967A,
    "darkseagreen": 0x8FBC8F,
    "darkslateblue": 0x483D8B,
    "darkslategray": 0x2F4F4F,
    "darkslategrey": 0x2F4F4F,
    "darkturquoise": 0x00CED1,
    "darkviolet": 0x9400D3,
    "deeppink": 0xFF1493,
    "deepskyblue": 0x00BFFF,
    "dimgray": 0x696969,
    "dimgrey": 0x696969,
    "dodgerblue": 0x1E90FF,
    "firebrick": 0xB22222,
    "floralwhite": 0xFFFAF0,
    "forestgreen": 0x228B22,
    "fuchsia": 0xFF00FF,
    "gainsboro": 0xDCDCDC,
    "ghostwhite": 0xF8F8FF,
    "gold": 0xFFD700,
    "goldenrod": 0xDAA520,
    "gray": 0x808080,
    "grey": 0x808080,
    "green": 0x008000,
    "greenyellow": 0xADFF2F,
    "honeydew": 0xF0FFF0,
    "hotpink": 0xFF69B4,
    "indianred": 0xCD5C5C,
    "indigo": 0x4B0082,
    "ivory": 0xFFFFF0,
    "khaki": 0xF0E68C,
    "lavender": 0xE6E6FA,
    "lavenderblush": 0xFFF0F5,
    "lawngreen": 0x7CFC00,
    "lemonchiffon": 0xFFFACD,
    "lightblue": 0xADD8E6,
    "lightcoral": 0xF08080,
    "lightcyan": 0xE0FFFF,
    "lightgoldenrodyellow": 0xFAFAD2,
    "lightgray": 0xD3D3D3,
    "lightgrey": 0xD3D3D3,
    "lightgreen": 0x90EE90,
    "lightpink": 0xFFB6C1,
    "lightsalmon": 0xFFA07A,
    "lightseagreen": 0x20B2AA,
    "lightskyblue": 0x87CEFA,
    "lightslategray": 0x778899,
    "lightslategrey": 0x778899,
    "lightsteelblue": 0xB0C4DE,
    "lightyellow": 0xFFFFE0,
    "lime": 0x00FF00,
    "limegreen": 0x32CD32,
    "linen": 0xFAF0E6,
    "magenta": 0xFF00FF,
    "maroon": 0x800000,
    "mediumaquamarine": 0x66CDAA,
    "mediumblue": 0x0000CD,
    "mediumorchid": 0xBA55D3,
    "mediumpurple": 0x9370DB,
    "mediumseagreen": 0x3CB371,
    "mediumslateblue": 0x7B68EE,
    "mediumspringgreen": 0x00FA9A,
    "mediumturquoise": 0x48D1CC,
    "mediumvioletred": 0xC71585,
    "midnightblue": 0x191970,
    "mintcream": 0xF5FFFA,
    "mistyrose": 0xFFE4E1,
    "moccasin": 0xFFE4B5,
    "navajowhite": 0xFFDEAD,
    "navy": 0x000080,
    "oldlace": 0xFDF5E6,
    "olive": 0x808000,
    "olivedrab": 0x6B8E23,
    "orange": 0xFFA500,
    "orangered": 0xFF4500,
    "orchid": 0xDA70D6,
    "palegoldenrod": 0xEEE8AA,
    "palegreen": 0x98FB98,
    "paleturquoise": 0xAFEEEE,
    "palevioletred": 0xDB7093,
    "papayawhip": 0xFFEFD5,
    "peachpuff": 0xFFDAB9,
    "peru": 0xCD853F,
    "pink": 0xFFC0CB,
    "plum": 0xDDA0DD,
    "powderblue": 0xB0E0E6,
    "purple": 0x800080,
    "rebeccapurple": 0x663399,
    "red": 0xFF0000,
    "rosybrown": 0xBC8F8F,
    "royalblue": 0x4169E1,
    "saddlebrown": 0x8B4513,
    "salmon": 0xFA8072,
    "sandybrown": 0xF4A460,
    "seagreen": 0x2E8B57,
    "seashell": 0xFFF5EE,
    "sienna": 0xA0522D,
    "silver": 0xC0C0C0,
    "skyblue": 0x87CEEB,
    "slateblue": 0x6A5ACD,
    "slategray": 0x708090,
    "slategrey": 0x708090,
    "snow": 0xFFFAFA,
    "springgreen": 0x00FF7F,
    "steelblue": 0x4682B4,
    "tan": 0xD2B48C,
    "teal": 0x008080,
    "thistle": 0xD8BFD8,
    "tomato": 0xFF6347,
    "turquoise": 0x40E0D0,
    "violet": 0xEE82EE,
    "wheat": 0xF5DEB3,
    "white": 0xFFFFFF,
    "whitesmoke": 0xF5F5F5,
    "yellow": 0xFFFF00,
    "yellowgreen": 0x9ACD32,
    "color.black": 0x000000,
    "color.darkgray": 0x595959,
    "color.gray": 0x999999,
    "color.lightgray": 0xBFBFBF,
    "color.white": 0xFFFFFF,
    "color.red": 0xFF0000,
    "color.yellow": 0xFFFF00,
    "color.green": 0x00FF00,
    "color.cyan": 0x00FFFF,
    "color.blue": 0x0000FF,
    "color.magenta": 0xFF00FF,
    "color.orange": 0xFFC800,
    "color.pink": 0xFFAFAF
}

def enable_camel_case_names():
    """Enables camel-case names for backward compatibility."""
    GWindow.eventLoop = GWindow.event_loop
    GWindow.requestFocus = GWindow.request_focus
    GWindow.getWidth = GWindow.get_width
    GWindow.getHeight = GWindow.get_height
    GWindow.addEventListener = GWindow.add_event_listener
    GWindow.setWindowTitle = GWindow.set_window_title
    GWindow.getWindowTitle = GWindow.get_window_title
    GWindow.getElementAt = GWindow.get_element_at
    GWindow.createTimer = GWindow.create_timer
    GWindow.setTimeout = GWindow.set_timeout
    GWindow.setInterval = GWindow.set_interval
    GWindow.getProgramName = GWindow.get_program_name
    GWindow.getScreenWidth = GWindow.get_screen_width
    GWindow.getScreenHeight = GWindow.get_screen_height
    GWindow.convertColorToRGB = GWindow.convert_color_to_rgb
    GWindow.convertRGBToColor = GWindow.convert_rgb_to_color
    GObject.getX = GObject.get_x
    GObject.getY = GObject.get_y
    GObject.getLocation = GObject.get_location
    GObject.setLocation = GObject.set_location
    GObject.movePolar = GObject.move_polar
    GObject.getWidth = GObject.get_width
    GObject.getHeight = GObject.get_height
    GObject.getSize = GObject.get_size
    GObject.setLineWidth = GObject.set_line_width
    GObject.getLineWidth = GObject.get_line_width
    GObject.setColor = GObject.set_color
    GObject.getColor = GObject.get_color
    GObject.setVisible = GObject.set_visible
    GObject.isVisible = GObject.is_visible
    GObject.sendForward = GObject.send_forward
    GObject.sendToFront = GObject.send_to_front
    GObject.sendBackward = GObject.send_backward
    GObject.sendToBack = GObject.send_to_back
    GObject.getParent = GObject.get_parent
    GFillableObject.setFilled = GFillableObject.set_filled
    GFillableObject.isFilled = GFillableObject.is_filled
    GFillableObject.setFillColor = GFillableObject.set_fill_color
    GFillableObject.getFillColor = GFillableObject.get_fill_color
    GRect.setSize = GRect.set_size
    GRect.setBounds = GRect.set_bounds
    GRect.getBounds = GRect.get_bounds
    GRect.getType = GRect.get_type
    GOval.setSize = GOval.set_size
    GOval.setBounds = GOval.set_bounds
    GOval.getBounds = GOval.get_bounds
    GOval.getType = GOval.get_type
    GCompound.removeAll = GCompound.remove_all
    GCompound.getElementAt = GCompound.get_element_at
    GCompound.getElementCount = GCompound.get_element_count
    GCompound.getElement = GCompound.get_element
    GCompound.getBounds = GCompound.get_bounds
    GCompound.getType = GCompound.get_type
    GArc.setStartAngle = GArc.set_start_angle
    GArc.getStartAngle = GArc.get_start_angle
    GArc.setSweepAngle = GArc.set_sweep_angle
    GArc.getSweepAngle = GArc.get_sweep_angle
    GArc.getStartPoint = GArc.get_start_point
    GArc.getEndPoint = GArc.get_end_point
    GArc.setFrameRectangle = GArc.set_frame_rectangle
    GArc.getFrameRectangle = GArc.get_frame_rectangle
    GArc.setFilled = GArc.set_filled
    GArc.getBounds = GArc.get_bounds
    GArc.getType = GArc.get_type
    GLine.setStartPoint = GLine.set_start_point
    GLine.getStartPoint = GLine.get_start_point
    GLine.setEndPoint = GLine.set_end_point
    GLine.getEndPoint = GLine.get_end_point
    GLine.getType = GLine.get_type
    GImage.getBounds = GImage.get_bounds
    GImage.getPixelArray = GImage.get_pixel_array
    GImage.getType = GImage.get_type
    GImage.getRed = GImage.get_red
    GImage.getGreen = GImage.get_green
    GImage.getBlue = GImage.get_blue
    GImage.getAlpha = GImage.get_alpha
    GImage.createRGBPixel = GImage.create_rgb_pixel
    GLabel.setFont = GLabel.set_font
    GLabel.getFont = GLabel.get_font
    GLabel.setLabel = GLabel.set_label
    GLabel.getLabel = GLabel.get_label
    GLabel.getAscent = GLabel.get_ascent
    GLabel.getDescent = GLabel.get_descent
    GLabel.getWidth = GLabel.get_width
    GLabel.getHeight = GLabel.get_height
    GLabel.getBounds = GLabel.get_bounds
    GLabel.getType = GLabel.get_type
    GPolygon.addVertex = GPolygon.add_vertex
    GPolygon.addEdge = GPolygon.add_edge
    GPolygon.addPolarEdge = GPolygon.add_polar_edge
    GPolygon.getVertices = GPolygon.get_vertices
    GPolygon.getBounds = GPolygon.get_bounds
    GPolygon.getType = GPolygon.get_type
    GPoint.getX = GPoint.get_x
    GPoint.getY = GPoint.get_y
    GDimension.getWidth = GDimension.get_width
    GDimension.getHeight = GDimension.get_height
    GRectangle.getX = GRectangle.get_x
    GRectangle.getY = GRectangle.get_y
    GRectangle.getWidth = GRectangle.get_width
    GRectangle.getHeight = GRectangle.get_height
    GRectangle.isEmpty = GRectangle.is_empty
    GMouseEvent.getX = GMouseEvent.get_x
    GMouseEvent.getY = GMouseEvent.get_y
    GMouseEvent.getSource = GMouseEvent.get_source
    GKeyEvent.getKey = GKeyEvent.get_key
    GKeyEvent.getSource = GKeyEvent.get_source

enable_camel_case_names()

# Allow British spelling

def enable_british_spelling():
    """Enables British spelling."""
    GWindow.convert_colour_to_rgb = GWindow.convert_color_to_rgb
    GWindow.convert_rgb_to_colour = GWindow.convert_rgb_to_color
    GWindow.convertColourToRGB = GWindow.convert_color_to_rgb
    GWindow.convertRGBToColour = GWindow.convert_rgb_to_color
    GObject.set_colour = GObject.set_color
    GObject.get_colour = GObject.get_color
    GObject.setColour = GObject.set_color
    GObject.getColour = GObject.get_color
    GFillableObject.set_fill_colour = GFillableObject.set_fill_color
    GFillableObject.get_fill_colour = GFillableObject.get_fill_color
    GFillableObject.setFillColour = GFillableObject.set_fill_color
    GFillableObject.getFillColour = GFillableObject.get_fill_color

enable_british_spelling()

# Check for successful compilation

if __name__ == "__main__":
    print("pgl.py compiled successfully")
