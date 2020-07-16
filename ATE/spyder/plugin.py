"""
ATE Plugin.
"""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtGui import QIcon

# Local imports
from spyder.api.plugins import ApplicationMenus, Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from ATE.spyder.project import ATEProject
from ATE.spyder.widgets.main_widget import ATEWidget

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class ATE(SpyderDockablePlugin):
    """
    Breakpoint list Plugin.
    """
    NAME = 'ate'
    REQUIRES = [Plugins.Editor]
    TABIFY = [Plugins.Projects]
    WIDGET_CLASS = ATEWidget
    CONF_SECTION = NAME

    # --- Signals
    # ------------------------------------------------------------------------
    sig_edit_goto_requested = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.
    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("ATE")

    def get_description(self):
        return _("Automatic test equipment.")

    def get_icon(self):
        return QIcon()

    def register(self):
        widget = self.get_widget()

        # Expose widget signals on the plugin
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)

        # Add toolbar
        self.add_application_toolbar('ate_toolbar', widget.toolbar)
        widget.toolbar.hide()

        # Register a new project type
        # TODO: Temporal fix
        projects = self._main._PLUGINS["project_explorer"]
        projects.register_project_type(ATEProject)

        # Register editor connection
        # TODO: Temporal fix
        editor = self._main._PLUGINS["editor"]
        self.sig_edit_goto_requested.connect(editor.load)

        # Register a new action to create consoles on the IPythonConsole
        # TODO: Temporal fix
        zconf_action = self.create_action(
            name="show_zconf_dialog",
            text="Select kernel from Zero Conf",
            tip="",
            icon=self.create_icon("run"),
            triggered=self.show_zero_conf_dialog,
        )
        ipython = self._main._PLUGINS["ipython_console"]
        # menu = ipython.get_main_menu()
        # self.add_item_to_menu(
        #     zconf_action,
        #     menu,
        #     "top",
        # )

    # --- ATE Plugin API
    # ------------------------------------------------------------------------
    def create_project(self, project_root):
        print(f"Plugin : Creating ATE project '{os.path.basename(project_root)}'")
        self.project_root = project_root
        self.get_widget().create_project(project_root)

    def open_project(self, project_root):
        print(f"Plugin : Opening ATE project '{os.path.basename(project_root)}'")
        self.project_root = project_root
        self.get_widget().open_project(project_root)

    def close_project(self):
        print("Plugin : Closing ATE project '{os.path.basename(self.project_root)}'")
        self.get_widget().close_project()

    def show_zero_conf_dialog(self):
        print("something!")

    def trial(self):
        print("this way!")