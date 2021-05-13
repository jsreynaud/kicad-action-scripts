#!/usr/bin/python
# -*- coding: utf-8 -*-
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
import wx


def wxPrint(msg):
    wx.LogMessage(msg)


#
if sys.version[0] == '2':  # maui
    xrange
else:
    xrange = range


"""
#  This script fills all areas of a specific net with Vias (Via Stitching)
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
# You can add modifications to parameters by adding functions calls:
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


class FillStrategy:
    def __init__(self, x_range, y_range, valid_predicate, centre_spacing):
        self.x_range = x_range
        self.y_range = y_range
        self.valid_predicate = valid_predicate
        self.centre_spacing = centre_spacing
    
    def generate_points(self):
        raise NotImplementedError


class GridFillStrategy(FillStrategy):
    def generate_points(self):
        x_steps = int((self.x_range[1] - self.x_range[0]) / self.centre_spacing) + 1
        y_steps = int((self.y_range[1] - self.y_range[0]) / self.centre_spacing) + 1

        points = []
        for x_i in range(x_steps):
            for y_i in range(y_steps):
                x = int(x_i * self.centre_spacing + self.x_range[0] + 0.5)
                y = int(y_i * self.centre_spacing + self.y_range[0] + 0.5)
                if self.valid_predicate(x, y):
                    points.append((x, y))
        
        return points


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
        self.SetSizeMM(0.46)
        # Size of the drill (diameter)
        self.SetDrillMM(0.20)
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
        self.star = False
        if self.netname is None:
            self.SetNetname("GND")

        self.tmp_dir = None

    def SetFile(self, filename):
        self.filename = filename
        if self.filename:
            self.SetPCB(LoadBoard(self.filename))

    def SetDebug(self):
        wxPrint("Set debug")
        self.debug = True
        return self

    def SetRandom(self, r):
        random.seed()
        self.random = r
        return self

    def SetStar(self):
        self.star = True
        return self

    def SetPCB(self, pcb):
        self.pcb = pcb
        if self.pcb is not None:
            self.pcb.BuildListOfNets()
        return self

    def SetNetname(self, netname):
        self.netname = netname  # .upper()
        # wx.LogMessage(self.netname)
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

    def AddVia(self, position):
        m = VIA(self.pcb)
        m.SetPosition(position)
        m.SetNet(self.pcb.FindNet(self.netname))
        m.SetViaType(VIA_THROUGH)
        m.SetDrill(int(self.drill))
        m.SetWidth(int(self.size))
        # again possible to mark via as own since no timestamp_t binding kicad v5.1.4
        m.SetTimeStamp(33)  # USE 33 as timestamp to mark this via as generated by this script
        #wx.LogMessage('adding vias')
        self.pcb.Add(m)

    def RefillBoardAreas(self):
        for i in range(self.pcb.GetAreaCount()):
            area = self.pcb.GetArea(i)
            area.ClearFilledPolysList()
            area.UnFill()
        filler = ZONE_FILLER(self.pcb)
        filler.Fill(self.pcb.Zones())

    def Run(self):
        """
        Launch the process
        """

        all_areas = [self.pcb.GetArea(i) for i in xrange(self.pcb.GetAreaCount())]
        target_areas = filter(lambda x: (x.GetNetname() == self.netname and (x.IsOnLayer(F_Cu) or x.IsOnLayer(B_Cu)) and not x.GetIsKeepout()), all_areas)

        # Validate that we don't have any top/bottom no-net layers already. If we do, we can't run this as we'd mess
        # them up when switching the net back.
        if any(filter(lambda x: (x.GetNetname() == '' and (x.IsOnLayer(F_Cu) or x.IsOnLayer(B_Cu)) and not x.GetIsKeepout()), all_areas)):
            wxPrint("Sorry, we can't run via stitching if there are no-net zones on top/bottom copper layers.")
            return
        
        # Change the net of the target areas to "No Net" and refill. That way we'll get a full fill
        # including islands
        for area in target_areas:
            area.SetNet(self.pcb.GetNetsByName()[''])
        self.RefillBoardAreas()

        # Search for areas on top/bottom layers
        all_areas = [self.pcb.GetArea(i) for i in xrange(self.pcb.GetAreaCount())]
        top_areas = filter(lambda x: (x.GetNetname() == '' and x.IsOnLayer(F_Cu) and not x.GetIsKeepout()), all_areas)
        bot_areas = filter(lambda x: (x.GetNetname() == '' and x.IsOnLayer(B_Cu) and not x.GetIsKeepout()), all_areas)
        
        # Calculate where it'd be valid to put vias that hit both top/bottom layers in the
        # filled areas, without the annulus going outside of them.
        valid = self._get_valid_placement_area(top_areas)
        valid.BooleanIntersection(self._get_valid_placement_area(bot_areas), SHAPE_POLY_SET.PM_STRICTLY_SIMPLE)
        
        
        # Place vias in a grid wherever we can.
        bounds = self.pcb.GetBoundingBox()
        x_range = (bounds.GetLeft(), bounds.GetRight())
        y_range = (bounds.GetTop(), bounds.GetBottom())
        valid_predicate = lambda x, y: valid.Contains(VECTOR2I(x, y))
        points = GridFillStrategy(x_range, y_range, valid_predicate, self.step).generate_points()
        for x, y in points:
            self.AddVia(wxPoint(x, y))

        # Reset target area nets to original and refill
        all_areas = [self.pcb.GetArea(i) for i in xrange(self.pcb.GetAreaCount())]
        target_areas = filter(lambda x: (x.GetNetname() == '' and (x.IsOnLayer(F_Cu) or x.IsOnLayer(B_Cu)) and not x.GetIsKeepout()), all_areas)
        for area in target_areas:
            area.SetNet(self.pcb.GetNetsByName()[self.netname])
        self.RefillBoardAreas()
    
    def _get_valid_placement_area(self, areas):
        # Get some polygons for top/bottom with a buffer.
        valid = SHAPE_POLY_SET()

        for area in areas:
            # Clone and inflate polys by the min width / 2. KiCAD seems to store them as polygons
            # with a line width, not as polys with a 0 line width.
            poly = SHAPE_POLY_SET(area.GetFilledPolysList(), True)
            poly.Inflate(area.GetMinThickness() // 2, 36)
            valid.BooleanAdd(poly, SHAPE_POLY_SET.PM_STRICTLY_SIMPLE)
        
        # Deflate by our via radius, and we have polygon encompassing where we can place via centers on the top.
        valid.Inflate(-int(self.size) // 2, 36)

        return valid


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s <KiCad pcb filename>" % sys.argv[0])
    else:
        import sys
        FillArea(sys.argv[1]).SetDebug().Run()
