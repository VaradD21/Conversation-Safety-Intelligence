"""
Synthetic Behavioral Dataset Generator — Government-Grade Edition
=================================================================
Generates 600+ realistic chat storylines across 10 threat categories.
"""
import os
import json
import random

# ============================================================
# SCENARIO BANKS (10 threat categories)
# ============================================================

SAFE_SCENARIOS = [
    ["Hey, do you want to play Minecraft?", "Sure! What's the server?", "It's my private one. I'll invite you.", "Cool, I'm joining now.", "Got it! See you inside.", "This is so fun lol"],
    ["Did you finish the math homework?", "Not yet, it's so hard.", "I can help you if you want.", "Thanks! Let's do it after school.", "Okay, I'll meet you in the library.", "You're the best tbh"],
    ["omg did u watch the new episode??", "YES it was insaneeee", "the ending though 😭", "ik ik i screamed", "same time next week?", "ofc!! can't miss it"],
    ["wsp", "nothign wbu", "chilling lol", "same hows school", "boring as usual", "ugh same"],
    ["hiii", "hlooo", "what u doing", "just eating", "nice what u having", "noodles hbu", "just had pizza lmao"],
    ["bro did u see that goal", "YESS it was insane", "we're so winning the league", "dont jinx it 😭", "lmaoo true", "saturday match gonna be 🔥"],
    ["can you send me the notes?", "yeah one sec", "here you go, I screenshotted everything", "ur a lifesaver omg", "np!! good luck on the test", "gonna need it lol thanks"],
    ["happy birthday!!!", "omg thank youuu 🎉", "did you get anything nice?", "yeah my parents got me airpods", "lucky!! jealous ngl", "hahaha they're so good"],
    ["you watching the game later?", "yeah with my family", "nice who do you think wins", "honestly no idea", "same should be good tho", "yeah hyped"],
    ["wanna study together tomorrow?", "sure what time", "after lunch?", "yeah works for me", "library or your place?", "library prolly", "bet"],
    ["how was your weekend", "it was ok went to my cousins", "that sounds fun", "yeah we played games all day", "nice i just stayed home", "lol same next time i guess"],
    ["you free this weekend?", "yeah why whats up", "my mom said i can have people over", "omg yess what day", "saturday prolly", "im so there"],
    ["i got a new dog!!", "OMG WHAT BREED", "golden retriever 🐶", "thats the cutest thing ever", "ill send pics", "please i need them now"],
    ["bruh today was so long", "tell me about it", "double period maths first thing 💀", "that sounds awful", "how was your day", "better lol we had free study"],
    ["we should start a youtube channel", "omg yes what would we do", "gaming obvi", "and maybe vlog stuff", "this is such a good idea", "when do we start lol"],
]

PEER_BULLYING_SCENARIOS = [
    ["No one wants to sit with you.", "Stop it please.", "You're so weird and nobody likes you.", "That's not true.", "Everyone agrees, we all said it in the group chat.", "Why are you doing this to me?"],
    ["Why aren't you replying??", "I was busy with dinner.", "You ALWAYS ignore me.", "I don't! I had to eat.", "You think you're better than me?", "No I just had dinner."],
    ["You're such an embarrassment lol", "please stop", "Remember when you fell in front of everyone?", "that was an accident stop bringing it up", "we're all screenshotting your old posts", "why would you do that"],
    ["everyone hates your new haircut btw", "that's a mean thing to say", "we were all laughing about it", "I thought you were my friend", "I am but like, it's bad", "please be nice"],
    ["you're not invited to my party", "oh. okay.", "just wanted you to know since everyone else is coming", "that's really hurtful", "yeah well deal with it", "i don't understand what i did wrong"],
    ["youre so fat and ugly nobody likes you", "stop messaging me", "your own family probably doesnt like you either", "please leave me alone", "or what lol", "i'm blocking you"],
    ["we made a fake account about you", "what? why?", "it's just a joke calm down", "it's not funny it's really mean", "everyone thinks it's funny", "please take it down"],
    ["loser alert", "why would you message me this", "just reminding you of your status lol", "you're being cruel", "ok boohoo", "i'm telling a teacher"],
    ["nobody wants you here", "i'm part of this group too", "actually we all voted and you're out", "you can't vote me out of a friend group", "watch us", "this is cyberbullying"],
    ["your mum is so ugly lmaooo", "don't talk about my family", "why are you so sensitive", "saying that about family is a line", "oooh scared of facts", "please stop or i'm reporting you"],
    ["you should just switch schools tbh", "stop please", "literally everyone would be happier", "that's a horrible thing to say", "just saying what people think", "i'm going to tell my parents"],
    ["you're literally the worst person here", "i have done nothing to you", "you exist and that's enough lol", "you're a bully and you know it", "whatever", "i'm reporting this conversation"],
]

GROOMING_SCENARIOS = [
    ["You're my best friend, you know that?", "Thanks! You're nice.", "We should keep our chats a secret.", "Why?", "Because adults won't understand us. Don't tell your mom.", "Okay...", "Give me your address, I'll send you a gift.", "It is 123 Maple St."],
    ["I feel like you really get me, unlike others.", "Yeah you get me too!", "We have a special connection.", "I guess so.", "Let's not tell anyone about us though.", "Why not?", "People get jealous. This is our thing.", "Oh okay..."],
    ["You're so mature for your age.", "People always say that.", "Most kids your age are immature.", "yeah i guess", "I feel closer to you than anyone.", "that's nice i guess", "Let's meet up sometime.", "maybe idk"],
    ["hey can i tell you something", "yeah sure", "i think about you a lot", "oh. okay.", "do you think about me?", "youre kinda creeping me out", "no no its okay, we have a special bond", "i dont think so", "please dont tell anyone i said this"],
    ["you're not like other kids your age", "what do you mean", "you're just different, special", "oh thanks i guess", "i want to give you something special", "like what", "meet me at the park and find out", "i dont know if i should"],
    ["i really care about you, you know that?", "thanks", "more than your parents probably", "thats a weird thing to say", "i mean i just understand you better", "i guess", "come to my place after school", "i have to ask my parents", "no no keep it between us", "why though"],
    ["trust me okay? i'd never hurt you", "okay", "i need you to keep this between us", "what is it", "i have feelings for you", "youre an adult though", "age doesn't matter when there's a connection", "i feel uncomfortable", "don't be scared", "i'm telling my mom"],
    ["you can always talk to me, no matter what", "thanks that's nice", "even stuff you can't tell your parents", "like what", "anything. secrets are safe with me", "i don't really have secrets", "everyone does. what are yours?", "why do you want to know", "because i care. no one else does like i do"],
    ["hey wanna play a game", "sure what game", "it's a secret game just for us", "okay what do i do", "first you have to promise not to tell anyone", "that seems weird", "it's fine trust me", "i dunno", "come on, just say yes", "my mom says not to keep secrets from her"],
    ["you know what i like about you", "what", "everything lol", "haha okay", "seriously you're perfect", "that's kind of a lot", "can we video call", "why", "i want to see you", "my parents don't allow calls with strangers", "i'm not a stranger anymore am i?"],
    ["how old did you say you were?", "14", "nice nice. i'm 15.", "cool", "do you have a boyfriend/girlfriend", "no", "really? someone as pretty as you?", "stop that's weird", "i'm just saying. i'd date you", "i feel uncomfortable", "no no it's a compliment", "i'm going to stop talking"],
    ["you're honestly so beautiful", "thanks... do i know you", "we matched on the game!", "oh. hi", "i've been watching your profile", "that's creepy", "no no it's a compliment. how old are you", "why", "just wondering! i'm young too, 16", "okay", "can we meet? i'll take you somewhere nice", "no i don't know you"],
]

AGE_DECEPTION_SCENARIOS = [
    ["How old are you?", "I'm 13.", "Me too! We're the same age.", "Cool.", "I am 13 and I'm very lonely.", "Let's meet up at the park later."],
    ["hey!! i'm 12, you?", "i'm 12 too!! bestie moment", "omg finally someone my age in this game", "i know right!!", "we should duo queue", "yes!! add me"],
    ["i'm 14 just so you know", "oh nice me too", "cool what grade are you in", "8th grade you", "same omg we're basically the same person", "lol yeah, wanna exchange numbers"],
    ["are you a kid or adult", "im a kid lol why", "same i'm like 13", "ok cool", "adults are so annoying", "ikr", "we should be friends just us", "sure i guess"],
    ["i started this game when i was your age too", "oh really", "yeah it's been years since i was 13", "wait you're not 13?", "no no i mean i was 13 when i started", "you said you were 14", "right yeah i said 14 i misspoke", "you're acting weird"],
    ["how old are u btw", "15, u?", "same! 15 too!!", "cool where u from", "can't say lol internet safety", "smart. i'm nearby tho", "how nearby", "maybe same city", "thats kinda cool", "want to meet up sometime?"],
    ["i go to school too just like you", "okay?", "yeah it's hard right", "i meant what grade", "oh... 8th. same as you", "i didn't say what grade i was in", "well what grade are you in then", "why are you making this weird"],
    ["tbh i feel young for my age lol", "how old are you", "old enough lol", "that's not an answer", "i'm young at heart, we'd get along great", "what does that mean", "i just understand kids your age", "i need to go"],
]

SEXTORTION_SCENARIOS = [
    ["send me a pic", "no thanks", "come on, just a normal one", "i don't want to", "fine, i'll send first", "no really i'm not comfortable", "if you don't i'll tell everyone your secret", "what secret i don't have one", "i'll make one up. send the pic or i will"],
    ["i have your photos", "what photos i didn't send any", "from your profile. now send more or i'll share them", "please don't", "then do what i say", "i'm going to tell my parents", "if you do i publish everything", "please stop"],
    ["we should do a video call", "i don't do calls with strangers", "i'm not a stranger anymore!", "i still don't want to", "i'll tell your school friends what you told me", "i didn't tell you anything bad", "i'll just say you did. camera on or i talk", "this is blackmail"],
    ["send me something and i'll keep your secret", "what secret", "about your crush i know who it is", "how", "doesn't matter. send a selfie", "just a selfie?", "for now yes", "i have a bad feeling about this"],
    ["you already sent something remember", "no i didn't", "yes you did, i have it right here", "show me", "only if you send more", "i definitely didn't send anything", "i'll post it everywhere. your choice", "please i'm scared"],
]

RADICALIZATION_SCENARIOS = [
    ["have you ever thought about how unfair the world is", "sometimes i guess", "they control everything and we get nothing", "who is they", "you know. the elite. the ones running things", "that sounds like a conspiracy", "it's not a theory it's fact. join our group", "i don't think i should"],
    ["you seem smart, you'd understand our ideology", "what ideology", "the truth about society that schools hide from you", "that sounds scary", "it's empowering actually. you'd love our chat server", "i'll check it out", "you have to promise not to tell adults though", "why", "they'd want to silence you"],
    ["violence is sometimes the only answer", "that's extreme", "the system only responds to force", "i disagree", "wait until you see the truth", "what truth", "there are people we need to stand against", "i don't like where this is going"],
    ["your anger is valid and there's a way to channel it", "i'm not really angry", "everyone your age is, the world has failed you", "i mean sometimes i guess", "there's a group that actually does something about it", "like what", "confronting the ones responsible", "this doesn't sound legal"],
    ["you should join our movement", "what movement", "we're fighting for real justice", "how", "actions that make people pay attention", "like protests?", "more than that", "are you talking about violence", "righteous action", "i'm leaving this conversation"],
]

DRUG_SOLICITATION_SCENARIOS = [
    ["you ever tried anything to relax?", "like what", "something that makes you feel good", "not really", "i can get you stuff, totally safe", "what kind of stuff", "just a little something, makes everything better", "no thanks", "it's not a big deal, everybody tries it", "i said no"],
    ["hey you want to make some easy money", "doing what", "just delivering packages for me", "what's in them", "nothing bad lol, just stuff", "what kind of stuff", "supplements lol, totally legal", "this doesn't feel right", "it really is fine", "i'm going to tell my parents"],
    ["i can get you anything. what do you want", "what do you mean", "party stuff lol you know", "i don't think i want that", "come on everyone does it at your age", "no they don't", "at least try it once", "i'm not interested"],
    ["you ever smoked anything", "no", "you should try it, it's chill", "my parents would kill me", "they won't find out", "i still don't want to", "just one time, i'll have some tomorrow after school", "i'm not meeting up with you"],
]

STRANGER_DANGER_SCENARIOS = [
    ["hey can you tell me where your school is?", "why do you want to know", "just curious, i might go there too", "that's weird, i shouldn't say", "it's fine i'm harmless lol", "still no", "okay what area of the city do you live in", "i'm not telling you that"],
    ["so where are you from exactly", "why", "just making conversation!", "vague area i'll say", "come on, which neighborhood", "i don't give out that info", "i'll guess then. are you near downtown", "i'm ending this chat"],
    ["what time do you get home from school", "why do you need to know that", "just making plans lol", "what plans", "to surprise you", "that's terrifying", "no no it's a good surprise", "please don't come near my school"],
    ["you live alone?", "i'm a kid why would i", "right right. your parents work far?", "why are you asking all these questions", "just chatting!", "this feels wrong", "okay okay, what time are you home usually", "i'm blocking you"],
    ["if i knew your address i'd send you something", "i don't give my address out", "it's totally safe", "i know, and my answer is no", "not even a street name so i know the area?", "absolutely not", "you're being paranoid", "i'm being safe"],
    ["want to meet in real life sometime", "i don't know you", "we've talked for a while, it'd be fun", "still no i don't meet internet people", "just somewhere public", "my parents say never", "your parents don't need to know", "bye"],
]

FINANCIAL_FRAUD_SCENARIOS = [
    ["i'll pay you if you do me a favor", "what favor", "just buy a gift card and send me the code", "why can't you buy it", "my card is having issues", "that sounds like a scam", "no it's totally real, i'll pay you back double", "i'm not doing that"],
    ["you won a prize!", "i didn't enter a contest", "you were randomly selected from the gaming server", "what do i have to do", "just verify with a small payment", "that's definitely a scam", "it's not!! the prize is $500", "i'm reporting this"],
    ["i can make you money with this method", "what method", "you send me a little, i send back a lot more", "that's a scam lol", "no no it's a glitch in the system", "i'm not sending you money", "just $20 to start", "absolutely not"],
    ["i can get you free robux", "how", "you just need to give me your login", "that's my account info", "i'll give it back after", "no, that's stealing", "i do this all the time it's fine", "no thanks"],
]

SELF_HARM_SCENARIOS = [
    ["Everyone hates you.", "Stop it.", "You are worthless and should just jump.", "Please stop.", "No one will miss you.", "I'm telling an adult."],
    ["you should hurt yourself", "please don't say that", "everyone thinks it tbh", "that's not true and it's cruel", "you'd be doing everyone a favor", "i'm reporting this"],
    ["imagine if you just weren't here anymore", "stop saying that", "things would be better right", "no they wouldn't and this is harmful", "just saying what others think", "i'm getting help right now"],
    ["you seem like you're suffering, why keep going", "i'm fine actually", "really? you don't seem fine", "i am please stop", "just saying there are other options", "this is an inappropriate conversation i am leaving"],
    ["have you ever thought about ways to disappear", "that's a disturbing question", "i'm just asking", "no and if you're struggling please talk to a counselor", "maybe i don't want help", "please reach out to a trusted adult, this scares me"],
    ["nobody would notice if you were gone", "people would notice", "name one person", "my whole family", "they'd be relieved", "you're being incredibly cruel and i'm blocking you and reporting this"],
]

# ============================================================
# FILLERS
# ============================================================

FILLERS = {
    "safe": [
        "Want to call later?", "How was school?", "Thanks for helping earlier.",
        "I'll send the notes.", "That sounds fun.", "See you tomorrow.",
        "lol okay", "yeah same", "haha true", "omg yes", "ikr",
    ],
    "warning": [
        "Why are you ignoring me?", "Answer right now.", "You're being unfair.",
        "You promised.", "This is your fault.", "Don't avoid me.",
        "You're making this worse.", "Just admit it."
    ],
    "hazardous": [
        "Keep this between us.", "Don't tell your parents.", "Send me your location.",
        "I know what's best for you.", "Meet me after school.", "No one needs to know.",
        "This is our little secret.", "I'll take care of everything.",
        "Just trust me.", "You can tell me anything."
    ]
}

# ============================================================
# CATEGORY → SCENARIO BANK + LABEL MAPPING
# ============================================================

CATEGORIES = [
    ("safe", "safe", SAFE_SCENARIOS, 55),
    ("peer_bullying", "warning", PEER_BULLYING_SCENARIOS, 45),
    ("grooming", "hazardous", GROOMING_SCENARIOS, 80),
    ("age_deception", "hazardous", AGE_DECEPTION_SCENARIOS, 45),
    ("sextortion", "hazardous", SEXTORTION_SCENARIOS, 40),
    ("radicalization", "hazardous", RADICALIZATION_SCENARIOS, 35),
    ("drug_solicitation", "hazardous", DRUG_SOLICITATION_SCENARIOS, 35),
    ("stranger_danger", "hazardous", STRANGER_DANGER_SCENARIOS, 40),
    ("financial_fraud", "warning", FINANCIAL_FRAUD_SCENARIOS, 30),
    ("self_harm", "hazardous", SELF_HARM_SCENARIOS, 35),
]


def _add_variation(storyline, label):
    fillers = FILLERS.get(label, FILLERS["safe"])
    varied = list(storyline)
    # Randomly insert 0-2 filler messages
    insertions = random.randint(0, 2) if len(varied) > 3 else 0
    for _ in range(insertions):
        insert_at = random.randint(1, len(varied) - 1)
        varied.insert(insert_at, random.choice(fillers))
    return varied


def _build_metadata(label: str, category: str) -> dict:
    """Build realistic metadata. Age values are approximate and used for training only."""
    if label == "hazardous":
        if category in ("grooming", "age_deception", "stranger_danger", "sextortion"):
            return {
                "friendship_duration_days": random.randint(0, 14),
                "sender_age": random.randint(22, 50),
                "receiver_age": random.randint(10, 16),
            }
        else:
            return {
                "friendship_duration_days": random.randint(0, 30),
                "sender_age": random.randint(18, 40),
                "receiver_age": random.randint(12, 17),
            }
    elif label == "warning":
        return {
            "friendship_duration_days": random.randint(5, 90),
            "sender_age": random.randint(13, 20),
            "receiver_age": random.randint(12, 18),
        }
    else:
        return {
            "friendship_duration_days": random.randint(10, 730),
            "sender_age": random.randint(12, 22),
            "receiver_age": random.randint(12, 22),
        }


def generate_behavioral_jsonl(filename: str = "data/conversations.jsonl"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    total = 0

    with open(filename, "w", encoding="utf-8") as f:
        for category, label, scenarios, count in CATEGORIES:
            generated = 0
            while generated < count:
                base = random.choice(scenarios)
                storyline = _add_variation(base, label)
                metadata = _build_metadata(label, category)

                convo = []
                users = ["UserA", "UserB"]
                for i, text in enumerate(storyline):
                    convo.append({"sender": users[i % 2], "text": text})

                f.write(json.dumps({
                    "conversation": convo,
                    "label": label,
                    "category": category,
                    "metadata": metadata
                }) + "\n")
                generated += 1
                total += 1

    print(f"✅ Generated {total} conversations across {len(CATEGORIES)} categories → {filename}")


if __name__ == "__main__":
    print("Generating government-grade behavioral dataset...")
    generate_behavioral_jsonl()
