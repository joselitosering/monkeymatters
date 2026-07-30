import { useEffect, useState } from 'react'

// Real client-clock countdown to the next 9:30 AM ET open, and a real market
// status derived from actual ET time — no fabricated data, just Date math.
export function useCountdown() {
  const [state, setState] = useState({ h: '00', m: '00', s: '00', etLabel: '—', status: 'Pre-Open' as 'Pre-Open' | 'Open' | 'Closed' })

  useEffect(() => {
    function tick() {
      const now = new Date()
      const etStr = now.toLocaleString('en-US', { timeZone: 'America/New_York' })
      const et = new Date(etStr)

      const timeStr = et.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) + ' ET'
      const dateStr = et.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

      const day = et.getDay()
      const minutesNow = et.getHours() * 60 + et.getMinutes()
      const isWeekday = day >= 1 && day <= 5
      const isOpen = isWeekday && minutesNow >= 570 && minutesNow < 960 // 9:30–16:00 ET
      const status: 'Pre-Open' | 'Open' | 'Closed' = isOpen ? 'Open' : isWeekday && minutesNow < 570 ? 'Pre-Open' : 'Closed'

      const target = new Date(et)
      let daysToAdd = 0
      if (day === 6) daysToAdd = 2
      else if (day === 0) daysToAdd = 1
      target.setDate(target.getDate() + daysToAdd)
      target.setHours(9, 30, 0, 0)
      let diff = target.getTime() - et.getTime()
      if (diff < 0) {
        target.setDate(target.getDate() + (day === 5 ? 3 : 1))
        diff = target.getTime() - et.getTime()
      }

      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setState({
        h: String(h).padStart(2, '0'), m: String(m).padStart(2, '0'), s: String(s).padStart(2, '0'),
        etLabel: `${dateStr} · ${timeStr}`, status,
      })
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return state
}
