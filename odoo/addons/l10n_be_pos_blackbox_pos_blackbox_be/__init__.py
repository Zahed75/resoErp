from . import models


def migrate_data_from_v1_to_v2(env):
    env["pos.config"]._migrate_blackbox_data_v1_to_v2()
