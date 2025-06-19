from swarm import Agent
import sqlite3
from datetime import datetime
import pprint
import os
import json
import uuid
from typing import List

# ----------------------------
# コンテキスト変数（必要に応じて拡張可能）
# ----------------------------
context_variables = {
    "db_file": "db.sqlite"  # SQLite の DB ファイルパス
}

# ----------------------------
# エージェントへの指示（秘書として予定管理を支援する）
# ----------------------------
def instructions(context_variables):
    return (
        "日本語で返答する。秘書としてふるまい、予定管理を支援します。"
        "あなたは SQLite データベースにアクセスし、タスクの追加、検索、編集、削除（完了状態への変更）を行います。"
        "\n\n【タスクの各フィールド】\n"
        "・id: タスクID（自動生成または指定可能）\n"
        "・title: タスクのタイトル（必須）\n"
        "・progress: 進捗（任意）\n"
        "・deadline: 期限（YYYY-MM-DD形式、任意）\n"
        "・estimate: 見積もり時間（整数、任意）\n"
        "・actual: 実績時間（初期値 0）\n"
        "・memo: メモ（任意）\n"
        "・cost: 費用（任意）\n"
        "・start: 開始日時（任意）\n"
        "・done: 完了状態（0または1、初期値 0）\n"
        "・parent: 親タスク（任意、デフォルト 'root'）\n"
        "・children: 子タスクのリスト（任意、各要素は文字列、デフォルトは空リスト）\n"
        "・shown: 表示フラグ（通常は 1）\n"
        "・del: 削除フラグ（通常は 0）\n"
        "・created_at, updated_at: 作成・更新日時\n"
    )

# ----------------------------
# Agent インスタンスの生成
# ----------------------------
schedule_agent = Agent(
    name="Schedule Agent",
    # model="mistral-small-24b-instruct-2501@iq3_m",  # 適宜モデルを変更してください
    model="phi-4",
    # model="gpt-4o",
    tool_choice="auto",
    instructions=instructions(context_variables)
)

# ----------------------------
# DB 接続のヘルパー関数
# ----------------------------
def get_db_connection():
    try:
        conn = sqlite3.connect(context_variables["db_file"])
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        print("DEBUG: DBファイル:", context_variables["db_file"])
        print("DEBUG: DB内のテーブル一覧:", [row["name"] for row in tables])
        return conn
    except sqlite3.Error as e:
        print(f"DEBUG: Error in get_db_connection: {str(e)}")
        raise

# ----------------------------
# タスク一覧を取得（未完了タスクを昇順に）
# ----------------------------
def list_tasks():
    """
    タスク一覧を取得します。
    
    引数:
      - なし

    処理内容:
      - データベースから、done フラグが 0（未完了）のタスクを期限の昇順で取得する。

    返り値:
      - タスクリスト（各タスクは dict）の JSON文字列
        例: "[]"（タスクがない場合）
    """
    try:
        print("DEBUG: list_tasks start")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT sql FROM sqlite_master WHERE name='tasks';")
        table_schema = cur.fetchone()
        print("DEBUG: tasks テーブルの定義:", table_schema["sql"] if table_schema else "tasksテーブルなし")
        cur.execute("SELECT * FROM tasks WHERE done = 0 ORDER BY deadline ASC")
        rows = cur.fetchall()
        conn.close()
        tasks = [dict(row) for row in rows]
        return json.dumps(tasks, ensure_ascii=False)
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in list_tasks: {str(e)}"})

# ----------------------------
# タイトルの部分一致でタスクを検索
# ----------------------------
def search_tasks(query: str):
    """
    タイトルの部分一致でタスクを検索します。
    
    引数:
      - query (str): 検索キーワード（必須）

    処理内容:
      - タイトルに query が含まれる（LIKE句）未完了のタスクを取得する。

    返り値:
      - 該当タスクのリスト（各タスクは dict）の JSON文字列
        例: "[{...}, {...}]"
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM tasks WHERE title LIKE ? AND done = 0 ORDER BY deadline ASC",
            ('%' + query + '%',)
        )
        rows = cur.fetchall()
        conn.close()
        tasks = [dict(row) for row in rows]
        return json.dumps(tasks, ensure_ascii=False)
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in search_tasks: {str(e)}"})

# ----------------------------
# 新規タスク（プロジェクト）の追加
# ----------------------------
def add_task(title: str, deadline: str = "", estimate: int = 0, memo: str = "",
             cost: str = "", start: str = "", parent: str = "root", progress: str = "", children: List[str] = None):
    """
    新規タスク（プロジェクト）の追加を行います。
    
    引数:
      - title (str): タスクのタイトル（必須）
      - deadline (str): 期限（YYYY-MM-DD形式、オプショナル、デフォルトは空文字）
      - estimate (int): 見積もり時間（整数、オプショナル、デフォルトは 0）
      - memo (str): メモ（オプショナル、デフォルトは空文字）
      - cost (str): 費用（オプショナル、デフォルトは空文字）
      - start (str): 開始日時（オプショナル、デフォルトは空文字）
      - parent (str): 親タスク（オプショナル、デフォルトは "root"）
      - progress (str): 進捗（オプショナル、デフォルトは空文字）
      - children (List[str]): 子タスクのリスト（オプショナル、各要素は文字列、デフォルトは空リスト）
    
    処理内容:
      - 各引数からタスク情報のオブジェクトを生成し、DB の tasks テーブルに INSERT する。
      - タスクIDは自動生成（UUID）される。
    
    返り値:
      - {"new_task_id": "タスクIDが返されます"} の JSON文字列。
      - エラー発生時は {"error": "エラーメッセージが返されます"} を返す。
    """
    if children is None:
        children = []
    if not title.strip():
        return json.dumps({"error": "新しいプロジェクトのタイトルが指定されていません。"})
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO tasks 
            (id, title, progress, deadline, estimate, actual, memo, cost, start, done, parent, children, shown, del, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                title,
                progress,
                deadline,
                estimate,
                0,
                memo,
                cost,
                start,
                0,
                parent,
                json.dumps(children, ensure_ascii=False),
                1,
                0,
                now,
                now
            )
        )
        conn.commit()
        conn.close()
        return json.dumps({"new_task_id": task_id})
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in add_task: {str(e)}"})

# ----------------------------
# 既存タスクの編集（更新する項目のみ更新）
# ----------------------------
def edit_task(task_id: str, title: str = None, deadline: str = None, estimate: int = None,
              memo: str = None, cost: str = None, start: str = None, parent: str = None,
              progress: str = None, children: List[str] = None):
    """
    既存タスクの編集を行います。更新する項目のみ指定してください。
    
    引数:
      - task_id (str): 更新対象のタスクID（必須）
      - title (str): タスクのタイトル（オプショナル）
      - deadline (str): 期限（YYYY-MM-DD形式、オプショナル）
      - estimate (int): 見積もり時間（整数、オプショナル）
      - memo (str): メモ（オプショナル）
      - cost (str): 費用（オプショナル）
      - start (str): 開始日時（オプショナル）
      - parent (str): 親タスク（オプショナル）
      - progress (str): 進捗（オプショナル）
      - children (List[str]): 子タスクのリスト（オプショナル、各要素は文字列）
    
    処理内容:
      - 指定された引数のみを更新する。
    
    返り値:
      - {"edited_task_id": "タスクIDが返されます"} の JSON文字列。更新項目がない場合は {"error": "更新する項目が指定されていません。"} を返す。
    """
    try:
        update_fields = {}
        if title is not None:
            update_fields["title"] = title
        if deadline is not None:
            update_fields["deadline"] = deadline
        if estimate is not None:
            update_fields["estimate"] = estimate
        if memo is not None:
            update_fields["memo"] = memo
        if cost is not None:
            update_fields["cost"] = cost
        if start is not None:
            update_fields["start"] = start
        if parent is not None:
            update_fields["parent"] = parent
        if progress is not None:
            update_fields["progress"] = progress
        if children is not None:
            update_fields["children"] = json.dumps(children, ensure_ascii=False)
        if not update_fields:
            return json.dumps({"error": "更新する項目が指定されていません。"})
    
        conn = get_db_connection()
        cur = conn.cursor()
        fields = []
        values = []
        for key, value in update_fields.items():
            fields.append(f"{key} = ?")
            values.append(value)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields.append("updated_at = ?")
        values.append(now)
        values.append(task_id)
        sql = "UPDATE tasks SET " + ", ".join(fields) + " WHERE id = ?"
        cur.execute(sql, values)
        conn.commit()
        conn.close()
        return json.dumps({"edited_task_id": task_id})
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in edit_task: {str(e)}"})

# ----------------------------
# タスクを完了状態に変更する
# ----------------------------
def mark_task_done(task_id: str):
    """
    タスクを完了状態に変更します。
    
    引数:
      - task_id (str): 対象タスクのID（必須）
    
    処理内容:
      - 指定された task_id のタスクの done フラグを 1 に設定する。
    
    返り値:
      - {"task_id": "タスクIDが返されます", "status": "done"} の JSON文字列
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("UPDATE tasks SET done = 1, updated_at = ? WHERE id = ?", (now, task_id))
        conn.commit()
        conn.close()
        return json.dumps({"task_id": task_id, "status": "done"})
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in mark_task_done: {str(e)}"})

# ----------------------------
# タスク削除（完了状態にする操作と同等）
# ----------------------------
def delete_task(task_id: str):
    """
    タスク削除を行います。
    
    ここではタスクを物理的に削除するのではなく、完了状態にする操作と同等の処理を行います。
    
    引数:
      - task_id (str): 対象タスクのID（必須）
    
    返り値:
      - mark_task_done と同じ返り値（JSON文字列）
    """
    return mark_task_done(task_id)

# ----------------------------
# 本日のタスクを取得する
# ----------------------------
def get_today_tasks():
    """
    本日のタスクを取得します。
    
    処理内容:
      - 今日の日付（YYYY-MM-DD形式）と一致する deadline のタスクのうち、done が 0 のものを取得する。
    
    返り値:
      - タスクリスト（各タスクは dict）の JSON文字列
    """
    try:
        today = datetime.today().strftime("%Y-%m-%d")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE deadline = ? AND done = 0 ORDER BY deadline ASC", (today,))
        rows = cur.fetchall()
        conn.close()
        tasks = [dict(row) for row in rows]
        return json.dumps(tasks, ensure_ascii=False)
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in get_today_tasks: {str(e)}"})

# ----------------------------
# エージェントに提供する関数群の登録
# ----------------------------
schedule_agent.functions.extend([
    list_tasks,
    search_tasks,
    add_task,
    edit_task,
    mark_task_done,
    delete_task,
    get_today_tasks,
])

# ----------------------------
# デバッグ用：直接実行した場合にタスク一覧を出力
# ----------------------------
if __name__ == "__main__":
    pprint.pprint(list_tasks())
