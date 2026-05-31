/**
 * React Context provider for the Agent visualization panel.
 *
 * Provides AppState and dispatch to the component tree via useReducer.
 */

import { createContext, useContext, useReducer } from 'react';
import type { AppState, AppAction } from './types';
import { appReducer, initialAppState } from './reducer';

interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialAppState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppState(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppState must be used within an AppProvider');
  }
  return ctx;
}
