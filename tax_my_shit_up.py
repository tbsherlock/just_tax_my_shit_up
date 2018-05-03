import csv
import sys
import os
import logging
import datetime
import price_tools
from decimal import Decimal

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
FILENAME = "sample_trade.csv"
RECORD_COUNTER = 0
EVENT_COUNTER = 0


class Record:
    def __init__(self, date, buy_asset, buy_volume, sell_asset, sell_volume, fee_asset, fee_volume, comment):
        global RECORD_COUNTER
        self.id = RECORD_COUNTER
        RECORD_COUNTER += 1
        self.date = datetime.datetime.strptime(date, "%d/%m/%Y")  # When the event occurred
        self.buy_asset = buy_asset.upper()  # The asset which we bought
        self.buy_volume = Decimal(buy_volume)  # The volume of bought asset
        self.sell_asset = sell_asset.upper()  # The asset which we sold
        self.sell_volume = Decimal(sell_volume)  # The volume of sold asset
        self.fee_asset = fee_asset.upper()  # The asset which fee was charged
        self.fee_volume = Decimal(fee_volume)  # The volume of fee charged
        self.fee_aud = price_tools.get_price_at_datetime(self.fee_asset, self.date) * self.fee_volume  # The total fees in AUD
        self.comment = comment  # A comment...
        self.unclaimed_buy_volume = Decimal(buy_volume)  # The volume of 'buy_asset' which has not been claimed
        self.unclaimed_sell_volume = Decimal(sell_volume)  # The volume of 'sell_asset' which has not been claimed
        self.unclaimed_fee_volume = Decimal(fee_volume)  # The volume of 'fees' which has not been claimed
        self.tax_events = []  # A list of TaxEvent objects


class TaxEvent:
    def __init__(self, buy_record, buy_price_aud, sell_price_aud, sell_record, date, fee_volume, fee_asset, fee_aud, aud_profit, event_volume, event_asset, held_days, buy_aud_vol, sell_aud_vol):
        global EVENT_COUNTER
        self.id = EVENT_COUNTER
        EVENT_COUNTER += 1
        self.buy_record = buy_record  # The id of the buy event
        self.buy_price_aud = buy_price_aud
        self.sell_price_aud = sell_price_aud
        self.sell_record = sell_record  # The id of the sell event
        self.date = date  # The date time of the event, should be that of the sell event
        self.fee_volume = fee_volume
        self.fee_asset = fee_asset
        self.fee_aud = fee_aud  # The total fees (in aud)
        self.aud_profit = aud_profit  # The profit made on the trade
        self.event_volume = event_volume  # The volume traded
        self.event_asset = event_asset  # The asset sold.bought
        self.held_days = held_days  # number of days the asset was held
        self.buy_aud_vol = buy_aud_vol
        self.sell_aud_vol = sell_aud_vol


ALL_RECORDS = list()  # A list of all transaction records
ALL_TAX_EVENTS = list()  # A list of taxable events


def read_input_file(file_name):
    with open(file_name, newline='') as csvfile:
        file_reader = csv.DictReader(csvfile, delimiter=',')
        for row in file_reader:
            try:
                new_record = Record(**row)
                ALL_RECORDS.append(new_record)
            except Exception as e:
                print("Failed to interpret line: %s" % e)
                print("--", row)
                raise
        logging.debug("loaded %s records from %s" % (len(ALL_RECORDS), file_name))


def read_input_directory(input_folder_path):
    file_read_counter = 0
    for file in os.listdir(input_folder_path):
        if file.endswith(".csv"):
            file_read_counter += 1
            read_input_file(os.path.join(input_folder_path, file))


def do_calc_gains():
    # Sort by date, recent records first
    sorted_records = sorted(ALL_RECORDS, key=lambda record: record.date)

    # Starting at the earliest record
    for sell_record in sorted_records[::-1]:
        print("rec: %s" % sell_record.id)
        # if the record sell_asset is AUD, then we ignore the entry (no gains capital gains when we buy with AUD)
        if sell_record.sell_asset in ['AUD']:
            continue

        # Start searching for buy records to match this sell record
        # Start with buy records that are more than 365 days old, these are cgt deduction candidates
        cgt_candidate_list = list(filter(lambda record: (sell_record.date - record.date).days > 365, sorted_records))[::-1]

        # Iterate over all CGT candidates, and compose taxable events
        for buy_record in cgt_candidate_list:
            calculate_taxable_event(sell_record, buy_record)
            if sell_record.unclaimed_sell_volume < 0.0001:
                break

        # Now iterate over all records, starting with the latest. If we cant have a cgt we want a short hold time
        for buy_record in sorted_records:
            calculate_taxable_event(sell_record, buy_record)
            if sell_record.unclaimed_sell_volume < 0.0001:
                break

        if sell_record.unclaimed_sell_volume != 0:
            logging.error("sell record still has unclaimed sell volume! %s" % sell_record.id)
            logging.error("when did I buy that %.2f %s" % (sell_record.unclaimed_sell_volume, sell_record.sell_asset))

        # cant calculate when we bought it, so assume it was all profit?
        try:
            event_vol = sell_record.unclaimed_sell_volume
            buy_price = 0
            buy_aud_vol = event_vol * buy_price
            sell_price = price_tools.get_price_at_datetime(sell_record.sell_asset, sell_record.date)
            sell_aud_vol = event_vol * sell_price
            profit_aud_vol = sell_aud_vol - buy_aud_vol

            fee = 0.0
            if 'None' not in sell_record.fee_asset:
                if sell_record.unclaimed_fee_volume != 0.0:
                    fee_price = price_tools.get_price_at_datetime(sell_record.fee_asset, sell_record.date)
                    fee = fee_price * sell_record.unclaimed_fee_volume
                    sell_record.unclaimed_fee_volume = 0.0

            tax_event_dict = dict()
            tax_event_dict['buy_record'] = sell_record  # The id of the buy event
            tax_event_dict['buy_price_aud'] = buy_price
            tax_event_dict['sell_price_aud'] = sell_price
            tax_event_dict['sell_record'] = sell_record  # The id of the sell event
            tax_event_dict['date'] = sell_record.date  # The date time of the event, should be that of the sell event
            tax_event_dict['fee_volume'] = sell_record.fee_volume
            tax_event_dict['fee_asset'] = sell_record.fee_asset
            tax_event_dict['fee_aud'] = fee  # The total fees (in aud)
            tax_event_dict['aud_profit'] = profit_aud_vol  # The profit made on the trade
            tax_event_dict['event_volume'] = event_vol  # The volume traded
            tax_event_dict['event_asset'] = sell_record.sell_asset  # The asset sold.bought
            tax_event_dict['held_days'] = sell_record.date - sell_record.date  # number of days the asset was held
            tax_event_dict['buy_aud_vol'] = buy_aud_vol  # the volume bought in aud
            tax_event_dict['sell_aud_vol'] = sell_aud_vol  # the volume sold in aud

            new_tax_event = TaxEvent(**tax_event_dict)
            ALL_TAX_EVENTS.append(new_tax_event)

            # Update the buy events
            sell_record.unclaimed_sell_volume -= event_vol
            sell_record.tax_events.append(new_tax_event.id)
        except Exception as e:
            logging.error("Unable to calculate taxable event: %s" % e)
            raise


def calculate_taxable_event(sell_record, buy_record):
    global ALL_RECORDS
    global ALL_TAX_EVENTS

    # Does the record 'buy' asset match this 'sell' asset?
    if sell_record.sell_asset not in buy_record.buy_asset:
        return

    # sell has to occur after the buy
    if sell_record.date <= buy_record.date:
        return

    # If the records buys have been claimed for
    if buy_record.unclaimed_buy_volume == 0:
        return

    # The size of this event
    event_vol = min(sell_record.unclaimed_sell_volume, buy_record.unclaimed_buy_volume)

    # Calculate taxable event parameters
    try:
        buy_price = price_tools.get_price_at_datetime(buy_record.buy_asset, buy_record.date)
        buy_aud_vol = event_vol * buy_price
        sell_price = price_tools.get_price_at_datetime(sell_record.sell_asset, sell_record.date)
        sell_aud_vol = event_vol * sell_price
        profit_aud_vol = sell_aud_vol - buy_aud_vol

        fee = 0.0
        if 'None' not in sell_record.fee_asset:
            if sell_record.unclaimed_fee_volume != 0.0:
                fee_price = price_tools.get_price_at_datetime(sell_record.fee_asset, sell_record.date)
                fee = fee_price * sell_record.unclaimed_fee_volume
                sell_record.unclaimed_fee_volume = 0.0

        print("~~~~~~~~~~~ %s %s" % (event_vol, sell_record.sell_asset))
        print("bought for rate %.4f ($%.4f total) on %s" % (buy_price, buy_aud_vol, buy_record.date.strftime("%d/%m/%Y")))
        print("  sold for rate %.4f ($%.4f total) on %s" % (sell_price, sell_aud_vol, sell_record.date.strftime("%d/%m/%Y")))
        #print("ASSETS", buy_record.buy_asset, sell_record.sell_asset)

        tax_event_dict = dict()
        tax_event_dict['buy_record'] = buy_record  # The id of the buy event
        tax_event_dict['buy_price_aud'] = buy_price
        tax_event_dict['sell_price_aud'] = sell_price
        tax_event_dict['sell_record'] = sell_record  # The id of the sell event
        tax_event_dict['date'] = sell_record.date  # The date time of the event, should be that of the sell event
        tax_event_dict['fee_volume'] = sell_record.fee_volume
        tax_event_dict['fee_asset'] = sell_record.fee_asset
        tax_event_dict['fee_aud'] = fee  # The total fees (in aud)
        tax_event_dict['aud_profit'] = profit_aud_vol  # The profit made on the trade
        tax_event_dict['event_volume'] = event_vol  # The volume traded
        tax_event_dict['event_asset'] = sell_record.sell_asset  # The asset sold.bought
        tax_event_dict['held_days'] = sell_record.date - buy_record.date  # number of days the asset was held
        tax_event_dict['buy_aud_vol'] = buy_aud_vol
        tax_event_dict['sell_aud_vol'] = sell_aud_vol

        new_tax_event = TaxEvent(**tax_event_dict)
        ALL_TAX_EVENTS.append(new_tax_event)

        # Update the buy events
        sell_record.unclaimed_sell_volume -= event_vol
        sell_record.tax_events.append(new_tax_event.id)
        buy_record.unclaimed_buy_volume -= event_vol
    except Exception as e:
        logging.error("Unable to calculate taxable event: %s" % e)
        raise


def write_output_files():
    total_profit = 0
    for event in ALL_TAX_EVENTS:
        print("%s - sold %.4f %s, $%.2f AUD profit; %s days held (bought on %s)" % (event.date.strftime("%Y-%m-%d"),
                                                                event.event_volume,
                                                                event.sell_record.sell_asset,
                                                                event.aud_profit,
                                                                event.held_days.days,
                                                                event.buy_record.date.strftime("%Y-%m-%d")  ) )
        #print("bought for %s, sold for %s" % (event['buy_aud_vol'], event['sell_aud_vol']))

    with open('output_tax_events.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'buy_ref', 'sell_ref', 'date_purchased', 'date_sold', 'days_held', 'asset_sold', 'units_sold', 'buy_volume(AUD)', 'buy_price(AUD)', 'sell_volume(AUD)', 'sell_price(AUD)',
                      'profit(AUD)', 'fees(AUD)', 'CGT_Discount']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for event in ALL_TAX_EVENTS:
            cgt_discount = False
            if event.held_days.days > 365:
                cgt_discount = True

            write_data = dict()
            write_data['id'] = event.id
            write_data['buy_ref'] = event.buy_record.id
            write_data['sell_ref'] = event.sell_record.id
            write_data['date_sold'] = event.sell_record.date.strftime("%Y/%m/%d")
            write_data['date_purchased'] = event.buy_record.date.strftime("%Y/%m/%d")
            write_data['days_held'] = event.held_days.days
            write_data['asset_sold'] = event.event_asset
            write_data['units_sold'] = "%.4f" % event.event_volume
            write_data['buy_volume(AUD)'] = "%.4f" % event.buy_aud_vol
            write_data['buy_price(AUD)'] = "%.4f" % event.buy_price_aud
            write_data['sell_volume(AUD)'] = "%.4f" % event.sell_aud_vol
            write_data['sell_price(AUD)'] = "%.4f" % event.sell_price_aud
            write_data['profit(AUD)'] = "%.4f" % event.aud_profit
            write_data['fees(AUD)'] = "%.4f" % event.fee_aud
            write_data['CGT_Discount'] = cgt_discount
            writer.writerow(write_data)

            total_profit += event.aud_profit

    print("total_profit", total_profit)

    with open('output_tax_trades.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'date', 'buy_asset', 'buy_volume', 'sell_asset', 'sell_volume', 'fee_asset', 'fee_volume', 'fee_aud', 'comment', 'unclaimed_buy_volume', 'unclaimed_sell_volume', 'tax_events']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for sell_record in ALL_RECORDS:
            write_data = dict()
            write_data['id'] = sell_record.id
            write_data['date'] = sell_record.date.strftime("%Y/%m/%d")
            write_data['buy_asset'] = sell_record.buy_asset
            write_data['buy_volume'] = "%.4f" % sell_record.buy_volume
            write_data['sell_asset'] = sell_record.sell_asset
            write_data['sell_volume'] = "%.4f" % sell_record.sell_volume
            write_data['fee_asset'] = sell_record.fee_asset
            write_data['fee_volume'] = "%.4f" % sell_record.fee_volume
            write_data['fee_aud'] = "%.4f" % sell_record.fee_aud
            write_data['comment'] = sell_record.comment
            write_data['unclaimed_buy_volume'] = "%.4f" % sell_record.unclaimed_buy_volume
            write_data['unclaimed_sell_volume'] = "%.4f" % sell_record.unclaimed_sell_volume
            write_data['tax_events'] = sell_record.tax_events
            writer.writerow(write_data)


if __name__ == '__main__':
    read_input_directory("input/")
    do_calc_gains()
    write_output_files()


