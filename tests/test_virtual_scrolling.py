# test_virtual_scrolling.py
"""
Performance test script for virtual scrolling and session management
"""
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add application directory to path
sys.path.append(str(Path(__file__).parent))

from config import Config
from db.base import DatabaseManager
from db.session_manager import SessionManager
from db.repositories import LifelistRepository, ObservationRepository
from db.models import Lifelist, Observation, Tag, LifelistType, LifelistTypeTier
from services.photo_manager import PhotoManager
from services.data_service import DataService


def create_test_data(session, num_observations=5000):
    """Create test data for performance testing"""
    print(f"Creating test data with {num_observations} observations...")

    # Create a lifelist type if needed
    lifelist_type = session.query(LifelistType).filter(
        LifelistType.name == "Performance Test"
    ).first()

    if not lifelist_type:
        lifelist_type = LifelistType(
            name="Performance Test",
            description="Test lifelist for performance testing"
        )
        session.add(lifelist_type)
        session.flush()

        # Add tiers
        tiers = ["verified", "unverified", "potential"]
        for i, tier in enumerate(tiers):
            tier_obj = LifelistTypeTier(
                lifelist_type_id=lifelist_type.id,
                tier_name=tier,
                tier_order=i
            )
            session.add(tier_obj)

    # Create test lifelist
    lifelist = Lifelist(
        name=f"Virtual Scroll Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        lifelist_type_id=lifelist_type.id
    )
    session.add(lifelist)
    session.flush()

    # Create tags (check if they already exist first)
    tags = []
    tag_names = ["Common", "Rare", "Near Threatened", "Endangered", "Extinct in Wild"]
    for name in tag_names:
        # Check if tag already exists
        existing_tag = session.query(Tag).filter(
            Tag.name == name,
            Tag.category == "Conservation Status"
        ).first()

        if existing_tag:
            tags.append(existing_tag)
        else:
            tag = Tag(name=name, category="Conservation Status")
            session.add(tag)
            tags.append(tag)
    session.flush()

    # Create observations in batches
    batch_size = 100
    entries = [
        "American Robin", "Blue Jay", "Northern Cardinal", "Red-winged Blackbird",
        "House Sparrow", "Rock Pigeon", "European Starling", "Great Blue Heron",
        "Bald Eagle", "Turkey Vulture", "Golden Eagle", "Peregrine Falcon",
        "Northern Mockingbird", "Brown Thrasher", "American Crow", "Common Grackle",
        "Ruby-throated Hummingbird", "Barred Owl", "Great Horned Owl", "Eastern Bluebird"
    ]

    start_time = time.time()
    for i in range(0, num_observations, batch_size):
        batch = []
        for j in range(batch_size):
            if i + j >= num_observations:
                break

            obs = Observation(
                lifelist_id=lifelist.id,
                entry_name=random.choice(entries),
                observation_date=datetime.now() - timedelta(days=random.randint(0, 1000)),
                location=f"Location {random.randint(1, 100)}",
                latitude=round(random.uniform(30, 45), 6),
                longitude=round(random.uniform(-100, -70), 6),
                tier=random.choice(["verified", "unverified", "potential"]),
                notes=f"Test observation {i + j + 1}"
            )
            batch.append(obs)

            # Add some tags
            num_tags = random.randint(0, 3)
            selected_tags = random.sample(tags, num_tags)
            obs.tags.extend(selected_tags)

        session.add_all(batch)

        if (i + batch_size) % 1000 == 0:
            session.commit()
            print(f"Created {i + batch_size} observations...")

    session.commit()
    end_time = time.time()

    print(f"Created {num_observations} observations in {end_time - start_time:.2f} seconds")
    return lifelist.id


def test_virtual_scrolling_performance(session_manager, lifelist_id):
    """Test virtual scrolling performance"""
    print("\nTesting virtual scrolling performance...")

    # Test batch loading at different offsets
    offsets = [0, 500, 1000, 2500, 4500]
    batch_sizes = [50, 100, 200]

    for batch_size in batch_sizes:
        print(f"\nTesting with batch size: {batch_size}")

        for offset in offsets:
            with session_manager.list_session() as session:
                start_time = time.time()

                observations = ObservationRepository.get_observations_batch(
                    session,
                    lifelist_id,
                    offset=offset,
                    limit=batch_size
                )

                end_time = time.time()

                print(f"  Offset {offset}: {end_time - start_time:.4f} seconds "
                      f"({len(observations)} rows)")


def test_filter_performance(session_manager, lifelist_id):
    """Test filter performance with large datasets"""
    print("\nTesting filter performance...")

    filters = [
        {"tier": "verified", "search_text": None, "tag_ids": None},
        {"tier": None, "search_text": "Robin", "tag_ids": None},
        {"tier": "unverified", "search_text": "Blue", "tag_ids": None},
        {"tier": None, "search_text": None, "tag_ids": [1, 2]}  # First two tags
    ]

    with session_manager.list_session() as session:
        for i, filter_set in enumerate(filters):
            start_time = time.time()

            count = ObservationRepository.count_observations(
                session,
                lifelist_id,
                tier=filter_set["tier"],
                search_text=filter_set["search_text"],
                tag_ids=filter_set["tag_ids"]
            )

            end_time = time.time()

            print(f"Filter {i + 1}: {end_time - start_time:.4f} seconds "
                  f"({count} matching rows)")


def test_detail_view_performance(session_manager, lifelist_id):
    """Test detail view performance with eager loading"""
    print("\nTesting detail view performance...")

    # Get some random observation IDs
    with session_manager.list_session() as session:
        observation_ids = session.query(Observation.id).filter(
            Observation.lifelist_id == lifelist_id
        ).limit(10).all()
        observation_ids = [id[0] for id in observation_ids]

    with session_manager.detail_session("test_detail") as session:
        for obs_id in observation_ids:
            start_time = time.time()

            observation_data = ObservationRepository.get_observation_with_eager_loading(
                session, obs_id
            )

            end_time = time.time()

            print(f"Observation {obs_id}: {end_time - start_time:.4f} seconds")

    # Clean up detail session
    session_manager.close_view_session("test_detail")


def test_memory_usage():
    """Test memory usage with virtual scrolling"""
    print("\nTesting memory usage...")

    # Create a simple virtual model
    from ui.views.lifelist_view import VirtualObservationModel

    # This would require Qt to test properly
    print("Memory usage test requires Qt environment - skipping in standalone test")


def test_export_performance(session_manager, data_service, lifelist_id):
    """Test export performance with chunked processing"""
    print("\nTesting export performance...")

    export_path = Path("test_export")

    start_time = time.time()

    with session_manager.chunked_operation() as session:
        success = data_service.export_lifelist(
            session,
            lifelist_id,
            export_path,
            include_photos=False,
            batch_size=200
        )

    end_time = time.time()

    if success:
        print(f"Export completed in {end_time - start_time:.2f} seconds")

        # Check exported file size
        json_file = next(export_path.glob("*.json"))
        file_size_mb = json_file.stat().st_size / (1024 * 1024)
        print(f"Exported file size: {file_size_mb:.2f} MB")
    else:
        print("Export failed")


def main():
    """Run all performance tests"""
    # Initialize database
    config = Config()
    db_manager = DatabaseManager("test_performance.db")
    db_manager.create_tables()

    # Create session manager
    session_manager = SessionManager(db_manager)

    try:
        # Create services
        photo_manager = PhotoManager("test_storage")
        data_service = DataService(photo_manager)

        # Create test data
        with session_manager.list_session() as session:
            lifelist_id = create_test_data(session)

        # Run performance tests
        test_virtual_scrolling_performance(session_manager, lifelist_id)
        test_filter_performance(session_manager, lifelist_id)
        test_detail_view_performance(session_manager, lifelist_id)
        test_export_performance(session_manager, data_service, lifelist_id)

        print("\nPerformance tests completed!")

    finally:
        # Ensure all connections are closed
        db_manager.Session.remove()

        # Clean up (with better error handling for Windows)
        try:
            Path("test_performance.db").unlink()
        except (FileNotFoundError, PermissionError) as e:
            print(f"\nNote: Could not delete test database file: {e}")
            print("This is common on Windows and can be ignored. You may need to delete it manually later.")

        # Clean up test export directory if it exists
        import shutil
        try:
            if Path("test_export").exists():
                shutil.rmtree("test_export")
        except (OSError, PermissionError) as e:
            print(f"\nNote: Could not delete test export directory: {e}")
            print("You may need to delete it manually later.")


if __name__ == "__main__":
    main()