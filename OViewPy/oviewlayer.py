import string
import requests
import json
import threading
import time
from progress.spinner import Spinner
from progress.bar import Bar
from OViewPy.server import Server
from OViewPy.varstruct import VarStruct, GeoBoundary, GeoPolygon


class OViewLayer:
    def __init__(self, server: Server, layerName: string) -> None:
        self.__server = server
        self.__layerName = layerName
        self.__layerInfo = None
        param = VarStruct()
        ret = VarStruct()
        param.Set("layername", self.__layerName)
        isSuccess = self.__server.DoCommand(
            command="Get3DLayerInfo",
            parm=param,
            ret=ret
        )
        if isSuccess:
            info = ret.ToDict()
            if info["success"]:
                self.__layerInfo = info["ret"]

    def getOviewLayerInfo(self) -> dict:
        return self.__layerInfo

    def getVectorEmtity(self, epsg: int = 4326, sql: str = "") -> dict:
        param = VarStruct()
        param.Set("LAYERNAME", self.__layerName)
        param.Set("SQL", sql)
        ret = VarStruct()
        spinner = Spinner('Loading ')
        docmdThread = threading.Thread(
            target=self.__server.DoCommand, args=("OV_SEARCHBYSQL", param, ret,))
        docmdThread.start()
        def loadingAnimate():
            while docmdThread.is_alive() :
                time.sleep(0.1)
                spinner.next()
        t = threading.Thread(target=loadingAnimate)
        t.start()
        docmdThread.join()
        retDict = None
        spinnerDissect = Spinner('Process： ')
        def animate():
            while retDict is None:
                time.sleep(0.1)
                spinnerDissect.next()
        t = threading.Thread(target=animate)
        t.start()
        retDict = ret.ToDict()
        fieldRet = self.__layerInfo[0]["field"]
        if retDict["SUCCESS"]:
            ret = retDict["RET"]
            geo = []
            attr = []
            bar = Bar('Process： ', max=len(ret))
            for i in range(len(ret)):
                geoVS = VarStruct()
                attrVS = VarStruct()
                geoVS.FromJson(json.dumps(ret[i]["geo"]))
                for j in range(len(fieldRet)):
                    attrValue = None
                    if fieldRet[j]["Type"] == 1:
                        attrValue = int(ret[i]["attr"][j])
                    elif fieldRet[j]["Type"] == 2:
                        attrValue = float(ret[i]["attr"][j])
                    elif fieldRet[j]["Type"] == 3:
                        attrValue = ret[i]["attr"][j]
                    attrVS.Set(fieldRet[j]["Name"], attrValue)
                geo.append(geoVS)
                attr.append(attrVS)
                bar.next()
            bar.finish()
            Emtity = {
                "success": True,
                "geo": geo,
                "attr": attr
            }
            return Emtity
        else:
            return retDict
