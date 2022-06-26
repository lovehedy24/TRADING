# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from functools import reduce
import pandas_ta as pd_ta

class DD(IStrategy):
    """
    This is a strategy template to get you started.
    More information in https://www.freqtrade.io/en/latest/strategy-customization/

    You can:
        :return: a Dataframe with all mandatory indicators for the strategies
    - Rename the class name (Do not forget to update class_name)
    - Add any methods you want to build your strategy
    - Add any lib you need to build your strategy

    You must keep:
    - the lib in the section "Do not remove these libs"
    - the methods: populate_indicators, populate_entry_trend, populate_exit_trend
    You should keep:
    - timeframe, minimal_roi, stoploss, trailing_*
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy.
    timeframe = '1h'

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }
    
    #minimal_roi = {
    #    "0": 100
    #}
    
    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.10

    # Trailing stoploss
    trailing_stop = True#False
    # trailing_only_offset_is_reached = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Strategy parameters
     
    buy_dc_upper_len = IntParameter(5, 60, default=20, space="buy")
    sell_dc_lower_len = IntParameter(5, 60, default=5, space="sell")
    
    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }
    
    @property
    def plot_config(self):
        return {
            'main_plot': 
            {
            'DC_lower': {'color': 'red'},
            'DC_upper': {'color': 'green'},
            'DC_mid': {},
            }
        }

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        
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
            donchian_df_X = pd_ta.donchian(dataframe['high'], dataframe['low'], lower_length=val_X,upper_length=dc_upper_len)
            dataframe['DC_lower_X'] = donchian_df_X[f"DCL_{val_X}_{dc_upper_len}"]
            dataframe['DC_upper_X'] = donchian_df_X[f"DCU_{val_X}_{dc_upper_len}"]
            dataframe['DC_mid_X'] = donchian_df_X[f"DCM_{val_X}_{dc_upper_len}"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """
        conditions = []
        
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
    