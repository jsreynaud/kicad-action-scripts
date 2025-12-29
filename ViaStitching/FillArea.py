#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  FillArea.py
#  Via stitching with spatial indexing, nudge search, and progress dialog
#
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com>
#  Copyright 2025 Geoff Wall / Ceres Imaging (enhancements)
#
#  Enhancements:
#  - Spatial hash indexing for O(1) collision detection
#  - Spiral nudge search to find valid positions when grid points blocked
#  - Progress dialog with cancel button
#  - Numbered groups for each run ("ViaStitching GND #1", "#2", etc.)
#  - Hole clearance parameter for drill-to-drill spacing
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
from builtins import abs
import sys
import tempfile
import shutil
import os
import random
import pprint
import wx
from inspect import currentframe, getframeinfo
import time
import math


def wxPrint(msg):
    wx.LogMessage(msg)


#
if sys.version[0] == "2":  # maui
    None
else:
    xrange = range


class SpatialHash:
    """
    Spatial hash for O(1) collision detection.
    Divides the board into a grid of cells, each containing references
    to objects that overlap that cell.
    """

    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.cells = {}  # (cx, cy) -> list of (x, y, radius, obj_type)

    def _get_cell(self, x, y):
        """Get cell coordinates for a point"""
        return (int(x // self.cell_size), int(y // self.cell_size))

    def _get_cells_for_circle(self, x, y, radius):
        """Get all cells that a circle overlaps"""
        min_cx = int((x - radius) // self.cell_size)
        max_cx = int((x + radius) // self.cell_size)
        min_cy = int((y - radius) // self.cell_size)
        max_cy = int((y + radius) // self.cell_size)
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                yield (cx, cy)

    def insert(self, x, y, radius, obj_type="obstacle"):
        """Insert an obstacle (circle) into the spatial hash"""
        for cell in self._get_cells_for_circle(x, y, radius):
            if cell not in self.cells:
                self.cells[cell] = []
            self.cells[cell].append((x, y, radius, obj_type))

    def insert_rect(self, x1, y1, x2, y2, obj_type="obstacle"):
        """Insert a rectangular obstacle"""
        # Ensure proper ordering
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        min_cx = int(x1 // self.cell_size)
        max_cx = int(x2 // self.cell_size)
        min_cy = int(y1 // self.cell_size)
        max_cy = int(y2 // self.cell_size)

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                cell = (cx, cy)
                if cell not in self.cells:
                    self.cells[cell] = []
                # Store as rect: (x1, y1, x2, y2, "rect", obj_type)
                self.cells[cell].append((x1, y1, x2, y2, "rect", obj_type))

    def insert_zone(self, zone, obj_type="zone"):
        """Insert a zone/rule area using its bounding box for spatial indexing"""
        bbox = zone.GetBoundingBox()
        x1, y1 = bbox.GetX(), bbox.GetY()
        x2, y2 = x1 + bbox.GetWidth(), y1 + bbox.GetHeight()

        min_cx = int(x1 // self.cell_size)
        max_cx = int(x2 // self.cell_size)
        min_cy = int(y1 // self.cell_size)
        max_cy = int(y2 // self.cell_size)

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                cell = (cx, cy)
                if cell not in self.cells:
                    self.cells[cell] = []
                # Store zone reference for precise testing later
                self.cells[cell].append(("zone", zone, obj_type))

    def check_collision(self, x, y, radius):
        """Check if a circle at (x,y) with given radius collides with any obstacle"""
        for cell in self._get_cells_for_circle(x, y, radius):
            if cell in self.cells:
                for item in self.cells[cell]:
                    if len(item) == 3 and item[0] == "zone":
                        # Zone items are handled by check_keepout_zones, skip here
                        continue
                    elif len(item) == 6 and item[4] == "rect":
                        # Rectangle collision
                        x1, y1, x2, y2, _, obj_type = item
                        # Check if circle center + radius overlaps rectangle
                        closest_x = max(x1, min(x, x2))
                        closest_y = max(y1, min(y, y2))
                        dist_sq = (x - closest_x) ** 2 + (y - closest_y) ** 2
                        if dist_sq <= radius * radius:
                            return True
                    elif len(item) == 4:
                        # Circle collision
                        ox, oy, oradius, obj_type = item
                        dist_sq = (x - ox) ** 2 + (y - oy) ** 2
                        min_dist = radius + oradius
                        if dist_sq <= min_dist * min_dist:
                            return True
        return False

    def check_keepout_zones(self, x, y):
        """Check if point (x,y) is inside any keepout zone. Returns the zone or None."""
        cell = self._get_cell(x, y)
        if cell in self.cells:
            for item in self.cells[cell]:
                if len(item) == 3 and item[0] == "zone":
                    _, zone, obj_type = item
                    if obj_type == "keepout":
                        # Do precise point-in-polygon test
                        point = VECTOR2I(int(x), int(y))
                        try:
                            if zone.HitTestInsideZone(point):
                                return zone
                        except:
                            # Fallback: check outline
                            try:
                                for i in range(zone.Outline().OutlineCount()):
                                    outline = zone.Outline().Outline(i)
                                    if outline.PointInside(point):
                                        return zone
                            except:
                                pass
        return None


class ViaObject:
    """
    ViaObject holds all information of a single Via
    """

    def __init__(self, x, y, pos_x, pos_y):
        self.X = x
        self.Y = y
        self.PosX = pos_x
        self.PosY = pos_y


class FillArea:
    """
    Automatically add vias on area where there are no tracks/existing vias,
    pads and keepout areas.

    Enhanced with:
    - Spatial hash indexing for O(1) collision detection
    - Nudge search to find valid positions near blocked grid points
    - Progress dialog with cancel support
    - Numbered groups for easier management
    """

    REASON_OK = 0
    REASON_NO_SIGNAL = 1
    REASON_OTHER_SIGNAL = 2
    REASON_KEEPOUT = 3
    REASON_TRACK = 4
    REASON_PAD = 5
    REASON_DRAWING = 6
    REASON_STEP = 7

    FILL_TYPE_RECTANGULAR = "Rectangular"
    FILL_TYPE_STAGGERED = "Staggered"
    FILL_TYPE_CONCENTRIC = "Concentric"
    FILL_TYPE_OUTLINE = "Outline"
    FILL_TYPE_OUTLINE_NO_HOLES = "Outline (No Holes)"

    def __init__(self, filename=None):
        self.filename = None
        self.clearance = 0
        self.hole_clearance = 0  # Enhancement: separate hole-to-hole clearance
        self.nudge_enabled = True  # Enhancement: nudge search
        self.ignored_layers = []  # Enhancement: layers to ignore during placement
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
        self.SetHoleClearanceMM(0.5)  # Default 0.5mm hole clearance
        self.only_selected_area = False
        self.delete_vias = False
        self.same_net_tracks = False
        if self.pcb is not None:
            for lnet in ["GND", "/GND"]:
                if self.pcb.FindNet(lnet) is not None:
                    self.SetNetname(lnet)
                    break
        self.netname = None
        self.debug = False
        self.random = False
        self.fill_type = self.FILL_TYPE_RECTANGULAR
        if self.netname is None:
            self.SetNetname("GND")

        self.tmp_dir = None
        self.parent_area = None
        self.pcb_group = None
        self.target_net = None
        self.spatial_hash = None  # Enhancement: spatial indexing
        self.progress_dialog = None  # Enhancement: progress dialog
        self.cancelled = False

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

    def SetIgnoredLayers(self, layer_names):
        """Set list of layer names to ignore during via placement"""
        self.ignored_layers = layer_names if layer_names else []
        return self

    def SetSameNetTracks(self, r):
        self.same_net_tracks = r
        return self

    def SetType(self, type):
        self.fill_type = type
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

    # Enhancement: hole clearance
    def SetHoleClearanceMM(self, s):
        """Set minimum hole-to-hole clearance in mm"""
        self.hole_clearance = float(FromMM(s))
        return self

    # Enhancement: nudge search toggle
    def SetNudgeEnabled(self, enabled):
        """Enable/disable nudge search for blocked grid positions"""
        self.nudge_enabled = enabled
        return self

    def GetReasonSymbol(self, reason):
        if isinstance(reason, ViaObject):
            return "X"
        if reason == self.REASON_NO_SIGNAL:
            return " "
        if reason == self.REASON_OTHER_SIGNAL:
            return "O"
        if reason == self.REASON_KEEPOUT:
            return "K"
        if reason == self.REASON_TRACK:
            return "T"
        if reason == self.REASON_PAD:
            return "P"
        if reason == self.REASON_DRAWING:
            return "D"
        if reason == self.REASON_STEP:
            return "-"

        return str(reason)

    def PrintRect(self, rectangle):
        """debugging tool - Print board in ascii art"""
        print("_" * (len(rectangle) + 2))
        for y in range(len(rectangle[0])):
            print("|", end="")
            for x in range(len(rectangle)):
                print("%s" % self.GetReasonSymbol(rectangle[x][y]), end="")
            print("|")
        print("_" * (len(rectangle) + 2))
        print(
            """
OK           = 'X'
NO_SIGNAL    = ' '
OTHER_SIGNAL = 'O'
KEEPOUT      = 'K'
TRACK        = 'T'
PAD          = 'P'
DRAWING      = 'D'
STEP         = '-'
"""
        )

    def AddVia(self, position, x, y):
        if self.parent_area:
            m = PCB_VIA(self.parent_area)
            m.SetPosition(position)
            if self.target_net is None:
                self.target_net = self.pcb.FindNet(self.netname)
            m.SetNet(self.target_net)
            m.SetViaType(VIATYPE_THROUGH)
            m.SetDrill(int(self.drill))
            m.SetWidth(int(self.size))
            m.SetIsFree(True)
            self.pcb.Add(m)
            self.pcb_group.AddItem(m)
            return m
        else:
            wxPrint("\nUnable to find a valid parent area (zone)")

    def RefillBoardAreas(self):
        for area in self.pcb.Zones():
            if Version() < "7":
                None
            else:
                area.SetNeedRefill(True)

    def CheckViaInAllAreas(self, via, all_areas):
        """Check if an existing Via collides with another area"""
        for area in all_areas:
            area_layer = area.GetLayer()
            area_layer_name = self.pcb.GetLayerName(area_layer)
            area_clearance = area.GetLocalClearance()
            area_priority = area.GetAssignedPriority()
            is_rules_area = area.GetIsRuleArea()
            is_rule_exclude_via_area = area.GetIsRuleArea() and area.GetDoNotAllowVias()
            is_target_net = area.GetNetname() == self.netname

            # Check if this layer should be ignored
            layer_is_ignored = area_layer_name in self.ignored_layers

            if not is_target_net or is_rule_exclude_via_area:
                offset = max(self.clearance, area_clearance) + self.size / 2
                # Test center point AND 4 corners to catch all cases
                test_offsets = [(0, 0), (-offset, -offset), (-offset, offset), (offset, -offset), (offset, offset)]
                for dx, dy in test_offsets:
                    point_to_test = VECTOR2I(int(via.PosX + dx), int(via.PosY + dy))

                    hit_test_area = False
                    if Version() < "7":
                        for layer_id in area.GetLayerSet().CuStack():
                            hit_test_area = hit_test_area or area.HitTestFilledArea(layer_id, point_to_test)
                    else:
                        for layer_id in area.GetLayerSet().CuStack():
                            for i in range(0, area.Outline().OutlineCount()):
                                area_outline = area.Outline().Outline(i)
                                if area.GetLayerSet().Contains(layer_id) and (layer_id != Edge_Cuts):
                                    hit_test_area = hit_test_area or area_outline.PointInside(point_to_test)

                    hit_test_edge = area.HitTestForEdge(point_to_test, 1)
                    try:
                        hit_test_zone = area.HitTestInsideZone(point_to_test)
                    except:
                        hit_test_zone = False

                    if is_rule_exclude_via_area and (hit_test_area or hit_test_edge or hit_test_zone):
                        return self.REASON_KEEPOUT

                    elif (not layer_is_ignored) and (hit_test_area or hit_test_edge) and not is_rules_area:
                        return self.REASON_OTHER_SIGNAL

                    elif (not layer_is_ignored) and hit_test_zone and not is_rules_area:
                        target_areas_on_same_layer = filter(
                            lambda x: ((x.GetPriority() > area_priority) and (x.GetLayer() == area_layer) and (x.GetNetname() == self.netname)), all_areas
                        )
                        for area_with_higher_priority in target_areas_on_same_layer:
                            if area_with_higher_priority.HitTestInsideZone(point_to_test):
                                break
                        else:
                            return self.REASON_OTHER_SIGNAL

        return self.REASON_OK

    def ClearViaInStepSize(self, rectangle, x, y, distance):
        """Clear nearby grid positions after placing a via (for Staggered pattern)"""
        for x_pos in range(x - distance, x + distance + 1):
            if (x_pos >= 0) and (x_pos < len(rectangle)):
                distance_y = distance - abs(x - x_pos) if self.fill_type == self.FILL_TYPE_STAGGERED else distance
                for y_pos in range(y - distance_y, y + distance_y + 1):
                    if (y_pos >= 0) and (y_pos < len(rectangle[0])):
                        if (x_pos == x) and (y_pos == y):
                            continue
                        rectangle[x_pos][y_pos] = self.REASON_STEP

    def CheckViaDistance(self, p, via, outline):
        """Check if vias would not overlap"""
        p2 = VECTOR2I(via.GetPosition())
        dist = self.clearance + self.size / 2 + via.GetWidth() / 2
        if outline.Collide(p2):
            dist = int(max(dist, self.step * 0.6))
        return (p - p2).EuclideanNorm() >= dist

    def AddViasAlongOutline(self, outline, outline_parent, all_vias, offset=0):
        """Add vias along outline for Concentric/Outline patterns"""
        via_placed = 0
        step = max(self.step, self.size + self.clearance)
        len_outline = int(outline.Length())
        steps = len_outline // step
        steps = 1 if steps == 0 else steps
        stepsize = int(len_outline // steps)
        for l in range(int(stepsize * offset), len_outline, stepsize):
            p = outline.PointAlong(l)
            if all(self.CheckViaDistance(p, via, outline_parent) for via in all_vias):
                via = self.AddVia(p, 0, 0)
                all_vias.append(via)
                via_placed += 1
        return via_placed

    def ConcentricFillVias(self):
        """Fill vias using Concentric/Outline pattern"""
        wxPrint("Calculate placement areas")

        zones = [zone for zone in self.pcb.Zones() if zone.GetNetname() == self.netname]
        if not zones:
            wxPrint("No zones matching criteria found")
            return 0

        self.parent_area = zones[0]

        poly_set = None
        for layer_id in self.pcb.GetEnabledLayers().CuStack():
            poly_set_layer = SHAPE_POLY_SET()
            for zone in zones:
                if zone.IsOnLayer(layer_id):
                    if poly_set is not None or not self.only_selected_area or zone.IsSelected():
                        if Version() < "7":
                            poly_set_layer.Append(zone.RawPolysList(layer_id))
                        else:
                            poly_set_layer.Append(zone.Outline())

            if poly_set is None:
                poly_set = poly_set_layer
            else:
                poly_set.BooleanIntersection(poly_set_layer)
                poly_set.Simplify()

            if poly_set.OutlineCount() == 0:
                wxPrint("No areas to fill")
                return

        poly_set.Inflate(int(-(1 * self.clearance + 0.5 * self.size)), CORNER_STRATEGY_CHAMFER_ALL_CORNERS, FromMM(0.01))

        wxPrint("Generating concentric via placement")
        all_vias = [track for track in self.pcb.GetTracks() if (track.GetClass() == "PCB_VIA" and track.GetNetname() == self.netname)]

        off = 0
        via_placed = 0
        while poly_set.OutlineCount() > 0:
            for i in range(0, poly_set.OutlineCount()):
                outline = poly_set.Outline(i)
                via_placed += self.AddViasAlongOutline(outline, outline, all_vias, off)

                if self.fill_type != self.FILL_TYPE_OUTLINE_NO_HOLES:
                    for k in range(0, poly_set.HoleCount(i)):
                        hole = poly_set.Hole(i, k)
                        via_placed += self.AddViasAlongOutline(hole, outline, all_vias, off)

            if self.fill_type == self.FILL_TYPE_CONCENTRIC:
                poly_set.Inflate(int(-max(self.step, self.size + self.clearance)), CORNER_STRATEGY_CHAMFER_ALL_CORNERS, FromMM(0.01))
                off = 0.5 if off == 0 else 0
            else:
                poly_set = SHAPE_POLY_SET()

        self.RefillBoardAreas()

        msg = "Done. {:d} vias placed. Remember to refill zones (press 'B').".format(via_placed)
        wxPrint(msg)

        return via_placed

    def BuildSpatialIndex(self, all_pads, all_tracks, max_clearance, keepout_zones=None):
        """Build spatial hash index for O(1) collision detection"""
        cell_size = max(self.step, self.size + self.clearance) * 2
        self.spatial_hash = SpatialHash(cell_size)

        # Index keepout zones (rule areas with via exclusion)
        if keepout_zones:
            for zone in keepout_zones:
                self.spatial_hash.insert_zone(zone, "keepout")

        # Index all pads
        for pad in all_pads:
            x, y = pad.GetPosition().x, pad.GetPosition().y
            max_size = max(pad.GetSize().x, pad.GetSize().y)
            radius = max_size / 2 + max(pad.GetOwnClearance(UNDEFINED_LAYER, ""), self.clearance, max_clearance) + self.size / 2
            self.spatial_hash.insert(x, y, radius, "pad")

            # Also add hole clearance if pad has a hole
            if hasattr(pad, 'GetDrillSize'):
                drill = pad.GetDrillSize()
                if drill.x > 0 or drill.y > 0:
                    hole_radius = max(drill.x, drill.y) / 2 + self.hole_clearance + self.drill / 2
                    self.spatial_hash.insert(x, y, hole_radius, "hole")

        # Index all tracks and vias
        for track in all_tracks:
            if self.same_net_tracks and not isinstance(track, PCB_VIA) and track.GetNetname() == self.netname:
                continue

            clearance = max(track.GetOwnClearance(UNDEFINED_LAYER, ""), self.clearance, max_clearance) + self.size / 2 + track.GetWidth() / 2

            if isinstance(track, PCB_VIA):
                x, y = track.GetPosition().x, track.GetPosition().y
                self.spatial_hash.insert(x, y, clearance, "via")
                # Add hole clearance for via drill
                hole_radius = track.GetDrill() / 2 + self.hole_clearance + self.drill / 2
                self.spatial_hash.insert(x, y, hole_radius, "hole")
            else:
                # Track segment - add as series of circles along the track
                start = track.GetStart()
                end = track.GetEnd()
                length = math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)
                if length > 0:
                    steps = max(1, int(length / (clearance / 2)))
                    for i in range(steps + 1):
                        t = i / steps
                        x = start.x + t * (end.x - start.x)
                        y = start.y + t * (end.y - start.y)
                        self.spatial_hash.insert(x, y, clearance, "track")

    def CheckPositionWithSpatialIndex(self, x, y):
        """Check if position is valid using spatial index"""
        via_radius = self.size / 2 + self.clearance
        # Check against obstacles (pads, tracks, vias)
        if self.spatial_hash.check_collision(x, y, via_radius):
            return False
        # Check against keepout zones
        if self.spatial_hash.check_keepout_zones(x, y):
            return False
        return True

    def FindNudgedPosition(self, x, y, max_nudge_distance):
        """
        Spiral search to find valid position near (x,y).
        Returns (new_x, new_y, True) if found, or (x, y, False) if not.
        """
        nudge_step = self.clearance / 2  # Small steps for nudge search

        # Spiral outward
        for distance in range(1, int(max_nudge_distance / nudge_step) + 1):
            radius = distance * nudge_step
            # Check points around the circle at this radius
            num_points = max(8, int(2 * math.pi * distance))
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                nx = x + radius * math.cos(angle)
                ny = y + radius * math.sin(angle)

                if self.CheckPositionWithSpatialIndex(nx, ny):
                    return (nx, ny, True)

        return (x, y, False)

    def GetNextGroupNumber(self):
        """Get the next available group number for this net"""
        max_num = 0
        prefix = f"ViaStitching {self.netname} #"

        for group in self.pcb.Groups():
            name = group.GetName()
            if name.startswith(prefix):
                try:
                    num = int(name[len(prefix):])
                    max_num = max(max_num, num)
                except ValueError:
                    pass

        return max_num + 1

    def Run(self):
        """Main function which does the via placement or deletion"""

        # Enhancement: Use numbered groups
        group_num = self.GetNextGroupNumber()
        VIA_GROUP_NAME = f"ViaStitching {self.netname} #{group_num}"

        if self.debug:
            print("Creating new group: " + VIA_GROUP_NAME)

        # Handle delete mode
        if self.delete_vias:
            wx.MessageBox(
                f"To delete vias:\n"
                f" - Use the Group Management section in the dialog, or\n"
                f" - Select one via to select its group, then press Delete\n\n"
                f"Groups are named like 'ViaStitching {self.netname} #1'",
                "Information"
            )
            return

        # Create new group for this run
        self.pcb_group = PCB_GROUP(None)
        self.pcb_group.SetName(VIA_GROUP_NAME)
        self.pcb.Add(self.pcb_group)

        # Handle Concentric/Outline patterns (original algorithm)
        if self.fill_type in [self.FILL_TYPE_CONCENTRIC, self.FILL_TYPE_OUTLINE, self.FILL_TYPE_OUTLINE_NO_HOLES]:
            result = self.ConcentricFillVias()
            if self.filename:
                self.pcb.Save(self.filename)
            return result

        # Rectangular/Staggered pattern with enhancements
        if self.debug:
            print("%s: Starting rectangular/staggered fill" % time.time())

        target_tracks = self.pcb.GetTracks()
        lboard = self.pcb.ComputeBoundingBox(False)
        origin = lboard.GetPosition()

        l_clearance = self.clearance + self.size
        if l_clearance < self.step:
            l_clearance = self.step

        # For Staggered pattern: use finer grid so spacing ≈ user's step value
        # With clear_distance=1, actual spacing ≈ 2 × l_clearance
        # So use l_clearance = step / 2
        if self.fill_type == self.FILL_TYPE_STAGGERED and self.step > 0:
            target_clearance = self.step // 2
            min_clearance = self.clearance + self.size
            l_clearance = max(target_clearance, min_clearance)

        x_limit = int((lboard.GetWidth() + l_clearance) / l_clearance) + 1
        y_limit = int((lboard.GetHeight() + l_clearance) / l_clearance) + 1

        if self.debug:
            print(f"Grid size: {x_limit} x {y_limit} = {x_limit * y_limit} positions")

        rectangle = [[self.REASON_NO_SIGNAL] * y_limit for i in xrange(x_limit)]

        all_pads = self.pcb.GetPads()
        all_tracks = self.pcb.GetTracks()

        try:
            all_drawings = filter(lambda x: x.GetClass() == "PTEXT" and self.pcb.GetLayerID(x.GetLayerName()) in (F_Cu, B_Cu), self.pcb.DrawingsList())
        except:
            all_drawings = filter(lambda x: x.GetClass() == "PTEXT" and self.pcb.GetLayerID(x.GetLayerName()) in (F_Cu, B_Cu), self.pcb.Drawings())

        # Use Zones() which includes rule areas in KiCad 8+
        # Also collect zones embedded in footprints (rule areas in footprints)
        all_areas = list(self.pcb.Zones())
        for footprint in self.pcb.GetFootprints():
            try:
                for zone in footprint.Zones():
                    all_areas.append(zone)
            except:
                pass  # Older KiCad versions may not have footprint zones
        target_areas = list(filter(lambda x: (x.GetNetname() == self.netname), all_areas))

        board_edge = SHAPE_POLY_SET()
        self.pcb.GetBoardPolygonOutlines(board_edge)
        b_clearance = max(self.pcb.GetDesignSettings().m_CopperEdgeClearance, self.clearance) + self.size
        board_edge.Deflate(int(b_clearance), CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.01))

        via_list = []
        max_target_area_clearance = 0

        # Create progress dialog
        total_steps = x_limit
        self.progress_dialog = wx.ProgressDialog(
            "Via Stitching",
            "Finding valid positions...",
            maximum=total_steps,
            style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME
        )
        self.cancelled = False

        # Phase 1: Find target area positions
        wxPrint("Finding positions in target areas...")
        for area in target_areas:
            if self.parent_area is None:
                self.parent_area = area
            is_selected_area = area.IsSelected()
            area_clearance = area.GetLocalClearance()
            if max_target_area_clearance < area_clearance:
                max_target_area_clearance = area_clearance

            if (not self.only_selected_area) or (self.only_selected_area and is_selected_area):
                for x in xrange(len(rectangle)):
                    if x % 10 == 0:
                        keep_going, _ = self.progress_dialog.Update(x, f"Scanning area: column {x}/{x_limit}")
                        if not keep_going:
                            self.cancelled = True
                            break

                    for y in xrange(len(rectangle[0])):
                        if rectangle[x][y] == self.REASON_NO_SIGNAL:
                            current_x = origin.x + (x * l_clearance)
                            current_y = origin.y + (y * l_clearance)

                            test_result = True
                            offset = 0
                            point_to_test = VECTOR2I(int(current_x), int(current_y))

                            hit_test_area = False
                            if Version() < "7":
                                hit_test_area = area.HitTestFilledArea(area.GetLayer(), VECTOR2I(point_to_test), int(offset))
                            else:
                                for i in range(0, area.Outline().OutlineCount()):
                                    area_outline = area.Outline().Outline(i)
                                    hit_test_area = hit_test_area or area_outline.PointInside(point_to_test)

                            hit_test_edge = area.HitTestForEdge(point_to_test, int(max(area_clearance, offset)))
                            test_result = hit_test_area and not hit_test_edge
                            test_result = test_result and board_edge.Collide(point_to_test)

                            if test_result:
                                via_obj = ViaObject(x=x, y=y, pos_x=current_x, pos_y=current_y)
                                rectangle[x][y] = via_obj
                                via_list.append(via_obj)

                if self.cancelled:
                    break

        if self.cancelled:
            self.progress_dialog.Destroy()
            wxPrint("Via stitching cancelled by user")
            return 0

        # Phase 2: Check against other areas
        self.progress_dialog.Update(0, "Checking against other areas...")
        wxPrint("Checking against other areas...")
        for idx, via in enumerate(via_list):
            if idx % 100 == 0:
                keep_going, _ = self.progress_dialog.Update(
                    int(idx * total_steps / len(via_list)) if via_list else 0,
                    f"Checking areas: {idx}/{len(via_list)}"
                )
                if not keep_going:
                    self.cancelled = True
                    break

            reason = self.CheckViaInAllAreas(via, all_areas)
            if reason != self.REASON_OK:
                rectangle[via.X][via.Y] = reason

        if self.cancelled:
            self.progress_dialog.Destroy()
            wxPrint("Via stitching cancelled by user")
            return 0

        # Collect keepout zones (rule areas that exclude vias)
        keepout_zones = [area for area in all_areas
                         if area.GetIsRuleArea() and area.GetDoNotAllowVias()]
        wxPrint(f"Found {len(keepout_zones)} keepout zone(s) that exclude vias")

        # Build spatial index for collision detection
        wxPrint("Building spatial index...")
        self.BuildSpatialIndex(all_pads, all_tracks, max_target_area_clearance, keepout_zones)

        # Phase 3: Check against pads (using spatial index)
        self.progress_dialog.Update(0, "Checking against pads...")
        wxPrint("Checking against pads...")
        for pad in all_pads:
            local_offset = max(pad.GetOwnClearance(UNDEFINED_LAYER, ""), self.clearance, max_target_area_clearance) + (self.size / 2)
            max_size = max(pad.GetSize().x, pad.GetSize().y)

            start_x = int(math.floor(((pad.GetPosition().x - (max_size / 2.0 + local_offset)) - origin.x) / l_clearance))
            stop_x = int(math.ceil(((pad.GetPosition().x + (max_size / 2.0 + local_offset)) - origin.x) / l_clearance))
            start_y = int(math.floor(((pad.GetPosition().y - (max_size / 2.0 + local_offset)) - origin.y) / l_clearance))
            stop_y = int(math.ceil(((pad.GetPosition().y + (max_size / 2.0 + local_offset)) - origin.y) / l_clearance))

            for x in range(start_x, stop_x + 1):
                for y in range(start_y, stop_y + 1):
                    try:
                        if isinstance(rectangle[x][y], ViaObject):
                            size_rect = VECTOR2I(int(2 * local_offset), int(2 * local_offset))
                            start_rect = VECTOR2I(int(origin.x + (l_clearance * x) - local_offset), int(origin.y + (l_clearance * y) - local_offset))
                            if pad.HitTest(BOX2I(start_rect, size_rect), False):
                                rectangle[x][y] = self.REASON_PAD
                    except:
                        pass

        # Phase 4: Check against tracks
        self.progress_dialog.Update(0, "Checking against tracks...")
        wxPrint("Checking against tracks...")
        for track in all_tracks:
            if self.same_net_tracks:
                if not isinstance(track, PCB_VIA) and track.GetNetname() == self.netname:
                    continue

            start_x = track.GetStart().x
            start_y = track.GetStart().y
            stop_x = track.GetEnd().x
            stop_y = track.GetEnd().y

            if start_x > stop_x:
                start_x, stop_x = stop_x, start_x
            if start_y > stop_y:
                start_y, stop_y = stop_y, start_y

            clearance = max(track.GetOwnClearance(UNDEFINED_LAYER, ""), self.clearance, max_target_area_clearance) + (self.size / 2) + (track.GetWidth() / 2)

            start_x = int(math.floor(((start_x - clearance) - origin.x) / l_clearance))
            stop_x = int(math.ceil(((stop_x + clearance) - origin.x) / l_clearance))
            start_y = int(math.floor(((start_y - clearance) - origin.y) / l_clearance))
            stop_y = int(math.ceil(((stop_y + clearance) - origin.y) / l_clearance))

            for x in range(start_x, stop_x + 1):
                for y in range(start_y, stop_y + 1):
                    try:
                        if isinstance(rectangle[x][y], ViaObject):
                            start_rect = VECTOR2I(int(origin.x + (l_clearance * x) - clearance), int(origin.y + (l_clearance * y) - clearance))
                            size_rect = VECTOR2I(int(2 * clearance), int(2 * clearance))
                            if track.HitTest(BOX2I(start_rect, size_rect), False):
                                rectangle[x][y] = self.REASON_TRACK
                    except:
                        pass

        # Phase 5: Check against drawings
        wxPrint("Checking against drawings...")
        for draw in all_drawings:
            inter = float(self.clearance + self.size) / 2
            bbox = draw.GetBoundingBox()

            start_x = int(math.floor(((bbox.GetPosition().x - inter) - origin.x) / l_clearance))
            stop_x = int(math.ceil(((bbox.GetPosition().x + (bbox.GetSize().x + inter)) - origin.x) / l_clearance))
            start_y = int(math.floor(((bbox.GetPosition().y - inter) - origin.y) / l_clearance))
            stop_y = int(math.ceil(((bbox.GetPosition().y + (bbox.GetSize().y + inter)) - origin.y) / l_clearance))

            for x in range(start_x, stop_x):
                for y in range(start_y, stop_y):
                    try:
                        rectangle[x][y] = self.REASON_DRAWING
                    except:
                        pass

        # Phase 6: Place vias
        self.progress_dialog.Update(0, "Placing vias...")
        wxPrint("Placing vias...")

        clear_distance = 0
        if self.step != 0.0 and self.fill_type == self.FILL_TYPE_STAGGERED:
            # With l_clearance = step/2, clear_distance = 1 gives spacing ≈ step
            clear_distance = 1

        via_placed = 0
        nudged_count = 0
        max_nudge_distance = self.step / 2

        for x in xrange(len(rectangle)):
            if x % 5 == 0:
                keep_going, _ = self.progress_dialog.Update(
                    int(x * total_steps / len(rectangle)),
                    f"Placing vias: column {x}/{len(rectangle)}, {via_placed} placed"
                )
                if not keep_going:
                    self.cancelled = True
                    break

            for y in xrange(len(rectangle[0])):
                if isinstance(rectangle[x][y], ViaObject):
                    if clear_distance:
                        self.ClearViaInStepSize(rectangle, x, y, clear_distance)

                    via = rectangle[x][y]
                    ran_x = 0
                    ran_y = 0

                    if self.random:
                        max_offset = max(self.step - (self.clearance + self.size), 0) / 2.0
                        ran_x = (random.random() * max_offset) - (max_offset / 2.0)
                        ran_y = (random.random() * max_offset) - (max_offset / 2.0)

                    final_x = via.PosX + ran_x
                    final_y = via.PosY + ran_y

                    # Enhancement: Use spatial index to verify position
                    if self.CheckPositionWithSpatialIndex(final_x, final_y):
                        self.AddVia(VECTOR2I(int(final_x), int(final_y)), via.X, via.Y)
                        # Add placed via to spatial index
                        self.spatial_hash.insert(final_x, final_y, self.size / 2 + self.clearance, "placed_via")
                        via_placed += 1
                    elif self.nudge_enabled:
                        # Enhancement: Try nudge search
                        nudged_x, nudged_y, found = self.FindNudgedPosition(final_x, final_y, max_nudge_distance)
                        if found:
                            self.AddVia(VECTOR2I(int(nudged_x), int(nudged_y)), via.X, via.Y)
                            self.spatial_hash.insert(nudged_x, nudged_y, self.size / 2 + self.clearance, "placed_via")
                            via_placed += 1
                            nudged_count += 1

        self.progress_dialog.Destroy()

        if self.cancelled:
            wxPrint(f"Via stitching cancelled. {via_placed} vias placed before cancellation.")
            return via_placed

        self.RefillBoardAreas()

        if self.filename:
            self.pcb.Save(self.filename)

        msg = f"Done! {via_placed} vias placed"
        if nudged_count > 0:
            msg += f" ({nudged_count} nudged from grid)"
        msg += ". Remember to refill zones (press 'B')."
        wxPrint(msg)

        return via_placed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s <KiCad pcb filename>" % sys.argv[0])
    else:
        FillArea(sys.argv[1]).SetDebug().Run()
