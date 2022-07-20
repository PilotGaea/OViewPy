# PilotGaea O'View Map Server API for Python

使用 PilotGaea O'View Map Server API for Python 在 Python 中處理O'View Map Server發布的地圖和地理空間數據。

這個library可讀取、編輯、分析、上架由O'View Map Server發布之地圖圖像與向量資料，並可透過API操作輸出及發佈處理後的成果。

此library只支援由 O'View Map Server 發佈的圖資，暫不支援外部資料處理。

## 安裝PliotGaea Python Module

```shell
pip install OViewPy
```

## 初始化Server物件

本章節為PliotGaea Python Module的起始點，在執行所有操作前須先初始化Server物件，提供Module取得Map Server資源的相關連線資訊。

```python
from OViewPy.server import Server

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
```

綁定Server物件後，即可取得Server相關資訊。

```python
from OViewPy.server import Server

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 取得目前Server版本
print("OView Map Server Version：",server.version)
# 取得WMTS URL
print("WMTS URL：",server.wmtsURL)
# 取得WMS URL
print("WMS URL：",server.wmsURL)
# 取得DoCommand URL
print("DoCommand URL：",server.docmdURL)
```

### 取得圖層列表

綁定Server物件後，可透過`getLayerList`取得2D圖層列表詳細資訊。<br/>
亦可使用`getOViewLayerList`取得3D圖層列表詳細資訊。

```python
from OViewPy.server import Server

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
layerList = server.getLayerList()
OViewLayerList = server.getOViewLayerList()
for list in layerList:
    print("圖層名稱：",list["layername"],"圖層類別：",list["type"])
print("===========================================")
for list in OViewLayerList:
    print("圖層名稱：",list["layername"],"圖層類別：",list["type"])

```

### 刪除圖層

如果想要刪除Server中已存在的圖層，可透過`deleteLayer`與`deleteOViewLayer`分別刪除2D及3D圖層。
> 注意！此刪除無法復原，請警慎使用。

```python
from OViewPy.server import Server

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
server.deleteLayer(layerName="ne_10m_lakes")
server.deleteOViewLayer(layerName="ModelSet")
```

### 上架圖層

#### 將圖片上架至伺服器

透過`saveImageToServer`可將圖片(JPG、PNG等)上架至Server

> 需特別注意，上架的圖片需在Server端目錄底下，並有相對應的World File，且確認圖層名稱不是已存在的圖層。

| 參數名稱 | Type | 預設值 | 說明 |
| :-----: | :---: | :---: | :--: |
| imageFilePath | string | None | 圖片檔案位置 |
| layerName | string | None | 上架後的圖層名稱 |
| epsg | int | 4326 | 座標參考系統 |

```python
from OViewPy.server import Server
from OViewPy.layer import Layer
from OViewPy.varstruct import GeoBoundary
from OViewPy.da import da

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
layer = Layer(server=server,layerName="Town_MOI")
boundary=GeoBoundary(147522.218692, 2422004.773002,
                         351690.114369, 2813163.248085)
# 取得圖片，取得成功會回傳圖片bytes資料
img = layer.getMapImage(
    boundary=boundary,
    crs="EPSG:3826",
    width=512,
    height=512,
    format="image/png"
)
# 儲存圖片，並生成World File
da.saveImg(
    img=img,
    savePath=".",
    imgName="testImage",
    imgType="png",
    worldFile=True,
    boundary=boundary
)
# 將圖片上架至Server
server.saveImageToServer(
    imageFilePath="D:\\NCHCProject\\jupyter_notebook\\testImage.png",
    layerName="testImage",
    epsg=3826
)
```

#### 將SHP File上架至伺服器

透過`saveVectorFileToServer`可將Shp File上架至Server

> 需特別注意，上架的Shp File需在Server端目錄底下，並確認圖層名稱不是已存在的圖層。

| 參數名稱 | Type | 預設值 | 說明 |
| :-----: | :---: | :---: | :--: |
| VectorFilePath | string | None | Shp File位置 |
| layerName | string | None | 上架後的圖層名稱 |
| epsg | int | 4326 | 座標參考系統 |

```python
from OViewPy.server import Server
from OViewPy.layer import Layer
from OViewPy.varstruct import GeoBoundary
from OViewPy.da import da

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
map = Layer(server=server, layerName="Town_MOI")
# 設定搜尋條件
sql = "County_ID==64"
# 取得向量資料
ret = map.getVectorEmtity(epsg=3826,sql=sql)
# 將向量資料存成SHP檔
da.saveAsShapeFile(sourceGeo=ret["geo"],sourceAttr=ret["attr"],fileName="TestShp_Kh")
# 將SHP檔上架至伺服器
server.saveVectorFileToServer(VectorFilePath="D:\\NCHCProject\\jupyter_notebook\\TestShp_Kh.shp",layerName="TestShp_Kh",epsg=3826)
```

## Layer Module (2D Layer)

### 取得圖層物件

透過此Module，可以取得OView Map Server上發布的影像圖層及向量圖層。<br/>
第一個參數(`server`)放置已綁定的Server物件，第二個參數(`layerName`)放置要取得的圖層名稱。

```python
from OViewPy.server import Server
from OViewPy.layer import Layer

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
layer = Layer(server=server,layerName="Town_MOI")
```

取得圖層物件後，即可透過``getLayerInfo``取得圖層相關資訊。

```python
from OViewPy.server import Server
from OViewPy.layer import Layer

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
layer = Layer(server=server,layerName="Town_MOI")
# 取得圖層資訊
layerInfo = layer.getLayerInfo()
print(layerInfo)
```

透過``getMapImage``可取得給定範圍內的地圖圖片，此Function的參數如下：

| 參數名稱 | Type | 預設值 | 說明 |
| :-----: | :---: | :---: | :--: |
| boundary | GeoBoundary | None | 欲取得圖片範圍。如未給值，將直接取得完整圖片。 |
| width | int | 512 | 圖片寬度 |
| height | int | 512 | 圖片高度 |
| crs | string | EPSG:4326 | 座標參考系統 |
| format | string | image/png | 圖片格式 |

```python
from OViewPy.server import Server
from OViewPy.layer import Layer
from OViewPy.varstruct import GeoBoundary
from OViewPy.da import da

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
layer = Layer(server=server,layerName="Town_MOI")
# 取得圖片，取得成功會回傳圖片bytes資料
img = layer.getMapImage(
    boundary=GeoBoundary(147522.218692, 2422004.773002,
                         351690.114369, 2813163.248085),
    crs="EPSG:3826",
    width=512,
    height=512,
    format="image/png"
)
# 顯示圖片
da.showImg(img)
```

如果圖層格式為`向量圖層`，可透過`getVectorEmtity`取得一定範圍內的向量資料。<br/>
此Function的參數如下：

| 參數名稱 | Type | 預設值 | 說明 |
| :-----: | :---: | :---: | :--: |
| bound | GeoBoundary/GeoPolygon | None | 欲取得向量資料範圍。如未給值，將直接取得完整圖層向量資料。 |
| epsg | int | 4326 | 座標參考系統 |
| sql | strong | "" | 搜尋條件 |

```python
from OViewPy.server import Server
from OViewPy.layer import Layer
from OViewPy.varstruct import GeoBoundary

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
map = Layer(server=server, layerName="Town_MOI")
# 設定搜尋條件
sql = "County_ID=64"
# 取得向量資料
ret = map.getVectorEmtity(epsg=3826,sql=sql)
print("Geo：", ret["geo"][0].ToDict())
print("Attr：", ret["attr"][0].ToDict())
```

## Data Access Module

### 使用資料處理模組

此模組可將取得的資料轉換成Python常用的Numpy、Shapely等資料格式，以供開發者方便計算。

#### 圖片(Bytes)與Numpy Array轉換

```python
from OViewPy.server import Server
from OViewPy.layer import Layer
from OViewPy.varstruct import GeoBoundary
from OViewPy.da import da
import cv2

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
layer = Layer(server=server,layerName="Town_MOI")
# 取得圖片，取得成功會回傳圖片bytes資料
img = layer.getMapImage(
    boundary=GeoBoundary(147522.218692, 2422004.773002,
                         351690.114369, 2813163.248085),
    crs="EPSG:3826",
    width=512,
    height=512,
    format="image/png"
)
# 將圖片轉換成Numpy Array
npArray = da.imgToNumPyArray(img)
# 透過cv2讀取Numpy Array
image = cv2.imdecode(npArray, cv2.IMREAD_UNCHANGED)
# 處理成高斯模糊
blurred = cv2.GaussianBlur(image, (51, 51), 0)
# 將處理後的圖片轉成jpg編碼
blurred = cv2.imencode('.jpg',blurred)[1]
# 將Numpy Array 轉回 Bytes格式
blurred = da.numPyArrayToImg(blurred)
# 顯示圖片
da.showImg(blurred)
# 儲存圖片
da.saveImg(img=blurred, savePath=".", imgName="高斯模糊", imgType="jpg")
```

#### 向量格式轉換成Numpy Array

```python
from OViewPy.server import Server
from OViewPy.layer import Layer
from OViewPy.varstruct import GeoBoundary
from OViewPy.da import da

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
map = Layer(server=server, layerName="Town_MOI")
# 設定範圍
geo = GeoBoundary(147522.218692, 2422004.773002,
                  351690.114369, 2813163.248085)
# 取得向量資料
ret = map.getVectorEmtity(bound=geo,epsg=3826)
# 將向量資料轉換成Numpy
npRet = da.vectorEmtityToNumPyArray(ret["geo"])
# 顯示資料類型
print(type(npRet[0]))
```

#### 向量格式轉換成Shapely

```python
from OViewPy.server import Server
from OViewPy.layer import Layer
from OViewPy.varstruct import GeoBoundary

# 綁定Server物件
server = Server(url="http://127.0.0.1:8080")
# 綁定Layer物件
map = Layer(server=server,layerName="Town_MOI")
# 設定範圍
geo = GeoBoundary(147522.218692, 2422004.773002,
                  351690.114369, 2813163.248085)
# 取得向量資料
ret = map.getVectorEmtity(bound=geo)
# 將向量資料轉換成Numpy
shpRet = da.vectorEmtityToShapely(ret["geo"])
# 顯示資料類型
print(type(shpRet[0]))
```