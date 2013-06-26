import sublime
import sublime_plugin
import os.path
import time
import subprocess


class RepositoryNotFoundError(Exception):
    pass


class NotFoundError(Exception):
    pass


file_status_cache = {}


def debug(text=''):
    if sublime.load_settings('CVS.sublime-settings').get('debug', False):
        print 'CVS: %s' % text


class CVSCommand():

    def get_path(self, paths):
        if paths is True:
            return self.get_window().active_view().file_name()
        return paths[0] if paths else self.get_window().active_view().file_name()

    def get_cvs(self, path):
        settings = sublime.load_settings('CVS.sublime-settings')

        if path is None:
            debug('Unable to run commands on an unsaved file')
            raise NotFoundError('Unable to run commands on an unsaved file')
        cvs = None

        cvs_path = settings.get('cvs_path')
        if not os.path.exists(cvs_path):
            debug('Specified CVS binary %s does not exist' % cvs_path)
            raise NotFoundError('Specified CVS binary does not exist')

        try:
            cvs = SublimeCVS(cvs_path, path)
        except (RepositoryNotFoundError):
            pass

        if cvs is None:
            debug('The current file does not appear to be in an ' +
                  'CVS working copy')
            raise NotFoundError('The current file does not appear to be in an ' +
                                'CVS working copy')
        return cvs

    def menus_enabled(self):
        settings = sublime.load_settings('CVS.sublime-settings')
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

    def output_to_panel(self, text, panel_name, syntax=None):
        if not hasattr(self, 'output_panel'):
            self.output_panel = self.get_window().get_output_panel(panel_name)
        panel = self.output_panel
        if syntax is not None:
            panel.set_syntax_file(syntax)

        panel.set_read_only(False)
        edit = panel.begin_edit()
        panel.insert(edit, panel.size(), text.decode('utf-8') + '\n\n')
        panel.end_edit(edit)
        panel.show(panel.size())
        panel.set_read_only(True)

        self.get_window().run_command("show_panel", {
            "panel": "output." + panel_name})


def handles_not_found(fn):
    def handler(self, *args, **kwargs):
        try:
            fn(self, *args, **kwargs)
        except (NotFoundError) as handler_not_found_exception:
            (exception) = handler_not_found_exception
            sublime.error_message('CVS: ' + str(exception))
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


class CvsAnnotateCommand(sublime_plugin.WindowCommand, CVSCommand):

    @handles_not_found
    def run(self, paths=None, revision=False):
        path = self.get_path(paths)
        cvs = self.get_cvs(path)

        if revision:
            result = cvs.status(path if paths else None)
            if revision == 'working':
                revision = result.split('Working revision:')[1].split()[0]
            elif revision == 'repository':
                revision = result.split('Repository revision:')[1].split()[0]
            else:
                revision = False

        self.output_to_new_file(cvs.annotate(path if paths else None, revision if revision else False), title='CVS Annotate')

    @invisible_when_not_found
    def is_visible(self, paths=None, revision=False):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None, revision=False):
        path = self.get_path(paths)
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class CvsDiffCommand(sublime_plugin.WindowCommand, CVSCommand):

    @handles_not_found
    def run(self, paths=None):
        settings = sublime.load_settings('CVS.sublime-settings')
        path = self.get_path(paths)
        diff = self.get_cvs(path).diff(
            path, unified_output=settings.get('diff_unified_output', False))
        if diff is not None:
            self.view = self.output_to_new_file(
                diff, title='CVS Diff', syntax="Packages/Diff/Diff.tmLanguage")

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if path and os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path) in ['M', 'F']


class CvsLogCommand(sublime_plugin.WindowCommand, CVSCommand):

    @handles_not_found
    def run(self, paths=None):
        settings = sublime.load_settings('CVS.sublime-settings')
        path = self.get_path(paths)
        self.output_to_new_file(self.get_cvs(path).log(
            path if paths else None, show_tags=settings.get('cvs_log_show_tags', True)), title='CVS Log')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class CvsStatusCommand(sublime_plugin.WindowCommand, CVSCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        status = self.get_cvs(path).status(path if paths else None)
        if status is not None:
            settings = sublime.load_settings('CVS.sublime-settings')
            output_style = settings.get('cvs_status_new_file', 'never')
            if output_style == 'always' or (output_style == 'foldersonly' and os.path.isdir(path)):
                self.output_to_new_file(status, 'CVS Status')
            else:
                self.output_to_panel(status, 'CVS Status')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class CvsUpdateCommand(sublime_plugin.WindowCommand, CVSCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        update = self.get_cvs(path).update(path)
        if update is not None:
            self.output_to_panel(update, 'CVS Update')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        return True

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        return path and self.get_cvs(path).get_status(path) in ['C', 'P', 'G']


class CVSStatusBar(sublime_plugin.EventListener, CVSCommand):

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
        debug('CVS root directory: %s' % root_dir)
        self.root_dir = root_dir

    def check_status(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'status', path]
        result = NonInteractiveProcess(args, cwd=self.root_dir).run()
        if os.path.isdir(path):
            if result.find('Status: Needs Checkout') != -1:
                return 'C'
            if result.find('Status: Needs Patch') != -1:
                return 'P'
            if result.find('Status: Needs Merge') != -1:
                return 'G'
            return 'U'

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

    def process_status(self, path):
        global file_status_cache
        settings = sublime.load_settings('CVS.sublime-settings')
        if path in file_status_cache and file_status_cache[path]['time'] > \
                time.time() - settings.get('cache_length', 5):
            debug('Fetching cached status for %s' % path)
            return file_status_cache[path]['status']

        start_time = 0
        if settings.get('debug', False):
            start_time = time.time()

        try:
            status = self.check_status(path)
        except (Exception) as check_status_exception:
            (exception) = check_status_exception
            sublime.error_message(str(exception))
            return []

        file_status_cache[path] = {
            'time': time.time() + settings.get('cache_length', 5),
            'status': status
        }

        debug('Fetching status %s for %s in %s seconds' % (status, path,
                                                           str(time.time() - start_time)))
        return status

    def get_status(self, path):
        return self.process_status(path)

    def annotate(self, path=None, revision=False):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'annotate']
        if revision:
            args.append('-r')
            args.append(revision)
        args.append(path)
        return NonInteractiveProcess(args, cwd=self.root_dir).run()

    def diff(self, path, unified_output=False):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'diff']
        if unified_output:
            args.append('-u')
        args.append(path)
        return NonInteractiveProcess(args, cwd=self.root_dir).run()

    def log(self, path=None, show_tags=True):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'log']
        if not show_tags:
            args.append('-N')
        args.append(path)
        return NonInteractiveProcess(args, cwd=self.root_dir).run()

    def status(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'status', path]
        return NonInteractiveProcess(args, cwd=self.root_dir).run()

    def update(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'update', path]
        return NonInteractiveProcess(args, cwd=self.root_dir).run()


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

        result = proc.stdout.read().replace('\r\n', '\n').rstrip(' \n\r')
        if len(result) > 0:
            return result
        return None


if sublime.version()[1] == "2":
    CVSStatusBar.on_post_save = CVSStatusBar._update
    CVSStatusBar.on_load = CVSStatusBar._update
