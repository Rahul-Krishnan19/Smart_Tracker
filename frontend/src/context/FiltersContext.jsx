import { createContext, useContext, useState } from 'react'
import { format, startOfMonth, endOfMonth } from 'date-fns'

const today = new Date()
const defaultTxFilters = {
  date_from: format(startOfMonth(today), 'yyyy-MM-dd'),
  date_to: format(endOfMonth(today), 'yyyy-MM-dd'),
  category: '',
  payment_method: '',
  payment_source: '',
  search: '',
  min_amount: '',
  max_amount: '',
}

const defaultAnalyticsFilters = {
  date_from: format(startOfMonth(today), 'yyyy-MM-dd'),
  date_to: format(endOfMonth(today), 'yyyy-MM-dd'),
  category: '',
  payment_source: '',
  search: '',
  min_amount: '',
  max_amount: '',
}

const FiltersContext = createContext(null)

export function FiltersProvider({ children }) {
  const [txFilters, setTxFilters] = useState(defaultTxFilters)
  const [analyticsFilters, setAnalyticsFilters] = useState(defaultAnalyticsFilters)
  return (
    <FiltersContext.Provider value={{ txFilters, setTxFilters, analyticsFilters, setAnalyticsFilters }}>
      {children}
    </FiltersContext.Provider>
  )
}

export function useFilters() {
  return useContext(FiltersContext)
}
