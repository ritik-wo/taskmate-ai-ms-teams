#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "2851b584-7025-47ce-ba67-5dd1922ce0ad")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "~TE8Q~RhSAe68ukOaDTEVhTUKKVTQEUzEY1vycxS")
