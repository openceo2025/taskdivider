# TaskDivider

## プロジェクト概要
TaskDivider は、Flask と swarm を利用した簡易的な予定管理ツールです。Web 画面からのタスク管理に加え、LLM エージェントによるスケジュール支援を想定しています。SQLite をデータベースとして利用し、各種操作は `agents.py` で定義されています。

## 動作環境
- Python 3.10 以上
- 主要依存パッケージ
  - Flask
  - swarm
  - pytest (テスト用)

## 仮想環境の作成例
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` には上記依存パッケージを記載しています。

## データベース初期化
初回起動時または `db.sqlite` が存在しない場合、`app.py` の `init_db()` により自動的に `schema.sql` を読み込んでテーブルを作成します。手動で初期化したい場合は以下の通りです。

```bash
python -c "import app; app.init_db()"
```

## サーバの起動
```bash
python app.py
```
デフォルトでは `localhost:5001` で起動します。

## テスト実行
```bash
pytest
```

以上です。
