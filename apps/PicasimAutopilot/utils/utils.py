from typing import Union


def normalize(value: Union[int, float], _min=-1, _max=1) -> Union[int, float]:
    """
    Normalize a value between a min and max value
    """
    if value > _max:
        return _max
    elif value < _min:
        return _min
    else:
        return value
