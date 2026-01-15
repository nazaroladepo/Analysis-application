# models.py
from typing import Optional, Any
from datetime import datetime, date # Import datetime for DateTime column type

from sqlalchemy import String, Date, DateTime, UniqueConstraint, ForeignKey, Float, JSON, Integer
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy.sql import func # For default values like current date/time

# Valid vegetation index strings
VEGETATION_INDICES = [
    "ARI", "ARI2", "AVI", "CCCI", "CIgreen", "CIRE", "CVI", "DSWI4", "DVI", 
    "EVI2", "ExR", "GEMI", "GNDVI", "GOSAVI", "GRNDVI", "GRVI", "GSAVI", 
    "IPVI", "LCI", "MCARI", "MCARI1", "MCARI2", "MGRVI", "MSAVI", "MSR", 
    "MTVI1", "MTVI2", "NDRE", "NDVI", "NDWI", "NGRDI", "NLI", "OSAVI", 
    "PVI", "RDVI", "RI", "RRI1", "SIPI2", "SR", "TCARI", "TCARIOSAVI", 
    "TNDVI", "TSAVI", "WDVI"
]

TEXTURE_FEATURES = ["color","green","nir","pca","red_edge","red"]


Base = declarative_base()
metadata = Base.metadata

class Plant(Base):
    __tablename__ = "plants"
    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True) # Ex: Sorghum_plant1
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    species: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    # add column for dates captured
    dates_captured: Mapped[list[date]] = mapped_column(JSON, nullable=True)
    # Add other metadata as needed (location, planting date, etc.)
    vegetation_indices = relationship("VegetationIndexTimeline", back_populates="plant")
    texture_features = relationship("TextureTimeline", back_populates="plant")
    morphology_features = relationship("MorphologyTimeline", back_populates="plant")
    processed_data = relationship("ProcessedData", back_populates="plant")

    def __repr__(self) -> str:
        return f"<Plant(id={self.id}, name='{self.name}', species='{self.species}')>"


class ProcessedData(Base):
    __tablename__ = "processed_data"

   # Define table-level arguments like unique constraints
    # The UniqueConstraint now applies to the 'id' (which is your plant identifier)
    # and the 'date_processed' to ensure uniqueness per plant per day.
    __table_args__ = (
        UniqueConstraint('id', 'date_captured', name='_unique_plant_image_per_day'),
    )

    # Primary Key - A String like "Sorghum_plant1_2024-12-04", "Sorghum_plant2_2024-06-01", etc.
    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)

    # Column for a user-customizable name.
    # It's nullable=True because the user might not provide one.
    name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Column for the plant identifier.
    # It's nullable=False because the plant identifier is required.
    plant_id: Mapped[str] = mapped_column(String(50), ForeignKey("plants.id"), nullable=False, index=True)

    # Column for the image key.
    # It's nullable=False because the image key is required.
    image_key: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Using DateTime for more precision, with a default to the current UTC time
    date_processed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now()) 

    # Column for the date the image was captured.
    # It's nullable=False because the capture date is required.
    date_captured: Mapped[date] = mapped_column(Date, nullable=False)

    
    vegetation_features: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    morphology_features: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    texture_features: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    plant = relationship("Plant", back_populates="processed_data")

    def __repr__(self) -> str:
        return f"<ProcessedImage(id={self.id}, plant_id='{self.plant_id}', date_processed={self.date_processed})>"


class VegetationIndexTimeline(Base):
    __tablename__ = "vegetation_index_timeline"
    #Composite Primary Key: plant_id, date_captured, index_type
    plant_id: Mapped[str] = mapped_column(String(50), ForeignKey("plants.id"), primary_key=True)
    date_captured: Mapped[date] = mapped_column(Date, primary_key=True)
    index_type: Mapped[str] = mapped_column(String(20), primary_key=True)  
    mean: Mapped[float] = mapped_column(Float, nullable=False)
    median: Mapped[float] = mapped_column(Float, nullable=False)
    std: Mapped[float] = mapped_column(Float, nullable=False)
    q25: Mapped[float] = mapped_column(Float, nullable=False)
    q75: Mapped[float] = mapped_column(Float, nullable=False)
    min: Mapped[float] = mapped_column(Float, nullable=False)
    max: Mapped[float] = mapped_column(Float, nullable=False)
    index_image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    plant = relationship("Plant", back_populates="vegetation_indices")

    def __repr__(self) -> str:
        return f"<VegetationIndexTimeline(plant_id='{self.plant_id}', date_captured={self.date_captured}, index_type='{self.index_type}')>"

class TextureTimeline(Base):
    __tablename__ = "texture_timeline"
    plant_id: Mapped[str] = mapped_column(String(50), ForeignKey("plants.id"), primary_key=True)
    date_captured: Mapped[date] = mapped_column(Date, primary_key=True)
    band_name: Mapped[str] = mapped_column(String(20), primary_key=True)
    texture_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    mean: Mapped[float] = mapped_column(Float, nullable=False)
    median: Mapped[float] = mapped_column(Float, nullable=False)
    std: Mapped[float] = mapped_column(Float, nullable=False)
    q25: Mapped[float] = mapped_column(Float, nullable=False)
    q75: Mapped[float] = mapped_column(Float, nullable=False)
    min: Mapped[float] = mapped_column(Float, nullable=False)
    max: Mapped[float] = mapped_column(Float, nullable=False)
    texture_image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    plant = relationship("Plant", back_populates="texture_features")

    def __repr__(self) -> str:
        return f"<TextureTimeline(plant_id='{self.plant_id}', date_captured={self.date_captured}, band_name='{self.band_name}', texture_type='{self.texture_type}')>"

class MorphologyTimeline(Base):
    __tablename__ = "morphology_timeline"
    plant_id: Mapped[str] = mapped_column(String(50), ForeignKey("plants.id"), primary_key=True)
    date_captured: Mapped[date] = mapped_column(Date, primary_key=True)
    
    # Size-related features
    size_area: Mapped[float] = mapped_column(Float, nullable=False)
    size_convex_hull_area: Mapped[float] = mapped_column(Float, nullable=False)
    size_solidity: Mapped[float] = mapped_column(Float, nullable=False)
    size_perimeter: Mapped[float] = mapped_column(Float, nullable=False)
    size_width: Mapped[float] = mapped_column(Float, nullable=False)
    size_height: Mapped[float] = mapped_column(Float, nullable=False)
    size_longest_path: Mapped[float] = mapped_column(Float, nullable=False)
    size_center_of_mass: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)  # Store as {"x": float, "y": float}
    size_convex_hull_vertices: Mapped[list[dict[str, float]]] = mapped_column(JSON, nullable=False)  # Store as [{"x": float, "y": float}, ...]
    size_ellipse_center: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)  # Store as {"x": float, "y": float}
    size_ellipse_major_axis: Mapped[float] = mapped_column(Float, nullable=False)
    size_ellipse_minor_axis: Mapped[float] = mapped_column(Float, nullable=False)
    size_ellipse_angle: Mapped[float] = mapped_column(Float, nullable=False)
    size_ellipse_eccentricity: Mapped[float] = mapped_column(Float, nullable=False)
    size_num_leaves: Mapped[int] = mapped_column(Integer, nullable=False)
    size_num_branches: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Morphology-related features
    morph_branch_pts: Mapped[list[dict[str, float]]] = mapped_column(JSON, nullable=False)  # Store as [{"x": float, "y": float}, ...]
    morph_tips: Mapped[list[dict[str, float]]] = mapped_column(JSON, nullable=False)  # Store as [{"x": float, "y": float}, ...]
    morph_segment_path_length: Mapped[list[float]] = mapped_column(JSON, nullable=False)  # Store as [float, float, ...]
    morph_segment_eu_length: Mapped[list[float]] = mapped_column(JSON, nullable=False)  # Store as [float, float, ...]
    morph_segment_curvature: Mapped[list[float]] = mapped_column(JSON, nullable=False)  # Store as [float, float, ...]
    morph_segment_angle: Mapped[list[float]] = mapped_column(JSON, nullable=False)  # Store as [float, float, ...]
    morph_segment_tangent_angle: Mapped[list[float]] = mapped_column(JSON, nullable=False)  # Store as [float, float, ...]
    morph_segment_insertion_angle: Mapped[list[float]] = mapped_column(JSON, nullable=False)  # Store as [float, float, ...]
    
    # Image key for reference
    morphology_image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    
    plant = relationship("Plant", back_populates="morphology_features")

    def __repr__(self) -> str:
        return f"<MorphologyTimeline(plant_id='{self.plant_id}', date_captured={self.date_captured})>"


# Example: Get NDVI time series for plant 'plant1'
# results = (
#     session.query(VegetationIndexTimeline)
#     .filter_by(plant_id="plant1", index_type="NDVI")
#     .order_by(VegetationIndexTimeline.date_captured)
#     .all()
# )

#Convert the results into lists for plotting (e.g., with matplotlib, Plotly, or for sending to a frontend)
# dates = [r.date_captured for r in results]
# means = [r.mean for r in results]
# medians = [r.median for r in results]
# stds = [r.std for r in results]
# q25s = [r.q25 for r in results]
# q75s = [r.q75 for r in results]
# mins = [r.min for r in results]
# maxs = [r.max for r in results]

