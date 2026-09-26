"""Explicit language requests and fixed, reviewed application wording. No translation API."""

import re
from typing import Literal

Language = Literal["en", "hi", "hinglish"]

# Current message only. Ambiguous requests fall back to the saved preference.
# Script alone never overrides the user's preference.
OVERRIDES: dict[Language, str] = {
    "en": r"\bin english\b|\benglish (?:mein|me)\b|अंग्रेज़ी में|अंग्रेजी में",
    "hi": r"\bin hindi\b|\bhindi (?:mein|me)\b|हिंदी में|हिन्दी में",
    "hinglish": r"\bin hinglish\b|\bhinglish (?:mein|me)\b|हिंग्लिश में",
}


def explicit_language(question: str) -> Language | None:
    matches = [language for language, pattern in OVERRIDES.items() if re.search(pattern, question.casefold())]
    return matches[0] if len(matches) == 1 else None


def resolve_language(question: str, saved: Language = "en") -> Language:
    return explicit_language(question) or saved


HINDI: dict[str, str] = {
    "sources": "ये चुने गए वर्तमान अवलोकन हैं। मान, इकाइयाँ और दी गई संदर्भ जानकारी ठीक उसी रूप में दिखाई गई हैं जिसमें वे दर्ज हैं। इनसे निदान स्थापित नहीं होता।",
    "increasing": "पास-पास की अवधियों की नियम-आधारित तुलना में बढ़ोतरी है। यह दर्ज मापों का वर्णन है, चिकित्सा निष्कर्ष नहीं।",
    "decreasing": "पास-पास की अवधियों की नियम-आधारित तुलना में कमी है। यह दर्ज मापों का वर्णन है, चिकित्सा निष्कर्ष नहीं।",
    "stable": "नियम-आधारित तुलना ऐप की स्थिरता सीमा के भीतर है। स्थिर का अर्थ स्वस्थ, सामान्य या सुरक्षित नहीं है।",
    "insufficient_data": "अवधि के रुझान के लिए पर्याप्त डेटा नहीं है। नवीनतम और पिछले माप की अलग से उपलब्ध तुलना किसी लगातार रुझान को स्थापित नहीं करती।",
    "clarify": "कृपया एक माप का नाम बताएं: वज़न, हृदय गति, हीमोग्लोबिन, TSH, Vitamin D, ग्लूकोज़ या CRP। या अपनी सबसे हाल में अपलोड की गई रिपोर्ट के बारे में पूछें। आप 7 या 30 दिनों की तुलना मांग सकते हैं।",
    "no_data": "इस प्रश्न से मेल खाने वाले प्रकाशित या स्वयं दर्ज किए गए योग्य अवलोकन नहीं हैं। रिपोर्ट के मानों की समीक्षा करके उन्हें स्पष्ट रूप से प्रकाशित करें, या समर्थित माप स्वयं दर्ज करें।",
    "unsupported_units": "उपलब्ध इकाइयों के समूहों को सुरक्षित रूप से मिलाया नहीं जा सकता। रुझान पृष्ठ पर हर मूल इकाई अलग देखें। कोई रूपांतरण या तुलना अनुमान से नहीं की गई है।",
    "unsupported_correlation": "वर्तमान माप सूची में सहसंबंध के लिए कोई समर्थित जोड़ी नहीं है। इसलिए कोई सांख्यिकीय संबंध नहीं दिया जा सकता। सहसंबंध से कारण और परिणाम स्थापित नहीं होते।",
    "safety": "मैं निदान नहीं कर सकता, दवा नहीं लिख सकता, दवा बदलने की सलाह नहीं दे सकता और किसी अन्य व्यक्ति की जानकारी या गोपनीय विवरण नहीं बता सकता। आप अपने दर्ज मापों के बारे में पूछ सकते हैं। स्वास्थ्य पेशेवर उन्हें आपके संदर्भ में समझा सकते हैं।",
    "emergency": "यदि आपको या आपके साथ किसी व्यक्ति को तत्काल खतरा हो सकता है, तो अभी आपातकालीन चिकित्सा सहायता लें। स्थानीय आपातकालीन सेवा से संपर्क करें या नज़दीकी आपातकालीन विभाग जाएं। चैट के उत्तर की प्रतीक्षा न करें।",
}
HINGLISH: dict[str, str] = {
    "sources": "Ye chune gaye maujooda observations hain. Values, units aur diye gaye reference text ko bilkul waise hi dikhaya gaya hai jaise record mein hain. Inse diagnosis tay nahi hota.",
    "increasing": "Paas ki do periods ki niyam-aadharit tulna mein badhotri hai. Ye darj measurements ka varnan hai, medical nateeja nahi.",
    "decreasing": "Paas ki do periods ki niyam-aadharit tulna mein kami hai. Ye darj measurements ka varnan hai, medical nateeja nahi.",
    "stable": "Niyam-aadharit tulna app ki stability seema ke andar hai. Stable ka matlab healthy, normal ya safe nahi hai.",
    "insufficient_data": "Period trend ke liye paryapt data nahi hai. Latest aur pichhle measurement ki alag uplabdh tulna se lagatar trend tay nahi hota.",
    "clarify": "Kripya ek metric batayein: weight, heart rate, hemoglobin, TSH, Vitamin D, glucose ya CRP. Ya apni sabse haal mein upload ki gayi report ke baare mein poochhein. Aap 7 ya 30 din ki tulna maang sakte hain.",
    "no_data": "Is sawal se milte hue eligible published ya khud darj kiye observations nahi hain. Report values ko review karke spasht roop se publish karein, ya supported measurement khud darj karein.",
    "unsupported_units": "Uplabdh unit groups ko surakshit tareeke se milaya nahi ja sakta. Trends mein har exact unit alag dekhein. Koi conversion ya comparison andaze se nahi kiya gaya hai.",
    "unsupported_correlation": "Maujooda metric catalog mein correlation ke liye koi supported pair nahi hai. Koi statistical association nahi diya ja sakta. Correlation se cause aur effect sabit nahi hote.",
    "safety": "Main diagnosis, prescription ya dawa badalne ki salah nahi de sakta, aur kisi doosre vyakti ka data ya secrets nahi bata sakta. Aap apne darj measurements ke baare mein poochh sakte hain. Healthcare professional unhein aapke sandarbh mein samjha sakte hain.",
    "emergency": "Agar aap ya aapke saath koi vyakti turant khatre mein ho sakta hai, abhi emergency medical madad lein. Apni local emergency service se sampark karein ya nazdeeki emergency department jayein. Chat ke jawab ka intezar na karein.",
}


def wording(code: str, language: Language, english: dict[str, str]) -> str:
    return (HINDI if language == "hi" else HINGLISH if language == "hinglish" else english)[code]
