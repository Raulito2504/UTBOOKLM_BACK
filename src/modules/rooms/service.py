from src.modules.rooms.ws import RoomConnectionManager, manager


def get_room_manager() -> RoomConnectionManager:
    return manager
