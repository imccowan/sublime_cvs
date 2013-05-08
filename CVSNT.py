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
        vcs = None

        try:
            vcs = CVSNT(settings.get('cvsnt_cvs_path'), path)
        except (RepositoryNotFoundError):
            pass

        if vcs is None:
            raise NotFoundError('The current file does not appear to be in an ' +
                                'CVS working copy')
        return vcs

    def menus_enabled(self):
        settings = sublime.load_settings('CVS.sublime-settings')
        return settings.get('enable_menus', True)

    def get_window(self):
        return self.window

    def _output_to_view(self, output_file, output, clear=False, syntax=None, **kwargs):
        if syntax is not None:
            output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, output)
        output_file.end_edit(edit)

    def scratch(self, output, title=False, position=None, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        if position:
            sublime.set_timeout(lambda: scratch_file.set_viewport_position(position), 0)
        return scratch_file


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


class CvsntAnnotateCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.scratch(self.get_cvs(path).annotate(path if paths else None), syntax=None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        vcs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return path and vcs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path)


class CvsntCommitCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_cvs(path).commit(path if os.path.isdir(path) else None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        if not path:
            return False
        self.get_cvs(path)
        return os.path.isdir(path)


class CvsntStatusCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        status = self.get_cvs(path).status(path if paths else None)
        if status is not None:
            print status
            #self.panel(status)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        vcs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return path and vcs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path)


class CvsntLogCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.scratch(self.get_cvs(path).log(path if paths else None), syntax=None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        vcs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return path and vcs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_cvs(path).get_status(path)


class CvsntDiffCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        diff = self.get_cvs(path).diff(path if paths else None)
        if diff is not None:
            self.scratch(diff, syntax="Packages/Diff/Diff.tmLanguage")
        else:
            self.panel('test')

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        vcs = self.get_cvs(path)
        if os.path.isdir(path):
            return True
        return vcs.get_status(path)

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        vcs = self.get_cvs(path)
        return vcs.get_status(path)


class CvsntAddCommand(sublime_plugin.WindowCommand, CVSNTCommand):

    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_cvs(path).add(path)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        return self.get_cvs(path).get_status(path)


class ForkGui():

    def __init__(self, cmd, cwd):
        subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=cwd)


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

    def process_status(self, vcs, path):
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
            status = vcs.check_status(path)
        except (Exception) as xxx_todo_changeme1:
            (exception) = xxx_todo_changeme1
            sublime.error_message(str(exception))

        file_status_cache[path] = {
            'time': time.time() + settings.get('cache_length'),
            'status': status
        }

        if settings.get('debug'):
            print 'Fetching status for %s in %s seconds' % (path,
                                                            str(time.time() - start_time))
        return status

    def annotate(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'annotate', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def diff(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'diff', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def status(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'status', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def log(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'log', path]
        cvs = CVS(self.path, self.root_dir)
        return cvs.run(args, self.root_dir)

    def add(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'add', '--nofork', path]
        #ForkGui(args, self.root_dir)

    def commit(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'commit', '--nofork', path]
        #ForkGui(args, self.root_dir)

    def get_status(self, path):
        cvs = CVS(self.path, self.root_dir)
        return self.process_status(cvs, path)


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
        result = proc.run().split('\n')
        if len(result) > 0:
            return not result[0].startswith('cvs status: nothing known about')
        return False

    def run(self, cmd, cwd):
        proc = NonInteractiveProcess(cmd, cwd=cwd)
        result = proc.run()
        if len(result) > 0:
            return result
        return None
