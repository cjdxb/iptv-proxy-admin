/**
 * 统一的时间处理工具
 * 所有从后端接收的时间都是 UTC 时间（ISO 8601 格式 + Z 后缀）
 * 前端统一转换为本地时区显示
 */

import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import relativeTime from 'dayjs/plugin/relativeTime'
import duration from 'dayjs/plugin/duration'
import 'dayjs/locale/zh-cn'

// 配置 dayjs
dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(relativeTime)
dayjs.extend(duration)
dayjs.locale('zh-cn')

/**
 * 格式化 UTC 时间为本地时间字符串
 *
 * @param {string} utcTimeString - UTC 时间字符串（ISO 8601 格式，如 "2024-01-30T12:34:56Z"）
 * @param {string} format - 输出格式，默认 "YYYY-MM-DD HH:mm:ss"
 * @returns {string} 格式化后的本地时间字符串，如果输入无效则返回 '-'
 *
 * @example
 * formatDateTime('2024-01-30T12:34:56Z')
 * // 输出: "2024-01-30 20:34:56" (假设本地时区为 UTC+8)
 *
 * formatDateTime('2024-01-30T12:34:56Z', 'YYYY/MM/DD HH:mm')
 * // 输出: "2024/01/30 20:34" (假设本地时区为 UTC+8)
 */
export function formatDateTime(utcTimeString, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!utcTimeString) return '-'

  // 解析 UTC 时间并转换为本地时区
  const localTime = dayjs.utc(utcTimeString).local()

  if (!localTime.isValid()) {
    console.warn('Invalid UTC time string:', utcTimeString)
    return '-'
  }

  return localTime.format(format)
}

/**
 * 格式化 UTC 日期为本地日期字符串
 *
 * @param {string} utcDateString - UTC 日期字符串（ISO 8601 格式）
 * @param {string} format - 输出格式，默认 "YYYY-MM-DD"
 * @returns {string} 格式化后的本地日期字符串
 *
 * @example
 * formatDate('2024-01-30')
 * // 输出: "2024-01-30"
 */
export function formatDate(utcDateString, format = 'YYYY-MM-DD') {
  if (!utcDateString) return '-'

  const localDate = dayjs.utc(utcDateString).local()

  if (!localDate.isValid()) {
    console.warn('Invalid UTC date string:', utcDateString)
    return '-'
  }

  return localDate.format(format)
}

/**
 * 格式化 UTC 时间为本地时间字符串（包含日期和时间）
 * 与 formatDateTime 类似，但默认格式更详细
 *
 * @param {string} utcTimeString - UTC 时间字符串
 * @returns {string} 格式化后的本地时间字符串
 *
 * @example
 * formatTime('2024-01-30T12:34:56Z')
 * // 输出: "2024-01-30 20:34:56" (假设本地时区为 UTC+8)
 */
export function formatTime(utcTimeString) {
  return formatDateTime(utcTimeString, 'YYYY-MM-DD HH:mm:ss')
}

/**
 * 格式化为友好的相对时间
 *
 * @param {string} utcTimeString - UTC 时间字符串
 * @returns {string} 相对时间描述，如 "3 分钟前"、"2 小时前"
 *
 * @example
 * formatRelativeTime('2024-01-30T12:30:00Z')  // 假设现在是 12:35
 * // 输出: "5 分钟前"
 */
export function formatRelativeTime(utcTimeString) {
  if (!utcTimeString) return '-'

  const localTime = dayjs.utc(utcTimeString).local()

  if (!localTime.isValid()) {
    console.warn('Invalid UTC time string:', utcTimeString)
    return '-'
  }

  return localTime.fromNow()
}

/**
 * 计算从指定 UTC 时间到现在的持续时间
 *
 * @param {string} startTimeString - 起始 UTC 时间字符串
 * @returns {string} 持续时间描述，如 "2 小时 30 分钟"
 *
 * @example
 * getDuration('2024-01-30T10:00:00Z')  // 假设现在是 12:30
 * // 输出: "2 小时 30 分钟"
 */
export function getDuration(startTimeString) {
  if (!startTimeString) return '-'

  const startTime = dayjs.utc(startTimeString).local()
  if (!startTime.isValid()) {
    console.warn('Invalid UTC time string:', startTimeString)
    return '-'
  }

  const now = dayjs()
  const diffSeconds = now.diff(startTime, 'second')

  if (diffSeconds < 0) return '-'
  if (diffSeconds < 60) return '小于1分钟'

  const hours = Math.floor(diffSeconds / 3600)
  const minutes = Math.floor((diffSeconds % 3600) / 60)

  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分钟`
  }
  return `${minutes} 分钟`
}

/**
 * 格式化秒数为易读的时长字符串
 *
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时长字符串
 *
 * @example
 * formatDuration(3665)
 * // 输出: "1 小时 1 分钟"
 */
export function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '-'

  if (seconds < 60) return '小于1分钟'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分钟`
  }
  return `${minutes} 分钟`
}

/**
 * 获取当前本地时间的 ISO 8601 字符串（用于发送给后端）
 * 注意：通常不需要这个函数，因为后端应该自己生成时间
 *
 * @returns {string} 当前本地时间的 ISO 8601 字符串
 */
export function getCurrentTimeISO() {
  return dayjs().toISOString()
}

/**
 * 解析 UTC 时间字符串为 dayjs 对象（本地时区）
 *
 * @param {string} utcTimeString - UTC 时间字符串
 * @returns {dayjs.Dayjs|null} dayjs 对象（本地时区）或 null（如果无效）
 */
export function parseUTC(utcTimeString) {
  if (!utcTimeString) return null

  const localTime = dayjs.utc(utcTimeString).local()
  return localTime.isValid() ? localTime : null
}

// 默认导出所有函数
export default {
  formatDateTime,
  formatDate,
  formatTime,
  formatRelativeTime,
  getDuration,
  formatDuration,
  getCurrentTimeISO,
  parseUTC
}
