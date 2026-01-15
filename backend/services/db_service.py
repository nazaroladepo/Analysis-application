# db_service.py

import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.db.models import Plant, ProcessedData, VegetationIndexTimeline, TextureTimeline, MorphologyTimeline

logger = logging.getLogger(__name__)

class PlantService:
    """Service class for plant-related database operations."""
    
    @staticmethod
    def _serialize_date_value(value: Any) -> str:
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _serialize_date_list(values: Optional[List[Any]]) -> List[str]:
        if not values:
            return []
        return [PlantService._serialize_date_value(value) for value in values]
    
    @staticmethod
    def create_or_update_plant(db: Session, plant_id: str, species: str, capture_date: date) -> Plant:
        """
        Create a new plant entry or update existing one with new capture date.
        
        Args:
            db: Database session
            plant_id: Unique plant identifier
            species: Plant species name
            capture_date: Date when the plant was captured
            
        Returns:
            Plant object
            
        Raises:
            IntegrityError: If there's a database constraint violation
        """
        try:
            # Check if plant already exists
            plant = db.query(Plant).filter(Plant.id == plant_id).first()
            
            capture_date_serialized = PlantService._serialize_date_value(capture_date)

            if plant:
                # Update existing plant - add new date if not already present
                existing_dates = PlantService._serialize_date_list(plant.dates_captured)
                if capture_date_serialized not in existing_dates:
                    existing_dates.append(capture_date_serialized)
                    existing_dates.sort()
                    plant.dates_captured = existing_dates
                    logger.info(f"Added date {capture_date_serialized} to existing plant {plant_id}. All dates: {existing_dates}")
                else:
                    logger.info(f"Date {capture_date_serialized} already exists for plant {plant_id}")
                # Ensure changes are tracked
                db.add(plant)
            else:
                # Create new plant
                plant = Plant(
                    id=plant_id,
                    species=species,
                    dates_captured=[capture_date_serialized]
                )
                db.add(plant)
                logger.info(f"Created new plant {plant_id} for species {species} with date {capture_date_serialized}")
            
            db.commit()
            db.refresh(plant)
            logger.info(f"Committed plant {plant_id}. Current dates: {plant.dates_captured}")
            return plant
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error for plant {plant_id}: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating/updating plant {plant_id}: {e}")
            raise
    
    @staticmethod
    def get_plant_by_id(db: Session, plant_id: str) -> Optional[Plant]:
        """Get plant by ID."""
        return db.query(Plant).filter(Plant.id == plant_id).first()
    
    @staticmethod
    def get_plants_by_species(db: Session, species: str) -> List[Plant]:
        """Get all plants for a specific species."""
        return db.query(Plant).filter(Plant.species == species).all()
    
    @staticmethod
    def get_all_plants(db: Session) -> List[Plant]:
        """Get all plants."""
        return db.query(Plant).all()
    
    @staticmethod
    def get_plant_statistics(db: Session) -> Dict[str, Any]:
        """Get plant statistics."""
        total_plants = db.query(Plant).count()
        total_species = db.query(Plant.species).distinct().count()
        species_counts = db.query(Plant.species, db.func.count(Plant.id)).group_by(Plant.species).all()
        
        return {
            "total_plants": total_plants,
            "total_species": total_species,
            "species_breakdown": {species: count for species, count in species_counts}
        }

class ProcessedDataService:
    """Service class for processed data operations."""
    
    @staticmethod
    def create_processed_data_entry(
        db: Session,
        plant_id: str,
        date_captured: date,
        image_key: Optional[str] = None,
        vegetation_features: Optional[Dict[str, Any]] = None,
        morphology_features: Optional[Dict[str, Any]] = None,
        texture_features: Optional[Dict[str, Any]] = None
    ) -> ProcessedData:
        """
        Create a new processed data entry.
        
        Args:
            db: Database session
            plant_id: Plant identifier
            date_captured: Date when the image was captured
            image_key: S3 key for the image
            vegetation_features: Vegetation analysis features
            morphology_features: Morphology analysis features
            texture_features: Texture analysis features
            
        Returns:
            ProcessedData object
        """
        try:
            # Create unique ID for the processed data entry
            processed_data_id = f"{plant_id}_{date_captured}"
            
            processed_data = ProcessedData(
                id=processed_data_id,
                plant_id=plant_id,
                date_captured=date_captured,
                image_key=image_key,
                vegetation_features=vegetation_features,
                morphology_features=morphology_features,
                texture_features=texture_features
            )
            
            db.merge(processed_data)
            db.commit()
            
            logger.info(f"Created processed data entry: {processed_data_id}")
            return processed_data
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error for processed data {processed_data_id}: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating processed data entry: {e}")
            raise
    
    @staticmethod
    def get_processed_data_by_plant_and_date(
        db: Session, 
        plant_id: str, 
        date_captured: date
    ) -> Optional[ProcessedData]:
        """Get processed data for a specific plant and date."""
        return db.query(ProcessedData).filter(
            ProcessedData.plant_id == plant_id,
            ProcessedData.date_captured == date_captured
        ).first()
    
    @staticmethod
    def get_processed_data_by_plant(db: Session, plant_id: str) -> List[ProcessedData]:
        """Get all processed data for a specific plant."""
        return db.query(ProcessedData).filter(ProcessedData.plant_id == plant_id).all()

class VegetationIndexService:
    """Service class for vegetation index timeline operations."""
    
    @staticmethod
    def create_vegetation_index_entry(
        db: Session,
        plant_id: str,
        date_captured: date,
        index_type: str,
        mean: float,
        median: float,
        std: float,
        q25: float,
        q75: float,
        min_val: float,
        max_val: float,
        index_image_key: str
    ) -> VegetationIndexTimeline:
        """
        Create a new vegetation index timeline entry.
        """
        try:
            entry = VegetationIndexTimeline(
                plant_id=plant_id,
                date_captured=date_captured,
                index_type=index_type,
                mean=mean,
                median=median,
                std=std,
                q25=q25,
                q75=q75,
                min=min_val,
                max=max_val,
                index_image_key=index_image_key
            )
            
            db.merge(entry)
            db.commit()
            
            logger.info(f"Created vegetation index entry: {plant_id}_{date_captured}_{index_type}")
            return entry
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error for vegetation index entry: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating vegetation index entry: {e}")
            raise

class TextureService:
    """Service class for texture timeline operations."""
    
    @staticmethod
    def create_texture_entry(
        db: Session,
        plant_id: str,
        date_captured: date,
        band_name: str,
        texture_type: str,
        mean: float,
        median: float,
        std: float,
        q25: float,
        q75: float,
        min_val: float,
        max_val: float,
        texture_image_key: str
    ) -> TextureTimeline:
        """
        Create a new texture timeline entry.
        """
        try:
            entry = TextureTimeline(
                plant_id=plant_id,
                date_captured=date_captured,
                band_name=band_name,
                texture_type=texture_type,
                mean=mean,
                median=median,
                std=std,
                q25=q25,
                q75=q75,
                min=min_val,
                max=max_val,
                texture_image_key=texture_image_key
            )
            
            db.merge(entry)
            db.commit()
            
            logger.info(f"Created texture entry: {plant_id}_{date_captured}_{band_name}_{texture_type}")
            return entry
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error for texture entry: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating texture entry: {e}")
            raise

class MorphologyService:
    """Service class for morphology timeline operations."""
    
    @staticmethod
    def create_morphology_entry(
        db: Session,
        plant_id: str,
        date_captured: date,
        size_area: float,
        size_convex_hull_area: float,
        size_solidity: float,
        size_perimeter: float,
        size_width: float,
        size_height: float,
        size_longest_path: float,
        size_center_of_mass: Dict[str, float],
        size_convex_hull_vertices: List[Dict[str, float]],
        size_ellipse_center: Dict[str, float],
        size_ellipse_major_axis: float,
        size_ellipse_minor_axis: float,
        size_ellipse_angle: float,
        size_ellipse_eccentricity: float,
        size_num_leaves: int,
        size_num_branches: int,
        morph_branch_pts: List[Dict[str, float]],
        morph_tips: List[Dict[str, float]],
        morph_segment_path_length: List[float],
        morph_segment_eu_length: List[float],
        morph_segment_curvature: List[float],
        morph_segment_angle: List[float],
        morph_segment_tangent_angle: List[float],
        morph_segment_insertion_angle: List[float],
        morphology_image_key: str
    ) -> MorphologyTimeline:
        """
        Create a new morphology timeline entry.
        
        Args:
            db: Database session
            plant_id: Plant identifier
            date_captured: Date when the image was captured
            size_area: Plant area
            size_convex_hull_area: Convex hull area
            size_solidity: Solidity measure
            size_perimeter: Plant perimeter
            size_width: Plant width
            size_height: Plant height
            size_longest_path: Longest path length
            size_center_of_mass: Center of mass coordinates {"x": float, "y": float}
            size_convex_hull_vertices: Convex hull vertices [{"x": float, "y": float}, ...]
            size_ellipse_center: Ellipse center coordinates {"x": float, "y": float}
            size_ellipse_major_axis: Ellipse major axis
            size_ellipse_minor_axis: Ellipse minor axis
            size_ellipse_angle: Ellipse angle
            size_ellipse_eccentricity: Ellipse eccentricity
            size_num_leaves: Number of leaves
            size_num_branches: Number of branches
            morph_branch_pts: Branch points [{"x": float, "y": float}, ...]
            morph_tips: Tip points [{"x": float, "y": float}, ...]
            morph_segment_path_length: Segment path lengths [float, ...]
            morph_segment_eu_length: Segment Euclidean lengths [float, ...]
            morph_segment_curvature: Segment curvatures [float, ...]
            morph_segment_angle: Segment angles [float, ...]
            morph_segment_tangent_angle: Segment tangent angles [float, ...]
            morph_segment_insertion_angle: Segment insertion angles [float, ...]
            morphology_image_key: S3 key for morphology image
            
        Returns:
            MorphologyTimeline object
        """
        try:
            entry = MorphologyTimeline(
                plant_id=plant_id,
                date_captured=date_captured,
                size_area=size_area,
                size_convex_hull_area=size_convex_hull_area,
                size_solidity=size_solidity,
                size_perimeter=size_perimeter,
                size_width=size_width,
                size_height=size_height,
                size_longest_path=size_longest_path,
                size_center_of_mass=size_center_of_mass,
                size_convex_hull_vertices=size_convex_hull_vertices,
                size_ellipse_center=size_ellipse_center,
                size_ellipse_major_axis=size_ellipse_major_axis,
                size_ellipse_minor_axis=size_ellipse_minor_axis,
                size_ellipse_angle=size_ellipse_angle,
                size_ellipse_eccentricity=size_ellipse_eccentricity,
                size_num_leaves=size_num_leaves,
                size_num_branches=size_num_branches,
                morph_branch_pts=morph_branch_pts,
                morph_tips=morph_tips,
                morph_segment_path_length=morph_segment_path_length,
                morph_segment_eu_length=morph_segment_eu_length,
                morph_segment_curvature=morph_segment_curvature,
                morph_segment_angle=morph_segment_angle,
                morph_segment_tangent_angle=morph_segment_tangent_angle,
                morph_segment_insertion_angle=morph_segment_insertion_angle,
                morphology_image_key=morphology_image_key
            )
            
            db.merge(entry)
            db.commit()
            
            logger.info(f"Created morphology entry: {plant_id}_{date_captured}")
            return entry
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error for morphology entry: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating morphology entry: {e}")
            raise
    
    @staticmethod
    def get_morphology_by_plant_and_date(
        db: Session, 
        plant_id: str, 
        date_captured: date
    ) -> Optional[MorphologyTimeline]:
        """Get morphology data for a specific plant and date."""
        return db.query(MorphologyTimeline).filter(
            MorphologyTimeline.plant_id == plant_id,
            MorphologyTimeline.date_captured == date_captured
        ).first()
    
    @staticmethod
    def get_morphology_by_plant(db: Session, plant_id: str) -> List[MorphologyTimeline]:
        """Get all morphology data for a specific plant."""
        return db.query(MorphologyTimeline).filter(
            MorphologyTimeline.plant_id == plant_id
        ).order_by(MorphologyTimeline.date_captured).all()
    
    @staticmethod
    def get_morphology_timeline(
        db: Session, 
        plant_id: str, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> List[MorphologyTimeline]:
        """
        Get morphology timeline for a plant within a date range.
        
        Args:
            db: Database session
            plant_id: Plant identifier
            start_date: Start date for timeline (inclusive)
            end_date: End date for timeline (inclusive)
            
        Returns:
            List of MorphologyTimeline objects ordered by date
        """
        query = db.query(MorphologyTimeline).filter(MorphologyTimeline.plant_id == plant_id)
        
        if start_date:
            query = query.filter(MorphologyTimeline.date_captured >= start_date)
        
        if end_date:
            query = query.filter(MorphologyTimeline.date_captured <= end_date)
        
        return query.order_by(MorphologyTimeline.date_captured).all()
    
    @staticmethod
    def get_morphology_statistics(db: Session, plant_id: str) -> Dict[str, Any]:
        """
        Get morphology statistics for a plant.
        
        Args:
            db: Database session
            plant_id: Plant identifier
            
        Returns:
            Dictionary containing morphology statistics
        """
        entries = db.query(MorphologyTimeline).filter(
            MorphologyTimeline.plant_id == plant_id
        ).order_by(MorphologyTimeline.date_captured).all()
        
        if not entries:
            return {}
        
        # Calculate statistics for numeric fields
        stats = {
            "total_entries": len(entries),
            "date_range": {
                "start": entries[0].date_captured,
                "end": entries[-1].date_captured
            },
            "size_area": {
                "min": min(e.size_area for e in entries),
                "max": max(e.size_area for e in entries),
                "avg": sum(e.size_area for e in entries) / len(entries)
            },
            "size_perimeter": {
                "min": min(e.size_perimeter for e in entries),
                "max": max(e.size_perimeter for e in entries),
                "avg": sum(e.size_perimeter for e in entries) / len(entries)
            },
            "size_width": {
                "min": min(e.size_width for e in entries),
                "max": max(e.size_width for e in entries),
                "avg": sum(e.size_width for e in entries) / len(entries)
            },
            "size_height": {
                "min": min(e.size_height for e in entries),
                "max": max(e.size_height for e in entries),
                "avg": sum(e.size_height for e in entries) / len(entries)
            },
            "size_num_leaves": {
                "min": min(e.size_num_leaves for e in entries),
                "max": max(e.size_num_leaves for e in entries),
                "avg": sum(e.size_num_leaves for e in entries) / len(entries)
            },
            "size_num_branches": {
                "min": min(e.size_num_branches for e in entries),
                "max": max(e.size_num_branches for e in entries),
                "avg": sum(e.size_num_branches for e in entries) / len(entries)
            }
        }
        
        return stats 