from bycycle.core.model.data import integrator
from bycycle.core.model import portlandor
from bycycle.core.model.portlandor import data


class Integrator(integrator.Integrator):

    def __init__(self, *args, **kwargs):
        self.region_module = portlandor
        self.region_data_module = data
        super(Integrator, self).__init__(*args, **kwargs)

    def get_state_code_for_city(self, city):
        return 'or' if city != 'vancouver' else 'wa'
