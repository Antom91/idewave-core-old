from World.Object.Unit.model import Unit
from World.Object.Unit.Stats.UnitStats import UnitStats


class UnitStatsBuilder(object):

    __slots__ = ('world_object', 'stats')

    def __init__(self, **kwargs):
        self.stats = UnitStats()
        self.world_object: Unit = kwargs.pop('world_object')

    def build(self):
        self.stats.health = self.stats.max_health = self.world_object.health

        return self

    def get_stats(self):
        return self.stats