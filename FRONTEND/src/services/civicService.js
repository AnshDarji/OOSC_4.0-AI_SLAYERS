import api from './api';

export const askCivicStream = async (payload, onMessage, onComplete, onError) => {
    try {
        let token = localStorage.getItem('token');
        if (!token) {
            console.warn("No token found, falling back to mock-token for development");
            token = "mock-token";
        }

        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/api/kanoon/query-stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;

        let accumulatedText = "";
        
        while (!done) {
            const { value, done: doneReading } = await reader.read();
            done = doneReading;
            
            if (value) {
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            if (data.type === 'status') {
                                onMessage({ type: 'status', text: data.data });
                            } else if (data.type === 'chunk') {
                                accumulatedText += data.data;
                                onMessage({ type: 'content', text: accumulatedText });
                            } else if (data.type === 'complete') {
                                onComplete({
                                    text: accumulatedText,
                                    citations: data.citations,
                                    metrics: data.metrics
                                });
                            } else if (data.type === 'error') {
                                onError(data.data);
                            } else if (data.type === 'metadata') {
                                onMessage({ type: 'metadata', conversation_id: data.conversation_id });
                            }
                        } catch (e) {
                            console.error("Failed to parse SSE data:", e);
                        }
                    }
                }
            }
        }
    } catch (err) {
        console.error("Civic stream error:", err);
        onError(err.message || "Connection failed");
    }
};
