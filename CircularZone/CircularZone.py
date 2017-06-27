from math import *
import pcbnew
from CircularZoneDlg import CircularZoneDlg
import wx


class CircularZone(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Create a circular zone"
        self.category = "Undefined"
        self.description = ""

    def build(self, center_x, center_y, radius, keepout, edge_count):
        sp = pcbnew.SHAPE_POLY_SET()
        sp.NewOutline()
        cnt = edge_count
        for i in range(cnt):
            x = int(center_x + radius * cos(i * 2 * pi / cnt))
            y = int(center_y + radius * sin(i * 2 * pi / cnt))
            sp.Append(x, y)
        # sp.OutlineCount()
        sp.thisown = 0
        zone = pcbnew.ZONE_CONTAINER(self.pcb)
        zone.SetOutline(sp)
        zone.SetLayer(pcbnew.F_Cu)
        zone.SetIsKeepout(keepout)
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
            val = int(value)
            if val < 1:
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
        for module in self.pcb.GetModules():
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
