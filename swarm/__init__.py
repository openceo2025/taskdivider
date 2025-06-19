class Agent:
    def __init__(self, name=None, model=None, tool_choice=None, instructions=None, temperature=None):
        self.name = name
        self.model = model
        self.tool_choice = tool_choice
        self.instructions = instructions
        self.temperature = temperature
        self.functions = []
