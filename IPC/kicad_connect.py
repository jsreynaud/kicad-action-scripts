#
#  kicad_connect.py
#
#  Robust connection helper for KiCad IPC API plugins.
#
#  Works around https://gitlab.com/kicad/code/kicad/-/issues/20880:
#  on Windows the Project Manager and the PCB editor can run as separate
#  processes that both claim the default API socket name. The plugin is
#  launched by the PCB editor but the connection may be answered by the
#  Project Manager, whose token does not match and which cannot serve
#  board commands.
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.

import glob
import os
import stat
import tempfile

from kipy import KiCad

WORKAROUND_APPLIED_HINT = (
    "Could not reach the PCB editor over the IPC API.\n\n"
    "This is a known KiCad issue on Windows (gitlab issue #20880): when the "
    "Project Manager and the PCB editor run as separate processes, the "
    "Project Manager owns the API socket but cannot serve board commands.\n\n"
    "A workaround file has been installed automatically ({path}).\n"
    "Please close ALL KiCad windows, start KiCad again as usual and run "
    "the plugin once more - it should then work permanently.\n"
)

WORKAROUND_MANUAL_HINT = (
    "Could not reach the PCB editor over the IPC API.\n\n"
    "This can be a known KiCad issue on Windows (gitlab issue #20880). "
    "See the plugin's README.md for a workaround, or open the board in "
    "the standalone PCB editor (double-click the .kicad_pcb file) without "
    "starting the Project Manager.\n"
)


def _dummy_socket_file():
    return os.path.join(tempfile.gettempdir(), "kicad", "api.sock")


def install_windows_socket_workaround():
    """Create a read-only dummy file at the default API socket path.

    KiCad's per-process socket fallback (api-<PID>.sock) only triggers
    when a file exists at the default path, which never happens on
    Windows because the socket is a named pipe there. With the dummy
    file in place, every KiCad process binds its own PID-suffixed pipe
    and passes the correct path to its plugins.

    Returns the file path if the file was newly created, else None.
    """
    if os.name != "nt":
        return None
    path = _dummy_socket_file()
    if os.path.exists(path):
        return None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(
                "Dummy file: forces KiCad to use per-process api-<PID>.sock "
                "pipes on Windows (workaround for "
                "gitlab.com/kicad/code/kicad issue 20880). Do not delete.\n"
            )
        os.chmod(path, stat.S_IREAD)
        return path
    except OSError:
        return None


def _socket_candidates():
    """Possible API socket paths of running KiCad instances, most
    specific first."""
    candidates = []

    env_socket = os.environ.get("KICAD_API_SOCKET")
    if env_socket:
        candidates.append(env_socket)

    if os.name == "nt":
        # Enumerate named pipes; KiCad pipes are named after the
        # default socket path (e.g. C:\...\Temp\kicad\api.sock or
        # api-<PID>.sock for secondary instances)
        try:
            for name in os.listdir("\\\\.\\pipe\\"):
                if "kicad" in name.lower() and name.lower().endswith(".sock"):
                    candidates.append("ipc://" + name)
        except OSError:
            pass
    else:
        # Unix domain sockets are real files below the temp directory
        pattern = os.path.join(tempfile.gettempdir(), "kicad", "api*.sock")
        candidates.extend("ipc://" + path for path in sorted(glob.glob(pattern)))

    seen = set()
    unique = []
    for c in candidates:
        key = c.replace("ipc://", "")
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def connect_to_kicad(client_name=None):
    """Connect to the KiCad instance that actually has a board open.

    Tries the environment-provided socket/token first, then all
    discoverable KiCad API sockets, each with and without the token.
    Returns (kicad, board) or raises RuntimeError with a diagnosis and
    workaround instructions.
    """
    env_token = os.environ.get("KICAD_API_TOKEN") or ""
    attempts = []

    tokens = [env_token, ""] if env_token else [""]
    for token in tokens:
        for socket_path in _socket_candidates() or [None]:
            try:
                kicad = KiCad(
                    socket_path=socket_path,
                    client_name=client_name,
                    kicad_token=token,
                )
                board = kicad.get_board()
                return kicad, board
            except BaseException as e:
                attempts.append(
                    "  - {} (token {}): {}".format(
                        socket_path or "<default>",
                        "from env" if token else "disabled",
                        str(e).strip() or type(e).__name__,
                    )
                )

    installed = install_windows_socket_workaround()
    if installed:
        hint = WORKAROUND_APPLIED_HINT.format(path=installed)
    else:
        hint = WORKAROUND_MANUAL_HINT
    raise RuntimeError(hint + "\nConnection attempts:\n" + "\n".join(attempts))
