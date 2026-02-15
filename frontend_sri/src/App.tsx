import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { NotificationProvider } from './context/NotificationContext'
import { routes } from './routes'

function App() {
  return (
    <NotificationProvider>
      <AppLayout>
        <Routes>
          {routes.map(({ path, element }) => (
            <Route key={path} path={path} element={element} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </NotificationProvider>
  )
}

export default App
