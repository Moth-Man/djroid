"""DAO for migration rules with CRUD operations and metadata helpers."""

from djroid.db.dao.base_dao import BaseDAO
from djroid.db.models.migration_rule import MigrationRule
from djroid.db.models.song import Song
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import Optional, List
import uuid


class MigrationRuleDAO(BaseDAO[MigrationRule]):
    """Data access object for migration rules."""

    def __init__(self, db: Session):
        super().__init__(MigrationRule, db)

    def create(self) -> MigrationRule:
        """Create a new empty migration rule (required by BaseDAO)."""
        rule = MigrationRule(
            metadata_tag="",
            metadata_value="",
            destination_directory=""
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def create_rule(
        self,
        metadata_tag: str,
        metadata_value: str,
        destination_directory: str,
        name: Optional[str] = None,
        priority: int = 0,
        enabled: bool = True
    ) -> MigrationRule:
        """Create a new migration rule with all parameters."""
        rule = MigrationRule(
            metadata_tag=metadata_tag,
            metadata_value=metadata_value,
            destination_directory=destination_directory,
            name=name,
            priority=priority,
            enabled=enabled
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_all_rules(self, enabled_only: bool = False) -> List[MigrationRule]:
        """Get all migration rules, optionally filtered by enabled status."""
        query = self.db.query(MigrationRule)
        if enabled_only:
            query = query.filter(MigrationRule.enabled == True)
        return query.order_by(MigrationRule.priority.asc()).all()

    def get_rules_by_tag(self, metadata_tag: str) -> List[MigrationRule]:
        """Get all rules for a specific metadata tag."""
        return self.db.query(MigrationRule).filter(
            MigrationRule.metadata_tag == metadata_tag
        ).order_by(MigrationRule.priority.asc()).all()

    def get_matching_rule(
        self,
        metadata_tag: str,
        metadata_value: str
    ) -> Optional[MigrationRule]:
        """Get the first enabled rule matching tag and value."""
        return self.db.query(MigrationRule).filter(
            MigrationRule.metadata_tag == metadata_tag,
            MigrationRule.metadata_value == metadata_value,
            MigrationRule.enabled == True
        ).order_by(MigrationRule.priority.asc()).first()

    def update_rule(
        self,
        rule_id: uuid.UUID,
        metadata_tag: Optional[str] = None,
        metadata_value: Optional[str] = None,
        destination_directory: Optional[str] = None,
        name: Optional[str] = None,
        priority: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> Optional[MigrationRule]:
        """Update an existing migration rule."""
        rule = self.get(rule_id)
        if not rule:
            return None

        if metadata_tag is not None:
            rule.metadata_tag = metadata_tag
        if metadata_value is not None:
            rule.metadata_value = metadata_value
        if destination_directory is not None:
            rule.destination_directory = destination_directory
        if name is not None:
            rule.name = name
        if priority is not None:
            rule.priority = priority
        if enabled is not None:
            rule.enabled = enabled

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: uuid.UUID) -> bool:
        """Delete a migration rule by ID."""
        return self.delete(rule_id)

    def rule_exists(self, metadata_tag: str, metadata_value: str) -> bool:
        """Check if a rule already exists for this tag/value combination."""
        return self.db.query(MigrationRule).filter(
            MigrationRule.metadata_tag == metadata_tag,
            MigrationRule.metadata_value == metadata_value
        ).first() is not None

    # Methods to get distinct values from songs table for dropdown population

    def get_available_metadata_tags(self) -> List[str]:
        """Get list of metadata tags that can be used for rules.

        Returns the common metadata fields from the songs table that make
        sense for organizing files (genre, artist, key, etc).
        """
        return [
            "genre",
            "artist",
            "album",
            "key",
            "year",
            "publisher",
            "bpm",  # Will need special handling for ranges
        ]

    def get_distinct_genres(self) -> List[str]:
        """Get all distinct genre values from songs table."""
        result = self.db.query(distinct(Song.genre)).filter(
            Song.genre.isnot(None),
            Song.genre != ""
        ).order_by(Song.genre).all()
        return [r[0] for r in result]

    def get_distinct_artists(self) -> List[str]:
        """Get all distinct artist values from songs table."""
        result = self.db.query(distinct(Song.artist)).filter(
            Song.artist.isnot(None),
            Song.artist != ""
        ).order_by(Song.artist).all()
        return [r[0] for r in result]

    def get_distinct_albums(self) -> List[str]:
        """Get all distinct album values from songs table."""
        result = self.db.query(distinct(Song.album)).filter(
            Song.album.isnot(None),
            Song.album != ""
        ).order_by(Song.album).all()
        return [r[0] for r in result]

    def get_distinct_keys(self) -> List[str]:
        """Get all distinct key values from songs table."""
        result = self.db.query(distinct(Song.key)).filter(
            Song.key.isnot(None),
            Song.key != ""
        ).order_by(Song.key).all()
        return [r[0] for r in result]

    def get_distinct_years(self) -> List[int]:
        """Get all distinct year values from songs table."""
        result = self.db.query(distinct(Song.year)).filter(
            Song.year.isnot(None)
        ).order_by(Song.year).all()
        return [r[0] for r in result]

    def get_distinct_publishers(self) -> List[str]:
        """Get all distinct publisher values from songs table."""
        result = self.db.query(distinct(Song.publisher)).filter(
            Song.publisher.isnot(None),
            Song.publisher != ""
        ).order_by(Song.publisher).all()
        return [r[0] for r in result]

    def get_distinct_values_for_tag(self, tag: str) -> List[str]:
        """Get distinct values for a given metadata tag.

        Args:
            tag: The metadata tag name (genre, artist, album, key, year, publisher)

        Returns:
            List of distinct values as strings
        """
        tag_methods = {
            "genre": self.get_distinct_genres,
            "artist": self.get_distinct_artists,
            "album": self.get_distinct_albums,
            "key": self.get_distinct_keys,
            "year": lambda: [str(y) for y in self.get_distinct_years()],
            "publisher": self.get_distinct_publishers,
        }

        method = tag_methods.get(tag.lower())
        if method:
            return method()
        return []
