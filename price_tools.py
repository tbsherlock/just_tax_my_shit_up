import os
import csv
import datetime
from decimal import Decimal



PRICE_DATA_DIR = "bars/"
PRICE_DATA = dict()  # keys are asset pair strings base_quote


def read_folder(folder_path):
    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            pair_string = os.path.splitext(file)[0]
            index_price_data(os.path.join(PRICE_DATA_DIR, file), pair_string)


def index_price_data(filename, asset_pair):
    """ Read price data into memory """
    global PRICE_DATA
    with open(filename, newline='') as csvfile:
        fieldnames = ['date', 'open', 'high', 'low', 'close', 'volume']
        file_reader = csv.DictReader(csvfile, delimiter=',', fieldnames=fieldnames)
        price_data = dict()
        for row in file_reader:
            try:
                date_string = row['date']
                price_data[date_string] = row
            except Exception as e:
                print("Failed to interpret line: %s" % e)
                print("--", row)
                raise
        PRICE_DATA[asset_pair] = price_data
        print("loaded %s bars for %s" % (len(price_data), asset_pair))


def get_price_at_datetime(asset_name, date_time):
    """ Return the value of asset_name at date_time in AUD. convert from asset_name to BTC, and then from BTC to AUD """
    global PRICE_DATA

    """ None is zero..? """
    if asset_name in ['None', 'NONE']:
        return Decimal(0.0)

    """ If asset_name is AUD, we know it is 1.0 """
    if asset_name in ['AUD']:
        return Decimal(1.0)

    if asset_name in ['BTC']:
        """ look up btc_usdt at this date """
        rate = PRICE_DATA['BTC_USDT'][date_time.strftime("%Y-%m-%d")]
        #print("VALS:", float(rate['high']), float(rate['low']), (float(rate['high']) + float(rate['low'])) / 2)
        return Decimal((float(rate['high']) + float(rate['low'])) / 2)

    if asset_name in ['USDT']:
        """ look up usdt_aud at this date """
        if date_time.strftime("%Y-%m-%d") in PRICE_DATA['USDT_AUD']:
            rate = PRICE_DATA['USDT_AUD'][date_time.strftime("%Y-%m-%d")]
        elif (date_time - datetime.timedelta(days=1)).strftime("%Y-%m-%d") in PRICE_DATA['USDT_AUD']:
            rate = PRICE_DATA['USDT_AUD'][(date_time - datetime.timedelta(days=1)).strftime("%Y-%m-%d")]
        elif (date_time - datetime.timedelta(days=2)).strftime("%Y-%m-%d") in PRICE_DATA['USDT_AUD']:
            rate = PRICE_DATA['USDT_AUD'][(date_time - datetime.timedelta(days=2)).strftime("%Y-%m-%d")]
        else:
            print("something fucked up?", date_time.strftime("%Y-%m-%d"))

        #print("VALS:", float(rate['high']), float(rate['low']), (float(rate['high']) + float(rate['low'])) / 2)
        return Decimal((float(rate['high']) + float(rate['low'])) / 2)

    """ Get this pair with BTC ratio """
    pair_step = asset_name + "_BTC"
    rate = PRICE_DATA[pair_step][date_time.strftime("%Y-%m-%d")]
    other_rate = get_price_at_datetime('BTC', date_time)
    #print("VALS2:", float(rate['high']), float(rate['low']), (float(rate['high']) + float(rate['low'])) / 2)
    return other_rate * Decimal((float(rate['high']) + float(rate['low'])) / 2)


read_folder(PRICE_DATA_DIR)
