# visualize cross section perpendicular to the centerline
# - two STL models
# - slice plane at each centerline point
# - fixed camera loaded from a .pvsm
# - show slice surfaces + boundary edges + red circle (NumPy+VTK)
from paraview.simple import *
import numpy as np
import csv, os, sys
import xml.etree.ElementTree as ET

# VTK imports
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkCommonCore import vtkPoints, vtkIdList
from vtkmodules.vtkCommonDataModel import vtkCellArray
from paraview.simple import TrivialProducer

# ---------- utils ----------
def get_script_dir():
    if '__file__' in globals():
        return os.path.dirname(os.path.abspath(__file__))
    if sys.argv and sys.argv[0]:
        try:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
        except Exception:
            pass
    return os.getcwd()

def read_camera_from_pvsm(pvsm_path):
    tree = ET.parse(pvsm_path); root = tree.getroot()
    def v3(prop):
        if prop is None: return None
        vals = prop.get('values')
        if vals: return [float(x) for x in vals.split()[:3]]
        els = prop.findall(".//Element")
        return [float(els[i].get('value')) for i in range(3)] if len(els) >= 3 else None
    def sc(prop):
        if prop is None: return None
        vals = prop.get('values')
        if vals: return float(vals.split()[0])
        el = prop.find(".//Element"); return float(el.get('value')) if el is not None else None
    pos = v3(root.find(".//Property[@name='CameraPosition']"))
    fp  = v3(root.find(".//Property[@name='CameraFocalPoint']"))
    up  = v3(root.find(".//Property[@name='CameraViewUp']"))
    ps  = sc(root.find(".//Property[@name='CameraParallelScale']"))
    if any(x is None for x in (pos, fp, up, ps)):
        raise RuntimeError("Could not read camera from pvsm.")
    return {"pos": pos, "fp": fp, "up": up, "pscale": ps}

def make_circle_polyline(center, normal, radius=1.0, npts=128):
    """任意中心・法線の円を vtkPolyData で生成して ParaView に渡す"""
    theta = np.linspace(0, 2*np.pi, npts, endpoint=True)
    pts = np.stack([np.cos(theta), np.sin(theta), np.zeros_like(theta)], axis=1) * radius

    # Z軸→normal の回転行列
    normal = np.array(normal)/np.linalg.norm(normal)
    z = np.array([0,0,1.0])
    v = np.cross(z, normal)
    c = np.dot(z, normal)
    if np.linalg.norm(v) < 1e-8:
        R = np.eye(3)
    else:
        vx = np.array([[0,-v[2],v[1]], [v[2],0,-v[0]], [-v[1],v[0],0]])
        R = np.eye(3) + vx + vx@vx*((1-c)/(np.linalg.norm(v)**2))

    pts = pts @ R.T + np.array(center)

    # VTK PolyData
    vtk_pts = vtkPoints()
    for p in pts: vtk_pts.InsertNextPoint(p.tolist())

    lines = vtkCellArray()
    idlist = vtkIdList()
    for i in range(len(pts)):
        idlist.InsertNextId(i)
    idlist.InsertNextId(0)  # 閉じる
    lines.InsertNextCell(idlist)

    poly = vtkPolyData()
    poly.SetPoints(vtk_pts)
    poly.SetLines(lines)

    src = TrivialProducer()
    src.GetClientSideObject().SetOutput(poly)
    return src

# ---------- paths ----------
base_dir = get_script_dir()
out_dir  = os.path.join(base_dir, "slices"); os.makedirs(out_dir, exist_ok=True)
stl_file  = os.path.join(base_dir, "input.stl")
stl_file2 = os.path.join(base_dir, "input2.stl")
csv_file  = os.path.join(base_dir, "centerline.csv")
pvsm_file = os.path.join(base_dir, "tmp2.pvsm")

for p, name in [(stl_file,"input.stl"), (stl_file2,"input2.stl"),
                (csv_file,"centerline.csv"), (pvsm_file,"tmp2.pvsm")]:
    if not os.path.isfile(p): raise FileNotFoundError(f"{name} not found: {p}")

# ---------- appearance ----------
BG_OPACITY         = 0.25
SLICE_OPACITY_1    = 0.40
SLICE_OPACITY_2    = 0.40
EDGE_COLOR1        = [1.0, 0.2, 0.1]
EDGE_COLOR2        = [0.1, 0.3, 1.0]
EDGE_WIDTH1        = 3.0
EDGE_WIDTH2        = 3.0
SAVE_EVERY         = 10   #10回に1回画像出力
TUBE_RADIUS_RATIO  = 0.01
CIRCLE_RADIUS_RATIO= 0.20
CIRCLE_LINE_WIDTH  = 4.0

# ---------- readers & view ----------
vessel1 = STLReader(FileNames=[stl_file])
vessel2 = STLReader(FileNames=[stl_file2])

view = GetActiveViewOrCreate('RenderView')
view.UseColorPaletteForBackground = 0
view.Background = [1,1,1]; view.Background2 = [1,1,1]
view.CameraParallelProjection = 1; view.OrientationAxesVisibility = 1

v1d = Show(vessel1, view); v1d.Representation = 'Surface'; v1d.Opacity = BG_OPACITY
v2d = Show(vessel2, view); v2d.Representation = 'Surface'; v2d.Opacity = BG_OPACITY
Render(); view.Update()

# スケール
def ub(b1,b2): return [min(b1[0],b2[0]),max(b1[1],b2[1]),min(b1[2],b2[2]),
                       max(b1[3],b2[3]),min(b1[4],b2[4]),max(b1[5],b2[5])]
b1 = vessel1.GetDataInformation().GetBounds()
b2 = vessel2.GetDataInformation().GetBounds()
B  = ub(b1,b2)
diag = np.linalg.norm([B[1]-B[0], B[3]-B[2], B[5]-B[4]])

# 固定カメラ（pvsmから）
cam = read_camera_from_pvsm(pvsm_file)
view.CameraPosition      = cam["pos"]
view.CameraFocalPoint    = cam["fp"]
view.CameraViewUp        = cam["up"]
view.CameraParallelScale = cam["pscale"]
Render()

# ---------- reusable filters ----------
slice1 = Slice(Input=vessel1); slice1.Triangulatetheslice = 0; slice1.SliceType = 'Plane'; slice1.SliceOffsetValues = [0.0]
slice2 = Slice(Input=vessel2); slice2.Triangulatetheslice = 0; slice2.SliceType = 'Plane'; slice2.SliceOffsetValues = [0.0]

s1_disp = Show(slice1, view); s1_disp.Representation = 'Surface'
s1_disp.DiffuseColor = EDGE_COLOR1; s1_disp.Opacity = SLICE_OPACITY_1
s2_disp = Show(slice2, view); s2_disp.Representation = 'Surface'
s2_disp.DiffuseColor = EDGE_COLOR2; s2_disp.Opacity = SLICE_OPACITY_2

edge1 = FeatureEdges(Input=slice1); edge1.BoundaryEdges = 1; edge1.ManifoldEdges = 0; edge1.NonManifoldEdges = 0; edge1.FeatureEdges = 0
edge2 = FeatureEdges(Input=slice2); edge2.BoundaryEdges = 1; edge2.ManifoldEdges = 0; edge2.NonManifoldEdges = 0; edge2.FeatureEdges = 0
e1_disp = Show(edge1, view); e1_disp.DiffuseColor = EDGE_COLOR1; e1_disp.LineWidth = EDGE_WIDTH1
e2_disp = Show(edge2, view); e2_disp.DiffuseColor = EDGE_COLOR2; e2_disp.LineWidth = EDGE_WIDTH2

# normalLine = Line()
# normalTube = Tube(Input=normalLine); normalTube.NumberofSides = 20
# normalTube.Radius = max(TUBE_RADIUS_RATIO*diag, 1e-6)
# norm_disp = Show(normalTube, view); norm_disp.DiffuseColor = [1,0,0]
normalLine = Line()
norm_disp = Show(normalLine, view)
norm_disp.DiffuseColor = [1,0,0]
norm_disp.LineWidth = 2.0

# ---------- centerline ----------
pts = []
with open(csv_file, 'r') as f:
    rd = csv.reader(f); next(rd)
    for row in rd: pts.append([float(row[0]), float(row[1]), float(row[2])])
if len(pts) < 2: raise RuntimeError("centerline.csv needs at least 2 points.")

def tangent_at(i):
    if i == 0:             v = np.array(pts[1]) - np.array(pts[0])
    elif i == len(pts)-1:  v = np.array(pts[-1]) - np.array(pts[-2])
    else:                  v = np.array(pts[i+1]) - np.array(pts[i-1])
    n = np.linalg.norm(v); return (v/(n+1e-12)).tolist()

arrow_len = 0.15*diag if diag>0 else 100.0

# ---------- main loop ----------
for i in range(len(pts)):
    origin = pts[i]; normal = tangent_at(i)

    # スライス面更新
    slice1.SliceType.Origin = origin; slice1.SliceType.Normal = normal
    slice2.SliceType.Origin = origin; slice2.SliceType.Normal = normal

    # 赤い円を生成
    circle_src = make_circle_polyline(origin, normal, radius=CIRCLE_RADIUS_RATIO*diag)
    circle_disp = Show(circle_src, view)
    circle_disp.DiffuseColor = [1,0,0]; circle_disp.LineWidth = CIRCLE_LINE_WIDTH

    # originの点を赤く表示
    sphere = Sphere()
    sphere.Center = origin
    sphere.Radius = 0.01 * diag   # 点の大きさを調整
    sphere_disp = Show(sphere, view)
    sphere_disp.DiffuseColor = [1,0,0]  # 赤

    # 法線ライン更新
    p1 = (np.array(origin) - np.array(normal)*arrow_len).tolist()
    p2 = (np.array(origin) + np.array(normal)*arrow_len).tolist()
    normalLine.Point1 = p1; normalLine.Point2 = p2

    # --- テキスト表示 ---
    def fmt_vec(vec):
        return "(" + ", ".join(f"{x:.3g}" for x in vec) + ")"
    txt = Text()
    txt.Text = f"Slice {i}\nOrigin: {fmt_vec(origin)}\nNormal: {fmt_vec(normal)}"
    txt_disp = Show(txt, view)
    txt_disp.WindowLocation = 'Upper Left Corner'
    txt_disp.FontSize = 12
    txt_disp.Color = [0.0, 0.0, 0.0]  # 黒文字
    txt_disp.Bold = 1
    txt_disp.FontFamily = 'Arial'

    # カメラ固定
    view.CameraPosition      = cam["pos"]
    view.CameraFocalPoint    = cam["fp"]
    view.CameraViewUp        = cam["up"]
    view.CameraParallelScale = cam["pscale"]

    Render(); view.Update()
    if i % SAVE_EVERY == 0:   # 修正点！
        SaveScreenshot(os.path.join(out_dir, f"view_{i:03d}.png"),
                       view, ImageResolution=[1200, 900], TransparentBackground=0)

    # 後片付け
    Delete(circle_src); del circle_src
    Delete(txt); del txt
    Delete(sphere); del sphere

Render()
