export type Tradition =
  | "madhyamaka"
  | "chan_zen"
  | "vajrayana"
  | "theravada"
  | "pure_land"
  | "shingon"
  | "gelug"
  | "engaged";

export type Master = {
  id: string;
  primaryName: string;
  scriptName?: string; // original script (hanko inscription)
  lifespan: string;
  birthYear: number;
  deathYear: number;
  tradition: Tradition;
  traditionLabel: string;
  country: string;
  summary: string;
  passages: Array<{
    text: string;
    work: string;
    edition: string;
    translator: string;
    locator: string;
  }>;
  teachers?: string[]; // ids
};

export const MASTERS: Master[] = [
  {
    id: "nagarjuna",
    primaryName: "Nāgārjuna",
    scriptName: "龍樹",
    lifespan: "c. 150 – c. 250",
    birthYear: 150,
    deathYear: 250,
    tradition: "madhyamaka",
    traditionLabel: "Madhyamaka",
    country: "South India",
    summary:
      "Founder of the Madhyamaka school. Through the logic of emptiness, he showed that all phenomena arise dependently and therefore lack any fixed essence. His Mūlamadhyamakakārikā remains the axis around which later Mahāyāna philosophy turns.",
    passages: [
      {
        text: "Whatever is dependently co-arisen, that is explained to be emptiness. That, being a dependent designation, is itself the middle way.",
        work: "Mūlamadhyamakakārikā",
        edition: "MMK",
        translator: "Jay Garfield, 1995",
        locator: "ch. 24, v. 18",
      },
      {
        text: "Neither from itself nor from another, nor from both, nor without cause, does anything, anywhere, ever arise.",
        work: "Mūlamadhyamakakārikā",
        edition: "MMK",
        translator: "Jay Garfield, 1995",
        locator: "ch. 1, v. 1",
      },
    ],
  },
  {
    id: "buddhaghosa",
    primaryName: "Buddhaghosa",
    scriptName: "बुद्धघोस",
    lifespan: "5th century",
    birthYear: 370,
    deathYear: 450,
    tradition: "theravada",
    traditionLabel: "Theravāda",
    country: "Sri Lanka",
    summary:
      "The great systematizer of Theravāda thought. At the Mahāvihāra he composed the Visuddhimagga, a detailed road-map from ethical conduct through concentration to the liberating wisdom that ends suffering.",
    passages: [
      {
        text: "Purification should be understood as Nibbāna, which is devoid of all stains and is utterly pure. The path leading to that purification is what is called the Path of Purification.",
        work: "Visuddhimagga",
        edition: "PTS ed.",
        translator: "Bhikkhu Ñāṇamoli, 1956",
        locator: "i.5",
      },
    ],
  },
  {
    id: "bodhidharma",
    primaryName: "Bodhidharma",
    scriptName: "菩提達磨",
    lifespan: "c. 440 – 528",
    birthYear: 440,
    deathYear: 528,
    tradition: "chan_zen",
    traditionLabel: "Chan",
    country: "India → China",
    summary:
      "The blue-eyed barbarian who brought Chan to China. He is said to have faced the wall at Shaolin for nine years, transmitting outside the scriptures, pointing directly to the human mind.",
    passages: [
      {
        text: "A special transmission outside the scriptures; not founded upon words and letters. By pointing directly to one's mind, it lets one see into one's own true nature and attain Buddhahood.",
        work: "Attributed verse",
        edition: "Wudeng Huiyuan",
        translator: "Red Pine, 1987",
        locator: "trad. attr.",
      },
    ],
  },
  {
    id: "huineng",
    primaryName: "Huineng",
    scriptName: "惠能",
    lifespan: "638 – 713",
    birthYear: 638,
    deathYear: 713,
    tradition: "chan_zen",
    traditionLabel: "Chan",
    country: "China",
    summary:
      "The Sixth Patriarch, an illiterate wood-cutter who awakened upon hearing a line of the Diamond Sutra. His Platform Sutra is the only text of a Chinese teacher canonized as a sutra.",
    passages: [
      {
        text: "Bodhi is fundamentally without any tree; the bright mirror is also not a stand. Fundamentally there is not a single thing. Where could any dust be attracted?",
        work: "Platform Sutra",
        edition: "Taishō T2008",
        translator: "Philip Yampolsky, 1967",
        locator: "Dunhuang ed., sec. 8",
      },
      {
        text: "Good friends, our own nature, in its origin, is pure. If we know our own minds and see our own nature, we all achieve Buddhahood.",
        work: "Platform Sutra",
        edition: "Taishō T2008",
        translator: "Red Pine, 2006",
        locator: "sec. 19",
      },
    ],
    teachers: ["bodhidharma"],
  },
  {
    id: "padmasambhava",
    primaryName: "Padmasambhava",
    scriptName: "པདྨ་འབྱུང་གནས",
    lifespan: "8th century",
    birthYear: 717,
    deathYear: 762,
    tradition: "vajrayana",
    traditionLabel: "Nyingma",
    country: "Oḍḍiyāna → Tibet",
    summary:
      "Guru Rinpoche. Tantric master who subdued the spirits of Tibet and co-founded Samye monastery. Hid countless terma teachings to be revealed in future ages.",
    passages: [
      {
        text: "If you do not apply the antidote against negative emotions as they arise, how will they ever cease? Look nakedly at their empty nature, and they self-liberate.",
        work: "Self-Liberation Through Seeing with Naked Awareness",
        edition: "Terma cycle",
        translator: "John Reynolds, 2000",
        locator: "ll. 112–115",
      },
    ],
  },
  {
    id: "kukai",
    primaryName: "Kūkai",
    scriptName: "空海",
    lifespan: "774 – 835",
    birthYear: 774,
    deathYear: 835,
    tradition: "shingon",
    traditionLabel: "Shingon",
    country: "Japan",
    summary:
      "Founder of Japanese Shingon. Poet, calligrapher, civil engineer, and esoteric master who taught that this very body, in this very life, can realize Buddhahood through mantra, mudrā, and mandala.",
    passages: [
      {
        text: "The Three Mysteries pervade the entire universe, adorning grandly the mandala of original enlightenment. Through them the practitioner swiftly attains the great awakening in this very body.",
        work: "Sokushin Jōbutsu Gi",
        edition: "Taishō T2428",
        translator: "Yoshito Hakeda, 1972",
        locator: "sec. 3",
      },
    ],
  },
  {
    id: "atisha",
    primaryName: "Atiśa",
    scriptName: "ཨ་ཏི་ཤ",
    lifespan: "982 – 1054",
    birthYear: 982,
    deathYear: 1054,
    tradition: "vajrayana",
    traditionLabel: "Kadam",
    country: "Bengal → Tibet",
    summary:
      "Dīpaṃkara Śrījñāna. Bengali master who reformed Tibetan Buddhism in its second diffusion, authoring the Bodhipathapradīpa — the seed of every later lamrim.",
    passages: [
      {
        text: "The foundation of all practice is the mind of enlightenment. Without it, no amount of ritual or learning accomplishes the goal.",
        work: "Bodhipathapradīpa",
        edition: "Tengyur",
        translator: "Geshe Sonam Rinchen, 1997",
        locator: "vv. 10–12",
      },
    ],
  },
  {
    id: "milarepa",
    primaryName: "Milarepa",
    scriptName: "མི་ལ་རས་པ",
    lifespan: "1052 – 1135",
    birthYear: 1052,
    deathYear: 1135,
    tradition: "vajrayana",
    traditionLabel: "Kagyü",
    country: "Tibet",
    summary:
      "Tibet's cotton-clad yogi. After terrible acts of black magic in youth, he purified them under Marpa's brutal discipline and sang one hundred thousand songs from the caves of the high Himalaya.",
    passages: [
      {
        text: "I have forgotten the view; the view and the meditation have become one. I have forgotten the meditation; it has dissolved into naked awareness itself.",
        work: "Mila Grubum (Hundred Thousand Songs)",
        edition: "Tsang Nyön Heruka ed.",
        translator: "Garma C.C. Chang, 1962",
        locator: "song 28",
      },
    ],
    teachers: ["atisha"],
  },
  {
    id: "shinran",
    primaryName: "Shinran",
    scriptName: "親鸞",
    lifespan: "1173 – 1263",
    birthYear: 1173,
    deathYear: 1263,
    tradition: "pure_land",
    traditionLabel: "Jōdo Shinshū",
    country: "Japan",
    summary:
      "Founder of True Pure Land Buddhism. Held that Amida's Vow has already accomplished the salvation of all beings; the nembutsu is not a work to earn the Pure Land but its expression.",
    passages: [
      {
        text: "Even a good person attains birth in the Pure Land, how much more so an evil person. Yet people ordinarily say the opposite.",
        work: "Tannishō",
        edition: "Hongwanji ed.",
        translator: "Taitetsu Unno, 1984",
        locator: "ch. 3",
      },
    ],
  },
  {
    id: "dogen",
    primaryName: "Dōgen",
    scriptName: "道元",
    lifespan: "1200 – 1253",
    birthYear: 1200,
    deathYear: 1253,
    tradition: "chan_zen",
    traditionLabel: "Sōtō",
    country: "Japan",
    summary:
      "Founder of Japanese Sōtō Zen. Returned from China having realized that body-and-mind is itself the dropped-off body-and-mind. The Shōbōgenzō turns Zen into language that burns.",
    passages: [
      {
        text: "To study the Buddha Way is to study the self. To study the self is to forget the self. To forget the self is to be actualized by the ten thousand things.",
        work: "Shōbōgenzō Genjōkōan",
        edition: "Taishō T2582",
        translator: "Kazuaki Tanahashi, 1985",
        locator: "§ 3",
      },
      {
        text: "Firewood becomes ash, and it does not become firewood again. Yet, do not suppose that the ash is after and the firewood is before.",
        work: "Shōbōgenzō Genjōkōan",
        edition: "Taishō T2582",
        translator: "Kazuaki Tanahashi, 1985",
        locator: "§ 9",
      },
    ],
  },
  {
    id: "longchenpa",
    primaryName: "Longchenpa",
    scriptName: "ཀློང་ཆེན་པ",
    lifespan: "1308 – 1364",
    birthYear: 1308,
    deathYear: 1364,
    tradition: "vajrayana",
    traditionLabel: "Nyingma",
    country: "Tibet",
    summary:
      "The omniscient Longchen Rabjam. Systematizer of Dzogchen, whose Seven Treasuries map the primordially pure ground, its spontaneous radiance, and the path of trekchö and tögal.",
    passages: [
      {
        text: "The nature of mind is empty like the sky; its radiance is the sun and moon; its compassion is the warmth that pervades all. These three are not separate.",
        work: "Finding Rest in the Nature of Mind",
        edition: "sNying thig collection",
        translator: "Padmakara Translation Group, 2017",
        locator: "ch. 2",
      },
    ],
    teachers: ["padmasambhava"],
  },
  {
    id: "tsongkhapa",
    primaryName: "Tsongkhapa",
    scriptName: "ཙོང་ཁ་པ",
    lifespan: "1357 – 1419",
    birthYear: 1357,
    deathYear: 1419,
    tradition: "gelug",
    traditionLabel: "Gelug",
    country: "Tibet",
    summary:
      "Founder of the Gelug school. Integrated Madhyamaka philosophy with the stages of the path in the Lamrim Chenmo, insisting that emptiness and dependent arising are the same meaning stated two ways.",
    passages: [
      {
        text: "When you see that dependent arising and emptiness are non-contradictory, that is the moment of seeing Nāgārjuna's thought. Until then, you have not yet understood the middle way.",
        work: "Lamrim Chenmo",
        edition: "Tengyur eds.",
        translator: "Lamrim Chenmo Translation Committee, 2000",
        locator: "vol. 3, ch. 24",
      },
    ],
    teachers: ["atisha", "nagarjuna"],
  },
  {
    id: "hakuin",
    primaryName: "Hakuin",
    scriptName: "白隠",
    lifespan: "1686 – 1768",
    birthYear: 1686,
    deathYear: 1768,
    tradition: "chan_zen",
    traditionLabel: "Rinzai",
    country: "Japan",
    summary:
      "The father of modern Rinzai Zen. Devised the kōan curriculum still used today, including the sound of one hand. Painter of fierce and tender ink.",
    passages: [
      {
        text: "All beings by nature are Buddha, as ice by nature is water; apart from water there is no ice, apart from beings no Buddha.",
        work: "Song of Zazen",
        edition: "Zazen Wasan",
        translator: "Norman Waddell, 1994",
        locator: "ll. 1–4",
      },
    ],
    teachers: ["dogen"],
  },
  {
    id: "ajahn-mun",
    primaryName: "Ajahn Mun",
    scriptName: "มั่น ภูริทัตโต",
    lifespan: "1870 – 1949",
    birthYear: 1870,
    deathYear: 1949,
    tradition: "theravada",
    traditionLabel: "Thai Forest",
    country: "Thailand",
    summary:
      "Revivalist of the Thai Forest tradition. Walking alone through forests and caves, he rebuilt a lineage of uncompromising practice that shaped Ajahn Chah and a generation of Western monks.",
    passages: [
      {
        text: "The heart is like a still pond. When the water is disturbed you cannot see the fish. When it is calm, you see everything down to the bottom.",
        work: "A Heart Released",
        edition: "Wat Pa Baan Taad ed.",
        translator: "Ṭhānissaro Bhikkhu, 1995",
        locator: "disc. 4",
      },
    ],
  },
  {
    id: "shunryu-suzuki",
    primaryName: "Shunryū Suzuki",
    scriptName: "鈴木俊隆",
    lifespan: "1904 – 1971",
    birthYear: 1904,
    deathYear: 1971,
    tradition: "chan_zen",
    traditionLabel: "Sōtō",
    country: "Japan → USA",
    summary:
      "Founder of San Francisco Zen Center. Planted Sōtō Zen in American soil with a warmth that disarmed the 1960s. His talks became the book that introduced beginner's mind to the West.",
    passages: [
      {
        text: "In the beginner's mind there are many possibilities, but in the expert's there are few.",
        work: "Zen Mind, Beginner's Mind",
        edition: "Weatherhill, 1970",
        translator: "Trudy Dixon (ed.)",
        locator: "prologue",
      },
    ],
    teachers: ["dogen", "hakuin"],
  },
  {
    id: "kalu-rinpoche",
    primaryName: "Kalu Rinpoche",
    scriptName: "ཀར་མ་རང་བྱུང་ཀུན་ཁྱབ",
    lifespan: "1905 – 1989",
    birthYear: 1905,
    deathYear: 1989,
    tradition: "vajrayana",
    traditionLabel: "Shangpa Kagyü",
    country: "Tibet → France",
    summary:
      "Realized yogi of both Shangpa and Karma Kagyü transmissions. Led the first three-year retreat in the West and quietly trained a generation of Western lamas.",
    passages: [
      {
        text: "You live in illusion and the appearance of things. There is a reality. You are that reality. When you know this, you know that you are nothing, and being nothing, you are everything.",
        work: "Oral teachings",
        edition: "collected talks",
        translator: "Ken McLeod, 1986",
        locator: "Vancouver, 1982",
      },
    ],
    teachers: ["milarepa"],
  },
  {
    id: "dilgo-khyentse",
    primaryName: "Dilgo Khyentse",
    scriptName: "དིལ་མགོ་མཁྱེན་བརྩེ",
    lifespan: "1910 – 1991",
    birthYear: 1910,
    deathYear: 1991,
    tradition: "vajrayana",
    traditionLabel: "Nyingma",
    country: "Tibet → Bhutan",
    summary:
      "A towering rime master, tertön, and poet. Teacher to the Dalai Lama and countless others. His presence itself was said to be the transmission.",
    passages: [
      {
        text: "The practice of Dharma should be the activity of the mind in every moment of daily life, not merely what you do on a cushion for an hour.",
        work: "The Heart of Compassion",
        edition: "Shechen ed.",
        translator: "Padmakara Translation Group, 2007",
        locator: "ch. 6",
      },
    ],
    teachers: ["longchenpa", "padmasambhava"],
  },
  {
    id: "ajahn-chah",
    primaryName: "Ajahn Chah",
    scriptName: "ชา สุภทฺโท",
    lifespan: "1918 – 1992",
    birthYear: 1918,
    deathYear: 1992,
    tradition: "theravada",
    traditionLabel: "Thai Forest",
    country: "Thailand",
    summary:
      "Heir of Ajahn Mun. Built Wat Pah Pong and Wat Pah Nanachat, training the first generation of Western Theravāda monks with plain-spoken teachings drawn from the forest itself.",
    passages: [
      {
        text: "Do everything with a mind that lets go. Do not expect any praise or reward. If you let go a little, you will have a little peace. If you let go a lot, you will have a lot of peace.",
        work: "Food for the Heart",
        edition: "Wisdom Publications",
        translator: "Ajahn Pasanno (ed.), 2002",
        locator: "§ 1",
      },
    ],
    teachers: ["ajahn-mun"],
  },
  {
    id: "thich-nhat-hanh",
    primaryName: "Thich Nhat Hanh",
    scriptName: "釋一行",
    lifespan: "1926 – 2022",
    birthYear: 1926,
    deathYear: 2022,
    tradition: "engaged",
    traditionLabel: "Engaged Buddhism",
    country: "Vietnam → France",
    summary:
      "Poet, peace activist, teacher of mindfulness as the ground of social transformation. Nominated for the Nobel Peace Prize by Martin Luther King Jr. Founder of Plum Village.",
    passages: [
      {
        text: "If you are a poet, you will see clearly that there is a cloud floating in this sheet of paper. Without a cloud, there will be no rain; without rain, the trees cannot grow; and without trees, we cannot make paper.",
        work: "The Heart of the Buddha's Teaching",
        edition: "Parallax Press",
        translator: "Parallax ed., 1998",
        locator: "ch. 11",
      },
    ],
    teachers: ["huineng"],
  },
  {
    id: "chogyam-trungpa",
    primaryName: "Chögyam Trungpa",
    scriptName: "ཆོས་རྒྱམ་དྲུང་པ",
    lifespan: "1939 – 1987",
    birthYear: 1939,
    deathYear: 1987,
    tradition: "vajrayana",
    traditionLabel: "Kagyü / Nyingma",
    country: "Tibet → USA",
    summary:
      "Controversial and electric. Eleventh Trungpa tulku who crossed the Himalayas on horseback and planted Vajrayāna in America through Shambhala and Naropa. His dharma cut through spiritual materialism.",
    passages: [
      {
        text: "Enlightenment is like falling out of a boat into cold water: you get the message very clearly.",
        work: "Cutting Through Spiritual Materialism",
        edition: "Shambhala",
        translator: "John Baker & Marvin Casper (eds.), 1973",
        locator: "ch. 1",
      },
    ],
    teachers: ["dilgo-khyentse"],
  },
];

export const MASTERS_SORTED = [...MASTERS].sort(
  (a, b) => a.deathYear - b.deathYear
);
