import unittest
import datetime
import price_tools


class TestTaxMethods(unittest.TestCase):
    def test_get_price_at_datetime_1(self):
        date = datetime.datetime.strptime("2015-09-18", "%Y-%m-%d")
        asset_string = "BTC"
        price = price_tools.get_price_at_datetime(asset_string, date)
        self.assertAlmostEqual(235.38200026, float(price))

    def test_get_price_at_datetime_2(self):
        date = datetime.datetime.strptime("2015-09-18", "%Y-%m-%d")
        asset_string = "USDT"
        price = price_tools.get_price_at_datetime(asset_string, date)
        self.assertAlmostEqual(1.0, float(price))

    def test_get_price_at_datetime_3(self):
        date = datetime.datetime.strptime("2015-09-18", "%Y-%m-%d")
        asset_string = "ETH"
        # 0.0037023150000000003 ETH_BTC
        # 235.38200025999998 BTC_USDT
        # infers
        # 1usd buys 0.87145831029260189656830007799999 eth
        price = price_tools.get_price_at_datetime(asset_string, date)
        self.assertAlmostEqual(0.87145831, float(price))

if __name__ == '__main__':
    unittest.main()