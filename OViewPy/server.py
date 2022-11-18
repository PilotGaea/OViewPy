import os
import string
import requests
import threading
import time

from numpy import number
from progress.spinner import Spinner
from progress.bar import Bar
from OViewPy.varstruct import GeoBoundary, VarStruct




class Server:
    def __init__(self, url) -> None:
        self.__serverURL = url
        self.__wmtsURL = url + "/wmts?"
        self.__wmsURL = url + "/wms?"
        self.__docmdURL = url + "/DoCmd?cmd="
        header = {
            "Content-Type": "application/json"
        }
        response = requests.get(
            url=self.__docmdURL + "GetServerInfo",
            headers=header,
            timeout=100000
        )
        if response.status_code == 200:
            jsonStr = response.json()
            self.__version = jsonStr["FullVersion"]
        else:
            self.__version = None

    @property
    def version(self) -> string:
        return self.__version

    @property
    def wmsURL(self) -> string:
        return self.__wmsURL

    @property
    def wmtsURL(self) -> string:
        return self.__wmtsURL

    @property
    def docmdURL(self) -> string:
        return self.__docmdURL

    @property
    def serverURL(self) -> string:
        return self.__serverURL
    
    def __loadingAnimate(docmdThread: threading.Thread):
        spinner = Spinner('Loading ')
        while docmdThread.is_alive():
            time.sleep(0.1)
            spinner.next()
            spinner.finish()
        

    def DoCommand(self, command: string, parm: VarStruct, ret: VarStruct, timeOut=100000) -> bool:
        header = {
            "Content-Type": "application/json"
        }
        if(parm != None):
            data = parm.ToJson()
        else:
            data = ""
        url = self.__docmdURL + command
        response = requests.post(
            url=url, headers=header, data=data.encode('utf-8'), timeout=timeOut)
        if response.status_code == 200:
            jsonStr = response.text
            ret.FromJson(jsonStr)
            return True
        else:
            jsonStr = response.text
            print(jsonStr)
            raise SystemError('Server Error')

    def getLayerList(self):
        parm = VarStruct()
        ret = VarStruct()
        self.DoCommand(command="GetAll2DLayerInfo", parm=parm, ret=ret)
        retDict = ret.ToDict()
        if retDict["success"]:
            return retDict["ret"]
        else:
            return retDict

    def getOViewLayerList(self):
        parm = VarStruct()
        ret = VarStruct()
        self.DoCommand(command="GetAll3DLayerInfo", parm=parm, ret=ret)
        retDict = ret.ToDict()
        if retDict["success"]:
            return retDict["ret"]
        else:
            return retDict

    def deleteLayer(self, layerName: string = None):
        if layerName == None:
            return False
        parm = VarStruct()
        ret = VarStruct()
        parm.Set("layername", layerName)
        self.DoCommand(command="Delete2DLayer", parm=parm, ret=ret)
        retDict = ret.ToDict()
        if retDict["success"]:
            return True
        else:
            return False

    def deleteOViewLayer(self, layerName: string = None):
        if layerName == None:
            return False
        parm = VarStruct()
        ret = VarStruct()
        parm.Set("layername", layerName)
        self.DoCommand(command="Delete3DLayer", parm=parm, ret=ret)
        retDict = ret.ToDict()
        if retDict["success"]:
            return True
        else:
            return False

    def saveImageToServer(self, imageFilePath: string, layerName: string, epsg: int = 4326):
        parm = VarStruct()
        parm.Set("imageFilePath", imageFilePath)
        parm.Set("outputFilePath", imageFilePath + ".tif")
        parm.Set("layerName", layerName)
        parm.Set("epsg", epsg)
        ret = VarStruct()
        spinner = Spinner('Loading ')
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("Image2RasterLayer", parm, ret,))
        docmdThread.start()
        
        def loadingAnimate():
            while docmdThread.is_alive():
                time.sleep(0.1)
                spinner.next()
            spinner.finish()
        t = threading.Thread(target=loadingAnimate)
        t.start()
        docmdThread.join()
        print("Done！")
        return

    def saveVectorFileToServer(self, VectorFilePath: string, layerName: string, epsg: number = 4326):
        parm = VarStruct()
        parm.Set("sourceUrl", VectorFilePath)
        parm.Set("layerName", layerName)
        parm.Set("epsg", epsg)
        ret = VarStruct()
        spinner = Spinner('Loading ')
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("VectorFile2VectorLayer", parm, ret,))
        docmdThread.start()

        def loadingAnimate():
            while docmdThread.is_alive():
                time.sleep(0.1)
                spinner.next()
            spinner.finish()
        t = threading.Thread(target=loadingAnimate)
        t.start()
        docmdThread.join()
        print("Done！")
        return
    
    def convertPhotogrammetry(self, layerName: string, layerDBFile: string, inputFileName: string, terrainDBFile: string, terrainName: string, exportType: string):
        if not os.path.exists(terrainDBFile):
            raise FileNotFoundError("terrainDBFile file is not found.")
        if not os.path.exists(inputFileName):
            raise FileExistsError("inputFileName is not found.")
        if os.path.isfile(layerDBFile): #判定layerDBFile是否已存在
            raise os.error("layerDBFile already been existed, please change the file name.")
        terrainDBFile = os.path.abspath(terrainDBFile)
        layerDBFile = os.path.abspath(layerDBFile)
        
        exportTypeStr = exportType.upper()
        if (exportTypeStr != "NORMAL") and (exportTypeStr != "I3S") and (exportTypeStr != "3DTILES"): #判定輸出檔案名是否正確
            raise ValueError("exportType is incorrect. You should enter 'NORMAL' or 'I3S' or '3DTILES'. ")
        
        param = VarStruct()
        param.Set("layerName", layerName)
        param.Set("layerDBFile", layerDBFile)
        param.Set("inputFileName", inputFileName)
        param.Set("terrainDBFile", terrainDBFile)
        param.Set("terrainName", terrainName)
        param.Set("exportTypeStr", exportTypeStr)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvertPhotogrammetry", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["id"]
    
    def convertPipeline(self, layerName: string, layerDBFile: string, terrainName: string, terrainDBFile: string, sourceFile: string, epsg: int, mlayerType: string, exportType: string) : 
        if not os.path.exists(terrainDBFile):
            raise FileNotFoundError("terrainDBFile file is not found.")
        if not os.path.exists(sourceFile):
            raise FileExistsError("sourceFile is not found.")
        if os.path.isfile(layerDBFile): #判定layerDBFile是否已存在
            raise os.error("layerDBFile already been existed, please change the file name.")
        terrainDBFile = os.path.abspath(terrainDBFile)
        layerDBFile = os.path.abspath(layerDBFile)
        
        mlayerTypeStr = mlayerType.upper()
        if (mlayerTypeStr != "PIPELINE") and (mlayerTypeStr != "MANHOLE") and (mlayerTypeStr != "EQUIPMENT"): #判定Layer是否正確
            raise ValueError("mlayerType is incorrect. You should enter 'PIPELINE' or 'MANHOLE' or 'EQUIPMENT'. ")
        exportTypeStr = exportType.upper()
        if (exportTypeStr != "NORMAL") and (exportTypeStr != "I3S") and (exportTypeStr != "3DTILES"): #判定輸出檔案名是否正確
            raise ValueError("exportType is incorrect. You should enter 'NORMAL' or 'I3S' or '3DTILES'. ")
        
        param = VarStruct()
        param.Set("layerName", layerName)
        param.Set("layerDBFile", layerDBFile)
        param.Set("terrainName", terrainName)
        param.Set("terrainDBFile", terrainDBFile)
        param.Set("sourceFile", sourceFile)
        param.Set("epsg", epsg)
        param.Set("mlayerTypeStr", mlayerTypeStr)
        param.Set("exportTypeStr", exportTypeStr)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvertPipeline", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["id"]
   
    def convertPointcloud(self, layerName: string, layerDBFile: string, pointcloudFileNames: string, terrainName: string, terrainDBFile: string, sourceEPSG: int, exportType: string) :
        if not os.path.exists(terrainDBFile):
            raise FileNotFoundError("terrainDBFile file is not found.")
        if not os.path.exists(pointcloudFileNames):
            raise FileExistsError("pointcloudFileNames is not found.")
        if os.path.isfile(layerDBFile): #判定layerDBFile是否已存在
            raise os.error("layerDBFile already been existed, please change the file name.")
        terrainDBFile = os.path.abspath(terrainDBFile)
        layerDBFile = os.path.abspath(layerDBFile)
        
        exportTypeStr = exportType.upper()
        if (exportTypeStr != "NORMAL") and (exportTypeStr != "I3S") and (exportTypeStr != "3DTILES"): #判定輸出檔案名是否正確
            raise ValueError("exportType is incorrect. You should enter 'NORMAL' or 'I3S' or '3DTILES'. ")
        
        param = VarStruct()
        param.Set("layerName", layerName)
        param.Set("layerDBFile", layerDBFile)
        param.Set("pointcloudFileNames", pointcloudFileNames)
        param.Set("terrainName", terrainName)
        param.Set("terrainDBFile", terrainDBFile)
        param.Set("sourceEPSG", sourceEPSG)
        param.Set("exportTypeStr", exportTypeStr)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvertPointcloud", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["id"]
       
    def hugeModelToModelLayer(self, dbPath: string, layerName: string, terrainDBFile: string, terrainName: string, sourceFileName: string, exportType: string):
        if not os.path.exists(terrainDBFile):
            raise FileNotFoundError("terrainDBFile file is not found.")
        terrainDBFile = os.path.abspath(terrainDBFile)
        if not os.path.exists(sourceFileName):
            raise FileExistsError("source file is not found.")
        sourceFileName = os.path.abspath(sourceFileName)
        if os.path.isfile(dbPath): #判定layerDBFile是否已存在
            raise os.error("dbPath already been existed, please change the file name.")
        dbPath = os.path.abspath(dbPath)
        
        exportTypeStr = exportType.upper()
        if (exportTypeStr != "NORMAL") and (exportTypeStr != "I3S") and (exportTypeStr != "3DTILES"): #判定輸出檔案名是否正確
            raise ValueError("exportType is incorrect. You should enter 'NORMAL' or 'I3S' or '3DTILES'. ")
        
        param = VarStruct()
        param.Set("dbPath", dbPath)
        param.Set("layerName", layerName)
        param.Set("terrainDBFile", terrainDBFile)
        param.Set("terrainName", terrainName)
        param.Set("sourceFileName", sourceFileName)
        param.Set("exportTypeStr", exportTypeStr)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvertModel", param, ret,)
        )
        docmdThread.start()
        docmdThread.join()
        return ret["id"]
    
    def shpToModelSet(self, layerName: string, layerDBFile: string, terrainName: string, terrainDBFile: string, sourceFileName: string, heightField: string, epsg: number, exportType: string):
        if not os.path.exists(terrainDBFile):
            raise FileNotFoundError("terrainDBFile file is not found.")
        terrainDBFile = os.path.abspath(terrainDBFile)
        if not os.path.exists(sourceFileName):
            raise FileExistsError("source file is not found.")
        sourceFileName = os.path.abspath(sourceFileName)
        layerDBFile = os.path.abspath(layerDBFile)
        
        exportTypeStr = exportType.upper()
        if (exportTypeStr != "NORMAL") and (exportTypeStr != "I3S") and (exportTypeStr != "3DTILES"):
            raise ValueError("exportType is incorrect. You should enter 'NORMAL' or 'I3S' or '3DTILES'. ")
                
        param = VarStruct()
        param.Set("sourceType", "shp")
        param.Set("layerName", layerName)
        param.Set("layerDBFile", layerDBFile)
        param.Set("terrainName", terrainName)
        param.Set("terrainDBFile", terrainDBFile)
        param.Set("sourceFileName", sourceFileName)
        param.Set("heightField", heightField)
        param.Set("epsg", epsg)
        param.Set("exportTypeStr", exportTypeStr)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvertModelSet", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["id"]

    def convertTerrain(self, layerName: string, layerDBFile: string, demFileNames: string, demEPSGs: string, exportBoundary: GeoBoundary = GeoBoundary(), isEllipsoid: bool = False, isHighResolutionPriority: bool = True):
        param = VarStruct()
        demFileNamesArr = demFileNames.split(",")
        demFileNames = ""
        for file in demFileNamesArr:
            if not os.path.exists(file):
                raise FileNotFoundError("Input file is not found.")
            demFileNames = demFileNames + os.path.abspath(file) + ","
        demFileNames = demFileNames[:-1]  
        layerDBFile = os.path.abspath(layerDBFile) 
        param.Set("layerName", layerName)
        param.Set("layerDBFile", layerDBFile)
        param.Set("demFileNames", demFileNames)
        param.Set("demEPSGs", demEPSGs)
        param.Set("exportBoundary", exportBoundary)
        param.Set("isEllipsoid", isEllipsoid)
        param.Set("isHighResolutionPriority", isHighResolutionPriority)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvertTerrain", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["id"]
        
    def getConvert3dProgress(self, id):
        param = VarStruct()
        param.Set("id", id)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvert_GetProgress", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["Progress"]
    
    def getConvert3dIsCompleted(self, id):
        param = VarStruct()
        param.Set("id", id)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvertIsCompleted", param, ret))
        docmdThread.start()
        docmdThread.join()
        return ret["isCompleted"]
            
    def getConvert3dProgressToFinish(self, id):
        progressLast = 0
        with Bar('Loading', fill='#', suffix='%(percent).1f%% - %(eta)ds') as bar:
            progress = self.getConvert3dProgress(id)
            while(progress < 100):
                time.sleep(0.5) #避免多次呼叫
                progressForward = progress - progressLast
                bar.next(progressForward)
                progressLast = progress
                progress = self.getConvert3dProgress(id)
                
            progressForward = progress - progressLast
            bar.next(progressForward)
            print("\nConvert 3D Progress Done!")
            
    def getConvert3dData(self, id):
        param = VarStruct()
        param.Set("id", id)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncConvert_GetData", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["Data"]
    
    def save3dToServer(self, dbLayerName: string, layerName: string, layerType: string, id="", dbUrl=""):
        param = VarStruct()
        if os.path.exists(dbUrl):
            dbUrl = os.path.abspath(dbUrl)
        param.Set("dbLayerName", dbLayerName)
        param.Set("layerName", layerName)
        param.Set("layerType", layerType)
        param.Set("id", id)
        param.Set("dbUrl", dbUrl)
        
        ret = VarStruct()
        docmdThread =  threading.Thread(
            target=self.DoCommand, args=("MapServer3DUpload", param, ret,))
        docmdThread.start()
        docmdThread.join()
        print("Save 3D to server Done!\n")
        return

    def tifToDem(self, inputTifFile: string, outputDemFile: string="defaultDEM.dem"):
        if not os.path.exists(inputTifFile):
            raise FileNotFoundError("Input file is not found.")
        inputTifFile = os.path.abspath(inputTifFile)
        outputDemFile = os.path.abspath(outputDemFile)
        param = VarStruct()
        param.Set("inputTifFile", inputTifFile)
        param.Set("outputDemFile", outputDemFile)
        ret = VarStruct()
        docmdThread = threading.Thread(
            target=self.DoCommand, args=("SyncTifToDem", param, ret,))
        docmdThread.start()
        docmdThread.join()
        return ret["id"]
    

    

