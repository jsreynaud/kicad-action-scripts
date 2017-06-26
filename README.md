# Some KiCad plugins in Python

Thoses plugins must be copied inside KiCad's python plugins
directory (~/.kicad_plugins or /usr/share/kicad/scripting/plugins/ for
Linux).
Most of them use python plugin (Action plugins) in KiCad. This feature
is enabled in daily builds of KiCad.
See https://forum.kicad.info/t/howto-register-a-python-plugin-inside-pcbnew-tools-menu/5540


## ViaStitching

A pure python via stitching.

After select "Via Stitching" in Tools menu, choose your options in the
interface.

![The interface](images/via1.png)

Then the result should be:

![The result](images/via2.png)

## CircularZone

A pure python script to create circular zone.

Select a component. This composent will be used as center of the
circular zone. If no component is selected, the origin (0,0) will be
used as center.

After select "Create a circular zone" in the Tools menu, choose the
radius and the type of zone (normal or keep out).

![The interface](image/circular1.png)

A circular zone will be created. Select it to change properties:

![Select zone](image/circular2.png)

![Open properties](image/circular3.png)

Refill the area (B hotkey) then the circular zone is ready.

![Final result](image/circular4.png)
