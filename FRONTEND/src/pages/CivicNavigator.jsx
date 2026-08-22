import React, { useState, useRef, useEffect } from 'react';
import { Scale, AlertCircle, FileText, CheckSquare, Building } from 'lucide-react';
import WorkspaceContainer from '../components/common/WorkspaceContainer';
import ConversationLayout from '../components/chat/ConversationLayout';
import ChatInput from '../components/chat/ChatInput';
import MessageBubble from '../components/chat/MessageBubble';
import { askCivicStream } from '../services/civicService';
import { useAuth } from '../contexts/AuthContext';
import ReactMarkdown from 'react-markdown';

import ExpandableSource from '../components/kanoon/ExpandableSource';

// Component to render the streamed or completed civic response
const CivicRenderer = ({ content, isStreaming }) => {
  // If it's a completed JSON string, try to parse it. Otherwise, it's raw streamed text.
  let displayContent = content;
  let citations = null;
  let sources = [];

  if (!isStreaming) {
    try {
      const parsed = JSON.parse(content);
      displayContent = parsed.answer || content;
      citations = parsed.similar_cases;
      sources = parsed.sources || [];
    } catch (e) {
      // It's just text
    }
  }

  return (
    <div className="flex flex-col gap-4 w-full text-text-primary text-[15px] leading-relaxed">
      <div className="prose prose-sm md:prose-base max-w-none prose-headings:font-semibold prose-a:text-primary prose-a:no-underline hover:prose-a:underline">
        <ReactMarkdown>{displayContent}</ReactMarkdown>
      </div>
      
      {citations && citations.length > 0 && (
        <div className="mt-6 p-4 bg-surface rounded-xl border border-border shadow-sm">
          <div className="flex items-center gap-2 mb-3 text-primary font-medium">
            <Building className="w-5 h-5" />
            <span>Similar Cases</span>
          </div>
          <div className="prose prose-sm max-w-none text-text-secondary">
            <ReactMarkdown>{citations}</ReactMarkdown>
          </div>
        </div>
      )}

      {sources && sources.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center gap-2 mb-4 text-primary font-medium">
            <Scale className="w-5 h-5" />
            <span>Sources & Authorities</span>
          </div>
          <div>
            {sources.map((source, idx) => (
              <ExpandableSource key={idx} source={source} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const CivicChatArea = ({ refreshConversations }) => {
  const { currentUser } = useAuth();
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isGenerating) return;
    
    const userMessage = { role: 'user', content: inputValue.trim() };
    setMessages(prev => [...prev, userMessage, { role: 'assistant', content: '', streaming: true }]);
    setInputValue('');
    setIsGenerating(true);
    setError(null);
    
    try {
      const payload = {
        question: userMessage.content,
        conversation_id: activeConversationId
      };

      await askCivicStream(
        payload,
        (msg) => {
          if (msg.type === 'metadata') {
            if (!activeConversationId && msg.conversation_id) {
              setActiveConversationId(msg.conversation_id);
              if (refreshConversations) refreshConversations();
            }
          } else if (msg.type === 'content') {
            setMessages(prev => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], content: msg.text };
              return newMsgs;
            });
          }
        },
        (completeData) => {
           // We store the full JSON so it renders citations properly on completion
           const finalJson = JSON.stringify({
               answer: completeData.text,
               sources: completeData.citations || []
           });
           setMessages(prev => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1] = { role: 'assistant', content: finalJson, streaming: false };
              return newMsgs;
           });
           setIsGenerating(false);
        },
        (err) => {
           setError(err || 'Failed to generate response.');
           setIsGenerating(false);
           // Remove the streaming message if it failed completely and is empty
           setMessages(prev => {
              const newMsgs = [...prev];
              if (newMsgs[newMsgs.length - 1].streaming && !newMsgs[newMsgs.length - 1].content) {
                  return newMsgs.slice(0, -1);
              }
              return newMsgs;
           });
        }
      );
      
    } catch (err) {
      setError(err.message || 'Failed to get an answer. Please try again.');
      setIsGenerating(false);
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setInputValue('');
    setError(null);
  };

  const handleSelectConversation = (conv) => {
    setActiveConversationId(conv.id);
  };

  const handleMessagesLoaded = (loadedMessages) => {
    setMessages(loadedMessages);
  };

  const EXAMPLE_QUESTIONS = [
    "I want to file RTI about road repair funds in my ward",
    "Bought a phone online, arrived broken, seller ignores me",
    "My landlord won't return my security deposit",
  ];

  return (
    <ConversationLayout
      featureType="know_kanoon"
      activeConversationId={activeConversationId}
      onNewChat={handleNewChat}
      onSelectConversation={handleSelectConversation}
      onMessagesLoaded={handleMessagesLoaded}
    >
      <div className="flex flex-col h-full bg-surface relative">
        <header className="h-16 flex items-center px-6 border-b border-border bg-surface/80 backdrop-blur-sm z-10 shrink-0">
          <div className="flex items-center gap-3 md:ml-12">
            <div className="p-1.5 bg-primary/10 rounded-button border border-primary/20">
              <Scale className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-text-primary tracking-tight leading-tight">Civic Navigator</h1>
              <p className="text-xs text-text-secondary">From problem to legal action in seconds</p>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto bg-background relative scroll-smooth scrollbar-thin scrollbar-thumb-border">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto p-6">
              <div className="w-16 h-16 bg-surface rounded-2xl shadow-sm border border-border flex items-center justify-center mb-6">
                <Scale className="w-8 h-8 text-primary" />
              </div>
              <h2 className="text-xl font-semibold text-text-primary mb-2">Resolve Civic & Consumer Issues</h2>
              <p className="text-text-secondary text-sm mb-8">
                Get step-by-step action plans, required evidence checklists, and the exact authorities to approach.
              </p>
              <div className="flex flex-col gap-2 w-full max-w-sm">
                {EXAMPLE_QUESTIONS.map((q, idx) => (
                  <button 
                    key={idx}
                    onClick={() => setInputValue(q)} 
                    className="text-sm bg-surface hover:bg-secondary border border-border px-4 py-3 rounded-xl text-text-primary text-left transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="pb-32">
              {messages.map((msg, idx) => (
                <MessageBubble 
                  key={idx} 
                  message={msg} 
                  renderContent={msg.role === 'assistant' ? (content) => <CivicRenderer content={content} isStreaming={msg.streaming} /> : null}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background to-transparent pt-10 pb-6 px-4 md:px-8 z-10 pointer-events-none">
          <div className="max-w-4xl mx-auto w-full pointer-events-auto">
            {error && (
              <div className="mb-4 p-3 bg-error-bg border border-error/50 rounded-lg flex items-center gap-2 text-error text-sm shadow-sm">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}
            <ChatInput 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onSubmit={handleSendMessage}
              isLoading={isGenerating}
              placeholder="E.g., I bought a defective phone and the seller won't refund me..."
            />
          </div>
        </div>
      </div>
    </ConversationLayout>
  );
};

const CivicNavigator = () => {
  return (
    <WorkspaceContainer>
      <CivicChatArea />
    </WorkspaceContainer>
  );
};

export default CivicNavigator;
