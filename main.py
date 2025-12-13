import os
import tempfile
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from openai import OpenAI
from pyexpat.errors import messages
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

# load environment variables
load_dotenv()

app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

chat_model = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.7
)

audio_model = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_API_BASE")
)

def tts_stream_func(text: str):
    try:
        response = audio_model.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        return response.iter_bytes()
    except Exception as e:
        raise ValueError(f"TTS Error: {e}")
tts_runnable = RunnableLambda(tts_stream_func)


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



class TTSRequest(BaseModel):
    text: str

# --- routing ---

@app.post("/stt")
async def tts(audio: UploadFile = File(...)):
    try:
        audio_content = await audio.read()

        response = audio_model.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file = (audio.filename,audio_content, audio.content_type)
        )

        return {"transcript": response.text}
    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts")
async def tts(request: TTSRequest):
    try:
        response = tts_runnable.invoke(request.text)

        # 将二进制音频数据直接流式返回给前端
        return StreamingResponse(
            response,
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


    system_template = """
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
    8. For your starting words, mention the company and position by name.
    """

    sys_prompt = ChatPromptTemplate.from_messages(["system", system_template]) # you cant use SystemMessage(content=system_template) directly here. Cuz the Langchain will think the whole template as a single message, not a template to be formatted.

    messages = sys_prompt.format_messages(
        company=company,
        position=position,
        jd_context=jd_text[:3000] if jd_text else "Not Provided.",
        resume_context=resume_text[:3000] if resume_text else "Not Provided."
    )

    try:
        response = chat_model.invoke(messages)

        ai_content = response.content

        history_dicts = [
            {"role": "system", "content": messages[0].content},
            {"role": "assistant", "content": ai_content}
        ]
        return {"history": history_dicts, "latest_response": ai_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/chat")
async def chat(request: ChatRequest):
   # transfer the json from front-end to the format that langchain accepts
    messages = []

    for msg in request.history:
        role = msg.get("role")
        if role == 'system':
            messages.append(SystemMessage(content=msg.get("content")))
        elif role == 'user':
            messages.append(HumanMessage(content=msg.get("content")))
        elif role == 'assistant':
            messages.append(AIMessage(content=msg.get("content")))

    messages.append(HumanMessage(content=request.user_input))

    try:
        response = chat_model.invoke(messages)

        ai_content = response.content

        # 更新对话历史
        history_dicts = request.history + [
            {"role": "user", "content": request.user_input},
            {"role": "assistant", "content": ai_content}
        ]

        return {"history": history_dicts, "latest_response": ai_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)