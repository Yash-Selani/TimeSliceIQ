/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useMemo } from 'react';
import { useYouTubePlayer } from '../hooks/useYouTubePlayer';

export interface PlayerContextValue {
  isReady: boolean;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  seekTo: (seconds: number, playAfterSeek?: boolean) => void;
  containerRef: React.RefObject<HTMLDivElement>;
  videoId?: string | null;
  playVideo?: () => void;
  pauseVideo?: () => void;
  player?: YT.Player | null;
}

export const PlayerContext = createContext<PlayerContextValue | null>(null);

export interface PlayerProviderProps {
  videoId?: string | null;
  children: React.ReactNode;
}

export const PlayerProvider: React.FC<PlayerProviderProps> = ({ videoId, children }) => {
  const {
    isReady,
    currentTime,
    duration,
    isPlaying,
    seekTo,
    playVideo,
    pauseVideo,
    containerRef,
    player,
  } = useYouTubePlayer({ videoId });

  const value = useMemo<PlayerContextValue>(
    () => ({
      isReady,
      currentTime,
      duration,
      isPlaying,
      seekTo,
      containerRef,
      videoId: videoId ?? null,
      playVideo,
      pauseVideo,
      player,
    }),
    [
      isReady,
      currentTime,
      duration,
      isPlaying,
      seekTo,
      containerRef,
      videoId,
      playVideo,
      pauseVideo,
      player,
    ],
  );

  return <PlayerContext.Provider value={value}>{children}</PlayerContext.Provider>;
};

export function usePlayerContext(): PlayerContextValue {
  const context = useContext(PlayerContext);
  if (!context) {
    throw new Error(
      'usePlayerContext must be used within a <PlayerProvider>. ' +
        'Please wrap your component tree in <PlayerProvider videoId={...}> to access YouTube player state.',
    );
  }
  return context;
}
