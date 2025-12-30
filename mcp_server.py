from mcp.server.fastmcp import FastMCP
import random
import json
import requests

mcp = FastMCP("Interview Helper")

# --- Helper: The LeetCode GraphQL Query ---
LEETCODE_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    data {
      title
      titleSlug
      difficulty
      topicTags {
        name
        slug
      }
    }
  }
}
"""

@mcp.tool()
def fetch_leetcode_question(difficulty: str = "Medium", tag: str = "") -> str:
    """
    Fetches a random LeetCode question based on difficulty and tag.

    Args:
        difficulty: Easy, Medium, or Hard
        tag: e.g., "dynamic-programming", "linked-list", "array", "hash-table"
    """

    url = "https://leetcode.com/graphql/"

    # Normalize inputs
    difficulty = difficulty.upper()
    if difficulty not in ["EASY", "MEDIUM", "HARD"]:
        return "Error: Invalid difficulty."

    # Prepare Filters
    filters = {
        "difficulty": difficulty
    }
    if tag:
        tag_slug = tag.lower().replace(" ", "-")
        filters["tags"] = [tag_slug]

    # payload
    payload = {
        "query": LEETCODE_QUERY,
        "variables": {
            "categorySlug": "",
            "limit": 100,
            "skip": 0,
            "filters": filters
        }
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # send request
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            return f"Error: Failed to fetch data from LeetCode. Status code: {response.status_code}"

        data = response.json()

        # parse data
        question_list = data.get("data", {}).get("problemsetQuestionList", {}).get("data", [])

        if not question_list:
            return "No questions found for the given criteria."

        # pick random
        question = random.choice(question_list)

        title = question["title"]
        slug = question["titleSlug"]
        # leetcode url is standard
        question_url = f"https://leetcode.com/problems/{slug}/"

        return f"Please ask the candidate to solve '{title}'. Difficulty: {difficulty} Link: {question_url}. Requirement: Analyze Time Complexity."
    except Exception as e:
        return f"Error: An exception occurred - {str(e)}"


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

    return f"Please ask the candidate to solve {problem}. Requirement: Analyze Time Complexity."

if __name__ == "__main__":
    mcp.run(transport="stdio")
