# Some KiCad plugins in Python

Thoses plugins must be copied inside KiCad's python plugins
directory (~/.kicad_plugins or /usr/share/kicad/scripting/plugins/ for
Linux).
Most of them use python plugin (Action plugins) in KiCad. This feature
is enabled in daily builds of KiCad.
See https://forum.kicad.info/t/howto-register-a-python-plugin-inside-pcbnew-tools-menu/5540


## ViaStiching

A pure python via stiching.

After select "Via Stiching" in Tools menu, choose your options in the
interface.

[The interface](images/via1.png)

Then the result should be:

[The result](images/via2.png)
