#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  FillAreaActionEnhanced.py
#  Enhanced via stitching action plugin with spatial indexing and nudge search
#
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com> (original FillAreaAction.py)
#  Copyright 2025 Geoff Wall / Ceres Imaging (enhancements)
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
import pcbnew
import wx
from . import FillAreaEnhanced
from . import FillAreaDialogEnhanced
import os


def PopulateNets(anet, dlg):
    """Populate net dropdown with zone nets"""
    netnames = list(set([zone.GetNetname() for zone in pcbnew.GetBoard().Zones()]))
    netnames.sort()
    dlg.m_cbNet.Set(netnames)
    if anet is not None:
        index = dlg.m_cbNet.FindString(anet)
        if index != wx.NOT_FOUND:
            dlg.m_cbNet.Select(index)
        elif netnames:
            dlg.m_cbNet.Select(0)


class FillAreaActionEnhanced(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Enhanced Via Stitching"
        self.category = "Modify PCB"
        self.description = "Via Stitching with nudge search and mil support"
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "./stitching-vias.png")
        self.show_toolbar_button = True

    def Run(self):
        # Create dialog
        dlg = FillAreaDialogEnhanced.FillAreaDialogEnhanced(None)

        # Get board design settings for defaults
        board = pcbnew.GetBoard()
        ds = board.GetDesignSettings()

        # Set defaults from board design settings
        dlg.SetSizeFromMM(pcbnew.ToMM(ds.GetCurrentViaSize()))
        dlg.SetDrillFromMM(pcbnew.ToMM(ds.GetCurrentViaDrill()))
        dlg.SetClearanceFromMM(pcbnew.ToMM(ds.GetSmallestClearanceValue()))
        # Grid defaults to 100 mil (2.54mm) - already set in dialog

        # Pass board reference for group management
        dlg.SetBoard(board)

        dlg.SetMinSize(dlg.GetSize())

        # Populate nets
        PopulateNets("GND", dlg)

        # Show dialog
        modal_result = dlg.ShowModal()

        if modal_result == wx.ID_OK:
            wx.LogMessage('Enhanced Via Stitching starting...')

            try:
                # Create enhanced filler
                fill = FillAreaEnhanced.FillAreaEnhanced(board)

                # Set parameters (all values returned as mm)
                fill.SetViaSizeMM(dlg.GetSizeValue())
                fill.SetDrillMM(dlg.GetDrillValue())
                fill.SetClearanceMM(dlg.GetClearanceValue())
                fill.SetHoleClearanceMM(dlg.GetHoleClearanceValue())
                fill.SetGridMM(dlg.GetStepValue())

                # Set net
                netname = dlg.m_cbNet.GetStringSelection()
                fill.SetNetname(netname)

                # Set options
                fill.SetStaggeredGrid(dlg.m_Staggered.IsChecked())
                fill.SetNudgeEnabled(dlg.m_Nudge.IsChecked())
                fill.SetViaThroughAreas(dlg.m_viaThroughAreas.IsChecked())
                fill.SetSameNetTracks(dlg.m_sameNetTracks.IsChecked())
                fill.SetOnlySelectedArea(dlg.m_only_selected.IsChecked())
                fill.SetRandomOffset(dlg.m_Random.IsChecked())
                fill.SetUnit(dlg.GetUnit())

                # Run!
                vias_placed = fill.Run()

                wx.LogMessage(f'Enhanced Via Stitching complete: {vias_placed} vias placed')

            except Exception as e:
                wx.LogError(f"Error during via stitching: {str(e)}")
                import traceback
                wx.LogError(traceback.format_exc())
        else:
            print("Cancelled")

        dlg.Destroy()


# Register the plugin
FillAreaActionEnhanced().register()
