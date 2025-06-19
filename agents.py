from swarm import Agent
import sqlite3
from datetime import datetime
import pprint
import os
import json
import uuid
from typing import List
import logging

logging.basicConfig(level=logging.INFO)

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
        "あなたはユーザーの指示に従い、SQLite データベースにアクセスし、タスクの追加、検索、編集、削除（完了状態への変更）を行います。"
        "それに必要なtoolが準備してあります。tool useをしたあとはJSON等で実行結果が返ってきますが、ユーザーにはJSONを直接見せず、自然な言語で整理してユーザーに結果を伝えてください。"
        "管理対象であるSQLiteに格納されているタスクは複数あり、木構造になっています"
        "ルート直下のタスクはプロジェクトと呼びます"       
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
    # model="phi-4",
    #model="gpt-4o",
    #model = "google_gemma-3-12b-it",
    # model = "deepseek-r1-distill-qwen-7b",
    model = "qwen3-8b-q4_k_m_qwen",
    #model = "devstralq4_k_m",
    tool_choice="auto",
    instructions=instructions(context_variables),
    temperature=0.2,   # ツール選択の確実性を高めるため低温度に固定
)

# ----------------------------
# 現在の日付と時刻を取得する関数
# ----------------------------
def get_current_datetime(**kwags):
    """
    現在の日付と時刻を返します.
    
    処理内容:
      - 現在の日時を取得し、"YYYY年MM月DD日 HH時MM分SS秒" の形式で文字列として返します。
      
    返り値:
      - 現在の日付と時刻の文字列
    """
    now = datetime.now()
    return now.strftime("%Y年%m月%d日 %H時%M分%S秒")

# ----------------------------
# DB 接続のヘルパー関数
# ----------------------------
def get_db_connection(**kwags):
    try:
        conn = sqlite3.connect(context_variables["db_file"])
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        logging.debug("DEBUG: DBファイル: %s", context_variables["db_file"])
        logging.debug("DEBUG: DB内のテーブル一覧: %s", [row["name"] for row in tables])
        return conn
    except sqlite3.Error as e:
        logging.debug("DEBUG: Error in get_db_connection: %s", str(e))
        raise

# ----------------------------
# ゼロパディング補正用のヘルパー関数
# ----------------------------
def normalize_date_string(date_str: str, **kwags) -> str:
    """
    日付文字列を正規化し、ゼロパディングされた"YYYY-MM-DD" 形式に変換します。
    """
    if not date_str.strip():
        return date_str
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logging.debug("DEBUG: normalize_date_string failed for %s: %s", date_str, e)
        raise ValueError(f"Invalid date format: {date_str}") from e
    
# ----------------------------
# タスク一覧を取得（未完了タスクを昇順に）
# ----------------------------
def list_tasks(**kwags):
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
        logging.debug("DEBUG: list_tasks start")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT sql FROM sqlite_master WHERE name='tasks';")
        table_schema = cur.fetchone()
        logging.debug("DEBUG: tasks テーブルの定義: %s", table_schema["sql"] if table_schema else "tasksテーブルなし")
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
def search_tasks(query: str, **kwags):
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
             cost: str = "", start: str = "", parent: str = "root", progress: str = "", **kwags):
    """
    新規タスク（プロジェクト）の追加を行います.
    
    引数:
      - title (str): タスクのタイトル（必須）
      - deadline (str): 期限（YYYY-MM-DD形式、オプショナル、デフォルトは空文字）
      - estimate (int): 見積もり時間（整数、オプショナル、デフォルトは 0）
      - memo (str): メモ（オプショナル、デフォルトは空文字）
      - cost (str): 費用（オプショナル、デフォルトは空文字）
      - start (str): 開始日時（オプショナル、デフォルトは空文字）
      - parent (str): 親タスクのID（オプショナル、デフォルトは "root"）
      - progress (str): 進捗（オプショナル、デフォルトは空文字）

    処理内容:
      - 各引数からタスク情報のオブジェクトを生成し、DB の tasks テーブルに INSERT する。
      - タスクIDは自動生成（UUID）される。
      - もし parent が "root" でなければ、親タスクの children フィールドに新規タスクの ID を追加する。

    返り値:
      - {"new_task_id": "タスクIDが返されます"} の JSON文字列。
      - エラー発生時は {"error": "エラーメッセージが返されます"} を返す。
    """
    if not title.strip():
        return json.dumps({"error": "新しいプロジェクトのタイトルが指定されていません。"})
    try:
        # 日付情報のゼロパディング補正をヘルパー関数で適用
        if deadline.strip():
            try:
                deadline = normalize_date_string(deadline)
            except ValueError as e:
                return json.dumps({"error": str(e)})
        if start.strip():
            try:
                start = normalize_date_string(start)
            except ValueError as e:
                return json.dumps({"error": str(e)})
    
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_id = str(uuid.uuid4())
        conn = get_db_connection()
        cur = conn.cursor()
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
                json.dumps([], ensure_ascii=False),  # 初期状態は空リスト
                1,
                0,
                now,
                now
            )
        )
        conn.commit()
        # もし親タスクが "root" でなければ、親タスクの children に新規タスクIDを追加
        if parent != "root":
            try:
                cur.execute("SELECT children FROM tasks WHERE id = ?", (parent,))
                row = cur.fetchone()
                if row is not None:
                    current_children = json.loads(row["children"]) if row["children"] else []
                    if task_id not in current_children:
                        current_children.append(task_id)
                    cur.execute("UPDATE tasks SET children = ?, updated_at = ? WHERE id = ?",
                                (json.dumps(current_children, ensure_ascii=False), now, parent))
                    conn.commit()
            except sqlite3.Error as e:
                # 親更新エラーはログに出すが、タスク追加自体は成功しているので無視
                logging.debug("DEBUG: Error updating parent's children in add_task: %s", str(e))
        conn.close()
        return json.dumps({"new_task_id": task_id})
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in add_task: {str(e)}"})

# ----------------------------
# 既存タスクの編集（更新する項目のみ更新）
# ----------------------------
def edit_task(task_id: str, title: str = None, deadline: str = None, estimate: int = None,
              memo: str = None, cost: str = None, start: str = None, parent: str = None,
              progress: str = None, **kwags):
    """
    既存タスクの編集を行います。更新する項目のみ指定してください.
    
    引数:
      - task_id (str): 更新対象のタスクID（必須）
      - title (str): タスクのタイトル（オプショナル）
      - deadline (str): 期限（YYYY-MM-DD形式、オプショナル）
      - estimate (int): 見積もり時間（整数、オプショナル）
      - memo (str): メモ（オプショナル）
      - cost (str): 費用（オプショナル）
      - start (str): 開始日時（オプショナル）
      - parent (str): 親タスクのID（オプショナル）※ただし、親子関係の編集は行わない
      - progress (str): 進捗（オプショナル）

    処理内容:
      - 指定された引数のみを更新する。children の編集は行いません。

    返り値:
      - {"edited_task_id": "タスクIDが返されます"} の JSON文字列。
      - 更新項目がない場合は {"error": "更新する項目が指定されていません。"} を返す。
    """
    try:
        update_fields = {}
        if title is not None:
            update_fields["title"] = title
        if deadline is not None:
            # ゼロパディング補正を適用
            if deadline.strip():
                try:
                    deadline = normalize_date_string(deadline)
                except ValueError as e:
                    return json.dumps({"error": str(e)})
            update_fields["deadline"] = deadline
        if estimate is not None:
            update_fields["estimate"] = estimate
        if memo is not None:
            update_fields["memo"] = memo
        if cost is not None:
            update_fields["cost"] = cost
        if start is not None:
            if start.strip():
                try:
                    start = normalize_date_string(start)
                except ValueError as e:
                    return json.dumps({"error": str(e)})
            update_fields["start"] = start
        if parent is not None:
            update_fields["parent"] = parent
        if progress is not None:
            update_fields["progress"] = progress
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
def mark_task_done(task_id: str, **kwags):
    """
    タスクを完了状態に変更します.
    
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
# タスクを物理的に削除する
# ----------------------------
def delete_task(task_id: str, **kwags):
    """
    タスク削除を行います.
    
    引数:
      - task_id (str): 対象タスクのID（必須）

    処理内容:
      - 対象タスクをデータベースから物理的に削除する。
      - もし削除対象タスクの親タスクが "root" でなければ、親タスクの children フィールドから
        削除するタスクの ID を取り除く。

    返り値:
      - {"deleted_task_id": "タスクIDが返されます"} の JSON文字列。
      - エラー発生時は {"error": "エラーメッセージが返されます"} を返す。
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # まず、削除対象タスクの親IDを取得
        cur.execute("SELECT parent FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if row is None:
            conn.close()
            return json.dumps({"error": "タスクが見つかりません。"})
        parent_id = row["parent"]
        # タスクの物理削除
        cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        # もし親タスクが "root" でなければ、親の children から task_id を削除する
        if parent_id != "root":
            cur.execute("SELECT children FROM tasks WHERE id = ?", (parent_id,))
            row_parent = cur.fetchone()
            if row_parent is not None:
                try:
                    current_children = json.loads(row_parent["children"]) if row_parent["children"] else []
                except Exception:
                    current_children = []
                if task_id in current_children:
                    current_children.remove(task_id)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cur.execute("UPDATE tasks SET children = ?, updated_at = ? WHERE id = ?",
                                (json.dumps(current_children, ensure_ascii=False), now, parent_id))
                    conn.commit()
        conn.close()
        return json.dumps({"deleted_task_id": task_id})
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in delete_task: {str(e)}"})

# ----------------------------
# 本日のタスクを取得する
# ----------------------------
def get_today_tasks(**kwags):
    """
    本日のタスクを取得します.
    
    処理内容:
      - 今日の日付（YYYY-MM-DD形式）と一致する deadline のタスクのうち、done が 0 のものを取得する.

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

def get_child_tasks(search_param: str, **kwags):
    """
    指定されたタスクIDまたはタスク名の一部に基づいて、そのタスクの子タスク一覧を取得します.
    
    引数:
      - search_param (str): タスクID、またはタスク名の一部を示す文字列.
    
    返り値:
      - 子タスク一覧の JSON 文字列（例: "[{...}, {...}]"）.
      - 指定されたタスクが見つからなかった場合は、{"error": "タスクが見つかりませんでした。"} の JSON文字列を返します.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # まず、引数をタスクIDとして検索
        cur.execute("SELECT * FROM tasks WHERE id = ?", (search_param,))
        task_row = cur.fetchone()

        # タスクIDで見つからなかった場合、タスク名の部分一致検索を実施
        if task_row is None:
            cur.execute("SELECT * FROM tasks WHERE title LIKE ?", ('%' + search_param + '%',))
            task_row = cur.fetchone()

        # 対象タスクが見つからなかった場合はエラーを返す
        if task_row is None:
            conn.close()
            return json.dumps({"error": "タスクが見つかりませんでした。"}, ensure_ascii=False)

        # 対象タスクの子タスクID一覧を取得（childrenフィールドはJSON文字列）
        children_json = task_row["children"]
        if children_json:
            try:
                children_ids = json.loads(children_json)
            except Exception:
                children_ids = []
        else:
            children_ids = []

        # 子タスクがない場合は空リストを返す
        if not children_ids:
            conn.close()
            return json.dumps([], ensure_ascii=False)

        # 子タスクID一覧に基づいて、子タスクの詳細情報を一括取得
        placeholders = ','.join(['?'] * len(children_ids))
        sql = f"SELECT * FROM tasks WHERE id IN ({placeholders})"
        cur.execute(sql, children_ids)
        child_rows = cur.fetchall()
        conn.close()
        child_tasks = [dict(row) for row in child_rows]
        return json.dumps(child_tasks, ensure_ascii=False)
    except sqlite3.Error as e:
        return json.dumps({"error": f"Database error in get_child_tasks: {str(e)}"}, ensure_ascii=False)

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
    get_current_datetime,
    get_child_tasks,
])

# ----------------------------
# デバッグ用：直接実行した場合にタスク一覧を出力
# ----------------------------
if __name__ == "__main__":
    logging.info(pprint.pformat(list_tasks()))
