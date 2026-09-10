import inspect

from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.contracts.utility.transactor import Transactor


def test_utility_contracts_are_abstract():
    for cls in (Password, Token, Transactor, SingleFlight, Clock, LeveledLogger):
        assert inspect.isabstract(cls), cls.__name__


def test_repository_contracts_are_abstract():
    for cls in (PermissionRepository, RoleRepository, RolePermissionRepository, UserRepository):
        assert inspect.isabstract(cls), cls.__name__
