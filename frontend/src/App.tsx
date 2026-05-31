import { AppProvider } from './state/context';
import { AppLayout } from './components/layout/AppLayout';

export default function App() {
  return (
    <AppProvider>
      <AppLayout />
    </AppProvider>
  );
}
