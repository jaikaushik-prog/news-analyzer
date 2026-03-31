import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="flex bg-background min-h-screen text-slate-100 font-sans">
      <Sidebar />
      <main className="flex-1 h-screen overflow-y-auto w-full">
        <Outlet />
      </main>
    </div>
  );
}
