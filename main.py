import os
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

from swarm.repl import run_demo_loop
from agents import schedule_agent
from threading import Thread
import app


def start_flask():
    """Initialize DB and run the Flask application."""
    app.init_db()
    app.app.run(host="0.0.0.0", port=5001, debug=True)

if __name__ == "__main__":
    # Launch Flask in a background thread and print the access URL
    flask_thread = Thread(target=start_flask, daemon=True)
    flask_thread.start()
    print("Flask server running at http://localhost:5001")

    run_demo_loop(
        schedule_agent,
        booluser_simulation=False,
        useragent=schedule_agent,
        booldebug=True,
        use_translation=False,
    )
