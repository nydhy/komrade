/**
 * Geocoding via OpenStreetMap Nominatim (free, no API key).
 * Converts address strings to lat/lng coordinates.
 */

export interface GeocodeSuggestion {
  display_name: string
  lat: number
  lon: number
  type: string
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null

/**
 * Search for addresses matching a query string.
 * Debounced — safe to call on every keystroke.
 */
export function searchAddress(query: string): Promise<GeocodeSuggestion[]> {
  return new Promise((resolve) => {
    if (debounceTimer) clearTimeout(debounceTimer)
    if (query.trim().length < 3) {
      resolve([])
      return
    }
    debounceTimer = setTimeout(async () => {
      try {
        const encoded = encodeURIComponent(query.trim())
        const res = await fetch(
          `https://nominatim.openstreetmap.org/search?q=${encoded}&format=json&limit=5&addressdetails=0`,
          {
            headers: { 'Accept-Language': 'en' },
          }
        )
        if (!res.ok) {
          resolve([])
          return
        }
        const data = await res.json()
        const suggestions: GeocodeSuggestion[] = data.map(
          (item: { display_name: string; lat: string; lon: string; type: string }) => ({
            display_name: item.display_name,
            lat: parseFloat(item.lat),
            lon: parseFloat(item.lon),
            type: item.type || '',
          })
        )
        resolve(suggestions)
      } catch {
        resolve([])
      }
    }, 400)
  })
}
