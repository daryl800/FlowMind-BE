import sxtwl
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

GAN = ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"]
ZHI = ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"]
ELEMENT_MAP = {
    "Jia":"Wood", "Yi":"Wood",
    "Bing":"Fire","Ding":"Fire",
    "Wu":"Earth","Ji":"Earth",
    "Geng":"Metal","Xin":"Metal",
    "Ren":"Water","Gui":"Water",
    "Zi":"Water","Chou":"Earth","Yin":"Wood","Mao":"Wood",
    "Chen":"Earth","Si":"Fire","Wu":"Fire","Wei":"Earth",
    "Shen":"Metal","You":"Metal","Xu":"Earth","Hai":"Water"
}

def calc_bazi(dt: datetime, tz_name="Asia/Hong_Kong"):
    # 1️⃣ Normalize timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    else:
        dt = dt.astimezone(ZoneInfo(tz_name))

    # 子初換日
    if dt.hour >= 23:
        dt += timedelta(days=1)

    y, m, d, h = dt.year, dt.month, dt.day, dt.hour
    lunar_day = sxtwl.fromSolar(y, m, d)

    # Get GanZhi indexes
    year_gz = lunar_day.getYearGZ()
    month_gz = lunar_day.getMonthGZ()
    day_gz = lunar_day.getDayGZ()
    hour_gz = lunar_day.getHourGZ(h)

    pillars = {
        "year": {"gan": GAN[year_gz.tg], "zhi": ZHI[year_gz.dz]},
        "month": {"gan": GAN[month_gz.tg], "zhi": ZHI[month_gz.dz]},
        "day": {"gan": GAN[day_gz.tg], "zhi": ZHI[day_gz.dz]},
        "hour": {"gan": GAN[hour_gz.tg], "zhi": ZHI[hour_gz.dz]},
    }

    # Day Master
    day_master = pillars["day"]["gan"]

    # Five Elements Strength
    fe_strength = {"Wood":0,"Fire":0,"Earth":0,"Metal":0,"Water":0}
    for p in pillars.values():
        for key in ["gan","zhi"]:
            e = ELEMENT_MAP[p[key]]
            fe_strength[e] += 1

    return {"pillars": pillars, "day_master": day_master, "five_elements_strength": fe_strength}


GAN_MAP = {
    "en": ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"],
    "cn": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
}

ZHI_MAP = {
    "en": ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"],
    "cn": ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
}

def localize_pillars(pillars, lang="en"):
    """
    pillars: {
        "year": {"gan": "Bing", "zhi": "Wu"},
        "month": {...},
        ...
    }
    Returns the same dict with extra fields: gan_local, zhi_local, and a full string.
    """
    lang = lang.lower()
    gan_map = GAN_MAP.get(lang, GAN_MAP["en"])
    zhi_map = ZHI_MAP.get(lang, ZHI_MAP["en"])

    def map_one(gz):
        gan_en = gz["gan"]
        zhi_en = gz["zhi"]
        gan_local = gan_map[GAN_MAP["en"].index(gan_en)]
        zhi_local = zhi_map[ZHI_MAP["en"].index(zhi_en)]
        return {**gz, "gan_local": gan_local, "zhi_local": zhi_local}

    localized = {k: map_one(v) for k,v in pillars.items()}

    # Generate a single string
    full_str = " ".join([v["gan_local"] + v["zhi_local"] for k,v in localized.items()])

    return localized, full_str

