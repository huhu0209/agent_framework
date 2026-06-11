import type { CacheEntry } from '../types'

const DB_NAME = 'agent-chat-cache'
const STORE_NAME = 'messages'
const DB_VERSION = 1

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function restoreCache(): Promise<Map<string, CacheEntry>> {
  try {
    const db = await openDb()
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const keysRequest = store.getAllKeys()
      const valuesRequest = store.getAll()
      tx.oncomplete = () => {
        const map = new Map<string, CacheEntry>()
        const keys = keysRequest.result as string[]
        const values = valuesRequest.result as CacheEntry[]
        for (let i = 0; i < keys.length; i++) {
          map.set(keys[i], values[i])
        }
        db.close()
        resolve(map)
      }
      tx.onerror = () => { db.close(); resolve(new Map()) }
    })
  } catch {
    return new Map()
  }
}

export async function persistCacheEntry(sessionId: string, entry: CacheEntry): Promise<void> {
  try {
    const db = await openDb()
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      store.put({ ...entry, cachedAt: Date.now() }, sessionId)
      tx.oncomplete = () => { db.close(); resolve() }
      tx.onerror = () => { db.close(); resolve() }
    })
  } catch {
    // persistent cache failure is silent
  }
}

export async function clearStaleEntries(maxAgeMs: number): Promise<void> {
  try {
    const db = await openDb()
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      const store = tx.objectStore(STORE_NAME)
      const request = store.openCursor()
      const cutoff = Date.now() - maxAgeMs
      request.onsuccess = () => {
        const cursor = request.result
        if (cursor) {
          const entry = cursor.value as CacheEntry
          if (entry.cachedAt < cutoff) {
            cursor.delete()
          }
          cursor.continue()
        }
      }
      tx.oncomplete = () => { db.close(); resolve() }
      tx.onerror = () => { db.close(); resolve() }
    })
  } catch {
    // silent
  }
}
