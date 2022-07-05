import pandas as pd

from .constants import CONTROL_ID


def get_control_df(df) -> pd.DataFrame:
    df = pd.DataFrame(df)
    df = df.set_index(CONTROL_ID)
    return df
