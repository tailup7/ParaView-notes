# 中心線と表面を読み込み、中心線のねじれや曲がりに合わせてコード内で指定された表面点を通って表面上を走る1本の点群を作成するpythonコード。
# 読み込む中心線(*.csv) はINLET → OUTLET の方向順に並んでいること。

import numpy as np
import tkinter as tk
from tkinter import filedialog
import pandas as pd
from stl import mesh

ref_point = np.array([0.099477, 0.27603, 0.11014])

class NodeCenterline:
    def __init__(self,id,x,y,z):
        self.id = id
        self.x = x
        self.y = y
        self.z = z

class NodeSurface:
    def __init__(self,id,x,y,z):
        self.id = id
        self.x = x
        self.y = y
        self.z = z
        self.closest_centerlinenode_id = None

    def find_closest_centerlinenode(self,nodes_centerline):
        min_distance_square = float("inf")
        for node_centerline in nodes_centerline:
            distance_square = (self.x-node_centerline.x)**2 + (self.y-node_centerline.y)**2 + (self.z-node_centerline.z)**2
            if distance_square < min_distance_square:
                min_distance_square = distance_square
                self.closest_centerlinenode_id = node_centerline.id
                # self.closest_centerlinenode_distance = np.sqrt(min_distance_square)  # 使わなさそうなら後で消す

# 絶対パスの取得
def select_csv_centerline():
    root = tk.Tk()
    root.withdraw() 
    root.attributes("-topmost", True)
    filepath  = filedialog.askopenfilename(
        title     = f"Select centerline file (*.csv)",
        filetypes = [("CSV files", "*.csv")], 
        parent    = root
    )
    root.destroy()
    return filepath

#絶対パスの取得
def select_stl():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  
    filepath = filedialog.askopenfilename(
        title     = "Select surface file",
        filetypes = [("stl files", "*.stl")],  
        parent    = root
    )
    root.destroy()
    return filepath

# インデックスは0スタート
def read_csv_centerline(filepath):
    df = pd.read_csv(filepath)
    nodes_centerline = [NodeCenterline(index, row['x'], row['y'], row['z']) for index, row in df.iterrows()]
    return nodes_centerline

def write_csv_surfaceline(vectors, filepath):
    df = pd.DataFrame(vectors, columns=["x", "y", "z"])
    df.to_csv(filepath, index=False)

def nodeinstance_to_vector(node):
    return np.array([node.x, node.y, node.z])

def unitvector(vector):
    return vector / np.linalg.norm(vector)


def rotation_matrix_from_a_to_b(a, b):
    """
    単位ベクトル a を単位ベクトル b に回す回転行列を返す。 つまり、R @ a = b となる。
    """
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    # 特殊ケース処理
    if np.isclose(s, 0):  
        if c > 0:  
            return np.eye(3)  # a と b が同じ向き → 恒等行列
        else:  
            # 逆向き (180度回転) → a に直交する任意の軸で180°回転
            # 例えば a と直交する標準基底を取る
            axis = np.zeros(3)
            axis[np.argmin(np.abs(a))] = 1.0
            v = np.cross(a, axis)
            v /= np.linalg.norm(v)
            K = np.array([[0, -v[2], v[1]],[v[2], 0, -v[0]],[-v[1], v[0], 0]])
            return np.eye(3) + 2 * K @ K  # 180°回転
    # Rodrigues の回転公式
    K = np.array([[0, -v[2], v[1]],[v[2], 0, -v[0]],[-v[1], v[0], 0]])
    R = np.eye(3) + K + K @ K * ((1 - c) / (s**2))
    return R

def find_closest_centerlinenode(ref_point, nodes_centerline):
    min_distance_square = float("inf")
    for node_centerline in nodes_centerline:
        distance_square = (ref_point[0] - node_centerline.x)**2 + (ref_point[1]-node_centerline.y)**2 + (ref_point[2] - node_centerline.z)**2
        if distance_square < min_distance_square:
            min_distance_square = distance_square
            closest_centerlinenode_id = node_centerline.id
    return closest_centerlinenode_id

# 引数は、NodeCenterlineクラスインスタンス, 及び、表面上の点(np.array型)
def calc_radius_direction_unitvector(closest_centerlinenode, point_surface):
    closest_centerlinenode_pvec = nodeinstance_to_vector(closest_centerlinenode)
    radius_direction_vector = point_surface - closest_centerlinenode_pvec
    radius_direction_unitvector = radius_direction_vector / np.linalg.norm(radius_direction_vector)
    return radius_direction_unitvector

# 反時計回りに90°方向の単位方向ベクトルを計算する。さらにその後、時計回りに90°方向(元の方向) の単位方向ベクトルを計算する
def calc_0and90unitvec(centerlinenode_prevto_closest_centerlinenode, closest_centerlinenode, ref_point):
    closest_centerlinenode_pvec = nodeinstance_to_vector(closest_centerlinenode)
    centerlinenode_nextto_closest_centerlinenode_pvec = nodeinstance_to_vector(centerlinenode_prevto_closest_centerlinenode)
    centerlinevector_OUTLET_INLET = centerlinenode_nextto_closest_centerlinenode_pvec - closest_centerlinenode_pvec
    crossvector = np.cross(centerlinevector_OUTLET_INLET, ref_point - closest_centerlinenode_pvec)
    unitcrossvector = crossvector / np.linalg.norm(crossvector)
    originalvector = np.cross(unitcrossvector, centerlinevector_OUTLET_INLET)
    unitoriginalvector = originalvector / np.linalg.norm(originalvector)
    return unitcrossvector, unitoriginalvector


def ray_triangle_intersect(orig, direction, v0, v1, v2, eps=1e-9):
    """
    Möller - Trumbore algorithm for ray-triangle intersection.
    Returns (t, intersection_point) or None if no intersection.
    """
    edge1 = v1 - v0
    edge2 = v2 - v0
    h = np.cross(direction, edge2)
    a = np.dot(edge1, h)
    if -eps < a < eps:
        return None  # レイは三角形と平行
    f = 1.0 / a
    s = orig - v0
    u = f * np.dot(s, h)
    if u < 0.0 or u > 1.0:
        return None
    q = np.cross(s, edge1)
    v = f * np.dot(direction, q)
    if v < 0.0 or u + v > 1.0:
        return None
    t = f * np.dot(edge2, q)
    if t > eps:  # レイと交差
        intersection = orig + direction * t
        return t, intersection
    else:
        return None  # 三角形の裏側 or 始点の前

def find_ray_mesh_intersection(stl_file, ray_origin, ray_direction):
    your_mesh = mesh.Mesh.from_file(stl_file)
    ray_direction = ray_direction / np.linalg.norm(ray_direction)  # 正規化
    closest_t = float("inf")
    closest_point = None
    for tri in your_mesh.vectors:
        v0, v1, v2 = tri
        result = ray_triangle_intersect(ray_origin, ray_direction, v0, v1, v2)
        if result is not None:
            t, point = result
            if t < closest_t:
                closest_t = t
                closest_point = point
    return closest_point

if __name__ == "__main__":
    surface_line_0  = []
    surface_line_90 = []
    filepath_centerline = select_csv_centerline()
    filepath_stl = select_stl()
    nodes_centerline = read_csv_centerline(filepath_centerline)
    closest_centerlinenode_id = find_closest_centerlinenode(ref_point, nodes_centerline)
    current_id = closest_centerlinenode_id
    direcvector90, direcvector0 = calc_0and90unitvec(nodes_centerline[closest_centerlinenode_id-1], nodes_centerline[closest_centerlinenode_id], ref_point)
    point_on_surface_line_0 = find_ray_mesh_intersection(filepath_stl, nodeinstance_to_vector(nodes_centerline[closest_centerlinenode_id]), direcvector0)
    point_on_surface_line_90 = find_ray_mesh_intersection(filepath_stl, nodeinstance_to_vector(nodes_centerline[closest_centerlinenode_id]), direcvector90)
    surface_line_0.append(point_on_surface_line_0)
    surface_line_90.append(point_on_surface_line_90)

    # INLET方向に表面上の線を走査する 
    #
    #  INLET 側 (ノード番号小さい)
    #   
    #         \
    #          ・
    #           \       中心線 Node と Edge
    #            \      ↓
    #             \
    #              ・ー ー ー ・ ー
    #              ↑          ↑ 
    #    次にここの           自分
    #    半径方向ベクトルを  
    #    生成したい                       OUTLET 側 (ノード番号大きい)
    #   
    #    自分が所属するEdge + さらに1つ前のEdge 
    #    が存在すれば、その2つから回転量を計算して、自分の半径方向ベクトルに作用させて、
    #    次のNodeの半径方向ベクトルを生成する

    # 端面付近は三角形パッチとぶつからずに point_on_surface_line_0, 90 がNone　になる可能性が高いので、計算しない
    while current_id >= 2:
        centerlinevector_OUTLET_INLET_this = unitvector(nodeinstance_to_vector(nodes_centerline[current_id-1]) - nodeinstance_to_vector(nodes_centerline[current_id]))
        centerlinevector_OUTLET_INLET_prev = unitvector(nodeinstance_to_vector(nodes_centerline[current_id-2]) - nodeinstance_to_vector(nodes_centerline[current_id-1]))
        R = rotation_matrix_from_a_to_b(centerlinevector_OUTLET_INLET_this, centerlinevector_OUTLET_INLET_prev) 
        direcvector0 = R @ direcvector0
        direcvector90 = R @ direcvector90
        point_on_surface_line_0  = find_ray_mesh_intersection(filepath_stl, nodeinstance_to_vector(nodes_centerline[current_id-1]), direcvector0)
        point_on_surface_line_90 = find_ray_mesh_intersection(filepath_stl, nodeinstance_to_vector(nodes_centerline[current_id-1]), direcvector90)
        surface_line_0.insert(0, point_on_surface_line_0)
        surface_line_90.insert(0, point_on_surface_line_90)
        current_id -= 1

    # OUTLET方向に表面上の線を走査する
    #
    #  INLET 側 (ノード番号小さい)
    #                \
    #                 ・             次にここの半径方向ベクトルを
    #                  \              生成したい 
    #                   \              ↓
    #                    ・ー ー ー ー ・ 
    #                    ↑              \
    #                   自分             \              ← 中心線 Node と Edge
    #                                     \
    #                                      ・
    #                                       \
    #                    
    #                                    OUTLET 側 (ノード番号大きい)
    #   
    #    自分が所属するEdge + さらに1つ次のEdge 
    #    が存在すれば、その2つから回転量を計算して、自分の半径方向ベクトルに作用させて、
    #    次のNodeの半径方向ベクトルを生成する

    current_id = closest_centerlinenode_id
    direcvector90, direcvector0 = calc_0and90unitvec(nodes_centerline[closest_centerlinenode_id-1], nodes_centerline[closest_centerlinenode_id], ref_point)
    # 端面付近は三角形パッチとぶつからずに point_on_surface_line_0, 90 がNone　になる可能性が高いので、計算しない
    while current_id <= len(nodes_centerline)-3:
        centerlinevector_INLET_OUTLET_this = unitvector(nodeinstance_to_vector(nodes_centerline[current_id+1]) - nodeinstance_to_vector(nodes_centerline[current_id]))
        centerlinevector_INLET_OUTLET_next = unitvector(nodeinstance_to_vector(nodes_centerline[current_id+2]) - nodeinstance_to_vector(nodes_centerline[current_id+1]))
        R = rotation_matrix_from_a_to_b(centerlinevector_INLET_OUTLET_this, centerlinevector_INLET_OUTLET_next) 
        direcvector0 = R @ direcvector0
        direcvector90 = R @ direcvector90
        point_on_surface_line_0  = find_ray_mesh_intersection(filepath_stl, nodeinstance_to_vector(nodes_centerline[current_id+1]), direcvector0)
        point_on_surface_line_90 = find_ray_mesh_intersection(filepath_stl, nodeinstance_to_vector(nodes_centerline[current_id+1]), direcvector90)
        surface_line_0.append(point_on_surface_line_0)
        surface_line_90.append(point_on_surface_line_90)
        current_id += 1

    write_csv_surfaceline(surface_line_0, "surfaceline0.csv")
    write_csv_surfaceline(surface_line_90, "surfaceline90.csv")
    