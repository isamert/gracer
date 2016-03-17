import os
import tempfile
import subprocess
from gi.repository import GObject, Gedit, Gtk, GtkSource

#TODO: add options page that can manage rust src path and racer path

class GracerPlugin(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "GracerPlugin"
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.view.get_completion().add_provider(GracerProvider(self.view))
        print("Gracer is activated.")

    def do_deactivate(self):
        #print("Gracer is deactivated.")
        pass

    def do_update_state(self):
        pass


class GracerProvider(GObject.Object, GtkSource.CompletionProvider):
    __gtype_name__ = 'GracerProvider'

    def __init__(self, view):
        GObject.Object.__init__(self)
        self._view = view

    def do_get_name(self):
        return _("Gracer Rust Code Completion")

    def do_match(self, context):
        _iter = context.get_iter()
        if type(_iter) is tuple:
            _iter = _iter[1]
        return _iter.get_buffer().get_uri_for_display().endswith(".rs")

    def do_get_priority(self):
        return 0

    def do_populate(self, context):
        document = self._view.get_buffer()
        proposals = []

        for _text, _type, _path in self.get_matches(document):
            proposals.append(GtkSource.CompletionItem.new(_text, _text, self.get_icon_for_type(_type), _path))

        context.add_proposals(self, proposals, True)

    def get_racer_command(self):
        #FIXME: RUST_SRC_PATH
        #FIXME: check racer executable
        paths = ("/usr/bin/racer", "/usr/local/bin/racer", os.path.expanduser("~/.cargo/bin/racer"))
        return [path for path in paths if os.path.exists(path)][0]

    def get_matches(self, document):
        temp_file = tempfile.NamedTemporaryFile()
        doc_text = document.get_text(document.get_start_iter(), document.get_end_iter(), False)
        temp_file.write(doc_text.encode('utf-8'))
        temp_file.seek(0)


        iter_cursor = document.get_iter_at_mark(document.get_insert())
        linenum = iter_cursor.get_line() + 1
        charnum = iter_cursor.get_line_index()

        subcommand = "complete"

        proc_args = [self.get_racer_command(), subcommand, str(linenum), str(charnum), temp_file.name]
        try:
            proc_result = subprocess.check_output(proc_args).decode()
        except Exception as e:
            print(proc_args, e.args)
            return []

        completion = []
        for line in proc_result.split('\n'):
            if line.startswith("MATCH "):
                line = line[6:]
                line_items = line.split(",")

                completion_text = line_items[0]
                completion_path = line_items[3]
                completion_type = line_items[4];
                completion.append((completion_text, completion_type, completion_path))

        temp_file.close()

        return completion

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



GObject.type_register(GracerProvider)
