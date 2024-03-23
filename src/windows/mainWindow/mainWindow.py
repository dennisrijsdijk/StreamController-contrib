"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio
GLib.threads_init()

# Import Python modules
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.elements.leftArea import LeftArea
from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar
from src.windows.mainWindow.headerBar import HeaderBar
from GtkHelper.GtkHelper import get_deepest_focused_widget, get_deepest_focused_widget_with_attr
from src.windows.mainWindow.elements.NoPagesError import NoPagesError
from src.windows.mainWindow.elements.NoDecksError import NoDecksError
from src.windows.mainWindow.deckSwitcher import DeckSwitcher
from src.windows.mainWindow.elements.PageSelector import PageSelector
from src.windows.mainWindow.elements.HeaderHamburgerMenuButton import HeaderHamburgerMenuButton


# Import globals
import globals as gl

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, deck_manager, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager

        # Store copied stuff
        self.key_dict = {}

        # Add tasks to run if build is complete
        self.on_finished: list = []

        self.build()
        self.init_actions()

        self.set_size_request(1000, 900)
        self.connect("close-request", self.on_close)

    def on_close(self, *args, **kwargs):
        self.hide()
        return True

    @log.catch
    def build(self):
        log.trace("Building main window")
        self.split_view = Adw.NavigationSplitView()
        self.set_content(self.split_view)

        # Add a main stack containing the normal ui and error pages
        self.main_stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.main_content_page = Adw.NavigationPage(title="StreamController", child=self.main_stack)

        # Add the main stack as the content widget of the split view
        self.split_view.set_content(self.main_content_page)
        self.split_view.set_show_content(self.main_content_page)

        # Main toast
        self.toast_overlay = Adw.ToastOverlay()
        self.main_stack.add_titled(self.toast_overlay, "main", "Main")

        # Add a box for the main content (right side)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.toast_overlay.set_child(self.main_box)

        self.leftArea = LeftArea(self, deck_manager=self.deck_manager, margin_end=3, width_request=500, margin_bottom=10)
        self.main_box.append(self.leftArea)

        self.sidebar = Sidebar(main_window=self, margin_start=4, width_request=300, margin_end=4)
        # self.mainPaned.set_end_child(self.sidebar)
        self.split_view.set_sidebar(self.sidebar)
        self.split_view.set_sidebar_width_fraction(0.4)
        self.split_view.set_min_sidebar_width(450)
        self.split_view.set_max_sidebar_width(600)

        # Add header
        self.header = Adw.HeaderBar(css_classes=["flat"], show_back_button=False)
        self.main_box.prepend(self.header)

        # Add deck switcher to the header bar
        self.deck_switcher = DeckSwitcher(self)
        self.deck_switcher.switcher.set_stack(self.leftArea.deck_stack)
        self.header.set_title_widget(self.deck_switcher)

        # Add menu button to the header bar
        self.menu_button = HeaderHamburgerMenuButton(main_window=self)
        self.header.pack_end(self.menu_button)

        # Add sidebar toggle button to the header bar
        self.sidebar_toggle_button = Gtk.ToggleButton(icon_name="sidebar", active=True)
        self.sidebar_toggle_button.connect("toggled", self.on_toggle_sidebar)
        self.header.pack_start(self.sidebar_toggle_button)


        # Error pages
        self.no_pages_error = NoPagesError()
        self.main_stack.add_titled(self.no_pages_error, "no-pages-error", "No Pages Error")

        self.no_decks_error = NoDecksError()
        self.main_stack.add_titled(self.no_decks_error, "no-decks-error", "No Decks Error")

        self.do_after_build_tasks()
        self.check_for_errors()
        

    def on_toggle_sidebar(self, button):
        if button.get_active():
            self.split_view.set_collapsed(False)
        else:
            self.split_view.set_collapsed(True)

    def init_actions(self):
        # Copy paste actions
        self.copy_action = Gio.SimpleAction.new("copy", None)
        self.cut_action = Gio.SimpleAction.new("cut", None)
        self.paste_action = Gio.SimpleAction.new("paste", None)
        self.remove_action = Gio.SimpleAction.new("remove", None)

        # Connect actions
        self.copy_action.connect("activate", self.on_copy)
        self.cut_action.connect("activate", self.on_cut)
        self.paste_action.connect("activate", self.on_paste)
        self.remove_action.connect("activate", self.on_remove)

        # Set accels
        gl.app.set_accels_for_action("win.copy", ["<Primary>c"])
        gl.app.set_accels_for_action("win.cut", ["<Primary>x"])
        gl.app.set_accels_for_action("win.paste", ["<Primary>v"])
        gl.app.set_accels_for_action("win.remove", ["Delete"])
        self.add_accel_actions()


    def add_accel_actions(self):
        return
        self.add_action(self.copy_action)
        self.add_action(self.cut_action)
        self.add_action(self.paste_action)
        self.add_action(self.remove_action)

    def remove_accel_actions(self):
        return
        self.remove_action(self.copy_action)
        self.remove_action("win.cut")
        self.remove_action("win.paste")
        self.remove_action("win.remove")


    def change_ui_to_no_connected_deck(self):
        if not hasattr(self, "leftArea"):
            self.add_on_finished(self.change_ui_to_no_connected_deck)
            return
        
        self.leftArea.show_no_decks_error()

    def change_ui_to_connected_deck(self):
        if not hasattr(self, "leftArea"):
            self.add_on_finished(self.change_ui_to_connected_deck)
            return
        
        self.leftArea.hide_no_decks_error()
        self.deck_switcher.set_show_switcher(True)

    def set_main_error(self, error: str=None):
        """"
        error: str
            no-decks: Shows the no decks available error
            no-pages: Shows the no pages available error
            None: Goes back to normal mode
        """
        if error is None:
            self.main_stack.set_visible_child(self.toast_overlay)
            self.deck_switcher.set_show_switcher(True)
            self.split_view.set_collapsed(False)
            self.sidebar_toggle_button.set_visible(True)
            return
        
        elif error == "no-decks":
            self.main_stack.set_visible_child(self.no_decks_error)

        elif error == "no-pages":
            self.main_stack.set_visible_child(self.no_pages_error)

        self.deck_switcher.set_show_switcher(False)
        self.split_view.set_collapsed(True)
        self.sidebar_toggle_button.set_visible(False)

    def check_for_errors(self):
        if len(gl.deck_manager.deck_controller) == 0:
            self.set_main_error("no-decks")

        elif len(gl.page_manager.get_page_names()) == 0:
            self.set_main_error("no-pages")

        else:
            self.set_main_error(None)

    def add_on_finished(self, task: callable) -> None:
        if not callable(task):
            return
        if task in self.on_finished:
            return
        self.on_finished.append(task)


    def reload_sidebar(self):
        if not hasattr(self, "sidebar"):
            self.add_on_finished(self.reload_sidebar)
            return
        
        self.sidebar.load_for_coords(self.sidebar.active_coords)

    def do_after_build_tasks(self):
        for task in self.on_finished:
            if callable(task):
                task()
            print()

    def on_copy(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_copy")
        if hasattr(child, "on_copy"):
            child.on_copy()

        return False

    def on_cut(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_cut")
        if hasattr(child, "on_cut"):
            child.on_cut()

        return False

    def on_paste(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_paste")
        if hasattr(child, "on_paste"):
            child.on_paste()

        return False

    def on_remove(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_remove")
        if hasattr(child, "on_remove"):
            child.on_remove()

        return False

    def show_info_toast(self, text: str) -> None:
        toast = Adw.Toast(
            title=text,
            timeout=3,
            priority=Adw.ToastPriority.NORMAL
        )
        self.toast_overlay.add_toast(toast)


class PageManagerNavPage(Adw.NavigationPage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, margin_top=30)
        self.set_child(self.main_box)

        for i in range(10):
            self.main_box.append(PageRow(window=None))


class PageRow(Gtk.ListBoxRow):
    def __init__(self, window: MainWindow):
        self.window = window
        super().__init__()
        self.set_margin_bottom(4)
        self.set_margin_start(50)
        self.set_margin_end(50)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.main_box)

        self.main_button = Gtk.Button(hexpand=True, height_request=30,
                                      label="Page Name",
                                      css_classes=["no-round-right"])
        self.main_box.append(self.main_button)

        self.main_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.config_button = Gtk.Button(height_request=30,
                                        icon_name="view-more",
                                        css_classes=["no-round-left"])
        self.config_button.connect("clicked", self.on_config)
        self.main_box.append(self.config_button)

    def on_config(self, button):
        return
        context = KeyButtonContextMenu(self, self.window)
        context.popup()