import { describe, it, expect, beforeEach } from 'vitest';
import {
  saveSearchHistory,
  getSearchHistory,
  saveChatHistory,
  getChatHistory,
  deleteSearchHistoryItem,
} from '../src/services/history';

describe('Per-User History Isolation', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('isolates search history strictly between different user accounts and guest', async () => {
    await saveSearchHistory(
      {
        videoId: 'vidA1111111',
        title: 'User A Video',
        channel: 'Channel A',
        url: 'https://www.youtube.com/watch?v=vidA1111111',
      },
      'uid-user-a'
    );

    await saveSearchHistory(
      {
        videoId: 'vidB2222222',
        title: 'User B Video',
        channel: 'Channel B',
        url: 'https://www.youtube.com/watch?v=vidB2222222',
      },
      'uid-user-b'
    );

    const historyA = await getSearchHistory('uid-user-a');
    const historyB = await getSearchHistory('uid-user-b');
    const historyC = await getSearchHistory('uid-user-c');
    const guestHistory = await getSearchHistory(null);

    expect(historyA.map((i) => i.videoId)).toEqual(['vidA1111111']);
    expect(historyB.map((i) => i.videoId)).toEqual(['vidB2222222']);
    expect(historyC).toEqual([]);
    expect(guestHistory).toEqual([]);
  });

  it('isolates chat history for the same video across different user accounts', async () => {
    const sharedVideoId = 'dQw4w9WgXcQ';

    await saveChatHistory(
      sharedVideoId,
      [{ id: '1', role: 'user', content: 'User A secret question' }],
      'uid-user-a'
    );

    await saveChatHistory(
      sharedVideoId,
      [{ id: '2', role: 'user', content: 'User B different question' }],
      'uid-user-b'
    );

    const chatA = await getChatHistory(sharedVideoId, 'uid-user-a');
    const chatB = await getChatHistory(sharedVideoId, 'uid-user-b');
    const chatC = await getChatHistory(sharedVideoId, 'uid-user-c');
    const guestChat = await getChatHistory(sharedVideoId, null);

    expect(chatA).toEqual([{ id: '1', role: 'user', content: 'User A secret question' }]);
    expect(chatB).toEqual([{ id: '2', role: 'user', content: 'User B different question' }]);
    expect(chatC).toBeNull();
    expect(guestChat).toBeNull();
  });

  it('purges legacy unscoped localStorage keys so old shared history cannot leak', async () => {
    localStorage.setItem(
      'timesliceiq_search_history',
      JSON.stringify([{ videoId: 'old12345678', title: 'Old Shared', url: 'https://youtu.be/old12345678', timestamp: 1 }])
    );
    localStorage.setItem(
      'timesliceiq_chat_history_old12345678',
      JSON.stringify({ videoId: 'old12345678', messages: [{ role: 'user', content: 'Leaked' }] })
    );

    const searches = await getSearchHistory('uid-new-user');
    const chat = await getChatHistory('old12345678', 'uid-new-user');

    expect(searches).toEqual([]);
    expect(chat).toBeNull();
    expect(localStorage.getItem('timesliceiq_search_history')).toBeNull();
    expect(localStorage.getItem('timesliceiq_chat_history_old12345678')).toBeNull();
  });

  it('deleting a video from one user does not affect another user', async () => {
    const sharedVideoId = 'abc12345678';
    await saveSearchHistory(
      { videoId: sharedVideoId, title: 'Shared', url: 'https://youtu.be/abc12345678' },
      'uid-user-a'
    );
    await saveSearchHistory(
      { videoId: sharedVideoId, title: 'Shared', url: 'https://youtu.be/abc12345678' },
      'uid-user-b'
    );
    await saveChatHistory(sharedVideoId, [{ role: 'user', content: 'A' }], 'uid-user-a');
    await saveChatHistory(sharedVideoId, [{ role: 'user', content: 'B' }], 'uid-user-b');

    await deleteSearchHistoryItem(sharedVideoId, 'uid-user-a');

    expect(await getSearchHistory('uid-user-a')).toEqual([]);
    expect(await getChatHistory(sharedVideoId, 'uid-user-a')).toBeNull();

    expect((await getSearchHistory('uid-user-b')).map((i) => i.videoId)).toEqual([sharedVideoId]);
    expect(await getChatHistory(sharedVideoId, 'uid-user-b')).toEqual([{ role: 'user', content: 'B' }]);
  });
});
