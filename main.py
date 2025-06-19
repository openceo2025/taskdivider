import os
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

from swarm.repl import run_demo_loop
from agents import schedule_agent

if __name__ == "__main__":
    run_demo_loop(schedule_agent, booluser_simulation = False, useragent = schedule_agent, booldebug=True, use_translation=False)