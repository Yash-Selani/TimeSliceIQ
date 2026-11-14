import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Singleton promise for idempotent YouTube IFrame API script loading.
 */
let apiLoadingPromise: Promise<void> | null = null;

export function loadYouTubeIFrameAPI(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.resolve();
  }

  // Already initialized and ready
  if (window.YT && window.YT.Player) {
    return Promise.resolve();
  }

  if (apiLoadingPromise) {
    return apiLoadingPromise;
  }

  apiLoadingPromise = new Promise<void>((resolve, reject) => {
    // Check if script element already exists
    const existingScript = document.querySelector<HTMLScriptElement>(
      'script[src*="youtube.com/iframe_api"]',
    );

    const prevReady = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      if (typeof prevReady === 'function') {
        try {
          prevReady();
        } catch (e) {
          console.error('Error in previous onYouTubeIframeAPIReady:', e);
        }
      }
      resolve();
    };

    if (!existingScript) {
      const script = document.createElement('script');
      script.src = 'https://www.youtube.com/iframe_api';
      script.async = true;
      script.onerror = (err) => {
        apiLoadingPromise = null;
        reject(new Error(`Failed to load YouTube IFrame API: ${String(err)}`));
      };

      const firstScript = document.getElementsByTagName('script')[0];
      if (firstScript && firstScript.parentNode) {
        firstScript.parentNode.insertBefore(script, firstScript);
      } else {
        document.head.appendChild(script);
      }
    }
  });

  return apiLoadingPromise;
}

export interface UseYouTubePlayerOptions {
  videoId?: string | null;
  containerRef?: React.RefObject<HTMLDivElement>;
  onReady?: (player: YT.Player) => void;
  onStateChange?: (state: YT.PlayerState | number) => void;
}

export interface UseYouTubePlayerReturn {
  isReady: boolean;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  seekTo: (seconds: number, playAfterSeek?: boolean) => void;
  playVideo: () => void;
  pauseVideo: () => void;
  containerRef: React.RefObject<HTMLDivElement>;
  player: YT.Player | null;
}

export function useYouTubePlayer(
  optionsOrVideoId?: UseYouTubePlayerOptions | string | null,
): UseYouTubePlayerReturn {
  const options: UseYouTubePlayerOptions =
    typeof optionsOrVideoId === 'string'
      ? { videoId: optionsOrVideoId }
      : (optionsOrVideoId ?? {});

  const { videoId } = options;

  const internalContainerRef = useRef<HTMLDivElement>(null);
  const containerRef = options.containerRef || internalContainerRef;

  const playerRef = useRef<YT.Player | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const [isReady, setIsReady] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Play / Pause controls
  const playVideo = useCallback(() => {
    if (playerRef.current) {
      try {
        playerRef.current.playVideo();
      } catch (err) {
        console.warn('YouTube Player playVideo failed:', err);
      }
    }
  }, []);

  const pauseVideo = useCallback(() => {
    if (playerRef.current) {
      try {
        playerRef.current.pauseVideo();
      } catch (err) {
        console.warn('YouTube Player pauseVideo failed:', err);
      }
    }
  }, []);

  // Method seekTo(seconds: number, playAfterSeek: boolean = true)
  // Calls player.seekTo(seconds, true)
  // If playAfterSeek, calls player.playVideo()
  // Updates currentTime optimistically
  const seekTo = useCallback((seconds: number, playAfterSeek: boolean = true) => {
    const targetSeconds = Math.max(0, seconds);
    setCurrentTime(targetSeconds);

    if (playerRef.current) {
      try {
        playerRef.current.seekTo(targetSeconds, true);
        if (playAfterSeek) {
          playerRef.current.playVideo();
        }
      } catch (err) {
        console.warn('YouTube Player seekTo failed:', err);
      }
    }
  }, []);

  // Lifecycle: Initialize or update player when videoId changes
  useEffect(() => {
    const activeContainer = containerRef.current;

    if (!videoId) {
      if (playerRef.current) {
        try {
          playerRef.current.destroy();
        } catch {
          // ignore
        }
        playerRef.current = null;
      }
      setIsReady(false);
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(0);
      return;
    }

    let isCancelled = false;
    let rAFId: number | null = null;
    let retryCount = 0;
    let mountedContainer: HTMLDivElement | null = activeContainer;

    const initPlayer = () => {
      if (isCancelled) return;

      const container = containerRef.current || activeContainer;
      if (!container) {
        if (retryCount < 30) {
          retryCount += 1;
          rAFId = window.requestAnimationFrame(initPlayer);
        }
        return;
      }
      mountedContainer = container;

      loadYouTubeIFrameAPI()
        .then(() => {
          if (isCancelled) return;
          const targetContainer = container;
          if (!targetContainer) return;

          // Destroy existing player instance if any
          if (playerRef.current) {
            try {
              playerRef.current.destroy();
            } catch {
              // ignore
            }
            playerRef.current = null;
          }

          // Clear container and create mount slot
          targetContainer.innerHTML = '';
          const slot = document.createElement('div');
          targetContainer.appendChild(slot);

          const player = new window.YT!.Player(slot, {
            videoId,
            width: '100%',
            height: '100%',
            host: 'https://www.youtube-nocookie.com',
            playerVars: {
              autoplay: 0,
              playsinline: 1,
              rel: 0,
              modestbranding: 1,
              enablejsapi: 1,
              origin: typeof window !== 'undefined' ? window.location.origin : undefined,
            },
            events: {
              onReady: (event) => {
                if (isCancelled) return;
                playerRef.current = event.target;
                setIsReady(true);
                try {
                  const dur = event.target.getDuration();
                  if (typeof dur === 'number' && dur > 0) {
                    setDuration(dur);
                  }
                } catch {
                  // ignore
                }
                optionsRef.current.onReady?.(event.target);
              },
              onStateChange: (event) => {
                if (isCancelled) return;
                const state = event.data;
                const playing = state === 1; // YT.PlayerState.PLAYING
                setIsPlaying(playing);

                if (playing) {
                  try {
                    const time = event.target.getCurrentTime();
                    if (typeof time === 'number' && !Number.isNaN(time)) {
                      setCurrentTime(time);
                    }
                    const dur = event.target.getDuration();
                    if (typeof dur === 'number' && dur > 0) {
                      setDuration(dur);
                    }
                  } catch {
                    // ignore
                  }
                }
                optionsRef.current.onStateChange?.(state);
              },
              onError: (event) => {
                console.warn('YouTube Player error code:', event.data);
              },
            },
          });

          playerRef.current = player;
        })
        .catch((err) => {
          if (!isCancelled) {
            console.error('Error initializing YouTube player:', err);
          }
        });
    };

    initPlayer();

    return () => {
      isCancelled = true;
      if (rAFId !== null) {
        window.cancelAnimationFrame(rAFId);
      }
      if (playerRef.current) {
        try {
          playerRef.current.destroy();
        } catch {
          // ignore
        }
        playerRef.current = null;
      }
      if (mountedContainer) {
        mountedContainer.innerHTML = '';
      }
      setIsReady(false);
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(0);
    };
  }, [videoId, containerRef]);

  // Polling: Poll getCurrentTime() every 250ms ONLY while playing
  useEffect(() => {
    if (!isPlaying || !isReady) {
      return;
    }

    const intervalId = window.setInterval(() => {
      if (playerRef.current) {
        try {
          const time = playerRef.current.getCurrentTime();
          if (typeof time === 'number' && !Number.isNaN(time)) {
            setCurrentTime(time);
          }
          const dur = playerRef.current.getDuration();
          if (typeof dur === 'number' && !Number.isNaN(dur) && dur > 0) {
            setDuration(dur);
          }
        } catch {
          // Player state might be transitioning
        }
      }
    }, 250);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isPlaying, isReady]);

  return {
    isReady,
    currentTime,
    duration,
    isPlaying,
    seekTo,
    playVideo,
    pauseVideo,
    containerRef,
    player: playerRef.current,
  };
}
