import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles # 导入这个
from fastapi.templating import Jinja2Templates # 导入这个
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 强烈建议将 Key 放入环境变量
# os.environ["OPENAI_API_KEY"] = "sk-..."
load_dotenv()
print(os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_API_BASE"))
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_API_BASE")  # 关键是加这一行
)

app = FastAPI()

# 允许跨域（前端开发需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 数据模型 ---
class Message(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class InterviewConfig(BaseModel):
    company: str
    position: str
    resume_summary: Optional[str] = None  # 可选：传入简历摘要


class ChatRequest(BaseModel):
    history: List[Message]
    user_input: str


# --- 核心提示词构建 ---
def create_system_prompt(config: InterviewConfig) -> str:
    resume_context = f"Candidate Resume Summary: {config.resume_summary}" if config.resume_summary else ""

    return f"""
    You are an expert AI Interviewer for {config.company}. 
    You are interviewing a candidate for the {config.position} role.

    {resume_context}

    YOUR RULES:
    1. Start by welcoming the candidate and asking them to introduce themselves.
    2. Ask ONE question at a time. Do not list multiple questions.
    3. Wait for the candidate's response.
    4. Based on the candidate's answer, either:
       - Dig deeper (follow-up question) if the answer is vague.
       - Move to the next relevant topic (technical or behavioral) if the answer is good.
    5. Be professional but slightly challenging, like a real senior interviewer.
    6. If the candidate struggles, offer a small hint, but verify their understanding.
    7. Keep the interview in ENGLISH.

    Goal: Assess if the candidate is a good fit for {config.company}.
    """


# --- API 接口 ---

@app.post("/start_interview")
async def start_interview(config: InterviewConfig):
    """初始化面试，返回第一句开场白"""
    system_prompt = create_system_prompt(config)

    messages = [{"role": "system", "content": system_prompt}]

    # 让 AI 生成第一句开场白
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 或 gpt-3.5-turbo, gpt-4
        messages=messages
    )

    first_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": first_message})

    return {"history": messages, "latest_response": first_message}


@app.post("/chat")
async def chat(request: ChatRequest):
    """处理用户回复并获取 AI 的下一个问题"""

    # 将用户输入添加到历史记录
    current_history = request.history
    current_history.append({"role": "user", "content": request.user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=current_history,
            temperature=0.7
        )

        ai_reply = response.choices[0].message.content
        current_history.append({"role": "assistant", "content": ai_reply})

        return {"history": current_history, "latest_response": ai_reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 1. 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# 2. 添加主页路由
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)