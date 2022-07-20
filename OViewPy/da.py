import imp
import string
import json
import numpy as np
import cv2
import os
import shapefile
from decimal import Decimal
from progress.bar import Bar
from shapely.geometry import shape, mapping
from OViewPy.varstruct import GeoBoundary, VarStruct


class da:
    def __init__(self) -> None:
        pass

    @staticmethod
    def imgToNumPyArray(img: bytes) -> np.array:
        if img == None:
            return
        return np.frombuffer(img, dtype="uint8")

    @staticmethod
    def numPyArrayToImg(array: np.array) -> bytes:
        if (array == None).any():
            return
        return array.tobytes()

    @staticmethod
    def vectorEmtityToNumPyArray(emtity):
        if emtity is None:
            return
        if type(emtity) == list:
            geoList = []
            for i in range(len(emtity)):
                emtityDict = emtity[i].ToDict()
                geoList.append(np.asarray(
                    emtityDict["coordinates"], dtype=object))
            return geoList
        elif type(emtity) == VarStruct:
            emtityDict = emtity.ToDict()
            return np.asarray(emtityDict["coordinates"], dtype=object)
        else:
            return None

    @staticmethod
    def numPyArrayToVarStruct(emtity):
        if emtity is None:
            return None
        if type(emtity) == list:
            geoList = []
            for i in range(len(emtity)):
                varEm = VarStruct()
                if emtity[i].ndim == 1:
                    varEm.Set("type", "Point")
                    varEm.Set("coordinates", emtity[i].tolist())
                elif emtity[i].ndim == 2:
                    if type(emtity[i][0][0]) == list:
                        varEm.Set("type", "MultiPolygon")
                        varEm.Set("coordinates", emtity[i].tolist())
                    else:
                        varEm.Set("type", "LineString")
                        varEm.Set("coordinates", emtity[i].tolist())
                elif emtity[i].ndim == 4:
                    varEm.Set("type", "MultiPolygon")
                    varEm.Set("coordinates", emtity[i].tolist())
                geoList.append(varEm)
            return geoList
        elif type(emtity) == np.ndarray:
            varEm = VarStruct()
            if emtity.ndim == 1:
                varEm.Set("type", "Point")
                varEm.Set("coordinates", emtity.tolist())
            elif emtity.ndim == 2:
                if type(emtity[0][0]) == list:
                    varEm.Set("type", "MultiPolygon")
                    varEm.Set("coordinates", emtity.tolist())
                else:
                    varEm.Set("type", "LineString")
                    varEm.Set("coordinates", emtity.tolist())
            elif emtity.ndim == 4:
                varEm.Set("type", "MultiPolygon")
                varEm.Set("coordinates", emtity.tolist())
            return varEm
        else:
            return None

    @staticmethod
    def vectorEmtityToShapely(emtity):
        if emtity is None:
            return
        if type(emtity) == list:
            geoList = []
            for i in range(len(emtity)):
                emtityDict = emtity[i].ToDict()
                geoList.append(shape(emtityDict))
            return geoList
        elif type(emtity) == VarStruct:
            return shape(emtity.ToDict())
        else:
            return None

    @staticmethod
    def shapelyToVarstruct(emtity):
        if emtity is None:
            return None
        if type(emtity) == list:
            geoList = []
            for i in range(len(emtity)):
                varEm = VarStruct()
                varEm.FromJson(json.dumps(mapping(emtity[i])))
                geoList.append(varEm)
            return geoList
        else:
            varEm = VarStruct()
            varEm.FromJson(json.dumps(mapping(emtity)))
            return varEm

    @staticmethod
    def showImg(img: bytes):
        if img == None:
            return
        image = np.frombuffer(img, dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_UNCHANGED)
        cv2.imshow('image', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    @staticmethod
    def saveImg(img: bytes, savePath: string = ".", imgName: string = "defaultImg", imgType: string = "png", worldFile: bool = False, boundary: GeoBoundary = None) -> bool:
        if img == None:
            return False
        imgIndex = 1
        if imgType == "jpg":
            worldFileType = "jgw"
        elif imgType == "gif":
            worldFileType = "gfw"
        elif imgType == "jp2":
            worldFileType = "j2w"
        elif imgType == "png":
            worldFileType = "pgw"
        elif imgType == "tif":
            worldFileType = "tfw"
        imgPath = f"{savePath}/{imgName}.{imgType}"
        worldFilePath = f"{savePath}/{imgName}.{worldFileType}"
        while os.path.exists(imgPath):
            imgIndex += 1
            imgPath = f"{savePath}/{imgName}{imgIndex}.{imgType}"
            worldFilePath = f"{savePath}/{imgName}{imgIndex}.{worldFileType}"
        image = np.frombuffer(img, dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_UNCHANGED)
        height, width, channels = image.shape
        image = cv2.imencode("."+imgType, image)[1]
        image = image.tobytes()
        try:
            with open(imgPath, 'wb') as f:
                f.write(image)
                f.flush()
            if worldFile and boundary:
                with open(worldFilePath, 'w') as f:
                    f.write(str(Decimal((boundary.east - boundary.west)/width)))
                    f.write("\n")
                    f.write(str(0.0))
                    f.write("\n")
                    f.write(str(0.0))
                    f.write("\n")
                    f.write(str(Decimal((boundary.south - boundary.north)/height)))
                    f.write("\n")
                    f.write(str(boundary.west))
                    f.write("\n")
                    f.write(str(boundary.north))
                    f.close()
        except:
            return False
        return True

    @staticmethod
    def saveAsShapeFile(sourceGeo: list, sourceAttr: list, savePath: string = ".", fileName: string = "defaultShp", encoding: string = "ansi") -> bool:
        if sourceGeo == None or sourceAttr == None:
            return False
        if type(sourceGeo[0]) == np.ndarray:
            sourceGeo = da.numPyArrayToVarStruct(sourceGeo)
            sourceGeo = da.vectorEmtityToShapely(sourceGeo)
        elif type(sourceGeo[0]) == VarStruct:
            sourceGeo = da.vectorEmtityToShapely(sourceGeo)
        fileIndex = 1
        filePath = f"{savePath}/{fileName}"
        while os.path.exists(filePath+".shp"):
            fileIndex += 1
            filePath = f"{savePath}/{fileName}{fileIndex}"
        w = shapefile.Writer(filePath, encoding=encoding)
        attrFieldList = list(sourceAttr[0].ToDict().keys())
        fieldsBar = Bar('Fields Creating  ', max=len(attrFieldList))
        for i in range(len(attrFieldList)):
            attrType = type(list(sourceAttr[0].ToDict().values())[i])
            if attrType == string:
                w.field(attrFieldList[i], 'C')
            elif attrType == int:
                w.field(attrFieldList[i], 'N')
            elif attrType == float:
                w.field(attrFieldList[i], 'N', decimal=15)
            elif attrType == bool:
                w.field(attrFieldList[i], 'L')
            else:
                w.field(attrFieldList[i], 'C')
            fieldsBar.next()
        fieldsBar.finish()
        geoBar = Bar('Converting  ', max=len(sourceGeo))
        for i in range(len(sourceGeo)):
            w.record(*list(sourceAttr[i].ToDict().values()))
            if sourceGeo[i].geom_type == "Point":
                w.multipoint(list(sourceGeo[i].coords))
            elif sourceGeo[i].geom_type == "Point Z":
                w.multipointz(list(sourceGeo[i].coords))
            elif sourceGeo[i].geom_type == "LineString":
                w.line([list(sourceGeo[i].coords)])
            elif sourceGeo[i].geom_type == "LineString Z":
                w.linez(sourceGeo[i].coords)
            elif sourceGeo[i].geom_type == "MultiPolygon":
                poly = []
                for j in range(len(sourceGeo[i].geoms)):
                    poly.append(sourceGeo[i].geoms[j].exterior.coords)
                w.poly(poly)
            elif sourceGeo[i].geom_type == "MultiPolygon Z":
                poly = []
                for j in range(len(sourceGeo[i].geoms)):
                    poly.append(sourceGeo[i].geoms[j].exterior.coords)
            elif sourceGeo[i].geom_type == "Polygon":
                w.poly(list(sourceGeo[i].exterior.coords))
            elif sourceGeo[i].geom_type == "Polygon Z":
                w.polyz(list(sourceGeo[i].exterior.coords))
            geoBar.next()
        geoBar.finish()
        w.close()
        return True
        