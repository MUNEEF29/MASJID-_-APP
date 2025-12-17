from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, AIChatHistory

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai')

ISLAMIC_KNOWLEDGE_BASE = {
    'prayer_times': {
        'fajr': 'Fajr (Dawn Prayer) - Performed before sunrise',
        'dhuhr': 'Dhuhr (Noon Prayer) - Performed after the sun passes its zenith',
        'asr': 'Asr (Afternoon Prayer) - Performed in the late afternoon',
        'maghrib': 'Maghrib (Sunset Prayer) - Performed just after sunset',
        'isha': 'Isha (Night Prayer) - Performed after twilight disappears'
    },
    'pillars': [
        'Shahada (Declaration of Faith) - Testimony that there is no god but Allah and Muhammad is His messenger',
        'Salah (Prayer) - Five daily prayers',
        'Zakat (Charity) - Giving 2.5% of savings to those in need',
        'Sawm (Fasting) - Fasting during Ramadan',
        'Hajj (Pilgrimage) - Pilgrimage to Mecca once in lifetime if able'
    ],
    'greetings': {
        'assalamu_alaikum': 'Assalamu Alaikum - Peace be upon you (greeting)',
        'wa_alaikum_assalam': 'Wa Alaikum Assalam - And upon you be peace (response)',
        'bismillah': 'Bismillah - In the name of Allah (said before starting anything)',
        'alhamdulillah': 'Alhamdulillah - Praise be to Allah (said when grateful)',
        'insha_allah': 'Insha Allah - God willing (said about future plans)',
        'masha_allah': 'Masha Allah - As Allah has willed (said when admiring)',
        'subhan_allah': 'Subhan Allah - Glory be to Allah (expression of amazement)',
        'jazak_allah': 'Jazak Allah Khair - May Allah reward you with goodness'
    },
    'duas': {
        'morning': 'Allahumma bika asbahna wa bika amsayna - O Allah, by Your leave we enter the morning and by Your leave we enter the evening',
        'evening': 'Allahumma bika amsayna wa bika asbahna - O Allah, by Your leave we enter the evening and by Your leave we enter the morning',
        'before_food': 'Bismillahi wa ala barakatillah - In the name of Allah and with blessings of Allah',
        'after_food': 'Alhamdulillahi lladhi at\'amana wa saqana wa ja\'alana minal muslimin - Praise be to Allah who fed us and gave us drink and made us Muslims',
        'before_sleep': 'Bismika Allahumma amutu wa ahya - In Your name O Allah, I die and I live',
        'entering_mosque': 'Allahumma iftah li abwaba rahmatika - O Allah, open for me the doors of Your mercy',
        'leaving_mosque': 'Allahumma inni as\'aluka min fadlika - O Allah, I ask You from Your bounty'
    }
}

def get_ai_response(message):
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['prayer', 'salah', 'namaz', 'pray']):
        if 'time' in message_lower or 'when' in message_lower:
            response = "The five daily prayers (Salah) are:\n\n"
            for name, desc in ISLAMIC_KNOWLEDGE_BASE['prayer_times'].items():
                response += f"- **{name.title()}**: {desc}\n"
            response += "\n*Prayer times vary by location and season. Please check local prayer times.*"
            return response
        else:
            return "Salah (prayer) is the second pillar of Islam. Muslims are required to pray five times daily: Fajr (dawn), Dhuhr (noon), Asr (afternoon), Maghrib (sunset), and Isha (night). Each prayer involves specific physical movements and recitations from the Quran."
    
    elif any(word in message_lower for word in ['pillar', 'arkaan', 'foundation']):
        response = "The **Five Pillars of Islam** are the foundation of Muslim life:\n\n"
        for i, pillar in enumerate(ISLAMIC_KNOWLEDGE_BASE['pillars'], 1):
            response += f"{i}. {pillar}\n\n"
        return response
    
    elif any(word in message_lower for word in ['zakat', 'charity', 'sadaqah']):
        return "**Zakat** is the third pillar of Islam and refers to obligatory charity. Muslims who possess wealth above a certain threshold (nisab) must give 2.5% of their savings annually to those in need.\n\n**Sadaqah** is voluntary charity given beyond the obligatory Zakat. Both forms of giving are highly encouraged in Islam and purify one's wealth.\n\n*This accounting system helps you track Zakat and Sadaqah separately to maintain proper Islamic financial records.*"
    
    elif any(word in message_lower for word in ['ramadan', 'fasting', 'sawm', 'roza']):
        return "**Ramadan** is the ninth month of the Islamic calendar during which Muslims fast from dawn to sunset. Fasting (Sawm) is the fourth pillar of Islam.\n\nDuring Ramadan:\n- Muslims abstain from food, drink, and other physical needs from Fajr to Maghrib\n- It is a time for spiritual reflection, increased devotion, and worship\n- The Night of Power (Laylat al-Qadr) falls within the last ten nights\n- Eid al-Fitr celebrates the end of Ramadan"
    
    elif any(word in message_lower for word in ['greeting', 'salam', 'hello', 'assalam']):
        response = "**Islamic Greetings and Phrases:**\n\n"
        for name, meaning in ISLAMIC_KNOWLEDGE_BASE['greetings'].items():
            response += f"- {meaning}\n"
        return response
    
    elif any(word in message_lower for word in ['dua', 'supplication', 'pray for']):
        response = "**Common Islamic Duas (Supplications):**\n\n"
        for occasion, dua in ISLAMIC_KNOWLEDGE_BASE['duas'].items():
            response += f"- **{occasion.replace('_', ' ').title()}**: {dua}\n\n"
        return response
    
    elif any(word in message_lower for word in ['quran', 'book', 'scripture']):
        return "The **Quran** is the holy book of Islam, believed to be the word of Allah revealed to Prophet Muhammad (PBUH) through the angel Jibreel (Gabriel) over 23 years.\n\nThe Quran consists of:\n- 114 Surahs (chapters)\n- 6,236 verses (ayahs)\n- Guidance for all aspects of life\n\nReading and memorizing the Quran is highly rewarded in Islam. The month of Ramadan is especially significant as the Quran was first revealed during this time."
    
    elif any(word in message_lower for word in ['hajj', 'pilgrimage', 'mecca', 'kaaba']):
        return "**Hajj** is the fifth pillar of Islam - the pilgrimage to Mecca that every able Muslim must perform at least once in their lifetime.\n\nKey elements of Hajj:\n- **Tawaf**: Circling the Kaaba seven times\n- **Sa'i**: Walking between the hills of Safa and Marwa\n- **Day of Arafah**: Standing in prayer on the plains of Arafat\n- **Stoning of the Devil**: Symbolic rejection of evil\n\nHajj occurs in the Islamic month of Dhul Hijjah, and Eid al-Adha is celebrated at its conclusion."
    
    elif any(word in message_lower for word in ['help', 'what can you', 'how can you']):
        return "**Welcome to Islamic AI Assistant!** I can help you with:\n\n- **Prayer Times**: Information about the five daily prayers\n- **Pillars of Islam**: Learn about the foundations of Muslim faith\n- **Zakat & Charity**: Understanding Islamic charitable giving\n- **Ramadan & Fasting**: Information about the holy month\n- **Islamic Greetings**: Common phrases and their meanings\n- **Duas**: Supplications for various occasions\n- **Quran**: Information about the holy book\n- **Hajj**: The pilgrimage to Mecca\n\nFeel free to ask any questions about Islamic teachings!"
    
    elif any(word in message_lower for word in ['bismillah', 'start', 'begin']):
        return "**Bismillah ir-Rahman ir-Rahim**\n\nبِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيْمِ\n\nMeaning: *In the name of Allah, the Most Gracious, the Most Merciful*\n\nThis phrase begins 113 of the 114 chapters of the Quran and is recited by Muslims before undertaking any significant action."
    
    elif any(word in message_lower for word in ['allah', 'god']):
        return "**Allah** is the Arabic word for God. In Islam, Allah is:\n\n- The One and Only God\n- The Creator of all that exists\n- All-Knowing (Al-Alim)\n- All-Merciful (Ar-Rahman)\n- The Most Gracious (Ar-Rahim)\n\nAllah has 99 beautiful names (Asma ul-Husna) that describe His attributes. Muslims worship Allah alone and believe there is no god but Him."
    
    else:
        return "**Assalamu Alaikum!** Peace be upon you.\n\nI'm your Islamic AI Assistant. I can help you learn about:\n\n- The Five Pillars of Islam\n- Prayer times and Salah\n- Zakat and Sadaqah (charity)\n- Ramadan and fasting\n- Common Islamic greetings and duas\n- The Holy Quran\n- Hajj pilgrimage\n\nPlease ask me anything about Islamic teachings, and I'll do my best to assist you!\n\n*Jazak Allah Khair*"


@ai_assistant_bp.route('/')
@login_required
def index():
    chat_history = AIChatHistory.query.filter_by(user_id=current_user.id).order_by(AIChatHistory.created_at.desc()).limit(20).all()
    return render_template('ai/index.html', chat_history=chat_history[::-1])


@ai_assistant_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    message = request.json.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    response = get_ai_response(message)
    
    chat = AIChatHistory(
        user_id=current_user.id,
        message=message,
        response=response
    )
    db.session.add(chat)
    db.session.commit()
    
    return jsonify({
        'response': response,
        'timestamp': chat.created_at.strftime('%Y-%m-%d %H:%M')
    })


@ai_assistant_bp.route('/clear', methods=['POST'])
@login_required
def clear_history():
    AIChatHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'success': True})
