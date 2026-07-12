#!/usr/bin/env python3
#
#  viastitching_action.py
#
#  Via stitching generator for KiCad, based on FillArea.py
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com>
#  Ported to the KiCad IPC API (kicad-python), 2026
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

import math
import os
import random
import sys
import traceback

import wx

from kipy.board_types import BoardLayer, Group, Via
from kipy.geometry import Vector2
from kipy.util.units import from_mm, to_mm
from shapely.geometry import Point
from shapely.geometry import box as shapely_box
from shapely.ops import polygonize, unary_union
from shapely.prepared import prep

from kicad_connect import connect_to_kicad
from kipy_shapely import (
    board_shape_to_shapely,
    polygon_to_shapely,
    track_to_shapely,
    zone_outline_to_shapely,
)

PATTERN_RECTANGULAR = "Rectangular"
PATTERN_STAR = "Star"
PATTERN_CONCENTRIC = "Concentric"
PATTERN_OUTLINE = "Outline"
PATTERN_OUTLINE_NO_HOLES = "Outline (No Holes)"

ORIGIN_BOARD_BOUNDS = "Board Bounds"
ORIGIN_ABSOLUTE = "Absolute (0, 0)"
ORIGIN_GRID = "Grid Origin"

GROUP_NAME_TEMPLATE = "ViaStitching {}"


def is_copper_layer(layer):
    return BoardLayer.Name(layer).endswith("_Cu")


class ViaStitcher:
    """Places stitching vias inside all copper zones of one net.

    All geometry work is done with shapely on the zone/track/pad outlines
    reported over the IPC API, so the algorithm is independent of KiCad's
    internal (SWIG) geometry classes.
    """

    def __init__(self, board, log=None):
        self.board = board
        self.log = log or (lambda msg: None)

        self.netname = "GND"
        self.size = from_mm(0.46)
        self.drill = from_mm(0.20)
        self.clearance = from_mm(0.2)
        self.edge_clearance = from_mm(0.5)
        self.step = from_mm(2.54)
        self.pattern = PATTERN_RECTANGULAR
        self.origin_mode = ORIGIN_BOARD_BOUNDS
        self.random_offset = False
        self.only_selected = False
        self.via_through_areas = False
        self.ignore_same_net_tracks = False
        self.refill_after = True

    # ------------------------------------------------------------------
    # Obstacle map
    # ------------------------------------------------------------------

    def _target_zones(self, zones):
        target = [
            z
            for z in zones
            if not z.is_rule_area()
            and z.net is not None
            and z.net.name == self.netname
            and any(is_copper_layer(l) for l in z.layers)
        ]
        if self.only_selected:
            selected_ids = {
                item.id.value for item in self.board.get_selection() if hasattr(item, "id")
            }
            target = [z for z in target if z.id.value in selected_ids]
        return target

    def _build_allowed_area(self):
        """Returns a shapely geometry containing all points where the
        center of a new stitching via may be placed."""
        margin = self.clearance + self.size / 2

        zones = list(self.board.get_zones())
        target_zones = self._target_zones(zones)
        if not target_zones:
            raise RuntimeError(
                "No copper zone found for net '{}'{}".format(
                    self.netname, " in selection" if self.only_selected else ""
                )
            )

        target_polys = []
        target_layer_priority = []  # (layers, priority, polygon)
        filled_count = 0
        for zone in target_zones:
            # Prefer the actual filled copper: the drawn zone outline may
            # extend past the board edge or cover areas that do not get
            # copper, which would produce dangling vias
            polys = []
            for layer, filled in zone.filled_polygons.items():
                if is_copper_layer(layer):
                    polys.extend(
                        p
                        for p in (polygon_to_shapely(f) for f in filled)
                        if p is not None and not p.is_empty
                    )
            if polys:
                filled_count += 1
            else:
                outline = zone_outline_to_shapely(zone)
                if outline is None or outline.is_empty:
                    continue
                polys = [outline]
            poly = unary_union(polys)
            target_polys.append(poly)
            target_layer_priority.append((set(zone.layers), zone.priority, poly))

        if not target_polys:
            raise RuntimeError("Target zones have no usable outline")
        if filled_count < len(target_polys):
            self.log(
                "Warning: {} zone(s) are not filled; using the drawn outline "
                "instead of the copper shape".format(len(target_polys) - filled_count)
            )

        allowed = unary_union(target_polys).buffer(-margin)
        self.log("Target area built from {} zone(s)".format(len(target_polys)))

        # Clip against the board outline (Edge.Cuts), respecting the
        # copper-to-edge clearance
        edge_margin = max(self.edge_clearance, self.clearance) + self.size / 2
        board_poly, edge_lines = self._board_polygon()
        if board_poly is not None:
            allowed = allowed.intersection(board_poly.buffer(-edge_margin))
            self.log("Board outline applied (with {:.3f} mm edge clearance)".format(
                to_mm(int(edge_margin - self.size / 2))))

        obstacles = []

        # Rule areas (keep-outs) that exclude vias
        for zone in zones:
            if not zone.is_rule_area():
                continue
            try:
                keepout_vias = zone.proto.rule_area_settings.keepout_vias
            except AttributeError:
                keepout_vias = False
            if not keepout_vias:
                continue
            poly = zone_outline_to_shapely(zone)
            if poly is not None and not poly.is_empty:
                obstacles.append(poly.buffer(self.size / 2))
        if obstacles:
            self.log("{} via keep-out area(s) considered".format(len(obstacles)))

        # Copper zones of other nets (unless vias may pass through them).
        # A same-net zone with higher priority uncovers the blocked region.
        if not self.via_through_areas:
            for zone in zones:
                if zone.is_rule_area():
                    continue
                if zone.net is not None and zone.net.name == self.netname:
                    continue
                if not any(is_copper_layer(l) for l in zone.layers):
                    continue
                poly = zone_outline_to_shapely(zone)
                if poly is None or poly.is_empty:
                    continue
                zone_layers = set(zone.layers)
                covers = [
                    t_poly
                    for t_layers, t_priority, t_poly in target_layer_priority
                    if t_priority > zone.priority and (t_layers & zone_layers)
                ]
                if covers:
                    poly = poly.difference(unary_union(covers))
                if not poly.is_empty:
                    obstacles.append(poly.buffer(margin))

        # If the board outline could not be assembled into a closed
        # polygon, at least keep clear of the individual edge drawings
        if board_poly is None and edge_lines:
            self.log(
                "Warning: board outline is not closed; keeping distance to "
                "{} edge segment(s) only".format(len(edge_lines))
            )
            for geom in edge_lines:
                obstacles.append(geom.buffer(edge_margin))

        # Pads (front and back polygonal shapes; through-hole pads
        # have a shape on both)
        pads = list(self.board.get_pads())
        pad_polys = 0
        for layer in (BoardLayer.BL_F_Cu, BoardLayer.BL_B_Cu):
            try:
                shapes = self.board.get_pad_shapes_as_polygons(pads, layer)
            except Exception as e:
                self.log("Warning: could not get pad shapes: {}".format(e))
                shapes = []
            for pad_poly in shapes:
                if pad_poly is None:
                    continue
                poly = polygon_to_shapely(pad_poly)
                if poly is not None and not poly.is_empty:
                    obstacles.append(poly.buffer(margin))
                    pad_polys += 1
        self.log("{} pad shape(s) considered".format(pad_polys))

        # Tracks
        track_count = 0
        for track in self.board.get_tracks():
            if (
                self.ignore_same_net_tracks
                and track.net is not None
                and track.net.name == self.netname
            ):
                continue
            line = track_to_shapely(track)
            obstacles.append(line.buffer(track.width / 2 + margin))
            track_count += 1
        self.log("{} track(s) considered".format(track_count))

        # Existing vias (all nets, including the target net: new vias
        # must not overlap them)
        for via in self.board.get_vias():
            obstacles.append(
                Point(via.position.x, via.position.y).buffer(via.diameter / 2 + margin)
            )

        # Text on outer copper layers
        try:
            texts = [
                t
                for t in self.board.get_text()
                if getattr(t, "layer", None) in (BoardLayer.BL_F_Cu, BoardLayer.BL_B_Cu)
            ]
            if texts:
                boxes = self.board.get_item_bounding_box(texts)
                for b in boxes:
                    if b is None:
                        continue
                    obstacles.append(
                        shapely_box(
                            b.pos.x, b.pos.y, b.pos.x + b.size.x, b.pos.y + b.size.y
                        ).buffer(margin)
                    )
        except Exception as e:
            self.log("Warning: could not process copper text: {}".format(e))

        if obstacles:
            allowed = allowed.difference(unary_union(obstacles))

        return allowed

    def _board_polygon(self):
        """Assemble the Edge.Cuts drawings into a closed board polygon.

        Returns (polygon, edge_lines). polygon is None if the outline
        could not be closed; edge_lines always contains the shapely
        geometries of the individual edge drawings.
        """
        edge_lines = []
        for shape in self.board.get_shapes():
            if shape.layer != BoardLayer.BL_Edge_Cuts:
                continue
            geom = board_shape_to_shapely(shape)
            if geom is not None and not geom.is_empty:
                edge_lines.append(geom)
        if not edge_lines:
            return None, edge_lines
        try:
            faces = list(polygonize(unary_union(edge_lines)))
        except Exception:
            faces = []
        if not faces:
            return None, edge_lines
        # The largest face is the board area; cutouts appear as holes in it
        return max(faces, key=lambda f: f.area), edge_lines

    # ------------------------------------------------------------------
    # Candidate generation
    # ------------------------------------------------------------------

    def _grid_origin(self, allowed):
        if self.origin_mode == ORIGIN_ABSOLUTE:
            return (0, 0)
        if self.origin_mode == ORIGIN_GRID:
            try:
                from kipy.proto.board import board_commands_pb2

                origin = self.board.get_origin(
                    board_commands_pb2.BoardOriginType.BOT_GRID
                )
                return (origin.x, origin.y)
            except Exception as e:
                self.log("Warning: grid origin not available ({}), using board bounds".format(e))
        minx, miny, _, _ = allowed.bounds
        return (minx, miny)

    def _grid_candidates(self, allowed):
        """Rectangular or star (staggered) grid of via positions."""
        step = max(self.step, self.size + self.clearance)
        minx, miny, maxx, maxy = allowed.bounds
        ox, oy = self._grid_origin(allowed)

        ix0 = int(math.floor((minx - ox) / step))
        ix1 = int(math.ceil((maxx - ox) / step))
        iy0 = int(math.floor((miny - oy) / step))
        iy1 = int(math.ceil((maxy - oy) / step))

        max_jitter = max(self.step - (self.clearance + self.size), 0) / 2.0

        prepared = prep(allowed)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                if self.pattern == PATTERN_STAR and (ix + iy) % 2:
                    continue
                x = ox + ix * step
                y = oy + iy * step
                if self.random_offset and max_jitter > 0:
                    x += random.uniform(-max_jitter / 2, max_jitter / 2)
                    y += random.uniform(-max_jitter / 2, max_jitter / 2)
                if prepared.contains(Point(x, y)):
                    yield (x, y)

    def _ring_candidates(self, allowed):
        """Via positions along the outline of the allowed area, optionally
        repeated on concentric inner rings."""
        spacing = max(self.step, self.size + self.clearance)
        ring_step = max(self.step, self.size + self.clearance)
        min_dist = max(spacing * 0.6, self.size + self.clearance)

        placed = []

        def far_enough(x, y):
            for px, py in placed:
                if math.hypot(px - x, py - y) < min_dist:
                    return False
            return True

        current = allowed
        offset_fraction = 0.0
        while current is not None and not current.is_empty:
            rings = []
            geoms = getattr(current, "geoms", [current])
            for geom in geoms:
                if geom.is_empty or not hasattr(geom, "exterior"):
                    continue
                rings.append(geom.exterior)
                if self.pattern != PATTERN_OUTLINE_NO_HOLES:
                    rings.extend(geom.interiors)

            for ring in rings:
                length = ring.length
                if length <= 0:
                    continue
                count = max(1, int(length // spacing))
                stepsize = length / count
                for i in range(count):
                    p = ring.interpolate((i + offset_fraction) * stepsize)
                    if far_enough(p.x, p.y):
                        placed.append((p.x, p.y))
                        yield (p.x, p.y)

            if self.pattern != PATTERN_CONCENTRIC:
                break
            current = current.buffer(-ring_step)
            offset_fraction = 0.5 if offset_fraction == 0.0 else 0.0

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _find_net(self):
        for net in self.board.get_nets():
            if net.name == self.netname:
                return net
        raise RuntimeError("Net '{}' not found".format(self.netname))

    def run(self):
        net = self._find_net()
        allowed = self._build_allowed_area()
        if allowed.is_empty:
            self.log("No space left for stitching vias")
            return 0

        if self.pattern in (PATTERN_RECTANGULAR, PATTERN_STAR):
            candidates = self._grid_candidates(allowed)
        else:
            candidates = self._ring_candidates(allowed)

        vias = []
        for x, y in candidates:
            via = Via()
            via.position = Vector2.from_xy(int(x), int(y))
            via.diameter = int(self.size)
            via.drill_diameter = int(self.drill)
            via.net = net
            vias.append(via)

        if not vias:
            self.log("No via positions found")
            return 0

        # Commit 1: create the vias and make them exist on the board.
        commit = self.board.begin_commit()
        try:
            created = self.board.create_items(vias)
            self.board.push_commit(commit, "Via stitching ({})".format(self.netname))
        except Exception:
            self.board.drop_commit(commit)
            raise

        # Commit 2: group the now-existing vias. A group's members are
        # resolved by KiCad from item UUIDs that must already be on the
        # board, so this cannot happen in the same commit as the vias
        # (otherwise the group ends up empty and is pruned on push).
        self._group_vias(created)

        # Sidecar record of the via UUIDs, independent of the group, so
        # deletion works even if the group is lost (e.g. dissolved by the
        # user or not persisted by a given KiCad version).
        self._remember_vias(created)

        if self.refill_after:
            self.log("Refilling zones...")
            try:
                self.board.refill_zones()
            except Exception as e:
                self.log("Warning: zone refill failed: {}".format(e))

        self.log("Done. {} vias placed.".format(len(created)))
        return len(created)

    # ------------------------------------------------------------------
    # Grouping and persistent bookkeeping
    # ------------------------------------------------------------------

    def _group_name(self):
        return GROUP_NAME_TEMPLATE.format(self.netname)

    def _group_vias(self, created):
        """Put the created (already existing) vias into a named group so
        the user can select and delete them as one unit."""
        group_name = self._group_name()
        commit = self.board.begin_commit()
        try:
            existing = next(
                (g for g in self.board.get_groups() if g.name == group_name), None
            )
            if existing is not None:
                existing.items = list(existing.items) + list(created)
                self.board.update_items(existing)
            else:
                group = Group()
                # Group.name has no setter in kicad-python <= 0.7.x
                group.proto.name = group_name
                group.items = list(created)
                self.board.create_items(group)
            self.board.push_commit(commit, "Group stitching vias ({})".format(self.netname))
        except Exception as e:
            self.board.drop_commit(commit)
            self.log("Warning: could not create group '{}': {}".format(group_name, e))

    def _sidecar_path(self):
        """Path of the file that stores the via UUIDs, next to the board."""
        try:
            project_path = self.board.get_project().path
            board_file = self.board.document.board_filename
        except Exception:
            return None
        if not project_path or not board_file:
            return None
        base = os.path.splitext(board_file)[0]
        return os.path.join(project_path, base + ".viastitching")

    def _remember_vias(self, created):
        path = self._sidecar_path()
        if path is None:
            return
        ids = set()
        for existing in self._recall_via_ids():
            ids.add(existing)
        for via in created:
            ids.add(via.id.value)
        try:
            with open(path, "w") as f:
                f.write("# Via UUIDs placed by the Via Stitching plugin. Safe to delete.\n")
                for value in sorted(ids):
                    f.write(value + "\n")
        except OSError as e:
            self.log("Warning: could not write sidecar file: {}".format(e))

    def _recall_via_ids(self):
        path = self._sidecar_path()
        if path is None or not os.path.exists(path):
            return set()
        try:
            with open(path) as f:
                return {
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                }
        except OSError:
            return set()

    def _clear_sidecar(self):
        path = self._sidecar_path()
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def delete_vias(self):
        """Remove all vias created by previous runs for this net, using
        the named group and the sidecar UUID record together."""
        from kipy.proto.common.types import base_types_pb2

        group_name = self._group_name()
        groups = self.board.get_groups()
        target_group = next((g for g in groups if g.name == group_name), None)

        # Collect UUIDs to remove from both sources
        id_values = set(self._recall_via_ids())
        if target_group is not None:
            for item in target_group.items:
                id_values.add(item.id.value)

        # Keep only UUIDs that still exist on the board
        present = {v.id.value for v in self.board.get_vias()}
        id_values &= present

        if not id_values and target_group is None:
            raise RuntimeError(
                "Nothing to delete: no group named '{}' and no recorded vias "
                "were found for this net.".format(group_name)
            )

        commit = self.board.begin_commit()
        try:
            if id_values:
                kiids = []
                for value in id_values:
                    kiid = base_types_pb2.KIID()
                    kiid.value = value
                    kiids.append(kiid)
                self.board.remove_items_by_id(kiids)
            if target_group is not None:
                self.board.remove_items(target_group)
            self.board.push_commit(commit, "Delete stitching vias ({})".format(self.netname))
        except Exception:
            self.board.drop_commit(commit)
            raise

        self._clear_sidecar()
        self.log("Removed {} vias".format(len(id_values)))
        return len(id_values)


# ----------------------------------------------------------------------
# Dialog
# ----------------------------------------------------------------------


class ViaStitchingDialog(wx.Dialog):
    def __init__(self, board):
        super().__init__(
            None,
            title="Via Stitching (IPC)",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.board = board

        zone_nets = sorted(
            {
                z.net.name
                for z in board.get_zones()
                if not z.is_rule_area() and z.net is not None and z.net.name
            }
        )
        default_net = next(
            (n for n in ("GND", "/GND") if n in zone_nets),
            zone_nets[0] if zone_nets else "",
        )

        grid = wx.FlexGridSizer(0, 2, 4, 8)
        grid.AddGrowableCol(1)

        def add_row(label, ctrl):
            grid.Add(
                wx.StaticText(self, label=label),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
                4,
            )
            grid.Add(ctrl, 1, wx.EXPAND | wx.RIGHT, 4)
            return ctrl

        self.net = add_row(
            "Net name", wx.ComboBox(self, value=default_net, choices=zone_nets, style=wx.CB_READONLY)
        )
        self.size = add_row("Via copper size (mm)", wx.TextCtrl(self, value="0.46"))
        self.drill = add_row("Via drill size (mm)", wx.TextCtrl(self, value="0.2"))
        self.clearance = add_row("Via clearance (mm)", wx.TextCtrl(self, value="0.2"))
        self.edge_clearance = add_row(
            "Board edge clearance (mm)", wx.TextCtrl(self, value="0.5")
        )
        self.step = add_row("Via grid / step (mm)", wx.TextCtrl(self, value="2.54"))
        self._apply_netclass_defaults(default_net)
        self.net.Bind(
            wx.EVT_COMBOBOX,
            lambda evt: self._apply_netclass_defaults(self.net.GetValue()),
        )
        self.pattern = add_row(
            "Pattern",
            wx.ComboBox(
                self,
                value=PATTERN_RECTANGULAR,
                choices=[
                    PATTERN_RECTANGULAR,
                    PATTERN_STAR,
                    PATTERN_CONCENTRIC,
                    PATTERN_OUTLINE,
                    PATTERN_OUTLINE_NO_HOLES,
                ],
                style=wx.CB_READONLY,
            ),
        )
        self.origin = add_row(
            "Grid origin",
            wx.ComboBox(
                self,
                value=ORIGIN_BOARD_BOUNDS,
                choices=[ORIGIN_BOARD_BOUNDS, ORIGIN_ABSOLUTE, ORIGIN_GRID],
                style=wx.CB_READONLY,
            ),
        )
        self.random = add_row("Random offset", wx.CheckBox(self))
        self.only_selected = add_row("Only selected zones", wx.CheckBox(self))
        self.through = add_row("Ignore zones on other layers", wx.CheckBox(self))
        self.same_net = add_row("Also on tracks with same net", wx.CheckBox(self))
        self.refill = add_row("Refill zones when done", wx.CheckBox(self))
        self.refill.SetValue(True)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        run_btn = wx.Button(self, wx.ID_OK, "Run")
        run_btn.SetDefault()
        delete_btn = wx.Button(self, wx.ID_DELETE, "Delete Vias")
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Cancel")
        buttons.AddStretchSpacer()
        buttons.Add(run_btn, 0, wx.ALL, 4)
        buttons.Add(delete_btn, 0, wx.ALL, 4)
        buttons.Add(cancel_btn, 0, wx.ALL, 4)
        delete_btn.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_DELETE))

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(grid, 1, wx.EXPAND | wx.ALL, 8)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 4)
        self.SetSizerAndFit(outer)
        self.Centre()

    def _apply_netclass_defaults(self, netname):
        """Preset via size/drill/clearance from the net class of the
        selected net, like the board would use for new vias."""
        try:
            net = next(n for n in self.board.get_nets() if n.name == netname)
            netclass = self.board.get_netclass_for_nets(net).get(netname)
            if netclass is None:
                return
            if netclass.via_diameter:
                self.size.SetValue(str(to_mm(netclass.via_diameter)))
            if netclass.via_drill:
                self.drill.SetValue(str(to_mm(netclass.via_drill)))
            if netclass.clearance:
                self.clearance.SetValue(str(to_mm(netclass.clearance)))
        except Exception:
            pass  # keep the generic defaults

    def configure(self, stitcher):
        def mm_value(ctrl):
            return from_mm(float(ctrl.GetValue().replace(",", ".")))

        stitcher.netname = self.net.GetValue()
        stitcher.size = mm_value(self.size)
        stitcher.drill = mm_value(self.drill)
        stitcher.clearance = mm_value(self.clearance)
        stitcher.edge_clearance = mm_value(self.edge_clearance)
        stitcher.step = mm_value(self.step)
        stitcher.pattern = self.pattern.GetValue()
        stitcher.origin_mode = self.origin.GetValue()
        stitcher.random_offset = self.random.IsChecked()
        stitcher.only_selected = self.only_selected.IsChecked()
        stitcher.via_through_areas = self.through.IsChecked()
        stitcher.ignore_same_net_tracks = not self.same_net.IsChecked()
        stitcher.refill_after = self.refill.IsChecked()


def main():
    app = wx.App()
    try:
        kicad, board = connect_to_kicad(client_name="via-stitching")
    except Exception as e:
        wx.MessageBox(
            "Could not connect to KiCad:\n\n{}".format(e), "Via Stitching", wx.ICON_ERROR
        )
        return 1

    dialog = ViaStitchingDialog(board)
    result = dialog.ShowModal()
    if result not in (wx.ID_OK, wx.ID_DELETE):
        dialog.Destroy()
        return 0

    messages = []
    stitcher = ViaStitcher(board, log=messages.append)
    try:
        dialog.configure(stitcher)
        if result == wx.ID_OK:
            count = stitcher.run()
            wx.MessageBox(
                "Done. {} vias placed.\n\n{}".format(count, "\n".join(messages)),
                "Via Stitching",
            )
        else:
            count = stitcher.delete_vias()
            wx.MessageBox(
                "Removed {} vias.".format(count),
                "Via Stitching",
            )
    except Exception as e:
        traceback.print_exc()
        wx.MessageBox(
            "Error: {}\n\n{}".format(e, "\n".join(messages)),
            "Via Stitching",
            wx.ICON_ERROR,
        )
        return 1
    finally:
        dialog.Destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
