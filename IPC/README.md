# IPC API version (KiCad 10+, future-proof)

This directory contains a port of the ViaStitching and CircularZone
plugins to the KiCad **IPC API** using the officially maintained
[kicad-python](https://gitlab.com/kicad/code/kicad-python) (`kipy`)
bindings.

Background: the classic SWIG based python bindings (used by the plugins
in `ViaStitching/` and `CircularZone/`) are deprecated since KiCad 9
and are planned to be **removed in KiCad 11**. The IPC API is the
stable, versioned replacement, so this port should keep working across
future major versions without changes.

## Requirements

- KiCad 9.0.1 or newer (KiCad 10 recommended)
- The IPC API server must be enabled:
  *Preferences → Plugins → Enable KiCad API server*

## Installation

Copy this `IPC` directory into KiCad's plugin directory:

- Windows: `%USERPROFILE%\Documents\KiCad\<version>\plugins\`
- Linux: `~/.local/share/kicad/<version>/plugins/`
- macOS: `~/Documents/KiCad/<version>/plugins/`

On the first start KiCad creates a private Python virtual environment
for the plugin and installs the dependencies from `requirements.txt`
(`kicad-python`, `wxPython`, `shapely`). This can take a few minutes;
the toolbar buttons appear once the environment is ready.

## Windows: token mismatch error when started from the Project Manager

On Windows, KiCad 10 runs the Project Manager and the PCB editor as
separate processes that both bind the API socket name `api.sock`
(upstream issue
[#20880](https://gitlab.com/kicad/code/kicad/-/issues/20880)). Plugins
launched from the PCB editor then reach the Project Manager instead
and fail with *"the provided kicad_token did not match this KiCad
instance's token"*.

KiCad's built-in fallback (binding `api-<PID>.sock` per process) only
triggers when a *file* named `api.sock` exists, which never happens on
Windows because the socket is a named pipe. Workaround until the issue
is fixed upstream: create a read-only dummy file at that path once
(all KiCad windows closed):

```powershell
New-Item -ItemType Directory -Force "$env:TEMP\kicad" | Out-Null
Set-Content "$env:TEMP\kicad\api.sock" "dummy - see KiCad issue 20880" -Encoding ascii
Set-ItemProperty "$env:TEMP\kicad\api.sock" -Name IsReadOnly -Value $true
```

Every KiCad process then binds its own `api-<PID>.sock` pipe and hands
the correct path to its plugins; the normal Project Manager workflow
works. Verified with KiCad 10.0.4.

## Differences to the SWIG version

- Geometry checks (zone outlines, tracks, pads, board edge, keep-outs)
  are computed with [shapely](https://shapely.readthedocs.io/) on the
  outlines reported by the IPC API instead of KiCad's internal hit-test
  functions. Results can differ marginally at the clearance boundary.
- Pad clearance uses the exact pad polygon shapes on the outer copper
  layers plus the user-provided via clearance; per-pad local clearance
  overrides are not queried.
- **Deleting stitching vias works directly** from the dialog now
  ("Delete Vias" removes the named group and its members in a single
  undo step) — no manual group selection needed anymore.
- Zone refill is performed through the API when "Refill zones when
  done" is checked.
