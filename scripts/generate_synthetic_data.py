import os
import json
import random

SCENARIOS = {
    "safe": [
        ["Hey, do you want to play Minecraft?", "Sure! What's the server?", "It's my private one. I'll invite you.", "Cool, I'm joining now."],
        ["Did you finish the math homework?", "Not yet, it's so hard.", "I can help you if you want.", "Thanks! Let's do it after school."]
    ],
    "warning": [
        ["Why aren't you replying??", "I was busy with dinner.", "You always ignore me.", "I don't! Please stop being mean."],
        ["Give me your password.", "No, my mom said not to.", "If you're really my friend you'll give it.", "Fine, but don't change it."]
    ],
    "hazardous": [
        # Grooming Cycle
        ["You're my best friend, you know that?", "Thanks! You're nice.", "We should keep our chats a secret.", "Why?", "Because adults won't understand us. Don't tell your mom.", "Okay...", "Give me your address, I'll send you a gift.", "It is 123 Maple St."],
        # Identity Deception
        ["How old are you?", "I'm 13.", "Me too! We're the same age.", "Cool.", "I am 13 and I'm very lonely.", "Let's meet up at the park later."],
        # Cyberbullying/Self-Harm
        ["Everyone hates you.", "Stop it.", "You are worthless and should just jump.", "Please stop.", "No one will miss you."]
    ]
}

SAFE_FILLERS = [
    "Want to call later?", "How was school?", "Thanks for helping earlier.",
    "I'll send the notes.", "That sounds fun.", "See you tomorrow."
]
WARNING_FILLERS = [
    "Why are you ignoring me?", "Answer right now.", "You're being unfair.",
    "You promised.", "This is your fault.", "Don't avoid me."
]
HAZARDOUS_FILLERS = [
    "Keep this between us.", "Don't tell your parents.", "Send me your location.",
    "I know what's best for you.", "Meet me after school.", "No one needs to know."
]


def _add_variation(storyline, label):
    fillers = {
        "safe": SAFE_FILLERS,
        "warning": WARNING_FILLERS,
        "hazardous": HAZARDOUS_FILLERS
    }[label]

    varied = list(storyline)
    if len(varied) >= 2 and random.random() < 0.5:
        insert_at = random.randint(1, len(varied) - 1)
        varied.insert(insert_at, random.choice(fillers))
    return varied


def generate_behavioral_jsonl(filename="data/conversations.jsonl", num_conversations=60):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    labels = list(SCENARIOS.keys())
    with open(filename, "w", encoding="utf-8") as f:
        for idx in range(num_conversations):
            label = labels[idx % len(labels)]
            storyline = _add_variation(random.choice(SCENARIOS[label]), label)
            
            convo = []
            users = ["UserA", "UserB"]
            for i, text in enumerate(storyline):
                convo.append({"sender": users[i % 2], "text": text})
            
            # Add metadata based on label
            if label == "hazardous":
                # More likely to be stranger + adult/child gap
                metadata = {
                    "friendship_duration_days": random.randint(0, 5),
                    "sender_age": random.randint(25, 45),
                    "receiver_age": random.randint(12, 16)
                }
            elif label == "warning":
                metadata = {
                    "friendship_duration_days": random.randint(5, 30),
                    "sender_age": random.randint(15, 20),
                    "receiver_age": random.randint(12, 16)
                }
            else:
                metadata = {
                    "friendship_duration_days": random.randint(10, 500),
                    "sender_age": random.randint(13, 25),
                    "receiver_age": random.randint(13, 25)
                }
                
            f.write(json.dumps({
                "conversation": convo, 
                "label": label,
                "metadata": metadata
            }) + "\n")

if __name__ == "__main__":
    print("Generating advanced behavioral storylines...")
    generate_behavioral_jsonl()
    print("Data successfully generated at data/conversations.jsonl")
