"""Unit tests for unlockable models (Unlockable, UserUnlockable)"""
import pytest
from datetime import datetime
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from pydantic import ValidationError
from src.models.game import Unlockable, UserUnlockable
from src.models.user import User


@pytest.fixture
def session():
    """Create a temporary in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user(session):
    """Create a test user"""
    user = User(name="test_user", age=10, email="test@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_unlockable(session):
    """Create a test unlockable"""
    unlockable = Unlockable(
        type="avatar_skin",
        name="Blue Avatar",
        description="A cool blue avatar",
        points_cost=100,
        unlock_method="redeem_points",
        rarity="common"
    )
    session.add(unlockable)
    session.commit()
    session.refresh(unlockable)
    return unlockable


def test_unlockable_model_creation(session):
    """Test that an Unlockable model can be created without errors"""
    unlockable = Unlockable(
        type="avatar_skin",
        name="Blue Avatar",
        description="A cool blue avatar",
        points_cost=100,
        unlock_method="redeem_points",
        rarity="rare"
    )
    assert unlockable.type == "avatar_skin"
    assert unlockable.name == "Blue Avatar"
    assert unlockable.description == "A cool blue avatar"
    assert unlockable.points_cost == 100
    assert unlockable.unlock_method == "redeem_points"
    assert unlockable.rarity == "rare"
    assert isinstance(unlockable.created_at, datetime)


def test_unlockable_model_persistence(session):
    """Test that Unlockable model can be persisted to database"""
    unlockable = Unlockable(
        type="theme",
        name="Dark Theme",
        description="A dark color theme",
        points_cost=50,
        unlock_method="earn_level_1",
        rarity="common"
    )
    session.add(unlockable)
    session.commit()
    session.refresh(unlockable)

    assert unlockable.id is not None
    assert unlockable.name == "Dark Theme"

    # Retrieve from database
    retrieved_unlockable = session.query(Unlockable).filter_by(name="Dark Theme").first()
    assert retrieved_unlockable is not None
    assert retrieved_unlockable.type == "theme"
    assert retrieved_unlockable.points_cost == 50


def test_unlockable_default_rarity(session):
    """Test that Unlockable rarity defaults to 'common'"""
    unlockable = Unlockable(
        type="effect",
        name="Sparkle Effect",
        points_cost=75,
        unlock_method="earn_streak_10"
    )
    session.add(unlockable)
    session.commit()
    session.refresh(unlockable)

    assert unlockable.rarity == "common"

    # Verify in database
    retrieved_unlockable = session.query(Unlockable).filter_by(name="Sparkle Effect").first()
    assert retrieved_unlockable.rarity == "common"


def test_unlockable_points_cost_non_negative(session):
    """Test that Unlockable points_cost can be 0 (non-negative constraint)"""
    unlockable = Unlockable(
        type="avatar_skin",
        name="Free Avatar",
        points_cost=0,
        unlock_method="redeem_points"
    )
    session.add(unlockable)
    session.commit()
    session.refresh(unlockable)

    assert unlockable.points_cost == 0
    retrieved_unlockable = session.query(Unlockable).filter_by(name="Free Avatar").first()
    assert retrieved_unlockable.points_cost == 0


def test_unlockable_points_cost_negative_validation(session):
    """Test that Unlockable points_cost < 0 raises ValidationError"""
    with pytest.raises(ValidationError):
        Unlockable.model_validate({
            "type": "avatar_skin",
            "name": "Invalid Avatar",
            "points_cost": -1,
            "unlock_method": "redeem_points"
        })


def test_unlockable_type_indexing(session):
    """Test that Unlockable type field is indexed and queries work efficiently"""
    unlockable1 = Unlockable(
        type="avatar_skin",
        name="Avatar 1",
        points_cost=100,
        unlock_method="redeem_points"
    )
    unlockable2 = Unlockable(
        type="theme",
        name="Theme 1",
        points_cost=50,
        unlock_method="earn_level_1"
    )
    unlockable3 = Unlockable(
        type="avatar_skin",
        name="Avatar 2",
        points_cost=120,
        unlock_method="redeem_points"
    )
    session.add_all([unlockable1, unlockable2, unlockable3])
    session.commit()

    # Query by type
    avatar_skins = session.query(Unlockable).filter_by(type="avatar_skin").all()
    themes = session.query(Unlockable).filter_by(type="theme").all()

    assert len(avatar_skins) == 2
    assert len(themes) == 1


def test_unlockable_table_creation(session):
    """Test that Unlockable table is created successfully"""
    result = session.query(Unlockable).all()
    assert result == []

    # Add an unlockable and verify it was inserted
    unlockable = Unlockable(
        type="avatar_skin",
        name="Test Avatar",
        points_cost=100,
        unlock_method="redeem_points"
    )
    session.add(unlockable)
    session.commit()

    result = session.query(Unlockable).all()
    assert len(result) == 1


def test_user_unlockable_model_creation(session, test_user, test_unlockable):
    """Test that a UserUnlockable model can be created without errors"""
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id,
        is_equipped=True
    )
    assert user_unlockable.user_id == test_user.id
    assert user_unlockable.unlockable_id == test_unlockable.id
    assert user_unlockable.is_equipped is True
    assert isinstance(user_unlockable.acquired_at, datetime)


def test_user_unlockable_model_persistence(session, test_user, test_unlockable):
    """Test that UserUnlockable model can be persisted to database"""
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id,
        is_equipped=False
    )
    session.add(user_unlockable)
    session.commit()
    session.refresh(user_unlockable)

    assert user_unlockable.id is not None

    # Retrieve from database
    retrieved_user_unlockable = session.query(UserUnlockable).filter_by(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    ).first()
    assert retrieved_user_unlockable is not None
    assert retrieved_user_unlockable.is_equipped is False


def test_user_unlockable_default_is_equipped(session, test_user, test_unlockable):
    """Test that UserUnlockable is_equipped defaults to False"""
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    session.add(user_unlockable)
    session.commit()
    session.refresh(user_unlockable)

    assert user_unlockable.is_equipped is False

    # Verify in database
    retrieved_user_unlockable = session.query(UserUnlockable).filter_by(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    ).first()
    assert retrieved_user_unlockable.is_equipped is False


def test_user_unlockable_table_creation(session, test_user, test_unlockable):
    """Test that UserUnlockable table is created successfully"""
    result = session.query(UserUnlockable).all()
    assert result == []

    # Add a user unlockable and verify it was inserted
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    session.add(user_unlockable)
    session.commit()

    result = session.query(UserUnlockable).all()
    assert len(result) == 1


def test_user_unlockable_foreign_key_constraint(session, test_user, test_unlockable):
    """Test that UserUnlockable properly references User and Unlockable"""
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    session.add(user_unlockable)
    session.commit()
    session.refresh(user_unlockable)

    # Verify foreign key references work
    retrieved_user_unlockable = session.query(UserUnlockable).filter_by(
        id=user_unlockable.id
    ).first()
    assert retrieved_user_unlockable.user_id == test_user.id
    assert retrieved_user_unlockable.unlockable_id == test_unlockable.id


def test_user_unlockable_relationship_to_user(session, test_user, test_unlockable):
    """Test that UserUnlockable relationship to User works correctly"""
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    session.add(user_unlockable)
    session.commit()
    session.refresh(user_unlockable)

    # Access the user through the relationship
    retrieved_user_unlockable = session.query(UserUnlockable).filter_by(
        id=user_unlockable.id
    ).first()
    assert retrieved_user_unlockable.user is not None
    assert retrieved_user_unlockable.user.id == test_user.id
    assert retrieved_user_unlockable.user.name == test_user.name


def test_user_unlockable_relationship_to_unlockable(session, test_user, test_unlockable):
    """Test that UserUnlockable relationship to Unlockable works correctly"""
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    session.add(user_unlockable)
    session.commit()
    session.refresh(user_unlockable)

    # Access the unlockable through the relationship
    retrieved_user_unlockable = session.query(UserUnlockable).filter_by(
        id=user_unlockable.id
    ).first()
    assert retrieved_user_unlockable.unlockable is not None
    assert retrieved_user_unlockable.unlockable.id == test_unlockable.id
    assert retrieved_user_unlockable.unlockable.name == test_unlockable.name


def test_unlockable_relationship_to_user_unlockables(session, test_user, test_unlockable):
    """Test that Unlockable relationship to UserUnlockable works correctly"""
    user_unlockable1 = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    other_user = User(name="other_user", age=11, email="other@example.com")
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    user_unlockable2 = UserUnlockable(
        user_id=other_user.id,
        unlockable_id=test_unlockable.id
    )
    session.add_all([user_unlockable1, user_unlockable2])
    session.commit()

    # Access user unlockables through the relationship
    retrieved_unlockable = session.query(Unlockable).filter_by(
        id=test_unlockable.id
    ).first()
    assert len(retrieved_unlockable.owned_by) == 2
    assert any(u.user_id == test_user.id for u in retrieved_unlockable.owned_by)
    assert any(u.user_id == other_user.id for u in retrieved_unlockable.owned_by)


def test_user_relationship_to_user_unlockables(session, test_user, test_unlockable):
    """Test that User relationship to UserUnlockable works correctly"""
    user_unlockable1 = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    unlockable2 = Unlockable(
        type="theme",
        name="Light Theme",
        points_cost=50,
        unlock_method="earn_level_1"
    )
    session.add(unlockable2)
    session.commit()
    session.refresh(unlockable2)

    user_unlockable2 = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=unlockable2.id
    )
    session.add_all([user_unlockable1, user_unlockable2])
    session.commit()

    # Access user unlockables through the relationship
    retrieved_user = session.query(User).filter_by(id=test_user.id).first()
    assert len(retrieved_user.user_unlockables) == 2
    assert all(u.user_id == test_user.id for u in retrieved_user.user_unlockables)


def test_unlockable_rarity_values(session):
    """Test that Unlockable supports different rarity values"""
    rarities = ["common", "rare", "epic"]
    for rarity in rarities:
        unlockable = Unlockable(
            type="avatar_skin",
            name=f"Avatar {rarity}",
            points_cost=100,
            unlock_method="redeem_points",
            rarity=rarity
        )
        session.add(unlockable)

    session.commit()

    # Verify all rarities are stored correctly
    common = session.query(Unlockable).filter_by(rarity="common").count()
    rare = session.query(Unlockable).filter_by(rarity="rare").count()
    epic = session.query(Unlockable).filter_by(rarity="epic").count()

    assert common == 1
    assert rare == 1
    assert epic == 1


def test_unlockable_unlock_methods(session):
    """Test that Unlockable supports different unlock methods"""
    methods = ["earn_level_1", "earn_streak_10", "redeem_points"]
    for method in methods:
        unlockable = Unlockable(
            type="avatar_skin",
            name=f"Avatar {method}",
            points_cost=100,
            unlock_method=method
        )
        session.add(unlockable)

    session.commit()

    # Verify all methods are stored correctly
    for method in methods:
        count = session.query(Unlockable).filter_by(unlock_method=method).count()
        assert count == 1


def test_multiple_users_with_same_unlockable(session, test_unlockable):
    """Test that multiple users can own the same unlockable"""
    user1 = User(name="user1", age=10, email="user1@example.com")
    user2 = User(name="user2", age=11, email="user2@example.com")
    session.add_all([user1, user2])
    session.commit()
    session.refresh(user1)
    session.refresh(user2)

    user_unlockable1 = UserUnlockable(
        user_id=user1.id,
        unlockable_id=test_unlockable.id
    )
    user_unlockable2 = UserUnlockable(
        user_id=user2.id,
        unlockable_id=test_unlockable.id
    )
    session.add_all([user_unlockable1, user_unlockable2])
    session.commit()

    # Verify both users own the unlockable
    unlockable_owners = session.query(UserUnlockable).filter_by(
        unlockable_id=test_unlockable.id
    ).all()
    assert len(unlockable_owners) == 2
    assert any(u.user_id == user1.id for u in unlockable_owners)
    assert any(u.user_id == user2.id for u in unlockable_owners)


def test_user_with_multiple_unlockables(session, test_user):
    """Test that a user can own multiple unlockables"""
    unlockable1 = Unlockable(
        type="avatar_skin",
        name="Avatar 1",
        points_cost=100,
        unlock_method="redeem_points"
    )
    unlockable2 = Unlockable(
        type="theme",
        name="Theme 1",
        points_cost=50,
        unlock_method="earn_level_1"
    )
    unlockable3 = Unlockable(
        type="effect",
        name="Effect 1",
        points_cost=75,
        unlock_method="earn_streak_10"
    )
    session.add_all([unlockable1, unlockable2, unlockable3])
    session.commit()
    session.refresh(unlockable1)
    session.refresh(unlockable2)
    session.refresh(unlockable3)

    user_unlockable1 = UserUnlockable(user_id=test_user.id, unlockable_id=unlockable1.id)
    user_unlockable2 = UserUnlockable(user_id=test_user.id, unlockable_id=unlockable2.id)
    user_unlockable3 = UserUnlockable(user_id=test_user.id, unlockable_id=unlockable3.id)
    session.add_all([user_unlockable1, user_unlockable2, user_unlockable3])
    session.commit()

    # Verify user owns all unlockables
    user_unlockables = session.query(UserUnlockable).filter_by(
        user_id=test_user.id
    ).all()
    assert len(user_unlockables) == 3
    assert any(u.unlockable_id == unlockable1.id for u in user_unlockables)
    assert any(u.unlockable_id == unlockable2.id for u in user_unlockables)
    assert any(u.unlockable_id == unlockable3.id for u in user_unlockables)


def test_user_unlockable_equipped_status(session, test_user, test_unlockable):
    """Test that equipped status can be tracked for user unlockables"""
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id,
        is_equipped=True
    )
    session.add(user_unlockable)
    session.commit()
    session.refresh(user_unlockable)

    # Change equipped status
    user_unlockable.is_equipped = False
    session.commit()
    session.refresh(user_unlockable)

    assert user_unlockable.is_equipped is False

    # Verify in database
    retrieved_user_unlockable = session.query(UserUnlockable).filter_by(
        id=user_unlockable.id
    ).first()
    assert retrieved_user_unlockable.is_equipped is False


def test_unlockable_created_at_timestamp(session):
    """Test that Unlockable created_at timestamp is set automatically"""
    before_creation = datetime.utcnow()
    unlockable = Unlockable(
        type="avatar_skin",
        name="Timestamped Avatar",
        points_cost=100,
        unlock_method="redeem_points"
    )
    session.add(unlockable)
    session.commit()
    session.refresh(unlockable)
    after_creation = datetime.utcnow()

    assert before_creation <= unlockable.created_at <= after_creation


def test_user_unlockable_acquired_at_timestamp(session, test_user, test_unlockable):
    """Test that UserUnlockable acquired_at timestamp is set automatically"""
    before_acquisition = datetime.utcnow()
    user_unlockable = UserUnlockable(
        user_id=test_user.id,
        unlockable_id=test_unlockable.id
    )
    session.add(user_unlockable)
    session.commit()
    session.refresh(user_unlockable)
    after_acquisition = datetime.utcnow()

    assert before_acquisition <= user_unlockable.acquired_at <= after_acquisition
