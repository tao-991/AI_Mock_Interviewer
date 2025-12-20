let history = [];
let currentAudio = null;
let recognition;
let isRecording = false;
let baseText = "";
let timerInterval;
let totalSeconds = 0;

async function startTimer() {
    clearInterval(timerInterval);
    totalSeconds = 0;

    timerInterval = setInterval(setTimer, 1000);
}


function setTimer(){
    totalSeconds++;

    const Second = totalSeconds % 60;
    const Minute = Math.floor(totalSeconds / 60);
    const Hours = Math.floor(Minute / 60);

    document.getElementById("hrs").innerHTML = pad(Hours);
    document.getElementById("secs").innerHTML = pad(Second);
    document.getElementById("mins").innerHTML = pad(Minute);
}

function pad(val){
    var valString = val + "";
    if (valString.length < 2){
        return "0" + valString;
    } else {
    return valString;
    }
}


async function playAudio(text) {
    // 如果有正在播放的，先停止（防止两个人同时说话）
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    try {
        const res = await fetch('/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: text })
        });

        if (!res.ok) throw new Error("TTS failed");

        // 把返回的二进制流变成 Blob URL
        const blob = await res.blob();
        const audioUrl = URL.createObjectURL(blob);

        // 播放
        currentAudio = new Audio(audioUrl);
        currentAudio.play();

    } catch (e) {
        console.error("Audio play error:", e);
    }
}

async function startInterview(btn, interview_type) {
    // 1. 获取输入数据
    const company = document.getElementById('company').value;
    const position = document.getElementById('position').value;
    const resumeFileInput = document.getElementById('resume-file');
    const jdFileInput = document.getElementById('jd-file');
    const this_interview_type = interview_type

    // 2. 校验
    if (!company || !position) return alert("Please fill in Company and Position.");

    // 3. UI 变为加载状态
    const originalText = btn.innerText;
    btn.innerText = "Initializing Interview...";
    btn.disabled = true;

    // 4. 构建 FormData (用于发送文件)
    const formData = new FormData();
    formData.append('company', company);
    formData.append('position', position);
    formData.append('interview_type', interview_type);
    if (resumeFileInput.files.length > 0) {
        formData.append('resume_file', resumeFileInput.files[0]);
    }
    if (jdFileInput.files.length > 0) {
        formData.append('jd_file', jdFileInput.files[0]);
    }

    try {
        // 5. 发送请求
        const res = await fetch('/start_interview', {
            method: 'POST',
            body: formData // 注意：使用 FormData 时不需要设置 Content-Type，浏览器会自动设置
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Upload failed");
        }

        const data = await res.json();

        // 6. 成功，切换界面
        history = data.history;
        renderChat();
        document.getElementById('setup-panel').classList.add('hidden');
        document.getElementById('chat-panel').classList.remove('hidden');
        startTimer();

        playAudio(data.latest_response);

    } catch (e) {
        alert("Error: " + e.message);
        btn.innerText = originalText;
        btn.disabled = false;
        console.error(e);
    }
}

function toggleRecording() {
    // 1. Check browser support
    if (!('webkitSpeechRecognition' in window)) {
        return alert("Browser not supported. Please use Chrome.");
    }

    const micBtn = document.getElementById('mic-btn');
    const inputField = document.getElementById('user-input');

    // --- STOP LOGIC ---
    if (isRecording) {
        recognition.stop(); // This triggers 'onend' automatically
        return;
    }

    // --- START LOGIC ---
    recognition = new webkitSpeechRecognition();
    recognition.lang = 'en-US';

    // 🔥 CRITICAL CHANGE: Keep recording until we say stop
    recognition.continuous = true;
    recognition.interimResults = true; // Show words as they are spoken

    // Save current text so we append to it, rather than overwriting it
    baseText = inputField.value;
    // Add a space if there is already text
    if (baseText.length > 0 && !baseText.endsWith(' ')) {
        baseText += " ";
    }

    recognition.start();

    // Update UI
    isRecording = true;
    micBtn.innerText = "🟥"; // Stop icon
    micBtn.style.background = "#dc3545"; // Red color
    inputField.placeholder = "Listening... (Click Red button to stop)";

    recognition.onresult = (event) => {
        let currentSessionTranscript = '';

        // Combine all results from this recording session
        for (let i = 0; i < event.results.length; ++i) {
            currentSessionTranscript += event.results[i][0].transcript;
        }

        // Update the textarea: Old Text + New Spoken Text
        inputField.value = baseText + currentSessionTranscript;

        // Auto-scroll to bottom
        inputField.scrollTop = inputField.scrollHeight;
    };

    recognition.onerror = (event) => {
        console.error("Speech error:", event.error);
        // Don't stop immediately on minor errors, but log them
    };

    recognition.onend = () => {
        // Reset UI when recording stops (either by user or Chrome timeout)
        isRecording = false;
        micBtn.innerText = "🎤";
        micBtn.style.background = "#28a745"; // Green color
        inputField.placeholder = "Type your answer here...";

        // Update baseText to the final result, so next time we start, we continue from here
        baseText = inputField.value;
    };
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    // 🔥 如果用户开始说话（输入），立即打断 AI 的语音
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    // 乐观更新
    history.push({ role: 'user', content: text });
    renderChat();
    input.value = '';

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ history: history, user_input: text })
        });
        const data = await res.json();
        history = data.history;
        renderChat();

        // 🔥 新增：播放 AI 的回复
        playAudio(data.latest_response);
    } catch (e) {
        console.error(e);
        alert("Connection error");
    }
}

function renderChat() {
    const chatBox = document.getElementById('chat-history');
    chatBox.innerHTML = '';
    history.filter(m => m.role !== 'system').forEach(msg => {
        const div = document.createElement('div');
        div.className = `msg ${msg.role}`;
        // 简单的换行处理
//        div.innerHTML = msg.content.replace(/\n/g, '<br>');
        if (msg.role == 'assistant'){
            div.innerHTML = 'Replied by Audio';
        } else{
            div.innerHTML = msg.content.replace(/\n/g, '<br>');
        }
        chatBox.appendChild(div);
    });
    chatBox.scrollTop = chatBox.scrollHeight;
}