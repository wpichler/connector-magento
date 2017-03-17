# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Wolfgang Pichler
#    Copyright 2016 Callino
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
from openerp import models, fields, api
from openerp.addons.connector.queue.job import Job, _unpickle
from openerp.addons.connector.session import ConnectorSessionHandler
_logger = logging.getLogger(__name__)
import openerp
import threading


class QueueJob(models.Model):
    _name = 'queue.job'
    _inherit = 'queue.job'

    @api.multi
    def button_run(self):
        for job in self:
            _logger.info("Requested to run this job %s now: ", job.uuid)
            func = _unpickle(job.func)
            (func_name, args, kwargs) = func
            dt_from_string = openerp.fields.Datetime.from_string
            eta = None
            if job.eta:
                eta = dt_from_string(job.eta)
            job_ = Job(func=func_name, args=args, kwargs=kwargs,
                       priority=job.priority, eta=eta, job_uuid=job.uuid,
                       description=job.name)
            _logger.info("got job: %r", job_)
            db_name = getattr(threading.currentThread(), 'dbname', '?')
            session_hdl = ConnectorSessionHandler(db_name, 1)
            with session_hdl.session() as session:
                job_.perform(session)
        return True
