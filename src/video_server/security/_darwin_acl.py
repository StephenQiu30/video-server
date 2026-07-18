"""Fail-closed Darwin extended ACL inspection."""

from __future__ import annotations

import ctypes
import errno
import sys

_ACL_TYPE_EXTENDED = 0x100


def ensure_no_extended_acl(descriptor: int) -> None:
    """Reject any Darwin extended ACL attached to an open file."""

    if sys.platform != "darwin":
        return

    try:
        system = ctypes.CDLL(None, use_errno=True)
        get_acl = system.acl_get_fd_np
        free_acl = system.acl_free
    except (AttributeError, OSError) as error:
        raise ValueError("Darwin ACL inspection is unavailable") from error

    get_acl.argtypes = [ctypes.c_int, ctypes.c_int]
    get_acl.restype = ctypes.c_void_p
    free_acl.argtypes = [ctypes.c_void_p]
    free_acl.restype = ctypes.c_int

    ctypes.set_errno(0)
    acl = get_acl(descriptor, _ACL_TYPE_EXTENDED)
    if not acl:
        error_number = ctypes.get_errno()
        if error_number == errno.ENOENT:
            return
        raise ValueError("Darwin extended ACL could not be inspected")

    if free_acl(acl) != 0:
        raise ValueError("Darwin extended ACL could not be released")
    raise ValueError("secret file must not have a Darwin extended ACL")
