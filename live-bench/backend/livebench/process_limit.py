# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Resource and network restrictions for untrusted document subprocesses."""

import ctypes
import errno
import os
import resource
import socket
import sys

from livebench.models import MAX_FILE_BYTES


def restrict_network():
    if sys.platform != "linux":
        return
    lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]

    class Comparison(ctypes.Structure):
        _fields_ = [
            ("arg", ctypes.c_uint),
            ("op", ctypes.c_int),
            ("datum_a", ctypes.c_uint64),
            ("datum_b", ctypes.c_uint64),
        ]

    context = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError("unable to initialize parser network isolation")
    try:
        for family in (socket.AF_INET, socket.AF_INET6, socket.AF_PACKET):
            comparison = Comparison(0, 4, family, 0)  # SCMP_CMP_EQ
            result = lib.seccomp_rule_add(
                context,
                0x00050000 | errno.EPERM,
                lib.seccomp_syscall_resolve_name(b"socket"),
                1,
                comparison,
            )
            if result:
                raise RuntimeError("unable to install parser network isolation")
        if lib.seccomp_load(context):
            raise RuntimeError("unable to load parser network isolation")
    finally:
        lib.seccomp_release(context)


if __name__ == "__main__":
    timeout = int(sys.argv[1])
    resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    restrict_network()
    os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
