import React, { useState, useEffect, useCallback } from 'react';
import { Landing } from '@/components/Landing';
import { AppShell } from '@/components/AppShell';
import { PlayerPane } from '@/components/PlayerPane';
import { PlayerProvider } from '@/contexts/PlayerContext';
import { ChatThread, type ChatMessageItem } from '@/components/ChatThread';
import { TranscriptPanel } from '@/components/TranscriptPanel';
import { LoadingState, ErrorState } from '@/components/ErrorState';
import { useIngest } from '@/hooks/useIngest';
import { useChat } from '@/hooks/useChat';
import type { IngestResponse, ChatMessage } from '@/lib/api-client';

export const App: React.FC = () => {
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
      setChatMessages([]);
      setLastQuestion('');
      setActiveTab('chat');
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
      setChatMessages((prev) => [...prev, assistantMessage]);
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
    [ingestMutation],
  );

  const handleSendMessage = useCallback(
    (question: string) => {
      if (!videoData) return;
      const userMessage: ChatMessageItem = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: question,
      };
      setChatMessages((prev) => [...prev, userMessage]);
      setLastQuestion(question);

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
    [videoData, chatMessages, chatMutation],
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
            padding: '0 var(--sp-3)',
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
            padding: '0 var(--sp-3)',
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
          <ErrorState
            code={ingestMutation.error?.code || 'INVALID_URL'}
            description={ingestMutation.error?.message}
            onRetry={() => {
              if (lastSubmittedUrl) ingestMutation.mutate(lastSubmittedUrl);
            }}
            onAction={() => {
              ingestMutation.reset();
            }}
          />
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

export default App;
