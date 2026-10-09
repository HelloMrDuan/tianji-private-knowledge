/**
 * 单日黄历 — the per-day almanac facts 择日 reasons over.
 *
 * The bulk comes from `shunshi-bazi-core`'s 黄历 engine (same tyme4ts calendar core as
 * the 八字 engine, so 择日 stays in lockstep with 流日). Two things it does not expose
 * are derived here from the day's Earthly Branch: 日冲生肖 and 煞方, both fixed rules.
 */

import { getHuangli } from 'shunshi-bazi-core';
import { SolarDay } from 'tyme4ts';

const ZHI = '子丑寅卯辰巳午未申酉戌亥';
const ZODIAC = '鼠牛虎兔龙蛇马羊猴鸡狗猪';
const GAN = '甲乙丙丁戊己庚辛壬癸';

const ZHI_TO_ZODIAC: Record<string, string> = {};
for (let i = 0; i < ZHI.length; i++) ZHI_TO_ZODIAC[ZHI[i]] = ZODIAC[i];

/** 地支六冲 — the branch each one clashes with. */
const ZHI_CHONG: Record<string, string> = {
 子: '午', 午: '子', 丑: '未', 未: '丑', 寅: '申', 申: '寅',
 卯: '酉', 酉: '卯', 辰: '戌', 戌: '辰', 巳: '亥', 亥: '巳',
};

/**
 * 煞方 by the day branch's 三合 group — 申子辰煞南, 寅午戌煞北, 巳酉丑煞东, 亥卯未煞西.
 * A fixed rule, not a judgement.
 */
const SHA_DIRECTION: Record<string, string> = {
 申: '南', 子: '南', 辰: '南',
 寅: '北', 午: '北', 戌: '北',
 巳: '东', 酉: '东', 丑: '东',
 亥: '西', 卯: '西', 未: '西',
};

export interface DayInfo {
 日期: string;
 星期: string;
 农历: string;
 干支: { 年: string; 月: string; 日: string };
 节气: string | null;
 宜: string[];
 忌: string[];
 冲: {
 地支: string;
 生肖: string;
 干支: string;
 煞方: string;
 虚岁: number | null;
 };
 十二神: { 建除: string | null; 黄黑道: string | null };
 神煞: { 吉神: string[]; 凶煞: string[] };
 彭祖百忌: string[];
 二十八宿: string | null;
 吉时: string[];
 吉神方位: Record<string, string | null>;
 节日: string[];
}

/**
 * 冲煞虚岁 — the nominal age of the generation the day clashes with.
 *
 * Traditional almanacs print "冲狗 45 岁", meaning: someone born in the most recent year
 * of that 干支 (壬戌 = 1982) is 45 by Chinese reckoning this year. Returns null when the
 * clashing 干支 cannot be resolved.
 */
function chongAge(currentYear: number, chongGanzhi: string): number | null {
 if (chongGanzhi.length !== 2) return null;
 for (let y = currentYear; y > currentYear - 60; y--) {
 const gz = GAN[(((y - 4) % 10) + 10) % 10] + ZHI[(((y - 4) % 12) + 12) % 12];
 if (gz === chongGanzhi) return currentYear - y + 1; // 虚岁
 }
 return null;
}

/** The 干支 of the year that the clashing branch most recently headed. */
function chongGanzhiFor(year: number, chongZhi: string): string {
 for (let y = year; y > year - 60; y--) {
 const zhi = ZHI[(((y - 4) % 12) + 12) % 12];
 if (zhi === chongZhi) return GAN[(((y - 4) % 10) + 10) % 10] + zhi;
 }
 return '';
}

/**
 * 黄道吉时 — the hour branches whose 十二神 falls on the 黄道 side, de-duplicated in order.
 *
 * Read from tyme4ts directly rather than from the 黄历 result, which reports each hour's
 * 宜/忌 but not its 十二神. `getHours()` returns 13 entries because 子时 appears at both
 * ends of the day; de-duplicating by branch collapses that back to 12.
 */
function goodHours(year: number, month: number, day: number): string[] {
 const out: string[] = [];
 for (const h of SolarDay.fromYmd(year, month, day).getLunarDay().getHours()) {
 const star = h.getTwelveStar() as unknown as { getEcliptic(): { getName(): string } };
 if (star.getEcliptic().getName() === '黄道') {
 const z = h.getSixtyCycle().getEarthBranch().toString();
 if (!out.includes(z)) out.push(z);
 }
 }
 return out;
}

/** Full almanac facts for one Gregorian day. */
export function getDay(year: number, month: number, day: number): DayInfo {
 const h = getHuangli({ year, month, day });
 const dayGanzhi = h.干支.日;
 const dayZhi = dayGanzhi[1];
 const chongZhi = ZHI_CHONG[dayZhi];
 const chongGz = chongGanzhiFor(year, chongZhi);

 return {
 日期: `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
 星期: h.星期,
 农历: h.农历,
 干支: h.干支,
 节气: h.节气,
 宜: h.宜,
 忌: h.忌,
 冲: {
 地支: chongZhi,
 生肖: ZHI_TO_ZODIAC[chongZhi],
 干支: chongGz,
 煞方: SHA_DIRECTION[dayZhi],
 虚岁: chongAge(year, chongGz),
 },
 十二神: h.十二神,
 神煞: h.神煞,
 彭祖百忌: h.彭祖百忌,
 二十八宿: h.二十八宿,
 吉时: goodHours(year, month, day),
 吉神方位: h.吉神方位,
 节日: h.节日,
 };
}

/** Today, by the host's local date. */
export function today(): { year: number; month: number; day: number } {
 const d = new Date();
 return { year: d.getFullYear(), month: d.getMonth() + 1, day: d.getDate() };
}

/** Day-of-week index (0 = Monday ... 6 = Sunday), for the weekend filter. */
export function weekdayIndex(year: number, month: number, day: number): number {
 const w = SolarDay.fromYmd(year, month, day).getWeek().getIndex(); // 0 = Sunday
 return (w + 6) % 7;
}
