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


class CVSNTCommand():

    def get_path(self, paths):
        if paths is True:
            return self.window.active_view().file_name()
        return paths[0] if paths else self.window.active_view().file_name()

    def get_cvs(self, path):
        settings = sublime.load_settings('CVSNT.sublime-settings')

        if path is None:
            raise NotFoundError('Unable to run commands on an unsaved file')
        cvs = None

        try:
            cvs = CVSNT(settings.get('cvsnt_cvs_path'), path)
        except (RepositoryNotFoundError):
            pass

        if cvs is None:
            raise NotFoundError('The current file does not appear to be in an ' +
                                'CVS working copy')
        return cvs

    def menus_enabled(self):
        settings = sublime.load_settings('CVS.sublime-settings')
        return settings.get('enable_menus', True)

    def get_window(self):
        return self.window

    def _output_to_file(self, output_file, output, clear=False, syntax=None, **kwargs):
        if syntax is not None:
            output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, output)
        output_file.end_edit(edit)

    def output_to_new_file(self, output, title=False, position=None, **kwargs):
        new_file = self.get_window().new_file()
        if title:
            new_file.set_name(title)
        new_file.set_scratch(True)
        self._output_to_file(new_file, output, **kwargs)
        new_file.set_read_only(True)
        if position:
            sublime.set_timeout(lambda: new_file.set_viewport_position(position), 0)
        return new_file

    def output_to_panel(self, text, panel_name):
        # get_output_panel doesn't "get" the panel, it *creates* it,
        # so we should only call get_output_panel once
        if not hasattr(self, 'output_panel'):
            self.output_panel = self.window.get_output_panel(panel_name)
        panel = self.output_panel

        # Write this text to the output panel and display it
        edit = panel.begin_edit()
        panel.insert(edit, panel.size(), text + '\n')
        panel.end_edit(edit)
        panel.show(panel.size())

        self.window.run_command("show_panel", {"panel": "output." + panel_name})


def handles_not_found(fn):
    def handler(self, *args, **kwargs):
        try:
            fn(self, *args, **kwargs)
        except (NotFoundError) as xxx_todo_changeme:
            (exception) = xxx_todo_changeme
            sublime.error_message('CVSNT: ' + str(exception))
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


# class CvsntAddCommand(sublime_plugin.WindowCommand, CVSNTCommand):

#     @handles_not_found
#     def run(self, paths=None):
#         path = self.get_path(paths)
#         #self.get_cvs(path).add(path)

#     @invisible_when_not_found
#     def is_visible(self, paths=None):
#         if not self.menus_enabled():
#             return False
#         path = self.get_path(paths)
#         return True #self.get_cvs(path).get_status(path) in ['']

#     @invisible_when_not_found
#     def is_enabled(self, paths=None):
#         path = self.get_path(paths)
#         if os.path.isdir(path):
#             return True
#         return False and path and self.get_cvs(path).get_status(path) in ['']


class CvsntAnnotateCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.output_to_new_file(self.get_cvs(path).annotate(path if paths else None), title=path + ' - CVS Annotated')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return True #path and cvs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return False
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


# class CvsntCommitCommand(sublime_plugin.WindowCommand, CVSNTCommand):

#     @handles_not_found
#     def run(self, paths=None):
#         path = self.get_path(paths)
#         #self.get_cvs(path).commit(path)

#     @invisible_when_not_found
#     def is_visible(self, paths=None):
#         if not self.menus_enabled():
#             return False
#         path = self.get_path(paths)
#         return True #self.get_cvs(path).get_status(path)

#     @invisible_when_not_found
#     def is_enabled(self, paths=None):
#         path = self.get_path(paths)
#         if os.path.isdir(path):
#             return True
#         return False and path and self.get_cvs(path).get_status(path)


class CvsntDiffCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        diff = self.get_cvs(path).diff(path if paths else None)
        if diff is not None:
            self.output_to_new_file(diff, title=path + ' - CVS Diff', syntax="Packages/Diff/Diff.tmLanguage")

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return True #cvs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        cvs = self.get_cvs(path)
        return cvs.get_status(path) in ['M', 'F']


class CvsntLogCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.output_to_new_file(self.get_cvs(path).log(path if paths else None), title=path + ' - CVS Log')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return True #path and cvs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return False
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class CvsntStatusCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        status = self.get_cvs(path).status(path if paths else None)
        if status is not None:
            print status

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        cvs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return False and path and cvs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path) in ['U', 'M', 'A', 'R', 'C', 'P', 'G', 'F']


class CvsntUpdateCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.output_to_panel(self.get_cvs(path).update(path), 'CVSUpdate')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        return True #self.get_cvs(path).get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path) in ['C', 'P', 'G']


class CVSNT():

    def __init__(self, binary_path, file):
        self.find_root('CVS', file)
        if binary_path is not None:
            self.path = binary_path
        else:
            self.set_binary_path('CVSNT\\cvs.exe', 'cvs.exe', 'cvsnt_cvs_path')

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

    def set_binary_path(self, path_suffix, binary_name, setting_name):
        root_drive = os.path.expandvars('%HOMEDRIVE%\\')

        possible_dirs = [
            'Program Files\\',
            'Program Files (x86)\\'
        ]

        for dir in possible_dirs:
            path = root_drive + dir + path_suffix
            if os.path.exists(path):
                self.path = path
                return

        self.path = None
        normal_path = root_drive + possible_dirs[0] + path_suffix
        raise NotFoundError('Unable to find ' + self.__class__.__name__ +
                            '.\n\nPlease add the path to ' + binary_name +
                            ' to the setting "' + setting_name + '" in "' +
                            sublime.packages_path() +
                            '\\CVSNT\\CVSNT.sublime-settings".\n\n' +
                            'Example:\n\n' + '{"' + setting_name + '": r"' +
                            normal_path + '"}')

    def process_status(self, cvs, path):
        global file_status_cache
        settings = sublime.load_settings('CVSNT.sublime-settings')
        if path in file_status_cache and file_status_cache[path]['time'] > \
                time.time() - settings.get('cache_length'):
            if settings.get('debug'):
                print 'Fetching cached status for %s' % path
            return file_status_cache[path]['status']

        if settings.get('debug'):
            start_time = time.time()

        try:
            status = cvs.check_status(path)
        except (Exception) as xxx_todo_changeme1:
            (exception) = xxx_todo_changeme1
            sublime.error_message(str(exception))

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

    # def add(self, path):
    #     path = os.path.relpath(path, self.root_dir)
    #     args = [self.path, 'add', path]
    #     return cvs.run(args, self.root_dir)

    def annotate(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'annotate', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    # def commit(self, path=None):
    #     path = os.path.relpath(path, self.root_dir)
    #     args = [self.path, 'commit', path]
    #     return cvs.run(args, self.root_dir)

    def diff(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'diff', path]
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

    def __init__(self, cvsnt_cvs_path, root_dir):
        self.cvs_path = os.path.dirname(cvsnt_cvs_path) + '\\cvs.exe'
        self.root_dir = root_dir

    def check_status(self, path):
        if os.path.isdir(path):
            proc = NonInteractiveProcess([self.cvs_path, 'log', '-l', '1',
                                          '"' + path + '"'], cwd=self.root_dir)
            result = proc.run().strip().split('\n')
            if result == ['']:
                return '?'
            return ''

        proc = NonInteractiveProcess([self.cvs_path, 'status', os.path.basename(path)],
                                     cwd=self.root_dir)
        result = proc.run()
        #.split('\n')
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


class CVSNTStatusBar(sublime_plugin.EventListener, CVSNTCommand):
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
    CVSNTStatusBar.on_post_save = CVSNTStatusBar._update
    CVSNTStatusBar.on_load = CVSNTStatusBar._update
