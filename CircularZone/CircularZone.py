from math import *
import pcbnew
from CircularZoneDlg import CircularZoneDlg
import wx


class CircularZone(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Create a circular zone"
        self.category = "Undefined"
        self.description = ""

    def build(self, center_x, center_y, radius, keepout):
        sp = pcbnew.SHAPE_POLY_SET()
        sp.NewOutline()
        cnt = 100
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
        if modal_result == wx.ID_OK:
            self.build(x, y, pcbnew.FromMM(
                int(a.m_radiusMM.GetValue())), a.m_radio_out.GetValue())
        else:
            print "Cancel"
        a.Destroy()
