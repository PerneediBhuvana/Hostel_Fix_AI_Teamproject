"""Labelled training data for the complaint classifier.

Hand-written examples (English + a little Telugu-English, since residents write that way)
plus a small template generator for variety. TEST_SET is kept separate and never trained on.
"""
import random

CATEGORY_EXAMPLES = {
    'Electricity': [
        'Fan not working in my room', 'Ceiling fan making loud noise and running slow',
        'Tube light is flickering all night', 'Power cut in the corridor since morning',
        'Switch board sparking when I plug the charger', 'Socket is loose and not giving power',
        'Bulb fused in the washroom', 'Low voltage, my laptop will not charge',
        'No current in room 204', 'Fan regulator broken', 'Electric shock from the switch',
        'Corridor lights are off, very dark', 'Short circuit smell near the board',
        'Geyser is not heating, no power supply to it', 'Wiring is hanging out of the wall',
        'Room fan speed control not working', 'Current poyindi, lights anni off',
        'Light switch is stuck and does not turn on', 'Inverter not working, power cuts frequent',
        'Plug point near my bed is burnt',
    ],
    'Plumbing': [
        'Tap is leaking continuously', 'Water leak from the ceiling in washroom',
        'Toilet flush is not working', 'Drain is blocked and water is overflowing',
        'Pipe burst near the bathroom wall', 'Wash basin tap is broken',
        'Bathroom shower is not working, pipe leaking', 'Commode is clogged',
        'Water dripping from the pipe under the sink', 'Flush tank keeps running',
        'Bathroom door drain smells and is blocked', 'Tap handle came off in my hand',
        'Sewage coming out of the floor drain', 'Pipe joint leaking in the corridor washroom',
        'Overhead tank pipe leaking on the terrace', 'Western toilet seat broken and flush stuck',
        'Tap lo water leak avtundi', 'Sink is blocked and water is not draining',
        'Water logging near the bathroom due to broken pipe', 'Shower head is broken',
    ],
    'Water': [
        'No water supply in the morning', 'Drinking water is not available on 2nd floor',
        'Water cooler is not working', 'Water tastes bad and smells dirty',
        'Low water pressure on the top floor', 'RO water purifier is not working',
        'Muddy water coming from the taps', 'No hot water for bathing',
        'Water tank is empty, no supply since last night', 'Drinking water has insects',
        'Water supply timing is irregular', 'Borewell motor not working, no water',
        'Yellow coloured water in the bathroom', 'Water dispenser out of order',
        'Neellu raavatledu', 'Water filter needs service, water is smelly',
        'Not enough water for all rooms in the evening', 'Water is not coming in the taps at all',
        'Cold water dispenser leaking and not cooling', 'Salty water supply, cannot drink',
    ],
    'Internet': [
        'WiFi is not working in my room', 'Internet is very slow in the evening',
        'Router is down on the second floor', 'No network signal in the hostel',
        'WiFi keeps disconnecting every few minutes', 'Cannot connect to hostel wifi',
        'Broadband connection not available since yesterday', 'LAN port in room is not working',
        'Wifi password not working', 'Internet speed is too low for online classes',
        'Router lights are blinking red', 'No internet during exams, please fix',
        'WiFi range is poor in corridor end rooms', 'Network keeps dropping while I attend lectures',
        'Wifi slow ga undi', 'Access point is not working near room 305',
        'Wifi login page not opening', 'Internet down for the whole block',
        'Ethernet cable is damaged in my room', 'Wifi signal is weak in my room',
    ],
    'Food': [
        'Stale food served in the mess', 'Food was undercooked at dinner',
        'Found an insect in the lunch rice', 'Breakfast is cold and tasteless',
        'Mess menu is not followed', 'Food quality is very poor, same dishes daily',
        'Hair found in the curry', 'Dinner was served late and cold',
        'Canteen hygiene is bad, plates are dirty', 'Not enough food quantity for everyone',
        'Chapati is raw and hard', 'Curd and milk smelled sour at breakfast',
        'Mess workers not wearing gloves while serving', 'Egg curry had a bad smell',
        'Food poisoning symptoms after eating dinner in mess', 'Lunch is too oily and spicy',
        'Annam lo rallu vachayi, food baagaledu', 'Mess food has no variety, menu repeated',
        'Fruits promised in menu are not given', 'Rice is undercooked and sambar is watery',
    ],
    'Cleaning': [
        'Garbage is not cleared from the floor', 'Washroom is very dirty and not cleaned',
        'Dust everywhere in the corridor', 'Cockroaches in my room, need pest control',
        'Dustbin is overflowing near the stairs', 'Bathroom floor has not been mopped for days',
        'Mosquitoes and bad smell near the drain, need cleaning', 'Room not swept by housekeeping',
        'Rats in the corridor, pest problem', 'Common area is filthy',
        'Sweeper did not come today', 'Spider webs and dust in the staircase',
        'Dirty toilets on the third floor, no cleaning', 'Garbage piled up behind the block',
        'Termites and ants in the room, pest control needed', 'Bed bugs in the mattress area',
        'Corridor ni clean cheyatledu', 'Washroom smells bad, housekeeping not done',
        'Trash bin not emptied for a week', 'Terrace is covered in dust and leaves',
    ],
    'Furniture': [
        'Chair is broken in my room', 'Study table leg is loose',
        'Bed frame is broken and squeaks', 'Cupboard door is off its hinges',
        'Mattress is torn and very old', 'Desk drawer is jammed',
        'Window latch is broken', 'Cot is shaky and unsafe to sleep on',
        'Wardrobe lock is not working', 'Bookshelf shelf has collapsed',
        'Room door will not close properly', 'Broken study chair, back support missing',
        'Table top has a big crack', 'Curtain rod fell down in my room',
        'Mirror in the room is broken', 'Locker in my cupboard has no key',
        'Bed virigindi, marokati kavali', 'Window glass is cracked',
        'Need a new chair, the old one is damaged', 'Notice board in room is falling off the wall',
    ],
    'Security': [
        'Main gate guard is not present at night', 'My phone was stolen from the room',
        'Unknown people entering the hostel at night', 'Lock on the hostel gate is broken',
        'CCTV camera is not working in the corridor', 'Theft in room 210, laptop missing',
        'Outsiders roaming around the hostel premises', 'Visitor register is not maintained at the gate',
        'Feeling unsafe walking back at night, no lights or guard', 'Room door lock is broken, anyone can enter',
        'Security guard sleeping on duty', 'Someone tried to break into the cycle shed',
        'Bike stolen from the hostel parking', 'Fire exit door is locked, unsafe',
        'Gate closing time is not followed by the guard', 'Suspicious person near the girls block',
        'Guard lekunda gate open ga undi', 'Wallet was stolen from my cupboard',
        'Boundary wall has a gap, anyone can enter', 'Emergency alarm is not working',
    ],
    'Others': [
        'Need an extension for the hostel fee payment', 'Request to change my room',
        'Noise from the construction next door', 'Laundry service is delayed',
        'Parcel not delivered to my room', 'Request for a new roommate',
        'Sports equipment is missing from the common room', 'Common room TV remote lost',
        'Library timing in the hostel needs to change', 'Ironing facility needed on each floor',
        'Please arrange a bus pickup for weekends', 'Playground has no proper lighting for evening games',
        'Mess bill is wrongly calculated', 'Need a notice about hostel rules',
        'Gym equipment is missing', 'Suggestion to start a reading room',
    ],
}

# Priority examples: sentence -> label
PRIORITY_EXAMPLES = {
    'Urgent': [
        'Fire in the electrical panel, smoke everywhere', 'Short circuit sparking near the bed, danger of fire',
        'Student got an electric shock from the switch', 'Gas smell in the kitchen, possible leak',
        'Food poisoning, several students are vomiting', 'Pipe burst flooding the whole corridor',
        'Stranger inside girls hostel right now', 'Student injured, need help immediately',
        'Ceiling is collapsing in room 105', 'Open live wires hanging in the corridor, emergency',
        'Sewage overflow flooding ground floor rooms', 'Fire exit blocked and alarm is not working, unsafe',
        'Emergency: someone is trapped in the lift', 'Burning smell from the wiring, sparks coming out',
        'Theft happening right now at the gate', 'Mass illness after dinner, many students sick',
    ],
    'High': [
        'No water supply since yesterday morning', 'WiFi is down for the entire block during exams',
        'Power cut in whole floor for two days', 'Toilet is overflowing and not usable',
        'Laptop stolen from room, please act fast', 'Insects found in food served to everyone',
        'Lock of the room is broken, not safe', 'All fans on this floor are not working in the heat',
        'No drinking water available for the whole floor', 'Drain blocked and water entering rooms',
        'Hot water not available for a week for all students', 'Internet not working for everyone since last night',
        'Guard is absent at night for many days', 'Leak from ceiling is getting worse every day',
        'Water cooler not working, students are suffering', 'Fridge in mess broken, food is spoiling',
    ],
    'Medium': [
        'Fan is making noise in my room', 'WiFi is slow in the evening',
        'Tap is leaking slowly', 'Food was cold at dinner',
        'Washroom needs cleaning today', 'Light bulb fused in the room',
        'Router signal is weak in my room', 'Dustbin is full near stairs',
        'Water pressure is low in the morning', 'Window latch is loose',
        'Cupboard door is stuck', 'Mess menu not followed today',
        'Room not swept this morning', 'Switch is not working properly',
        'Wifi disconnects sometimes', 'Shower is dripping',
    ],
    'Low': [
        'Minor scratch on the study table', 'Small crack in the mirror, cosmetic only',
        'Request to change curtain colour', 'Notice board slightly tilted, not urgent',
        'Suggestion to add more books in the reading room', 'Paint peeling a little near the window',
        'Whenever possible, please replace the old chair cushion', 'Minor stain on the wall',
        'Would like an extra shelf, no hurry', 'Small dust on the table in common room',
        'Cosmetic damage on the cupboard handle', 'Suggestion for a better menu variety next month',
        'Request for extra hangers in room', 'Door paint faded, can be done later',
        'Small dent in the dustbin lid', 'Please polish the chair when time permits',
    ],
}

# --- template generator for extra variety (training only) -----------------
_TEMPLATES = {
    'Electricity': (['fan', 'tube light', 'switch board', 'socket', 'bulb', 'power supply', 'regulator', 'charging point'],
                    ['is not working', 'is sparking', 'keeps tripping', 'has stopped working', 'is making a burning smell', 'is flickering']),
    'Plumbing': (['tap', 'flush', 'drain', 'pipe', 'toilet', 'wash basin', 'shower', 'sink'],
                 ['is leaking', 'is blocked', 'is broken', 'is overflowing', 'is clogged', 'has burst']),
    'Water': (['drinking water', 'water supply', 'water cooler', 'RO purifier', 'hot water', 'water tank', 'water dispenser'],
              ['is not available', 'is dirty and smelly', 'has stopped', 'is very low', 'is not coming', 'is out of order']),
    'Internet': (['wifi', 'internet', 'router', 'network', 'broadband', 'LAN port'],
                 ['is not working', 'is very slow', 'keeps disconnecting', 'is down', 'is unavailable', 'has no signal']),
    'Food': (['mess food', 'breakfast', 'lunch', 'dinner', 'rice', 'curry', 'chapati'],
             ['is stale', 'is undercooked', 'is tasteless', 'was cold', 'had an insect', 'smells bad']),
    'Cleaning': (['washroom', 'corridor', 'room floor', 'staircase', 'dustbin', 'common area'],
                 ['is dirty', 'is not cleaned', 'has garbage', 'is full of dust', 'has cockroaches', 'needs mopping']),
    'Furniture': (['chair', 'study table', 'bed', 'cupboard', 'mattress', 'desk', 'window'],
                  ['is broken', 'is damaged', 'is loose', 'has fallen apart', 'is cracked', 'needs replacement']),
    'Security': (['main gate', 'CCTV camera', 'door lock', 'security guard', 'visitor entry', 'cycle shed'],
                 ['is not working', 'is unsafe', 'is unattended at night', 'is broken', 'was tampered with', 'has no guard']),
}
_LOCATIONS = ['in my room', 'on the second floor', 'in block A', 'near the stairs', 'since yesterday', 'in the corridor', 'in room 3{}'.format(7), 'on the ground floor', '']


def build_category_dataset(seed=7, per_template=6):
    rng = random.Random(seed)
    texts, labels = [], []
    for label, items in CATEGORY_EXAMPLES.items():
        for t in items:
            texts.append(t)
            labels.append(label)
    for label, (subjects, problems) in _TEMPLATES.items():
        for _ in range(per_template * len(subjects)):
            s, p, l = rng.choice(subjects), rng.choice(problems), rng.choice(_LOCATIONS)
            texts.append(f'The {s} {p} {l}'.strip())
            labels.append(label)
    return texts, labels


def build_priority_dataset():
    texts, labels = [], []
    for label, items in PRIORITY_EXAMPLES.items():
        for t in items:
            texts.append(t)
            labels.append(label)
    return texts, labels


# Held-out hand-written test set: NEVER used for training.
TEST_SET = [
    ('Light in my bathroom keeps tripping the switch', 'Electricity'),
    ('Table fan stopped, motor smells burnt', 'Electricity'),
    ('Room has no current since evening', 'Electricity'),
    ('Tap in 2nd floor washroom dripping all day', 'Plumbing'),
    ('Toilet pipe is blocked and overflowing', 'Plumbing'),
    ('Bathroom basin leaking water on the floor', 'Plumbing'),
    ('We are not getting any drinking water on third floor', 'Water'),
    ('Water from tap is brown and has a smell', 'Water'),
    ('Hot water geyser supply not there in the morning', 'Water'),
    ('Wifi is extremely slow during online exam', 'Internet'),
    ('Router in our corridor is not working', 'Internet'),
    ('Cannot connect to the hostel network at all', 'Internet'),
    ('Dinner rice was raw and the curry was cold', 'Food'),
    ('Found a cockroach in the mess sambar', 'Food'),
    ('Breakfast idli was hard and stale', 'Food'),
    ('Room has not been swept and the dustbin is overflowing', 'Cleaning'),
    ('Ants and cockroaches all over the bathroom, needs cleaning', 'Cleaning'),
    ('Garbage thrown behind the hostel has started to smell', 'Cleaning'),
    ('My study chair leg has broken', 'Furniture'),
    ('Cot is very old and the frame is cracked', 'Furniture'),
    ('Cupboard shelf fell down', 'Furniture'),
    ('Guard was not at the gate last night and someone walked in', 'Security'),
    ('Somebody stole my charger and earphones from the room', 'Security'),
    ('Camera near main entrance is not recording', 'Security'),
    ('I want to shift to another room with my friend', 'Others'),
    ('Mess bill amount seems wrong this month', 'Others'),
    ('Please arrange a TV for the common room', 'Others'),
]
