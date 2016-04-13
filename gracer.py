import os
import tempfile
import subprocess
from gi.repository import GObject, Gedit, Gtk, GtkSource, PeasGtk


class Settings:
    def get_config_file_path():
        path = os.path.abspath(os.path.dirname(__file__))
        path += os.path.sep
        return path + "gracer.config"

    def get_value(key, default_value):
        if os.path.exists(Settings.get_config_file_path()):
            settings = {}
            with open(Settings.get_config_file_path(), 'r') as settings_file:
                for line in settings_file.readlines():
                    _key, val = line.rstrip('\n').split("=")
                    settings[_key] = val

            if key in settings:
                return settings[key]
        return default_value

    def save_settings(settings):
        with open(Settings.get_config_file_path(), 'w') as settings_file:
            settings_file.writelines([key + "=" + settings[key] + '\n' for key in settings])


class Racer:
    def __init__(self):
        self.RUST_SRC_PATH = None
        self.RACER_PATH    = None

    def get_rust_src_path(self):
        if self.RUST_SRC_PATH is not None:
            return self.RUST_SRC_PATH

        default_value = ""
        possible_rust_paths = ("/usr/src/rust/src", "/usr/local/src/rust/src", os.environ.get('RUST_SRC_PATH'))
        for path in possible_rust_paths:
            if path is not None and os.path.exists(path):
                default_value = path

        self.RUST_SRC_PATH = Settings.get_value("rust_src_path", default_value)
        return self.RUST_SRC_PATH

    def get_racer_path(self):
        if self.RACER_PATH is not None:
            return self.RACER_PATH

        default_value = ""
        possible_racer_paths = ("/usr/bin/racer", "/usr/local/bin/racer", os.path.expanduser("~/.cargo/bin/racer"))
        for path in possible_racer_paths:
            if os.path.exists(path):
                default_value = path

        self.RACER_PATH = Settings.get_value("racer_path", default_value)
        return self.RACER_PATH

    def init_racer(self, document, subcommand):
        temp_file = tempfile.NamedTemporaryFile()
        doc_text = document.get_text(document.get_start_iter(), document.get_end_iter(), False)
        temp_file.write(doc_text.encode('utf-8'))
        temp_file.seek(0)

        iter_cursor = document.get_iter_at_mark(document.get_insert())
        linenum = iter_cursor.get_line() + 1
        charnum = iter_cursor.get_line_index()

        rust_src_path = self.get_rust_src_path()
        racer_path = self.get_racer_path()

        if not os.path.exists(rust_src_path) or not os.path.exists(racer_path):
            print(rust_src_path, racer_path, "Try to set rust source path and racer path in plugin settings.")

        proc_args = (racer_path, subcommand, str(linenum), str(charnum), temp_file.name)
        output = ""

        try:
            output = subprocess.check_output(proc_args, env=dict(os.environ, RUST_SRC_PATH=rust_src_path)).decode()
        except Exception as e:
            print(e)

        temp_file.close()
        return output

    def get_matches(self, document):
        proc_result = self.init_racer(document, "complete")
        if proc_result == "" or proc_result is None:
            return []

        completion = []
        for line in proc_result.split('\n'):
            if line.startswith("MATCH "):
                line = line[6:]
                line_items = line.split(",")

                completion_text = line_items[0]
                completion_path = line_items[3]
                completion_type = line_items[4]
                completion_line = line_items[5]
                completion.append((completion_text, completion_type, completion_path, completion_line))

        return completion

    def get_definition(self, document):
        proc_result = self.init_racer(document, "find-definition")
        if proc_result == "" or proc_result is None:
            return None

        for line in proc_result.split('\n'):
            if line.startswith("MATCH "):
                line = line[6:]
                line_items = line.split(",")

                definition_line = line_items[1]
                definition_char = line_items[2]
                definition_file = line_items[3]
                definition_str = line_items[5]

                return (definition_line, definition_char, definition_file, definition_str)

        return None


class GracerPlugin(GObject.Object, Gedit.ViewActivatable, PeasGtk.Configurable):
    __gtype_name__ = "GracerPlugin"
    view = GObject.property(type=Gedit.View)
    racer = Racer()

    def __init__(self):
        GObject.Object.__init__(self)

        self.completion_provider = None
        self.handler_on_view_populate_popup = None

    def do_activate(self):
        document = self.view.get_buffer()
        document.connect("load", self.on_document_load)

        if document.get_uri_for_display().endswith(".rs"):
            self.completion_provider = GracerCompletionProvider(self.racer)
            self.view.get_completion().add_provider(self.completion_provider)
            self.view.connect('populate-popup', self.on_view_populate_popup)

    def do_deactivate(self):
        pass

    def on_document_load(self, document):
        if document.get_uri_for_display().endswith(".rs"):
            if self.completion_provider is None:
                self.completion_provider = GracerCompletionProvider(self.racer)
                self.view.get_completion().add_provider(self.completion_provider)

            if self.handler_on_view_populate_popup is None:
                self.handler_on_view_populate_popup = self.view.connect('populate-popup', self.on_view_populate_popup)
        else:
            if self.completion_provider is not None:
                self.view.get_completion().remove_provider(self.completion_provider)
                self.completion_provider = None

            if self.handler_on_view_populate_popup is not None:
                self.view.disconnect(self.handler_on_view_populate_popup)
                self.handler_on_view_populate_popup = None

    def do_create_configure_widget(self):
        table = Gtk.Table(3, 2, Gtk.true())
        table.set_row_spacings(5)
        table.set_col_spacings(5)

        lbl_racerpath = Gtk.Label("Racer path: ")
        lbl_rustsrc   = Gtk.Label("Rust source path: ")

        self.txt_racerpath = Gtk.TextView()
        self.txt_rustsrc   = Gtk.TextView()

        rust_src_path = self.racer.get_rust_src_path()
        racer_path = self.racer.get_racer_path()

        self.txt_racerpath.get_buffer().set_text(racer_path)
        self.txt_rustsrc.get_buffer().set_text(rust_src_path)

        btn_save = Gtk.Button("Save")
        btn_save.connect("clicked", self.on_btn_save_clicked)

        table.attach(lbl_racerpath, 0, 1, 0, 1)
        table.attach(lbl_rustsrc, 0, 1, 1, 2)
        table.attach(self.txt_racerpath, 1, 2, 0, 1)
        table.attach(self.txt_rustsrc, 1, 2, 1, 2)
        table.attach(btn_save, 0, 2, 2, 3)

        return table

    def on_btn_save_clicked(self, btn):
        settings = {"racer_path":self.txt_racerpath.get_buffer().get_text(self.txt_racerpath.get_buffer().get_start_iter(),
                                                                             self.txt_racerpath.get_buffer().get_end_iter(), False),
                    "rust_src_path":self.txt_rustsrc.get_buffer().get_text(self.txt_rustsrc.get_buffer().get_start_iter(),
                                                                             self.txt_rustsrc.get_buffer().get_end_iter(), False)}
        Settings.save_settings(settings)

    def on_view_populate_popup(self, view, menu):
        menu_find_definition = Gtk.ImageMenuItem(_("Find Definition"))
        menu_find_definition.connect('activate', self.on_find_definition_active)
        #menu_find_definition.set_image(gtk.image_new_from_stock(gtk.STOCK_COMMENT, gtk.ICON_SIZE_MENU))
        menu_find_definition.show()

        separator = Gtk.SeparatorMenuItem()
        separator.show()

        menu.prepend(separator)
        menu.prepend(menu_find_definition)

    def on_find_definition_active(self, menu_item):
        #FIXME: check file name
        document = self.view.get_buffer()
        result = self.racer.get_definition(document)
        try:
            result_line = int(result[0]) - 1 # -1, because line numbering is 0-based
            result_char = int(result[1])
            document.place_cursor(document.get_iter_at_line_offset(result_line, result_char))
        except Exception as e: # probably not found anything
            print(e)


class GracerCompletionProvider(GObject.Object, GtkSource.CompletionProvider):
    __gtype_name__ = 'GracerProvider'

    def __init__(self, _racer):
        GObject.Object.__init__(self)
        self.racer = _racer

    def do_get_name(self):
        return _("Gracer Rust Code Completion")

    def do_match(self, context):
        # checked this before at GracerPlugin.do_active
        print(context)
        return True

    def do_get_priority(self):
        return 0

    def do_populate(self, context):
        _, it = context.get_iter()
        document = it.get_buffer()
        proposals = []

        #TODO: add completion for type (ex. add extra brackets for functions)
        for _text, _type, _path, _line in self.racer.get_matches(document):
            proposals.append(GtkSource.CompletionItem.new(
                _text, _text, self.get_icon_for_type(_type),
                _line.replace('&', '&amp;').replace('<', '&lt;')))

        context.add_proposals(self, proposals, True)

    def get_icon_for_type(self, _type):
        #FIXME: find real icon names
        icon_names = {"Module":"code-class", "Struct":"code-class", "StructField":"field",
                      "Trait":"field", "Function":"code-function", "Let":"code-variable",
                      "Enum":"icon", "Crate":"code-class"}

        theme = Gtk.IconTheme.get_default()
        try:
            return theme.load_icon(icon_names[_type], 16, 0)
        except:
            return theme.load_icon(Gtk.STOCK_YES, 16, 0)


GObject.type_register(GracerCompletionProvider)
