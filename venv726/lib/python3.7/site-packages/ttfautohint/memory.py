import sys
from ctypes import cdll, c_size_t, c_void_p, CFUNCTYPE
from ctypes.util import find_library


# we load the libc to get the standard malloc and free functions.
# They will be used anyway by libttfautohint if we didn't provide the
# 'alloc-func' and 'free-func' callbacks. However, by explicitly passing
# them, we ensure that both libttfautohint and cytpes will use the same
# memory allocation functions. E.g. on Windows, a DLL may be linked
# with a different version of the C runtime library than the application
# which loads the DLL.
if sys.platform == "win32":
    libc = cdll.msvcrt
else:
    libc_path = find_library("c")
    if libc_path is None:
        raise OSError("Could not find the libc shared library")
    libc = cdll.LoadLibrary(libc_path)

malloc = libc.malloc
malloc.argtypes = [c_size_t]
malloc.restype = c_void_p

free = libc.free
free.argtypes = [c_void_p]
free.restype = None

realloc = libc.realloc
realloc.argtypes = [c_void_p, c_size_t]
realloc.restype = c_void_p

TA_Alloc_Func_Proto = CFUNCTYPE(c_void_p, c_size_t)
alloc_callback = TA_Alloc_Func_Proto(lambda size: malloc(size))

TA_Free_Func_Proto = CFUNCTYPE(None, c_void_p)
free_callback = TA_Free_Func_Proto(lambda p: free(p))
