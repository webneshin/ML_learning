import datetime
import logging
from datetime import *

import pymongo
import requests

import pandas as pd
from pandas import DataFrame
from binance import Client
from binance.enums import HistoricalKlinesType

def _generate_table_name(joft: str, interval: str, market_type: HistoricalKlinesType):
    return joft + '_' + interval + '_' + market_type.name + '_Binance'


def check_ip(country: str):
    re = requests.get('http://ip-api.com/json/').json()
    current_country = re['country']
    if current_country != country:
        raise ValueError("Ip bayad az '{}' bashad va dar hal hazer az '{}' ast.".format(country, current_country))
    print("IP from '{}' . its OK!".format(country))


def get_data_from_mongo(table_name: str) -> DataFrame:
    # Get Data From Mongo
    client_db = pymongo.MongoClient(port=27017)
    db = client_db.Trader8
    table_mongo = db[table_name]
    if table_mongo.estimated_document_count() > 0:
        df = pd.DataFrame(table_mongo.find({}, {
            '_id': 0
        }).sort([("open_time", pymongo.ASCENDING)]))
        df.set_index('open_time', inplace=True)
    else:
        df = pd.DataFrame()

    return df


def _get_start_time(df: DataFrame) -> datetime:
    # Get Start Time
    start_time = datetime(2001, 1, 1, 0, 0)
    if not df.empty:
        to_utc = (datetime.now() - datetime.utcnow()).seconds * 1000000000
        start_time = df.tail(1).index.values[0]
        start_time = start_time - to_utc + 100000000
    print('Start Time:', start_time)
    return start_time


def _get_data_from_binance(joft: str, interval: str, market_type: HistoricalKlinesType, start_time: datetime,
                           country: str):
    # Get Data From Binance
    check_ip(country)
    client = Client('lSJStmJ7lwD2QSkxDYJ0OdscqqDqVI1JJRIuG2XlHg2yBQGnY1u78J7k28CpsumG',
                    'LJTW6Bog4MDyRlrMfnFZ8bJQ0A6bHoKk5vGGvhQu5PLw1sfPnK4gNVIABwx62qx5')
    now = datetime.now()
    print('start get data from binance:', datetime.now())
    print('Getting Data ...')
    binance_data = client.get_historical_klines(joft, interval, str(start_time), None, klines_type=market_type)
    print('finish get data from binance:', datetime.now())
    binance_data = binance_data[0:-1]
    print('{} radif data gerefte shod az binance'.format(len(binance_data)))
    client.close_connection()
    return binance_data, now


def _update_data(table_name, binance_data, now):
    # Add data to Mongo
    client_db = pymongo.MongoClient(port=27017)
    db = client_db.Trader8
    table_mongo = db[table_name]
    if len(binance_data) > 0:
        for kline in binance_data:
            result = db[table_name].insert_one({
                'open_time': datetime.fromtimestamp(int(kline[0]) / 1000),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5]),
                'close_time': datetime.fromtimestamp(int(kline[6]) / 1000),
                'quote_asset_volume': float(kline[7]),
                'number_trades': int(kline[8]),
                'taker_buy_base_asset_volume': float(kline[9]),
                'taker_buy_quote_asset_volume': float(kline[10]),
                'ignore': float(kline[11]),
                'comment': '',
                'importTime': now
            })
        print('tamam radifha ezafe shod')

    else:
        print('etelaat jadidi mojod nist')


def get_and_update_data(joft: str, interval: str, market_type: HistoricalKlinesType, country: str | None) -> DataFrame:
    """
    :param joft: ETHUSDT
    :param interval: 1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h,1d,3d,1w,1M
    :param market_type: FUTURES or SPOT
    :param country: Netherlands
    :return: df
    """
    table_name = _generate_table_name(joft, interval, market_type)
    df = get_data_from_mongo(table_name=table_name)
    if not country:
        logging.warning('not updatetd! for update set "country"!')
        return df
    start_time = _get_start_time(df)
    binance_data, now = _get_data_from_binance(joft, interval, market_type, start_time, country)
    _update_data(table_name, binance_data, now)
    df = get_data_from_mongo(table_name=table_name)
    return df


def is_positive(number):
    if number < 0:
        return False
    return True