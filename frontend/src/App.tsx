import React, { useState, useEffect, useCallback } from 'react';
import { Landing } from '@/components/Landing';
import { AppShell } from '@/components/AppShell';
import { PlayerPane } from '@/components/PlayerPane';
import { PlayerProvider } from '@/contexts/PlayerContext';
import { ChatThread, type ChatMessageItem } from '@/components/ChatThread';
import { TranscriptPanel } from '@/components/TranscriptPanel';
import { LoadingState, ErrorState } from '@/components/ErrorState';
import { UserMenu } from '@/components/Auth/UserMenu';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import {
  saveSearchHistory,
  getChatHistory,
  saveChatHistory,
} from '@/services/history';
import { useIngest } from '@/hooks/useIngest';
import { useChat } from '@/hooks/useChat';
import type { IngestResponse, ChatMessage } from '@/lib/api-client';

const AppContent: React.FC = () => {
  const { user } = useAuth();

  // Application State
  const [videoData, setVideoData] = useState<IngestResponse | null>(null);
  const [lastSubmittedUrl, setLastSubmittedUrl] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'chat' | 'transcript'>('chat');
  const [chatMessages, setChatMessages] = useState<ChatMessageItem[]>([]);
  const [lastQuestion, setLastQuestion] = useState<string>('');
  const [loadingStage, setLoadingStage] = useState<1 | 2 | 3>(1);

  // Ingest Mutation
  const ingestMutation = useIngest({
    onSuccess: (data) => {
      setVideoData(data);
      setActiveTab('chat');
      setLastQuestion('');

      // 1. Save to search history
      saveSearchHistory(
        {
          videoId: data.video_id,
          title: data.title,
          channel: data.channel,
          url: lastSubmittedUrl,
        },
        user ? user.uid : null
      );

      // 2. Restore previous chat history for this video if available
      getChatHistory(data.video_id, user ? user.uid : null).then((saved) => {
        if (saved && Array.isArray(saved) && saved.length > 0) {
          setChatMessages(saved as ChatMessageItem[]);
        } else {
          setChatMessages([]);
        }
      });
    },
  });

  // Chat Mutation
  const chatMutation = useChat({
    onSuccess: (response) => {
      const assistantMessage: ChatMessageItem = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        blocks: response.blocks,
        follow_ups: response.follow_ups,
      };
      setChatMessages((prev) => {
        const updated = [...prev, assistantMessage];
        if (videoData) {
          saveChatHistory(videoData.video_id, updated, user ? user.uid : null);
        }
        return updated;
      });
    },
  });

  // Advance staged loading indicator during ingest
  useEffect(() => {
    if (ingestMutation.isPending) {
      setLoadingStage(1);
      const timer = setTimeout(() => {
        setLoadingStage(2);
      }, 1800);
      return () => clearTimeout(timer);
    } else {
      setLoadingStage(1);
    }
  }, [ingestMutation.isPending]);

  // Handlers
  const handleIngest = useCallback(
    (url: string) => {
      setLastSubmittedUrl(url);
      ingestMutation.mutate(url);
    },
    [ingestMutation]
  );

  const handleSendMessage = useCallback(
    (question: string) => {
      if (!videoData) return;
      const userMessage: ChatMessageItem = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: question,
      };

      const updatedHistory = [...chatMessages, userMessage];
      setChatMessages(updatedHistory);
      setLastQuestion(question);

      // Save user question to chat history
      saveChatHistory(videoData.video_id, updatedHistory, user ? user.uid : null);

      // Build history for backend
      const history: ChatMessage[] = chatMessages
        .filter((m) => m.content || (m.blocks && m.blocks.length > 0))
        .map((m) => ({
          role: m.role,
          content: m.content || (m.blocks ? m.blocks.map((b) => b.text).join(' ') : ''),
        }));

      chatMutation.mutate({
        video_id: videoData.video_id,
        question,
        history,
      });
    },
    [videoData, chatMessages, chatMutation, user]
  );

  const handleRetryQuestion = useCallback(() => {
    if (!lastQuestion || !videoData) return;

    const history: ChatMessage[] = chatMessages
      .slice(0, -1)
      .filter((m) => m.content || (m.blocks && m.blocks.length > 0))
      .map((m) => ({
        role: m.role,
        content: m.content || (m.blocks ? m.blocks.map((b) => b.text).join(' ') : ''),
      }));

    chatMutation.mutate({
      video_id: videoData.video_id,
      question: lastQuestion,
      history,
    });
  }, [lastQuestion, videoData, chatMessages, chatMutation]);

  const handleResetToLanding = useCallback(() => {
    setVideoData(null);
    setChatMessages([]);
    setLastQuestion('');
    setLastSubmittedUrl('');
    ingestMutation.reset();
    chatMutation.reset();
  }, [ingestMutation, chatMutation]);

  // 1. Loading state when no video is loaded yet
  if (!videoData && ingestMutation.isPending) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
        <header
          style={{
            borderBottom: '1px solid var(--rule)',
            height: '56px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 var(--sp-4)',
          }}
        >
          <span
            style={{
              fontSize: 'var(--fs-lg)',
              fontWeight: 'var(--fw-semibold)',
              letterSpacing: '-0.03em',
              textTransform: 'uppercase',
            }}
          >
            TIMESLICEIQ
          </span>
          <UserMenu onSelectVideo={handleIngest} />
        </header>
        <main
          id="main-content"
          tabIndex={-1}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 'var(--sp-4)',
          }}
        >
          <LoadingState stage={loadingStage} />
        </main>
      </div>
    );
  }

  // 2. Ingest error state when no video is loaded
  if (!videoData && ingestMutation.isError) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
        <header
          style={{
            borderBottom: '1px solid var(--rule)',
            height: '56px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 var(--sp-4)',
          }}
        >
          <button
            type="button"
            onClick={handleResetToLanding}
            style={{
              fontSize: 'var(--fs-lg)',
              fontWeight: 'var(--fw-semibold)',
              letterSpacing: '-0.03em',
              textTransform: 'uppercase',
              background: 'none',
              border: 'none',
              color: 'var(--text)',
              cursor: 'pointer',
              padding: 0,
            }}
          >
            TIMESLICEIQ
          </button>
          <UserMenu onSelectVideo={handleIngest} />
        </header>
        <main
          id="main-content"
          tabIndex={-1}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 'var(--sp-4)',
          }}
        >
          {(() => {
            const err = ingestMutation.error;
            const is5xx = (err?.status && err.status >= 500) || err?.code === 'LLM_FAILED';
            return (
              <ErrorState
                code={is5xx ? 'TRANSCRIPT_BLOCKED' : (err?.code || 'INVALID_URL')}
                title={is5xx ? 'Video Ingestion Failed' : undefined}
                description={
                  err?.message ||
                  (is5xx
                    ? 'The server took too long to fetch or index this video. Please try again.'
                    : undefined)
                }
                actionLabel={is5xx ? 'Retry Video' : undefined}
                onRetry={() => {
                  if (lastSubmittedUrl) ingestMutation.mutate(lastSubmittedUrl);
                }}
                onAction={() => {
                  ingestMutation.reset();
                }}
              />
            );
          })()}
        </main>
      </div>
    );
  }

  // 3. Landing state when no video is loaded
  if (!videoData) {
    return (
      <Landing
        onSubmit={handleIngest}
        isLoading={ingestMutation.isPending}
        initialUrl={lastSubmittedUrl}
      />
    );
  }

  // 4. Workspace state when video is ingested
  return (
    <PlayerProvider videoId={videoData.video_id}>
      <AppShell
        onSwitchVideo={handleIngest}
        isSwitching={ingestMutation.isPending}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onLogoClick={handleResetToLanding}
        playerPane={
          <PlayerPane
            videoId={videoData.video_id}
            title={videoData.title}
            channel={videoData.channel}
          />
        }
        chatPane={
          <ChatThread
            messages={chatMessages}
            isLoading={chatMutation.isPending}
            error={chatMutation.error}
            onSendMessage={handleSendMessage}
            onRetry={handleRetryQuestion}
            onSelectFollowUp={handleSendMessage}
          />
        }
        transcriptPane={
          <TranscriptPanel
            transcript={videoData.transcript}
            isActiveTab={activeTab === 'transcript'}
          />
        }
      />
    </PlayerProvider>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
