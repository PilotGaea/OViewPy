import string
import json
import threading
import time
import numpy as np
import os
import rasterio
from rasterio.transform import from_bounds
import matplotlib.pyplot as plt
import geojsoncontour
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

    def getOviewLayerInfo(self) -> dict:
        return self.__layerInfo


class OViewEmtityLayer(OViewLayer):
    def __init__(self, server: Server, layerName: string) -> None:
        super().__init__(server, layerName)

    def getVectorEmtity(self, bound=None, epsg: int = 4326, sql: str = "") -> dict:
        param = VarStruct()
        fieldParam = VarStruct()
        fieldParam.Set("LAYERNAME", self.layerName)
        ret = VarStruct()
        fieldRet = VarStruct()
        searchCmd = ""
        if bound == None:
            param.Set("LAYERNAME", self.layerName)
            param.Set("SQL", sql)
            searchCmd = "OV_SEARCHBYSQL"
        elif isinstance(bound, GeoBoundary):
            param.Set("LAYERNAME", self.layerName)
            param.Set("EPSG", epsg)
            param.Set("GEO", bound.ToGeoPolygon())
            param.Set("SQL", sql)
            searchCmd = "OV_SEARCHBYINCLUDE"
        elif isinstance(bound, GeoPolygon):
            param.Set("LAYERNAME", self.layerName)
            param.Set("EPSG", epsg)
            param.Set("GEO", bound)
            param.Set("SQL", sql)
            searchCmd = "OV_SEARCHBYINCLUDE"
        else:
            raise ValueError('You must pass either GeoBoundary or GeoPolygon')

        spinner = Spinner('Loading ')
        docmdThread = threading.Thread(
            target=self.server.DoCommand, args=(searchCmd, param, ret,))
        docmdThread.start()

        def loadingAnimate():
            while docmdThread.is_alive():
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
        fieldRet = self.layerInfo["field"]
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
                    if fieldRet[j]["Type"] == "Integer":
                        attrValue = int(ret[i]["attrs"][j])
                    elif fieldRet[j]["Type"] == "Double":
                        attrValue = float(ret[i]["attrs"][j])
                    elif fieldRet[j]["Type"] == "String":
                        attrValue = ret[i]["attrs"][j]
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


class TerrainLayer(OViewLayer):
    def __init__(self, server: Server, layerName: string) -> None:
        super().__init__(server, layerName)
        if self.layerInfo["type"] != "Terrain":
            raise TypeError('This layer is not a TerrainLayer')

    def getDEMMatrix(self, boundary: GeoBoundary, cellDemSize: int = 500, epsg: int = 4326) -> np.ndarray:
        if boundary is None or type(boundary) != GeoBoundary:
            raise ValueError("You must pass either GeoBoundary")
        parm = VarStruct()
        parm.Set("layerName", self.layerName)
        parm.Set("epsg", epsg)
        parm.Set("cellDemSize", cellDemSize)
        parm.Set("boundary", boundary)
        ret = VarStruct()
        spinner = Spinner('Loading ')
        docmdThread = threading.Thread(
            target=self.server.DoCommand, args=("GetTerrainMatrix", parm, ret,))
        docmdThread.start()

        def loadingAnimate():
            while docmdThread.is_alive():
                time.sleep(0.1)
                spinner.next()
            spinner.finish()
        t = threading.Thread(target=loadingAnimate)
        t.start()
        docmdThread.join()
        if ret.ToDict()["success"]:
            return np.asarray(ret.ToDict()["matrix"])
        else:
            raise SystemError(ret.ToDict()["error"])

    def hillshadeAnalysis(self, boundary: GeoBoundary, cellDemSize: int = 500, epsg: int = 4326, azimuth: int = 30, altitude: int = 30, savePath: string = ".", fileName: string = "defaultDEM", width: int = 21600, height: int = 21600):
        def hillshade(array, azimuth, angle_altitude):
            x, y = np.gradient(array)
            slope = np.pi/2. - np.arctan(np.sqrt(x*x + y*y))
            aspect = np.arctan2(-x, y)
            azimuth = azimuth*np.pi / 180.
            altitude = angle_altitude*np.pi / 180.
            shade = np.sin(altitude) * np.sin(slope) + np.cos(altitude) * \
                np.cos(slope) * np.cos(azimuth - aspect)
            return 255*(shade + 1)/2
        matrix = self.getDEMMatrix(
            boundary=boundary, cellDemSize=cellDemSize, epsg=epsg)
        hs_array = hillshade(matrix, azimuth, altitude)
        fileIndex = 1
        filePath = f"{savePath}/{fileName}.tif"
        while os.path.exists(filePath):
            fileIndex += 1
            filePath = f"{savePath}/{fileName}{fileIndex}.tif"
        with rasterio.open(
            filePath,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            crs="EPSG:4326",
            count=1,
            transform=from_bounds(boundary.west, boundary.south, boundary.east,
                                  boundary.north, width, height),
            dtype=hs_array.dtype
        ) as dst:
            dst.write(hs_array, 1)
            return True

    def slopeAnalysis(self, boundary: GeoBoundary, cellDemSize: int = 500, epsg: int = 4326, savePath: string = ".", fileName: string = "defaultSlope", width: int = 21600, height: int = 21600):
        def slope_gradient(z):
            x, y = np.gradient(z)
            slope = (np.pi/2. - np.arctan(np.sqrt(x*x + y*y)))
            return slope
        matrix = self.getDEMMatrix(
            boundary=boundary, cellDemSize=cellDemSize, epsg=epsg)
        slope_array = slope_gradient(matrix)
        fileIndex = 1
        filePath = f"{savePath}/{fileName}.tif"
        while os.path.exists(filePath):
            fileIndex += 1
            filePath = f"{savePath}/{fileName}{fileIndex}.tif"
        with rasterio.open(
            filePath,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            crs="EPSG:4326",
            count=1,
            transform=from_bounds(boundary.west, boundary.south, boundary.east,
                                  boundary.north, width, height),
            dtype=slope_array.dtype
        ) as dst:
            dst.write(slope_array, 1)
            return True

    def aspectAnalysis(self, boundary: GeoBoundary, cellDemSize: int = 500, epsg: int = 4326, savePath: string = ".", fileName: string = "defaultAspect", width: int = 21600, height: int = 21600):
        def aspect(z):
            x, y = np.gradient(z)
            return np.arctan2(-x, y)
        matrix = self.getDEMMatrix(
            boundary=boundary, cellDemSize=cellDemSize, epsg=epsg)
        aspect_array = aspect(matrix)
        fileIndex = 1
        filePath = f"{savePath}/{fileName}.tif"
        while os.path.exists(filePath):
            fileIndex += 1
            filePath = f"{savePath}/{fileName}{fileIndex}.tif"
        with rasterio.open(
            filePath,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            crs="EPSG:4326",
            count=1,
            transform=from_bounds(boundary.west, boundary.south, boundary.east,
                                  boundary.north, width, height),
            dtype=aspect_array.dtype
        ) as dst:
            dst.write(aspect_array, 1)
            return True

    def contourLineAnalysis(self, boundary: GeoBoundary, cellDemSize: int = 500, epsg: int = 4326, savePath: string = ".", fileName: string = "defaultContourLine", fileType: string = "image", width: int = 21600, height: int = 21600, levels: int = 20):
        matrix = self.getDEMMatrix(
            boundary=boundary, cellDemSize=cellDemSize, epsg=epsg)
        xdata = []
        ydata = []
        xGeoCount = (boundary.east - boundary.west) / (len(matrix) - 1)
        yGeoCount = (boundary.north - boundary.south) / (len(matrix[0]) - 1)
        for i in range(len(matrix)):
            for j in range(len(matrix[0])):
                xdata.append(float(boundary.east - xGeoCount*i))
                ydata.append(float(boundary.north - yGeoCount*j))
        nrows, ncols = matrix.shape
        xi = np.linspace(min(xdata), max(xdata), ncols)
        yi = np.linspace(max(ydata), min(ydata), nrows)
        X, Y = np.meshgrid(xi, yi)
        width = width*0.0104166667
        height = height*0.0104166667
        fig = plt.figure(figsize=(width, height))
        ax = fig.add_subplot(1, 1, 1)
        contourf = plt.contourf(X, Y, matrix, levels,
                                alpha=0.75, cmap=plt.cm.jet)
        C = plt.contour(X, Y, matrix, levels, colors='black')
        if fileType == "image":
            fileIndex = 1
            filePath = f"{savePath}/{fileName}"
            while os.path.exists(f"{filePath}.png"):
                fileIndex += 1
                filePath = f"{savePath}/{fileName}{fileIndex}"
            plt.clabel(C, inline=True, fontsize=10)
            plt.savefig(f"{filePath}.png",
                        bbox_inches='tight', pad_inches=-0.05)
        elif fileType == "geojson":
            fileIndex = 1
            filePath = f"{savePath}/{fileName}"
            while os.path.exists(f"{filePath}.geojson"):
                fileIndex += 1
                filePath = f"{savePath}/{fileName}{fileIndex}"
            geo_json = geojsoncontour.contour_to_geojson(
                contour=C,
                ndigits=3,
                unit='m'
            )
            with open(f"{filePath}.geojson", 'w') as outfile:
                outfile.write(geo_json)
                outfile.close()
        else:
            raise ValueError("You must pass either image or geojson")
        print("Done!")


class ModelLayer(OViewEmtityLayer):
    def __init__(self, server: Server, layerName: string) -> None:
        super().__init__(server, layerName)
        if self.layerInfo["type"] != "Model":
            raise TypeError('This layer is not a ModelLayer')


class ModelSetLayer(OViewEmtityLayer):
    def __init__(self, server: Server, layerName: string) -> None:
        super().__init__(server, layerName)
        if self.layerInfo["type"] != "ModelSet":
            raise TypeError('This layer is not a ModelSetLayer')


class PipeLineLayer(OViewEmtityLayer):
    def __init__(self, server: Server, layerName: string) -> None:
        super().__init__(server, layerName)
        if self.layerInfo["type"] != "Pipeline":
            raise TypeError('This layer is not a PipelineSetLayer')
