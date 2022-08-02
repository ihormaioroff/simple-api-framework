import datetime
import decimal
import json
from itertools import islice

import aioredis


class Redis:
    def __init__(self, **kwargs):
        self.prefix = kwargs.get('prefix')
        self.url = kwargs.get('url')
        self.max_insert_size = kwargs.get('max_insert_size', 50000)
        self.connect_timeout = kwargs.get('connect_timeout', 60)
        self.timeout = kwargs.get('timeout', 60)
        self.retries = kwargs.get('retries', 3)

    def __pre_process_new_data(self, data):
        if isinstance(data, dict):
            result_dict = {}
            for key, value in data.items():
                if isinstance(key, datetime.date):
                    key = key.strftime("%Y-%m-%d")
                result_dict[key] = self.__pre_process_new_data(value)
            data = result_dict.copy()
        elif isinstance(data, list):
            for index in range(len(data)):
                data[index] = self.__pre_process_new_data(data[index])
        elif isinstance(data, datetime.date):
            data = data.strftime("%Y-%m-%d")
        elif isinstance(data, decimal.Decimal):
            data = float(data)
        return data

    def __chunks(self, data):
        it = iter(data)
        for i in range(0, len(data), self.max_insert_size):
            yield {k: data[k] for k in islice(it, self.max_insert_size)}

    async def __connection(self):
        if not self.url:
            raise Exception("You need to set Redis URL")

        redis = await aioredis.from_url(
            self.url, encoding="utf-8", socket_connect_timeout=self.connect_timeout, socket_timeout=self.timeout
        )
        return redis

    async def __put(self, key, data, tries=0):
        redis = await self.__connection()

        for item in self.__chunks(data):
            try:
                await redis.hset(f"{self.prefix}:{key}", mapping=item)
            except:
                tries += 1
                if tries > self.retries:
                    return
                return await self.__put(key, data, tries)

    async def set(self, key: str, dictionary: dict | list):
        try:
            data = self.__pre_process_new_data(dictionary)
            for data_key, value in data.items():
                data[data_key] = json.dumps(value)
            await self.__put(key, data)
        except Exception as e:
            raise e

    async def get(self, key: str, elements: str | list | None = None):
        try:
            redis = await self.__connection()
            if not elements:
                results = {}
                result = await redis.hgetall(f"{self.prefix}:{key}")
                if result:
                    for k, v in result.items():
                        results[k] = json.loads(v)
                return results
            elif isinstance(elements, str):
                result = await redis.hget(f"{self.prefix}:{key}", elements)
                if result:
                    result = json.loads(result)
                return result
            else:
                results = {}
                pipeline = redis.pipeline()
                for e in elements:
                    pipeline.hget(f"{self.prefix}:{key}", e)
                result = pipeline.execute()
                if result:
                    for i, k in enumerate(elements):
                        results[k] = json.loads(result[i])
                return results
        except Exception as e:
            raise e
