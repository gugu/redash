import time
from flask import request, Blueprint
from flask_restful import Resource, abort
from flask_login import current_user, login_required
from peewee import DoesNotExist

from redash import settings
from redash.tasks import record_event
from redash.models import ApiUser
from redash.authentication import current_org

routes = Blueprint('redash', __name__, template_folder=settings.fix_assets_path('templates'))


class BaseResource(Resource):
    decorators = [login_required]

    def __init__(self, *args, **kwargs):
        super(BaseResource, self).__init__(*args, **kwargs)
        self._user = None

    def dispatch_request(self, *args, **kwargs):
        kwargs.pop('org_slug', None)

        return super(BaseResource, self).dispatch_request(*args, **kwargs)

    @property
    def current_user(self):
        return current_user._get_current_object()

    @property
    def current_org(self):
        return current_org._get_current_object()

    def record_event(self, options):
        if isinstance(self.current_user, ApiUser):
            options.update({
                'api_key': self.current_user.id,
                'org_id': self.current_org.id
            })
        else:
            options.update({
                'user_id': self.current_user.id,
                'org_id': self.current_org.id
            })

        options.update({
            'user_agent': request.user_agent.string,
            'ip': request.remote_addr
        })

        if 'timestamp' not in options:
            options['timestamp'] = int(time.time())

        record_event.delay(options)


def require_fields(req, fields):
    for f in fields:
        if f not in req:
            abort(400)


def get_object_or_404(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except DoesNotExist:
        abort(404)


def org_scoped_rule(rule):
    if settings.MULTI_ORG:
        return "/<org_slug:org_slug>{}".format(rule)

    return rule
