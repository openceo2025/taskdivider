import os
import sqlite3
import unittest
import json
from datetime import datetime, timedelta

# agents.py 内の関数・変数をインポート
from agents import (
    context_variables,
    get_db_connection,
    list_tasks,
    search_tasks,
    add_task,
    edit_task,
    mark_task_done,
    delete_task,
    get_today_tasks,
    get_child_tasks,
)

# テスト実行時はデフォルトの db.sqlite ではなく test_db.sqlite を利用する
context_variables["db_file"] = "test_db.sqlite"

def init_db():
    """
    test_db.sqlite の初期化を行う関数。
    既に存在する場合は削除し、tasks テーブルを新たに作成する。
    """
    db_file = context_variables["db_file"]
    if os.path.exists(db_file):
        os.remove(db_file)
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT,
            progress TEXT,
            deadline TEXT,
            estimate INTEGER,
            actual INTEGER,
            memo TEXT,
            cost TEXT,
            start TEXT,
            done INTEGER,
            parent TEXT,
            children TEXT,
            shown INTEGER,
            del INTEGER,
            created_at TEXT,
            updated_at TEXT
        );
    ''')
    conn.commit()
    conn.close()

class TestScheduleAgent(unittest.TestCase):

    def setUp(self):
        # 各テストの前に DB を初期化する
        init_db()

    # --- list_tasks ---
    def test_list_tasks_empty(self):
        """タスクが登録されていない場合、list_tasks() の返り値が文字列型の '[]' になっていることを確認"""
        result = list_tasks()
        self.assertIsInstance(result, str)  # 返り値そのものが文字列であること
        try:
            tasks = json.loads(result)
        except Exception as e:
            self.fail(f"list_tasks() の返り値が JSON としてパースできない: {e}")
        self.assertEqual(tasks, [])

    # --- add_task ---
    def test_add_task(self):
        """add_task: 明示的な引数入力の場合、返り値が文字列型の JSON 文字列になっており、DB に正しく登録されることを確認"""
        result = add_task(
            title="テストタスク",
            deadline="2025-02-11",
            estimate=2,
            memo="テスト用タスク",
            cost="1000",
            start="2025-02-10",
            parent="root",
            progress=""
        )
        self.assertIsInstance(result, str)
        try:
            result_obj = json.loads(result)
        except Exception as e:
            self.fail(f"add_task() の返り値が JSON としてパースできない: {e}")
        self.assertIn("new_task_id", result_obj)
        new_task_id = result_obj["new_task_id"]

        # DB から追加したタスクを確認
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (new_task_id,))
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "テストタスク")

    # --- edit_task ---
    def test_edit_task(self):
        """edit_task: 明示的な引数入力の場合、返り値が文字列型の JSON 文字列になっており、更新が反映されることを確認"""
        # まずタスクを追加
        add_result = add_task(
            title="編集前タスク",
            deadline="2025-02-11",
            estimate=2,
            memo="編集前",
            cost="500",
            start="2025-02-10",
            parent="root",
            progress=""
        )
        add_obj = json.loads(add_result)
        task_id = add_obj["new_task_id"]

        # 編集する場合は更新する項目のみ（children は edit_task では扱わない）
        edit_result = edit_task(
            task_id,
            title="編集後タスク",
            deadline=None,
            estimate=None,
            memo="編集済み",
            cost=None,
            start=None,
            parent=None,
            progress=None
        )
        self.assertIsInstance(edit_result, str)
        try:
            edit_obj = json.loads(edit_result)
        except Exception as e:
            self.fail(f"edit_task() の返り値が JSON としてパースできない: {e}")
        self.assertEqual(edit_obj.get("edited_task_id"), task_id)

        # DB の内容を確認
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        conn.close()
        self.assertEqual(row["title"], "編集後タスク")
        self.assertEqual(row["memo"], "編集済み")

    # --- mark_task_done ---
    def test_mark_task_done(self):
        """mark_task_done: タスクIDを明示的に渡した場合、返り値が文字列型になっており、タスクが完了状態になることを確認"""
        add_result = add_task(
            title="完了テストタスク",
            deadline="2025-02-11",
            estimate=3,
            memo="完了テスト",
            cost="2000",
            start="2025-02-10",
            parent="root",
            progress=""
        )
        add_obj = json.loads(add_result)
        task_id = add_obj["new_task_id"]

        result = mark_task_done(task_id)
        self.assertIsInstance(result, str)
        try:
            result_obj = json.loads(result)
        except Exception as e:
            self.fail(f"mark_task_done() の返り値が JSON としてパースできない: {e}")
        self.assertEqual(result_obj.get("status"), "done")

        # DB の更新確認
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        conn.close()
        self.assertEqual(row["done"], 1)

    # --- delete_task ---
    def test_delete_task(self):
        """delete_task: タスクIDを明示的に渡した場合、返り値が文字列型の JSON 文字列になっており、タスクが物理的に削除されることを確認"""
        add_result = add_task(
            title="削除テストタスク",
            deadline="2025-02-11",
            estimate=1,
            memo="削除テスト",
            cost="300",
            start="2025-02-10",
            parent="root",
            progress=""
        )
        add_obj = json.loads(add_result)
        task_id = add_obj["new_task_id"]

        result = delete_task(task_id)
        self.assertIsInstance(result, str)
        try:
            result_obj = json.loads(result)
        except Exception as e:
            self.fail(f"delete_task() の返り値が JSON としてパースできない: {e}")
        self.assertIn("deleted_task_id", result_obj)
        self.assertEqual(result_obj.get("deleted_task_id"), task_id)

        # DB から削除されていることを確認
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        conn.close()
        self.assertIsNone(row)

    # --- search_tasks ---
    def test_search_tasks(self):
        """search_tasks: クエリ入力を明示的に渡した場合、返り値が文字列型になっており、期待件数が返ることを確認"""
        # タスクを追加
        add_task("会議", "2025-02-11", 1, "", "", "", "root", "")
        add_task("会議事前打ち合わせ", "2025-02-12", 2, "", "", "", "root", "")
        add_task("買い物", "2025-02-13", 1, "", "", "", "root", "")
        
        result = search_tasks("会")
        self.assertIsInstance(result, str)
        try:
            result_list = json.loads(result)
        except Exception as e:
            self.fail(f"search_tasks() の返り値が JSON としてパースできない: {e}")
        self.assertEqual(len(result_list), 2)
        titles = [task["title"] for task in result_list]
        self.assertIn("会議", titles)
        self.assertIn("会議事前打ち合わせ", titles)

    # --- get_today_tasks ---
    def test_get_today_tasks(self):
        """get_today_tasks: 本日の日付のタスクのみが返り、返り値が文字列型になっていることを確認"""
        today = datetime.today().strftime("%Y-%m-%d")
        tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        add_task("今日のタスク", today, 1, "", "", "", "root", "")
        add_task("明日のタスク", tomorrow, 1, "", "", "", "root", "")

        result = get_today_tasks()
        self.assertIsInstance(result, str)
        try:
            result_list = json.loads(result)
        except Exception as e:
            self.fail(f"get_today_tasks() の返り値が JSON としてパースできない: {e}")
        # 本日のタスクのみ取得されるはず
        self.assertEqual(len(result_list), 1)
        self.assertEqual(result_list[0]["title"], "今日のタスク")

    # --- get_child_tasks ---
    def test_get_child_tasks(self):
        """get_child_tasks: 複数の子タスクを持つ親タスクに対して、成功・失敗パターンを確認"""
        # 親タスクと子タスクを2つ作成
        parent_result = add_task("親タスク")
        parent_id = json.loads(parent_result)["new_task_id"]
        json.loads(add_task("子タスク1", parent=parent_id))
        json.loads(add_task("子タスク2", parent=parent_id))

        # 親タスクIDから子タスクを取得
        result = get_child_tasks(parent_id)
        self.assertIsInstance(result, str)
        try:
            child_list = json.loads(result)
        except Exception as e:
            self.fail(f"get_child_tasks() の返り値が JSON としてパースできない: {e}")
        self.assertEqual(len(child_list), 2)
        titles = [c["title"] for c in child_list]
        self.assertIn("子タスク1", titles)
        self.assertIn("子タスク2", titles)

        # 親タスク名（部分一致）から子タスクを取得
        result_by_title = get_child_tasks("親タ")
        child_list2 = json.loads(result_by_title)
        self.assertEqual(len(child_list2), 2)

        # 存在しないIDを指定した場合はエラー
        result_error = get_child_tasks("nonexistent")
        self.assertIsInstance(result_error, str)
        error_obj = json.loads(result_error)
        self.assertIn("error", error_obj)

if __name__ == "__main__":
    unittest.main()
