from config import DATABASE_CONFIG, hasher
from database.methods_schedule import MethodsSchedule
from database.methods_services import MethodsServices
from database.methods_users import MethodsUsers
from database.methods_workers import MethodsWorkers


class Database(MethodsUsers, MethodsSchedule, MethodsServices, MethodsWorkers):
    def __init__(self, conf):
        super().__init__(conf)


db = Database(DATABASE_CONFIG)
