from abc import ABC, abstractmethod
import copy
from enum import Enum
import math
import json
from pickle import FALSE

class LAYER_TYPE(Enum):
    NONE = 0,
    SET = 1,
    MERGE = 2,
    VECTOR_BASE = 32,
    VECTOR_ORACLE = 33,
    VECTOR_SQLSERVER = 34,
    VECTOR_POSTGRESQL = 35,
    RASTER_BASE = 64,
    RASTER_WMS = 65,
    RASTER_WMTS = 66,
    RASTER_DWG = 67,
    CUSTOM = 96,
    TERRAIN_BASE = 128,
    OV_TERRAIN = 256,
    OV_PHOTOGRAMMETRYMODEL = 257,
    OV_PIPELINE = 258,
    OV_TILEMAP = 259,
    OV_WMS = 260,
    OV_MESH = 261,
    OV_VECTOR = 262,
    OV_LIDAR = 263,
    OV_MESHPOINTS = 264,
    OV_MULTIWATER = 265,
    OV_CITYMESH = 266,
    OV_OGCI3S = 267,
    OV_MODEL = 268,
    OV_MODELSET = 269,
    OV_SENSORTHINGS = 270,
    OV_POINTCLOUD = 271,
    OV_STREETVIEW = 272,
    OV_SCENE = 273,
    OV_PROJECTOR = 274

class GEO_STATUS(Enum):
    LEFT = 1
    RIGHT = 2
    BEYOND = 3
    BEHIND = 4
    BETWEEN = 5
    ORIGIN = 6
    DESTINATION = 7
    COLLINEAR = 8
    PARALLEL = 9
    SKEW = 10
    SKEW_CROSS = 11
    SKEW_NO_CROSS = 12


class GeoUtility:
    ErrorRange = 0.00001

    @staticmethod
    def DotProductXY(p1x, p1y, p2x, p2y):
        return p1x*p2x+p1y*p2y


class VarValue(ABC):
    @abstractmethod
    def ToJsonDict(self, includeZ=False):
        pass

    def ToJson(self):
        return json.dumps(self.ToJsonDict())


class GeoPoint(VarValue):
    def __init__(self, x=.0, y=.0, z=.0):
        super().__init__()
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other):
        return GeoPoint(self.x+other.x, self.y+other.y)

    def __sub__(self, other):
        return GeoPoint(self.x-other.x, self.y-other.y)

    def __mul__(self, scale):
        return GeoPoint(self.x*scale, self.y*scale)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeoPoint):
            return False
        return abs(self.x-other.x) <= GeoUtility.ErrorRange and abs(self.y-other.y) <= GeoUtility.ErrorRange

    @property
    def Length(self):
        return math.sqrt(self.x*self.x+self.y*self.y)

    @property
    def PolarAngel(self):
        if self.x == 0 and self.y == 0:
            return -1.0
        if self.x == 0:
            if self.y > 0:
                return 90.0
            else:
                return 270.0
        theta = math.atan(self.y/self.x)
        theta *= 360/(2*math.pi)
        if self.x > 0.0:
            if self.y >= 0.0:
                return theta
            else:
                return 360.0+theta
        else:
            return 180+theta

    def Distance(self, p):
        return math.sqrt(math.pow(p.x-self.x, 2)+math.pow(p.y-self.y, 2))

    def CopyFrom(self, point):
        self.x = point.x
        self.y = point.y
        self.z = point.z
        return self

    def ToJsonDict(self, includeZ=False):
        ret = {}
        if includeZ:
            ret["type"] = "Point Z"
        else:
            ret["type"] = "Point"
        ret["coordinates"] = CoordinatesConverter.FromGeoPoint(self, includeZ)
        return ret

    def FromJson(self, jsonStr):
        obj = json.loads(jsonStr)
        if("type" in obj and "coordinates" in obj):
            self.CopyFrom(CoordinatesConverter.ToGeoType(
                obj["type"], obj["coordinates"]))
            return self
        else:
            return None


class GeoLine:
    class StatusObj:
        Status = GEO_STATUS.SKEW_CROSS

    class T:
        t = 0

    def __init__(self, fromPoint=GeoPoint(), toPoint=GeoPoint()) -> None:
        self.From = fromPoint
        self.To = toPoint

    def __OnSegment(self, p, q, r):
        if(
            q.x <= max(p.x, r.x) and q.x >= min(p.x, r.x) and
            q.y <= max(p.y, r.y) and q.y >= min(p.y, r.y)
        ):
            return True
        return False

    def __Orientation(self, p, q, r):
        val = (q.y-p.y)*(r.x-q.x)-(q.x-p.x)*(r.y-q.y)
        if val == 0:
            return 0
        elif val > 0:
            return 1
        else:
            return 2

    def __LineIntersect_Deprecated(self, e, t: T):
        ax = self.From.x
        ay = self.From.y
        bx = self.To.x
        by = self.To.y
        cx = e.From.x
        cy = e.From.y
        dx = e.To.x
        dy = e.To.y

        nx = dy-cy
        ny = cx-dx

        maxValue = max(ax, ay, bx, by, cx, cy, dx, dy)
        maxValue /= 1000000000.0

        denom = GeoUtility.DotProductXY(nx, ny, bx-ax, by-ay)
        if abs(denom) < maxValue:
            x1 = cx
            y1 = cy
            x2 = dx
            y2 = dy
            _a = y2-y1
            _b = -(x2-x1)
            _c = (x2-x1)*y1-(y2-y1)*x1
            dist = abs(_a*ax+_b*ay+_c)/(math.sqrt(_a*_a+_b*_b))
            if dist < maxValue:
                return GEO_STATUS.COLLINEAR
            else:
                status = e.Classify(self.From)
                if(status == GEO_STATUS.LEFT or status == GEO_STATUS.RIGHT):
                    return GEO_STATUS.PARALLEL
                else:
                    return GEO_STATUS.COLLINEAR

    def __Intersect1_Deprecated(self, e, obj: T):
        errorRange = GeoUtility.ErrorRange

        crossType = e.__LineIntersect_Deprecated(self, obj)
        s = obj.t

        if(crossType == GEO_STATUS.COLLINEAR or crossType == GEO_STATUS.PARALLEL):
            obj.t = 0.0
            return crossType

        self.__LineIntersect_Deprecated(e, obj)
        t = obj.t
        s_ErrorRange = errorRange/e.Length
        t_ErrorRange = errorRange/self.Length
        if(s < -s_ErrorRange or s > 1+s_ErrorRange):
            return GEO_STATUS.SKEW_NO_CROSS
        elif(-t_ErrorRange <= t and t <= 1+t_ErrorRange):
            return GEO_STATUS.SKEW_CROSS
        else:
            return GEO_STATUS.SKEW_NO_CROSS

    def __Intersect2_Deprecated(self, e, p: GeoPoint):
        t = GeoLine.T()
        ret = self.__Intersect1_Deprecated(e, t)
        if(ret != GEO_STATUS.COLLINEAR and ret != GEO_STATUS.PARALLEL):
            vx = self.To.x-self.From.x
            vy = self.To.y-self.From.y
            p.x = self.From.x+vx*t.t
            p.y = self.From.y+vy*t.t

    @property
    def Length(self):
        return self.From.Distance(self.To)

    def Classify(self, p):
        p2 = copy.deepcopy(p)
        a = self.To-self.From
        b = p2-self.From
        sa = a.x*b.y-b.x*a.y
        maxValue = max(a.x, a.y, b.x, b.y, p.x, p.y)
        maxValue /= 1000000000.0

        if sa > maxValue:
            return GEO_STATUS.LEFT
        elif sa < -maxValue:
            return GEO_STATUS.RIGHT
        elif a.x*b.x < -maxValue or a.y*b.y < -maxValue:
            return GEO_STATUS.BEHIND
        elif a.Length < b.Length:
            return GEO_STATUS.BEYOND
        elif self.From == p2:
            return GEO_STATUS.ORIGIN
        elif self.To == p2:
            return GEO_STATUS.DESTINATION
        else:
            return GEO_STATUS.BETWEEN

    def Rot(self):
        m = (self.From+self.To)*0.5
        v = self.To-self.From
        n = GeoPoint(v.y, -v.x)

        self.From = m-n*0.5
        self.To = m+n*0.5

    def InterSect0(self, target, p: GeoPoint, statusObj: StatusObj, endPointInclude=True, includeZ=False) -> bool:
        ret = False
        p1 = copy.deepcopy(self.From)
        q1 = copy.deepcopy(self.To)
        p2 = copy.deepcopy(target.From)
        q2 = copy.deepcopy(target.To)

        o1 = self.__Orientation(p1, q1, p2)
        o2 = self.__Orientation(p1, q1, q2)
        o3 = self.__Orientation(p2, q2, p1)
        o4 = self.__Orientation(p2, q2, q1)

        a1 = q1.y-p1.y
        b1 = p1.x-q1.x
        c1 = a1*(p1.x)+b1*(p1.y)

        a2 = q2.y-p2.y
        b2 = p2.x-q2.x
        c2 = a2*(p2.x)+b2*(p2.y)

        determinant = a1*b2-a2*b1
        determinant_tolerance = 0.00000001

        if(o1 != o2 and o3 != o4 and abs(determinant) > determinant_tolerance):
            p.x = (b2*c1-b1*c2)/determinant
            p.y = (a1*c2-a2*c1)/determinant
            statusObj.Status = GEO_STATUS.SKEW_CROSS
            ret = True
        elif(o1 == 0 and self.__OnSegment(p1, p2, q1)):
            p.CopyFrom(p2)
            statusObj.Status = GEO_STATUS.COLLINEAR
            ret = True
        elif(o2 == 0 and self.__OnSegment(p1, q2, q1)):
            p.CopyFrom(q2)
            statusObj.Status = GEO_STATUS.COLLINEAR
        elif(o3 == 0 and self.__OnSegment(p2, p1, q2)):
            p.CopyFrom(p1)
            statusObj.Status = GEO_STATUS.COLLINEAR
        elif(o4 == 0 and self.__OnSegment(p2, q1, q2)):
            p.CopyFrom(q1)
            statusObj.Status = GEO_STATUS.COLLINEAR
        elif(o1 == 0 and o2 == 0 and o3 == 0 and o4 == 0):
            statusObj.Status = GEO_STATUS.COLLINEAR
        elif(determinant == 0):
            statusObj.Status = GEO_STATUS.PARALLEL
        else:
            statusObj.Status = GEO_STATUS.SKEW_NO_CROSS

        if(ret and includeZ):
            z = self.To.z-self.From.z
            dis = self.To.Distance(self.From)
            t = p.Distance(self.From)
            p.z = self.From.z
            if(dis > 0 and t > 0):
                p.z += z*(t/dis)

        if statusObj.Status == GEO_STATUS.SKEW_NO_CROSS:
            statusObj.Status = self.__Intersect2_Deprecated(target, p)
            if(statusObj.Status == GEO_STATUS.SKEW_CROSS):
                ret = True

        if(statusObj.Status == GEO_STATUS.SKEW_CROSS):
            if(not endPointInclude):
                if(p == self.From or p == self.To):
                    statusObj.Status = GEO_STATUS.SKEW_NO_CROSS
                    ret = False
        return ret

    def InterSect1(self, target, tObj: T, includeZ: bool):
        statusObj = GeoLine.StatusObj()
        p = GeoPoint()
        ret = self.InterSect0(target, p, statusObj, True, includeZ)
        tObj.t = 0
        if ret:
            disFT = self.To.Distance(self.From)
            disP = p.Distance(self.From)
            if disFT != 0:
                tObj.t = disP/disFT
        return statusObj.Status

    def InterSect2(self, target, p: GeoPoint, includeZ: bool):
        statusObj = GeoLine.StatusObj()
        self.InterSect0(target, p, statusObj, True, includeZ)
        return statusObj.Status

    def InterSect(self, target, obj, includeZ=False):
        if obj != None:
            if isinstance(obj, GeoPoint):
                return self.InterSect2(target, obj, includeZ)
            elif isinstance(obj, GeoLine.T):
                obj.t = 0
                return self.InterSect1(target, obj, includeZ)
        else:
            return GEO_STATUS.SKEW_CROSS

    def GetNearPoint(self, p: GeoPoint, ret: GeoPoint):
        status = self.Classify(p)
        if(
            status == GEO_STATUS.ORIGIN or
            status == GEO_STATUS.DESTINATION or
            status == GEO_STATUS.BETWEEN
        ):
            ret.CopyFrom(p)
            return 0
        elif status == GEO_STATUS.BEHIND:
            ret.CopyFrom(self.From)
            return self.From.Distance(p)
        elif status == GEO_STATUS.BEYOND:
            ret.CopyFrom(self.To)
            return self.To.Distance(p)
        elif(
            status == GEO_STATUS.LEFT or
            status == GEO_STATUS.RIGHT
        ):
            line = GeoLine(self.From, self.To)
            line.Rot()
            v = line.To-line.From
            line.From = p
            line.To = p+v
            interPoint = GeoPoint()
            self.InterSect(line, interPoint)
            if self.From == interPoint:
                ret.CopyFrom(self.From)
            elif self.To == interPoint:
                ret.CopyFrom(self.To)
            elif (
                (self.From.x-interPoint.x)*(interPoint.x-self.To.x) >= 0 and
                (self.From.y-interPoint.y)*(interPoint.y-self.To.y) >= 0
            ):
                ret.CopyFrom(interPoint)
            else:
                if self.From.Distance(p) < self.To.Distance(p):
                    ret.CopyFrom(self.From)
                else:
                    ret.CopyFrom(self.To)
            return ret.Distance(p)
        else:
            return -1

    def Distance(self, p: GeoPoint):
        return self.GetNearPoint(p, GeoPoint())


class GeoPolyline(VarValue):
    def __init__(self, points=None) -> None:
        super().__init__()
        self.Buffer = []
        if points != None:
            for point in points:
                self.Buffer.append(copy.deepcopy(point))

    def CopyFrom(self, other):
        self.Buffer = copy.deepcopy(other.Buffer)

    def ToJsonDict(self, includeZ=False):
        ret = {}
        if includeZ:
            ret["type"] = "LineString Z"
        else:
            ret["type"] = "LineString"
        ret["coordinates"] = CoordinatesConverter.FromGeoPoints(
            self.Buffer, includeZ, False, False)
        return ret

    def FromJson(self, jsonStr):
        obj = json.loads(jsonStr)
        if("type" in obj and "coordinates" in obj):
            self.CopyFrom(CoordinatesConverter.ToGeoType(
                obj["type"], obj["coordinates"]))
            return self
        else:
            return None


class GeoPolygon(VarValue):
    def __init__(self, points=None) -> None:
        super().__init__()
        self.Buffer = []
        if points != None:
            for point in points:
                self.Buffer.append(copy.deepcopy(point))

    @property
    def Boundary(self):
        ret = GeoBoundary()
        for i in range(0, len(self.Buffer)):
            if i == 0:
                ret.west = ret.east = self.Buffer[i].x
                ret.north = ret.south = self.Buffer[i].y
            else:
                if self.Buffer[i].x < ret.west:
                    ret.west = self.Buffer[i].x
                if self.Buffer[i].y < ret.south:
                    ret.south = self.Buffer[i].y
                if self.Buffer[i].x > ret.east:
                    ret.east = self.Buffer[i].x
                if self.Buffer[i].y > ret.north:
                    ret.north = self.Buffer[i].y
        return ret

    def ToJsonDict(self, includeZ=False):
        ret = {}
        if includeZ:
            ret["type"] = "MultiPolygon Z"
        else:
            ret["type"] = "MultiPolygon"
        coors = []
        bounds = []
        gjpg = []
        for bound in self.Buffer:
            ring = CoordinatesConverter.FromGeoPoint(bound, includeZ)
            gjpg.append(ring)
        coors.append(gjpg)
        bounds.append(coors)
        ret["coordinates"] = bounds
        return ret

    def CopyFrom(self, other):
        self.Buffer = copy.deepcopy(other.Buffer)

    def FromJson(self, jsonStr):
        obj = json.loads(jsonStr)
        if("type" in obj and "coordinates" in obj):
            self.CopyFrom(CoordinatesConverter.ToGeoType(
                obj["type"], obj["coordinates"]))
            return self
        else:
            return None

    def DistanceInBound(self, p: GeoPoint):
        ret = -1.0
        dist = 0.0
        for i in range(0, len(self.Buffer)):
            dist = GeoLine(self.Buffer[i], self.Buffer[(
                i+1) % len(self.Buffer)]).Distance(p)
            if(ret == -1 or dist < ret):
                ret = dist
            if ret == 0:
                break
        return ret

    def __SignedAngle(self, a: GeoPoint, _from: GeoPoint, _to: GeoPoint):
        v = _from-a
        w = _to-a
        va = v.PolarAngel
        wa = w.PolarAngel
        if(va == -1 or wa == -1):
            return 180.0
        x = wa-va
        if(x == 180 or x == -180):
            return 180
        elif x < -180:
            return x+360.0
        elif x > 180:
            return x-360
        else:
            return x

    def PtInPolygon(self, p: GeoPoint, inBound: dict):
        errorRange = GeoUtility.ErrorRange
        if len(self.Buffer) < 3:
            return False
        inBound["inBound"] = False
        if(errorRange > 0 and self.DistanceInBound(p) <= errorRange):
            inBound["inBound"] = False
            return True
        total = 0.0
        for i in range(0, len(self.Buffer)):
            x = self.__SignedAngle(
                p, self.Buffer[i], self.Buffer[(i+1) % len(self.Buffer)])
            if x == 180:
                inBound["inBound"] = False
                return True
            total += x
        return abs(total) > 180

    def Include(self, polygon, bound: bool):
        if not self.Boundary.Include(polygon.Boundary):
            return False
        inBound = {}
        for point in polygon.Buffer:
            if((not self.PtInPolygon(point, inBound)) or ((not bound) and inBound["inBound"])):
                return False
        return True


class GeoPolygonSet(VarValue):
    def __init__(self) -> None:
        super().__init__()
        self.Bounds = []
        self.Holes = []

    def ToJsonDict(self, includeZ=False):
        ret = {}
        if includeZ:
            ret["type"] = "MultiPolygon Z"
        else:
            ret["type"] = "MultiPolygon"
        coors = []
        innerCount = len(self.Holes)
        innerMarks = []
        for i in range(0, innerCount):
            innerMarks.append(False)

        for bound in self.Bounds:
            gjpg = []
            ring = CoordinatesConverter.FromGeoPoints(
                bound.Buffer, includeZ, True, True)
            gjpg.append(ring)
            for i in range(0, len(self.Holes)):
                if innerMarks[i]:
                    continue
                if bound.Include(self.Holes[i], True):
                    innerRing = CoordinatesConverter.FromGeoPoints(
                        self.Holes[i].Buffer, includeZ, False, True)
                    gjpg.append(innerRing)
                    innerMarks[i] = True
            coors.append(gjpg)
        ret["coordinates"] = coors
        return ret

    def CopyFrom(self, other):
        self.Bounds = copy.deepcopy(other.Bounds)
        self.Holes = copy.deepcopy(other.Holes)

    def FromJson(self, jsonStr):
        obj = json.loads(jsonStr)
        if("type" in obj and "coordinates" in obj):
            self.CopyFrom(CoordinatesConverter.ToGeoType(
                obj["type"], obj["coordinates"]))
            return self
        else:
            return None


class GeoBoundary(VarValue):
    def __init__(self, west=.0, south=.0, east=.0, north=.0) -> None:
        super().__init__()
        self.west = west
        self.south = south
        self.east = east
        self.north = north

    def Include(self, boundary):
        west1 = self.west
        east1 = self.east
        north1 = self.north
        south1 = self.south
        west2 = boundary.west
        east2 = boundary.east
        north2 = boundary.north
        south2 = boundary.south
        if west1 > east1:
            west1, east1 = east1, west1
        if north1 > south1:
            north1, south1 = south1, north1
        if west2 > east2:
            west2, east2 = east2, west2
        if north2 > south2:
            north2, south2 = south2, north2
        return west1 <= west2 and east1 >= east2 and north1 <= north2 and south1 >= south2

    def CopyFrom(self, other):
        self.west = other.west
        self.south = other.south
        self.east = other.east
        self.north = other.north

    def ToJsonDict(self, includeZ=False):
        ret = {}
        ret["type"] = "Boundary"
        ret["bbox"] = [self.west, self.south, self.east, self.north]
        return ret

    def FromJson(self, jsonStr):
        obj = json.loads(jsonStr)
        if("type" in obj and "bbox" in obj):
            self.CopyFrom(CoordinatesConverter.ToGeoBoundary(obj["bbox"]))
            return self
        else:
            return None

    def ToGeoPolygon(self) -> GeoPolygon:
        return GeoPolygon(
            points=[
                GeoPoint(self.west, self.south),
                GeoPoint(self.east, self.south),
                GeoPoint(self.east, self.north),
                GeoPoint(self.west, self.north)
            ]
        )


class VarStruct:
    def __init__(self) -> None:
        self.__data = {}
        pass

    def __getitem__(self, key):
        return self.__data[key]

    def __setitem__(self, key, value):
        if(
            isinstance(value, VarValue) or
            not isinstance(value, object) or
            not isinstance(value, set)
        ):
            self.__data[key] = value
        else:
            raise TypeError()

    def __delitem__(self, key):
        del self.__data[key]

    def Set(self, key, value):
        self[key] = value

    def Get(self, key):
        return self[key]

    def ToJson(self, includeZ=False):
        # ensure_ascii=False是為了避免中文亂碼的問題
        return json.dumps(self.__data, ensure_ascii=False, default=lambda obj: obj.ToJsonDict(includeZ))

    def ToDict(self, includeZ=False):
        jsonStr = json.dumps(
            self.__data,  ensure_ascii=False, default=lambda obj: obj.ToJsonDict(includeZ))
        return json.loads(jsonStr)

    def __JsonDeserialize(self, jsonValue):
        ret = None
        if isinstance(jsonValue, dict):
            ret = {}
            if("type" in jsonValue and "coordinates" in jsonValue):
                return CoordinatesConverter.ToGeoType(jsonValue["type"], jsonValue["coordinates"])
            elif("type" in jsonValue and "bbox" in jsonValue):
                return CoordinatesConverter.ToGeoBoundary(jsonValue["bbox"])
            else:
                for key in jsonValue:
                    ret[key] = self.__JsonDeserialize(jsonValue[key])
        elif isinstance(jsonValue, list):
            ret = []
            for ele in jsonValue:
                ret.append(self.__JsonDeserialize(ele))
        else:
            ret = jsonValue
        return ret

    def FromJson(self, jsonStr):
        self.__data.clear()
        jsonObj = json.loads(jsonStr)
        self.__data = self.__JsonDeserialize(jsonObj)


class CoordinatesConverter:
    @staticmethod
    def FromGeoPoint(point, includeZ=False) -> list:
        ret = [point.x, point.y]
        if includeZ:
            ret.append(point.z)
        return ret

    @staticmethod
    def FromGeoPoints(points, includeZ=False, reverse=False, addHead=True) -> list:
        ret = []
        for point in points:
            ret.append(CoordinatesConverter.FromGeoPoint(point, includeZ))
        if addHead:
            ret.append(CoordinatesConverter.FromGeoPoint(points[0], includeZ))
        if reverse:
            ret.reverse()
        return ret

    @staticmethod
    def ToGeoPoint(coordinates, includeZ=False) -> GeoPoint:
        if includeZ:
            return GeoPoint(coordinates[0], coordinates[1], coordinates[2])
        else:
            return GeoPoint(coordinates[0], coordinates[1])

    def ToGeoPoints(coordinates, includeZ=False) -> list:
        points = []
        for value in coordinates:
            points.append(CoordinatesConverter.ToGeoPoint(value, includeZ))
        return points

    @staticmethod
    def ToGeoPolyline(coordinates, includeZ=False) -> GeoPolyline:
        return GeoPolyline(CoordinatesConverter.ToGeoPoints(coordinates, includeZ))

    @staticmethod
    def ToGeoPolygon(coordinates, includeZ=False) -> GeoPolygon:
        points: list = coordinates[0]
        points.reverse()
        points.pop()
        ret = GeoPolygon(CoordinatesConverter.ToGeoPoints(points, includeZ))
        return ret

    @staticmethod
    def ToGeoPolygonSet(coordinates, includeZ=False) -> GeoPolygonSet:
        ret = GeoPolygonSet()
        for polygonList in coordinates:
            for i in range(0, len(polygonList)):
                points: list = polygonList[i]
                if i == 0:
                    points.reverse()
                    bound = GeoPolygon(
                        CoordinatesConverter.ToGeoPoints(points, includeZ))
                    ret.Bounds.append(bound)
                else:
                    hole = GeoPolygon(
                        CoordinatesConverter.ToGeoPoints(points, includeZ))
                    ret.Holes.append(hole)
        return ret

    @staticmethod
    def ToGeoType(type, coordinates) -> VarValue:
        maker = {
            "Point Z": lambda: CoordinatesConverter.ToGeoPoint(coordinates, True),
            "Point": lambda: CoordinatesConverter.ToGeoPoint(coordinates, False),
            "LineString Z": lambda: CoordinatesConverter.ToGeoPolyline(coordinates, True),
            "LineString": lambda: CoordinatesConverter.ToGeoPolyline(coordinates, False),
            "MultiPolygon Z": lambda: CoordinatesConverter.ToGeoPolygonSet(coordinates, True),
            "MultiPolygon": lambda: CoordinatesConverter.ToGeoPolygonSet(coordinates, False),
            "Polygon Z": lambda: CoordinatesConverter.ToGeoPolygon(coordinates, True),
            "Polygon": lambda: CoordinatesConverter.ToGeoPolygon(coordinates, False)
        }
        return maker[type]()

    @staticmethod
    def ToGeoBoundary(bbox) -> VarValue:
        return GeoBoundary(
            bbox[0],
            bbox[1],
            bbox[2],
            bbox[3]
        )
