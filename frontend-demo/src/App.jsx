import { Route, Routes } from 'react-router-dom'
import { BusinessProvider } from './context/BusinessContext'
import RoleSelect from './pages/RoleSelect'
import CustomerDemo from './pages/customer/CustomerDemo'
import BusinessLayout from './pages/business/BusinessLayout'
import Onboarding from './pages/business/Onboarding'
import Login from './pages/business/Login'
import OnboardComplete from './pages/business/OnboardComplete'
import Overview from './pages/business/Overview'
import CasesList from './pages/business/CasesList'
import CaseDetail from './pages/business/CaseDetail'
import Invoices from './pages/business/Invoices'
import StartRecovery from './pages/business/StartRecovery'
import Settings from './pages/business/Settings'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RoleSelect />} />
      <Route path="/customer" element={<CustomerDemo />} />

      <Route
        path="/business/*"
        element={
          <BusinessProvider>
            <Routes>
              <Route path="onboard" element={<Onboarding />} />
              <Route path="login" element={<Login />} />
              <Route path="onboard/complete" element={<OnboardComplete />} />
              <Route element={<BusinessLayout />}>
                <Route index element={<Overview />} />
                <Route path="cases" element={<CasesList />} />
                <Route path="cases/:caseId" element={<CaseDetail />} />
                <Route path="invoices" element={<Invoices />} />
                <Route path="start-recovery" element={<StartRecovery />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </BusinessProvider>
        }
      />
    </Routes>
  )
}
