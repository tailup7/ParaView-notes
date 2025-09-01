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


## 血管断面の可視化と断面積計算
