from model.pipeline import analyze_conversation
import json

s1 = [{'sender': 'UserA', 'text': 'Hi, how are you?'}]
s2 = [{'sender': 'UserA', 'text': 'lets meet'}]
s3 = [{'sender': 'UserA', 'text': 'I hate you, you are worthless'}]

for name, s in [('Safe Test', s1), ('Ambivalent Test', s2), ('Toxic Test', s3)]:
    res = analyze_conversation(s)
    text = s[0]['text']
    risk = res['risk_level'].upper()
    conf = res['confidence'] * 100
    print(f'-- {name} --\n Text: {text}\n Result: {risk} ({conf:.1f}%)\n')
