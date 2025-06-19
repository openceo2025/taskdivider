from flask import Flask, render_template, request, Response, jsonify, g
import os
import json
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# SQLite の DB ファイルパス
DATABASE = os.path.join(os.path.dirname(__file__), 'db.sqlite')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        # 初期化前のテーブル一覧を取得
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables_before = [row["name"] for row in cur.fetchall()]
        logging.debug("DEBUG: init_db 開始前のテーブル一覧: %s", tables_before)
        
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
                logging.debug("DEBUG: schema.sql の内容:\n%s", schema_sql)
                db.executescript(schema_sql)
        except Exception as e:
            logging.debug("DEBUG: schema.sql の読み込み・実行で例外発生: %s", e)
        
        db.commit()
        
        # 初期化後のテーブル一覧を取得
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables_after = [row["name"] for row in cur.fetchall()]
        logging.debug("DEBUG: init_db 完了後のテーブル一覧: %s", tables_after)
        logging.info("DB初期化完了")

@app.before_request
def ensure_db_initialized():
    db = get_db()
    cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks';")
    if cur.fetchone() is None:
        init_db()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ルートページ：テンプレートをレンダリング
@app.route('/')
def index():
    return render_template('index.html')

# GET /php/storage.json  
# SQLite の tasks テーブルからデータを読み出し、JSON形式で返す
@app.route('/php/storage.json', methods=['GET'])
def get_storage():
    db = get_db()
    cur = db.execute("SELECT * FROM tasks")
    rows = cur.fetchall()
    data = {"root": {}}
    for row in rows:
        # children は JSON 文字列として保存している前提
        children = json.loads(row["children"]) if row["children"] else []
        data["root"][str(row["id"])] = {
            "title": row["title"],
            "progress": row["progress"],
            "deadline": row["deadline"],
            "manhour": {
                "estimate": row["estimate"],
                "actual": row["actual"]
            },
            "memo": row["memo"],
            "cost": row["cost"],
            "start": row["start"],
            "done": bool(row["done"]),
            "parent": row["parent"],
            "children": children,
            "shown": bool(row["shown"]),
            "del": bool(row["del"])
        }
    return Response(json.dumps(data, ensure_ascii=False, indent=4), mimetype='application/json')

# POST /php/memoSave  
# LLM などから送信される JSON データを、SQLite の tasks テーブルにアップサートする
@app.route('/php/memoSave', methods=['POST'])
def memo_save():
    jsondata = request.form.get('jsondata')
    if jsondata is not None:
        try:
            data = json.loads(jsondata)
            db = get_db()
            # data["root"] には全タスクの情報が入っている前提
            for task_id, task in data["root"].items():
                children_str = json.dumps(task["children"], ensure_ascii=False)
                db.execute("""
                    REPLACE INTO tasks 
                    (id, title, progress, deadline, estimate, actual, memo, cost, start, done, parent, children, shown, del, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (
                    task_id,
                    task["title"],
                    task["progress"],
                    task["deadline"],
                    task["manhour"]["estimate"],
                    task["manhour"]["actual"],
                    task["memo"],
                    task["cost"],
                    task["start"],
                    1 if task["done"] else 0,
                    task["parent"],
                    children_str,
                    1 if task["shown"] else 0,
                    1 if task["del"] else 0
                ))
            db.commit()
            return "OK", 200
        except json.JSONDecodeError:
            return "Invalid JSON", 400
    else:
        return "No jsondata provided", 400

if __name__ == '__main__':
    # デバッグモードで起動（本番環境では適切な設定に変更してください）
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
