import pymongo


class MongoDB:
    def __init__(self, **kwargs):
        self.url = kwargs.get('url')

    def __connect(self):
        if not self.url:
            raise Exception("MongoDB: no connection url specified")
        mongo = pymongo.MongoClient(self.url)
        return mongo.get_default_database()

    def insert(self, collection, data, remove=False):
        db = self.__connect()
        db_collection = db[collection]
        db_collection.create_index(keys='_id', name=f'{collection}Index')
        if remove:
            db_collection.delete_many({})
        if isinstance(data, list):
            db_collection.insert_many(data)
        else:
            db_collection.insert_one(data)

    def get(self, collection, many=True, parameters=None):
        db = self.__connect()
        db_collection = db[collection]
        if not parameters:
            parameters = {}
        if many:
            result = db_collection.find(parameters)
        else:
            result = db_collection.find_one(filter=parameters)
        return result
