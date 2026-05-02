"""
Short child-friendly English stories for Interactive Story Mode.
Each story has exactly 2 comprehension questions answered by voice.
"""

STORIES = [
    {
        "id": 1,
        "title": "The Little Bird",
        "story": (
            "Once there was a little bird named Rani. "
            "She wanted to fly very high in the sky. "
            "Every day she tried again and again, even when she fell. "
            "One day she touched the clouds and sang the happiest song. "
            "Moral: Never give up. Keep trying every single day."
        ),
        "questions": [
            {
                "q": "What was the name of the bird in our story?",
                "a": ["rani", "bird rani", "rani the bird"],
                "hint": "Uska naam R se shuru hota tha",
            },
            {
                "q": "What did the bird finally touch?",
                "a": ["clouds", "the clouds", "sky", "touched clouds"],
                "hint": "Woh aasman mein bohot upar gayi",
            },
        ],
    },
    {
        "id": 2,
        "title": "The Kind Boy",
        "story": (
            "Ravi was a kind boy who lived in a small village. "
            "One day he found a baby rabbit near an old well. "
            "He brought the rabbit home and fed it every day with love. "
            "Soon the rabbit became his best friend. "
            "Moral: Kindness always makes new friends."
        ),
        "questions": [
            {
                "q": "Who helped the baby rabbit in our story?",
                "a": ["ravi", "the boy ravi", "kind boy", "a boy named ravi"],
                "hint": "Ek achha ladka tha jiska naam R se shuru hota tha",
            },
            {
                "q": "Where did Ravi find the rabbit?",
                "a": ["near a well", "near the well", "well", "old well", "by the well"],
                "hint": "Paani wali jagah ke paas",
            },
        ],
    },
    {
        "id": 3,
        "title": "The Clever Girl",
        "story": (
            "Meera was a blind girl who loved to learn English. "
            "She listened carefully to every word her teacher said. "
            "She practised speaking English every single day. "
            "One day Meera spoke so well that her whole class clapped for her. "
            "Moral: Listening and daily practice make you great."
        ),
        "questions": [
            {
                "q": "What was the name of the girl in our story?",
                "a": ["meera", "the girl meera", "meera the girl"],
                "hint": "Uska naam M se shuru hota tha",
            },
            {
                "q": "How did Meera become good at English?",
                "a": [
                    "listening", "by listening", "listening carefully",
                    "practice", "daily practice", "she practised",
                ],
                "hint": "Woh roz sunti aur practice karti thi",
            },
        ],
    },
    {
        "id": 4,
        "title": "The Magic Seeds",
        "story": (
            "A poor farmer had only three tiny seeds. "
            "He planted them with love and watered them every day. "
            "His neighbour laughed and said they would never grow. "
            "But after three months three tall fruit trees stood in his field. "
            "The farmer shared the fruit with everyone, even his neighbour. "
            "Moral: Hard work and kindness always win in the end."
        ),
        "questions": [
            {
                "q": "What did the farmer plant in our story?",
                "a": ["seeds", "three seeds", "tiny seeds", "magic seeds"],
                "hint": "Kuch beej the",
            },
            {
                "q": "What grew after three months?",
                "a": ["trees", "three trees", "tall trees", "fruit trees", "three tall trees"],
                "hint": "Paudhe bade hokar ped bane",
            },
        ],
    },
    {
        "id": 5,
        "title": "The Honest Shopkeeper",
        "story": (
            "Old Hassan ran a small shop in the market. "
            "One day a girl named Sara left her purse on the counter. "
            "Hassan kept the purse safe and waited all day for her to return. "
            "When Sara came back, Hassan smiled and returned her purse. "
            "The whole village called him the most honest man they knew. "
            "Moral: Honesty is the greatest treasure."
        ),
        "questions": [
            {
                "q": "What did Sara leave in the shop?",
                "a": ["purse", "her purse", "a purse", "bag", "money bag"],
                "hint": "Ek chota sa bag ya batahua",
            },
            {
                "q": "What did Hassan do when Sara came back?",
                "a": [
                    "returned purse", "gave purse back", "gave it back",
                    "gave the purse", "returned it", "gave back the purse",
                ],
                "hint": "Usne wapas kar diya jo Sara ka tha",
            },
        ],
    },
]
