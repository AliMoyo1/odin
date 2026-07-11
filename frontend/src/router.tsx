import { createBrowserRouter, Navigate } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import AppShell from './components/AppShell'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Tasks from './pages/Tasks'
import Files from './pages/Files'
import Knowledge from './pages/Knowledge'
import Memory from './pages/Memory'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'chat',      element: <Chat /> },
      { path: 'chat/:conversationId', element: <Chat /> },
      { path: 'tasks',     element: <Tasks /> },
      { path: 'files',     element: <Files /> },
      { path: 'knowledge', element: <Knowledge /> },
      { path: 'memory',    element: <Memory /> },
    ],
  },
])
