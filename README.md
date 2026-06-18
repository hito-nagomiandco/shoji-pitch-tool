# 障子ピッチツール Streamlit版

1枚の障子小パネル用のスマホWebツールです。

## 起動方法

```bash
pip install -r requirements.txt
streamlit run app.py
```

ブラウザで `http://localhost:8501` が開きます。

## ファイル構成

- app.py: スマホ向けWeb画面
- shoji_panel_calculator.py: 計算・PNG生成エンジン
- requirements.txt: 必要ライブラリ

## 入力できるもの

- パネル有効幅
- パネル有効高さ
- 組子幅
- 組子厚み
- 組子本数
- 変化率
- 曲線タイプ
- 密になる方向
