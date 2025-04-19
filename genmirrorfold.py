import pcbnew
import os
import wx
import json

from pcbnew import VECTOR2I, wxPoint, wxPointMM, wxSize, FromMM

from mirrorfold_dialog import MirrorFoldDialog

def getIdentifier(item):
    return str(item.GetPosition().x)+";"+str(item.GetPosition().y)+";"+str(item.GetLayerName())

def getPadIdentifier(item):
    return str(item.GetPosition().x)+";"+str(item.GetPosition().y)+";"+str(item.GetName())


"""
def createTHTPad(component,num,pos, drill,size):
    newMod = io.FootprintLoad(LIBPATH, FOOTPRINT)
    newMod.SetReference("P-%s-%d" % (component, num))
    x = CENTER[0] + r * math.cos(theta)
    newMod.SetPosition(pos)
"""


class MirrorFold(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Mirror Fold"
        self.category = "-"
        self.description = "-"
        self.show_toolbar_button = True # Optional, defaults to False"

    def Run(self):
        self.board = pcbnew.GetBoard()

        board_file = self.board.GetFileName()
        self.board_path = os.path.abspath(board_file)
        os.chdir(os.path.dirname(self.board_path))

        saveData = {}
        if os.path.exists("mirrorfold_state.json"):
            with open("mirrorfold_state.json", "r") as f:
                saveData = json.load(f)

        dialog = MirrorFoldDialog(None)
        dialog.mirror_dist.SetValue(saveData.get("mirror_dist", 50))
        dialog.mirror_dir.SetSelection(saveData.get("mirror_dir", 0))
        modal_result = dialog.ShowModal()
        if modal_result == wx.ID_OK:
            fold_dist = FromMM(dialog.mirror_dist.GetValue())
            flip_dir = None
            fold_plane = VECTOR2I(fold_dist, fold_dist)
            match dialog.mirror_dir.GetStringSelection():
                case "horizontal":
                    flip_dir = pcbnew.FLIP_DIRECTION_LEFT_RIGHT
                case "vertical":
                    flip_dir = pcbnew.FLIP_DIRECTION_TOP_BOTTOM

            for d in self.board.GetDrawings():
                if(getIdentifier(d) in saveData.get("placed", [])):
                    self.board.Remove(d)

            saveData = {"mirror_dist": dialog.mirror_dist.GetValue(), "mirror_dir": dialog.mirror_dir.GetSelection(),"placed": []}

            sourceLayers = [pcbnew.User_2,pcbnew.User_3,pcbnew.User_4]
            destLayers = [pcbnew.Edge_Cuts,pcbnew.F_SilkS,pcbnew.B_SilkS]

            for fp in self.board.GetFootprints():
                if (fp.GetReference().endswith("_FoldPads")):
                    self.board.Remove(fp)

            for fp in self.board.GetFootprints():
                hasCutout = False
                for d in fp.GraphicalItems():
                    if (d.GetLayer() in sourceLayers):

                        newd = d.Duplicate()
                        #for some reason, text flips the wrong way and behaves weird in general
                        print("a")
                        try:
                            newd_text = newd.GetShownText(True)
                            if (flip_dir == pcbnew.FLIP_DIRECTION_LEFT_RIGHT):
                                newd.Mirror(fold_plane,pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
                            else:
                                newd.Mirror(fold_plane,pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
                            newd.SetText(newd_text)
                            newd.SetMirrored(not d.IsMirrored())
                        except:
                            newd.Mirror(fold_plane,flip_dir)

                        
                        layerIndex = sourceLayers.index(d.GetLayer())
                        newLayer = destLayers[layerIndex]
                        if (newLayer == pcbnew.Edge_Cuts):
                            hasCutout = True
                        newd.SetLayer(newLayer)

                        saveData["placed"].append(getIdentifier(newd))
                        
                        self.board.Add(newd)

                fpnew = pcbnew.FOOTPRINT(self.board)
                fpnew.SetReference(fp.GetReference()+"_FoldPads")
                fpnew_pos = fp.GetPosition()-fold_plane
                if(flip_dir == pcbnew.FLIP_DIRECTION_LEFT_RIGHT):
                    fpnew_pos.x *= -1
                else:
                    fpnew_pos.y *= -1
                fpnew_pos += fold_plane
                
                fpnew.SetPosition(fpnew_pos)

                fpnew.SetLayer(pcbnew.F_SilkS)

                hasNewPads = False
                for pad in fp.Pads():
                    pname = pad.GetName()

                    if (not (pname.endswith("_F") or pname.endswith("_FC"))):
                        continue

                    hasNewPads = True
                    newpad = pad.Duplicate()

                    pad_pos = pad.GetPosition()-fold_plane
                    if(flip_dir == pcbnew.FLIP_DIRECTION_LEFT_RIGHT):
                        pad_pos.x *= -1
                    else:
                        pad_pos.y *= -1

                    pad_pos += fold_plane

                    newpad.SetPosition(pad_pos)

                    if(pname.endswith("_FC")):
                        pad.SetProperty(pcbnew.PAD_PROP_CASTELLATED)

                    saveData["placed"].append(getPadIdentifier(newpad))
                    fpnew.Add(newpad)

                if (hasNewPads):
                    self.board.Add(fpnew)

            with open("mirrorfold_state.json", "w") as f:
                json.dump(saveData, f)





        dialog.Destroy()

MirrorFold().register()