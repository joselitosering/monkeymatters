import { createContext, useContext } from 'react'
import { snapshot as baseline } from './data'

export const SnapshotContext = createContext<typeof baseline>(baseline)
export function useSnapshot() {
  return useContext(SnapshotContext)
}
export const SnapshotProvider = SnapshotContext.Provider
