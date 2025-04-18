import pcbnew
import os
import wx
import json

from pcbnew import VECTOR2I, wxPoint, wxPointMM, wxSize, FromMM

from mirrorfold_dialog import MirrorFoldDialog

def getIdentifier(item):
    return str(item.GetPosition().x)+";"+str(item.GetPosition().y)+";"+str(item.GetLayerName())


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
                for d in fp.GraphicalItems():
                    if (d.GetLayer() in sourceLayers):
                        newd = d.Duplicate()
                        #newd.TransformShapeToPolygon()
                        #for some reason, text flips the wrong way
                        newd.Mirror(fold_plane,flip_dir)

                        
                        layerIndex = sourceLayers.index(d.GetLayer())
                        newd.SetLayer(destLayers[layerIndex])

                        saveData["placed"].append(getIdentifier(newd))

                        self.board.Add(newd)
            
            with open("mirrorfold_state.json", "w") as f:
                json.dump(saveData, f)





        dialog.Destroy()

MirrorFold().register()