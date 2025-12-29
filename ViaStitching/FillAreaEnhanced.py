#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  FillAreaEnhanced.py
#  Enhanced via stitching with spatial indexing and nudge search
#
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com> (original FillArea.py)
#  Copyright 2025 Geoff Wall / Ceres Imaging (enhancements)
#
#  Enhancements over original:
#  - Spatial hash indexing for O(1) collision detection
#  - Spiral nudge search to find valid positions when grid points blocked
#  - Staggered (brick/hex) grid pattern option for ~15% denser packing
#  - Mil/mm unit support with live conversion
#  - Separate hole-to-hole clearance rule
#  - Numbered groups for each run with delete functionality
#  - Progress dialog with cancel button
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function
from pcbnew import *
import math
import random
import wx

def wxPrint(msg):
    wx.LogMessage(msg)


# =============================================================================
# Unit Conversion - KiCad uses nanometers internally
# =============================================================================

# KiCad internal unit is 1nm, but pcbnew functions use "IU" which is also nm
# FromMM(1.0) returns 1,000,000 (1mm = 1,000,000 nm)
# 1 mil = 0.0254 mm = 25,400 nm

def FromMils(mils):
    """Convert mils to KiCad internal units (nanometers)"""
    return int(mils * 25400)

def ToMils(iu):
    """Convert KiCad internal units to mils"""
    return float(iu) / 25400.0

def FromUserUnits(value, unit='mm'):
    """Convert user units (mm or mil) to KiCad internal units"""
    if unit.lower() in ('mil', 'mils', 'th'):
        return FromMils(value)
    else:  # mm
        return int(FromMM(value))

def ToUserUnits(iu, unit='mm'):
    """Convert KiCad internal units to user units (mm or mil)"""
    if unit.lower() in ('mil', 'mils', 'th'):
        return ToMils(iu)
    else:  # mm
        return ToMM(iu)


# =============================================================================
# Spatial Hash - O(1) average collision detection
# =============================================================================

class SpatialHash:
    """
    Grid-based spatial hash for fast collision queries.
    Objects are stored in cells based on their bounding box.
    Query returns only objects in nearby cells.
    """

    def __init__(self, cell_size):
        """
        cell_size: Size of each hash cell in KiCad internal units (nm)
                   Should be roughly the size of the largest object you're querying
        """
        self.cell_size = cell_size
        self.cells = {}  # {(cell_x, cell_y): [objects]}

    def _get_cell(self, x, y):
        """Get cell coordinates for a point"""
        return (int(x // self.cell_size), int(y // self.cell_size))

    def _get_cells_for_bbox(self, min_x, min_y, max_x, max_y):
        """Get all cells that overlap a bounding box"""
        min_cell = self._get_cell(min_x, min_y)
        max_cell = self._get_cell(max_x, max_y)

        cells = []
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                cells.append((cx, cy))
        return cells

    def insert(self, obj, min_x, min_y, max_x, max_y):
        """Insert object with its bounding box"""
        for cell in self._get_cells_for_bbox(min_x, min_y, max_x, max_y):
            if cell not in self.cells:
                self.cells[cell] = []
            self.cells[cell].append(obj)

    def query(self, min_x, min_y, max_x, max_y):
        """Query objects that might intersect the given bbox"""
        # Use list + seen set of IDs since KiCad objects aren't hashable
        result = []
        seen_ids = set()
        for cell in self._get_cells_for_bbox(min_x, min_y, max_x, max_y):
            if cell in self.cells:
                for obj in self.cells[cell]:
                    obj_id = id(obj)
                    if obj_id not in seen_ids:
                        seen_ids.add(obj_id)
                        result.append(obj)
        return result

    def query_point(self, x, y, radius):
        """Query objects near a point within radius"""
        return self.query(x - radius, y - radius, x + radius, y + radius)


# =============================================================================
# Spiral Search Generator
# =============================================================================

def spiral_offsets(max_radius, step):
    """
    Generate (dx, dy) offsets in a spiral pattern from center.

    KiCad coordinate system:
    - X increases to the right
    - Y increases downward (screen coordinates)
    - Origin typically at top-left

    Spiral pattern (numbers show order):
         9  2 10
         4  0  1    0 = center (0,0)
        11  3 12    1 = (step, 0), 2 = (0, -step), etc.
         8  5  6
           7

    Args:
        max_radius: Maximum distance from center to search (in IU)
        step: Distance between spiral points (in IU)

    Yields:
        (dx, dy) offsets from center
    """
    yield (0, 0)  # Always try center first

    if step <= 0:
        return

    # Generate points in expanding rings
    ring = 1
    while ring * step <= max_radius:
        r = ring * step

        # Right side: (r, y) for y from 0 to r
        for i in range(ring + 1):
            y = i * step
            yield (r, y)
            if y != 0:
                yield (r, -y)

        # Left side: (-r, y)
        for i in range(ring + 1):
            y = i * step
            yield (-r, y)
            if y != 0:
                yield (-r, -y)

        # Top: (x, -r) excluding corners
        for i in range(1, ring):
            x = i * step
            yield (x, -r)
            yield (-x, -r)

        # Bottom: (x, r) excluding corners
        for i in range(1, ring):
            x = i * step
            yield (x, r)
            yield (-x, r)

        ring += 1


def spiral_offsets_fine(max_radius, coarse_step, fine_step):
    """
    Two-phase spiral: coarse search first, then fine search around best candidates.

    Args:
        max_radius: Maximum search radius
        coarse_step: Initial coarse step size
        fine_step: Fine step size for detailed search
    """
    # Phase 1: Coarse spiral
    for offset in spiral_offsets(max_radius, coarse_step):
        yield offset

    # Phase 2: Fine offsets around coarse points (if different from coarse)
    if fine_step < coarse_step:
        for coarse_offset in spiral_offsets(max_radius, coarse_step):
            if coarse_offset == (0, 0):
                continue
            cx, cy = coarse_offset
            for fine_offset in spiral_offsets(coarse_step // 2, fine_step):
                if fine_offset == (0, 0):
                    continue
                fx, fy = fine_offset
                yield (cx + fx, cy + fy)


# =============================================================================
# Enhanced Via Stitching
# =============================================================================

class FillAreaEnhanced:
    """
    Enhanced via stitching with:
    - Spatial hash indexing for O(1) collision detection
    - Spiral nudge search when grid positions are blocked
    - Support for mils or mm input
    """

    REASON_OK = 0
    REASON_NO_SIGNAL = 1
    REASON_OTHER_SIGNAL = 2
    REASON_KEEPOUT = 3
    REASON_TRACK = 4
    REASON_PAD = 5
    REASON_DRAWING = 6
    REASON_STEP = 7
    REASON_VIA = 8  # Too close to another via

    def __init__(self, board=None):
        self.pcb = board if board else GetBoard()
        self.pcb.BuildListOfNets()

        # Via parameters (stored in KiCad internal units)
        self.via_size = FromMM(0.6)      # Via copper diameter
        self.via_drill = FromMM(0.3)     # Via drill diameter
        self.clearance = FromMM(0.2)     # Copper-to-copper clearance
        self.hole_clearance = FromMM(0.2) # Hole-to-hole clearance (edge to edge)
        self.grid_step = FromMM(2.54)    # Grid spacing

        # Search parameters
        self.nudge_enabled = True
        self.nudge_max_radius = None     # Auto-calculated if None
        self.nudge_step = None           # Auto-calculated if None

        # Options
        self.netname = "GND"
        self.via_through_areas = False   # Ignore areas on other layers
        self.same_net_tracks = False     # Allow vias on same-net tracks
        self.only_selected_area = False
        self.random_offset = False
        self.staggered_grid = True       # Offset alternating rows for denser packing
        self.unit = 'mm'                 # Display unit

        # Internal state
        self.pad_hash = None
        self.track_hash = None
        self.via_hash = None
        self.zone_hash = None
        self.placed_vias = []            # Track vias we've placed
        self.parent_area = None
        self.target_net = None
        self.pcb_group = None

        # Find GND net
        for lnet in ["GND", "/GND"]:
            if self.pcb.FindNet(lnet) is not None:
                self.netname = lnet
                break

    # -------------------------------------------------------------------------
    # Configuration methods (chainable)
    # -------------------------------------------------------------------------

    def SetUnit(self, unit):
        """Set display unit: 'mm' or 'mil'"""
        self.unit = unit.lower()
        return self

    def SetViaSizeMils(self, mils):
        self.via_size = FromMils(mils)
        return self

    def SetViaSizeMM(self, mm):
        self.via_size = int(FromMM(mm))
        return self

    def SetDrillMils(self, mils):
        self.via_drill = FromMils(mils)
        return self

    def SetDrillMM(self, mm):
        self.via_drill = int(FromMM(mm))
        return self

    def SetClearanceMils(self, mils):
        self.clearance = FromMils(mils)
        return self

    def SetClearanceMM(self, mm):
        self.clearance = int(FromMM(mm))
        return self

    def SetHoleClearanceMils(self, mils):
        self.hole_clearance = FromMils(mils)
        return self

    def SetHoleClearanceMM(self, mm):
        self.hole_clearance = int(FromMM(mm))
        return self

    def SetGridMils(self, mils):
        self.grid_step = FromMils(mils)
        return self

    def SetGridMM(self, mm):
        self.grid_step = int(FromMM(mm))
        return self

    def SetNetname(self, name):
        self.netname = name
        return self

    def SetNudgeEnabled(self, enabled):
        self.nudge_enabled = enabled
        return self

    def SetViaThroughAreas(self, enabled):
        self.via_through_areas = enabled
        return self

    def SetSameNetTracks(self, enabled):
        self.same_net_tracks = enabled
        return self

    def SetOnlySelectedArea(self, enabled):
        self.only_selected_area = enabled
        return self

    def SetRandomOffset(self, enabled):
        self.random_offset = enabled
        if enabled:
            random.seed()
        return self

    def SetStaggeredGrid(self, enabled):
        self.staggered_grid = enabled
        return self

    # -------------------------------------------------------------------------
    # Spatial indexing setup
    # -------------------------------------------------------------------------

    def _build_spatial_indexes(self):
        """Build spatial hash indexes for fast collision detection"""

        # Cell size should be roughly the query radius we'll use
        # Using via_size + clearance as a reasonable cell size
        cell_size = max(self.via_size + self.clearance, self.grid_step // 2)

        wxPrint(f"Building spatial indexes (cell size: {ToUserUnits(cell_size, self.unit):.2f} {self.unit})...")

        # Index for pads
        self.pad_hash = SpatialHash(cell_size)
        for pad in self.pcb.GetPads():
            bbox = pad.GetBoundingBox()
            self.pad_hash.insert(pad,
                                 bbox.GetLeft(), bbox.GetTop(),
                                 bbox.GetRight(), bbox.GetBottom())

        # Index for tracks (including existing vias)
        self.track_hash = SpatialHash(cell_size)
        self.via_hash = SpatialHash(cell_size)
        for track in self.pcb.GetTracks():
            if track.GetClass() == "PCB_VIA":
                pos = track.GetPosition()
                r = track.GetWidth() // 2
                self.via_hash.insert(track, pos.x - r, pos.y - r, pos.x + r, pos.y + r)
            else:
                bbox = track.GetBoundingBox()
                self.track_hash.insert(track,
                                       bbox.GetLeft(), bbox.GetTop(),
                                       bbox.GetRight(), bbox.GetBottom())

        # Index for zones/areas
        self.zone_hash = SpatialHash(cell_size * 4)  # Larger cells for zones
        for i in range(self.pcb.GetAreaCount()):
            area = self.pcb.GetArea(i)
            bbox = area.GetBoundingBox()
            self.zone_hash.insert(area,
                                  bbox.GetLeft(), bbox.GetTop(),
                                  bbox.GetRight(), bbox.GetBottom())

        wxPrint(f"Indexed {len(list(self.pcb.GetPads()))} pads, "
                f"{len(list(self.pcb.GetTracks()))} tracks/vias, "
                f"{self.pcb.GetAreaCount()} zones")

    # -------------------------------------------------------------------------
    # Collision detection
    # -------------------------------------------------------------------------

    def _check_position(self, x, y):
        """
        Check if a via can be placed at position (x, y).

        Returns:
            (can_place, reason) tuple
        """
        query_radius = self.via_size // 2 + self.clearance

        # Check against pads (including NPTHs and PTHs with hole-to-hole clearance)
        nearby_pads = self.pad_hash.query_point(x, y, query_radius + FromMM(5))  # Extra margin for large pads
        for pad in nearby_pads:
            pad_pos = pad.GetPosition()

            # PAD_ATTRIB: PTH=0, SMD=1, CONN=2, NPTH=3
            pad_attr = pad.GetAttribute()
            is_npth = (pad_attr == 3)  # PAD_ATTRIB_NPTH
            is_pth = (pad_attr == 0)   # PAD_ATTRIB_PTH (through-hole with copper)

            if is_npth:
                # For NPTHs, use drill size + clearance (no copper pad to check)
                drill_size = pad.GetDrillSize()
                # Use the larger of X or Y drill (for oval holes)
                hole_radius = max(drill_size.x, drill_size.y) // 2

                # Copper clearance: via radius to hole edge
                copper_min_dist = hole_radius + self.via_size // 2 + self.clearance

                # Hole-to-hole clearance: our drill radius to their hole edge
                hole_min_dist = hole_radius + self.via_drill // 2 + self.hole_clearance

                min_dist = max(copper_min_dist, hole_min_dist)

                # Simple distance check for NPTHs
                dist_sq = (x - pad_pos.x) ** 2 + (y - pad_pos.y) ** 2
                if dist_sq < min_dist ** 2:
                    return (False, self.REASON_PAD)

            elif is_pth:
                # PTH pad: check BOTH copper clearance AND hole-to-hole clearance
                drill_size = pad.GetDrillSize()
                pad_hole_radius = max(drill_size.x, drill_size.y) // 2

                # Copper-to-copper clearance (via copper to pad copper)
                pad_clearance = max(pad.GetOwnClearance(UNDEFINED_LAYER, ""), self.clearance)
                copper_min_dist = self.via_size // 2 + pad_clearance

                # Hole-to-hole clearance (via drill to pad drill)
                hole_min_dist = self.via_drill // 2 + pad_hole_radius + self.hole_clearance

                # Quick bounding box check using copper requirement
                pad_size = pad.GetSize()
                half_w = pad_size.x // 2 + copper_min_dist
                half_h = pad_size.y // 2 + copper_min_dist

                if (abs(x - pad_pos.x) < half_w and abs(y - pad_pos.y) < half_h):
                    # Detailed copper check using pad shape
                    test_point = VECTOR2I(int(x), int(y))
                    if pad.HitTest(test_point, int(copper_min_dist)):
                        return (False, self.REASON_PAD)

                # Also check hole-to-hole distance (simple circular check)
                dist_sq = (x - pad_pos.x) ** 2 + (y - pad_pos.y) ** 2
                if dist_sq < hole_min_dist ** 2:
                    return (False, self.REASON_PAD)

            else:
                # SMD pad - only copper clearance matters (no hole)
                pad_clearance = max(pad.GetOwnClearance(UNDEFINED_LAYER, ""), self.clearance)
                min_dist = self.via_size // 2 + pad_clearance

                # Quick bounding box check
                pad_size = pad.GetSize()
                half_w = pad_size.x // 2 + min_dist
                half_h = pad_size.y // 2 + min_dist

                if (abs(x - pad_pos.x) < half_w and abs(y - pad_pos.y) < half_h):
                    # Detailed check using pad shape
                    test_point = VECTOR2I(int(x), int(y))
                    if pad.HitTest(test_point, int(min_dist)):
                        return (False, self.REASON_PAD)

        # Check against tracks
        nearby_tracks = self.track_hash.query_point(x, y, query_radius + FromMM(2))
        for track in nearby_tracks:
            if self.same_net_tracks and track.GetNetname() == self.netname:
                continue

            track_clearance = max(track.GetOwnClearance(UNDEFINED_LAYER, ""), self.clearance)
            min_dist = self.via_size // 2 + track.GetWidth() // 2 + track_clearance

            test_point = VECTOR2I(int(x), int(y))
            if track.HitTest(test_point, int(min_dist)):
                return (False, self.REASON_TRACK)

        # Check against existing vias - both copper clearance AND hole clearance
        nearby_vias = self.via_hash.query_point(x, y, query_radius + self.grid_step)
        for via in nearby_vias:
            via_pos = via.GetPosition()

            # Copper-to-copper clearance check
            copper_min_dist = self.via_size // 2 + via.GetWidth() // 2 + self.clearance

            # Hole-to-hole clearance check (edge to edge)
            # Our drill radius + their drill radius + hole clearance
            via_drill = via.GetDrill()
            hole_min_dist = self.via_drill // 2 + via_drill // 2 + self.hole_clearance

            # Use the larger of the two requirements
            min_dist = max(copper_min_dist, hole_min_dist)

            dist_sq = (x - via_pos.x) ** 2 + (y - via_pos.y) ** 2
            if dist_sq < min_dist ** 2:
                return (False, self.REASON_VIA)

        # Check against vias we've placed in this run - both copper and hole clearance
        for placed_via in self.placed_vias:
            # Copper clearance: via_radius + via_radius + clearance = via_size + clearance
            copper_min_dist = self.via_size + self.clearance

            # Hole clearance: drill_radius + drill_radius + hole_clearance = via_drill + hole_clearance
            hole_min_dist = self.via_drill + self.hole_clearance

            min_dist = max(copper_min_dist, hole_min_dist)

            dist_sq = (x - placed_via[0]) ** 2 + (y - placed_via[1]) ** 2
            if dist_sq < min_dist ** 2:
                return (False, self.REASON_VIA)

        # Check against zones (keepouts, other nets)
        nearby_zones = self.zone_hash.query_point(x, y, query_radius)
        for area in nearby_zones:
            is_keepout = area.GetIsRuleArea() and area.GetDoNotAllowVias()
            is_target_net = area.GetNetname() == self.netname

            if is_keepout:
                # Check if point is inside keepout
                test_point = VECTOR2I(int(x), int(y))
                for i in range(area.Outline().OutlineCount()):
                    if area.Outline().Outline(i).PointInside(test_point):
                        return (False, self.REASON_KEEPOUT)

            elif not is_target_net:
                # Check what layer this zone is on
                zone_layer = area.GetLayer()

                # Get layer type: LT_SIGNAL=0, LT_POWER=1, LT_MIXED=2, LT_JUMPER=3
                # We only ignore zones on POWER plane layers, not signal layers
                layer_type = self.pcb.GetLayerType(zone_layer)
                is_power_plane = (layer_type == 1)  # LT_POWER

                # If "ignore other layers" is enabled AND this is a power plane layer, skip
                if self.via_through_areas and is_power_plane:
                    continue

                # Check collision with other net's copper pour on signal layers
                test_point = VECTOR2I(int(x), int(y))
                offset = self.via_size // 2 + self.clearance
                for dx, dy in [(-offset, -offset), (offset, -offset),
                               (-offset, offset), (offset, offset)]:
                    corner = VECTOR2I(int(x + dx), int(y + dy))
                    for i in range(area.Outline().OutlineCount()):
                        if area.Outline().Outline(i).PointInside(corner):
                            return (False, self.REASON_OTHER_SIGNAL)

        return (True, self.REASON_OK)

    def _is_in_target_zone(self, x, y):
        """Check if position is inside a target net zone"""
        test_point = VECTOR2I(int(x), int(y))

        nearby_zones = self.zone_hash.query_point(x, y, self.via_size)
        for area in nearby_zones:
            if area.GetNetname() != self.netname:
                continue
            if area.GetIsRuleArea():
                continue
            if self.only_selected_area and not area.IsSelected():
                continue

            # Check if point is inside this zone
            for i in range(area.Outline().OutlineCount()):
                outline = area.Outline().Outline(i)
                if outline.PointInside(test_point):
                    # Also check we're not too close to the edge
                    if not area.HitTestForEdge(test_point, int(self.via_size // 2 + self.clearance)):
                        if self.parent_area is None:
                            self.parent_area = area
                        return True

        return False

    # -------------------------------------------------------------------------
    # Nudge search
    # -------------------------------------------------------------------------

    def _find_valid_position(self, grid_x, grid_y):
        """
        Try to find a valid via position at or near the grid point.

        Args:
            grid_x, grid_y: Ideal grid position in KiCad internal units

        Returns:
            (x, y) of valid position, or None if no valid position found
        """
        # First check the exact grid position
        can_place, reason = self._check_position(grid_x, grid_y)
        if can_place and self._is_in_target_zone(grid_x, grid_y):
            return (grid_x, grid_y)

        if not self.nudge_enabled:
            return None

        # Calculate nudge parameters
        # Max nudge radius is half the grid step (stay in our cell)
        max_radius = self.nudge_max_radius or (self.grid_step // 2 - self.via_size // 2 - self.clearance)
        if max_radius <= 0:
            return None

        # Nudge step - try ~8-12 positions per axis within the cell
        nudge_step = self.nudge_step or max(max_radius // 6, FromMM(0.1))

        # Spiral search for valid position
        for dx, dy in spiral_offsets(max_radius, nudge_step):
            if dx == 0 and dy == 0:
                continue  # Already checked center

            test_x = grid_x + dx
            test_y = grid_y + dy

            # Must still be in target zone
            if not self._is_in_target_zone(test_x, test_y):
                continue

            can_place, reason = self._check_position(test_x, test_y)
            if can_place:
                return (test_x, test_y)

        return None

    # -------------------------------------------------------------------------
    # Via placement
    # -------------------------------------------------------------------------

    def _add_via(self, x, y):
        """Add a via at the specified position"""
        if self.parent_area is None:
            wxPrint("Error: No parent area found")
            return None

        via = PCB_VIA(self.parent_area)
        via.SetPosition(VECTOR2I(int(x), int(y)))

        if self.target_net is None:
            self.target_net = self.pcb.FindNet(self.netname)
        via.SetNet(self.target_net)
        via.SetViaType(VIATYPE_THROUGH)
        via.SetDrill(int(self.via_drill))
        via.SetWidth(int(self.via_size))
        via.SetIsFree(True)

        self.pcb.Add(via)
        if self.pcb_group:
            self.pcb_group.AddItem(via)

        # Track for collision detection with subsequent vias
        self.placed_vias.append((x, y))

        return via

    # -------------------------------------------------------------------------
    # Main entry point
    # -------------------------------------------------------------------------

    def Run(self):
        """Execute via stitching"""

        # Find next available group number for this net
        existing_numbers = []
        prefix = f"ViaStitching {self.netname} #"
        for group in self.pcb.Groups():
            name = group.GetName()
            if name.startswith(prefix):
                try:
                    num = int(name[len(prefix):])
                    existing_numbers.append(num)
                except ValueError:
                    pass

        next_number = 1
        if existing_numbers:
            next_number = max(existing_numbers) + 1

        VIA_GROUP_NAME = f"ViaStitching {self.netname} #{next_number}"

        # Create new group for this run
        self.pcb_group = PCB_GROUP(None)
        self.pcb_group.SetName(VIA_GROUP_NAME)
        self.pcb.Add(self.pcb_group)

        wxPrint(f"Creating group: {VIA_GROUP_NAME}")

        # Build spatial indexes
        self._build_spatial_indexes()

        # Get board bounds
        board_bbox = self.pcb.ComputeBoundingBox(False)
        origin_x = board_bbox.GetLeft()
        origin_y = board_bbox.GetTop()
        width = board_bbox.GetWidth()
        height = board_bbox.GetHeight()

        wxPrint(f"Board: {ToUserUnits(width, self.unit):.1f} x {ToUserUnits(height, self.unit):.1f} {self.unit}")
        wxPrint(f"Grid: {ToUserUnits(self.grid_step, self.unit):.1f} {self.unit}, "
                f"Via: {ToUserUnits(self.via_size, self.unit):.1f}/{ToUserUnits(self.via_drill, self.unit):.1f} {self.unit}")
        wxPrint(f"Pattern: {'staggered (brick)' if self.staggered_grid else 'rectangular'}, "
                f"Nudge: {'enabled' if self.nudge_enabled else 'disabled'}")
        wx.Yield()  # Show initial messages immediately

        # Calculate grid
        margin = self.via_size // 2 + self.clearance
        start_x = origin_x + margin
        start_y = origin_y + margin

        num_x = int((width - 2 * margin) // self.grid_step) + 1
        num_y = int((height - 2 * margin) // self.grid_step) + 1

        wxPrint(f"Checking {num_x} x {num_y} = {num_x * num_y} grid positions...")

        vias_placed = 0
        vias_nudged = 0
        positions_checked = 0

        # Create progress dialog for real-time feedback
        progress_dlg = wx.ProgressDialog(
            "Via Stitching Progress",
            "Starting via stitching...",
            maximum=num_y,
            parent=None,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME | wx.PD_CAN_ABORT
        )
        cancelled = False

        try:
            # Iterate through grid (Y outer loop for staggered pattern)
            for iy in range(num_y):
                grid_y = start_y + iy * self.grid_step

                # For staggered grid, offset odd rows by half the grid step
                if self.staggered_grid and (iy % 2 == 1):
                    row_offset = self.grid_step // 2
                else:
                    row_offset = 0

                # Update progress dialog
                status_msg = f"Row {iy+1}/{num_y} - {vias_placed} vias placed ({vias_nudged} nudged)"
                keep_going, _ = progress_dlg.Update(iy, status_msg)
                if not keep_going:
                    cancelled = True
                    wxPrint("Via stitching cancelled by user")
                    break

                for ix in range(num_x):
                    grid_x = start_x + ix * self.grid_step + row_offset
                    positions_checked += 1

                    # Check if this grid cell is in a target zone at all
                    if not self._is_in_target_zone(grid_x, grid_y):
                        continue

                    # Try to find valid position (with nudging if enabled)
                    result = self._find_valid_position(grid_x, grid_y)

                    if result:
                        place_x, place_y = result

                        # Apply random offset if enabled
                        if self.random_offset:
                            max_rand = max(self.grid_step // 4 - self.clearance, 0)
                            if max_rand > 0:
                                place_x += random.randint(-max_rand, max_rand)
                                place_y += random.randint(-max_rand, max_rand)

                        self._add_via(place_x, place_y)
                        vias_placed += 1

                        # Track if we nudged
                        if place_x != grid_x or place_y != grid_y:
                            vias_nudged += 1
        finally:
            progress_dlg.Destroy()

        # Mark zones for refill
        for i in range(self.pcb.GetAreaCount()):
            area = self.pcb.GetArea(i)
            area.SetNeedRefill(True)

        wxPrint(f"\n{'='*50}")
        if cancelled:
            wxPrint(f"CANCELLED: {vias_placed} vias placed before cancellation")
        else:
            wxPrint(f"COMPLETE: {vias_placed} vias placed")
        wxPrint(f"{'='*50}")
        wxPrint(f"  Grid positions checked: {positions_checked}")
        wxPrint(f"  Vias at exact grid points: {vias_placed - vias_nudged}")
        wxPrint(f"  Vias placed via nudge search: {vias_nudged}")
        if vias_nudged > 0:
            wxPrint(f"  (Nudge search found {vias_nudged} extra positions that would have been skipped)")
        wxPrint(f"\nRemember to refill zones: Edit > Fill All Zones (or press 'B')")

        return vias_placed


# =============================================================================
# Convenience function for command-line or console use
# =============================================================================

def run_enhanced_stitching(
    netname="GND",
    grid_mils=100,
    via_size_mils=24,
    via_drill_mils=12,
    clearance_mils=8,
    nudge=True,
    ignore_other_layers=True,
    unit='mil'
):
    """
    Run enhanced via stitching with mil-based parameters.

    Example:
        from FillAreaEnhanced import run_enhanced_stitching
        run_enhanced_stitching(grid_mils=100, via_size_mils=24, via_drill_mils=12)
    """
    filler = FillAreaEnhanced()
    filler.SetUnit(unit)
    filler.SetNetname(netname)
    filler.SetGridMils(grid_mils)
    filler.SetViaSizeMils(via_size_mils)
    filler.SetDrillMils(via_drill_mils)
    filler.SetClearanceMils(clearance_mils)
    filler.SetNudgeEnabled(nudge)
    filler.SetViaThroughAreas(ignore_other_layers)

    return filler.Run()


if __name__ == "__main__":
    # Test from command line
    import sys
    if len(sys.argv) > 1:
        board = LoadBoard(sys.argv[1])
        filler = FillAreaEnhanced(board)
        filler.SetUnit('mil')
        filler.SetGridMils(100)
        filler.SetViaSizeMils(24)
        filler.SetDrillMils(12)
        filler.SetClearanceMils(8)
        filler.SetNudgeEnabled(True)
        filler.SetViaThroughAreas(True)
        filler.Run()
        board.Save(sys.argv[1])
    else:
        print("Usage: python FillAreaEnhanced.py <board.kicad_pcb>")
