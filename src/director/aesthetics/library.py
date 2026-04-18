"""美學知識庫 — 所有從 Round 3-6 累積的導演語言 → 技術參數映射。"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════
# 色彩詞庫 (Round 4 + 擴寫 30 組商業片)
# ═══════════════════════════════════════════════════════════

COLOR_PALETTES: dict[str, dict] = {
    # ── 光線/通透感系列 ──
    "乾淨的光影": {
        "keywords": ["clean", "crisp", "airy"],
        "reference": "Apple 官方影片 / Her",
        "prompt": "clean high-key lighting, preserved highlight detail at 95 IRE, shadows lifted to 15 IRE, no muddy blacks, crisp edge transitions, soft rolloff in skin tones",
        "hsl_range": {"hue": [0, 360], "saturation": [20, 50], "lightness": [60, 85]},
    },
    "通透感": {
        "keywords": ["translucent", "luminous", "airy"],
        "reference": "Uniqlo 廣告 / Amélie",
        "prompt": "airy translucent atmosphere, luminous mid-tones, soft ambient fill from multiple directions, glowing subsurface scattering in skin, no hard shadows",
        "hsl_range": {"hue": [180, 220], "saturation": [15, 35], "lightness": [70, 90]},
    },
    "空氣感": {
        "keywords": ["atmospheric", "dimensional", "breathable"],
        "reference": "Sofia Coppola / Somewhere",
        "prompt": "atmospheric depth with subtle haze layers, volumetric light rays, background softly falling into mist, aerial perspective",
    },
    "清爽": {
        "keywords": ["refreshing", "crisp", "cool"],
        "reference": "寶礦力水得 / Evian",
        "prompt": "refreshing clean palette, cool whites with cyan undertones (#F0F8FA / #D4E8EF / #8FB8C8), high-key exposure, sparkling highlights like water reflections",
        "hsl_range": {"hue": [180, 210], "saturation": [20, 40], "lightness": [75, 92]},
    },
    "日系通透": {
        "keywords": ["japanese", "soft", "muted"],
        "reference": "蒼井優廣告 / 岩井俊二",
        "prompt": "Japanese translucent aesthetic, soft washed palette with subtle green tint (#F5F7F0 / #D8DCC9), creamy highlights with pink undertones, Fujifilm Pro 400H film emulation",
    },
    "北歐極簡": {
        "keywords": ["nordic", "minimalist", "natural"],
        "reference": "IKEA / Marimekko",
        "prompt": "Nordic minimalist palette, neutral warm greys (#EAE7E0 / #C5BDB0), natural wood undertones (#8B7355), occasional cool blue accents, matte finish",
    },

    # ── 商業能量系列 ──
    "熱情": {
        "keywords": ["passionate", "warm", "saturated"],
        "reference": "可口可樂 / Nike",
        "prompt": "high-energy warm palette, saturated reds and oranges (#E63946 / #F77F00), bright 85% luminance, warm 2800K color temperature, vivid skin tones",
        "hsl_range": {"hue": [0, 30], "saturation": [70, 90], "lightness": [50, 70]},
    },
    "熱血": {
        "keywords": ["intense", "crimson", "gold"],
        "reference": "Adidas All or Nothing",
        "prompt": "intense deep crimson and gold (#8B0000 / #FFB800), high contrast 1.8 ratio, dramatic shadows, sweat-glistening highlights, cinematic sports aesthetic",
    },
    "活力": {
        "keywords": ["vibrant", "energetic", "playful"],
        "reference": "M&M / Fanta",
        "prompt": "vibrant energetic yellows and oranges (#FFB703 / #FB8500), 80%+ saturation, pure bright tones with no desaturation, playful color blocking",
    },
    "銳利": {
        "keywords": ["sharp", "precise", "steel"],
        "reference": "BMW / Samsung Galaxy",
        "prompt": "sharp edge definition, microcontrast boosted, crisp deep blacks (#0D1117), steel blue highlights (#4A90E2), tack-sharp focus throughout, precision-engineered aesthetic",
    },
    "力量感": {
        "keywords": ["powerful", "monochromatic", "dramatic"],
        "reference": "Under Armour / BOSS",
        "prompt": "powerful monochromatic palette, desaturated midtones, crushed deep blacks, bright metallic silver highlights, high contrast 2.2 ratio, dramatic Rembrandt lighting",
    },
    "運動感": {
        "keywords": ["dynamic", "motion", "energetic"],
        "reference": "Nike Just Do It",
        "prompt": "dynamic saturated colors, motion blur on edges, bright sun glare and lens flares, sweat droplets catching light, high-energy color grading",
    },

    # ── 專業/商務系列 ──
    "專業": {
        "keywords": ["professional", "corporate", "navy"],
        "reference": "Apple Keynote / Goldman Sachs",
        "prompt": "professional corporate palette, deep navy blues (#0A2540 / #1E3A5F), neutral platinum greys (#B8BEC4), clean whites, desaturation at 30%, executive aesthetic",
    },
    "可信賴": {
        "keywords": ["trustworthy", "stable", "balanced"],
        "reference": "銀行廣告 / Toyota",
        "prompt": "trustworthy palette, stable medium blues (#2B5C8A), warm neutral greys (#9B9590), balanced warm-cool equilibrium, soft contrast 1.3 ratio",
    },
    "高級": {
        "keywords": ["luxury", "matte", "understated"],
        "reference": "Rolex / Dior / Mercedes",
        "prompt": "luxury monochromatic aesthetic, matte deep blacks (#1A1A1A), single dominant hue with 5-10% saturation, champagne gold accents (#CCA677), understated elegance",
    },
    "奢華": {
        "keywords": ["opulent", "lustrous", "rich"],
        "reference": "LV / Hermès",
        "prompt": "opulent palette, deep emerald or burgundy (#1B4332 / #6A040F), lustrous gold accents (#FFD700), silky specular highlights, velvet shadow depth",
    },
    "科技感": {
        "keywords": ["futuristic", "tech", "cyan"],
        "reference": "Samsung / Tesla / Intel",
        "prompt": "futuristic tech aesthetic, electric cyan accents (#00D4FF), deep technical blacks (#000814), subtle blue rim lighting, glowing edges, sterile precision",
    },
    "現代簡約": {
        "keywords": ["modern", "minimalist", "geometric"],
        "reference": "Apple / Muji",
        "prompt": "modern minimalist palette, pure whites with cool undertones, geometric grey shadows, single bold accent color covering <10% frame, uncluttered",
    },

    # ── 情感/生活系列 ──
    "溫暖治癒": {
        "keywords": ["warm", "healing", "amber"],
        "reference": "Ghibli / 是枝裕和",
        "prompt": "warm healing tones, amber and cream palette (#D4A574 / #F5E6D3), 3200K tungsten warmth, soft diffused golden hour light, comforting hearth-like atmosphere",
    },
    "親密": {
        "keywords": ["intimate", "warm", "close"],
        "reference": "王家衛 / 是枝裕和",
        "prompt": "intimate close-up atmosphere, low-key warm lighting, shallow depth with foreground bokeh, whispered warm tones, candlelit warmth",
    },
    "浪漫": {
        "keywords": ["romantic", "pink", "dreamy"],
        "reference": "La La Land / 珠寶廣告",
        "prompt": "romantic palette, dusty pink and rose gold (#F4C2C2 / #E8B4B8), soft dreamy diffusion, magenta shift in highlights, ethereal glow, lens halation",
    },
    "夢幻": {
        "keywords": ["dreamy", "lavender", "ethereal"],
        "reference": "Sofia Coppola / Tim Walker",
        "prompt": "dreamlike palette, pale lavender and blush (#C7B8E8 / #F5C7D4), diffused highlights with bloom, magenta shifts, hazy out-of-focus layers",
    },
    "懷舊": {
        "keywords": ["nostalgic", "vintage", "faded"],
        "reference": "Call Me By Your Name",
        "prompt": "nostalgic vintage palette, faded yellow-browns (#B8A58A), desaturation at 40%, noticeable film grain ISO 400, sun-bleached quality",
    },
    "治癒系": {
        "keywords": ["healing", "pastel", "serene"],
        "reference": "Mr. Children MV / 保養品",
        "prompt": "healing pastel palette, soft blush pinks and sky blues (#FFD6DE / #C8E3F0), diffused natural light, high-key exposure, serene low-contrast tones",
    },

    # ── 戲劇/氛圍系列 ──
    "陰鬱": {
        "keywords": ["moody", "crushed", "melancholic"],
        "reference": "Joker / Mother!",
        "prompt": "moody atmospheric palette, crushed blacks with green-cyan shift, desaturated midtones (20% saturation), deep shadow depth, melancholic chiaroscuro",
    },
    "神秘": {
        "keywords": ["mysterious", "deep", "smoky"],
        "reference": "Blade Runner 2049",
        "prompt": "mysterious atmospheric palette, deep blues and purples (#1D1B3C / #4A3A6A), smoky haze, single-source practical lighting",
    },
    "緊張": {
        "keywords": ["tense", "red-accent", "opposition"],
        "reference": "Mission Impossible",
        "prompt": "tense palette, desaturated cool background with pops of saturated red (#C00000), high contrast 1.8 ratio, strong warm-cool opposition",
    },
    "昭和感": {
        "keywords": ["showa", "analog", "magenta-shift"],
        "reference": "岩井俊二 / Love Letter",
        "prompt": "Showa-era aesthetic, faded amber and magenta tones, Kodak Portra 400 emulation, visible grain at ISO 400, slight magenta-green color shift, analog warmth",
    },
    "賽博龐克": {
        "keywords": ["cyberpunk", "neon", "teal-magenta"],
        "reference": "Blade Runner / Ghost in the Shell",
        "prompt": "cyberpunk palette, teal-magenta contrast (#00B4D8 / #E63946), neon reflections in puddles, RGB channel separation in shadows, rain-soaked atmosphere",
    },
    "極簡": {
        "keywords": ["minimalist", "clean", "spacious"],
        "reference": "無印良品 / Apple",
        "prompt": "minimalist aesthetic, single dominant hue, 70%+ negative space, soft even lighting, no shadows beyond subject, clean geometric composition",
    },
}


# ═══════════════════════════════════════════════════════════
# 構圖 12 法 (Round 4)
# ═══════════════════════════════════════════════════════════

COMPOSITION_METHODS: dict[str, dict] = {
    "對稱構圖": {
        "use": "權威、神聖、儀式感",
        "reference": "Wes Anderson / Kubrick",
        "prompt": "perfectly symmetrical composition, central vanishing point, one-point perspective",
    },
    "黃金螺旋": {
        "use": "自然引導視線",
        "reference": "Renaissance 繪畫",
        "prompt": "Fibonacci spiral composition, subject on golden ratio focal point",
    },
    "三分法": {
        "use": "通用平衡",
        "reference": "紀錄片 / 商業",
        "prompt": "rule of thirds, subject on right-third intersection",
    },
    "中央構圖": {
        "use": "情感直擊、肖像",
        "reference": "Amélie 肖像",
        "prompt": "centered composition, subject filling middle third",
    },
    "框中框": {
        "use": "限制感、窺視感",
        "reference": "王家衛 / 侯孝賢",
        "prompt": "frame within frame, subject viewed through doorway or window",
    },
    "對角線": {
        "use": "動能、不安",
        "reference": "Hitchcock",
        "prompt": "diagonal composition from lower-left to upper-right, dynamic tension",
    },
    "低角度仰拍": {
        "use": "權威、英雄感",
        "reference": "Marvel",
        "prompt": "low angle worm's-eye view, subject towering over camera",
    },
    "高角度俯拍": {
        "use": "弱小、全局感",
        "reference": "Bird's eye suspense",
        "prompt": "high angle bird's-eye view, subject appearing small in environment",
    },
    "荷蘭角": {
        "use": "不穩定、瘋狂",
        "reference": "恐怖片",
        "prompt": "Dutch angle tilt 15°, disorienting composition",
    },
    "負空間": {
        "use": "孤獨、冥想",
        "reference": "極簡廣告",
        "prompt": "negative space dominates 70% of frame, subject small in lower corner",
    },
    "Leading Lines": {
        "use": "引導視線",
        "reference": "所有攝影",
        "prompt": "strong leading lines from foreground converging to subject",
    },
    "前景遮擋": {
        "use": "窺視、親密",
        "reference": "是枝裕和",
        "prompt": "foreground occlusion with shallow depth: blurred out-of-focus elements in first 30% of frame (leaves/fabric/window frame), creating voyeuristic intimacy, main subject in middle ground sharply in focus",
    },
}


# ═══════════════════════════════════════════════════════════
# 光線 10 型 (Round 4)
# ═══════════════════════════════════════════════════════════

LIGHTING_TYPES: dict[str, dict] = {
    "Golden Hour": {
        "direction": "側逆光低角", "quality": "溫暖柔軟",
        "prompt": "golden hour sunlight at 15° elevation, warm amber, long shadows, atmospheric haze",
    },
    "Blue Hour": {
        "direction": "環境光無方向", "quality": "冷柔",
        "prompt": "blue hour ambient light, cool cyan-blue sky, soft fill from environment, no sun",
    },
    "Window Light": {
        "direction": "單側柔光", "quality": "柔弱對比",
        "prompt": "north-facing window light from left, soft diffused, subtle gradient across face",
    },
    "Hard Noon": {
        "direction": "正上方", "quality": "硬光強對比",
        "prompt": "harsh noon sun directly overhead, deep shadows under brow and nose, high contrast",
    },
    "Practical Light": {
        "direction": "場景燈", "quality": "暖、集中",
        "prompt": "practical tungsten lamps within the scene, warm pools of light, dark edges",
    },
    "Rim Light": {
        "direction": "逆側光", "quality": "硬邊緣",
        "prompt": "backlit rim light separating subject from dark background, 0.5-stop edge highlight",
    },
    "Rembrandt Light": {
        "direction": "45° 高角", "quality": "三角形面光",
        "prompt": "Rembrandt lighting at 45° elevation and 45° horizontal from subject, fill at -1.5 stops, triangular light pattern on cheek, classical portrait from 17th century Dutch painting",
    },
    "Split Lighting": {
        "direction": "正側 90°", "quality": "對比強",
        "prompt": "split lighting 90° side, half face in shadow, film noir aesthetic",
    },
    "Butterfly Lighting": {
        "direction": "正前方高", "quality": "均勻柔和",
        "prompt": "butterfly lighting directly in front and above, symmetrical nose shadow, beauty lighting",
    },
    "Motivated Light": {
        "direction": "符合場景邏輯", "quality": "自然",
        "prompt": "motivated lighting consistent with practical sources in scene, naturalistic",
    },
}


# ═══════════════════════════════════════════════════════════
# 美術風格 × 藝術家 (Round 4)
# ═══════════════════════════════════════════════════════════

ART_REFERENCES: dict[str, dict] = {
    "Hopper": {
        "essence": "都市孤獨、銳利光線",
        "prompt": "in the style of Edward Hopper, solitary figures in urban isolation, sharp sunlight cutting through windows",
    },
    "浮世繪": {
        "essence": "平面透視、流動線條",
        "prompt": "ukiyo-e aesthetic, flat perspective with flowing lines, traditional Japanese composition",
    },
    "Magritte": {
        "essence": "超現實、不可能並置",
        "prompt": "Magritte surrealism, impossible juxtapositions, blue sky reality",
    },
    "Wes Anderson": {
        "essence": "對稱、粉彩、精密居中",
        "prompt": "Wes Anderson symmetrical composition, pastel palette, meticulous centered framing",
    },
    "Tarkovsky": {
        "essence": "長鏡頭、詩意、霧感",
        "prompt": "Tarkovsky cinematography, long contemplative takes, misty atmosphere, dripping water, poetic realism",
    },
    "宮崎駿": {
        "essence": "手繪背景、自然細節、金色光",
        "prompt": "Ghibli aesthetic, hand-painted backgrounds, lush natural detail, golden atmospheric light",
    },
    "Vermeer": {
        "essence": "左側窗光、17 世紀荷蘭寫實",
        "prompt": "Vermeer lighting from left window, detailed interior, 17th century Dutch realism",
    },
    "Caravaggio": {
        "essence": "強烈明暗對比、聚光源",
        "prompt": "Caravaggio chiaroscuro, extreme light-dark contrast, spotlight from single source",
    },
    "王家衛": {
        "essence": "高對比、霓虹、anamorphic bokeh",
        "prompt": "Wong Kar-wai style, anamorphic 1.33x bokeh, high contrast low saturation, neon reflections",
    },
    "Anton Corbijn": {
        "essence": "極簡、黑白、人文",
        "prompt": "Anton Corbijn style, minimalist black and white, intimate human portraiture",
    },
    "Paolo Roversi": {
        "essence": "柔焦、霧感、畫意攝影",
        "prompt": "Paolo Roversi painterly photography, soft focus, hazy ethereal atmosphere",
    },
    "Helmut Newton": {
        "essence": "硬光、黑白、權力美學",
        "prompt": "Helmut Newton power aesthetic, hard direct light, bold black and white composition",
    },
    "Tim Walker": {
        "essence": "童話感、過曝、粉紅",
        "prompt": "Tim Walker fairytale aesthetic, overexposed highlights, whimsical pink tones",
    },
    "Sebastião Salgado": {
        "essence": "紀實黑白、高對比、質感",
        "prompt": "Sebastião Salgado documentary style, high contrast black and white, textural depth",
    },
    "北歐自然": {
        "essence": "柔光、自然色、窗邊",
        "prompt": "Nordic natural aesthetic, north-facing window soft light, muted pastel palette with cool undertones (#F5F3F0 / #D4E0E8 / #8EA4B8), minimalist composition with breathing space, warm wood textures",
    },
}


# ═══════════════════════════════════════════════════════════
# 運鏡器材 + 鏡頭 (Round 3 + 4)
# ═══════════════════════════════════════════════════════════

CAMERA_MOVEMENT_GEAR: dict[str, dict] = {
    "static_tripod": {"zh": "三腳架靜止", "prompt": "tripod-mounted static shot, absolutely still, no movement"},
    "handheld_organic": {"zh": "手持自然", "prompt": "handheld camera with natural breathing motion, subtle organic sway"},
    "gimbal_smooth": {"zh": "穩定器平順", "prompt": "gimbal stabilized smooth glide, fluid controlled movement"},
    "steadicam_floating": {"zh": "Steadicam 浮動", "prompt": "steadicam floating movement with subtle vertical bob from walking"},
    "dolly_horizontal": {"zh": "軌道水平", "prompt": "dolly track horizontal movement, perfectly level parallel travel"},
    "crane_vertical": {"zh": "搖臂垂直", "prompt": "crane vertical rise or descent, smooth mechanical trajectory"},
    "drone_aerial": {"zh": "空拍機", "prompt": "aerial drone shot, smooth flight with gentle banking"},
    "zoom_optical": {"zh": "光學變焦", "prompt": "optical zoom in, camera position fixed, focal length change"},
}


# ═══════════════════════════════════════════════════════════
# 品類 → 美學預設對應 (Round 4 + 6)
# ═══════════════════════════════════════════════════════════

CATEGORY_AESTHETICS: dict[str, dict] = {
    "保健食品": {
        "colors": ["清爽", "北歐極簡", "通透感"],
        "art_reference": "北歐自然",
        "lighting": "Window Light",
        "composition": "負空間",
        "music_emotion": "溫暖治癒",
    },
    "美妝保養": {
        "colors": ["治癒系", "夢幻", "日系通透"],
        "art_reference": "Paolo Roversi",
        "lighting": "Butterfly Lighting",
        "composition": "中央構圖",
        "music_emotion": "夢幻",
    },
    "3C電子": {
        "colors": ["科技感", "銳利", "專業"],
        "art_reference": "Anton Corbijn",
        "lighting": "Rim Light",
        "composition": "對稱構圖",
        "music_emotion": "科技冷感",
    },
    "金融保險": {
        "colors": ["專業", "可信賴", "現代簡約"],
        "art_reference": "Anton Corbijn",
        "lighting": "Motivated Light",
        "composition": "對稱構圖",
        "music_emotion": "專業可信",
    },
    "汽車": {
        "colors": ["力量感", "銳利", "奢華"],
        "art_reference": "Helmut Newton",
        "lighting": "Rim Light",
        "composition": "對角線",
        "music_emotion": "力量感",
    },
    "食品飲料": {
        "colors": ["熱情", "活力", "通透感"],
        "art_reference": "Tim Walker",
        "lighting": "Golden Hour",
        "composition": "三分法",
        "music_emotion": "活力熱情",
    },
    "運動用品": {
        "colors": ["運動感", "熱血", "銳利"],
        "art_reference": "Sebastião Salgado",
        "lighting": "Hard Noon",
        "composition": "低角度仰拍",
        "music_emotion": "運動熱血",
    },
    "精品珠寶": {
        "colors": ["奢華", "高級", "神秘"],
        "art_reference": "Caravaggio",
        "lighting": "Rembrandt Light",
        "composition": "中央構圖",
        "music_emotion": "高級奢華",
    },
    "親子家庭": {
        "colors": ["溫暖治癒", "懷舊", "日系通透"],
        "art_reference": "宮崎駿",
        "lighting": "Window Light",
        "composition": "前景遮擋",
        "music_emotion": "溫暖治癒",
    },
    "旅遊戶外": {
        "colors": ["空氣感", "通透感", "熱情"],
        "art_reference": "宮崎駿",
        "lighting": "Golden Hour",
        "composition": "Leading Lines",
        "music_emotion": "活力熱情",
    },
}


# ═══════════════════════════════════════════════════════════
# 自然條件 Prompt 模板 (Round 6)
# ═══════════════════════════════════════════════════════════

NATURAL_CONDITIONS: dict[str, dict] = {
    "黃昏陽台": {
        "prompt": "Golden hour lighting at 6:47 PM in late summer, sun at 12° elevation from horizon, warm orange-pink sky gradient (#FFA07A to #FF6347 at top, #87CEEB to #E6E6FA near horizon), directional warm light from left side at 30° angle",
    },
    "晨霧森林": {
        "prompt": "Early morning 6:30 AM forest light, sun filtering through mist at low angle, volumetric god rays cutting through dense fog, cool blue-green tones (#A8B5A0 / #4A5D52) with warm golden spots, atmospheric particulate haze",
    },
    "雨天街景": {
        "prompt": "Overcast rainy afternoon, diffused light with no shadows, wet pavement reflections amplifying colors, muted cyan-grey palette (#8FA4AE), atmospheric rain particles in air, dripping surfaces",
    },
    "夜晚霓虹": {
        "prompt": "Urban night scene 11 PM, mixed color temperature lighting from neon signs and street lamps, deep shadows with vibrant accent lighting (magenta #FF006E, cyan #00D4FF), wet reflections, atmospheric haze",
    },
    "冬日晴朗": {
        "prompt": "Winter clear day 2 PM, low-angle sun at 25° elevation, cool blue shadows on snow (#B8D4E3), warm amber highlights on surfaces (#FFB800), crisp high-contrast lighting, visible breath particles",
    },
    "夏日正午": {
        "prompt": "Summer midday 12:30 PM, harsh overhead sun at 85° elevation, deep short shadows directly below subjects, saturated vibrant colors, heat shimmer on distant surfaces, lens flare when pointed near sun",
    },
    "室內暖光": {
        "prompt": "Interior tungsten lighting 3200K, warm amber glow from practical lamps, pools of light with darker corners, cozy ambient atmosphere, soft shadow gradients",
    },
    "攝影棚白": {
        "prompt": "Photography studio white cyclorama background, soft diffused lighting from 2-3 sources, even illumination with controlled shadows, color temperature 5500K daylight balanced, clean commercial aesthetic",
    },
    "自然窗光": {
        "prompt": "North-facing window natural light, soft diffused, no direct sun, even illumination from large window source, subtle gradient from bright to shadow across subject",
    },
    "傍晚室內": {
        "prompt": "Evening interior mixed lighting, warm tungsten from practicals mixing with cool blue window light from outside, dramatic color temperature contrast, Vermeer-esque",
    },
}


# ═══════════════════════════════════════════════════════════
# 音樂情緒 (Round 5B)
# ═══════════════════════════════════════════════════════════

MUSIC_EMOTIONS: dict[str, dict] = {
    "溫暖治癒": {"bpm_range": [60, 80], "instruments": ["piano", "acoustic guitar", "strings"], "prompt": "warm healing instrumental, gentle piano melody with soft strings and acoustic guitar"},
    "專業可信": {"bpm_range": [90, 110], "instruments": ["synth pad", "piano"], "prompt": "professional minimalist electronic, stable synth pad with gentle piano, corporate elegance"},
    "活力熱情": {"bpm_range": [120, 140], "instruments": ["drum machine", "bass", "synth lead"], "prompt": "energetic pop EDM, punchy drums with synth lead, upbeat commercial energy"},
    "高級奢華": {"bpm_range": [70, 90], "instruments": ["orchestra", "piano", "female vocal"], "prompt": "neo-classical luxury, orchestral strings with piano and ethereal female vocals"},
    "科技冷感": {"bpm_range": [120, 130], "instruments": ["synthesizer", "electronic beats"], "prompt": "tech house electronic, cool synthesizers with precise electronic beats"},
    "日常治癒": {"bpm_range": [80, 100], "instruments": ["acoustic guitar", "ukulele", "vocals"], "prompt": "indie folk daily life, acoustic guitar and ukulele with warm mixed vocals"},
    "運動熱血": {"bpm_range": [140, 160], "instruments": ["electric guitar", "heavy drums", "808 bass"], "prompt": "sports rock trap, aggressive electric guitar with heavy drums and 808 bass"},
    "神秘張力": {"bpm_range": [80, 100], "instruments": ["low drone", "strings", "percussion"], "prompt": "cinematic tension, low drone with building strings and tribal percussion"},
    "夢幻": {"bpm_range": [70, 95], "instruments": ["synth pad", "piano", "reverb vocals"], "prompt": "dreamy ethereal, lush synth pads with reverb-heavy piano and airy vocals"},
}


# ═══════════════════════════════════════════════════════════
# 聲音設計風格 (Round 5B)
# ═══════════════════════════════════════════════════════════

SOUND_DESIGN_STYLES: dict[str, dict] = {
    "Hans Zimmer 式": {"ref": "Interstellar / Dune", "prompt": "Zimmer-style bass-heavy score, gradual build, emotional orchestral swells"},
    "久石讓式": {"ref": "Ghibli 所有作品", "prompt": "Joe Hisaishi-style piano melody, warm strings, gentle nostalgia"},
    "Trent Reznor 式": {"ref": "Social Network / Mank", "prompt": "Reznor-style synthesizer score, dissonant textures, industrial cool"},
    "Max Richter 式": {"ref": "Arrival", "prompt": "Richter-style minimalist strings, meditative layering, emotional restraint"},
    "坂本龍一式": {"ref": "末代皇帝", "prompt": "Sakamoto-style ambient piano, Eastern harmony, philosophical depth"},
    "Daft Punk 式": {"ref": "Tron Legacy", "prompt": "Daft Punk-style electronic synth, motorik beats, futuristic"},
    "Lo-fi 日系": {"ref": "YouTube lo-fi girl", "prompt": "Japanese lo-fi aesthetic, relaxed beats, coffee shop ambience"},
    "90s 廣告 jingle": {"ref": "Coca-Cola / 金莎", "prompt": "90s commercial jingle, bright memorable melody, 8-bar hook"},
}


# ═══════════════════════════════════════════════════════════
# AI 生成禁區 (Round 3 + 6)
# ═══════════════════════════════════════════════════════════

FORBIDDEN_PATTERNS: dict[str, dict] = {
    "文字_中文": {"risk": 10, "workaround": "blank label, no text, add text in post-production"},
    "文字_英文": {"risk": 8, "workaround": "simplified or abstract text, add exact copy in post"},
    "Logo_特寫": {"risk": 10, "workaround": "use reference logo composite in post"},
    "手指_小物件": {"risk": 7, "workaround": "avoid finger count visibility, use wider framing or hand-on-table composition"},
    "液體_倒出": {"risk": 8, "workaround": "show liquid already in container, not mid-pour"},
    "多人_擁抱": {"risk": 6, "workaround": "avoid entangled limbs, use side-by-side composition"},
    "鏡面_完美反射": {"risk": 5, "workaround": "add intentional distortion or bokeh to reflection"},
    "對稱_物件": {"risk": 4, "workaround": "introduce slight asymmetry to avoid uncanny valley"},
}
