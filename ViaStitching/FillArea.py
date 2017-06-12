#!/usr/bin/python
#
#  FillArea.py
#
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

from __future__ import print_function
from pcbnew import *
import sys
import tempfile
import shutil
import os
import random
import pprint

"""#  This script fill all areas with Via (Via Stitching) is the area is on
# a specific net (by default /GND fallback to GND)
#
#
# Usage in pcbnew's python console:
#  First you neet to copy this file (named FillArea.py) in your kicad_plugins
# directory (~/.kicad_plugins/ on Linux)
# Launch pcbnew and open python console (last entry of Tools menu)
# Then enter the following line (one by one, Hit enter after each)
import FillArea
FillArea.FillArea().Run()


# Other example:
# You can add modifications to parameters by adding functions call:
FillArea.FillArea().SetDebug().SetNetname("GND").SetStepMM(1.27).SetSizeMM(0.6).SetDrillMM(0.3).SetClearanceMM(0.2).Run()

# with
# SetDebug: Activate debug mode (print evolution of the board in ascii art)
# SetNetname: Change the netname to consider for the filling
# (default is /GND or fallback to GND)
# SetStepMM: Change step between Via (in mm)
# SetSizeMM: Change Via copper size (in mm)
# SetDrillMM: Change Via drill hole size (in mm)
# SetClearanceMM: Change clearance for Via (in mm)

#  You can also use it in command line. In this case, the first parameter is
# the pcb file path. Default options are applied.

"""


class FillArea:
    """
    Automaticaly add via on area where there are no track/existing via,
    pads and keepout areas
    """

    def __init__(self, filename=None):
        self.filename = None
        self.clearance = 0
        # Net name to use
        self.SetPCB(GetBoard())
        # Set the filename
        self.SetFile(filename)
        # Step between via
        self.SetStepMM(2.54)
        # Size of the via (diameter of copper)
        self.SetSizeMM(0.35)
        # Size of the drill (diameter)
        self.SetDrillMM(0.30)
        # Isolation between via and other elements
        # ie: radius from the border of the via
        self.SetClearanceMM(0.2)
        self.only_selected_area = False
        self.delete_vias = False
        if self.pcb is not None:
            for lnet in ["GND", "/GND"]:
                if self.pcb.FindNet(lnet) is not None:
                    self.SetNetname(lnet)
                    break
        self.netname = None
        self.debug = False
        self.random = False
        if self.netname is None:
            self.SetNetname("GND")

        self.tmp_dir = None

    def SetFile(self, filename):
        self.filename = filename
        if self.filename:
            self.SetPCB(LoadBoard(self.filename))

    def SetDebug(self):
        self.debug = True
        return self

    def SetRandom(self):
        random.seed()
        self.random = True
        return self

    def SetPCB(self, pcb):
        self.pcb = pcb
        if self.pcb is not None:
            self.pcb.BuildListOfNets()
        return self

    def SetNetname(self, netname):
        self.netname = netname
        return self

    def SetStepMM(self, s):
        self.step = float(FromMM(s))
        return self

    def SetSizeMM(self, s):
        self.size = float(FromMM(s))
        return self

    def SetDrillMM(self, s):
        self.drill = float(FromMM(s))
        return self

    def OnlyOnSelectedArea(self):
        self.only_selected_area = True
        return self

    def DeleteVias(self):
        self.delete_vias = True
        return self

    def SetClearanceMM(self, s):
        self.clearance = float(FromMM(s))
        return self

    def PrintRect(self, rectangle):
        """debuging tool
        Print board in ascii art
        """
        for y in range(rectangle[0].__len__()):
            for x in range(rectangle.__len__()):
                print("%X" % rectangle[x][y], end='')
            print()
        print()

    def PrepareFootprint(self):
        """Don't use via since it's not possible to force a Net.
        So use a fake footprint (only one THPad)
        """
        self.tmp_dir = tempfile.mkdtemp(".pretty")
        module_txt = """(module VIA_MATRIX (layer F.Cu) (tedit 5862471A)
  (fp_text reference REF** (at 0 0) (layer F.SilkS) hide
    (effects (font (size 0 0) (thickness 0.0)))
  )
  (fp_text value VIA_MATRIX (at 0 0) (layer F.Fab) hide
    (effects (font (size 0 0) (thickness 0.0)))
  )
  (pad 1 thru_hole circle (at 0 0) (size 1.5 1.5) (drill 0.762) (layers *.Cu))
)"""

        # Create the footprint on a temp directory
        f = open(os.path.join(self.tmp_dir, "VIA_MATRIX.kicad_mod"), 'w')
        f.write(module_txt)
        f.close()

        plugin = IO_MGR.PluginFind(IO_MGR.KICAD)
        module = plugin.FootprintLoad(self.tmp_dir, "VIA_MATRIX")
        module.FindPadByName("1").SetSize(wxSize(self.size, self.size))
        module.FindPadByName("1").SetDrillSize(wxSize(self.drill, self.drill))
        module.FindPadByName("1").SetLocalClearance(int(self.clearance))
        module.FindPadByName("1").SetNet(self.pcb.FindNet(self.netname))
        module.FindPadByName("1").SetZoneConnection(PAD_ZONE_CONN_FULL)
        return module

    def CleanupFootprint(self):
        """
        cleanup temp footprint
        """
        if self.tmp_dir and os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def AddModule(self, module, position, x, y):
        m = MODULE(module)
        m.SetPosition(position)
        m.SetReference("V%s_%s" % (x, y))
        m.SetValue("AUTO_VIA")
        m.SetLastEditTime()
        m.thisown = 0
        self.pcb.AddNative(m, ADD_APPEND)
        m.SetFlag(IS_NEW)

    def RefillBoardAreas(self):
        for i in range(self.pcb.GetAreaCount()):
            area = self.pcb.GetArea(i)
            area.ClearFilledPolysList()
            area.UnFill()
            if not area.GetIsKeepout():
                area.BuildFilledSolidAreasPolygons(self.pcb)

    def Run(self):
        """
        Launch the process
        """

        if self.delete_vias:
            for module in self.pcb.GetModules():
                print("* Deleting module: %s" % module.GetValue())
                if module.GetValue() == "AUTO_VIA":
                    self.pcb.DeleteNative(module)
            self.RefillBoardAreas()
            return

        lboard = self.pcb.ComputeBoundingBox()
        rectangle = []
        origin = lboard.GetPosition()
        module = self.PrepareFootprint()

        # Create an initial rectangle: all is off
        # get a margin to avoid out of range
        # Values:
        #    0 => position is ok for via
        # != 0 => position is not ok.
        # Number is for debuging: check what feature is disabling this position
        l_clearance = self.step + self.clearance + self.size
        x_limit = int((lboard.GetWidth() + l_clearance) / self.step) + 1
        y_limit = int((lboard.GetHeight() + l_clearance) / self.step) + 1
        for x in range(0, x_limit):
            rectangle.append([])
            for y in range(0, y_limit):
                rectangle[x].append(0x8)

        if self.debug:
            print("Initial rectangle")
            self.PrintRect(rectangle)

        # Enum all area
        for i in range(self.pcb.GetAreaCount()):
            area = self.pcb.GetArea(i)
            # If use only selected area mode
            # only_selected_area | is selected | keepout | result
            #              False |           X |       X | True
            #               True |        True |       X | True
            #               True |       False |    True | True
            #               True |       False |   False | False
            if not (self.only_selected_area and not area.IsSelected() and not area.GetIsKeepout()):
                # Handle only area on same target net of keepout are
                if area.GetNetname() == self.netname or area.GetIsKeepout():
                    keepOutMode = area.GetIsKeepout()
                    for y in range(rectangle[0].__len__()):
                        for x in range(rectangle.__len__()):
                            testResult = not keepOutMode  # = False if is Keepout
                            offset = self.clearance + self.size / 2
                            #offset = int(self.inter / 2)
                            # For keepout area: Deny Via
                            # For same net area: Allow if not denied by keepout
                            current_x = origin.x + (x * self.step)
                            current_y = origin.y + (y * self.step)
                            for dx in [-offset, offset]:
                                for dy in [-offset, offset]:
                                    r = area.HitTestFilledArea(wxPoint(current_x + dx,
                                                                       current_y + dy))
                                    if keepOutMode:
                                        testResult |= r
                                    else:
                                        testResult &= r

                                        if keepOutMode:
                                            testResult |= r
                                        else:
                                            testResult &= r
                                            if testResult:
                                                if keepOutMode:
                                                    rectangle[x][y] = 0x1
                                                else:
                                                    # Allow only if it's first step disabling
                                                    # ie: keepout are keeped
                                                    if rectangle[x][y] == 0x8:
                                                        rectangle[x][y] = 0

        if self.debug:
            print("Post Area handling")
            self.PrintRect(rectangle)

        # Same job with all pads
        for pad in self.pcb.GetPads():
            local_offset = max(pad.GetClearance(),
                               self.clearance) + self.size / 2
            max_size = max(pad.GetSize().x, pad.GetSize().y)
            start_x = int(floor(((pad.GetPosition().x - (max_size / 2.0 +
                                                         local_offset)) - origin.x) / self.step))
            stop_x = int(ceil(((pad.GetPosition().x + (max_size / 2.0 +
                                                       local_offset)) - origin.x) / self.step))

            start_y = int(floor(((pad.GetPosition().y - (max_size / 2.0 +
                                                         local_offset)) - origin.y) / self.step))
            stop_y = int(ceil(((pad.GetPosition().y + (max_size / 2.0 +
                                                       local_offset)) - origin.y) / self.step))

            for x in range(start_x, stop_x + 1):
                for y in range(start_y, stop_y + 1):
                    start_rect = wxPoint(origin.x + (self.step * x) -
                                         local_offset,
                                         origin.y + (self.step * y) -
                                         local_offset)
                    size_rect = wxSize(2 * local_offset, 2 * local_offset)
                    if pad.HitTest(EDA_RECT(start_rect, size_rect), False):
                        rectangle[x][y] |= 0x2

        # Same job with tracks
        for track in self.pcb.GetTracks():
            start_x = track.GetStart().x
            start_y = track.GetStart().y

            stop_x = track.GetEnd().x
            stop_y = track.GetEnd().y

            if start_x > stop_x:
                d = stop_x
                stop_x = start_x
                start_x = d

            if start_y > stop_y:
                d = stop_y
                stop_y = start_y
                start_y = d

            osx = start_x
            osy = start_y
            opx = stop_x
            opy = stop_y

            clearance = max(track.GetClearance(), self.clearance) + \
                self.size / 2 + track.GetWidth() / 2

            start_x = int(floor(((start_x - clearance) -
                                 origin.x) / self.step))
            stop_x = int(ceil(((stop_x + clearance) - origin.x) / self.step))

            start_y = int(floor(((start_y - clearance) -
                                 origin.y) / self.step))
            stop_y = int(ceil(((stop_y + clearance) - origin.y) / self.step))

            for x in range(start_x, stop_x + 1):
                for y in range(start_y, stop_y + 1):
                    start_rect = wxPoint(origin.x + (self.step * x) -
                                         clearance,
                                         origin.y + (self.step * y) -
                                         clearance)
                    size_rect = wxSize(2 * clearance, 2 * clearance)
                    if track.HitTest(EDA_RECT(start_rect, size_rect), False):
                        rectangle[x][y] |= 0x4

        if self.debug:
            print("Post Pad + tracks")
            self.PrintRect(rectangle)

        # Same job with existing text
        for draw in self.pcb.m_Drawings:
            if (draw.GetClass() == 'PTEXT' and
                    self.pcb.GetLayerID(draw.GetLayerName()) in (F_Cu, B_Cu)):
                inter = float(self.clearance + self.size)
                bbox = draw.GetBoundingBox()
                start_x = int(floor(((bbox.GetPosition().x - inter) -
                                     origin.x) / self.step))
                stop_x = int(ceil(((bbox.GetPosition().x +
                                    (bbox.GetSize().x + inter)) -
                                   origin.x) / self.step))

                start_y = int(floor(((bbox.GetPosition().y - inter) -
                                     origin.y) / self.step))
                stop_y = int(ceil(((bbox.GetPosition().y +
                                    (bbox.GetSize().y + inter)) -
                                   origin.y) / self.step))

                for x in range(start_x, stop_x + 1):
                    for y in range(start_y, stop_y + 1):
                        rectangle[x][y] |= 0xA

        if self.debug:
            print("Post Drawnings: final result (0: mean ok for a via)")
            self.PrintRect(rectangle)

        for y in range(rectangle[0].__len__()):
            for x in range(rectangle.__len__()):
                if rectangle[x][y] == 0:
                    ran_x = 0
                    ran_y = 0
                    if self.random:
                        ran_x = (random.random() * self.step / 2.0) - \
                            (self.step / 4.0)
                        ran_y = (random.random() * self.step / 2.0) - \
                            (self.step / 4.0)
                    self.AddModule(module, wxPoint(origin.x + (self.step * x) + ran_x,
                                                   origin.y + (self.step * y) + ran_y), x, y)

        self.RefillBoardAreas()

        if self.filename:
            self.pcb.Save(self.filename)
        self.CleanupFootprint()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s <KiCad pcb filename>" % sys.argv[0])
    else:
        import sys
        FillArea(sys.argv[1]).SetDebug().Run()
