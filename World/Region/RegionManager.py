from time import time
from typing import List, Union, Callable, Dict

from World.Region.model import Region, DefaultLocation
from World.Region.Octree.OctreeManager import OctreeManager

from DB.Connection.WorldConnection import WorldConnection
from World.WorldPacket.Constants.WorldOpCode import WorldOpCode
from Utils.Debug.Logger import Logger


class RegionManager(object):

    __slots__ = ('external_session', 'session', 'region', 'regions')

    def __init__(self, **kwargs):
        external_session = kwargs.pop('session', None)

        if external_session:
            self.session = external_session
        else:
            connection = WorldConnection()
            self.session = connection.session

        self.region: Union[Region, None] = None
        self.regions: Dict[int, Region] = self.load_all()

    # def get_regions_as_json(self):
    #     return [region.to_json() for region in self.regions]

    # FIXME: get region from ALREADY loaded regions list
    def get_region(self, **kwargs) -> Region:
        # TODO: fix args receiving
        identifier = kwargs.pop('identifier', None)
        try:
            region = self.session.query(Region).filter_by(identifier=identifier).first()
        except Exception as e:
            raise Exception('[Region Manager]: get_region exception "{}"'.format(e))
        else:
            return region

    def create(self, **kwargs):
        identifier = kwargs.pop('identifier', None)
        y1 = kwargs.pop('y1', None)
        y2 = kwargs.pop('y2', None)
        x1 = kwargs.pop('x1', None)
        x2 = kwargs.pop('x2', None)
        continent_id = kwargs.pop('continent_id', None)

        self.region = Region()
        self.region.identifier = identifier
        self.region.y1 = y1
        self.region.y2 = y2
        self.region.x1 = x1
        self.region.x2 = x2
        self.region.continent_id = continent_id

        return self

    def create_default_location(self, **kwargs) -> None:
        identifier = kwargs.pop('identifier', None)
        x = kwargs.pop('x', None)
        y = kwargs.pop('y', None)
        z = kwargs.pop('z', None)
        map_id = kwargs.pop('map_id', None)
        race = kwargs.pop('race', None)

        region = self.session.query(Region).filter_by(identifier=identifier).first()

        default_location = DefaultLocation()
        default_location.region = region
        default_location.x = x
        default_location.y = y
        default_location.z = z
        default_location.map_id = map_id
        default_location.race = race

        self.session.add(default_location)
        self.session.commit()

    def load_all(self) -> Dict[int, Region]:
        Logger.debug('[RegionMgr]: Loading regions')
        regions = self.session.query(Region).all()
        t0 = time()

        result: Dict[int, Region] = {}

        for region in regions:
            objects = RegionManager.load_region_objects(region)
            octree = OctreeManager.create_octree(
                x0=region.x2,
                x1=region.x1,
                y0=region.y2,
                y1=region.y1,
                objects=objects
            )
            region.set_octree(octree)
            result[region.id] = region

        t1 = time()
        Logger.debug('[RegionMgr]: regions loaded in {}s'.format(t1 - t0))

        return result

    # TODO: store separately players, units and other objects
    @staticmethod
    def load_region_objects(region: Region):
        return {unit.guid: unit for unit in region.units}

    # @staticmethod
    # def get_spawn_packets(objects: List[Union[Unit, Player]]):
    #     update_flags = (
    #         UpdateObjectFlags.UPDATEFLAG_HIGHGUID.value |
    #         UpdateObjectFlags.UPDATEFLAG_LIVING.value |
    #         UpdateObjectFlags.UPDATEFLAG_HAS_POSITION.value
    #     )
    #
    #     head_mgr = None
    #
    #     while objects:
    #         current = objects.pop()
    #         manager = RegionManager.get_manager_by_object_type(current)
    #
    #         if manager is None:
    #             Logger.warning('[RegionMgr]: it seems there are object with incorrect type')
    #             continue
    #
    #         fields = RegionManager.get_update_fields_by_object_type(current)
    #
    #         with manager as mgr:
    #             RegionManager._init_update_packet_builder(
    #                 mgr,
    #                 object_update_type=ObjectUpdateType.CREATE_OBJECT2,
    #                 update_flags=update_flags,
    #                 update_object=objects.pop()
    #             )
    #
    #             if head_mgr is None:
    #                 head_mgr = mgr
    #
    #             batch = mgr.create_batch(fields)
    #             head_mgr.add_batch(batch)
    #
    #     if head_mgr is None:
    #         return []
    #
    #     return head_mgr.build_update_packet().get_update_packets()

    # @staticmethod
    # def send_despawn_packets(current_object: Player, guids: List[int]) -> None:
    #     asyncio.ensure_future(
    #         QueuesRegistry.dynamic_packets_queue.put((
    #             current_object.name,
    #             [pack('<Q', guid) for guid in guids],
    #             WorldOpCode.SMSG_DESTROY_OBJECT
    #         ))
    #     )

    def save(self):
        self.session.add(self.region)
        self.session.commit()
        return self

    def broadcast(self, opcode: WorldOpCode, packets: List[bytes], callback: Callable):
        callback(opcode=opcode, packets=packets, regions=self.regions)

    # enter/exit are safe, should be used instead of __del__
    def __enter__(self):
        connection = WorldConnection()
        self.session = connection.session
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        return False
