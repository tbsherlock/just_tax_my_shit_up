import csv
import sys
import os
import logging
import datetime
import price_tools
from decimal import Decimal

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
FILENAME = "sample_trade.csv"
INPUT_COUNTER = 0
SELL_EVENT_COUNTER = 0
BUY_EVENT_COUNTER = 0
ALL_INPUT_RECORDS = list()  # A list of all transaction records
ALL_BUY_EVENTS = list()  # A list of all buy events
ALL_SELL_EVENTS = list()  # A list of all sell events


class InputRecord:
    def __init__(self, date, buy_asset, buy_volume, sell_asset, sell_volume, fee_asset, fee_volume, sell_events=None, buy_events=None, comment=""):
        global INPUT_COUNTER
        self.id = INPUT_COUNTER
        INPUT_COUNTER += 1
        if sell_events is None:
            sell_events = list()

        if buy_events is None:
            buy_events = list()

        self.date = datetime.datetime.strptime(date, "%d/%m/%Y")  # When the event occurred
        self.buy_events = buy_events
        self.buy_asset = buy_asset.upper()  # The asset which we bought
        self.buy_volume = Decimal(buy_volume)  # The volume of bought asset
        self.sell_events = sell_events
        self.sell_asset = sell_asset.upper()  # The asset which we sold
        self.sell_volume = Decimal(sell_volume)  # The volume of sold asset
        self.fee_asset = fee_asset.upper()  # The asset which fee was charged
        self.fee_volume = Decimal(fee_volume)  # The volume of fee charged
        self.comment = comment  # A comment...
        self.unclaimed_buy_volume = Decimal(buy_volume)  # The volume of 'buy_asset' which has not been claimed
        self.unclaimed_sell_volume = Decimal(sell_volume)  # The volume of 'sell_asset' which has not been claimed
        self.unclaimed_fee_volume = Decimal(fee_volume)  # The volume of 'fees' which has not been claimed
        self.tax_events = []  # A list of TaxEvent objects


class SellEvent:
    def __init__(self, date, input_record, buy_events, cost_base_aud, sell_asset, sell_volume, sell_price_aud, sell_volume_aud, gross_profit, net_profit, fee_aud, sell_unclaimed_volume=0.0, days_held=0, comment=""):
        global SELL_EVENT_COUNTER
        self.id = SELL_EVENT_COUNTER  # Unique ID for this entry
        SELL_EVENT_COUNTER += 1
        self.date = date  # Date when this sell event occured
        self.input_record = input_record
        self.buy_events = buy_events  # link to a BuyEvent object where the asset was bought
        self.cost_base_aud = cost_base_aud  # The cost base for this event
        self.sell_unclaimed_volume = sell_unclaimed_volume  # Volume of asset which has not been linked to buy event
        self.sell_asset = sell_asset  # Asset which was sold
        self.sell_volume = sell_volume  # Volume of the asset which was sold
        self.sell_price_aud = sell_price_aud  # Price ($aud per unit) the asset was sold
        self.sell_volume_aud = sell_volume_aud  # The total $aud volume which was sold
        self.gross_profit = gross_profit  # Sale of asset minus Cost of asset
        self.net_profit = net_profit  # gross profit minus fees
        self.fee_aud = fee_aud  # The $aud paid in fees
        self.days_held = days_held
        self.comment = comment

    def calculate_profit(self):
        self.gross_profit = self.sell_volume_aud - self.cost_base_aud
        self.net_profit = self.gross_profit - self.fee_aud


class BuyEvent:
    def __init__(self, date, input_record, sell_events, buy_asset, buy_volume, buy_price_aud, buy_volume_aud, buy_unclaimed_volume, comment=""):
        global BUY_EVENT_COUNTER
        self.id = BUY_EVENT_COUNTER  # Unique ID for this entry
        BUY_EVENT_COUNTER += 1
        self.input_record = input_record
        self.sell_events = sell_events  # A list of SellEvent which correspond to this buy event
        self.date = date  # The date this event occured
        self.buy_unclaimed_volume = buy_unclaimed_volume  # The volume of asset which has not been linked to a sell event
        self.buy_asset = buy_asset  # Asset which was sold
        self.buy_volume = buy_volume  # Volume of the asset which was sold
        self.buy_price_aud = buy_price_aud  # Price ($aud per unit) the asset was sold
        self.buy_volume_aud = buy_volume_aud  # The total $aud volume which was sold
        self.comment = comment


def read_input_file(file_name):
    with open(file_name, newline='') as csvfile:
        file_reader = csv.DictReader(csvfile, delimiter=',')
        for row in file_reader:
            try:
                new_record = InputRecord(**row)
                ALL_INPUT_RECORDS.append(new_record)
            except Exception as e:
                print("Failed to interpret line: %s" % e)
                print("--", row)
                raise
        logging.debug("loaded %s records from %s" % (len(ALL_INPUT_RECORDS), file_name))


def read_input_directory(input_folder_path):
    file_read_counter = 0
    for file in os.listdir(input_folder_path):
        if file.endswith(".csv"):
            file_read_counter += 1
            read_input_file(os.path.join(input_folder_path, file))


def input_record_to_buy_event(input_record):
    # Create a buy_event for each input record
    buy_price_aud = price_tools.get_price_at_datetime(input_record.buy_asset, input_record.date)
    buy_event_dict = dict()
    buy_event_dict['date'] = input_record.date
    buy_event_dict['input_record'] = input_record
    buy_event_dict['sell_events'] = []
    buy_event_dict['buy_asset'] = input_record.buy_asset
    buy_event_dict['buy_volume'] = input_record.buy_volume
    buy_event_dict['buy_price_aud'] = buy_price_aud
    buy_event_dict['buy_volume_aud'] = buy_price_aud * input_record.buy_volume
    buy_event_dict['buy_unclaimed_volume'] = input_record.buy_volume
    buy_event_dict['comment'] = ""
    return BuyEvent(**buy_event_dict)


def input_record_to_sell_event(input_record):
    # Create a SellEvent for a input record
    sell_price_aud = price_tools.get_price_at_datetime(input_record.sell_asset, input_record.date)
    fee_price = price_tools.get_price_at_datetime(input_record.fee_asset, input_record.date)
    fee_aud = fee_price * input_record.unclaimed_fee_volume
    sell_event_dict = dict()
    sell_event_dict['date'] = input_record.date
    sell_event_dict['input_record'] = input_record
    sell_event_dict['buy_events'] = []
    sell_event_dict['cost_base_aud'] = 0
    sell_event_dict['sell_asset'] = input_record.sell_asset
    sell_event_dict['sell_volume'] = input_record.sell_volume
    sell_event_dict['sell_price_aud'] = sell_price_aud
    sell_event_dict['sell_volume_aud'] = sell_price_aud * input_record.sell_volume
    sell_event_dict['sell_unclaimed_volume'] = input_record.sell_volume
    sell_event_dict['gross_profit'] = 0
    sell_event_dict['net_profit'] = 0
    sell_event_dict['fee_aud'] = fee_aud
    sell_event_dict['comment'] = ""
    return SellEvent(**sell_event_dict)


def do_calc_gains():
    """ The method used to calculate profit is to iterate over all sell events. Each sold asset should be matched
    to a corresponding buy of an asset. However, we want to minimise profit events when the assets were held for
    less than 365 days """
    # Sort by date, recent records first
    global ALL_BUY_EVENTS
    global ALL_SELL_EVENTS
    sorted_buy_records = sorted(ALL_BUY_EVENTS, key=lambda record: record.date)
    sorted_sell_records = sorted(ALL_SELL_EVENTS, key=lambda record: record.date)

    # Starting at the earliest record
    for sell_event in sorted_sell_records[::-1]:
        # if the record sell_asset is AUD, then we ignore the entry (no gains capital gains when we buy with AUD)
        if sell_event.sell_asset in ['AUD']:
            continue

        # Start searching for buy records to match this sell record
        # Start with buy records that are more than 365 days old, these are cgt deduction candidates
        cgt_candidate_list = list(filter(lambda record: (sell_event.date - record.date).days > 365, sorted_buy_records))[::-1]

        # Iterate over all CGT candidates, and compose taxable events
        for buy_event in cgt_candidate_list:
            # Ignore the dust
            if sell_event.sell_unclaimed_volume == 0.0:
                break
            calculate_taxable_event(sell_event, buy_event)

        # Now iterate over all records, starting with the latest. If we cant have a cgt we want a short hold time
        for buy_event in sorted_buy_records:
            # Ignore the dust
            if sell_event.sell_unclaimed_volume == 0.0:
                break
            calculate_taxable_event(sell_event, buy_event)

        if sell_event.sell_unclaimed_volume != 0:
            logging.error("sell record still has unclaimed sell volume! %s" % sell_event.id)
            logging.error("when did I buy that %.2f %s?" % (sell_event.sell_unclaimed_volume, sell_event.sell_asset))


def calculate_taxable_event(sell_event, buy_event):
    # Does the record 'buy' asset match this 'sell' asset?
    if sell_event.sell_asset not in buy_event.buy_asset:
        #logging.error("sell_asset does not match buy_asset? This should not occur")
        return

    # sell has to occur after the buy
    if sell_event.date <= buy_event.date:
        #logging.error("sell_record occured before buy event?")
        return

    # If the records buys have been claimed for
    if buy_event.buy_unclaimed_volume == 0:
        #logging.error("already_claimed")
        return

    # The volume to link
    event_vol = min(sell_event.sell_unclaimed_volume, buy_event.buy_unclaimed_volume)

    # Calculate taxable event parameters
    try:
        sell_event.buy_events.append(buy_event)
        sell_event.cost_base_aud += (event_vol / sell_event.sell_volume) * buy_event.buy_price_aud * event_vol
        sell_event.sell_unclaimed_volume = round(sell_event.sell_unclaimed_volume - event_vol, 4)
        sell_event.days_held = (sell_event.date - buy_event.date).days
        sell_event.calculate_profit()

        buy_event.sell_events.append(sell_event)
        buy_event.buy_unclaimed_volume = round(buy_event.buy_unclaimed_volume - event_vol, 4)

        sell_event.input_record.sell_events.append(sell_event.id)
        sell_event.input_record.unclaimed_sell_volume -= event_vol
        buy_event.input_record.buy_events.append(buy_event.id)
        buy_event.input_record.unclaimed_buy_volume -= event_vol

    except Exception as e:
        logging.error("Unable to calculate taxable event: %s" % e)
        raise


def write_all_output_files():
    total_profit = 0
    for input_record in ALL_INPUT_RECORDS:
        pass
        #print("%s - sold %.4f %s, $%.2f AUD profit; %s days held (bought on %s)" % (input_record.date.strftime("%Y-%m-%d"),
        #                                                        input_record.event_volume,
        #                                                        input_record.sell_record.sell_asset,
        #                                                        input_record.aud_profit,
        #                                                        input_record.held_days.days,
        #                                                        input_record.buy_record.date.strftime("%Y-%m-%d")  ) )
        #print("bought for %s, sold for %s" % (event['buy_aud_vol'], event['sell_aud_vol']))

    with open('output_input_events.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'date', 'buy_asset', 'buy_volume', 'sell_asset', 'sell_volume', 'fee_asset', 'fee_volume', 'unclaimed_buy_volume', 'unclaimed_sell_volume', 'sell_events', 'buy_events', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for input_record in ALL_INPUT_RECORDS:
            #cgt_discount = False
            #if input_record.held_days.days > 365:
            #    cgt_discount = True

            write_data = dict()
            write_data['id'] = input_record.id
            write_data['date'] = input_record.date.strftime("%Y/%m/%d")
            write_data['buy_asset'] = input_record.buy_asset
            write_data['buy_volume'] = input_record.buy_volume
            write_data['sell_asset'] = input_record.sell_asset
            write_data['sell_volume'] = "%.4f" % input_record.sell_volume
            write_data['fee_asset'] = input_record.fee_asset
            write_data['fee_volume'] = "%.4f" % input_record.fee_volume
            write_data['unclaimed_buy_volume'] = "%.4f" % input_record.unclaimed_buy_volume
            write_data['unclaimed_sell_volume'] = "%.4f" % input_record.unclaimed_sell_volume
            write_data['sell_events'] = list(set(input_record.sell_events))
            write_data['buy_events'] = list(set(input_record.buy_events))
            write_data['comment'] = input_record.comment
            writer.writerow(write_data)

            #total_profit += input_record.aud_profit

    #print("total_profit", total_profit)

    with open('output_sell_events.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'date', 'input_record', 'buy_events', 'cost_base_aud', 'sell_unclaimed_volume', 'sell_asset', 'sell_volume', 'sell_price_aud', 'sell_volume_aud', 'gross_profit', 'net_profit', 'fee_aud', 'days_held', 'cgt_discount', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for sell_record in ALL_SELL_EVENTS:
            buy_events = []
            for evt in sell_record.buy_events:
                buy_events.append(evt.id)

            cgt_discount = False
            if sell_record.days_held > 365:
                cgt_discount = True

            write_data = dict()
            write_data['id'] = sell_record.id
            write_data['date'] = sell_record.date.strftime("%Y/%m/%d")
            write_data['input_record'] = sell_record.input_record.id
            write_data['buy_events'] = buy_events
            write_data['cost_base_aud'] = "%.4f" % sell_record.cost_base_aud
            write_data['sell_unclaimed_volume'] = "%.4f" % sell_record.sell_unclaimed_volume
            write_data['sell_asset'] = sell_record.sell_asset
            write_data['sell_volume'] = "%.4f" % sell_record.sell_volume
            write_data['sell_price_aud'] = "%.4f" % sell_record.sell_price_aud
            write_data['sell_volume_aud'] = "%.4f" % sell_record.sell_volume_aud
            write_data['gross_profit'] = "%.4f" % sell_record.gross_profit
            write_data['net_profit'] = "%.4f" % sell_record.net_profit
            write_data['fee_aud'] = "%.4f" % sell_record.fee_aud
            write_data['days_held'] = sell_record.days_held
            write_data['cgt_discount'] = cgt_discount
            write_data['comment'] = sell_record.comment
            writer.writerow(write_data)

    with open('output_buy_events.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'date', 'input_record', 'sell_events', 'buy_unclaimed_volume', 'buy_asset', 'buy_volume', 'buy_price_aud', 'buy_volume_aud', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for buy_record in ALL_BUY_EVENTS:
            sell_events = []
            for evt in buy_record.sell_events:
                sell_events.append(evt.id)

            write_data = dict()
            write_data['id'] = buy_record.id
            write_data['date'] = buy_record.date.strftime("%Y/%m/%d")
            write_data['input_record'] = buy_record.input_record.id
            write_data['sell_events'] = sell_events
            write_data['buy_unclaimed_volume'] = "%.4f" % buy_record.buy_unclaimed_volume
            write_data['buy_asset'] = buy_record.buy_asset
            write_data['buy_volume'] = "%.4f" % buy_record.buy_volume
            write_data['buy_price_aud'] = "%.4f" % buy_record.buy_price_aud
            write_data['buy_volume_aud'] = "%.4f" % buy_record.buy_volume_aud
            write_data['comment'] = buy_record.comment
            writer.writerow(write_data)


if __name__ == '__main__':
    read_input_directory("input/")
    # interpret all input records
    for record in ALL_INPUT_RECORDS:
        ALL_BUY_EVENTS.append(input_record_to_buy_event(record))
        ALL_SELL_EVENTS.append(input_record_to_sell_event(record))

    do_calc_gains()
    write_all_output_files()


