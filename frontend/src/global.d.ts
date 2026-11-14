export {};

declare global {
  namespace YT {
    enum PlayerState {
      UNSTARTED = -1,
      ENDED = 0,
      PLAYING = 1,
      PAUSED = 2,
      BUFFERING = 3,
      CUED = 5,
    }

    interface PlayerVars {
      autoplay?: 0 | 1;
      cc_load_policy?: 1;
      color?: 'red' | 'white';
      controls?: 0 | 1;
      disablekb?: 0 | 1;
      enablejsapi?: 0 | 1;
      end?: number;
      fs?: 0 | 1;
      hl?: string;
      iv_load_policy?: 1 | 3;
      list?: string;
      listType?: 'playlist' | 'search' | 'user_uploads';
      loop?: 0 | 1;
      modestbranding?: 1;
      origin?: string;
      playlist?: string;
      playsinline?: 0 | 1;
      rel?: 0 | 1;
      start?: number;
      widget_referrer?: string;
      [key: string]: unknown;
    }

    interface PlayerEvents {
      onReady?: (event: { target: Player }) => void;
      onStateChange?: (event: { data: PlayerState | number; target: Player }) => void;
      onError?: (event: { data: number; target?: Player }) => void;
      onPlaybackQualityChange?: (event: { data: string; target: Player }) => void;
      onPlaybackRateChange?: (event: { data: number; target: Player }) => void;
    }

    interface PlayerOptions {
      width?: string | number;
      height?: string | number;
      videoId?: string;
      host?: string;
      playerVars?: PlayerVars;
      events?: PlayerEvents;
    }

    interface Player {
      playVideo(): void;
      pauseVideo(): void;
      stopVideo(): void;
      seekTo(seconds: number, allowSeekAhead?: boolean): void;
      getCurrentTime(): number;
      getDuration(): number;
      getPlayerState(): PlayerState | number;
      destroy(): void;
      getIframe(): HTMLIFrameElement;
      cueVideoById(videoId: string, startSeconds?: number): void;
      loadVideoById(videoId: string, startSeconds?: number): void;
    }

    interface PlayerConstructor {
      new (elementId: string | HTMLElement, options: PlayerOptions): Player;
    }
  }

  interface Window {
    onYouTubeIframeAPIReady?: () => void;
    YT?: {
      Player: YT.PlayerConstructor;
      PlayerState: typeof YT.PlayerState;
      loaded?: number;
      ready?: (callback: () => void) => void;
    };
  }

  type YTPlayer = YT.Player;
}
