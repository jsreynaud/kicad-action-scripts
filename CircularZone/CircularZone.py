from math import *
import pcbnew
from .CircularZoneDlg import CircularZoneDlg
import wx
import os


class CircularZone(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Circular Zone\nKeepout Zone Generator"
        self.category = "Modify PCB"
        self.description = "Create a Circular Zone\nor a Circular Keepout Zone"
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "./round_keepout_area.png")
        self.show_toolbar_button = True

    def build(self, center_x, center_y, radius, keepout, edge_count):
        sp = pcbnew.SHAPE_POLY_SET()
        sp.NewOutline()
        cnt = int(edge_count)
        for i in range(cnt):
            x = int(center_x + radius * cos(i * 2 * pi / cnt))
            y = int(center_y + radius * sin(i * 2 * pi / cnt))
            sp.Append(x, y)
        # sp.OutlineCount()
        sp.thisown = 0
        zone = pcbnew.ZONE(self.pcb)
        zone.SetOutline(sp)
        zone.SetLayer(pcbnew.F_Cu)
        zone.SetIsRuleArea(keepout)
        zone.SetDoNotAllowCopperPour(keepout)
        zone.SetDoNotAllowFootprints(keepout)
        zone.SetDoNotAllowPads(keepout)
        zone.SetDoNotAllowTracks(keepout)
        zone.SetDoNotAllowVias(keepout)

        zone.thisown = 0
        self.pcb.Add(zone)

    def Warn(self, message, caption='Warning!'):
        dlg = wx.MessageDialog(
            None, message, caption, wx.OK | wx.ICON_WARNING)
        dlg.ShowModal()
        dlg.Destroy()

    def CheckInput(self, value, data):
        val = None
        try:
            val = float(value)
            if val == 0:
                raise Exception("Invalid")
        except:
            self.Warn(
                "Invalid parameter for %s: Must be a positive number" % data)
            val = None
        return val

    def Run(self):
        self.pcb = pcbnew.GetBoard()
        a = CircularZoneDlg(None)
        x = 0
        y = 0
        reference = None
        for module in self.pcb.Footprints():
            if module.IsSelected():
                x = module.GetPosition().x
                y = module.GetPosition().y
                reference = module.GetReference()
                break
        if reference is None:
            a.m_comment.SetLabel("No reference position: start at origin")
        else:
            a.m_comment.SetLabel("Using %s as position reference" % reference)

        a.m_radiusMM.SetValue("10")
        modal_result = a.ShowModal()

        segment = self.CheckInput(
            a.m_textCtrl_seg.GetValue(), "segment number")
        radius = self.CheckInput(a.m_radiusMM.GetValue(), "radius")

        if segment is not None and radius is not None:
            if modal_result == wx.ID_OK:
                self.build(x, y, pcbnew.FromMM(
                    radius), a.m_radio_out.GetValue(), segment)
            else:
                None  # Cancel
        else:
            None  # Invalid input
        a.Destroy()
