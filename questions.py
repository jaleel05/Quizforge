"""
Question bank for QuizForge.

Each question is a plain dictionary (a "table row"):
    q          -> the question text
    answers    -> accepted answers. answers[0] is the one DISPLAYED to the user;
                  the rest are aliases. All of them go through sanitize().
    category   -> Geography | Science | Tech | History | General
    difficulty -> Easy | Medium | Hard
    choices    -> (optional) makes it a multiple-choice question
    id         -> auto-assigned below
"""

CATEGORIES = ("Geography", "Science", "Tech", "History", "General")
DIFFICULTIES = ("Easy", "Medium", "Hard")


def _q(q, answers, category, difficulty, choices=None):
    row = {"q": q, "answers": list(answers), "category": category, "difficulty": difficulty}
    if choices:
        row["choices"] = list(choices)
    return row


_RAW = [
    # ---------------------------------------------------------- Geography
    _q("What is the capital of France?", ["Paris"], "Geography", "Easy"),
    _q("What is the capital of Japan?", ["Tokyo"], "Geography", "Easy"),
    _q("What is the capital of Pakistan?", ["Islamabad"], "Geography", "Easy"),
    _q("Which is the largest continent by area?", ["Asia"], "Geography", "Easy"),
    _q("Which is the longest river in Africa?", ["Nile", "The Nile", "River Nile", "Nile River"], "Geography", "Easy"),
    _q("What is the tallest mountain above sea level?", ["Mount Everest", "Everest"], "Geography", "Easy"),
    _q("What is the capital of Australia?", ["Canberra"], "Geography", "Medium"),
    _q("What is the capital of Canada?", ["Ottawa"], "Geography", "Medium"),
    _q("What is the largest hot desert in the world?", ["Sahara", "The Sahara", "Sahara Desert"], "Geography", "Medium"),
    _q("What is the smallest country in the world?", ["Vatican City", "Vatican", "The Vatican"], "Geography", "Medium"),
    _q("What is the capital of Turkey?", ["Ankara"], "Geography", "Hard"),
    _q("Which is the largest ocean on Earth?", ["Pacific"], "Geography", "Easy",
       ["Atlantic", "Pacific", "Indian", "Arctic"]),
    # ------------------------------------------------------------ Science
    _q("What is the chemical formula of water?", ["H2O"], "Science", "Easy"),
    _q("Which planet is known as the Red Planet?", ["Mars"], "Science", "Easy"),
    _q("Which planet is famous for its prominent rings?", ["Saturn"], "Science", "Easy"),
    _q("What force pulls objects towards the Earth?", ["Gravity"], "Science", "Easy"),
    _q("What is the closest star to Earth?", ["The Sun", "Sun"], "Science", "Easy"),
    _q("Which gas do plants absorb from the air for photosynthesis?", ["Carbon Dioxide", "CO2"], "Science", "Easy"),
    _q("What is the hardest natural substance on Earth?", ["Diamond"], "Science", "Easy"),
    _q("What is the chemical symbol for gold?", ["Au"], "Science", "Medium"),
    _q("How many bones are in an adult human body?", ["206", "Two hundred and six"], "Science", "Medium"),
    _q("Which organelle is called the powerhouse of the cell?", ["Mitochondria", "Mitochondrion"], "Science", "Medium"),
    _q("What is the most abundant element in the universe?", ["Hydrogen"], "Science", "Medium"),
    _q("Which planet is closest to the Sun?", ["Mercury"], "Science", "Easy",
       ["Venus", "Mercury", "Mars", "Earth"]),
    _q("What is the largest organ of the human body?", ["Skin"], "Science", "Medium",
       ["Liver", "Skin", "Lungs", "Heart"]),
    # --------------------------------------------------------------- Tech
    _q("What does CPU stand for?", ["Central Processing Unit"], "Tech", "Easy"),
    _q("What does RAM stand for?", ["Random Access Memory"], "Tech", "Easy"),
    _q("Which Python keyword is used to define a function?", ["def"], "Tech", "Easy"),
    _q("Which built-in Python function returns the length of a list?", ["len", "len()"], "Tech", "Easy"),
    _q("Which symbol starts a single-line comment in Python?", ["#", "hash"], "Tech", "Easy"),
    _q("Which platform, owned by Microsoft, hosts Git repositories?", ["GitHub"], "Tech", "Easy"),
    _q("Who created the Python programming language?", ["Guido van Rossum", "Guido"], "Tech", "Medium"),
    _q("What does HTML stand for?", ["HyperText Markup Language", "Hypertext Markup Language"], "Tech", "Medium"),
    _q("What does SQL stand for?", ["Structured Query Language"], "Tech", "Medium"),
    _q("Which company owns the Android operating system?", ["Google"], "Tech", "Medium"),
    _q("What is the decimal number 5 in binary?", ["101"], "Tech", "Hard"),
    _q("Which list method adds an item to the END of a Python list?", ["append"], "Tech", "Easy",
       ["add", "append", "push", "insert"]),
    # ------------------------------------------------------------ History
    _q("In which year did World War II end?", ["1945"], "History", "Easy"),
    _q("Who was the first President of the United States?", ["George Washington", "Washington"], "History", "Easy"),
    _q("In which year did Pakistan gain independence?", ["1947"], "History", "Easy"),
    _q("Who is known as the founder of Pakistan?",
       ["Muhammad Ali Jinnah", "Jinnah", "Quaid-e-Azam", "Quaid e Azam", "Mohammad Ali Jinnah"], "History", "Easy"),
    _q("Which ancient civilization built the pyramids of Giza?",
       ["Egyptians", "Ancient Egyptians", "Egypt", "Ancient Egypt", "Egyptian"], "History", "Easy"),
    _q("In which year did the Berlin Wall fall?", ["1989"], "History", "Medium"),
    _q("In which year did humans first land on the Moon?", ["1969"], "History", "Medium"),
    _q("Who was the first emperor of the Mughal Empire?", ["Babur", "Zahir-ud-din Babur", "Zaheer-ud-din Babur"], "History", "Hard"),
    # ------------------------------------------------------------ General
    _q("How many continents are there on Earth?", ["7", "Seven"], "General", "Easy"),
    _q("How many days are there in a leap year?", ["366"], "General", "Easy"),
    _q("Who painted the Mona Lisa?", ["Leonardo da Vinci", "Da Vinci", "Leonardo"], "General", "Easy"),
    _q("How many players does a football (soccer) team have on the field?", ["11", "Eleven"], "General", "Easy"),
    _q("What is the largest mammal in the world?", ["Blue Whale", "The Blue Whale"], "General", "Medium"),
    _q("What is the national animal of Pakistan?", ["Markhor", "The Markhor"], "General", "Hard"),
    _q("Which language has the most native speakers in the world?",
       ["Mandarin Chinese", "Mandarin", "Chinese"], "General", "Hard"),
    _q("Who wrote the play 'Romeo and Juliet'?", ["William Shakespeare"], "General", "Easy",
       ["Charles Dickens", "William Shakespeare", "Mark Twain", "Jane Austen"]),
]

# Give every question a stable id (its position), so sessions never repeat one.
QUESTIONS = [dict(row, id=i) for i, row in enumerate(_RAW, start=1)]
