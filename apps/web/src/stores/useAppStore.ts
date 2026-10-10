import { create } from 'zustand';

interface AppState {
  selectedWardId: string | null;
  selectedAssessmentId: string | null;
  sidebarOpen: boolean;
  simulatorRunning: boolean;
  llmMode: 'FAST' | 'PRECISE';
  setSelectedWardId: (id: string | null) => void;
  setSelectedAssessmentId: (id: string | null) => void;
  setSidebarOpen: (open: boolean) => void;
  setSimulatorRunning: (running: boolean) => void;
  setLlmMode: (mode: 'FAST' | 'PRECISE') => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedWardId: null,
  selectedAssessmentId: null,
  sidebarOpen: true,
  simulatorRunning: false,
  llmMode: 'FAST',
  setSelectedWardId: (id) => set({ selectedWardId: id }),
  setSelectedAssessmentId: (id) => set({ selectedAssessmentId: id }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setSimulatorRunning: (running) => set({ simulatorRunning: running }),
  setLlmMode: (mode) => set({ llmMode: mode }),
}));
