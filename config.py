from environs import Env

from environs import Env

env = Env()
env.read_env()

token = env.str("TOKEN")
CALENDAR_A = env.str("CALENDAR_A")
CALENDAR_B = env.str("CALENDAR_B")
admin_id = env.str("ADMIN_ID")
