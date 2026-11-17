import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { AuthModal } from './AuthModal';
import { HistoryDrawer } from '../History/HistoryDrawer';
import styles from './UserMenu.module.css';

export interface UserMenuProps {
  onSelectVideo: (url: string) => void;
}

export const UserMenu: React.FC<UserMenuProps> = ({ onSelectVideo }) => {
  const { user, isGuest, signOutUser } = useAuth();
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    setIsDropdownOpen(false);
    await signOutUser();
  };

  return (
    <>
      <div className={styles.container} ref={dropdownRef}>
        {/* History Button */}
        <button
          type="button"
          className={styles.historyBtn}
          onClick={() => setIsHistoryOpen(true)}
          aria-label="View history"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          History
        </button>

        {/* User Account / Sign In */}
        {user ? (
          <>
            <button
              type="button"
              className={styles.userPill}
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              aria-label="User menu"
            >
              {user.photoURL ? (
                <img src={user.photoURL} alt="" className={styles.avatar} />
              ) : (
                <span className={styles.avatarPlaceholder}>
                  {(user.displayName || user.email || 'U').charAt(0).toUpperCase()}
                </span>
              )}
              <span>{user.displayName || user.email?.split('@')[0]}</span>
            </button>

            {isDropdownOpen && (
              <div className={styles.dropdown}>
                <div className={styles.userEmail}>{user.email}</div>
                <button
                  type="button"
                  className={styles.dropdownItem}
                  onClick={() => {
                    setIsDropdownOpen(false);
                    setIsHistoryOpen(true);
                  }}
                >
                  Saved Videos
                </button>
                <button
                  type="button"
                  className={styles.dropdownItem}
                  onClick={handleSignOut}
                >
                  Sign Out
                </button>
              </div>
            )}
          </>
        ) : isGuest ? (
          <>
            <button
              type="button"
              className={styles.userPill}
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              aria-label="Guest user menu"
            >
              <span className={styles.avatarPlaceholder}>G</span>
              <span>Guest User</span>
            </button>

            {isDropdownOpen && (
              <div className={styles.dropdown}>
                <div className={styles.userEmail}>Local Mode (No Cloud Sync)</div>
                <button
                  type="button"
                  className={styles.dropdownItem}
                  onClick={() => {
                    setIsDropdownOpen(false);
                    setIsAuthOpen(true);
                  }}
                >
                  Sign In with Firebase
                </button>
                <button
                  type="button"
                  className={styles.dropdownItem}
                  onClick={() => {
                    setIsDropdownOpen(false);
                    setIsHistoryOpen(true);
                  }}
                >
                  Saved Videos
                </button>
                <button
                  type="button"
                  className={styles.dropdownItem}
                  onClick={handleSignOut}
                >
                  Exit Guest Mode
                </button>
              </div>
            )}
          </>
        ) : (
          <button
            type="button"
            className={styles.signInBtn}
            onClick={() => setIsAuthOpen(true)}
          >
            Sign In
          </button>
        )}
      </div>

      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectVideo={onSelectVideo}
      />
    </>
  );
};

export default UserMenu;
