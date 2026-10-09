/**
 * 择日 — picking auspicious days for an activity, and judging a specific day.
 *
 * The verdict is a fact from the almanac, not a judgement: a day suits 嫁娶 iff its 宜
 * list literally contains one of that event's keywords. Nothing here is inferred, and
 * nothing is invented for activities the almanac does not cover.
 */

import { getDay, today, weekdayIndex, type DayInfo } from './day.js';
import { EVENT_YI, ZERI_EVENTS, SPECULATION_WORDS } from './events.js';

/** Days are handled as UTC-midnight timestamps so date arithmetic never hits a DST seam. */
function toUTC(y: number, m: number, d: number): number {
 return Date.UTC(y, m - 1, d);
}

function fromUTC(ts: number): { year: number; month: number; day: number } {
 const d = new Date(ts);
 return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1, day: d.getUTCDate() };
}

const DAY_MS = 86_400_000;

export type Verdict = '宜' | '忌' | '不宜' | '未明确' | 'unknown';

export interface DayCheck {
 matched: boolean;
 activity: string;
 event: string | null;
 date: string;
 verdict: Verdict;
 宜: string[];
 忌: string[];
 冲: string;
 十二神: string;
 吉时: string[];
 说明: string;
}

/**
 * Does a specific day suit a specific activity?
 *
 * `event` is the resolved slug, or null when the activity could not be matched — in
 * which case only the day's overall 宜/忌 is reported. Making up a verdict for an
 * activity the almanac never mentions would be the one thing this tool must not do.
 */
export function checkDay(
 event: string | null,
 activity: string,
 year: number,
 month: number,
 day: number,
): DayCheck {
 const d = getDay(year, month, day);
 let verdict: Verdict = 'unknown';

 if (event) {
 const kws = EVENT_YI[event];
 if (kws.some((k) => d.宜.includes(k))) {
 verdict = '宜';
 } else if (kws.some((k) => d.忌.includes(k))) {
 verdict = '忌';
 } else if (d.宜.includes('馀事勿取') || d.宜.includes('余事勿取')) {
 // 馀事勿取 closing the 宜 list marks a 破日/weak day: only the few things listed
 // are advisable and nothing else is. Graded by stakes — contracts, investments and
 // other real undertakings get 不宜 (pick another day), while small-stakes flutters
 // are not worth holding to that standard and stay neutral.
 verdict = SPECULATION_WORDS.some((w) => activity.includes(w)) ? '未明确' : '不宜';
 } else {
 verdict = '未明确';
 }
 }

 return {
 matched: event !== null,
 activity,
 event,
 date: d.日期,
 verdict,
 宜: d.宜,
 忌: d.忌,
 冲: `冲${d.冲.生肖},煞${d.冲.煞方}方`,
 十二神: `${d.十二神.建除}(${d.十二神.黄黑道})`,
 吉时: d.吉时,
 说明:
 event === null
 ? '该事项不在可择吉清单,只能据当日整体宜忌谨慎建议,不臆造此事吉凶。'
 : 'verdict 为真值:宜/忌 = 黄历明确列出;不宜 = 当天「馀事勿取」(破日/弱日)' +
 '且此事属正经大事;未明确 = 当日宜忌未提此事(或属小额娱乐不较真),据整体吉凶谨慎说。',
 };
}

export interface GoodDay {
 日期: string;
 星期: string;
 农历: string;
 日干支: string;
 冲生肖: string;
 煞方: string;
 十二神: string;
 黄黑道: string | null;
 宜: string[];
 吉时: string[];
 /** Which of the 7 major categories this day is 宜 for */
 同宜事项: string[];
 /** Which of the 7 major categories this day is 忌 for */
 同忌事项: string[];
}

export interface SelectOptions {
 /** Keep only Saturdays and Sundays. */
 weekendOnly?: boolean;
 /**
 * Skip days that clash with these zodiac signs (i.e. the day's 冲生肖 is one of them).
 * Pass the birthday person's sign to avoid days that clash with them.
 */
 excludeZodiac?: string[];
 /** Hard cap on how many days are scanned. Default 180. */
 maxDays?: number;
 /** Stop once this many good days are found. */
 limit?: number;
}

export interface SelectResult {
 start: string;
 end: string;
 event: string;
 keywords: string[];
 excludeZodiac: string[] | null;
 weekendOnly: boolean;
 daysScanned: number;
 count: number;
 goodDays: GoodDay[];
 truncated: boolean;
}

function toGoodDay(d: DayInfo): GoodDay {
 return {
 日期: d.日期,
 星期: d.星期,
 农历: d.农历,
 日干支: d.干支.日,
 冲生肖: d.冲.生肖,
 煞方: d.冲.煞方,
 十二神: d.十二神.建除 ?? '',
 黄黑道: d.十二神.黄黑道,
 宜: d.宜,
 吉时: d.吉时,
 同宜事项: ZERI_EVENTS.filter((ev) => EVENT_YI[ev].some((k) => d.宜.includes(k))),
 同忌事项: ZERI_EVENTS.filter((ev) => EVENT_YI[ev].some((k) => d.忌.includes(k))),
 };
}

/**
 * Scan a closed date range and return every day that suits the event.
 *
 * `maxDays` is a hard stop so an over-wide range cannot turn into an unbounded scan;
 * when it truncates, the result says so rather than silently reporting fewer days.
 */
export function findGoodDays(
 event: string,
 start: { year: number; month: number; day: number },
 end: { year: number; month: number; day: number },
 opts: SelectOptions = {},
): SelectResult {
 const keywords = EVENT_YI[event];
 if (!keywords) throw new Error(`未知事项: ${event}`);

 const { weekendOnly = false, excludeZodiac = [], maxDays = 180, limit } = opts;

 let s = toUTC(start.year, start.month, start.day);
 let e = toUTC(end.year, end.month, end.day);
 if (e < s) [s, e] = [e, s];

 const spanDays = Math.floor((e - s) / DAY_MS) + 1;
 const truncated = spanDays > maxDays;
 if (truncated) e = s + (maxDays - 1) * DAY_MS;

 const exclude = new Set(excludeZodiac.map((z) => z.trim()).filter(Boolean));
 const goodDays: GoodDay[] = [];
 let scanned = 0;

 for (let ts = s; ts <= e; ts += DAY_MS) {
 const { year, month, day } = fromUTC(ts);
 scanned++;
 if (weekendOnly && weekdayIndex(year, month, day) < 5) continue;

 const d = getDay(year, month, day);
 if (exclude.size && exclude.has(d.冲.生肖)) continue;
 if (!keywords.some((k) => d.宜.includes(k))) continue;

 goodDays.push(toGoodDay(d));
 if (limit && goodDays.length >= limit) break;
 }

 const fmt = (ts: number) => {
 const { year, month, day } = fromUTC(ts);
 return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
 };

 return {
 start: fmt(s),
 end: fmt(e),
 event,
 keywords,
 excludeZodiac: exclude.size ? [...exclude].sort() : null,
 weekendOnly,
 daysScanned: scanned,
 count: goodDays.length,
 goodDays,
 truncated,
 };
}

/** Scan forward from a start date (default today) for the next N days. */
export function findGoodDaysAhead(
 event: string,
 days = 60,
 start?: { year: number; month: number; day: number },
 opts: SelectOptions = {},
): SelectResult {
 const s = start ?? today();
 const endTs = toUTC(s.year, s.month, s.day) + (days - 1) * DAY_MS;
 return findGoodDays(event, s, fromUTC(endTs), { ...opts, maxDays: Math.max(days, opts.maxDays ?? days) });
}
