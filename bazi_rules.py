FAVORABLE_MAP = {
    "Wood":["Wood","Water"], "Fire":["Fire","Wood"],
    "Earth":["Earth","Fire"], "Metal":["Metal","Earth"], "Water":["Water","Metal"]
}

UNFAVORABLE_MAP = {
    "Wood":["Fire","Metal"], "Fire":["Water","Metal"],
    "Earth":["Wood","Water"], "Metal":["Fire","Wood"], "Water":["Earth","Fire"]
}

COLOR_MAP = {
    "Wood":["Green","Brown"], "Fire":["Red","Orange"],
    "Earth":["Yellow","Beige"], "Metal":["White","Gray"], "Water":["Blue","Black"]
}

NUMBER_MAP = {
    "Wood":[3,8], "Fire":[2,7], "Earth":[5,0], "Metal":[4,9], "Water":[1,6]
}

def get_favorable_elements(day_master):
    return FAVORABLE_MAP.get(day_master, [])

def get_unfavorable_elements(day_master):
    return UNFAVORABLE_MAP.get(day_master, [])

def get_lucky_colors(day_master):
    return COLOR_MAP.get(day_master, [])

def get_lucky_numbers(day_master):
    return NUMBER_MAP.get(day_master, [])
