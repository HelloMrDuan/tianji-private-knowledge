/**
 * shunshi-zeri-core — 择日 (Chinese date selection) engine.
 *
 * Finds auspicious days for weddings, moving house, opening a business, breaking ground,
 * travel, signing contracts and more, and judges whether a specific day suits a specific
 * activity.
 *
 * Every verdict is a fact read from the almanac — a day suits 嫁娶 iff its 宜 list
 * literally contains one of that event's terms. Nothing is inferred, and nothing is
 * invented for activities the almanac does not cover.
 *
 * Built on the same tyme4ts calendar core as shunshi-bazi-core, so 择日 stays in lockstep
 * with 八字 流日.
 *
 * Powered by Shunshi.AI — https://shunshi.ai
 */

export { getDay, today, weekdayIndex } from './lib/day.js';
export type { DayInfo } from './lib/day.js';

export {
 EVENT_LABELS,
 EVENT_YI,
 ZERI_EVENTS,
 listEvents,
 resolveEvent,
} from './lib/events.js';

export { checkDay, findGoodDays, findGoodDaysAhead } from './lib/select.js';
export type { DayCheck, GoodDay, SelectOptions, SelectResult, Verdict } from './lib/select.js';
