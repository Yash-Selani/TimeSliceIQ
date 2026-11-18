import React, { useEffect, useState } from 'react';
import {
  getSearchHistory,
  deleteSearchHistoryItem,
  type SearchHistoryItem,
} from '../../services/history';
import { useAuth } from '../../contexts/AuthContext';
import styles from './HistoryDrawer.module.css';

export interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectVideo: (url: string) => void;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  onSelectVideo,
}) => {
  const { user } = useAuth();
  const [historyItems, setHistoryItems] = useState<SearchHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  const userId = user ? user.uid : null;

  useEffect(() => {
    // Immediately clear stale items whenever the active user changes
    setHistoryItems([]);
    if (!isOpen) return;

    let cancelled = false;
    setLoading(true);
    getSearchHistory(userId)
      .then((items) => {
        if (!cancelled) {
          setHistoryItems(items);
        }
      })
      .catch((err) => console.warn('Failed to load history:', err))
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, userId]);

  if (!isOpen) return null;

  const handleDelete = async (e: React.MouseEvent, videoId: string) => {
    e.stopPropagation();
    await deleteSearchHistoryItem(videoId, user ? user.uid : null);
    setHistoryItems((prev) => prev.filter((i) => i.videoId !== videoId));
  };

  const handleSelect = (url: string) => {
    onSelectVideo(url);
    onClose();
  };

  return (
    <div className={styles.backdrop} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.drawer} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>History & Saved Videos</h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Close history"
          >
            ✕
          </button>
        </div>

        <div className={styles.list}>
          {loading ? (
            <div className={styles.emptyState}>Loading history...</div>
          ) : historyItems.length === 0 ? (
            <div className={styles.emptyState}>
              No analyzed videos yet. Videos you analyze and their chat conversations will appear here.
            </div>
          ) : (
            historyItems.map((item) => (
              <div
                key={item.videoId}
                className={styles.item}
                onClick={() => handleSelect(item.url)}
                role="button"
                tabIndex={0}
              >
                <img
                  src={`https://i.ytimg.com/vi/${item.videoId}/hqdefault.jpg`}
                  alt=""
                  className={styles.thumbnail}
                  loading="lazy"
                />
                <div className={styles.itemInfo}>
                  <div className={styles.itemTitle} title={item.title}>
                    {item.title}
                  </div>
                  <div className={styles.itemMeta}>
                    {item.channel || 'YouTube'} · {new Date(item.timestamp).toLocaleDateString()}
                  </div>
                </div>
                <button
                  type="button"
                  className={styles.deleteBtn}
                  onClick={(e) => handleDelete(e, item.videoId)}
                  title="Remove from history"
                  aria-label="Remove item"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryDrawer;
