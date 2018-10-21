# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from kombu import Connection

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.liveaction import LiveActionDB
from st2common.transport import consumers
from st2common.transport import utils as transport_utils
from st2common.util import action_db as action_utils
from st2common.util import execution_queue_db as exdb
from st2common.transport.queues import ACTIONSCHEDULER_REQUEST_QUEUE
from st2common.persistence.execution_queue import ExecutionQueue

__all__ = [
    'ActionExecutionQueuer',
    'get_queuer'
]


LOG = logging.getLogger(__name__)


class ActionExecutionQueuer(consumers.MessageHandler):
    message_type = LiveActionDB

    def process(self, request):
        """Adds execution into execution_queue database for scheduling

        :param request: Action execution request.
        :type request: ``st2common.models.db.liveaction.LiveActionDB``
        """
        if request.status != action_constants.LIVEACTION_STATUS_REQUESTED:
            LOG.info('%s is ignoring %s (id=%s) with "%s" status.',
                     self.__class__.__name__, type(request), request.id, request.status)
            return

        try:
            liveaction_db = action_utils.get_liveaction_by_id(request.id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find liveaction %s in the database.', request.id)
            raise

        execution_request = exdb.create_execution_request_from_liveaction(
            liveaction_db,
            delay=liveaction_db.delay
        )
        ExecutionQueue.add_or_update(execution_request)


def get_queuer():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return ActionExecutionQueuer(conn, [ACTIONSCHEDULER_REQUEST_QUEUE])
