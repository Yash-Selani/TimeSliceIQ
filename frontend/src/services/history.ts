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

const LEGACY_SEARCH_KEY = 'timesliceiq_search_history';
const LEGACY_CHAT_PREFIX = 'timesliceiq_chat_history_';

/** Build strictly user-scoped localStorage keys so accounts never share cached history */
function getSearchStorageKey(userId?: string | null): string {
  return userId ? `timesliceiq_u_${userId}_searches` : 'timesliceiq_guest_searches';
}

function getChatStorageKey(videoId: string, userId?: string | null): string {
  return userId
    ? `timesliceiq_u_${userId}_chat_${videoId}`
    : `timesliceiq_guest_chat_${videoId}`;
}

/** Strip undefined values so Firestore setDoc never rejects a write */
function sanitizeForFirestore<T>(data: T): T {
  return JSON.parse(JSON.stringify(data)) as T;
}

/** Remove legacy unscoped keys left over from earlier builds so they cannot leak across users */
export function purgeLegacyUnscopedHistory(): void {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    localStorage.removeItem(LEGACY_SEARCH_KEY);
    const keysToDelete: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith(LEGACY_CHAT_PREFIX)) {
        keysToDelete.push(k);
      }
    }
    for (const k of keysToDelete) {
      localStorage.removeItem(k);
    }
  } catch {
    // ignore storage errors
  }
}

/** Read strictly scoped local search history */
function getLocalSearches(userId?: string | null): SearchHistoryItem[] {
  try {
    const raw = localStorage.getItem(getSearchStorageKey(userId));
    return raw ? (JSON.parse(raw) as SearchHistoryItem[]) : [];
  } catch {
    return [];
  }
}

/** Write strictly scoped local search history */
function setLocalSearches(items: SearchHistoryItem[], userId?: string | null): void {
  try {
    localStorage.setItem(getSearchStorageKey(userId), JSON.stringify(items.slice(0, 30)));
  } catch {
    // Ignore storage quota errors
  }
}

/** Read strictly scoped local chat history */
function getLocalChat(videoId: string, userId?: string | null): unknown[] | null {
  try {
    const raw = localStorage.getItem(getChatStorageKey(videoId, userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed?.messages) ? parsed.messages : null;
  } catch {
    return null;
  }
}

/** Write strictly scoped local chat history */
function setLocalChat(videoId: string, messages: unknown[], userId?: string | null): void {
  try {
    localStorage.setItem(
      getChatStorageKey(videoId, userId),
      JSON.stringify({ videoId, messages, updatedAt: Date.now() })
    );
  } catch {
    // ignore
  }
}

export async function saveSearchHistory(
  item: Omit<SearchHistoryItem, 'timestamp'>,
  userId?: string | null
): Promise<void> {
  purgeLegacyUnscopedHistory();

  const record: SearchHistoryItem = sanitizeForFirestore({
    videoId: item.videoId,
    title: item.title,
    channel: item.channel || 'YouTube',
    url: item.url,
    timestamp: Date.now(),
  });

  // 1. Update strictly scoped local cache for this user/guest only
  const current = getLocalSearches(userId).filter((s) => s.videoId !== item.videoId);
  setLocalSearches([record, ...current], userId);

  // 2. If signed in to Firebase, persist under users/{userId}/searches/{videoId}
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
  purgeLegacyUnscopedHistory();

  // Signed-in Firebase user: Firestore is the authoritative per-user source of truth.
  // Never merge with guest or another user's localStorage.
  if (userId && db) {
    try {
      const searchesRef = collection(db, 'users', userId, 'searches');
      const q = query(searchesRef, orderBy('timestamp', 'desc'), limit(30));
      const snapshot = await getDocs(q);
      const remoteItems: SearchHistoryItem[] = [];
      snapshot.forEach((d: { data: () => SearchHistoryItem }) => {
        remoteItems.push(d.data());
      });

      const sorted = remoteItems.sort((a, b) => b.timestamp - a.timestamp);
      // Sync this user's own scoped cache to match Firestore exactly (including empty [])
      setLocalSearches(sorted, userId);
      return sorted;
    } catch (err) {
      console.warn('Failed to fetch search history from Firestore, using user-scoped cache:', err);
      return getLocalSearches(userId);
    }
  }

  // Fallback / Guest mode: strictly scoped localStorage (user-scoped if userId set, else guest-scoped)
  return getLocalSearches(userId);
}

export async function deleteSearchHistoryItem(
  videoId: string,
  userId?: string | null
): Promise<void> {
  // 1. Remove from strictly scoped local cache
  const filtered = getLocalSearches(userId).filter((s) => s.videoId !== videoId);
  setLocalSearches(filtered, userId);
  try {
    localStorage.removeItem(getChatStorageKey(videoId, userId));
  } catch {
    // ignore
  }

  // 2. Remove from this user's Firestore collections
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
  purgeLegacyUnscopedHistory();

  const cleanMessages = sanitizeForFirestore(messages);

  // 1. Save to strictly scoped local cache for this user/guest only
  setLocalChat(videoId, cleanMessages, userId);

  // 2. If signed in to Firebase, save under users/{userId}/chats/{videoId}
  if (userId && db) {
    try {
      const docRef = doc(db, 'users', userId, 'chats', videoId);
      await setDoc(
        docRef,
        {
          videoId,
          userId,
          messages: cleanMessages,
          updatedAt: Date.now(),
        },
        { merge: true }
      );
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
  purgeLegacyUnscopedHistory();

  // Signed-in Firebase user: Firestore users/{userId}/chats/{videoId} is authoritative.
  // If this user has no chat document for this video, return null (never leak another user's chat).
  if (userId && db) {
    try {
      const docRef = doc(db, 'users', userId, 'chats', videoId);
      const snap = await getDoc(docRef);
      if (snap.exists()) {
        const data = snap.data();
        if (Array.isArray(data.messages) && data.messages.length > 0) {
          setLocalChat(videoId, data.messages, userId);
          return data.messages;
        }
      }
      // This user has no saved chat for this video in Firestore
      try {
        localStorage.removeItem(getChatStorageKey(videoId, userId));
      } catch {
        // ignore
      }
      return null;
    } catch (err) {
      console.warn('Failed to load chat history from Firestore, using user-scoped cache:', err);
      return getLocalChat(videoId, userId);
    }
  }

  // Fallback / Guest mode: strictly scoped localStorage (user-scoped if userId set, else guest-scoped)
  return getLocalChat(videoId, userId);
}
