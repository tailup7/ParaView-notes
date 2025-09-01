# ParaView の howto
血管の3Dモデリングと流体解析を進めるうえで、ParaViewで行った可視化やデータ解析の手順のおぼえがき

## 環境
ParaView 5.13.3

## CLI を利用したバッチ処理
単に形状や解析結果の可視化をするだけならGUIを使うのが速いが、データ解析をしたい場合は CLI を利用すると便利。ParaView は pvpython という python 限定 の CLI を提供している。ParaViewをインストールするとセットでインストールされるが、パスは手動で通す必要がある。pvpython.exe は(windowsの場合)以下の場所に入っている。
```
C:/Program Files/ParaView5.13.3/bin/
```
パスを通した後、paraviewライブラリを利用したpythonスクリプトをコマンドラインから実行できるようになる
```
$ pvpython your-method.py
```
GUI上でもEditorを利用でき、下の画像のように "Tool" → "Python Script Editor" → コードを書く → "File" → "Run" で実行できる。
<p align="left">
  <img src="pictures/editor1.png" height="220">
  <img src="pictures/editor2.png" height="220">
</p>

## 断面の可視化と断面積計算 (GUI)
1. 3次元形状をimportする
2. "slice"フィルタで切断したい位置、角度を調整(下図左)し、"Pipeline Browser"から"slice1"のみ表示してそれ以外はチェックを外す。"slice1"の"properties"を開き、"show plane"のチェックを外し、カメラの"Reset"を押して図形位置を画面中心に合わせる(下図右)。
<p align="left">
  <img src="pictures/slice1.png" height="280">
  <img src="pictures/slice2.png" height="280">
</p>
3. "Filters" → "alphabetical" → "Delauny2D" で閉曲線の内部に三角形メッシュを生成する(下図左)。
  "Pipeline Browser"で生成された"Delauny2D1"を選択し、"Filters" → "Alphabetical" → "Cell Size" を押す。
    生成された"CellSize1"を選択し、"Properties" → "Compute Area"のみにチェック入れ、他外す → 各三角形パッチの面積が可視化される(下図右)。
<p align="left">
  <img src="pictures/slice3.png" height="280">
  <img src="pictures/slice4.png" height="280">
</p>
4. "Filters" → "Alphabetical" → "IntegrateVariables" → 開いたspread sheet で "showing" を "IntegrateVariable1", "Attribute" を "Cell Data"  にすると、"Area" のcolumnに総面積が表示される(下図)
<p align="left">
  <img src="pictures/slice5.png" width="60%">
</p>

## 断面の可視化と断面積計算 (CLI)
上記手順は直感的だが、切断面の決め方が決定的でない(一応、GUI上でもslice面の位置、角度共に数値で指定はできる)。また大量処理には向かない。例えば血管の中心線に沿って一定の間隔で垂直断面をとって、全体的な断面形状を知りたいときはCLIを用いる。
