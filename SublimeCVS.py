import sublime
import sublime_plugin
import os.path
import subprocess
import time


class RepositoryNotFoundError(Exception):
    pass


class NotFoundError(Exception):
    pass


file_status_cache = {}


class SublimeCVSCommand():

    def get_path(self, paths):
        if paths is True:
            return self.window.active_view().file_name()
        return paths[0] if paths else self.window.active_view().file_name()

    def get_cvs(self, path):
        settings = sublime.load_settings('SublimeCVS.sublime-settings')

        if path is None:
            raise NotFoundError('Unable to run commands on an unsaved file')
        cvs = None

        try:
            cvs = SublimeCVS(settings.get('cvs_path'), path)
        except (RepositoryNotFoundError):
            pass

        if cvs is None:
            raise NotFoundError('The current file does not appear to be in an ' +
                                'CVS working copy')
        return cvs

    def menus_enabled(self):
        settings = sublime.load_settings('SublimeCVS.sublime-settings')
        return settings.get('enable_menus', True)

    def get_window(self):
        return self.window

    def _output_to_file(self, output_file, text, clear=False, syntax=None, **kwargs):
        if syntax is not None:
            output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, text.decode('utf-8'))
        output_file.end_edit(edit)

    def output_to_new_file(self, text, title=False, position=None, **kwargs):
        new_file = self.get_window().new_file()
        if title:
            new_file.set_name(title)
        new_file.set_scratch(True)
        self._output_to_file(new_file, text, **kwargs)
        new_file.set_read_only(True)
        if position:
            sublime.set_timeout(
                lambda: new_file.set_viewport_position(position), 0)
        return new_file

    def output_to_panel(self, text, panel_name):
        if not hasattr(self, 'output_panel'):
            self.output_panel = self.window.get_output_panel(panel_name)
        panel = self.output_panel

        edit = panel.begin_edit()
        panel.insert(edit, panel.size(), text.decode('utf-8') + '\n')
        panel.end_edit(edit)
        panel.show(panel.size())

        self.window.run_command("show_panel", {
                                "panel": "output." + panel_name})


def handles_not_found(fn):
    def handler(self, *args, **kwargs):
        try:
            fn(self, *args, **kwargs)
        except (NotFoundError) as handler_not_found_exception:
            (exception) = handler_not_found_exception
            sublime.error_message('SublimeCVS: ' + str(exception))
    return handler


def invisible_when_not_found(fn):
    def handler(self, *args, **kwargs):
        try:
            res = fn(self, *args, **kwargs)
            if res is not None:
                return res
            return True
        except (NotFoundError):
            return False
    return handler


class SublimeCvsAnnotateCommand(sublime_plugin.WindowCommand, SublimeCVSCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.output_to_new_file(self.get_cvs(path).annotate(
            path if paths else None), title=path + ' - CVS Annotated')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return False
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class SublimeCvsDiffCommand(sublime_plugin.WindowCommand, SublimeCVSCommand):

    @handles_not_found
    def run(self, paths=None):
        settings = sublime.load_settings('SublimeCVS.sublime-settings')
        path = self.get_path(paths)
        diff = self.get_cvs(path).diff(
            path if paths else None, unified_output=settings.get('diff_unified_output'))
        if diff is not None:
            self.output_to_new_file(
                diff, title=path + ' - CVS Diff', syntax="Packages/Diff/Diff.tmLanguage")

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        cvs = self.get_cvs(path)
        return cvs.get_status(path) in ['M', 'F']


class SublimeCvsLogCommand(sublime_plugin.WindowCommand, SublimeCVSCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.output_to_new_file(self.get_cvs(path).log(
            path if paths else None), title=path + ' - CVS Log')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return False
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class SublimeCvsStatusCommand(sublime_plugin.WindowCommand, SublimeCVSCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        status = self.get_cvs(path).status(path if paths else None)
        if status is not None:
            self.output_to_panel(status, 'CVSStatus')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return path and cvs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class SublimeCvsUpdateCommand(sublime_plugin.WindowCommand, SublimeCVSCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        update = self.get_cvs(path).update(path)
        if update is not None:
            self.output_to_panel(update, 'CVSUpdate')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path) in ['C', 'P', 'G']


class SublimeCVS():

    def __init__(self, binary_path, file):
        self.find_root('CVS', file)
        self.path = binary_path

    def find_root(self, name, path, find_first=True):
        root_dir = None
        last_dir = None
        cur_dir = path if os.path.isdir(path) else os.path.dirname(path)
        while cur_dir != last_dir:
            if root_dir is not None and not os.path.exists(os.path.join(cur_dir, name)):
                break
            if os.path.exists(os.path.join(cur_dir, name)):
                root_dir = cur_dir
                if find_first:
                    break
            last_dir = cur_dir
            cur_dir = os.path.dirname(cur_dir)

        if root_dir is None:
            raise RepositoryNotFoundError('Unable to find ' + name +
                                          ' directory')
        self.root_dir = root_dir

    def process_status(self, cvs, path):
        global file_status_cache
        settings = sublime.load_settings('SublimeCVS.sublime-settings')
        if path in file_status_cache and file_status_cache[path]['time'] > \
                time.time() - settings.get('cache_length'):
            if settings.get('debug'):
                print 'Fetching cached status for %s' % path
            return file_status_cache[path]['status']

        if settings.get('debug'):
            start_time = time.time()

        try:
            status = cvs.check_status(path)
        except (Exception) as check_status_exception:
            (exception) = check_status_exception
            sublime.error_message(str(exception))
            return []

        file_status_cache[path] = {
            'time': time.time() + settings.get('cache_length'),
            'status': status
        }

        if settings.get('debug'):
            print 'Fetching status %s for %s in %s seconds' % (status, path,
                                                               str(time.time() - start_time))
        return status

    def get_status(self, path):
        cvs = CVS(self.path, self.root_dir)
        return self.process_status(cvs, path)

    def annotate(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'annotate', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def diff(self, path, unified_output=False):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'diff']
        if unified_output:
            args.append('-u')
        args.append(path)
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def log(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'log', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def status(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'status', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def update(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'update', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)


class NonInteractiveProcess():

    def __init__(self, args, cwd=None):
        self.args = args
        self.cwd = cwd

    def run(self):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(self.args, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                startupinfo=startupinfo, cwd=self.cwd)

        return proc.stdout.read().replace('\r\n', '\n').rstrip(' \n\r')


class CVS():

    def __init__(self, cvs_path, root_dir):
        self.cvs_path = cvs_path
        self.root_dir = root_dir

    def check_status(self, path):
        if os.path.isdir(path):
            proc = NonInteractiveProcess([self.cvs_path, 'log', '-l', '1',
                                          '"' + path + '"'], cwd=self.root_dir)
            result = proc.run().strip().split('\n')
            if result == ['']:
                return '?'
            return ''

        proc = NonInteractiveProcess(
            [self.cvs_path, 'status', os.path.basename(path)],
            cwd=self.root_dir)
        result = proc.run()
        if len(result) > 0:
            if result.find('Status: Unknown') != -1:
                return ''
            if result.find('Status: Up-to-date') != -1:
                return 'U'
            if result.find('Status: Locally Modified') != -1:
                return 'M'
            if result.find('Status: Locally Added') != -1:
                return 'A'
            if result.find('Status: Locally Removed') != -1:
                return 'R'
            if result.find('Status: Needs Checkout') != -1:
                return 'C'
            if result.find('Status: Needs Patch') != -1:
                return 'P'
            if result.find('Status: Needs Merge') != -1:
                return 'G'
            if result.find('Status: Unresolved Conflict') != -1:
                return 'F'
        return ''

    def run(self, cmd, cwd):
        proc = NonInteractiveProcess(cmd, cwd=cwd)
        result = proc.run()
        if len(result) > 0:
            return result
        return None


class SublimeCVSStatusBar(sublime_plugin.EventListener, SublimeCVSCommand):

    def _update(self, view):
        try:
            path = view.file_name()
            if path:
                status = self.get_cvs(path).get_status(path)
                if status == 'U':
                    status = 'Up-to-date'
                elif status == 'M':
                    status = 'Locally Modified'
                elif status == 'A':
                    status = 'Locally Added'
                elif status == 'R':
                    status = 'Locally Removed'
                elif status == 'C':
                    status = 'Needs Checkout'
                elif status == 'P':
                    status = 'Needs Patch'
                elif status == 'G':
                    status = 'Needs Merge'
                elif status == 'F':
                    status = 'Unresolved Conflict'
                else:
                    status = 'Unknown'
                view.set_status('file_info', 'CVS Status: ' + status)
        except (NotFoundError):
            pass
        except (RepositoryNotFoundError):
            pass

if sublime.version()[1] == "2":
    SublimeCVSStatusBar.on_post_save = SublimeCVSStatusBar._update
    SublimeCVSStatusBar.on_load = SublimeCVSStatusBar._update
