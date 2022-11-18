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
from sridentify import Sridentify
from OViewPy.varstruct import GeoBoundary, VarStruct
import rasterio
from rasterio.transform import from_bounds



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
    def vectorEntityToNumPyArray(Entity):
        if Entity is None:
            return
        if type(Entity) == list:
            geoList = []
            for i in range(len(Entity)):
                EntityDict = Entity[i].ToDict()
                geoList.append(np.asarray(
                    EntityDict["coordinates"], dtype=object))
            return geoList
        elif type(Entity) == VarStruct:
            EntityDict = Entity.ToDict()
            return np.asarray(EntityDict["coordinates"], dtype=object)
        else:
            return None

    @staticmethod
    def __makeEnt2VarStruct(Entity) -> VarStruct:
        varEm = VarStruct()
        if Entity.ndim == 1:
            varEm.Set("type", "Point")
            varEm.Set("coordinates", Entity.tolist())
        elif Entity.ndim == 2:
            if type(Entity[0][0]) == list:
                varEm.Set("type", "MultiPolygon")
                varEm.Set("coordinates", Entity.tolist())
            else:
                varEm.Set("type", "LineString")
                varEm.Set("coordinates", Entity.tolist())
        elif Entity.ndim == 4:
            varEm.Set("type", "MultiPolygon")
            varEm.Set("coordinates", Entity.tolist())
        return varEm

    @staticmethod
    def numPyArrayToVarStruct(Entity):
        if Entity is None:
            return None
        if type(Entity) == list:
            geoList = []
            for i in range(len(Entity)):
                ent = Entity[i]
                varEm = da.__makeEnt2VarStruct(ent)
                geoList.append(varEm)
            return geoList
        elif type(Entity) == np.ndarray:
            varEm = da.__makeEnt2VarStruct(Entity)
            return varEm
        else:
            return None

    @staticmethod
    def vectorEntityToShapely(Entity):
        if Entity is None:
            return
        if type(Entity) == list:
            geoList = []
            for i in range(len(Entity)):
                EntityDict = Entity[i].ToDict()
                geoList.append(shape(EntityDict))
            return geoList
        elif type(Entity) == VarStruct:
            return shape(Entity.ToDict())
        else:
            return None

    @staticmethod
    def shapelyToVarstruct(Entity):
        if Entity is None:
            return None
        if type(Entity) == list:
            geoList = []
            for i in range(len(Entity)):
                varEm = VarStruct()
                varEm.FromJson(json.dumps(mapping(Entity[i])))
                geoList.append(varEm)
            return geoList
        else:
            varEm = VarStruct()
            varEm.FromJson(json.dumps(mapping(Entity)))
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
        if img is None:
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
        img = cv2.imencode("."+imgType, image)[1]
        img = img.tobytes()
        with open(imgPath, 'wb') as f:
                f.write(img)
                f.flush()
        if worldFile and boundary:
            height, width, channels = image.shape
            with open(worldFilePath, 'w') as worldFile:
                worldFile.write(str(float((boundary.east - boundary.west)/width)))
                worldFile.write("\n")
                worldFile.write(str(0.0))
                worldFile.write("\n")
                worldFile.write(str(0.0))
                worldFile.write("\n")
                worldFile.write(str(float((boundary.south - boundary.north)/height)))
                worldFile.write("\n")
                worldFile.write(str(boundary.west))
                worldFile.write("\n")
                worldFile.write(str(boundary.north))
                worldFile.close()
        return True

    @staticmethod
    def saveAsShapeFile(sourceGeo: list, sourceAttr: list, epsg: int = 4326, savePath: string = ".", fileName: string = "defaultShp", encoding: string = "ansi") -> bool:
        if sourceGeo == None or sourceAttr == None:
            return False
        if type(sourceGeo[0]) == np.ndarray:
            sourceGeo = da.numPyArrayToVarStruct(sourceGeo)
            sourceGeo = da.vectorEntityToShapely(sourceGeo)
        elif type(sourceGeo[0]) == VarStruct:
            sourceGeo = da.vectorEntityToShapely(sourceGeo)
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
        ident = Sridentify()
        ident.from_epsg(epsg)
        ident.to_prj(f'{filePath}.prj')
        return True
    
       
    @staticmethod
    def numPyArrayToTIF(Entity: np.ndarray,  boundary: GeoBoundary, savePath: string = ".", fileName: string = "defaultTIF", width: int = 21600, height: int = 21600):
        if Entity is None:
            return None
        filePath = f"{savePath}/{fileName}.tif"
        fileIndex = 1
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
            dtype=Entity.dtype
        ) as dst:
            dst.write(Entity, 1)
            return True

