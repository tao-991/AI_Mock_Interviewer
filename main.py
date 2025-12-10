import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from openai import OpenAI
from pypdf import PdfReader  # 新增：用于读取PDF
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# 配置 OpenAI (请确保您的 KEY 和 BASE 环境变量已设置)
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_API_BASE")
)


# --- 辅助函数：提取PDF文字 ---
def extract_text_from_pdf(file: UploadFile) -> str:
    if not file:
        return ""
    try:
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


# --- 数据模型 ---
# 注意：start_interview 改用 Form Data 接收，所以这里不需要 Pydantic 模型了
class ChatRequest(BaseModel):
    history: List[dict]
    user_input: str


# --- 核心提示词构建 ---
def create_system_prompt(company: str, position: str, resume_text: str, jd_text: str) -> str:
    jd_context = f"--- JOB DESCRIPTION (JD) ---\n{jd_text[:3000]}" if jd_text else "Job Description: Not provided. Please rely on general knowledge for this role."
    resume_context = f"--- CANDIDATE RESUME ---\n{resume_text[:3000]}" if resume_text else "Candidate Resume: Not provided. Ask the candidate to introduce themselves and their background."


    return f"""
    You are an expert AI Interviewer for {company}. 
    You are interviewing a candidate for the {position} role.

    --- JOB DESCRIPTION (JD) ---
    {jd_context}  # 限制长度防止 Token 溢出

    --- CANDIDATE RESUME ---
    {resume_context} # 限制长度防止 Token 溢出

    YOUR GOAL:
    Conduct a realistic mock interview.

    YOUR RULES:
    1. Start by welcoming the candidate.
    2. Ask ONE question at a time.
    3. If the Resume is provided, ask specifically about their experience. If NOT provided, ask them to describe their relevant experience.
    4. If the JD is provided, align questions to it. If NOT provided, ask standard questions for a {position}.
    5. Be professional but slightly challenging.
    6. Keep the interview in ENGLISH.
    7. The first question should be an introduction question about their background and experience.
    """


class TTSRequest(BaseModel):
    text: str

# --- 路由 ---

@app.post("/tts")
async def tts(request: TTSRequest):
    try:
        # 使用 OpenAI 的 tts-1 模型
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",  # 可选声音: alloy, echo, fable, onyx, nova, shimmer
            input=request.text
        )

        # 将二进制音频数据直接流式返回给前端
        return StreamingResponse(
            response.iter_bytes(),
            media_type="audio/mpeg"
        )
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/start_interview")
async def start_interview(
        company: str = Form(...),
        position: str = Form(...),
        resume_file: Optional[UploadFile] = File(None),
        jd_file: Optional[UploadFile] = File(None)
):
    # 1. 解析 PDF
    resume_text = extract_text_from_pdf(resume_file)
    jd_text = extract_text_from_pdf(jd_file)



    # 2. 生成 System Prompt
    system_prompt = create_system_prompt(company, position, resume_text, jd_text)

    messages = [{"role": "system", "content": system_prompt}]

    # 3. 让 AI 生成第一句
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 或者 gpt-3.5-turbo
            messages=messages,
            temperature=0.7
        )
        first_message = response.choices[0].message.content
        messages.append({"role": "assistant", "content": first_message})

        return {"history": messages, "latest_response": first_message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: ChatRequest):
    # 这里保持不变，继续对话
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)