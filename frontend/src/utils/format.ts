/** 时间与数字格式化工具。 */

/** 绝对时间：YYYY-MM-DD HH:mm */
export function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** 相对时间：刚刚 / n分钟前 / n小时前 / 昨天 / n天前 / 日期（中文论坛常规展示） */
export function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso

  const now = Date.now()
  const diffMs = now - date.getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diffMs < minute) return '刚刚'
  if (diffMs < hour) return `${Math.floor(diffMs / minute)} 分钟前`
  if (diffMs < day) return `${Math.floor(diffMs / hour)} 小时前`

  // 昨天（自然日判断）
  const startOfToday = new Date(now)
  startOfToday.setHours(0, 0, 0, 0)
  const startOfDate = new Date(date)
  startOfDate.setHours(0, 0, 0, 0)
  const dayDiff = Math.round((startOfToday.getTime() - startOfDate.getTime()) / day)
  if (dayDiff === 1) return '昨天'
  if (dayDiff < 7) return `${dayDiff} 天前`

  return formatTime(iso).slice(0, 10)
}

/** 数字缩写：1.2万 / 3.4k / 567 */
export function formatCount(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1).replace(/\.0$/, '')}万`
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`
  return String(n)
}
