from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os

MONGO_USER = os.environ.get('MONGO_USER')
MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD')
MONGO_CLUSTER = os.environ.get('MONGO_CLUSTER')
MONGO_DB = os.environ.get('MONGO_DB')
MONGO_COLLECTION = os.environ.get('MONGO_COLLECTION')

uri = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}.qgtzkpa.mongodb.net/?retryWrites=true&w=majority&appName={MONGO_CLUSTER}"

class DBCONNECTION:
    def __init__(self):
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        self.db = self.client[MONGO_DB]
        self.collection = self.db[MONGO_COLLECTION]
        self.ping_db()

    def ping_db(self):
        try:
            self.client.admin.command('ping')
        except Exception as e:
            print(e)

    def insert_data(self, user_id, url, key):
        data = {
            "user_id": user_id,
            "endpoint": url,
            "api_key": key
        }
        insert_id = self.collection.insert_one(data)
        if insert_id:
            return True
        else:
            return False

    def get_data(self, user_id):
        data = self.collection.find_one({"user_id": user_id})
        return data