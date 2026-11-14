import React, { useState } from 'react';
import { Tabs, type TabItem } from '../primitives/Tabs/Tabs';
import styles from './AppShell.module.css';

export interface AppShellProps {
  onSwitchVideo?: (url: string) => void;
  isSwitching?: boolean;
  activeTab?: 'chat' | 'transcript';
  onTabChange?: (tab: 'chat' | 'transcript') => void;
  playerPane?: React.ReactNode;
  chatPane?: React.ReactNode;
  transcriptPane?: React.ReactNode;
  onLogoClick?: () => void;
  children?: React.ReactNode;
}

const WORKSPACE_TABS: TabItem[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'transcript', label: 'Transcript' },
];

export const AppShell: React.FC<AppShellProps> = ({
  onSwitchVideo,
  isSwitching = false,
  activeTab = 'chat',
  onTabChange,
  playerPane,
  chatPane,
  transcriptPane,
  onLogoClick,
  children,
}) => {
  const [switchUrl, setSwitchUrl] = useState('');

  const handleSwitchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = switchUrl.trim();
    if (trimmed && onSwitchVideo) {
      onSwitchVideo(trimmed);
      setSwitchUrl('');
    }
  };

  const handleTabChange = (id: string) => {
    if (onTabChange && (id === 'chat' || id === 'transcript')) {
      onTabChange(id);
    }
  };

  const isDualPane = Boolean(playerPane || chatPane || transcriptPane);

  return (
    <div className={styles.shell}>
      {/* Sticky Top Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <button
            type="button"
            className={styles.wordmark}
            onClick={onLogoClick}
            aria-label="TimeSliceIQ Home"
          >
            TIMESLICEIQ
          </button>

          {onSwitchVideo && (
            <form className={styles.urlForm} onSubmit={handleSwitchSubmit} noValidate>
              <label htmlFor="header-url-input" className="sr-only">
                Switch video URL
              </label>
              <input
                id="header-url-input"
                type="url"
                className={styles.urlInput}
                placeholder="Switch video URL..."
                value={switchUrl}
                onChange={(e) => setSwitchUrl(e.target.value)}
                disabled={isSwitching}
                autoComplete="off"
                spellCheck="false"
              />
              <button
                type="submit"
                className={styles.urlSubmitBtn}
                disabled={isSwitching || !switchUrl.trim()}
                aria-busy={isSwitching}
              >
                {isSwitching ? 'Loading...' : 'Switch'}
              </button>
            </form>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      {isDualPane ? (
        <main id="main-content" tabIndex={-1} className={styles.workspace}>
          {/* Left Column (7/12 cols desktop): Video Player */}
          <div className={styles.playerColumn}>{playerPane}</div>

          {/* Right Column (5/12 cols desktop): Tabs (Chat / Transcript) */}
          <div className={styles.tabsColumn}>
            <nav className={styles.tabsHeader} aria-label="Workspace tabs">
              <Tabs
                tabs={WORKSPACE_TABS}
                activeId={activeTab}
                onChange={handleTabChange}
                ariaLabel="Workspace panels"
              />
            </nav>

            <div
              id={`tabpanel-${activeTab}`}
              role="tabpanel"
              aria-labelledby={`tab-${activeTab}`}
              tabIndex={0}
              className={styles.tabPanel}
            >
              {activeTab === 'chat' ? chatPane : transcriptPane}
            </div>
          </div>
        </main>
      ) : (
        <main id="main-content" tabIndex={-1} className={styles.mainContent}>
          {children}
        </main>
      )}
    </div>
  );
};

export default AppShell;
