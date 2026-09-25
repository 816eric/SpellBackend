import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from src.services.unlockable_manager import UnlockableManager
from src.models.user import User
from src.models.game import Unlockable, UserUnlockable

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_create_unlockable(session: Session):
    """Test creating a cosmetic."""
    manager = UnlockableManager(session)
    unlockable = manager.create_unlockable(
        type="avatar_skin",
        name="Blue Cat",
        description="A blue cat",
        points_cost=0,
        unlock_method="earn_level_1"
    )

    assert unlockable.id is not None
    assert unlockable.name == "Blue Cat"

def test_redeem_insufficient_points(session: Session):
    """Test redeeming with insufficient points."""
    manager = UnlockableManager(session)

    user = User(name="poor_user", total_points=10)
    unlockable = Unlockable(
        type="avatar",
        name="Expensive",
        points_cost=50,
        unlock_method="redeem_points"
    )
    session.add_all([user, unlockable])
    session.commit()

    result = manager.redeem_unlockable(user.id, unlockable.id)
    assert result["ok"] is False
    assert "Insufficient" in result["message"]

def test_redeem_success(session: Session):
    """Test successful cosmetic redemption."""
    manager = UnlockableManager(session)

    user = User(name="rich_user", total_points=100, coins=100)
    unlockable = Unlockable(
        type="avatar",
        name="Blue Cat",
        points_cost=50,
        unlock_method="redeem_points"
    )
    session.add_all([user, unlockable])
    session.commit()

    result = manager.redeem_unlockable(user.id, unlockable.id)
    assert result["ok"] is True
    assert result["remaining_points"] == 50

def test_equip_cosmetic(session: Session):
    """Test equipping a cosmetic."""
    manager = UnlockableManager(session)

    user = User(name="user")
    unlockable = Unlockable(
        type="avatar",
        name="Blue Cat",
        points_cost=0,
        unlock_method="earn_level_1"
    )
    session.add_all([user, unlockable])
    session.commit()

    # Own it first
    manager.redeem_unlockable(user.id, unlockable.id)

    # Equip
    result = manager.equip_cosmetic(user.id, unlockable.id)
    assert result["ok"] is True
