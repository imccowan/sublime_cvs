import os.path
import subprocess


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
            proc = NonInteractiveProcess(
                [self.cvs_path, 'status'], cwd=self.root_dir)
            result = proc.run()
            if result.find('Status: Needs Checkout') != -1:
                return 'C'
            if result.find('Status: Needs Patch') != -1:
                return 'P'
            if result.find('Status: Needs Merge') != -1:
                return 'G'
            return 'U'

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

    def status(self, file):
        args = [self.cvs_path, 'status', file]
        return self.run(args, self.root_dir)
