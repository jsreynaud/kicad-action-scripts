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
import math
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
                x = int(round(x_i * self.centre_spacing + self.x_range[0]))
                y = int(round(y_i * self.centre_spacing + self.y_range[0]))
                if self.valid_predicate(x, y):
                    points.append((x, y))
        
        return points


class BridsonFillStrategy(FillStrategy):
    """
    This fill stragegy implements Bridsons Poisson disc sampling algorithm to generate
    randomly spaced points that are roughly uniformly spaced.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.k = 10

        # Start with a grid we can use for localised searching. Cell spacing is centre_spacing / sqrt(2)
        # such that no more than one point can end up in a cell.
        self._cell_size = self.centre_spacing / math.sqrt(2)
        self._x_steps = int((self.x_range[1] - self.x_range[0]) / self._cell_size)
        self._y_steps = int((self.y_range[1] - self.y_range[0]) / self._cell_size)
        self._checked = [[False] * self._x_steps for i in range(self._y_steps)]
        self._points = [[None] * self._x_steps for i in range(self._y_steps)]


    def generate_points(self):
        active = []
        for i in range(self._y_steps):
            for j in range(self._x_steps):
                if self._checked[i][j]:
                    continue
                else:
                    # Generate up to k random points in this cell until one is valid.
                    for _ in range(self.k):
                        point = self._generate_random_point_in_cell(i, j)
                        if self._is_valid(point):
                            self._points[i][j] = point
                            active.append(point)
                            break
                    self._checked[i][j] = True
                
                while active:
                    # If we have active points, do the Poisson disc sampling
                    base = active.pop()
                    for _ in range(self.k):
                        point = self._generate_random_point_in_disc(base)
                        if self._is_valid(point):
                            x_i, y_i = self._cell_index(point)
                            self._points[y_i][x_i] = point
                            active.append(point)
                            self._checked[y_i][x_i] = True

        
        points = []
        for row in self._points:
            for point in row:
                if point:
                    points.append(point)
        
        return points
    
    def _cell_index(self, point):
        x_i = math.floor((point[0] - self.x_range[0]) / self._cell_size)
        y_i = math.floor((point[1] - self.y_range[0]) / self._cell_size)
        return (x_i, y_i)
    
    def _is_valid(self, point):
        # Get the cell index for this point
        x_i, y_i = self._cell_index(point)

        # Check we're in bounds
        if x_i < 0 or x_i >= self._x_steps or y_i < 0 or y_i >= self._y_steps:
            return False
        
        # Check there isn't already a point in this cell
        if self._points[y_i][x_i]:
            return False
        
        # Check surrounding points
        for ox_i, oy_i in ((-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-2, 0), (0, 2), (2, 0), (0, -2)):
            px_i = x_i + ox_i
            py_i = y_i + oy_i
            if px_i < 0 or px_i >= self._x_steps or py_i < 0 or py_i >= self._y_steps:
                continue
            nbr = self._points[py_i][px_i]
            if nbr and math.sqrt((nbr[0] - point[0]) ** 2 + (nbr[1] - point[1]) ** 2) < self.centre_spacing:
                return False
        
        # Finally, check the predicate
        return self.valid_predicate(*point)
    
    def _generate_random_point_in_cell(self, i, j):
        x = self.x_range[0] + (j + random.random()) * self._cell_size
        y = self.y_range[0] + (i + random.random()) * self._cell_size
        return (int(round(x)), int(round(y)))
    
    def _generate_random_point_in_disc(self, base):
        r = math.sqrt(3 * random.random() + 1) * self.centre_spacing
        th = random.uniform(0, math.pi)
        return (int(round(base[0] + r * math.sin(th))), int(round(base[1] + r * math.cos(th))))


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
        points = BridsonFillStrategy(x_range, y_range, valid_predicate, self.step).generate_points()
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
