import { lazy, Suspense } from 'react'
import { ProtectedRoute } from '../components/ProtectedRoute'

const Dashboard = lazy(() => import('../pages/Dashboard'))
const Login = lazy(() => import('../pages/Login'))
const Register = lazy(() => import('../pages/Register'))
const Buddies = lazy(() => import('../pages/Buddies'))
const BuddyInbox = lazy(() => import('../pages/BuddyInbox'))
const Settings = lazy(() => import('../pages/Settings'))
const Profile = lazy(() => import('../pages/Profile'))
const BuddyMap = lazy(() => import('../pages/BuddyMap'))
const SosHistory = lazy(() => import('../pages/SosHistory'))

export const routes = [
  {
    path: '/',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      </Suspense>
    ),
  },
  {
    path: '/login',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <Login />
      </Suspense>
    ),
  },
  {
    path: '/register',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <Register />
      </Suspense>
    ),
  },
  {
    path: '/buddies',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <ProtectedRoute>
          <Buddies />
        </ProtectedRoute>
      </Suspense>
    ),
  },
  {
    path: '/inbox',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <ProtectedRoute>
          <BuddyInbox />
        </ProtectedRoute>
      </Suspense>
    ),
  },
  {
    path: '/settings',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <ProtectedRoute>
          <Settings />
        </ProtectedRoute>
      </Suspense>
    ),
  },
  {
    path: '/profile',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <ProtectedRoute>
          <Profile />
        </ProtectedRoute>
      </Suspense>
    ),
  },
  {
    path: '/sos-history',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <ProtectedRoute>
          <SosHistory />
        </ProtectedRoute>
      </Suspense>
    ),
  },
  {
    path: '/map',
    element: (
      <Suspense fallback={<div>Loading...</div>}>
        <ProtectedRoute>
          <BuddyMap />
        </ProtectedRoute>
      </Suspense>
    ),
  },
]
