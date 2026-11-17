import { db } from '../lib/firebase';
import {
  collection,
  doc,
  setDoc,
  getDoc,
  getDocs,
  deleteDoc,
  query,
  orderBy,
  limit,
} from 'firebase/firestore';

export interface SearchHistoryItem {
  videoId: string;
  title: string;
  channel?: string;
  url: string;
  timestamp: number;
}

const LOCAL_SEARCH_KEY = 'timesliceiq_search_history';
const LOCAL_CHAT_PREFIX = 'timesliceiq_chat_history_';

/** Read local storage search history safely */
function getLocalSearches(): SearchHistoryItem[] {
  try {
    const raw = localStorage.getItem(LOCAL_SEARCH_KEY);
    return raw ? (JSON.parse(raw) as SearchHistoryItem[]) : [];
  } catch {
    return [];
  }
}

/** Write local storage search history safely */
function setLocalSearches(items: SearchHistoryItem[]): void {
  try {
    localStorage.setItem(LOCAL_SEARCH_KEY, JSON.stringify(items.slice(0, 30)));
  } catch {
    // Ignore storage quota errors
  }
}

export async function saveSearchHistory(
  item: Omit<SearchHistoryItem, 'timestamp'>,
  userId?: string | null
): Promise<void> {
  const record: SearchHistoryItem = {
    ...item,
    timestamp: Date.now(),
  };

  // 1. Always update local storage
  const current = getLocalSearches().filter((s) => s.videoId !== item.videoId);
  setLocalSearches([record, ...current]);

  // 2. If user is signed in to Firebase, sync to Firestore
  if (userId && db) {
    try {
      const docRef = doc(db, 'users', userId, 'searches', item.videoId);
      await setDoc(docRef, record, { merge: true });
    } catch (err) {
      console.warn('Failed to save search history to Firestore:', err);
    }
  }
}

export async function getSearchHistory(userId?: string | null): Promise<SearchHistoryItem[]> {
  const localItems = getLocalSearches();

  if (userId && db) {
    try {
      const searchesRef = collection(db, 'users', userId, 'searches');
      const q = query(searchesRef, orderBy('timestamp', 'desc'), limit(30));
      const snapshot = await getDocs(q);
      const remoteItems: SearchHistoryItem[] = [];
      snapshot.forEach((d: { data: () => SearchHistoryItem }) => {
        remoteItems.push(d.data());
      });

      if (remoteItems.length > 0) {
        // Merge and deduplicate
        const mergedMap = new Map<string, SearchHistoryItem>();
        for (const it of [...remoteItems, ...localItems]) {
          if (!mergedMap.has(it.videoId)) {
            mergedMap.set(it.videoId, it);
          }
        }
        const merged = Array.from(mergedMap.values()).sort((a, b) => b.timestamp - a.timestamp);
        setLocalSearches(merged);
        return merged;
      }
    } catch (err) {
      console.warn('Failed to fetch search history from Firestore:', err);
    }
  }

  return localItems;
}

export async function deleteSearchHistoryItem(
  videoId: string,
  userId?: string | null
): Promise<void> {
  // 1. Remove from local storage
  const filtered = getLocalSearches().filter((s) => s.videoId !== videoId);
  setLocalSearches(filtered);
  try {
    localStorage.removeItem(`${LOCAL_CHAT_PREFIX}${videoId}`);
  } catch {
    // ignore
  }

  // 2. Remove from Firestore
  if (userId && db) {
    try {
      const docRef = doc(db, 'users', userId, 'searches', videoId);
      await deleteDoc(docRef);
      const chatDocRef = doc(db, 'users', userId, 'chats', videoId);
      await deleteDoc(chatDocRef);
    } catch (err) {
      console.warn('Failed to delete search history from Firestore:', err);
    }
  }
}

export async function saveChatHistory(
  videoId: string,
  messages: unknown[],
  userId?: string | null
): Promise<void> {
  if (!videoId) return;

  // 1. Save to local storage
  try {
    localStorage.setItem(
      `${LOCAL_CHAT_PREFIX}${videoId}`,
      JSON.stringify({ videoId, messages, updatedAt: Date.now() })
    );
  } catch {
    // ignore
  }

  // 2. Save to Firestore
  if (userId && db) {
    try {
      const docRef = doc(db, 'users', userId, 'chats', videoId);
      await setDoc(docRef, { videoId, messages, updatedAt: Date.now() }, { merge: true });
    } catch (err) {
      console.warn('Failed to save chat history to Firestore:', err);
    }
  }
}

export async function getChatHistory(
  videoId: string,
  userId?: string | null
): Promise<unknown[] | null> {
  if (!videoId) return null;

  // 1. Check local storage first for fast response
  let localMessages: unknown[] | null = null;
  try {
    const raw = localStorage.getItem(`${LOCAL_CHAT_PREFIX}${videoId}`);
    if (raw) {
      const parsed = JSON.parse(raw);
      localMessages = parsed.messages || null;
    }
  } catch {
    localMessages = null;
  }

  // 2. If logged in, fetch from Firestore
  if (userId && db) {
    try {
      const docRef = doc(db, 'users', userId, 'chats', videoId);
      const snap = await getDoc(docRef);
      if (snap.exists()) {
        const data = snap.data();
        if (Array.isArray(data.messages) && data.messages.length > 0) {
          return data.messages;
        }
      }
    } catch (err) {
      console.warn('Failed to load chat history from Firestore:', err);
    }
  }

  return localMessages;
}
