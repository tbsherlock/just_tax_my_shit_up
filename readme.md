This script for calculating tax owed for CGT purposes.

it will produce two output files;
output_tax_trades - This is a summary of all the CGT events
output_tax_events - This is a summary of all of the taxale events 

The outputs are in csv format, columns described here:

**output_tax_trades**
+ id - This is a unique number to reference this trade
+ date - This is the date where the trade occured
+ buy_asset - This is the asset which was purchased
+ buy_volume - This is the volume of the asset which was purchased
+ sell_asset - This is the asset which was sold
+ sell_volume - This is the volume of the asset which was sold
+ fee_asset - This is the asset in which the fee was charged
+ fee_volume - This is the volume of fee_asset which was charged as fee
+ comment - This value is carried through from input comment column
+ unclaimed_buy_volume - How much of the buy volume has not been matched with a sell event (should still be held)
+ unclaimed_sell_volume - How much of the sell volume has not been matched with a buy event (should be 0)
+ tax_events - A list of references to the id column of the output_tax_events.csv, events which involve this trade

**output_tax_events**
+ id - This is a unique number to reference this tax event
+ buy_ref - Reference id of the record where the asset was bought, see output_tax_events.csv
+ sell_ref - Reference id of the record where the asset was sold, see output_tax_events.csv
+ date_sold - Date when the sell event occurred
+ date_purchase - Date when the purchase event occurred
+ days_held - This is the number of days which the asset was held
+ asset_sold - The asset which was bought/sold
+ units_sold - The volume of the asset which was bought/sold as claimed in this event
+ buy_volume(AUD) - AUD value of the asset bought at the time of purchase
+ sell_volume(AUD) - AUD value of the asset sold at the time of sale
+ profit(AUD) - This is the total profit in AUD for this event
+ fees(AUD) - This is the total fees for this tax event, fees will be claimed once for each sell record
+ CGT_Discount - This is TRUE if this event is eligable for the CGT discount (more than 365 days held)
