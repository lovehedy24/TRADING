# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

# --- Do not remove these libs ---
import numpy as np  # noqa
from numpy import NaN as npNaN
import pandas as pd  # noqa
from pandas import DataFrame

# from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade
from datetime import datetime

from freqtrade.strategy import (IStrategy, BooleanParameter, CategoricalParameter, DecimalParameter, IntParameter)
from functools import reduce
from technical.util import resample_to_interval
from technical.util import resampled_merge

# ------------------------------------------------------------------------------------------------
# Add your lib to import here
# import talib.abstract as ta
#import talib as ta
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

import pandas_ta as pd_ta


class Donchian_Opt_MY(IStrategy):
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation | the Sample strategy to get the latest version.
    INTERFACE_VERSION = 2

    # Minimal ROI designed f| the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    # minimal_roi = {
    #     "60": 0.01,
    #     "30": 0.02,
    #     "0": 0.04
    # }

    # Unrealistic ROI, so this won't interfere with the strategy logic
    minimal_roi = {
        "0": 100
    }

    # Optimal stoploss designed f| the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    # stoploss = -0.25

    # Unrealistic Stoploss, so this won't interfere with the strategy logic
    stoploss = -1

    # Trailing stoploss
    trailing_stop = True
    # trailing_only_offset_is_reached = True
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Optimal timeframe for the strategy.
    timeframe = '1h'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the "ask_strategy" section in the config.
    # use_sell_signal = False
    # sell_profit_only = True
    # ignore_roi_if_buy_signal = True

    # Number of candles the strategy requires bef|e producing valid signals
    startup_candle_count: int = 100

    # Optional |der type mapping.
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional |der time in f|ce.
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
    }

    plot_config = {
        'main_plot': {
            'DC_lower': {'color': 'red'},
            'DC_upper': {'color': 'green'},
            'DC_mid': {},
        }
    }

    # HYPEROPT ####################################################################################################
    
    # Donchian parametros optimizar
    buy_dc_upper_len = IntParameter(5, 60, default=20, space="buy")
    sell_dc_lower_len = IntParameter(5, 60, default=5, space="sell")
    
    
    #buy_dc_enabled = CategoricalParameter([True, False], default=False, space="buy")
    #sell_dc_enabled = CategoricalParameter([True, False], default=False, space="sell")

    # Triggers
    
    

    # sell_trigger = CategoricalParameter(["adx_signal", "rsi_signal"], default="adx_signal", space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        
        # Donchian ---------------------------------------------------------------------------------------- /
   
        dc_lower_len = 20
        dc_upper_len = 60
        #for val in self.buy_dc_upper_len.range:
        #    dataframe['DC_upper'] = ta.MAX(dataframe, timeperiod=val)
            
        #for val in self.sell_dc_lower_len.range:    
        #    dataframe['DC_lower'] = ta.MIN(dataframe, timeperiod=val)
        #dataframe['DC_lower'] = ta.MIN(dataframe, timeperiod=5)
        
        # Ret|na columnas con nombres: DCL_10_15, DCM_10_15, DCU_10_15
        for val in self.buy_dc_upper_len.range:
            donchian_df = pd_ta.donchian(dataframe['high'], dataframe['low'], lower_length=dc_lower_len,
                                      upper_length=val)
            dataframe['DC_lower'] = donchian_df[f"DCL_{dc_lower_len}_{val}"]
            dataframe['DC_upper'] = donchian_df[f"DCU_{dc_lower_len}_{val}"]
            dataframe['DC_mid'] = donchian_df[f"DCM_{dc_lower_len}_{val}"]
        
        for val_X in self.sell_dc_lower_len.range:
            donchian_df_X = pd_ta.donchian(dataframe['close'], dataframe['close'], lower_length=val_X,upper_length=dc_upper_len)
            dataframe['DC_lower_X'] = donchian_df_X[f"DCL_{val_X}_{dc_upper_len}"]
            dataframe['DC_upper_X'] = donchian_df_X[f"DCU_{val_X}_{dc_upper_len}"]
            dataframe['DC_mid_X'] = donchian_df_X[f"DCM_{val_X}_{dc_upper_len}"]
            
        # ADX --------------------------------------------------------------------------------------------- /
        #dataframe['adx'] = ta.ADX(dataframe['resample_1440_high'], dataframe['resample_1440_low'], dataframe['resample_1440_close'], timeperiod=14)
        #dataframe['adx_level'] = 25

        # RSI --------------------------------------------------------------------------------------------- /
        #dataframe['rsi'] = ta.RSI(dataframe['resample_1440_close'])
        #dataframe['rsi_up'] = 60
        #dataframe['rsi_down'] = 40

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        conditions = []


        #if self.buy_dc_enabled.value:
        conditions.append(dataframe['close'].shift(1) >= dataframe['DC_upper'])

        
        #Check that volume is not 0
        conditions.append(dataframe['volume'] > 0)

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # GUARDS &TRENDS
        #if self.sell_dc_enabled.value:
        conditions.append(dataframe['close'].shift(1) < dataframe['DC_lower_X'])

        # Check that volume is not 0
        conditions.append(dataframe['volume'] > 0)

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'] = 1

        return dataframe
