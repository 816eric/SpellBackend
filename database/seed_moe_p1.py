"""One-off seed script: MOE (Singapore) Primary 1 Chinese characters,
sourced from the official 2024 "欢乐伙伴2.0" 小学华文生字表 (Primary One,
Term 1 lessons 1-10 and Term 2 lessons 11-19).

Idempotent: safe to re-run. Checks for existing SpellingWord (text +
language="chinese"), existing Tag (by tag string) before inserting.

Creates:
- 19 lesson tags, label_type="MOE", named "MOE::P1::上::第一课" ...
  "MOE::P1::下::第十九课".
- 1 shared tag "MOE::P1::写字", label_type="MOE", applied to every
  character that appears in ANY lesson's 识写字 (write-required) list.
- One SpellingWord per unique character (deduped across lessons),
  language="chinese", with pinyin (tone marks) and a short English gloss.
- WordTagLink rows connecting each word to every lesson tag it appears in,
  plus the write-required tag where applicable.

Run: .venv/bin/python database/seed_moe_p1.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select, create_engine
from src.models.word import SpellingWord
from src.models.tag import Tag
from src.models.link import WordTagLink

DB_PATH = Path(__file__).resolve().parent / "db.sqlite3"
engine = create_engine(f"sqlite:///{DB_PATH}")

# Chinese numerals for lesson numbers 1-19.
CJK_LESSON_NUM = [
    None, "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九",
]

# (term: "上"/"下", lesson_number, 识读字 string, 识写字 string)
LESSONS = [
    ("上", 1, "衣鱼雨一二五耳牙口人", "一二五口人"),
    ("上", 2, "木土马八巴你我也他弟不爸她妈的父母女儿", "木土八也不女儿"),
    ("上", 3, "力河禾立米合气和哥几七了个句可以吗去", "力禾几七个可去"),
    ("上", 4, "日石子字车四十士只把尺是书出自己它吃", "日子车四十巴士只"),
    ("上", 5, "山羊毛草太阳王三伞包老师早安半午奶玩具", "山羊毛王三书早午"),
    ("上", 6, "鸟竹田苗象家刀网在里上下大小来哭笑男爷姐", "田刀在上下大小来"),
    ("上", 7, "果开瓜火花叶面关朵两片画笔长广多少床", "开火关两长广多少"),
    ("上", 8, "目舌手足本工厂走跑飞妹门看见问又头们身体", "目手本工门见又头"),
    ("上", 9, "牛井虫弓贝心豆六支条九粒今什么华文点说语", "牛贝六支九什么文"),
    ("上", 10, "月天地风雷电水寸方正反白好坏对古旧有没云", "月天水寸正反白古"),
    ("下", 11, "甲丁前后左右中间边同学朋友坐高发直起回周末", "后左右中间面的同学画回"),
    ("下", 12, "鸡饭鸭元饿饱饼干狗喜欢肉猫采歌唱青菜汤蛋香", "包半元吃干肉虫今米豆"),
    ("下", 13, "用刷巾抹洗要脸放冲凉东西到先请很泡变谢", "用牙巾以要东西雨马先点"),
    ("下", 14, "这双袜那皮鞋件服被还色红都动作快收拾穿事做", "是皮衣和里尺还自己好"),
    ("下", 15, "甜苦臭生重喝甘汁买斤串弯选最抱拿办法圆切怎", "生果汁买斤办法看"),
    ("下", 16, "扫户桌椅兄房阿叔会写啊完业躲进净谁打听声", "父母她他会你们爸妈打"),
    ("下", 17, "昨晚星明庆祝节爱给国乐课台讲故每童因为", "昨明给快乐没有这老师每"),
    ("下", 18, "兔尾短眼睛爪尖物虎狮园期带黑站叫认话再孩", "爪尖气玩我弟妹站叫再"),
    ("下", 19, "组屋公校场商店梯扶常球步图习伙伴游拍兴戏", "公园姐哥习起到高兴心"),
]

WRITE_TAG_NAME = "MOE::P1::写字"

# Pinyin (tone marks) + short English gloss for every unique character
# across the lists above. Homographs/function-vs-content-word cases (都,
# 地, etc) are glossed for how they're used in this beginner-vocab list.
PINYIN_MEANING = {
    "衣": ("yī", "clothes"),
    "鱼": ("yú", "fish"),
    "雨": ("yǔ", "rain"),
    "一": ("yī", "one"),
    "二": ("èr", "two"),
    "五": ("wǔ", "five"),
    "耳": ("ěr", "ear"),
    "牙": ("yá", "tooth"),
    "口": ("kǒu", "mouth"),
    "人": ("rén", "person"),
    "木": ("mù", "wood/tree"),
    "土": ("tǔ", "soil/earth"),
    "马": ("mǎ", "horse"),
    "八": ("bā", "eight"),
    "巴": ("bā", "(in 巴士, bus)"),
    "你": ("nǐ", "you"),
    "我": ("wǒ", "I/me"),
    "也": ("yě", "also"),
    "他": ("tā", "he/him"),
    "弟": ("dì", "younger brother"),
    "不": ("bù", "not"),
    "爸": ("bà", "dad"),
    "她": ("tā", "she/her"),
    "妈": ("mā", "mom"),
    "的": ("de", "possessive particle"),
    "父": ("fù", "father"),
    "母": ("mǔ", "mother"),
    "女": ("nǚ", "female/daughter"),
    "儿": ("ér", "son/child"),
    "力": ("lì", "strength"),
    "河": ("hé", "river"),
    "禾": ("hé", "grain/rice plant"),
    "立": ("lì", "to stand"),
    "米": ("mǐ", "rice"),
    "合": ("hé", "to combine"),
    "气": ("qì", "air/gas"),
    "和": ("hé", "and/harmony"),
    "哥": ("gē", "older brother"),
    "几": ("jǐ", "how many"),
    "七": ("qī", "seven"),
    "了": ("le", "completed-action particle"),
    "个": ("gè", "measure word"),
    "句": ("jù", "sentence"),
    "可": ("kě", "can/may"),
    "以": ("yǐ", "(in 可以, may/can)"),
    "吗": ("ma", "question particle"),
    "去": ("qù", "to go"),
    "日": ("rì", "sun/day"),
    "石": ("shí", "stone"),
    "子": ("zǐ", "child/son"),
    "字": ("zì", "character/word"),
    "车": ("chē", "vehicle"),
    "四": ("sì", "four"),
    "十": ("shí", "ten"),
    "士": ("shì", "(in 巴士, bus)"),
    "只": ("zhǐ", "only"),
    "把": ("bǎ", "measure word / to hold"),
    "尺": ("chǐ", "ruler"),
    "是": ("shì", "to be"),
    "书": ("shū", "book"),
    "出": ("chū", "to go out"),
    "自": ("zì", "self"),
    "己": ("jǐ", "self/oneself"),
    "它": ("tā", "it"),
    "吃": ("chī", "to eat"),
    "山": ("shān", "mountain"),
    "羊": ("yáng", "sheep/goat"),
    "毛": ("máo", "fur/hair"),
    "草": ("cǎo", "grass"),
    "太": ("tài", "too/very"),
    "阳": ("yáng", "sun"),
    "王": ("wáng", "king"),
    "三": ("sān", "three"),
    "伞": ("sǎn", "umbrella"),
    "包": ("bāo", "bag/bun"),
    "老": ("lǎo", "old"),
    "师": ("shī", "teacher"),
    "早": ("zǎo", "early/morning"),
    "安": ("ān", "peace/safe"),
    "半": ("bàn", "half"),
    "午": ("wǔ", "noon"),
    "奶": ("nǎi", "milk/grandma"),
    "玩": ("wán", "to play"),
    "具": ("jù", "(in 玩具, toy)"),
    "鸟": ("niǎo", "bird"),
    "竹": ("zhú", "bamboo"),
    "田": ("tián", "field"),
    "苗": ("miáo", "seedling"),
    "象": ("xiàng", "elephant"),
    "家": ("jiā", "home/family"),
    "刀": ("dāo", "knife"),
    "网": ("wǎng", "net"),
    "在": ("zài", "at/in"),
    "里": ("lǐ", "inside"),
    "上": ("shàng", "up/above"),
    "下": ("xià", "down/below"),
    "大": ("dà", "big"),
    "小": ("xiǎo", "small"),
    "来": ("lái", "to come"),
    "哭": ("kū", "to cry"),
    "笑": ("xiào", "to laugh/smile"),
    "男": ("nán", "male"),
    "爷": ("yé", "grandpa"),
    "姐": ("jiě", "older sister"),
    "果": ("guǒ", "fruit"),
    "开": ("kāi", "to open"),
    "瓜": ("guā", "melon"),
    "火": ("huǒ", "fire"),
    "花": ("huā", "flower"),
    "叶": ("yè", "leaf"),
    "面": ("miàn", "face/surface"),
    "关": ("guān", "to close"),
    "朵": ("duǒ", "measure word for flowers"),
    "两": ("liǎng", "two"),
    "片": ("piàn", "slice/piece"),
    "画": ("huà", "to draw/picture"),
    "笔": ("bǐ", "pen"),
    "长": ("cháng", "long"),
    "广": ("guǎng", "wide/broad"),
    "多": ("duō", "many/much"),
    "少": ("shǎo", "few/little"),
    "床": ("chuáng", "bed"),
    "目": ("mù", "eye"),
    "舌": ("shé", "tongue"),
    "手": ("shǒu", "hand"),
    "足": ("zú", "foot"),
    "本": ("běn", "measure word for books"),
    "工": ("gōng", "work"),
    "厂": ("chǎng", "factory"),
    "走": ("zǒu", "to walk"),
    "跑": ("pǎo", "to run"),
    "飞": ("fēi", "to fly"),
    "妹": ("mèi", "younger sister"),
    "门": ("mén", "door"),
    "看": ("kàn", "to look/watch"),
    "见": ("jiàn", "to see"),
    "问": ("wèn", "to ask"),
    "又": ("yòu", "again"),
    "头": ("tóu", "head"),
    "们": ("men", "plural suffix"),
    "身": ("shēn", "body"),
    "体": ("tǐ", "body"),
    "牛": ("niú", "cow"),
    "井": ("jǐng", "well (water)"),
    "虫": ("chóng", "insect"),
    "弓": ("gōng", "bow (weapon)"),
    "贝": ("bèi", "shell"),
    "心": ("xīn", "heart"),
    "豆": ("dòu", "bean"),
    "六": ("liù", "six"),
    "支": ("zhī", "measure word/branch"),
    "条": ("tiáo", "measure word/strip"),
    "九": ("jiǔ", "nine"),
    "粒": ("lì", "measure word for grains"),
    "今": ("jīn", "now/today"),
    "什": ("shén", "(in 什么, what)"),
    "么": ("me", "(in 什么, what)"),
    "华": ("huá", "Chinese (as in 华文)"),
    "文": ("wén", "language/writing"),
    "点": ("diǎn", "point/o'clock"),
    "说": ("shuō", "to speak"),
    "语": ("yǔ", "language"),
    "月": ("yuè", "moon/month"),
    "天": ("tiān", "sky/day"),
    "地": ("dì", "ground/land"),
    "风": ("fēng", "wind"),
    "雷": ("léi", "thunder"),
    "电": ("diàn", "electricity"),
    "水": ("shuǐ", "water"),
    "寸": ("cùn", "inch"),
    "方": ("fāng", "square/direction"),
    "正": ("zhèng", "correct/straight"),
    "反": ("fǎn", "opposite"),
    "白": ("bái", "white"),
    "好": ("hǎo", "good"),
    "坏": ("huài", "bad/broken"),
    "对": ("duì", "correct/toward"),
    "古": ("gǔ", "ancient"),
    "旧": ("jiù", "old (used)"),
    "有": ("yǒu", "to have"),
    "没": ("méi", "not have"),
    "云": ("yún", "cloud"),
    "甲": ("jiǎ", "first (of a series)/armor"),
    "丁": ("dīng", "(in 甲丁, a name/4th heav. stem)"),
    "前": ("qián", "front/before"),
    "后": ("hòu", "back/after"),
    "左": ("zuǒ", "left"),
    "右": ("yòu", "right"),
    "中": ("zhōng", "middle/China"),
    "间": ("jiān", "between/room"),
    "边": ("biān", "side"),
    "同": ("tóng", "same/together"),
    "学": ("xué", "to learn"),
    "朋": ("péng", "friend"),
    "友": ("yǒu", "friend"),
    "坐": ("zuò", "to sit"),
    "高": ("gāo", "tall/high"),
    "发": ("fā", "to send out/hair"),
    "直": ("zhí", "straight"),
    "起": ("qǐ", "to rise/get up"),
    "回": ("huí", "to return"),
    "周": ("zhōu", "week"),
    "末": ("mò", "end"),
    "鸡": ("jī", "chicken"),
    "饭": ("fàn", "cooked rice/meal"),
    "鸭": ("yā", "duck"),
    "元": ("yuán", "dollar/unit of currency"),
    "饿": ("è", "hungry"),
    "饱": ("bǎo", "full (from eating)"),
    "饼": ("bǐng", "biscuit/cake"),
    "干": ("gān", "dry"),
    "狗": ("gǒu", "dog"),
    "喜": ("xǐ", "happy/to like"),
    "欢": ("huān", "joyful (in 喜欢, to like)"),
    "肉": ("ròu", "meat"),
    "猫": ("māo", "cat"),
    "采": ("cǎi", "to pick/gather"),
    "歌": ("gē", "song"),
    "唱": ("chàng", "to sing"),
    "青": ("qīng", "green/blue"),
    "菜": ("cài", "vegetable"),
    "汤": ("tāng", "soup"),
    "蛋": ("dàn", "egg"),
    "香": ("xiāng", "fragrant"),
    "用": ("yòng", "to use"),
    "刷": ("shuā", "to brush"),
    "巾": ("jīn", "towel"),
    "抹": ("mǒ", "to wipe"),
    "洗": ("xǐ", "to wash"),
    "要": ("yào", "to want/need"),
    "脸": ("liǎn", "face"),
    "放": ("fàng", "to put/release"),
    "冲": ("chōng", "to rinse/rush"),
    "凉": ("liáng", "cool (in 冲凉, shower)"),
    "东": ("dōng", "east"),
    "西": ("xī", "west"),
    "到": ("dào", "to arrive"),
    "先": ("xiān", "first"),
    "请": ("qǐng", "please"),
    "很": ("hěn", "very"),
    "泡": ("pào", "to soak"),
    "变": ("biàn", "to change"),
    "谢": ("xiè", "thank"),
    "这": ("zhè", "this"),
    "双": ("shuāng", "pair"),
    "袜": ("wà", "socks"),
    "那": ("nà", "that"),
    "皮": ("pí", "skin/leather"),
    "鞋": ("xié", "shoe"),
    "件": ("jiàn", "measure word for clothes"),
    "服": ("fú", "clothing"),
    "被": ("bèi", "passive marker/quilt"),
    "还": ("hái", "still/also"),
    "色": ("sè", "color"),
    "红": ("hóng", "red"),
    "都": ("dōu", "all/also"),
    "动": ("dòng", "to move"),
    "作": ("zuò", "to do/make"),
    "快": ("kuài", "fast"),
    "收": ("shōu", "to collect"),
    "拾": ("shí", "to pick up (in 收拾, tidy up)"),
    "穿": ("chuān", "to wear"),
    "事": ("shì", "matter/affair"),
    "做": ("zuò", "to do/make"),
    "甜": ("tián", "sweet"),
    "苦": ("kǔ", "bitter"),
    "臭": ("chòu", "smelly"),
    "生": ("shēng", "raw/to be born"),
    "重": ("zhòng", "heavy"),
    "喝": ("hē", "to drink"),
    "甘": ("gān", "sweet/pleasant"),
    "汁": ("zhī", "juice"),
    "买": ("mǎi", "to buy"),
    "斤": ("jīn", "catty (unit of weight)"),
    "串": ("chuàn", "string/bunch"),
    "弯": ("wān", "bent/curve"),
    "选": ("xuǎn", "to choose"),
    "最": ("zuì", "most"),
    "抱": ("bào", "to hug/hold"),
    "拿": ("ná", "to hold/take"),
    "办": ("bàn", "to handle (in 办法, method)"),
    "法": ("fǎ", "method/law"),
    "圆": ("yuán", "round"),
    "切": ("qiē", "to cut"),
    "怎": ("zěn", "how (in 怎么)"),
    "扫": ("sǎo", "to sweep"),
    "户": ("hù", "household/door"),
    "桌": ("zhuō", "table"),
    "椅": ("yǐ", "chair"),
    "兄": ("xiōng", "older brother"),
    "房": ("fáng", "room/house"),
    "阿": ("ā", "prefix for names/kin"),
    "叔": ("shū", "uncle"),
    "会": ("huì", "can/will"),
    "写": ("xiě", "to write"),
    "啊": ("a", "exclamatory particle"),
    "完": ("wán", "to finish"),
    "业": ("yè", "occupation/schoolwork"),
    "躲": ("duǒ", "to hide"),
    "进": ("jìn", "to enter"),
    "净": ("jìng", "clean"),
    "谁": ("shéi", "who"),
    "打": ("dǎ", "to hit/play"),
    "听": ("tīng", "to listen"),
    "声": ("shēng", "sound"),
    "昨": ("zuó", "yesterday"),
    "晚": ("wǎn", "evening/late"),
    "星": ("xīng", "star"),
    "明": ("míng", "bright/next"),
    "庆": ("qìng", "to celebrate"),
    "祝": ("zhù", "to wish/celebrate"),
    "节": ("jié", "festival"),
    "爱": ("ài", "love"),
    "给": ("gěi", "to give"),
    "国": ("guó", "country"),
    "乐": ("lè", "happy"),
    "课": ("kè", "lesson/class"),
    "台": ("tái", "platform/stage"),
    "讲": ("jiǎng", "to speak/tell"),
    "故": ("gù", "reason (in 故事, story)"),
    "每": ("měi", "every"),
    "童": ("tóng", "child"),
    "因": ("yīn", "because"),
    "为": ("wèi", "for/because of"),
    "兔": ("tù", "rabbit"),
    "尾": ("wěi", "tail"),
    "短": ("duǎn", "short"),
    "眼": ("yǎn", "eye"),
    "睛": ("jīng", "eyeball (in 眼睛, eye)"),
    "爪": ("zhǎo", "claw"),
    "尖": ("jiān", "sharp/pointed"),
    "物": ("wù", "thing/object"),
    "虎": ("hǔ", "tiger"),
    "狮": ("shī", "lion"),
    "园": ("yuán", "garden"),
    "期": ("qī", "period of time"),
    "带": ("dài", "to bring/belt"),
    "黑": ("hēi", "black"),
    "站": ("zhàn", "to stand/station"),
    "叫": ("jiào", "to call/shout"),
    "认": ("rèn", "to recognize"),
    "话": ("huà", "speech/words"),
    "再": ("zài", "again"),
    "孩": ("hái", "child"),
    "组": ("zǔ", "group"),
    "屋": ("wū", "house"),
    "公": ("gōng", "public"),
    "校": ("xiào", "school"),
    "场": ("chǎng", "field/venue"),
    "商": ("shāng", "commerce/business"),
    "店": ("diàn", "shop"),
    "梯": ("tī", "stairs/ladder"),
    "扶": ("fú", "to support/help up"),
    "常": ("cháng", "often"),
    "球": ("qiú", "ball"),
    "步": ("bù", "step"),
    "图": ("tú", "picture/map"),
    "习": ("xí", "to practise/study"),
    "伙": ("huǒ", "partner (in 伙伴, companion)"),
    "伴": ("bàn", "companion"),
    "游": ("yóu", "to swim/travel"),
    "拍": ("pāi", "to pat/clap"),
    "兴": ("xìng", "mood/interest (in 高兴, happy)"),
    "戏": ("xì", "play/drama"),
}


def main():
    with Session(engine) as session:
        write_required_chars = set()
        for _, _, _, write_str in LESSONS:
            write_required_chars.update(write_str)

        # Ensure/reuse the shared write-required tag.
        write_tag = session.exec(
            select(Tag).where(Tag.tag == WRITE_TAG_NAME)
        ).first()
        if not write_tag:
            write_tag = Tag(
                tag=WRITE_TAG_NAME,
                created_by="admin",
                description="Characters Primary 1 students must be able to write (识写字), not just recognize.",
                label_type="MOE",
            )
            session.add(write_tag)
            session.commit()
            session.refresh(write_tag)

        word_count = 0
        link_count = 0
        missing_pinyin = []

        for term, num, read_str, write_str in LESSONS:
            cjk_num = CJK_LESSON_NUM[num]
            lesson_tag_name = f"MOE::P1::{term}::第{cjk_num}课"
            lesson_tag = session.exec(
                select(Tag).where(Tag.tag == lesson_tag_name)
            ).first()
            if not lesson_tag:
                lesson_tag = Tag(
                    tag=lesson_tag_name,
                    created_by="admin",
                    description=f"MOE Primary 1 {term} lesson {num} (第{cjk_num}课) characters.",
                    label_type="MOE",
                )
                session.add(lesson_tag)
                session.commit()
                session.refresh(lesson_tag)

            write_set = set(write_str)
            for ch in read_str:
                pinyin, meaning = PINYIN_MEANING.get(ch, (None, None))
                if pinyin is None:
                    missing_pinyin.append(ch)

                word = session.exec(
                    select(SpellingWord).where(
                        (SpellingWord.text == ch) & (SpellingWord.language == "chinese")
                    )
                ).first()
                if not word:
                    word = SpellingWord(
                        text=ch,
                        language="chinese",
                        created_by="admin",
                        pinyin=pinyin,
                        meaning=meaning,
                    )
                    session.add(word)
                    session.commit()
                    session.refresh(word)
                    word_count += 1
                else:
                    # Backfill pinyin/meaning if missing (idempotent re-run,
                    # or a word that pre-existed from another source).
                    changed = False
                    if not word.pinyin and pinyin:
                        word.pinyin = pinyin
                        changed = True
                    if not word.meaning and meaning:
                        word.meaning = meaning
                        changed = True
                    if changed:
                        session.add(word)
                        session.commit()

                # Link to the lesson tag (idempotent).
                existing_link = session.exec(
                    select(WordTagLink).where(
                        (WordTagLink.word_id == word.id) & (WordTagLink.tag_id == lesson_tag.id)
                    )
                ).first()
                if not existing_link:
                    session.add(WordTagLink(word_id=word.id, tag_id=lesson_tag.id))
                    link_count += 1

                # Link to the write-required tag if applicable (idempotent).
                if ch in write_set:
                    existing_write_link = session.exec(
                        select(WordTagLink).where(
                            (WordTagLink.word_id == word.id) & (WordTagLink.tag_id == write_tag.id)
                        )
                    ).first()
                    if not existing_write_link:
                        session.add(WordTagLink(word_id=word.id, tag_id=write_tag.id))
                        link_count += 1

            session.commit()

        print(f"New SpellingWord rows created: {word_count}")
        print(f"New WordTagLink rows created: {link_count}")
        if missing_pinyin:
            print(f"WARNING: missing pinyin/meaning for: {sorted(set(missing_pinyin))}")
        else:
            print("All characters have pinyin/meaning.")


if __name__ == "__main__":
    main()
