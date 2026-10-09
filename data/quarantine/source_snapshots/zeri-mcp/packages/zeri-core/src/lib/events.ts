/**
 * 择日事项 — the activity whitelist and the almanac keywords each one matches.
 *
 * Whether a day suits an activity is decided by whether the almanac's 宜 (recommends)
 * list literally contains one of that activity's keywords. That is a fact from the
 * calendar engine, not a judgement — which is the whole point: no model is asked to
 * decide whether a Tuesday is good for a wedding.
 */

/** 事项 slug → the almanac terms that count as a match. */
export const EVENT_YI: Record<string, string[]> = {
 wedding: ['嫁娶', '结婚', '纳采', '订盟'], // 结婚吉日
 moving: ['入宅', '移徙', '搬家'], // 搬家吉日
 opening: ['开市', '开业', '开张'], // 开业吉日
 travel: ['出行', '远行'], // 出行吉日
 groundbreaking: ['动土', '破土', '修造'], // 动土吉日
 praying: ['祭祀', '祈福', '斋醮'], // 祈福吉日
 contract: ['立券', '交易', '纳财'], // 签约吉日
 bed: ['安床'], // 安床(婚育 / 健康)
 healing: ['求医', '治病'], // 就医
 schooling: ['入学'], // 入学
};

/**
 * Natural-language activity words → slug. Tried exact first, then fuzzy.
 *
 * Speculative and financial activities (lottery, stocks, investment) are all really
 * 交易/纳财 and map to `contract`; the verdict still comes from whether the day suits
 * trading, and the tool description adds a note about not encouraging speculation.
 */
export const EVENT_ALIAS: Record<string, string> = {
 结婚: 'wedding', 嫁娶: 'wedding', 领证: 'wedding', 订婚: 'wedding', 婚礼: 'wedding',
 搬家: 'moving', 入宅: 'moving', 乔迁: 'moving', 移徙: 'moving', 入伙: 'moving', 搬迁: 'moving',
 开业: 'opening', 开市: 'opening', 开张: 'opening', 开店: 'opening',
 出行: 'travel', 远行: 'travel', 旅行: 'travel', 出差: 'travel',
 动土: 'groundbreaking', 破土: 'groundbreaking', 修造: 'groundbreaking',
 装修: 'groundbreaking', 盖房: 'groundbreaking', 开工: 'groundbreaking',
 祈福: 'praying', 祭祀: 'praying', 斋醮: 'praying', 拜拜: 'praying', 上香: 'praying',
 签约: 'contract', 立券: 'contract', 交易: 'contract', 纳财: 'contract',
 签合同: 'contract', 提车: 'contract',
 投资: 'contract', 理财: 'contract', 炒股: 'contract', 股票: 'contract', 基金: 'contract',
 彩票: 'contract', 买彩票: 'contract', 刮刮乐: 'contract', 抽奖: 'contract',
 买马: 'contract', 博彩: 'contract', 投注: 'contract',
 安床: 'bed',
 看病: 'healing', 求医: 'healing', 治病: 'healing', 就医: 'healing',
 手术: 'healing', 动手术: 'healing', 针灸: 'healing',
 入学: 'schooling', 上学: 'schooling', 开学: 'schooling', 报到: 'schooling',
};

/**
 * The 7 major categories the date-picker form offers.
 *
 * bed / healing / schooling exist for free-text queries but are not offered as form
 * options — they are not the kind of thing anyone plans a date range around.
 */
export const ZERI_EVENTS = [
 'wedding',
 'moving',
 'opening',
 'travel',
 'groundbreaking',
 'praying',
 'contract',
] as const;

/** Human-readable labels for the slugs. */
export const EVENT_LABELS: Record<string, string> = {
 wedding: '嫁娶 / 结婚',
 moving: '入宅 / 搬家',
 opening: '开市 / 开业',
 travel: '出行 / 远行',
 groundbreaking: '动土 / 修造',
 praying: '祭祀 / 祈福',
 contract: '立券 / 交易',
 bed: '安床',
 healing: '求医 / 治病',
 schooling: '入学',
};

/** All recognised event slugs. */
export function listEvents(): string[] {
 return Object.keys(EVENT_YI);
}

/**
 * Natural-language activity → slug.
 *
 * Returns null when nothing matches — the caller then falls back to reporting the day's
 * overall 宜/忌 rather than inventing a verdict for an activity the almanac never covers.
 */
export function resolveEvent(activity: string | null | undefined): string | null {
 const a = (activity ?? '').trim();
 if (!a) return null;
 if (a in EVENT_YI) return a; // already a slug
 if (a in EVENT_ALIAS) return EVENT_ALIAS[a];
 // Fuzzy: the activity word and a keyword contain one another
 for (const [slug, kws] of Object.entries(EVENT_YI)) {
 if (kws.some((k) => a.includes(k) || k.includes(a))) return slug;
 }
 for (const [alias, slug] of Object.entries(EVENT_ALIAS)) {
 if (alias.includes(a) || a.includes(alias)) return slug;
 }
 return null;
}

/**
 * Small-stakes speculation. When a day says 馀事勿取 these are reported as 未明确
 * rather than 不宜 — the phrase is about not undertaking anything of consequence, and
 * treating a lottery ticket as consequential would be overreach in the other direction.
 */
export const SPECULATION_WORDS = [
 '彩票', '刮刮乐', '刮刮樂', '抽奖', '抽獎', '买马', '買馬',
 '博彩', '投注', '六合彩', '乐透', '樂透', '赌', '賭',
];
