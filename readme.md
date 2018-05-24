This script for calculating tax owed for CGT purposes.

it will produce three output files;
output_input_events - An output file, to feed into future years?
output_sell_events - All events where assets were sold 
output_buy_events - All events where assets were purchased

The outputs are in csv format, columns described here:

**output_input_events**
+ id - This is a unique number to reference this trade
+ date - This is the date where the trade occured
+ buy_asset - This is the asset which was purchased
+ buy_volume - This is the volume of the asset which was purchased
+ sell_asset - This is the asset which was sold
+ sell_volume - This is the volume of the asset which was sold
+ fee_asset - This is the asset in which the fee was charged
+ fee_volume - This is the volume of fee_asset which was charged as fee
+ unclaimed_buy_volume - How much of the buy volume has not been matched with a sell event (should still be held)
+ unclaimed_sell_volume - How much of the sell volume has not been matched with a buy event (should be 0)
+ sell_events - A list if id's which point to sell events referenced in this trade
+ buy_events - A list if id's which point to buy events referenced in this trade
+ tax_events - A list of references to the id column of the output_tax_events.csv, events which involve this trade
+ comment - This value is carried through from input comment column


**output_sell_events**
+ id - This is a unique number to reference this tax event
+ date - This is the date where the sell occured
+ input_record - Reference id of the trade in output_input_events.csv
+ buy_events - List of reference id of the record where the asset was bought, see output_buy_events.csv
+ cost_base_aud - the cost of the assets when purchased in AUD
+ sell_unclaimed_volume - Any remaining units of asset which were not matched with buy events
+ sell_asset - The asset which was sold
+ sell_volume - The volume of the asset which was sold as claimed in this event
+ sell_price_aud - AUD price per asset unit
+ sell_volume_aud - AUD value of the asset sold at the time of sale
+ gross_profit - This is the total profit in AUD for this event, before fees
+ net_profit - This is the total profit in AUD for this event, after fees
+ fee_aud - This is the total fees for this sale, fees will be claimed for sell record
+ CGT_Discount - This is TRUE if this event is eligable for the CGT discount (more than 365 days held)

**output_buy_events**
+ id - This is a unique number to reference this tax event
+ date - This is the date where the sell occured
+ input_record - Reference id of the trade in output_input_events.csv
+ sell_events - List of reference id of the record where the asset was sold, see output_sell_events.csv
+ cost_base_aud - the cost of the assets when purchased in AUD
+ buy_unclaimed_volume - Any remaining units of asset which were not matched with sell events
+ buy_asset - The asset which was bought
+ buy_volume - The volume of the asset which was bought as claimed in this event
+ buy_price_aud - AUD price per asset unit
+ buy_volume_aud - AUD value of the asset bought at the time of sale


