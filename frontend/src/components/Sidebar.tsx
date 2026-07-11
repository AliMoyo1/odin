import { NavLink } from 'react-router-dom'
import { useUIStore } from '../stores/ui'
import HermesOrb from './HermesOrb'
import LabelCaps from './LabelCaps'
import { useUIStore as _useUI } from '../stores/ui'
import { clearAccessToken } from '../lib/auth'
import { useNavigate } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/dashboard', icon: 'grid_view',   label: 'Dashboard' },
  { to: '/chat',      icon: 'forum',        label: 'Chat'      },
  { to: '/tasks',     icon: 'checklist',    label: 'Tasks'     },
  { to: '/files',     icon: 'folder_open',  label: 'Files'     },
  { to: '/knowledge', icon: 'auto_stories', label: 'Knowledge' },
  { to: '/memory',    icon: 'psychology',   label: 'Memory'    },
]

export default function Sidebar() {
  const isRunActive = useUIStore((s) => s.isRunActive)
  const setToken = _useUI((s) => s.setAccessToken)
  const navigate = useNavigate()

  async function handleLogout() {
    await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' })
    clearAccessToken()
    setToken(null)
    navigate('/login')
  }

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-[280px] bg-terminal-black border-r border-glass-border flex flex-col py-6 z-50"
      aria-label="Main navigation"
    >
      <div className="px-6 flex items-center space-x-3 mb-6">
        <HermesOrb state={isRunActive ? 'thinking' : 'idle'} size={40} />
        <div>
          <h1 className="text-headline-md font-headline-md font-bold text-primary leading-none">ODIN</h1>
          <LabelCaps className="text-on-surface-variant opacity-60">System Active</LabelCaps>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-1 overflow-y-auto" aria-label="Sections">
        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              isActive
                ? 'bg-primary-container text-on-primary-container shadow-[0_0_15px_rgba(255,107,0,0.3)] scale-95 flex items-center px-4 py-3 space-x-3 rounded-xl transition-all'
                : 'text-on-surface-variant hover:text-primary hover:bg-surface-container-high flex items-center px-4 py-3 space-x-3 rounded-xl transition-colors'
            }
            aria-label={label}
          >
            <span className="material-symbols-outlined">{icon}</span>
            <LabelCaps>{label}</LabelCaps>
          </NavLink>
        ))}

        <div
          className="text-on-surface-variant/30 flex items-center px-4 py-3 space-x-3 rounded-xl cursor-not-allowed select-none"
          aria-disabled="true"
          aria-label="Learning, coming soon"
          role="menuitem"
        >
          <span className="material-symbols-outlined">school</span>
          <LabelCaps>Learning</LabelCaps>
          <span className="ml-auto text-[9px] font-code-sm text-on-surface-variant/30 border border-on-surface-variant/20 px-1 rounded">SOON</span>
        </div>
      </nav>

      <div className="px-4 pt-4 border-t border-glass-border space-y-1 mt-2">
        <button
          onClick={handleLogout}
          className="text-on-surface-variant hover:text-status-critical flex items-center px-4 py-3 space-x-3 rounded-xl w-full transition-colors"
          aria-label="Logout"
        >
          <span className="material-symbols-outlined">logout</span>
          <LabelCaps>Logout</LabelCaps>
        </button>
      </div>
    </aside>
  )
}
