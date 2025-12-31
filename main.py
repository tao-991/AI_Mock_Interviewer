import os
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from openai import OpenAI, api_key
from contextlib import AsyncExitStack
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.messages import ToolMessage

# load environment variables
load_dotenv()

app = FastAPI()



# Connect the mcp servers
server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

chat_model = ChatOpenAI(
    model_name="gpt-4o-mini",
    # model_name="gemini-3-pro-preview", #gemini 3 is quite slow
    temperature=0.7,
    openai_api_key=os.environ.get("API_KEY"),
    openai_api_base=os.environ.get("API_BASE")
)

audio_model = OpenAI(
    api_key=os.environ.get("API_KEY"),
    base_url=os.environ.get("API_BASE")
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
        interview_type: str = Form(...),
        resume_file: Optional[UploadFile] = File(None),
        jd_file: Optional[UploadFile] = File(None)
):
    # 1. 解析 PDF
    resume_text = extract_text_from_pdf(resume_file)
    jd_text = extract_text_from_pdf(jd_file)

    # try to follow the CO-STAR framework for the system prompt
    system_template = """
    [Context]
    You are an expert AI Interviewer for {company}. You are interviewing a candidate for the {position} role.
    

    --- JOB DESCRIPTION (JD) ---
    {jd_context}  # 限制长度防止 Token 溢出

    --- CANDIDATE RESUME ---
    {resume_context} # 限制长度防止 Token 溢出

    [Objective]
    Conduct a realistic mock interview. This interview round is a {interview_type} interview. 
    
    
    [Style]
    1. Start by welcoming the candidate.
    2. Ask ONE question at a time. Do not try to ask many questions in one reply. Keep your reply short and clear otherwise the interviewee can not remember.
    3. If the Resume is provided, ask specifically about their experience. If NOT provided, ask them to describe their relevant experience.
    4. If the JD is provided, align questions to it. If NOT provided, ask standard questions for a {position}.
    5. Keep the interview in ENGLISH.
    6. The first question should be an introduction question about their background and experience.
    7. For your starting words, mention the company and position by name.
    8. Your questions should be more related to the interview type. And you need to tell the interviewee what type of the interview this is at the starting.
    9. If the interview_type is **technical**, there should be at least one Leetcode coding question in first 5 questions. 
    
    
    [Tone]
    Be professional but slightly challenging.
    
    [Audience]
    The target audience is the interviewee who is going to attend the {position} role at {company}.
    
    [Response Format]
    1. Make sure your response it natural for transferring to oral speaking English. 
    
    
    [Constraint]
    1. Reject to answer all questions which are not relevant to the interview. Remind the users to follow the interview scenario.
    2. You **can't** ask interviewee to choose the **difficulty and tags** of the coding question. You need to decide it by yourself based on the position level and JD.
    """

    sys_prompt = ChatPromptTemplate.from_messages(["system",
                                                   system_template])  # you cant use SystemMessage(content=system_template) directly here. Cuz the Langchain will think the whole template as a single message, not a template to be formatted.

    messages = sys_prompt.format_messages(
        company=company,
        position=position,
        interview_type=interview_type,
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
    # Add a constraint after user input to make sure the AI model will not answer irrelevant questions
    topic_constraint = "Judge that if the user question is relevant to the interview scenario. If not, refuse to answer and remind the user to follow the interview scenario. And asked the interviewee again about the previous not answered question."

    for msg in request.history:
        role = msg.get("role")
        if role == 'system':
            messages.append(SystemMessage(content=msg.get("content")))
        elif role == 'user':
            messages.append(HumanMessage(content=msg.get("content")))
        elif role == 'assistant':
            messages.append(AIMessage(content=msg.get("content")))

    messages.append(HumanMessage(content=request.user_input + topic_constraint))

    async with AsyncExitStack() as stack:
        try:
            read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params))
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()

            # retrieve tools list
            mcp_tools = await session.list_tools()

            # convert the MCP tool to langchain tool message
            openai_tools = []
            for tool in mcp_tools.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })

            # if it finds the tools, use it, otherwise, just use normal chat
            if openai_tools:
                llm_with_tools = chat_model.bind_tools(openai_tools)
            else:
                llm_with_tools = chat_model

            # first round: try to use MCP tools
            ai_response = llm_with_tools.invoke(messages)

            trigger_coding_ui = None

            # check if AI want to use tool
            if ai_response.tool_calls:
                # add the tool message to the messages
                messages.append(ai_response)

                for tool_call in ai_response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]

                    # call the tool via MCP
                    result = await session.call_tool(tool_name, tool_args)

                    # add the tool result to the messages
                    tool_response_message = result.content[0].text if result.content else "No response from tool."

                    if "https://leetcode.com/problems/" in tool_response_message:
                        trigger_coding_ui = tool_response_message
                        tool_response_message += "\n\n[SYSTEM INSTRUCTION: You MUST output the LeetCode link provided above using Markdown format: [Title](URL). Do not omit the link.]"

                    messages.append(ToolMessage(
                        content=tool_response_message,
                        tool_name=tool_name,
                        tool_call_id=tool_id
                    ))

                # Add constraint message here to make sure the AI model will not answer irrelevant questions

                # final round: get the final response from the AI after tool usage
                final_response = chat_model.invoke(messages)
                ai_content = final_response.content

            else:
                # if no tool call, just use the first response
                ai_content = ai_response.content


        except Exception as e:
            # if the MCP connection failed, fall back to normal chat
            print(f"MCP Error (falling back to normal chat) : {e}")
            fallback_response = chat_model.invoke(messages)
            ai_content = fallback_response.content

    # update conversation history
    history_dicts = request.history + [
        {"role": "assistant", "content": ai_content}
    ]

    return {"history": history_dicts, "latest_response": ai_content, "trigger_coding": trigger_coding_ui}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
