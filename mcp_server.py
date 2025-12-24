from mcp.server.fastmcp import FastMCP
import random

mcp = FastMCP("Algorithm Puzzle Selector")

PROBLEMS = {
    "easy" : ["Two Sum", "Merge Two Sorted List"],
    "medium" : ["Longest Substring Without Repeating Characters", "3Sum"],
    "hard" : ["Median of Two Sorted Arrays", "Trapping Rain Water"]
}

@mcp.tool()
def get_coding_problems(difficulty: str = "medium") -> str:
    """
    Get a random coding problem based on difficulty.

    :arg:
        difficulty: Easy, Medium, Hard
    """

    difficulty = difficulty.lower()

    if difficulty not in PROBLEMS:
        return "Error: Invalid difficulty."

    problem = random.choice(PROBLEMS[difficulty])

    return f"Please ask the candidate to solbe {problem}. Requirement: Analyze Time Complexity."

if __name__ == "__main__":
    mcp.run()
