from __future__ import absolute_import
import subprocess
import sys
import os

OTS_SANITIZE = os.path.join(os.path.dirname(__file__), "ots-sanitize")

__all__ = ["sanitize", "OTSError", "CalledProcessError"]


try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0+unknown"


class OTSError(Exception):
    pass


# subprocess.CalledProcessError on python < 3.5 doesn't have 'stderr' argument.
# Regardless, it's a good idea to wrap subprocess' exceptions with our own.
class CalledProcessError(OTSError, subprocess.CalledProcessError):
    def __init__(self, returncode, cmd, output=None, stderr=None):
        subprocess.CalledProcessError.__init__(self, returncode, cmd, output=output)
        self.stderr = stderr

    @property
    def stdout(self):
        """Alias for output attribute, to match stderr"""
        return self.output


try:
    from subprocess import CompletedProcess as _CompletedProcess

    class CompletedProcess(_CompletedProcess):
        pass


except ImportError:  # only added from python 3.5
    from collections import namedtuple

    class CompletedProcess(
        namedtuple("CompletedProcess", "args returncode stdout stderr")
    ):
        def check_returncode(self):
            if self.returncode:
                raise CalledProcessError(
                    self.returncode, self.args, self.stdout, self.stderr
                )


def _run(args, capture_output=False, check=False, **kwargs):
    if capture_output:
        if ("stdout" in kwargs) or ("stderr" in kwargs):
            raise ValueError(
                "stdout and stderr arguments may not be used with capture_output."
            )
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    process = subprocess.Popen(args, **kwargs)
    try:
        stdout, stderr = process.communicate()
    except:
        process.kill()
        process.wait()
        raise
    retcode = process.poll()
    if check and retcode:
        raise CalledProcessError(retcode, args, output=stdout, stderr=stderr)
    return CompletedProcess(args, retcode, stdout, stderr)


def sanitize(*args, **kwargs):
    """Run the embedded ots-sanitize executable with the list of positional
    arguments (strings).
    Return an ots.CompletedProcess object with the following attributes:
    args, returncode, stdout, stderr.
    If check=True, and the subprocess exits with a non-zero exit code, an
    ots.CalledProcessError exception will be raised.
    If capture_output=True, stdout and stderr will be captured.
    All extra keyword arguments are forwarded to subprocess.Popen constructor.
    """
    return _run([OTS_SANITIZE] + list(args), **kwargs)
