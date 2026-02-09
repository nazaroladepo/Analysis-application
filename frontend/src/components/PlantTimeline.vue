<template>
  <div class="plant-timeline">
    <div class="timeline-header">
      <div class="header-content">
        <div>
          <h2>Plant Timeline Analysis</h2>
          <p v-if="selectedPlants.length === 0">{{ plantIdDisplayText }} - {{ species }}</p>
          <p v-else>{{ selectedPlantsDisplayText }} - {{ species }}</p>
        </div>
      </div>
    </div>

    <div class="timeline-content">
      <!-- Chart and Configuration Container -->
      <div class="chart-and-config">
        <!-- Chart Container -->
        <div class="chart-container">
          <canvas ref="timelineChart" width="800" height="400"></canvas>

          <div v-if="isLoadingTimeline" class="loading-overlay">
            <div class="loading-spinner"></div>
            <p>Loading timeline data...</p>
            <p v-if="selectedPlantIds.length > 0" class="loading-detail">
              Loading data for {{ selectedPlantIds.length }} plant{{ selectedPlantIds.length > 1 ? 's' : '' }}...
            </p>
          </div>
          <div v-else-if="selectedPlantIds.length === 0" class="no-data-overlay">
            <p>Select at least one plant to view timeline data</p>
          </div>
          <div v-else-if="!hasDataLoaded && !hasLoadedOnce" class="no-data-overlay">
            <p>Select a feature type and specific feature to load data</p>
          </div>
          <div v-else-if="hasDataLoaded && currentData.length === 0" class="no-data-overlay">
            <p>No data available for the selected plants and feature</p>
          </div>
        </div>
        
        <!-- Configuration Panel -->
        <div class="config-panel" :class="{ 'disabled': isLoadingTimeline }">
          <h3>Display Configuration</h3>
          
          <!-- Plant Selection (Multi-select) -->
          <div class="config-group">
            <label>Select Plants (Max 3):</label>
            <div class="plant-selector-container">
              <select 
                v-model="tempSelectedPlant" 
                @change="addPlant"
                :disabled="isLoadingPlants || selectedPlantIds.length >= 3"
                class="plant-select-dropdown"
              >
                <option value="">-- Select a plant --</option>
                <option 
                  v-for="plant in availablePlantOptions" 
                  :key="plant.value" 
                  :value="plant.value"
                  :disabled="isPlantSelected(plant.value)"
                >
                  {{ plant.label }}
                </option>
              </select>
              <small v-if="selectedPlantIds.length >= 3" class="max-plants-warning">
                Maximum 3 plants selected
              </small>
            </div>
            
            <!-- Selected Plants List -->
            <div v-if="selectedPlants.length > 0" class="selected-plants-list">
              <div class="selected-plants-header">
                <span>Selected Plants ({{ selectedPlants.length }}/3):</span>
              </div>
              <div class="selected-plant-item" v-for="(plant, index) in selectedPlants" :key="getPlantId(plant)">
                <span class="plant-name">{{ formatPlantName(getPlantId(plant)) }}</span>
                <button 
                  @click="removePlant(index)" 
                  class="remove-plant-btn"
                  :disabled="isLoadingTimeline"
                  title="Remove plant"
                >
                  ×
                </button>
              </div>
            </div>
          </div>
          
          <!-- Feature Selection -->
          <div class="config-group">
            <label>Feature Type:</label>
            <select v-model="selectedFeatureType" @change="onFeatureTypeChange">
              <option value="">Select Feature Type</option>
              <option value="vegetation">Vegetation Index</option>
              <option value="texture">Texture Feature</option>
              <option value="morphology">Morphology Feature</option>
            </select>
          </div>
          
          <!-- Vegetation Index Selection -->
          <div v-if="selectedFeatureType === 'vegetation'" class="config-group">
            <label>Vegetation Index:</label>
            <select v-model="selectedFeature" @change="onFeatureChange">
              <option value="">Select Vegetation Index</option>
              <option v-for="index in availableVegetationIndices" :key="index.value" :value="index.value">
                {{ index.label }}
              </option>
            </select>
            <div v-if="selectedFeature" class="feature-description">
              <small>
                <span v-if="selectedFeature === 'NDVI'">Normalized Difference Vegetation Index - Measures vegetation health and density</span>
                <span v-else-if="selectedFeature === 'EVI2'">Enhanced Vegetation Index 2 - Improved vegetation index with reduced atmospheric effects</span>
                <span v-else-if="selectedFeature === 'GNDVI'">Green Normalized Difference Vegetation Index - Uses green band for vegetation assessment</span>
                <span v-else-if="selectedFeature === 'NDRE'">Normalized Difference Red Edge - Sensitive to chlorophyll content</span>
                <span v-else-if="selectedFeature === 'OSAVI'">Optimized Soil Adjusted Vegetation Index - Accounts for soil background</span>
                <span v-else-if="selectedFeature === 'MSAVI'">Modified Soil Adjusted Vegetation Index - Improved soil adjustment</span>
                <span v-else-if="selectedFeature === 'GEMI'">Global Environmental Monitoring Index - Less sensitive to atmospheric effects</span>
                <span v-else-if="selectedFeature === 'ARVI'">Atmospherically Resistant Vegetation Index - Reduces atmospheric effects</span>
                <span v-else-if="selectedFeature === 'SAVI'">Soil Adjusted Vegetation Index - Accounts for soil brightness</span>
                <span v-else-if="selectedFeature === 'TVI'">Transformed Vegetation Index - Square root transformation of NDVI</span>
                <span v-else>Vegetation index for plant health and growth monitoring</span>
              </small>
            </div>
          </div>
          
          <!-- Texture Band Selection -->
          <div v-if="selectedFeatureType === 'texture'" class="config-group">
            <label>Texture Band:</label>
            <select v-model="selectedTextureBand" @change="onTextureBandChange">
              <option value="">Select Band</option>
              <option v-for="band in availableTextureBands" :key="band.value" :value="band.value">
                {{ band.label }}
              </option>
            </select>
          </div>
          
          <!-- Texture Type Selection -->
          <div v-if="selectedFeatureType === 'texture' && selectedTextureBand" class="config-group">
            <label>Texture Type:</label>
            <select v-model="selectedTextureType" @change="onFeatureChange">
              <option value="">Select Type</option>
              <option v-for="type in availableTextureTypes" :key="type.value" :value="type.value">
                {{ type.label }}
              </option>
            </select>
            <div v-if="selectedTextureType" class="texture-description">
              <small>
                <span v-if="selectedTextureType === 'lbp'">Local Binary Pattern - Texture descriptor for pattern analysis</span>
                <span v-else-if="selectedTextureType === 'hog'">Histogram of Oriented Gradients - Edge and orientation descriptor</span>
                <span v-else-if="selectedTextureType === 'lac1'">Lacunarity (Base Window) - Texture heterogeneity at base scale</span>
                <span v-else-if="selectedTextureType === 'lac2'">Lacunarity (Multi-scale) - Average heterogeneity across scales</span>
                <span v-else-if="selectedTextureType === 'lac3'">DBC Lacunarity - Deep learning-based lacunarity</span>
                <span v-else-if="selectedTextureType === 'ehd_map'">Edge Histogram Descriptor - Distribution of edge directions</span>
              </small>
            </div>
          </div>
          
          <!-- Morphology Feature Selection -->
          <div v-if="selectedFeatureType === 'morphology'" class="config-group">
            <label>Morphology Feature:</label>
            <select v-model="selectedFeature" @change="onFeatureChange">
              <option value="">Select Morphology Feature</option>
              <option v-for="feature in availableMorphologyFeatures" :key="feature.value" :value="feature.value">
                {{ feature.label }}
              </option>
            </select>
            <div v-if="selectedFeature" class="feature-description">
              <small>
                <span v-if="selectedFeature === 'size_area'">Plant area in pixels - Overall size measurement</span>
                <span v-else-if="selectedFeature === 'size_perimeter'">Plant perimeter - Boundary length measurement</span>
                <span v-else-if="selectedFeature === 'size_width'">Plant width - Horizontal extent measurement</span>
                <span v-else-if="selectedFeature === 'size_height'">Plant height - Vertical extent measurement</span>
                <span v-else-if="selectedFeature === 'size_num_leaves'">Number of leaves - Leaf count</span>
                <span v-else-if="selectedFeature === 'size_num_branches'">Number of branches - Branch count</span>
                <span v-else-if="selectedFeature === 'size_solidity'">Solidity - Ratio of plant area to convex hull area</span>
                <span v-else-if="selectedFeature === 'size_ellipse_eccentricity'">Ellipse eccentricity - Shape elongation measure</span>
                <span v-else>Morphological feature for plant structure analysis</span>
              </small>
            </div>
          </div>
          
          <!-- Date Range Selection -->
          <div class="config-group">
            <label>Date Range:</label>
            <div class="date-range">
              <select v-model="startDate" @change="updateChart">
                <option value="">Start Date</option>
                <option v-for="date in availableDates" :key="date" :value="date">
                  {{ formatDate(date) }}
                </option>
              </select>
              <span>to</span>
              <select v-model="endDate" @change="updateChart">
                <option value="">End Date</option>
                <option v-for="date in availableDates" :key="date" :value="date">
                  {{ formatDate(date) }}
                </option>
              </select>
            </div>
          </div>
          
          <!-- Statistics Display Options -->
          <div class="config-group">
            <label>Statistics Display:</label>
            <div class="checkbox-group-two-columns">
              <div class="checkbox-column">
                <label>
                  <input type="checkbox" v-model="showMean" @change="updateChart" />
                  Mean
                </label>
                <label>
                  <input type="checkbox" v-model="showMedian" @change="updateChart" />
                  Median
                </label>
                <label>
                  <input type="checkbox" v-model="showStd" @change="updateChart" />
                  St. Dev.
                </label>
                <label>
                  <input type="checkbox" v-model="showQ25" @change="updateChart" />
                  Q25
                </label>
              </div>
              <div class="checkbox-column">
                <label>
                  <input type="checkbox" v-model="showQ75" @change="updateChart" />
                  Q75
                </label>
                <label>
                  <input type="checkbox" v-model="showMin" @change="updateChart" />
                  Min
                </label>
                <label>
                  <input type="checkbox" v-model="showMax" @change="updateChart" />
                  Max
                </label>
              </div>
            </div>
          </div>
          
          <!-- Image Display Options -->
          <div class="config-group">
            <label>Image Display:</label>
            <div class="checkbox-group-two-columns">
              <div class="checkbox-column">
                <label>
                  <input type="checkbox" v-model="showImages" @change="updateChart" />
                  Show Images on Chart
                </label>
              </div>
            </div>
          </div>
          
          <div v-if="showImages" class="config-group">
            <label>Number of Images:</label>
            <select v-model="numImages" @change="updateChart">
              <option value="3">3 Images</option>
              <option value="5">5 Images</option>
              <option value="7">7 Images</option>
              <option value="10">10 Images</option>
              <option value="15">15 Images</option>
            </select>
          </div>
          
          <div v-if="showImages" class="config-group">
            <label>Image Size:</label>
            <select v-model="imageSize" @change="updateChart">
              <option value="small">Small (30px)</option>
              <option value="medium">Medium (50px)</option>
              <option value="large">Large (70px)</option>
              <option value="xlarge">Extra Large (100px)</option>
            </select>
          </div>
          
          <!-- Statistics Summary -->
          <div v-if="currentData.length > 0" class="stats-summary">
            <h4>Statistics Summary</h4>
            <div class="stat-item">
              <span>Plants:</span>
              <span>{{ selectedPlantIds.length || 1 }}</span>
            </div>
            <div class="stat-item">
              <span>Data Points:</span>
              <span>{{ currentData.length }}</span>
            </div>
            <div class="stat-item" v-if="availableDates.length > 0">
              <span>Date Range:</span>
              <span>{{ formatDate(availableDates[0]) }} - {{ formatDate(availableDates[availableDates.length - 1]) }}</span>
            </div>
            <div class="stat-item" v-if="showMean">
              <span>Mean Range:</span>
              <span>{{ formatValue(minMean) }} - {{ formatValue(maxMean) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Chart from 'chart.js/auto';
import { getVegetationTimeline, getTextureTimeline, getMorphologyTimeline, getPlantDates, getAvailablePlants } from '@/api.js';

export default {
  name: 'PlantTimeline',
  props: {
    species: {
      type: String,
      required: true
    },
    plantId: {
      type: [String, Object],
      required: true
    },
    analysisDate: {
      type: [String, Object],
      default: null
    }
  },
  
  data() {
    return {
      chart: null,
      loading: false,
      // Multi-plant data structure: { plantId: { vegetation: [], texture: [], morphology: [] } }
      multiPlantData: {},
      plantDates: [],
      isLoadingTimeline: false,
      isLoadingPlants: false,
      hasLoadedOnce: false,
      selectedFeatureType: 'vegetation',
      selectedFeature: '',
      selectedTextureBand: '',
      selectedTextureType: '',
      showMean: true,
      showMedian: false,
      showStd: false,
      showQ25: false,
      showQ75: false,
      showMin: false,
      showMax: false,
      showImages: false,
      numImages: 5,
      imageSize: 'medium',
      startDate: '',
      endDate: '',
      availableTextureTypes: [],
      currentData: [],
      selectedPlants: [],
      plantOptions: [],
      tempSelectedPlant: '' // Temporary selection for dropdown
    };
  },
  
  computed: {
    // Helper computed property to get the actual plantId value
    actualPlantId() {
      if (typeof this.plantId === 'string') {
        return this.plantId;
      } else if (this.plantId && typeof this.plantId === 'object' && this.plantId.value) {
        return this.plantId.value;
      }
      return this.plantId;
    },

    // Get plant IDs from selected plants
    selectedPlantIds() {
      if (!Array.isArray(this.selectedPlants) || this.selectedPlants.length === 0) {
        return [];
      }
      return this.selectedPlants.map(p => this.getPlantId(p)).filter(Boolean);
    },

    // Available plant options (excluding already selected)
    availablePlantOptions() {
      return this.plantOptions.filter(opt => !this.isPlantSelected(opt.value));
    },

    plantIdDisplayText() {
      if (!this.plantId) return "Select a Plant";
      if (typeof this.plantId === 'string') {
        return this.formatPlantName(this.plantId);
      }
      if (this.plantId && typeof this.plantId === 'object') {
        if (this.plantId.label) return this.plantId.label;
        if (this.plantId.value) return this.formatPlantName(this.plantId.value);
      }
      return String(this.plantId);
    },

    // Color palette for statistics (consistent across all plants)
    statisticsColors() {
      return {
        mean: '#4A90E2',      // Blue
        median: '#E24A4A',    // Red
        std: '#4AE2A0',       // Teal
        q25: '#E2A04A',       // Orange
        q75: '#A04AE2',       // Purple
        min: '#E2E24A',       // Yellow
        max: '#4AE24A'        // Green
      };
    },

    // Plant colors (distinct for each plant)
    plantColors() {
      return [
        '#FF6B6B',  // Coral red
        '#4ECDC4',  // Turquoise
        '#95E1D3'   // Mint green
      ];
    },

    // Marker shapes for plants
    plantMarkers() {
      return ['circle', 'rect', 'triangle'];
    },

    availableVegetationIndices() {
      return [
        { value: 'NDVI', label: 'NDVI (Normalized Difference Vegetation Index)' },
        { value: 'EVI2', label: 'EVI2 (Enhanced Vegetation Index 2)' },
        { value: 'GNDVI', label: 'GNDVI (Green Normalized Difference Vegetation Index)' },
        { value: 'NDRE', label: 'NDRE (Normalized Difference Red Edge)' },
        { value: 'OSAVI', label: 'OSAVI (Optimized Soil Adjusted Vegetation Index)' },
        { value: 'MSAVI', label: 'MSAVI (Modified Soil Adjusted Vegetation Index)' },
        { value: 'GEMI', label: 'GEMI (Global Environmental Monitoring Index)' },
        { value: 'ARVI', label: 'ARVI (Atmospherically Resistant Vegetation Index)' },
        { value: 'SAVI', label: 'SAVI (Soil Adjusted Vegetation Index)' },
        { value: 'TVI', label: 'TVI (Transformed Vegetation Index)' },
        { value: 'ARI', label: 'ARI (Anthocyanin Reflectance Index)' },
        { value: 'ARI2', label: 'ARI2 (Anthocyanin Reflectance Index 2)' },
        { value: 'AVI', label: 'AVI (Advanced Vegetation Index)' },
        { value: 'CCCI', label: 'CCCI (Canopy Chlorophyll Content Index)' },
        { value: 'CIgreen', label: 'CIgreen (Chlorophyll Index Green)' },
        { value: 'CIRE', label: 'CIRE (Chlorophyll Index Red Edge)' },
        { value: 'CVI', label: 'CVI (Chlorophyll Vegetation Index)' },
        { value: 'DSWI4', label: 'DSWI4 (Drought Stress Water Index 4)' },
        { value: 'DVI', label: 'DVI (Difference Vegetation Index)' },
        { value: 'ExR', label: 'ExR (Excess Red)' },
        { value: 'GRNDVI', label: 'GRNDVI (Green Red Normalized Difference Vegetation Index)' },
        { value: 'GRVI', label: 'GRVI (Green Red Vegetation Index)' },
        { value: 'GOSAVI', label: 'GOSAVI (Green Optimized Soil Adjusted Vegetation Index)' },
        { value: 'GSAVI', label: 'GSAVI (Green Soil Adjusted Vegetation Index)' },
        { value: 'IPVI', label: 'IPVI (Infrared Percentage Vegetation Index)' },
        { value: 'LCI', label: 'LCI (Leaf Chlorophyll Index)' },
        { value: 'MCARI', label: 'MCARI (Modified Chlorophyll Absorption in Reflectance Index)' },
        { value: 'MCARI1', label: 'MCARI1 (Modified Chlorophyll Absorption in Reflectance Index 1)' },
        { value: 'MCARI2', label: 'MCARI2 (Modified Chlorophyll Absorption in Reflectance Index 2)' },
        { value: 'MGRVI', label: 'MGRVI (Modified Green Red Vegetation Index)' },
        { value: 'MSR', label: 'MSR (Modified Simple Ratio)' },
        { value: 'MTVI1', label: 'MTVI1 (Modified Triangular Vegetation Index 1)' },
        { value: 'MTVI2', label: 'MTVI2 (Modified Triangular Vegetation Index 2)' },
        { value: 'NDWI', label: 'NDWI (Normalized Difference Water Index)' },
        { value: 'NGRDI', label: 'NGRDI (Normalized Green Red Difference Index)' },
        { value: 'NLI', label: 'NLI (Nonlinear Vegetation Index)' },
        { value: 'PVI', label: 'PVI (Perpendicular Vegetation Index)' },
        { value: 'RDVI', label: 'RDVI (Renormalized Difference Vegetation Index)' },
        { value: 'RI', label: 'RI (Redness Index)' },
        { value: 'RRI1', label: 'RRI1 (Red Edge Ratio Index 1)' },
        { value: 'SIPI2', label: 'SIPI2 (Structure Insensitive Pigment Index 2)' },
        { value: 'SR', label: 'SR (Simple Ratio)' },
        { value: 'TCARI', label: 'TCARI (Transformed Chlorophyll Absorption in Reflectance Index)' },
        { value: 'TCARIOSAVI', label: 'TCARIOSAVI (TCARI/OSAVI)' },
        { value: 'TNDVI', label: 'TNDVI (Transformed Normalized Difference Vegetation Index)' },
        { value: 'TSAVI', label: 'TSAVI (Transformed Soil Adjusted Vegetation Index)' },
        { value: 'WDVI', label: 'WDVI (Weighted Difference Vegetation Index)' }
      ];
    },

    availableTextureBands() {
      return [
        { value: 'color', label: 'Color (RGB Composite)' },
        { value: 'green', label: 'Green Band' },
        { value: 'nir', label: 'NIR (Near-Infrared)' },
        { value: 'pca', label: 'PCA (Principal Component Analysis)' },
        { value: 'red_edge', label: 'Red Edge' },
        { value: 'red', label: 'Red Band' }
      ];
    },

    availableMorphologyFeatures() {
      return [
        { value: 'size_area', label: 'Plant Area' },
        { value: 'size_perimeter', label: 'Plant Perimeter' },
        { value: 'size_width', label: 'Plant Width' },
        { value: 'size_height', label: 'Plant Height' },
        { value: 'size_num_leaves', label: 'Number of Leaves' },
        { value: 'size_num_branches', label: 'Number of Branches' },
        { value: 'size_solidity', label: 'Solidity' },
        { value: 'size_convex_hull_area', label: 'Convex Hull Area' },
        { value: 'size_longest_path', label: 'Longest Path' },
        { value: 'size_ellipse_major_axis', label: 'Ellipse Major Axis' },
        { value: 'size_ellipse_minor_axis', label: 'Ellipse Minor Axis' },
        { value: 'size_ellipse_angle', label: 'Ellipse Angle' },
        { value: 'size_ellipse_eccentricity', label: 'Ellipse Eccentricity' }
      ];
    },

    
    selectedImages() {
      if (!this.showImages || !this.currentData.length) return [];
      
      const dataWithImages = this.currentData.filter(d => d.image_key);
      
      if (dataWithImages.length <= this.numImages) {
        return dataWithImages.map(d => ({
          date: d.date,
          url: d.image_key
        }));
      }
      
      // Select evenly spaced images
      const step = Math.floor(dataWithImages.length / this.numImages);
      const selectedData = [];
      for (let i = 0; i < this.numImages; i++) {
        const index = i * step;
        if (index < dataWithImages.length) {
          selectedData.push(dataWithImages[index]);
        }
      }
      
      return selectedData.map(d => ({
        date: d.date,
        url: d.image_key
      }));
    },
    
    minMean() {
      if (!this.currentData.length) return 0;
      return Math.min(...this.currentData.map(d => d.mean));
    },
    
    maxMean() {
      if (!this.currentData.length) return 0;
      return Math.max(...this.currentData.map(d => d.mean));
    },

    availableDates() {
      // Get dates from all plants' timeline data
      const allDates = new Set();
      
      Object.values(this.multiPlantData).forEach(plantData => {
        if (plantData.vegetation) {
          plantData.vegetation.forEach(v => allDates.add(v.date));
        }
        if (plantData.texture) {
          plantData.texture.forEach(t => allDates.add(t.date));
        }
        if (plantData.morphology) {
          plantData.morphology.forEach(m => allDates.add(m.date));
        }
      });
      
      const sortedDates = Array.from(allDates).sort();
      return sortedDates.length > 0 ? sortedDates : this.plantDates;
    },

    hasImages() {
      return this.currentData.some(d => d.image_key);
    },

    hasDataLoaded() {
      return Object.keys(this.multiPlantData).length > 0;
    }
  },
  
  watch: {
    // Temporarily disable data watchers to test if they're causing the issue
    // vegetationData: {
    //   handler(newData) {
    //     console.log('PlantTimeline: vegetationData changed:', newData);
    //     if (newData) {
    //       this.initializeDates();
    //       this.$nextTick(() => {
    //         if (this.chart) {
    //           this.updateChart();
    //         }
    //       });
    //     }
    //   },
    //   immediate: true
    // },
    
    // textureData: {
    //   handler(newData) {
    //     console.log('PlantTimeline: textureData changed:', newData);
    //     if (newData) {
    //       this.initializeDates();
    //       this.$nextTick(() => {
    //         if (this.chart) {
    //           this.updateChart();
    //         }
    //       });
    //     }
    //   },
    //   immediate: true
    // },
    
    // morphologyData: {
    //   handler(newData) {
    //     console.log('PlantTimeline: morphologyData changed:', newData);
    //     if (newData) {
    //       this.initializeDates();
    //       this.$nextTick(() => {
    //         if (this.chart) {
    //           this.updateChart();
    //         }
    //       });
    //     }
    //   },
    //   immediate: true
    // },
    
    selectedFeatureType: {
      handler(newType) {
        console.log('PlantTimeline: selectedFeatureType changed to:', newType);
        // Auto-load data when switching to morphology tab
        if (newType === 'morphology' && this.selectedFeature) {
          console.log('Auto-loading morphology data...');
          this.loadTimelineData().then(() => {
            this.$nextTick(() => {
              if (!this.chart) {
                this.initializeChart();
              }
              this.updateChart();
            });
          });
        }
      }
    }
  },
  
  async mounted() {
    // Load available plants for dropdown
    await this.loadAvailablePlants();
    
    // Initialize with default plant if provided
    if (this.actualPlantId) {
      // Find the option that matches the actual plant ID
      const matchingOption = this.plantOptions.find(opt => opt.value === this.actualPlantId);
      if (matchingOption) {
        this.selectedPlants = [matchingOption];
      } else if (this.actualPlantId) {
        // Fallback: create option from plantId
        this.selectedPlants = [{
          label: this.formatPlantName(this.actualPlantId),
          value: this.actualPlantId
        }];
      }
    }
    
    // Load plant dates first
    this.loadPlantDates();
    
    // Initialize chart after DOM is ready
    this.$nextTick(() => {
      this.initializeChart();
    });
  },
  
  // Use activated hook for when component becomes visible (useful for tab switching)
  activated() {
    // Only load plant dates if not already loaded
    if (this.plantDates.length === 0 && !this.isLoadingTimeline) {
      this.loadPlantDates();
    }
  },
  
  beforeUnmount() {
    if (this.chart) {
      this.chart.destroy();
    }
  },
  
  methods: {
    // Format plant name (e.g., "plant1" -> "Plant 1")
    formatPlantName(plantId) {
      if (!plantId) return '';
      const plantNumber = String(plantId).replace(/\D/g, '');
      return `Plant ${plantNumber}`;
    },

    // Load available plants for the dropdown
    async loadAvailablePlants() {
      try {
        this.isLoadingPlants = true;
        const data = await getAvailablePlants();
        const speciesPlants = data.plants_by_species[this.species] || [];
        
        // Convert to dropdown options format
        this.plantOptions = speciesPlants.map(plant => {
          const plantNumber = plant.id.replace(/\D/g, '');
          return {
            label: `Plant ${plantNumber}`,
            value: plant.id
          };
        }).sort((a, b) => {
          const aNum = parseInt(a.value.replace(/\D/g, '')) || 0;
          const bNum = parseInt(b.value.replace(/\D/g, '')) || 0;
          return aNum - bNum;
        });
      } catch (error) {
        console.error('Error loading available plants:', error);
        this.plantOptions = [];
      } finally {
        this.isLoadingPlants = false;
      }
    },

    // Get plant ID from plant object or string
    getPlantId(plant) {
      if (typeof plant === 'string') return plant;
      if (typeof plant === 'object' && plant.value) return plant.value;
      return String(plant);
    },

    // Check if a plant is already selected
    isPlantSelected(plantId) {
      return this.selectedPlantIds.includes(plantId);
    },

    // Add a plant to selection
    addPlant() {
      if (!this.tempSelectedPlant || this.selectedPlantIds.length >= 3) {
        this.tempSelectedPlant = '';
        return;
      }
      
      const plantId = this.tempSelectedPlant;
      
      // Check if already selected
      if (this.isPlantSelected(plantId)) {
        this.tempSelectedPlant = '';
        return;
      }
      
      // Find the plant option
      const plantOption = this.plantOptions.find(opt => opt.value === plantId);
      if (plantOption) {
        this.selectedPlants.push(plantOption);
        // Reset dropdown selection
        this.tempSelectedPlant = '';
        // Trigger change handler
        this.onPlantsChange();
      }
    },

    // Remove a plant from selection
    removePlant(index) {
      if (index >= 0 && index < this.selectedPlants.length) {
        this.selectedPlants.splice(index, 1);
        this.onPlantsChange();
      }
    },

    // Handle plant selection change
    onPlantsChange() {
      // Ensure selectedPlants is an array
      if (!Array.isArray(this.selectedPlants)) {
        this.selectedPlants = [];
      }
      
      // Limit to 3 plants
      if (this.selectedPlants.length > 3) {
        this.selectedPlants = this.selectedPlants.slice(0, 3);
      }
      
      // Clear existing data for removed plants
      const currentPlantIds = this.selectedPlantIds;
      Object.keys(this.multiPlantData).forEach(plantId => {
        if (!currentPlantIds.includes(plantId)) {
          delete this.multiPlantData[plantId];
        }
      });
      
      // If plants were removed, we still have data, just update chart
      if (this.selectedPlants.length > 0 && this.hasDataLoaded) {
        // Update chart immediately with existing data
        this.$nextTick(() => {
          if (this.chart) {
            this.updateChart();
          }
        });
        
        // Reload data if feature is selected (to get fresh data)
        if (this.selectedFeature || (this.selectedTextureBand && this.selectedTextureType)) {
          this.loadTimelineData().then(() => {
            if (this.chart) {
              this.updateChart();
            }
          });
        }
      } else if (this.selectedPlants.length > 0 && (this.selectedFeature || (this.selectedTextureBand && this.selectedTextureType))) {
        // New plants selected, need to load data
        this.hasLoadedOnce = false;
        this.$nextTick(() => {
          this.loadTimelineData().then(() => {
            if (this.chart) {
              this.updateChart();
            }
          });
        });
      } else if (this.chart) {
        // Clear chart if no plants selected
        this.updateChart();
      }
    },

    async loadPlantDates() {
      try {
        // Load dates for the first selected plant or default plant
        const plantIdToUse = this.selectedPlantIds[0] || this.actualPlantId;
        if (!plantIdToUse) return;
        
        console.log('Loading plant dates for:', this.species, plantIdToUse);
        const response = await getPlantDates(this.species, plantIdToUse);
        this.plantDates = response.dates || [];
        console.log('Plant dates loaded:', this.plantDates);
        
        // Initialize date range after loading plant dates
        this.initializeDates();
      } catch (error) {
        console.error('Error loading plant dates:', error);
        this.plantDates = [];
      }
    },
    
    async loadTimelineData() {
      if (this.isLoadingTimeline) {
        console.log('Already loading timeline data, skipping...');
        return;
      }
      
      // Get plants to load data for
      let plantsToLoad = this.selectedPlantIds;
      
      // Fallback to default plantId if no plants selected
      if (plantsToLoad.length === 0 && this.actualPlantId) {
        plantsToLoad = [this.actualPlantId];
        // Also update selectedPlants if it's empty
        if (this.selectedPlants.length === 0) {
          const matchingOption = this.plantOptions.find(opt => opt.value === this.actualPlantId);
          if (matchingOption) {
            this.selectedPlants = [matchingOption];
          }
        }
      }
      
      if (plantsToLoad.length === 0) {
        console.log('No plants selected to load data for');
        return;
      }
      
      this.isLoadingTimeline = true;
      console.log('Starting to load timeline data for plants:', plantsToLoad);
      
      try {
        // Load data for each selected plant
        const loadPromises = plantsToLoad.map(async (plantId) => {
          if (!this.multiPlantData[plantId]) {
            this.multiPlantData[plantId] = {
              vegetation: null,
              texture: null,
              morphology: null
            };
          }
          
          // Load vegetation data
          if (this.selectedFeatureType === 'vegetation' && this.selectedFeature) {
            try {
              const vegResponse = await getVegetationTimeline(this.species, plantId, this.selectedFeature);
              this.multiPlantData[plantId].vegetation = vegResponse.timeline || [];
              if (this.multiPlantData[plantId].vegetation.length > 0) this.hasLoadedOnce = true;
            } catch (error) {
              console.error(`Error loading vegetation for ${plantId}:`, error);
              this.multiPlantData[plantId].vegetation = [];
            }
          }
          
          // Load texture data
          if (this.selectedFeatureType === 'texture' && this.selectedTextureBand && this.selectedTextureType) {
            try {
              const textureResponse = await getTextureTimeline(
                this.species, 
                plantId, 
                this.selectedTextureBand, 
                this.selectedTextureType
              );
              this.multiPlantData[plantId].texture = textureResponse.timeline || textureResponse || [];
              if (this.multiPlantData[plantId].texture.length > 0) this.hasLoadedOnce = true;
            } catch (error) {
              console.error(`Error loading texture for ${plantId}:`, error);
              this.multiPlantData[plantId].texture = [];
            }
          }
          
          // Load morphology data
          if (this.selectedFeatureType === 'morphology' && this.selectedFeature) {
            try {
              const morphResponse = await getMorphologyTimeline(this.species, plantId, this.selectedFeature);
              this.multiPlantData[plantId].morphology = morphResponse.timeline || [];
              if (this.multiPlantData[plantId].morphology.length > 0) this.hasLoadedOnce = true;
            } catch (error) {
              console.error(`Error loading morphology for ${plantId}:`, error);
              this.multiPlantData[plantId].morphology = [];
            }
          }
        });
        
        await Promise.all(loadPromises);
        console.log('Timeline data loading completed for all plants');
        
      } catch (error) {
        console.error('Error loading timeline data:', error);
      } finally {
        this.isLoadingTimeline = false;
        console.log('Loading state reset');
      }
    },
    
    
    initializeChart() {
      if (!this.$refs.timelineChart) {
        console.warn('Canvas element not found, chart initialization skipped');
        return false;
      }
      
      // Destroy existing chart if it exists
      if (this.chart) {
        this.chart.destroy();
        this.chart = null;
      }
      
      const ctx = this.$refs.timelineChart.getContext('2d');
      
      // Register custom plugin for clickable image rendering
      Chart.register({
        id: 'imagePlugin',
        beforeDraw: (chart) => {
          if (!this.showImages || !this.currentData.length) return;
          
          const ctx = chart.ctx;
          const selectedImages = this.selectedImages;
          
          selectedImages.forEach((imageData) => {
            const datasetIndex = 0; // Use first dataset for positioning
            const dataIndex = this.currentData.findIndex(d => d.date === imageData.date);
            
            if (dataIndex === -1) return;
            
            const meta = chart.getDatasetMeta(datasetIndex);
            const point = meta.data[dataIndex];
            
            if (!point) return;
            
            // Get image size based on selection
            const sizeMap = {
              'small': 30,
              'medium': 50,
              'large': 70,
              'xlarge': 100
            };
            const imageSize = sizeMap[this.imageSize] || 50;
            
            // Create image element
            const img = new Image();
            img.onload = () => {
              const x = point.x;
              const y = point.y - imageSize - 15; // Position above point
              
              // Draw image background
              ctx.save();
              ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
              ctx.fillRect(x - imageSize/2, y, imageSize, imageSize);
              
              // Draw image
              ctx.drawImage(img, x - imageSize/2, y, imageSize, imageSize);
              
              // Draw border
              ctx.strokeStyle = '#4ade80';
              ctx.lineWidth = 2;
              ctx.strokeRect(x - imageSize/2, y, imageSize, imageSize);
              
              // Draw date label
              ctx.fillStyle = '#333';
              ctx.font = '10px Arial';
              ctx.textAlign = 'center';
              ctx.fillText(this.formatDate(imageData.date), x, y + imageSize + 12);
              
              ctx.restore();
            };
            img.onerror = () => {
              // Draw placeholder if image fails to load
              ctx.save();
              const x = point.x;
              const y = point.y - imageSize - 15;
              
              ctx.fillStyle = 'rgba(200, 200, 200, 0.8)';
              ctx.fillRect(x - imageSize/2, y, imageSize, imageSize);
              
              ctx.strokeStyle = '#999';
              ctx.lineWidth = 1;
              ctx.strokeRect(x - imageSize/2, y, imageSize, imageSize);
              
              ctx.fillStyle = '#666';
              ctx.font = '10px Arial';
              ctx.textAlign = 'center';
              ctx.fillText('No Image', x, y + imageSize/2);
              ctx.fillText(this.formatDate(imageData.date), x, y + imageSize + 12);
              
              ctx.restore();
            };
            img.src = imageData.url;
          });
        }
      });
      
      this.chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: []
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            intersect: false,
            mode: 'index'
          },
          plugins: {
            title: {
              display: true,
              text: 'Plant Timeline Analysis',
              font: {
                size: 16,
                weight: 'bold',
                color: 'white'
              }
            },
            legend: {
              display: true,
              position: 'top',
              labels: {
                color: 'white',
                font: {
                  size: 12
                }
              }
            },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              titleColor: 'white',
              bodyColor: 'white',
              callbacks: {
                title: (context) => {
                  return `Date: ${context[0].label}`;
                },
                label: (context) => {
                  const dataset = context.dataset;
                  return `${dataset.label}: ${this.formatValue(context.parsed.y)}`;
                },
                afterBody: (context) => {
                  const dataIndex = context[0].dataIndex;
                  const dataset = context[0].dataset;
                  const date = this.availableDates[dataIndex];
                  
                  if (!date) return [];
                  
                  // Find data point for this plant and date
                  const dataPoint = this.currentData.find(d => 
                    d.plantId === dataset.plantId && d.date === date
                  );
                  
                  const tooltipLines = [];
                  if (dataPoint && dataPoint.image_key) {
                    tooltipLines.push(`Image: Available`);
                  }
                  return tooltipLines;
                }
              }
            }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Date',
                font: {
                  weight: 'bold',
                  color: 'white'
                }
              },
              ticks: {
                maxRotation: 45,
                color: 'white'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            },
            y: {
              title: {
                display: true,
                text: 'Value',
                font: {
                  weight: 'bold',
                  color: 'white'
                }
              },
              ticks: {
                color: 'white'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            }
          }
        }
      });
      
      // Add click event handler for images
      this.$refs.timelineChart.addEventListener('click', (event) => {
        if (!this.showImages || !this.currentData.length) return;
        
        const rect = this.$refs.timelineChart.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        // Check if click is on an image
        const selectedImages = this.selectedImages;
        const sizeMap = {
          'small': 30,
          'medium': 50,
          'large': 70,
          'xlarge': 100
        };
        const imageSize = sizeMap[this.imageSize] || 50;
        
        selectedImages.forEach((imageData) => {
          const dataIndex = this.currentData.findIndex(d => d.date === imageData.date);
          if (dataIndex === -1) return;
          
          const meta = this.chart.getDatasetMeta(0);
          const point = meta.data[dataIndex];
          
          if (!point) return;
          
          const imageX = point.x;
          const imageY = point.y - imageSize - 15;
          
          // Check if click is within image bounds
          if (x >= imageX - imageSize/2 && x <= imageX + imageSize/2 &&
              y >= imageY && y <= imageY + imageSize) {
            this.showFullImage(imageData.url, imageData.date);
          }
        });
      });
      
      console.log('Chart initialized successfully');
      return true;
    },
    
    initializeDates() {
      if (this.plantDates.length > 0) {
        this.startDate = this.plantDates[0];
        this.endDate = this.plantDates[this.plantDates.length - 1];
        console.log('Initialized date range:', { startDate: this.startDate, endDate: this.endDate });
      } else {
        console.log('No plant dates available for initialization');
      }
    },
    
    toggleImages() {
      this.showImages = !this.showImages;
    },
    
    
    onTextureBandChange() {
      console.log('Texture band changed to:', this.selectedTextureBand);
      
      // Clear texture data when band changes
      this.textureData = null;
      this.updateTextureFeatures();
    },
    
    updateTextureFeatures() {
      if (!this.selectedTextureBand) {
        this.availableTextureTypes = [];
        this.selectedTextureType = '';
        return;
      }
      
      // Available texture features based on the analysis pipeline
      this.availableTextureTypes = [
        { value: 'lbp', label: 'LBP (Local Binary Pattern)' },
        { value: 'hog', label: 'HOG (Histogram of Oriented Gradients)' },
        { value: 'lac1', label: 'Lac1 (Lacunarity - Base Window)' },
        { value: 'lac2', label: 'Lac2 (Lacunarity - Multi-scale)' },
        { value: 'lac3', label: 'Lac3 (DBC Lacunarity)' },
        { value: 'ehd_map', label: 'EHD (Edge Histogram Descriptor)' }
      ];
      this.selectedTextureType = '';
    },
    
    onFeatureTypeChange() {
      console.log('Feature type changed to:', this.selectedFeatureType);
      this.selectedFeature = '';
      this.selectedTextureBand = '';
      this.selectedTextureType = '';
      // Clear existing data when feature type changes
      this.vegetationData = null;
      this.textureData = null;
      this.morphologyData = null;
    },
    
    async onFeatureChange() {
      console.log('Feature change triggered:', {
        selectedFeatureType: this.selectedFeatureType,
        selectedFeature: this.selectedFeature,
        selectedTextureBand: this.selectedTextureBand,
        selectedTextureType: this.selectedTextureType,
        selectedPlants: this.selectedPlantIds
      });
      
      // Get plants to load data for
      const plantsToLoad = this.selectedPlantIds.length > 0 
        ? this.selectedPlantIds 
        : [this.actualPlantId].filter(Boolean);
      
      if (plantsToLoad.length === 0) {
        console.log('No plants selected - not loading data');
        return;
      }
      
      // Automatically load data when feature changes
      if (this.selectedFeatureType === 'vegetation' && this.selectedFeature) {
        console.log('Loading vegetation data for plants:', plantsToLoad);
        await this.loadTimelineData();
        this.initializeDates();
        this.$nextTick(() => {
          if (!this.chart) {
            this.initializeChart();
          }
          this.updateChart();
        });
      } else if (this.selectedFeatureType === 'texture' && this.selectedTextureBand && this.selectedTextureType) {
        console.log('Loading texture data for plants:', plantsToLoad);
        await this.loadTimelineData();
        this.initializeDates();
        this.$nextTick(() => {
          if (!this.chart) {
            this.initializeChart();
          }
          this.updateChart();
        });
      } else if (this.selectedFeatureType === 'morphology' && this.selectedFeature) {
        console.log('Loading morphology data for plants:', plantsToLoad);
        await this.loadTimelineData();
        this.initializeDates();
        this.$nextTick(() => {
          if (!this.chart) {
            this.initializeChart();
          }
          this.updateChart();
        });
      } else {
        console.log('Incomplete selection - not loading data');
      }
    },
    
    updateChart() {
      if (!this.chart) {
        console.warn('Chart not initialized, cannot update');
        return;
      }
      
      // Check if we have plants selected
      if (this.selectedPlantIds.length === 0) {
        console.log('No plants selected, clearing chart');
        this.chart.data.labels = [];
        this.chart.data.datasets = [];
        this.chart.update('none');
        return;
      }
      
      this.loading = true;
      console.log('Updating chart...');
      console.log('Current state:', {
        selectedPlants: this.selectedPlantIds,
        selectedFeatureType: this.selectedFeatureType,
        selectedFeature: this.selectedFeature,
        selectedTextureBand: this.selectedTextureBand,
        selectedTextureType: this.selectedTextureType,
        multiPlantData: Object.keys(this.multiPlantData)
      });
      
      try {
        const data = this.getChartData();
        console.log('Chart data:', data);
        
        if (data.labels.length === 0 || data.datasets.length === 0) {
          console.warn('No data to display in chart');
          this.chart.data.labels = [];
          this.chart.data.datasets = [];
          this.chart.update('none');
          return;
        }
        
        this.chart.data.labels = data.labels;
        this.chart.data.datasets = data.datasets;
        
        // Update chart title
        this.chart.options.plugins.title.text = this.getChartTitle();
        
        this.chart.update('active');
        console.log('Chart updated successfully with', data.labels.length, 'labels and', data.datasets.length, 'datasets');
      } catch (error) {
        console.error('Error updating chart:', error);
      } finally {
        this.loading = false;
      }
    },
    
    getChartData() {
      // Get plants to display
      const plantsToDisplay = this.selectedPlantIds.length > 0 
        ? this.selectedPlantIds 
        : [this.actualPlantId].filter(Boolean);
      
      if (plantsToDisplay.length === 0) {
        return { labels: [], datasets: [] };
      }
      
      // Collect all timeline data from all plants
      const allTimelineData = [];
      const dateSet = new Set();
      
      plantsToDisplay.forEach(plantId => {
        const plantData = this.multiPlantData[plantId];
        if (!plantData) return;
        
        let plantTimelineData = [];
        
        if (this.selectedFeatureType === 'vegetation' && this.selectedFeature && plantData.vegetation) {
          plantTimelineData = plantData.vegetation.map(item => ({
            ...item,
            plantId: plantId,
            plantName: this.formatPlantName(plantId)
          }));
        } else if (this.selectedFeatureType === 'texture' && this.selectedTextureBand && this.selectedTextureType && plantData.texture) {
          plantTimelineData = plantData.texture.map(item => ({
            ...item,
            plantId: plantId,
            plantName: this.formatPlantName(plantId)
          }));
        } else if (this.selectedFeatureType === 'morphology' && this.selectedFeature && plantData.morphology) {
          plantTimelineData = plantData.morphology.map(item => ({
            ...item,
            plantId: plantId,
            plantName: this.formatPlantName(plantId)
          }));
        }
        
        // Filter by date range
        plantTimelineData = plantTimelineData.filter(d => this.isDateInRange(d.date));
        plantTimelineData.forEach(d => dateSet.add(d.date));
        allTimelineData.push(...plantTimelineData);
      });
      
      if (allTimelineData.length === 0) {
        return { labels: [], datasets: [] };
      }
      
      // Get all unique dates and sort them (string comparison works for YYYY-MM-DD format)
      const allDates = Array.from(dateSet).sort((a, b) => {
        // Direct string comparison works for YYYY-MM-DD format
        if (a < b) return -1;
        if (a > b) return 1;
        return 0;
      });
      const labels = allDates.map(d => this.formatDate(d));
      
      // Store current data for computed properties
      this.currentData = allTimelineData;
      
      const datasets = [];
      
      // Create datasets for each plant and each statistic
      plantsToDisplay.forEach((plantId, plantIndex) => {
        const plantName = this.formatPlantName(plantId);
        const plantColor = this.plantColors[plantIndex % this.plantColors.length];
        const markerShape = this.plantMarkers[plantIndex % this.plantMarkers.length];
        
        // Get plant's timeline data
        const plantData = allTimelineData.filter(d => d.plantId === plantId);
        const plantDataByDate = {};
        plantData.forEach(d => {
          plantDataByDate[d.date] = d;
        });
        
        // Create data arrays aligned with all dates
        const getDataForStat = (statName) => {
          return allDates.map(date => {
            const dataPoint = plantDataByDate[date];
            return dataPoint ? dataPoint[statName] : null;
          });
        };
        
        // Mean
        if (this.showMean) {
          datasets.push({
            label: `${plantName} - Mean`,
            data: getDataForStat('mean'),
            borderColor: this.statisticsColors.mean,
            backgroundColor: this.hexToRgba(this.statisticsColors.mean, 0.2),
            pointBackgroundColor: plantColor,
            pointBorderColor: this.statisticsColors.mean,
            pointBorderWidth: 2,
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointStyle: markerShape,
            plantId: plantId,
            statistic: 'mean'
          });
        }
        
        // Median
        if (this.showMedian) {
          datasets.push({
            label: `${plantName} - Median`,
            data: getDataForStat('median'),
            borderColor: this.statisticsColors.median,
            backgroundColor: this.hexToRgba(this.statisticsColors.median, 0.2),
            pointBackgroundColor: plantColor,
            pointBorderColor: this.statisticsColors.median,
            pointBorderWidth: 2,
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointStyle: markerShape,
            plantId: plantId,
            statistic: 'median'
          });
        }
        
        // Standard Deviation
        if (this.showStd) {
          datasets.push({
            label: `${plantName} - Std Dev`,
            data: getDataForStat('std'),
            borderColor: this.statisticsColors.std,
            backgroundColor: this.hexToRgba(this.statisticsColors.std, 0.2),
            pointBackgroundColor: plantColor,
            pointBorderColor: this.statisticsColors.std,
            pointBorderWidth: 2,
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointStyle: markerShape,
            plantId: plantId,
            statistic: 'std'
          });
        }
        
        // Q25
        if (this.showQ25) {
          datasets.push({
            label: `${plantName} - Q25`,
            data: getDataForStat('q25'),
            borderColor: this.statisticsColors.q25,
            backgroundColor: this.hexToRgba(this.statisticsColors.q25, 0.2),
            pointBackgroundColor: plantColor,
            pointBorderColor: this.statisticsColors.q25,
            pointBorderWidth: 2,
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointStyle: markerShape,
            plantId: plantId,
            statistic: 'q25'
          });
        }
        
        // Q75
        if (this.showQ75) {
          datasets.push({
            label: `${plantName} - Q75`,
            data: getDataForStat('q75'),
            borderColor: this.statisticsColors.q75,
            backgroundColor: this.hexToRgba(this.statisticsColors.q75, 0.2),
            pointBackgroundColor: plantColor,
            pointBorderColor: this.statisticsColors.q75,
            pointBorderWidth: 2,
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointStyle: markerShape,
            plantId: plantId,
            statistic: 'q75'
          });
        }
        
        // Min
        if (this.showMin) {
          datasets.push({
            label: `${plantName} - Min`,
            data: getDataForStat('min'),
            borderColor: this.statisticsColors.min,
            backgroundColor: this.hexToRgba(this.statisticsColors.min, 0.2),
            pointBackgroundColor: plantColor,
            pointBorderColor: this.statisticsColors.min,
            pointBorderWidth: 2,
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointStyle: markerShape,
            plantId: plantId,
            statistic: 'min'
          });
        }
        
        // Max
        if (this.showMax) {
          datasets.push({
            label: `${plantName} - Max`,
            data: getDataForStat('max'),
            borderColor: this.statisticsColors.max,
            backgroundColor: this.hexToRgba(this.statisticsColors.max, 0.2),
            pointBackgroundColor: plantColor,
            pointBorderColor: this.statisticsColors.max,
            pointBorderWidth: 2,
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointStyle: markerShape,
            plantId: plantId,
            statistic: 'max'
          });
        }
      });
      
      return { labels, datasets };
    },

    // Helper to convert hex to rgba
    hexToRgba(hex, alpha = 1) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    },
    
    getChartTitle() {
      if (this.selectedFeatureType === 'vegetation' && this.selectedFeature) {
        return `${this.selectedFeature} Timeline`;
      } else if (this.selectedFeatureType === 'texture' && this.selectedTextureBand && this.selectedTextureType) {
        return `${this.selectedTextureBand} ${this.selectedTextureType} Timeline`;
      }
      return 'Plant Timeline Analysis';
    },
    
    isDateInRange(date) {
      if (!this.startDate && !this.endDate) return true;
      if (this.startDate && date < this.startDate) return false;
      if (this.endDate && date > this.endDate) return false;
      return true;
    },
    
    formatDate(dateString) {
      if (!dateString) return '';
      
      // Parse date string directly to avoid timezone issues
      // Dates from DB are in YYYY-MM-DD format
      if (typeof dateString === 'string' && dateString.match(/^\d{4}-\d{2}-\d{2}/)) {
        const [year, month, day] = dateString.split('-');
        // Create date in local timezone (not UTC) to avoid day shift
        const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return date.toLocaleDateString();
      }
      
      // Fallback for other date formats
      const date = new Date(dateString);
      return date.toLocaleDateString();
    },
    
    formatValue(value) {
      if (typeof value === 'number') {
        return value.toFixed(4);
      }
      return value;
    },
    
    handleImageError(event) {
      event.target.src = 'https://via.placeholder.com/200x150?text=Image+Not+Available';
    },


    showFullImage(imageUrl, date) {
      // Create modal or use existing modal system
      const modal = document.createElement('div');
      modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        cursor: pointer;
      `;
      
      const img = document.createElement('img');
      img.src = imageUrl;
      img.style.cssText = `
        max-width: 90%;
        max-height: 90%;
        object-fit: contain;
        border-radius: 8px;
      `;
      
      const caption = document.createElement('div');
      caption.textContent = `Date: ${this.formatDate(date)}`;
      caption.style.cssText = `
        position: absolute;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        color: white;
        font-size: 16px;
        background: rgba(0, 0, 0, 0.7);
        padding: 8px 16px;
        border-radius: 4px;
      `;
      
      modal.appendChild(img);
      modal.appendChild(caption);
      
      modal.addEventListener('click', () => {
        document.body.removeChild(modal);
      });
      
      document.body.appendChild(modal);
    }
  }
};
</script>

<style scoped>
.plant-timeline {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  background: transparent;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.timeline-header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  text-align: left;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.refresh-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 40px;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.images-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 40px;
}

.images-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
}

.images-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.images-btn.active {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
}

.timeline-header h2 {
  margin: 0 0 8px 0;
  color: white;
  font-size: 20px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.timeline-header p {
  margin: 0;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}

.timeline-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 20px;
  margin-bottom: 20px;
  min-height: 0;
}

.chart-and-config {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.chart-container {
  flex: 1;
  background: rgba(255, 255, 255, 0.33);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  position: relative;
  height: 400px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  min-height: 0;
}

.loading-overlay,
.no-data-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: 12px;
}

.no-data-overlay {
  background: rgba(255, 255, 255, 0.8);
}

.no-data-overlay p {
  color: #666;
  font-size: 16px;
  margin-bottom: 16px;
}

.retry-btn,
.load-btn {
  background: #4ade80;
  color: #000;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.retry-btn:hover,
.load-btn:hover {
  background: #22c55e;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.loading-detail {
  margin-top: 8px;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.6);
}

.loading-spinner.small {
  width: 20px;
  height: 20px;
  border-width: 2px;
  margin-bottom: 0;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.config-panel {
  width: 320px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  height: fit-content;
  border: 1px solid rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
  transition: opacity 0.3s ease;
}

.config-panel.disabled {
  opacity: 0.6;
  pointer-events: none;
}

.config-panel h3 {
  margin-top: 0;
  margin-bottom: 24px;
  color: white;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 2px solid #4ade80;
  padding-bottom: 8px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.config-group {
  margin-bottom: 20px;
}

.config-group label {
  display: block;
  margin-bottom: 8px;
  color: white;
  font-weight: 500;
  font-size: 14px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.config-group select,
.config-group input[type="number"],
.config-group input[type="date"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.config-group select:focus,
.config-group input:focus {
  outline: none;
  border-color: #4ade80;
  box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.1);
  background: rgba(255, 255, 255, 0.15);
}

.config-group select option {
  background: #333;
  color: white;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-group-two-columns {
  display: flex;
  gap: 20px;
}

.checkbox-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.checkbox-group label,
.checkbox-column label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: normal;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.8);
  transition: color 0.2s ease;
}

.checkbox-group label:hover,
.checkbox-column label:hover {
  color: #4ade80;
}

.checkbox-group input[type="checkbox"],
.checkbox-column input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: #4ade80;
  cursor: pointer;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 12px;
}

.date-range select {
  flex: 1;
}

.date-range span {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  font-weight: 500;
}

.max-plants-warning {
  display: block;
  margin-top: 4px;
  color: #ffd700;
  font-size: 11px;
  font-style: italic;
}

.plant-selector-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plant-select-dropdown {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}

.plant-select-dropdown:focus {
  outline: none;
  border-color: #4ade80;
  box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.1);
  background: rgba(255, 255, 255, 0.15);
}

.plant-select-dropdown:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.plant-select-dropdown option {
  background: #333;
  color: white;
}

.selected-plants-list {
  margin-top: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.selected-plants-header {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.selected-plant-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  margin-bottom: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  border-left: 3px solid #4ade80;
  transition: background 0.2s ease;
}

.selected-plant-item:last-child {
  margin-bottom: 0;
}

.selected-plant-item:hover {
  background: rgba(255, 255, 255, 0.12);
}

.plant-name {
  color: white;
  font-size: 14px;
  font-weight: 500;
  flex: 1;
}

.remove-plant-btn {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  padding: 0;
  flex-shrink: 0;
}

.remove-plant-btn:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.3);
  border-color: rgba(239, 68, 68, 0.6);
  transform: scale(1.1);
}

.remove-plant-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.texture-description,
.feature-description {
  margin-top: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  border-left: 3px solid #4ade80;
}

.texture-description small,
.feature-description small {
  color: rgba(255, 255, 255, 0.8);
  font-size: 11px;
  line-height: 1.4;
}

.stats-summary {
  margin-top: 24px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.stats-summary h4 {
  margin: 0 0 12px 0;
  color: white;
  font-size: 14px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.stat-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
}

.stat-item:last-child {
  margin-bottom: 0;
}

.stat-item span:first-child {
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}

.stat-item span:last-child {
  color: white;
  font-weight: 600;
}

.images-section {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  margin-top: 20px;
}

.images-section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: white;
  font-size: 18px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.image-item {
  text-align: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.image-item h4 {
  margin: 0 0 12px 0;
  color: white;
  font-size: 14px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.image-item img {
  width: 100%;
  height: 160px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #ddd;
  transition: transform 0.2s ease;
}

.image-item img:hover {
  transform: scale(1.02);
}

/* New styles for images above chart */
.images-section-above {
  width: 320px; /* Match config panel width */
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
  transition: opacity 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.images-section-above h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: white;
  font-size: 18px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.images-grid-small {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  width: 100%;
}

.image-item-small {
  text-align: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.image-item-small h4 {
  margin: 0 0 12px 0;
  color: white;
  font-size: 12px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.image-item-small img {
  width: 100%;
  height: 160px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #ddd;
  transition: transform 0.2s ease;
}

.image-item-small img:hover {
  transform: scale(1.02);
}

/* Responsive Design */

/* Large screens (1440px and above) */
@media (min-width: 1440px) {
  .chart-container {
    height: 450px;
  }
}

/* Medium-large screens (1200px - 1024px) */
@media (max-width: 1200px) {
  .timeline-content {
    flex-direction: column;
  }
  
  .chart-and-config {
    flex-direction: column;
  }
  
  .chart-container {
    height: 350px;
  }
  
  .config-panel {
    width: 100%;
  }
  
  .images-section-above {
    width: 100%;
  }
}

/* Tablets (1024px and below) */
@media (max-width: 1024px) {
  .chart-container {
    height: 320px;
  }
  
  .timeline-header h2 {
    font-size: 22px;
  }
  
  .timeline-header p {
    font-size: 14px;
  }
}

/* Medium tablets and small laptops (900px - 768px) */
@media (max-width: 900px) {
  .chart-container {
    height: 300px;
  }
  
  .config-panel {
    padding: 16px;
  }
}

/* Mobile devices (768px and below) */
@media (max-width: 768px) {
  .timeline-header {
    padding: 12px 16px;
  }
  
  .timeline-header h2 {
    font-size: 18px;
  }
  
  .timeline-header p {
    font-size: 12px;
  }
  
  .config-panel {
    padding: 14px;
  }
  
  .config-panel h3 {
    font-size: 16px;
  }
  
  .config-group {
    margin-bottom: 14px;
  }
  
  .config-group label {
    font-size: 12px;
  }
  
  .chart-container {
    height: 280px;
    padding: 14px;
  }
  
  .checkbox-group-two-columns {
    flex-direction: column;
    gap: 12px;
  }
  
  .checkbox-column {
    gap: 8px;
  }
  
  .images-grid-small {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .image-item-small img {
    height: 120px;
  }
  
  .plant-select-dropdown {
    font-size: 13px;
    padding: 8px 12px;
  }
  
  .selected-plants-list {
    font-size: 12px;
  }
  
  .selected-plant-item {
    padding: 6px 10px;
  }
}

/* Small mobile devices (480px and below) */
@media (max-width: 480px) {
  .timeline-content {
    gap: 12px;
  }
  
  .timeline-header {
    padding: 10px 12px;
  }
  
  .timeline-header h2 {
    font-size: 16px;
  }
  
  .timeline-header p {
    font-size: 11px;
  }
  
  .config-panel {
    padding: 12px;
  }
  
  .config-panel h3 {
    font-size: 14px;
  }
  
  .config-group {
    margin-bottom: 12px;
  }
  
  .config-group label {
    font-size: 11px;
  }
  
  .chart-container {
    height: 250px;
    padding: 12px;
  }
  
  .images-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .date-range {
    flex-direction: column;
    gap: 8px;
  }
  
  .date-range input {
    width: 100%;
    font-size: 12px;
    padding: 6px 10px;
  }
  
  select {
    font-size: 12px;
    padding: 6px 10px;
  }
  
  .plant-select-dropdown {
    font-size: 12px;
    padding: 6px 10px;
  }
  
  .selected-plants-list {
    font-size: 11px;
  }
  
  .selected-plant-item {
    padding: 5px 8px;
  }
  
  .remove-plant-btn {
    font-size: 18px;
    width: 24px;
    height: 24px;
  }
}

/* Extra small devices (360px and below) */
@media (max-width: 360px) {
  .timeline-header h2 {
    font-size: 14px;
  }
  
  .timeline-header p {
    font-size: 10px;
  }
  
  .config-panel {
    padding: 10px;
  }
  
  .config-panel h3 {
    font-size: 13px;
  }
  
  .chart-container {
    height: 220px;
    padding: 10px;
  }
  
  .image-item-small img {
    height: 100px;
  }
}

.chart-container {
  position: relative;
}

.chart-thumbnail {
  position: absolute;
  width: 40px;
  height: 40px;
  border: 2px solid #4ade80;
  border-radius: 4px;
  overflow: hidden;
  background: white;
  z-index: 10;
  cursor: pointer;
  transition: transform 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.chart-thumbnail:hover {
  transform: scale(1.2);
  z-index: 11;
}

.chart-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chart-thumbnail.no-image {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 10px;
  background: #f5f5f5;
}
</style>