import string
import requests
import json
import threading
import time
from progress.spinner import Spinner
from progress.bar import Bar
from OViewPy.server import Server
from OViewPy.varstruct import VarStruct, GeoBoundary, GeoPolygon


class Layer:
    def __init__(self, server: Server, layerName: string) -> None:
        self.__server = server
        self.__layerName = layerName
        self.__layerInfo = None
        param = VarStruct()
        ret = VarStruct()
        param.Set("layername", layerName)
        isSuccess = server.DoCommand(
            command="Get2DLayerInfo",
            parm=param,
            ret=ret
        )
        if isSuccess:
            info = ret.ToDict()
            if info["success"]:
                self.__layerInfo = info["ret"][0]

    @property
    def server(self):
        return self.__server

    @property
    def layerName(self):
        return self.__layerName

    @property
    def layerInfo(self):
        return self.__layerInfo

    def getMapImage(self, boundary: GeoBoundary = None, width: int = 512, height: int = 512, crs="EPSG:4326", format="image/png") -> bytes:
        if boundary == None:
            jsStr = json.dumps(
                self.layerInfo["boundary"], default=lambda obj: obj.ToJsonDict(False))
            boundary = GeoBoundary().FromJson(jsStr)
            crs = "EPSG:"+str(self.layerInfo["epsgcode"])
        data = {
            "service": "WMS",
            "version": 1.3,
            "request": "GetMap",
            "layers": self.layerName,
            "style": "",
            "crs": crs,
            "bbox": f"{boundary.west},{boundary.south},{boundary.east},{boundary.north}",
            "width": width,
            "height": height,
            "format": format,
            "transparent": True
        }
        url = self.__server.wmsURL
        response = None
        spinner = Spinner('Loading ')

        def animate():
            while response is None:
                time.sleep(0.1)
                spinner.next()
        t = threading.Thread(target=animate)
        t.start()
        response = requests.get(url, params=data, stream=True)
        spinner.finish()
        if response.status_code != 200:
            return None
        return response.content


class RasterLayer(Layer):
    def __init__(self, server: Server, layerName: string) -> None:
        super().__init__(server, layerName)
        if self.layerInfo["type"] != "Raster":
            raise TypeError('This layer is not a RasterLayer')
        pass


class VectorLayer(Layer):
    def __init__(self, server: Server, layerName: string) -> None:
        super().__init__(server, layerName)
        if self.layerInfo["type"] != "Vector":
            raise TypeError('This layer is not a VectorLayer')
        pass

    def getVectorEmtity(self, bound=None, epsg: int = 4326, sql: str = "") -> dict:
        param = VarStruct()
        fieldParam = VarStruct()
        fieldParam.Set("layername", self.layerName)
        ret = VarStruct()
        fieldRet = VarStruct()
        searchCmd = ""
        if bound == None:
            param.Set("layername", self.layerName)
            param.Set("sql", sql)
            searchCmd = "SearchBySQL"
        elif isinstance(bound, GeoBoundary):
            param.Set("layername", self.layerName)
            param.Set("epsgcode", epsg)
            param.Set("geo", bound.ToGeoPolygon())
            param.Set("sql", sql)
            searchCmd = "SearchByInclude"
        elif isinstance(bound, GeoPolygon):
            param.Set("layername", self.layerName)
            param.Set("epsgcode", epsg)
            param.Set("geo", bound)
            param.Set("sql", sql)
            searchCmd = "SearchByInclude"
        else:
            raise ValueError('You must pass either GeoBoundary or GeoPolygon')

        spinner = Spinner('Loading ')
        docmdThread = threading.Thread(
            target=self.server.DoCommand, args=(searchCmd, param, ret,))
        fieldDocmdThread = threading.Thread(
            target=self.server.DoCommand, args=("GetFieldDefine", fieldParam, fieldRet,))
        docmdThread.start()
        fieldDocmdThread.start()

        def loadingAnimate():
            while docmdThread.is_alive() or fieldDocmdThread.is_alive():
                time.sleep(0.1)
                spinner.next()
        t = threading.Thread(target=loadingAnimate)
        t.start()
        docmdThread.join()
        fieldDocmdThread.join()
        retDict = None
        spinnerDissect = Spinner('Process： ')

        def animate():
            while retDict is None:
                time.sleep(0.1)
                spinnerDissect.next()
        t = threading.Thread(target=animate)
        t.start()
        retDict = ret.ToDict()
        fieldRet = fieldRet.ToDict()
        if retDict["success"] and fieldRet["success"]:
            ret = retDict["ret"]["ent"]
            geo = []
            attr = []
            bar = Bar('Process： ', max=len(ret))
            for i in range(len(ret)):
                geoVS = VarStruct()
                attrVS = VarStruct()
                geoVS.FromJson(json.dumps(ret[i]["geo"]))
                for j in range(len(fieldRet["ret"]["fieldname"])):
                    attrValue = None
                    if fieldRet["ret"]["fieldtype"][j] == 1:
                        attrValue = int(ret[i]["attr"][j])
                    elif fieldRet["ret"]["fieldtype"][j] == 2:
                        attrValue = float(ret[i]["attr"][j])
                    elif fieldRet["ret"]["fieldtype"][j] == 3:
                        attrValue = ret[i]["attr"][j]
                    attrVS.Set(fieldRet["ret"]["fieldname"][j], attrValue)
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
            return ret
