# db/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Table, Index, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

# Many-to-many relationship between observations and tags
observation_tags = Table(
    'observation_tags',
    Base.metadata,
    Column('observation_id', Integer, ForeignKey('observations.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class LifelistType(Base):
    __tablename__ = 'lifelist_types'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    icon = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lifelists = relationship("Lifelist", back_populates="lifelist_type")
    tiers = relationship("LifelistTypeTier", back_populates="lifelist_type", cascade="all, delete-orphan")
    configs = relationship("LifelistTypeConfig", back_populates="lifelist_type", cascade="all, delete-orphan")


class LifelistTypeTier(Base):
    __tablename__ = 'lifelist_type_tiers'

    id = Column(Integer, primary_key=True)
    lifelist_type_id = Column(Integer, ForeignKey('lifelist_types.id', ondelete='CASCADE'))
    tier_name = Column(String, nullable=False)
    tier_order = Column(Integer, nullable=False)

    # Relationships
    lifelist_type = relationship("LifelistType", back_populates="tiers")


class LifelistTypeConfig(Base):
    __tablename__ = 'lifelist_type_configs'

    id = Column(Integer, primary_key=True)
    lifelist_type_id = Column(Integer, ForeignKey('lifelist_types.id', ondelete='CASCADE'))
    config_key = Column(String, nullable=False)
    config_value = Column(String)

    # Relationships
    lifelist_type = relationship("LifelistType", back_populates="configs")


class Lifelist(Base):
    __tablename__ = 'lifelists'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    lifelist_type_id = Column(Integer, ForeignKey('lifelist_types.id'))
    classification = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lifelist_type = relationship("LifelistType", back_populates="lifelists")
    observations = relationship("Observation", back_populates="lifelist", cascade="all, delete-orphan")
    custom_fields = relationship("CustomField", back_populates="lifelist", cascade="all, delete-orphan")
    tiers = relationship("LifelistTier", back_populates="lifelist", cascade="all, delete-orphan")
    classifications = relationship("Classification", back_populates="lifelist", cascade="all, delete-orphan")


class LifelistTier(Base):
    __tablename__ = 'lifelist_tiers'

    id = Column(Integer, primary_key=True)
    lifelist_id = Column(Integer, ForeignKey('lifelists.id', ondelete='CASCADE'))
    tier_name = Column(String, nullable=False)
    tier_order = Column(Integer, nullable=False)

    # Relationships
    lifelist = relationship("Lifelist", back_populates="tiers")

    __table_args__ = (
        Index('idx_unique_tier_name', 'lifelist_id', 'tier_name', unique=True),
    )


class CustomField(Base):
    __tablename__ = 'custom_fields'

    id = Column(Integer, primary_key=True)
    lifelist_id = Column(Integer, ForeignKey('lifelists.id', ondelete='CASCADE'))
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)
    field_options = Column(JSON)
    is_required = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)

    # Relationships
    lifelist = relationship("Lifelist", back_populates="custom_fields")
    options = relationship("FieldOption", back_populates="field", cascade="all, delete-orphan")
    dependencies = relationship("FieldDependency",
                                foreign_keys="FieldDependency.field_id",
                                back_populates="field",
                                cascade="all, delete-orphan")
    parent_dependencies = relationship("FieldDependency",
                                       foreign_keys="FieldDependency.parent_field_id",
                                       back_populates="parent_field",
                                       cascade="all, delete-orphan")
    values = relationship("ObservationCustomField", back_populates="field", cascade="all, delete-orphan")


class FieldOption(Base):
    __tablename__ = 'field_options'

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    option_value = Column(String, nullable=False)
    option_label = Column(String)
    option_order = Column(Integer, default=0)

    # Relationships
    field = relationship("CustomField", back_populates="options")


class FieldDependency(Base):
    __tablename__ = 'field_dependencies'

    id = Column(Integer, primary_key=True)
    field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    parent_field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    condition_type = Column(String, nullable=False)
    condition_value = Column(String)

    # Relationships
    field = relationship("CustomField", foreign_keys=[field_id], back_populates="dependencies")
    parent_field = relationship("CustomField", foreign_keys=[parent_field_id], back_populates="parent_dependencies")


class Observation(Base):
    __tablename__ = 'observations'

    id = Column(Integer, primary_key=True)
    lifelist_id = Column(Integer, ForeignKey('lifelists.id', ondelete='CASCADE'))
    entry_name = Column(String, nullable=False)
    observation_date = Column(DateTime)
    location = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    tier = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lifelist = relationship("Lifelist", back_populates="observations")
    photos = relationship("Photo", back_populates="observation", cascade="all, delete-orphan")
    custom_fields = relationship("ObservationCustomField", back_populates="observation", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=observation_tags, back_populates="observations")

    __table_args__ = (
        Index('idx_observation_entry', 'lifelist_id', 'entry_name'),
        Index('idx_observation_tier', 'lifelist_id', 'tier'),
    )


class ObservationCustomField(Base):
    __tablename__ = 'observation_custom_fields'

    id = Column(Integer, primary_key=True)
    observation_id = Column(Integer, ForeignKey('observations.id', ondelete='CASCADE'))
    field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    value = Column(String)

    # Relationships
    observation = relationship("Observation", back_populates="custom_fields")
    field = relationship("CustomField", back_populates="values")

    __table_args__ = (
        Index('idx_obs_field', 'observation_id', 'field_id', unique=True),
    )


class Photo(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True)
    observation_id = Column(Integer, ForeignKey('observations.id', ondelete='CASCADE'))
    file_path = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    latitude = Column(Float)
    longitude = Column(Float)
    taken_date = Column(DateTime)
    width = Column(Integer)
    height = Column(Integer)

    # Relationships
    observation = relationship("Observation", back_populates="photos")

    __table_args__ = (
        Index('idx_photos_observation', 'observation_id'),
        Index('idx_photos_primary', 'observation_id', 'is_primary'),
    )


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String)

    # Relationships
    observations = relationship("Observation", secondary=observation_tags, back_populates="tags")
    child_tags = relationship("TagHierarchy",
                              foreign_keys="TagHierarchy.parent_tag_id",
                              back_populates="parent_tag",
                              cascade="all, delete-orphan")
    parent_tags = relationship("TagHierarchy",
                               foreign_keys="TagHierarchy.tag_id",
                               back_populates="tag",
                               cascade="all, delete-orphan")


class TagHierarchy(Base):
    __tablename__ = 'tag_hierarchy'

    id = Column(Integer, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'))
    parent_tag_id = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'))

    # Relationships
    tag = relationship("Tag", foreign_keys=[tag_id], back_populates="parent_tags")
    parent_tag = relationship("Tag", foreign_keys=[parent_tag_id], back_populates="child_tags")


class Classification(Base):
    __tablename__ = 'classifications'

    id = Column(Integer, primary_key=True)
    lifelist_id = Column(Integer, ForeignKey('lifelists.id', ondelete='CASCADE'))
    name = Column(String, nullable=False)
    version = Column(String)
    source = Column(String)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lifelist = relationship("Lifelist", back_populates="classifications")
    entries = relationship("ClassificationEntry", back_populates="classification", cascade="all, delete-orphan")


class ClassificationEntry(Base):
    __tablename__ = 'classification_entries'

    id = Column(Integer, primary_key=True)
    classification_id = Column(Integer, ForeignKey('classifications.id', ondelete='CASCADE'))
    name = Column(String, nullable=False)
    alternate_name = Column(String)
    parent_id = Column(Integer, ForeignKey('classification_entries.id', ondelete='SET NULL'))
    category = Column(String)
    code = Column(String)
    rank = Column(String)
    is_custom = Column(Boolean, default=False)
    additional_data = Column(JSON)

    # Relationships
    classification = relationship("Classification", back_populates="entries")
    parent = relationship("ClassificationEntry", remote_side=[id], backref="children")

    __table_args__ = (
        Index('idx_classification_name', 'classification_id', 'name'),
        Index('idx_classification_alt', 'classification_id', 'alternate_name'),
        Index('idx_classification_category', 'classification_id', 'category'),
    )