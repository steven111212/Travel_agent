document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');

    // 監聽發送按鈕點擊事件
    sendButton.addEventListener('click', sendMessage);
    
    // 監聽輸入框按下Enter鍵事件
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // 發送訊息函數
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return; // 如果訊息為空不處理
        
        // 添加用戶訊息到聊天界面
        addMessageToChat('user', message);
        
        // 清空輸入框
        userInput.value = '';
        
        // 顯示打字指示器
        typingIndicator.style.display = 'block';
        
        // 發送請求到後端
        fetchBotResponse(message);
    }

    // 格式化天氣文本
    function formatWeatherText(text) {
        return text
            .replace(/🌡️.*\n/g, '<span style="color:#FF5722;font-weight:bold;">$&</span>') // 溫度
            .replace(/☔.*\n/g, '<span style="color:#2196F3;font-weight:bold;">$&</span>') // 降水
            .replace(/☁️.*\n/g, '<span style="color:#607D8B;font-weight:bold;">$&</span>') // 雲層
            .replace(/🌬️.*\n/g, '<span style="color:#00BCD4;font-weight:bold;">$&</span>') // 風速
            .replace(/氣溫:.*\n/g, '<span style="color:#FF5722;">$&</span>') // 溫度
            .replace(/降雨機率:.*\n/g, '<span style="color:#2196F3;">$&</span>') // 降水
            .replace(/天氣預報.*\n/g, '<span style="color:#3F51B5;font-weight:bold;font-size:1.1em;">$&</span>') // 標題
            .replace(/={3,}/g, '<span style="color:#BDBDBD;">$&</span>'); // 分隔線
    }
    
    // 格式化交通文本
    function formatTransportationText(text) {
        return text
            .replace(/📍.*\n/g, '<span style="color:#2196F3;font-weight:bold;font-size:1.1em;">$&</span>') // 藍色標題
            .replace(/選項\s\d+:.*/g, '<span style="color:#4CAF50;font-weight:bold;">$&</span>') // 綠色選項
            .replace(/⏱️.*\n/g, '<span style="color:#FF9800;">$&</span>') // 橙色時間
            .replace(/💰.*\n/g, '<span style="color:#9C27B0;">$&</span>') // 紫色費用
            .replace(/🛣️.*\n/g, '<span style="color:#607D8B;">$&</span>') // 灰色路線
            .replace(/={3,}/g, '<span style="color:#BDBDBD;">$&</span>') // 淺灰色分隔線
            .replace(/步驟 \d+:/g, '<span class="step-text">$&</span>') // 步驟文字
            .replace(/交通方式:.*/g, '<span class="transport-text">$&</span>'); // 交通方式文字
    }

    // 添加訊息到聊天界面
    function addMessageToChat(sender, message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        
        // 改進：更有效地檢測預格式化文本
        const isFormattedText = sender === 'bot' && (
            message.includes('\n') || 
            message.includes('┌') || 
            message.includes('│') || 
            message.includes('=====') ||
            message.includes('📍') ||
            message.includes('🌡️') ||
            message.includes('☔') ||
            /選項\s\d+:/.test(message) ||
            /氣溫:/.test(message)
        );
        
        if (isFormattedText) {
            // 處理格式化文本
            messageDiv.classList.add('formatted-text');
            const preElement = document.createElement('pre');
            preElement.style.margin = '0';
            preElement.style.fontFamily = 'monospace';
            preElement.style.whiteSpace = 'pre-wrap';
            preElement.style.wordBreak = 'break-word';
            
            // 檢查是否包含分隔符（意味著是複合回應）
            const hasMultipleResponses = message.includes('==============================');
            
            if (hasMultipleResponses) {
                // 分割回應並處理每個部分
                const parts = message.split('==============================');
                let processedParts = [];
                
                for (let part of parts) {
                    part = part.trim();
                    if (part) {
                        // 根據內容類型應用不同的樣式
                        if (part.includes('🌡️') || part.includes('氣溫:')) {
                            // 天氣部分的樣式
                            processedParts.push(formatWeatherText(part));
                        } else if (part.includes('📍') || part.includes('選項')) {
                            // 交通部分的樣式
                            processedParts.push(formatTransportationText(part));
                        } else {
                            // 一般文本
                            processedParts.push(part);
                        }
                    }
                }
                
                // 重新組合，使用分隔線
                preElement.innerHTML = processedParts.join('<hr style="border: 1px dashed #ccc; margin: 10px 0;">');
            } else {
                // 單一類型的回應
                if (message.includes('🌡️') || message.includes('氣溫:')) {
                    preElement.innerHTML = formatWeatherText(message);
                } else if (message.includes('📍') || message.includes('選項')) {
                    preElement.innerHTML = formatTransportationText(message);
                } else {
                    // 添加一般基本的格式
                    preElement.innerHTML = message
                        .replace(/={3,}/g, '<span style="color:#BDBDBD;">$&</span>');
                }
            }
            
            // 處理 Google Maps 連結
            preElement.innerHTML = preElement.innerHTML.replace(/Google Maps導航: (https:\/\/[^\s]+)/g, 'Google Maps導航: <a class="google-maps-link" href="$1" target="_blank">$1</a>');
            
            // 修正大眾運輸路線步驟一的空白問題
            preElement.innerHTML = preElement.innerHTML.replace(/步驟 1：\s*<br>/g, '步驟 1：');
            
            messageDiv.appendChild(preElement);
        } else {
            // 一般文本直接顯示
            messageDiv.textContent = message;
        }
        
        chatContainer.appendChild(messageDiv);
        
        // 滾動到底部
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // 向後端請求機器人回應
    function fetchBotResponse(message) {
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
        })
        .then(response => response.json())
        .then(data => {
            // 隱藏打字指示器
            typingIndicator.style.display = 'none';
            
            // 添加機器人回應到聊天界面
            addMessageToChat('bot', data.response);
        })
        .catch(error => {
            console.error('Error:', error);
            typingIndicator.style.display = 'none';
            addMessageToChat('bot', '抱歉，發生錯誤，請稍後再試。');
        });
    }
});