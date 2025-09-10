

from experiments.jplag.jplag_api_handler import JPlagApiHandler

import os
api_handler = JPlagApiHandler(
    port=os.environ.get('JPLAG_API_PORT', 9995),
    auto_start=False
)

from experiments.jplag.jplag_api_interface import (
    compare as jplag_compare,
    compare_many as jplag_compare_many,
    jplag_dists
)

from experiments.jplag.jplag import calc_jplag_distances
