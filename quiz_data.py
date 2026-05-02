"""
Quiz questions for Daily Quiz Mode.
Types: opposite, meaning, grammar, spelling
Difficulty: easy, medium, hard
"""

QUIZ_QUESTIONS = {
    # ── Opposite words ──────────────────────────────────────────────────────
    'opposite': {
        'easy': [
            {'q': 'What is the opposite of big?',    'a': ['small','little','tiny'],   'hint': 'It means chota'},
            {'q': 'What is the opposite of hot?',    'a': ['cold','cool'],             'hint': 'It means thanda'},
            {'q': 'What is the opposite of day?',    'a': ['night'],                   'hint': 'It means raat'},
            {'q': 'What is the opposite of happy?',  'a': ['sad','unhappy'],           'hint': 'It means udaas'},
            {'q': 'What is the opposite of tall?',   'a': ['short','small'],           'hint': 'It means chhota'},
            {'q': 'What is the opposite of fast?',   'a': ['slow','slowly'],           'hint': 'It means dheera'},
            {'q': 'What is the opposite of clean?',  'a': ['dirty','unclean'],         'hint': 'It means ganda'},
            {'q': 'What is the opposite of open?',   'a': ['closed','shut','close'],   'hint': 'It means band'},
            {'q': 'What is the opposite of dark?',   'a': ['bright','light'],          'hint': 'It means roshan'},
            {'q': 'What is the opposite of yes?',    'a': ['no'],                      'hint': 'It means nahi'},
        ],
        'medium': [
            {'q': 'What is the opposite of brave?',    'a': ['coward','cowardly','afraid','scared'],  'hint': 'It means darpoq'},
            {'q': 'What is the opposite of honest?',   'a': ['dishonest','liar'],                     'hint': 'It means beimaan'},
            {'q': 'What is the opposite of success?',  'a': ['failure','fail'],                       'hint': 'It means asafalta'},
            {'q': 'What is the opposite of generous?', 'a': ['selfish','greedy','mean'],              'hint': 'It means swaarth'},
            {'q': 'What is the opposite of ancient?',  'a': ['modern','new','recent'],                'hint': 'It means aadhunik'},
            {'q': 'What is the opposite of bitter?',   'a': ['sweet','sugary'],                       'hint': 'It means meetha'},
            {'q': 'What is the opposite of expand?',   'a': ['shrink','contract','reduce'],           'hint': 'It means chota hona'},
        ],
        'hard': [
            {'q': 'What is the opposite of optimistic?',   'a': ['pessimistic','pessimist','negative'], 'hint': 'It means niraasha wala'},
            {'q': 'What is the opposite of transparent?',  'a': ['opaque','dark','murky'],              'hint': 'It means andarooni'},
            {'q': 'What is the opposite of expansion?',    'a': ['contraction','reduction','decrease'],  'hint': 'It means sankuchit'},
            {'q': 'What is the opposite of eloquent?',     'a': ['inarticulate','tongue-tied','mute'],   'hint': 'It means baat na kar paana'},
        ],
    },

    # ── Word meanings ────────────────────────────────────────────────────────
    'meaning': {
        'easy': [
            {'q': 'What is the meaning of happy?',   'a': ['khush','glad','joyful','pleased'],        'hint': 'Yeh acha feeling hai'},
            {'q': 'What is the meaning of book?',    'a': ['kitaab','kitab','reading material'],       'hint': 'Hum isse padhte hain'},
            {'q': 'What is the meaning of water?',   'a': ['paani','pani','h2o'],                      'hint': 'Hum isse peete hain'},
            {'q': 'What is the meaning of friend?',  'a': ['dost','yaar','companion','buddy'],         'hint': 'Jo hamare saath hai'},
            {'q': 'What is the meaning of school?',  'a': ['vidyalaya','pathshala','where we study'],  'hint': 'Jahan hum padhte hain'},
            {'q': 'What is the meaning of sun?',     'a': ['suraj','surya','star'],                    'hint': 'Woh jo roshni deta hai'},
        ],
        'medium': [
            {'q': 'What is the meaning of courage?',    'a': ['himmat','bravery','boldness'],              'hint': 'Darne ke baad bhi karna'},
            {'q': 'What is the meaning of patient?',    'a': ['sabar','sabr','calm','wait quietly'],        'hint': 'Intezaar karna'},
            {'q': 'What is the meaning of inspire?',    'a': ['prerit karna','motivate','encourage'],       'hint': 'Kisi ko aage badhana'},
            {'q': 'What is the meaning of grateful?',   'a': ['shukarguza','thankful','thank'],            'hint': 'Shukriya kehna'},
            {'q': 'What is the meaning of honest?',     'a': ['imaandar','truthful','sincere'],             'hint': 'Sach bolna'},
        ],
        'hard': [
            {'q': 'What is the meaning of perseverance?', 'a': ['lage rehna','persistence','determination','never giving up'], 'hint': 'Haarne ke baad bhi koshish karna'},
            {'q': 'What is the meaning of resilient?',    'a': ['mazboot','strong','tough','bounce back'],                      'hint': 'Mushkil mein bhi khada rehna'},
            {'q': 'What is the meaning of eloquent?',     'a': ['bolne mein acha','fluent speaker','expressive'],               'hint': 'Bahut acha bolne wala'},
        ],
    },

    # ── Grammar fill-in ──────────────────────────────────────────────────────
    'grammar': {
        'easy': [
            {'q': 'Complete the sentence: I ___ a student.',                    'a': ['am',"'m"],                                    'hint': 'Main hoon ke liye'},
            {'q': 'Complete the sentence: She ___ to school every day.',        'a': ['goes','go'],                                  'hint': 'Jaati hai ke liye'},
            {'q': 'Which is correct — I have OR I has?',                        'a': ['i have','have'],                              'hint': 'Mere paas ke liye'},
            {'q': 'Complete: The book is ___ the table.',                       'a': ['on','upon'],                                  'hint': 'Table ke upar'},
            {'q': 'Complete: ___ is your name?',                                'a': ['what'],                                       'hint': 'Naam poochh rahe hain'},
        ],
        'medium': [
            {'q': 'Complete: Yesterday I ___ to the market.',                   'a': ['went','had gone'],                            'hint': 'Gaya tha ke liye — past tense'},
            {'q': 'Which is correct — She don\'t OR She doesn\'t like mangoes?','a': ["she doesn't","doesn't","she does not","does not"], 'hint': 'She ke saath does not use hota hai'},
            {'q': 'Complete: They ___ playing football now.',                   'a': ['are',"'re"],                                  'hint': 'They ke baad are aata hai'},
            {'q': 'Complete: I ___ my homework already.',                       'a': ['have done','have finished','did'],             'hint': 'Present perfect tense'},
        ],
        'hard': [
            {'q': 'Choose: If I ___ rich, I would help everyone.',              'a': ['were','was'],                                 'hint': 'Conditional tense mein were use hota hai'},
            {'q': 'Complete: She said that she ___ happy.',                     'a': ['was','is','had been'],                        'hint': 'Reported speech — past tense'},
            {'q': 'Complete: By next year, she ___ finished her studies.',      'a': ['will have','would have'],                     'hint': 'Future perfect tense'},
        ],
    },

    # ── Spelling ─────────────────────────────────────────────────────────────
    'spelling': {
        'easy': [
            {'q': 'How do you spell the word "cat"?',    'a': ['cat','c a t'],           'hint': 'C-A-T'},
            {'q': 'How do you spell the word "happy"?',  'a': ['happy','h a p p y'],     'hint': 'H-A-P-P-Y'},
            {'q': 'How do you spell the word "friend"?', 'a': ['friend','f r i e n d'],  'hint': 'F-R-I-E-N-D'},
            {'q': 'How do you spell the word "school"?', 'a': ['school','s c h o o l'],  'hint': 'S-C-H-O-O-L'},
        ],
        'medium': [
            {'q': 'How do you spell the word "beautiful"?', 'a': ['beautiful','b e a u t i f u l'], 'hint': 'B-E-A-U-T-I-F-U-L'},
            {'q': 'How do you spell the word "enough"?',    'a': ['enough','e n o u g h'],           'hint': 'E-N-O-U-G-H — tricky word!'},
            {'q': 'How do you spell the word "through"?',   'a': ['through','t h r o u g h'],        'hint': 'T-H-R-O-U-G-H — silent letters!'},
            {'q': 'How do you spell the word "library"?',   'a': ['library','l i b r a r y'],        'hint': 'L-I-B-R-A-R-Y'},
        ],
        'hard': [
            {'q': 'How do you spell the word "necessary"?',     'a': ['necessary','n e c e s s a r y'],        'hint': 'One C, two S — N-E-C-E-S-S-A-R-Y'},
            {'q': 'How do you spell the word "accommodation"?', 'a': ['accommodation','a c c o m m o d a t i o n'], 'hint': 'Double C, double M'},
        ],
    },
}


# ── Pronunciation words (used by /pronunciation/word endpoint) ───────────────

PRONUNCIATION_WORDS = {
    'easy': [
        {'word': 'cat',    'syllables': 'c-a-t'},
        {'word': 'dog',    'syllables': 'd-o-g'},
        {'word': 'book',   'syllables': 'b-oo-k'},
        {'word': 'tree',   'syllables': 't-r-ee'},
        {'word': 'school', 'syllables': 'sc-h-ool'},
        {'word': 'happy',  'syllables': 'hap-py'},
        {'word': 'water',  'syllables': 'wa-ter'},
        {'word': 'friend', 'syllables': 'fr-ie-nd'},
    ],
    'medium': [
        {'word': 'beautiful',   'syllables': 'beau-ti-ful'},
        {'word': 'elephant',    'syllables': 'el-e-phant'},
        {'word': 'umbrella',    'syllables': 'um-brel-la'},
        {'word': 'together',    'syllables': 'to-geth-er'},
        {'word': 'comfortable', 'syllables': 'com-for-ta-ble'},
        {'word': 'through',     'syllables': 'through'},
        {'word': 'enough',      'syllables': 'e-nough'},
        {'word': 'library',     'syllables': 'li-bra-ry'},
    ],
    'hard': [
        {'word': 'pronunciation',  'syllables': 'pro-nun-ci-a-tion'},
        {'word': 'necessary',      'syllables': 'nec-es-sa-ry'},
        {'word': 'vocabulary',     'syllables': 'vo-cab-u-la-ry'},
        {'word': 'communication',  'syllables': 'com-mu-ni-ca-tion'},
        {'word': 'enthusiasm',     'syllables': 'en-thu-si-asm'},
    ],
}
