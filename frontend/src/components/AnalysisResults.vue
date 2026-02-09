<template>
  <div class="analysis-results">

    <!-- Content based on results state -->
    <div class="results-content">
      <!-- No results state -->
      <div v-if="!results" class="no-results">
        <div class="no-results-message">
          <h4>Selected: {{ species }}</h4>
          <!-- <h4>No Results Available</h4> -->
          <p>Please run an analysis to see results here.</p>
        </div>
      </div>

      <!-- Results available - show with tabs -->
      <div v-else class="results-available">

        <!-- Tabs Navigation -->
        <div class="tabs-container">
          <div class="tabs-header sticky-tabs">
            <button
              v-for="(tab, index) in tabs"
              :key="index"
              class="tab-button"
              :class="{ active: activeTab === index }"
              @click="activeTab = index"
            >
              {{ tab.label }}
            </button>
          </div>

          <!-- Tab Content -->
          <div class="tab-content">
            <!-- Images Tab -->
            <div v-if="activeTab === 0" class="tab-panel">
              <div class="tab-header">
                <h3>Main Images</h3>
                <button v-if="mainImages_DB.length" @click="downloadAllImages()" class="download-all-btn">
                  Download All Images
                </button>
              </div>
              <div v-if="mainImages_DB.length">
                <div class="image-grid">
                  <div v-for="img in mainImages_DB" :key="img.label" class="image-item">
                    <img 
                      :src="img.url" 
                      :alt="img.label" 
                      class="result-image clickable" 
                      @click="openImageModal(img)"
                    />
                    <h4 class="image-title">{{ img.label.replace(/Image/gi, '').trim() }}</h4>
                  </div>
                </div>
              </div>
              <div v-else class="no-images-message">
                <h4>No Images Available</h4>
                <p>No images were found in the analysis results.</p>
                <p><strong>Debug Info:</strong> Plant ID: {{ getDisplayText(plantId) }}, Date: {{ getDisplayText(analysisDate) }}</p>
              </div>
            </div>

            <!-- Texture Images Tab -->
            <div v-else-if="activeTab === 1" class="tab-panel">
              <div class="tab-header">
                <h3>Texture Images</h3>
                <button v-if="textureImages_DB.length" @click="downloadAllImages()" class="download-all-btn">
                  Download All Images
                </button>
              </div>
              <div v-if="textureImages_DB.length">
                <div class="image-grid">
                  <div v-for="img in textureImages_DB" :key="img.label" class="image-item">
                    <img 
                      :src="img.url" 
                      :alt="img.label" 
                      class="result-image clickable" 
                      @click="openImageModal(img)"
                    />
                    <h4 class="image-title">{{ img.label.replace(/Image/gi, '').trim() }}</h4>
                  </div>
                </div>
              </div>
              <div v-else class="no-images-message">
                <h4>No Texture Images Available</h4>
                <p>No texture images were found in the analysis results.</p>
              </div>
            </div>

            <!-- Vegetation Indices Images Tab -->
            <div v-else-if="activeTab === 2" class="tab-panel">
              <div class="tab-header">
                <h3>Vegetation Indices Images</h3>
                <button v-if="vegetationIndicesImages_DB.length" @click="downloadAllImages()" class="download-all-btn">
                  Download All Images
                </button>
              </div>
              <div v-if="vegetationIndicesImages_DB.length">
                <div class="image-grid">
                  <div v-for="img in vegetationIndicesImages_DB" :key="img.label" class="image-item">
                    <img 
                      :src="img.url" 
                      :alt="img.label" 
                      class="result-image clickable" 
                      @click="openImageModal(img)"
                    />
                    <h4 class="image-title">{{ img.label.replace(/Image/gi, '').trim() }}</h4>
                  </div>
                </div>
              </div>
              <div v-else class="no-images-message">
                <h4>No Vegetation Indices Available</h4>
                <p>No vegetation indices were found in the analysis results.</p>
              </div>
            </div>

            <!-- Morphological Images Tab -->
            <div v-else-if="activeTab === 3" class="tab-panel">
              <div class="tab-header">
                <h3>Morphological Images</h3>
                <button v-if="morphologicalImages.length" @click="downloadAllImages()" class="download-all-btn">
                  Download All Images
                </button>
              </div>
              <div v-if="morphologicalImages.length">
                <div class="image-grid">
                  <div v-for="img in morphologicalImages" :key="img.label" class="image-item">
                    <img 
                      :src="img.url" 
                      :alt="img.label" 
                      class="result-image clickable" 
                      @click="openImageModal(img)"
                      @error="handleImageError($event, img.key)"
                      @load="img.loaded = true"
                    />
                    <h4 class="image-title">{{ img.label.replace(/Image/gi, '').trim() }}</h4>
                  </div>
                </div>
              </div>
              <div v-else class="no-images-message">
                <h4>No Morphological Images Available</h4>
                <p>No morphological images were found for this plant and date.</p>
                <p><strong>Debug Info:</strong> Plant ID: {{ getDisplayText(plantId) }}, Date: {{ getDisplayText(analysisDate) }}</p>
              </div>
            </div>

            <!-- Vegetation Indices Table Tab -->
            <div v-else-if="activeTab === 4" class="tab-panel">
              <div class="tab-header">
                <h3>Vegetation Indices Table</h3>
                <button @click="downloadCSV('vegIndex')" class="download-btn">
                  Download CSV
                </button>
              </div>
              <div class="table-controls">
                <input 
                  v-model="vegIndexSearch" 
                  type="text" 
                  placeholder="Search vegetation indices..." 
                  class="search-input"
                />
                
              </div>
              <div v-if="filteredVegIndexItemsDB.length" class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th v-for="header in vegIndexHeaders" :key="header.value" @click="sortTable('vegIndex', header.value)" class="sortable-header">
                        {{ header.text }}
                        <span v-if="sortColumn === header.value" class="sort-indicator">
                          {{ sortDirection === 'asc' ? '↑' : '↓' }}
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in filteredVegIndexItemsDB" :key="item.index">
                      <td v-for="header in vegIndexHeaders" :key="header.value">
                        {{ formatValue(item[header.value]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="no-data-message">
                <h4>No Vegetation Indices Data Available</h4>
                <p>No vegetation indices data was found in the analysis results.</p>
              </div>
            </div>

            <!-- Texture Features Table Tab -->
            <div v-else-if="activeTab === 5" class="tab-panel">
              <div class="tab-header">
                <h3>Texture Features Table</h3>
                <button @click="downloadCSV('texture')" class="download-btn">
                  Download CSV
                </button>
              </div>
              <div class="table-controls">
                <input 
                  v-model="textureSearch" 
                  type="text" 
                  placeholder="Search texture features..." 
                  class="search-input"
                />
              </div>
              <div v-if="filteredTextureItemsDB.length" class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th v-for="header in textureHeaders" :key="header.value" @click="sortTable('texture', header.value)" class="sortable-header">
                        {{ header.text }}
                        <span v-if="sortColumn === header.value" class="sort-indicator">
                          {{ sortDirection === 'asc' ? '↑' : '↓' }}
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in filteredTextureItemsDB" :key="item.feature"> 
                      <td v-for="header in textureHeaders" :key="header.value">
                        {{ formatValue(item[header.value]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="no-data-message">
                <h4>No Texture Features Data Available</h4>
                <p>No texture features data was found in the analysis results.</p>
              </div>
            </div>

            <!-- Morphological Features Table Tab -->
            <div v-else-if="activeTab === 6" class="tab-panel">
              <div class="tab-header">
                <h3>Morphological Features Table</h3>
                <button @click="downloadCSV('morph')" class="download-btn">
                  Download CSV
                </button>
              </div>
              <div class="table-controls">
                <input 
                  v-model="morphSearch" 
                  type="text" 
                  placeholder="Search morphological features..." 
                  class="search-input"
                />
              </div>
              <div v-if="filteredMorphItems.length" class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th v-for="header in morphHeaders" :key="header.value" @click="sortTable('morph', header.value)" class="sortable-header">
                        {{ header.text }}
                        <span v-if="sortColumn === header.value" class="sort-indicator">
                          {{ sortDirection === 'asc' ? '↑' : '↓' }}
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in filteredMorphItems" :key="item.feature">
                      <td v-for="header in morphHeaders" :key="header.value">
                        {{ formatValue(item[header.value]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="no-data-message">
                <h4>No Morphological Features Data Available</h4>
                <p>No morphological features data was found in the analysis results.</p>
              </div>
            </div>

            <!-- Plant Timeline Tab -->
            <div v-else-if="activeTab === 7" class="tab-panel timeline-tab">
              <PlantTimeline 
                :species="species"
                :plant-id="plantId"
                :analysis-date="analysisDate"
              />
            </div>

            <!-- Charts Tab -->
            <div v-else-if="activeTab === 8" class="tab-panel charts-tab">
              <ChartsView />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Image Modal -->
    <div v-if="showModal" class="image-modal" @click="closeImageModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <button class="modal-download" @click="downloadModalImage" title="Download Image">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7,10 12,15 17,10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          </button>
          <button class="modal-close" @click="closeImageModal" title="Close">×</button>
        </div>
        <img :src="selectedImage.url" :alt="selectedImage.label" class="modal-image" />
        <h3 class="modal-title">{{ selectedImage.label }}</h3>
      </div>
    </div>


  </div>
</template>

<script>
import PlantTimeline from './PlantTimeline.vue';
import ChartsView from './ChartsView.vue';
import { downloadImagesZip } from '@/api.js';

export default {
  name: 'AnalysisResults',
  components: {
    PlantTimeline,
    ChartsView
  },
  props: {
    // Basic props
    species: {
      type: String,
      required: true
    },
    
    plantId: {
      type: [String, Object],
      default: null
    },
    
    analysisDate: {
      type: [String, Object],
      default: null
    },
    
    // Results data
    results: {
      type: Object,
      default: null
    },
    
    // Configuration
    title: {
      type: String,
      default: 'Analysis Results'
    },
    
    showStatus: {
      type: Boolean,
      default: true
    }
  },
  
  data() {
    return {
      processingTime: 1.3,
      activeTab: 0,
      showModal: false,
      selectedImage: null,
      
      // Search and sort state
      vegIndexSearch: '',
      textureSearch: '',
      morphSearch: '',
      sortColumn: '',
      sortDirection: 'asc',
      
      
      // Vegetation indices list (same as ResultViewer.vue)
      vegIndexList: [
        'ARI','ARI2','AVI','CCCI','CIgreen','CIRE','CVI','DSWI4','DVI',
        'EVI2','ExR','GEMI','GNDVI','GOSAVI','GRNDVI','GRVI','GSAVI',
        'IPVI','LCI','MCARI','MCARI1','MCARI2','MGRVI','MSAVI','MSR',
        'MTVI1','MTVI2','NDRE','NDVI','NDWI','NGRDI','NLI','OSAVI',
        'PVI','RDVI','RI','RRI1','SIPI2','SR','TCARI','TCARIOSAVI',
        'TNDVI','TSAVI','WDVI'
      ],
      
      // Tab definitions
      tabs: [
        { label: 'Images', key: 'images' },
        { label: 'Texture Images', key: 'texture-images' },
        { label: 'Vegetation Indices Images', key: 'veg-indices-images' },
        { label: 'Morphological Images', key: 'morphological-images' },
        { label: 'Vegetation Indices Table', key: 'veg-indices-table' },
        { label: 'Texture Features Table', key: 'texture-features-table' },
        { label: 'Morphological Features Table', key: 'morphological-features-table' },
        { label: 'Plant Timeline', key: 'plant-timeline' },
        { label: 'Charts', key: 'charts' }
      ],
      
      // Loading states
      isLoading: false,
    };
  },
  

  
  // Watch for changes in results to reload database data
  watch: {
    // Reset to first tab when new results are loaded
    results: {
      handler(newResults) {
        if (newResults) {
          this.activeTab = 0;
        }
      },
      immediate: true
    },
    
    
  },
  
  computed: {
    
    // Extract nested result object if present
    nestedResult() {
      if (!this.results) return null;
      for (const key in this.results) {
        if (key.endsWith('_result') && typeof this.results[key] === 'object') {
          return this.results[key];
        }
      }
      return null;
    },
    
    mainImages() {
      if (!this.results) {
        console.log('mainImages: no results object');
        return [];
      }
      const keys = ['original', 'mask', 'overlay', 'segmented'];
      const images = keys.filter(k => this.results[k]).map(k => ({ 
        label: this.capitalize(k), 
        key: k, 
        url: this.results[k] 
      }));
      console.log('mainImages computed - results:', this.results);
      if (images.length > 0) {
        console.log(`mainImages: found ${images.length} images`);
      } else {
        console.log('mainImages: no images found');
      }
      return images;
    },

    mainImages_DB() {
      if (!this.results || !this.results.mainImages) {
        console.log('mainImages_DB: no dbData or mainImages');
        return [];
      }
      const keys = ['original', 'mask', 'overlay', 'segmented'];
      const dbImages = keys.filter(key => this.results.mainImages[key])
        .map(key => ({
          label: this.capitalize(key),
          key: key,
          url: this.results.mainImages[key]
        }));

      if (dbImages.length > 0) {
        console.log(`mainImages_DB: found ${dbImages.length} images`);
      } else {
        console.log('mainImages_DB: no images found');
      }
      return dbImages;
    },
    
    textureImages() {
      if (!this.results) {
        console.log('textureImages: no result object');
        return [];
      }
      // Find all keys that match texture_{band}_{suffix} and group by band
      const bands = ['color','green','nir','pca','red','red_edge'];
      const suffixes = [
        'orig','gray','lbp','hog','lac1','lac2','lac3','ehd_map'
      ];
      let images = [];
      console.log('textureImages computed - result:', this.results);
      for (const band of bands) {
        for (const suffix of suffixes) {
          const key = `texture_${band}_${suffix}`;
          if (this.results[key]) {
            images.push({
              label: `${this.capitalize(band)} ${suffix.replace(/\d+_/, '').replace('_', ' ').replace('.png','')}`,
              band,
              suffix,
              url: this.results[key]
            });
          }
        }
      }
      console.log(`textureImages: found ${images.length} texture images`);
      if (images.length > 0) {
        console.log('textureImages: sample image keys found:', images.slice(0, 3).map(img => img.label));
      } else {
        console.log('textureImages: no texture images found');
      }
      return images;
    },

    textureImages_DB() {
      if (!this.results || !this.results.textureImages) {
        console.log('textureImages_DB: no results or textureImages');
        return [];
      }
      //print number of texture images in results
      const bands = ['color','green','nir','pca','red','red_edge'];
      const suffixes = [
        'orig','gray','lbp','hog','lac1','lac2','lac3','ehd_map'
      ];
      let dbImages = [];
      console.log('textureImages computed - results:', this.results);
      for (const band of bands) {
        for (const suffix of suffixes) {
          const key = `${band}_${suffix}`;
          if (this.results.textureImages[key]) {
            dbImages.push({
              label: `${this.capitalize(band)} ${suffix.replace(/\d+_/, '').replace('_', ' ').replace('.png','')}`,
              url: this.results.textureImages[key]
            });
          }
        }
      }

      if (dbImages.length > 0) {
        console.log(`textureImages_DB: found ${dbImages.length} images`);
      } else {
        console.log('textureImages_DB: no images found');
      }
      return dbImages;
    },
    
    morphologicalImages() {
      if (!this.results || !this.results.morphologyImages) {
        console.log('morphologicalImages_DB: no results or morphologyImages');
        return [];
      }
      
      console.log('morphologicalImages computed - results:', this.results);
      const backendMap = this.results.morphologyImages || {};

      // Define the expected morphological image types (fixed order/labels)
      const morphologicalImageTypes = [
        'skeleton',
        'branch_pts', 
        'tip_pts',
        'segmented_id',
        'path_lengths',
        'euclidean_lengths',
        'curvature',
        'angles',
        'tangent_angles',
        'insertion_angles',
        'size_analysis',
        'filled_segments',
        'pruned_200',
        'pruned_100',
        'pruned_50',
        'pruned_30',
        'pruned_10'
      ];
      
      // Build only images that the backend actually provided
      const dbImages = morphologicalImageTypes
        .filter(type => backendMap[type])
        .map(type => ({
          label: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          key: type,
          url: backendMap[type],
          loaded: false
        }));
      
      console.log(`morphologicalImages_DB: found ${dbImages.length} morphology images`);
      if (dbImages.length > 0) {
        console.log('morphologicalImages_DB: sample found:', dbImages.slice(0, 5).map(img => img.label));
      } else {
        console.log('morphologicalImages_DB: no morphology images found');
        console.log('morphologicalImages_DB: available keys:', Object.keys(backendMap));
      }
      return dbImages;
    },
    
    vegetationIndicesImages() {
      if (!this.results) {
        console.log('vegetationIndicesImages: no result object');
        return [];
      }
      
      console.log('vegetationIndicesImages computed - result:', this.results);
      const images = this.vegIndexList
        .filter(key => this.results[`vegetation_indices_${key}`])
        .map(key => ({
          label: key.toUpperCase(),
          url: this.results[`vegetation_indices_${key}`]
        }));
      
      console.log(`vegetationIndicesImages: found ${images.length} vegetation indices images`);
      if (images.length > 0) {
        console.log('vegetationIndicesImages: sample indices found:', images.slice(0, 5).map(img => img.label));
      } else {
        console.log('vegetationIndicesImages: no vegetation indices images found');
        console.log('vegetationIndicesImages: checking for vegetation_indices keys in result:', 
          Object.keys(this.results).filter(key => key.startsWith('vegetation_indices_')));
      }
      return images;
    },

    vegetationIndicesImages_DB() {
      if (!this.results || !this.results.vegetationIndicesImages) {
        console.log('vegetationIndicesImages_DB: no results or vegImages');
        return [];
      }
      
      console.log('vegetationIndicesImages computed - results:', this.results);
      const dbImages = this.vegIndexList
        .filter(key => this.results.vegetationIndicesImages[key])
        .map(key => ({
          label: key.toUpperCase(),
          url: this.results.vegetationIndicesImages[key]
        }));
      
      console.log(`vegetationIndicesImages_DB: found ${dbImages.length} vegetation indices images`);
      if (dbImages.length > 0) {
        console.log('vegetationIndicesImages_DB: sample indices found:', dbImages.slice(0, 5).map(img => img.label));
      } else {
        console.log('vegetationIndicesImages: no vegetation indices images found');
        console.log('vegetationIndicesImages: checking for vegetation_indices keys in result:', 
          Object.keys(this.results).filter(key => key.startsWith('vegetation_indices_')));
      }
      return dbImages;
    },
    
    // Table headers for vegetation indices
    vegIndexHeaders() {
      return [
        { text: 'Index', value: 'index' },
        { text: 'Mean', value: 'mean' },
        { text: 'Std', value: 'std' },
        { text: 'Min', value: 'min' },
        { text: 'Max', value: 'max' },
        { text: '25%', value: 'q25' },
        { text: '50%', value: 'median' },
        { text: '75%', value: 'q75' }
      ];
    },
    
    // Table items for vegetation indices
    vegIndexItems() {
      const nested = this.nestedResult;
      if (!nested || !nested.vegetation_features || !Array.isArray(nested.vegetation_features)) return [];
      return nested.vegetation_features;
    },


    
    filteredVegIndexItemsDB() {
      if (!this.results || !this.results.vegetationIndicesTable){
        console.log('filteredVegIndexItemsDB: no vegetationIndicesTable');
        return [];
      }
      
      return this.results.vegetationIndicesTable.map(item => ({
        index: item.index,
        mean: item.mean,
        std: item.std,
        min: item.min,
        max: item.max,
        q25: item.q25,
        median: item.median,
        q75: item.q75
      }));
    },
    // Filtered and sorted vegetation indices
    filteredVegIndexItems() {
      if (!this.results || !this.results.vegetationIndicesTable) {
        return [];
      }
      
      let items = this.results.vegetationIndicesTable;
      
      // Apply search filter
      if (this.vegIndexSearch) {
        const search = this.vegIndexSearch.toLowerCase();
        items = items.filter(item => 
          item.index && item.index.toLowerCase().includes(search)
        );
      }
      
      // Apply sorting
      if (this.sortColumn && this.sortColumn.startsWith('vegIndex_')) {
        const column = this.sortColumn.replace('vegIndex_', '');
        items = [...items].sort((a, b) => {
          const aVal = a[column];
          const bVal = b[column];
          if (this.sortDirection === 'asc') {
            return aVal > bVal ? 1 : -1;
          } else {
            return aVal < bVal ? 1 : -1;
          }
        });
      }
      
      return items;
    },
    
    // Table headers for texture features
    textureHeaders() {
      return [
        { text: 'Feature', value: 'feature' },
        { text: 'Band', value: 'band' },
        { text: 'Texture Type', value: 'texture_type' },
        { text: 'Mean', value: 'mean' },
        { text: 'Std', value: 'std' },
        { text: 'Min', value: 'min' },
        { text: 'Max', value: 'max' },
        { text: '25%', value: 'q25' },
        { text: '50%', value: 'median' },
        { text: '75%', value: 'q75' }
      ];
    },
    
    // Table items for texture features
    textureItems() {
      const nested = this.nestedResult;
      if (!nested || !nested.texture_features || !Array.isArray(nested.texture_features)) return [];
      // Flatten all features for all bands
      return nested.texture_features.flatMap(obj =>
        Object.entries(obj).map(([feature, value]) => ({
          feature: obj.plant_id ? `${obj.plant_id} - ${feature}` : feature,
          value
        }))
      );
    },



    // Method to get texture features table from database
    filteredTextureItemsDB() {
      if (!this.results || !this.results.textureFeaturesTable){
        console.log('filteredTextureItemsDB: no textureFeaturesTable');
        return [];
      }
      
      return this.results.textureFeaturesTable.map(item => ({
        feature: item.feature,
        band: item.band,
        texture_type: item.texture_type,
        mean: item.mean,
        std: item.std,
        min: item.min,
        max: item.max,
        q25: item.q25,
        median: item.median,
        q75: item.q75
      }));
    },
    
    // Filtered and sorted texture features
    filteredTextureItems() {
      if (!this.results || !this.results.textureFeaturesTable) {
        return [];
      }
      
      let items = this.results.textureFeaturesTable;
      
      // Apply search filter
      if (this.textureSearch) {
        const search = this.textureSearch.toLowerCase();
        items = items.filter(item => 
          item.feature && item.feature.toLowerCase().includes(search)
        );
      }
      
      // Apply sorting
      if (this.sortColumn && this.sortColumn.startsWith('texture_')) {
        const column = this.sortColumn.replace('texture_', '');
        items = [...items].sort((a, b) => {
          const aVal = a[column];
          const bVal = b[column];
          if (this.sortDirection === 'asc') {
            return aVal > bVal ? 1 : -1;
          } else {
            return aVal < bVal ? 1 : -1;
          }
        });
      }
      
      return items;
    },
    
    // Table headers for morphology features
    morphHeaders() {
      return [
        { text: 'Feature', value: 'feature' },
        { text: 'Value', value: 'value' },
        { text: 'Unit', value: 'unit' }
      ];
    },
    
    // Table items for morphology features from database
    morphItems() {
      if (!this.results || !this.results.morphologyFeaturesTable) {
        console.log('morphItems: no results or morphologyFeaturesTable');
        return [];
      }
      console.log('morphItems: found morphology data:', this.results.morphologyFeaturesTable);
      return this.results.morphologyFeaturesTable;
    },
    
    // Filtered and sorted morphological features
    filteredMorphItems() {
      if (!this.results || !this.results.morphologyFeaturesTable) {
        console.log('filteredMorphItems: no results or morphologyFeaturesTable');
        return [];
      }
      
      let items = this.results.morphologyFeaturesTable;
      console.log('filteredMorphItems: processing items:', items);

      console.log('filteredMorphItems: items:', items);
      
      // Apply search filter
      if (this.morphSearch) {
        const search = this.morphSearch.toLowerCase();
        items = items.filter(item => 
          item.feature && item.feature.toLowerCase().includes(search)
        );
      }
      
      // Apply sorting
      if (this.sortColumn && this.sortColumn.startsWith('morph_')) {
        const column = this.sortColumn.replace('morph_', '');
        items = [...items].sort((a, b) => {
          const aVal = a[column];
          const bVal = b[column];
          if (this.sortDirection === 'asc') {
            return aVal > bVal ? 1 : -1;
          } else {
            return aVal < bVal ? 1 : -1;
          }
        });
      }
      
      return items;
    },
    

  },
  
  methods: {
    getDisplayText(option) {
      if (!option) return '';
      if (typeof option === 'string' || typeof option === 'number') {
        return option.toString();
      }
      return option.label || option.toString();
    },
    capitalize(s) {
      return s.charAt(0).toUpperCase() + s.slice(1);
    },
    openImageModal(image) {
      this.selectedImage = image;
      this.showModal = true;
    },
    closeImageModal() {
      this.showModal = false;
      this.selectedImage = null;
    },
    sortTable(tableType, column) {
      if (this.sortColumn === `${tableType}_${column}`) {
        this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortColumn = `${tableType}_${column}`;
        this.sortDirection = 'asc';
      }
    },
    formatValue(value) {
      if (typeof value === 'number') {
        return value.toFixed(4);
      }
      return value;
    },
    downloadCSV(type) {
      let headers = [];
      let items = [];
      
      if (type === 'vegIndex') {
        headers = this.vegIndexHeaders.map(h => h.text);
        items = this.filteredVegIndexItems;
      } else if (type === 'texture') {
        headers = this.textureHeaders.map(h => h.text);
        items = this.filteredTextureItems;
      } else if (type === 'morph') {
        headers = this.morphHeaders.map(h => h.text);
        items = this.filteredMorphItems;
      }
      
      const csv = [
        headers.join(','),
        ...items.map(row => 
          headers.map(h => {
            const value = row[h.toLowerCase()];
            return JSON.stringify(value);
          }).join(',')
        )
      ].join('\n');
      
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_table.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    },
    

    // Download a single image
    async downloadImage(image) {
      if (!image || !image.url) {
        console.error('Invalid image object:', image);
        return;
      }

      try {
        // Try to fetch the image as a blob to handle CORS issues
        const response = await fetch(image.url);
        if (!response.ok) {
          throw new Error(`Failed to fetch image: ${response.statusText}`);
        }
        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        
        // Create a temporary anchor element to trigger download
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `${(image.label || 'image').replace(/[^a-zA-Z0-9]/g, '_')}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // Clean up the blob URL
        window.URL.revokeObjectURL(blobUrl);
      } catch (error) {
        console.error('Error downloading image:', error);
        // Fallback: try direct download or open in new tab
        try {
          const a = document.createElement('a');
          a.href = image.url;
          a.download = `${(image.label || 'image').replace(/[^a-zA-Z0-9]/g, '_')}.png`;
          a.target = '_blank';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        } catch (fallbackError) {
          console.error('Fallback download also failed:', fallbackError);
          // Last resort: open in new tab
          window.open(image.url, '_blank');
        }
      }
    },

    // Download all images for the current tab as a zip file
    async downloadAllImages() {
      let images = [];
      let tabName = '';

      // Get images based on active tab
      if (this.activeTab === 0) {
        images = this.mainImages_DB;
        tabName = 'main_images';
      } else if (this.activeTab === 1) {
        images = this.textureImages_DB;
        tabName = 'texture_images';
      } else if (this.activeTab === 2) {
        images = this.vegetationIndicesImages_DB;
        tabName = 'vegetation_indices_images';
      } else if (this.activeTab === 3) {
        images = this.morphologicalImages;
        tabName = 'morphological_images';
      }

      if (images.length === 0) {
        alert('No images available to download.');
        return;
      }

      console.log(`Starting download of ${images.length} images for ${tabName}`);

      try {
        // Extract image URLs
        const imageUrls = images
          .filter(img => img && img.url)
          .map(img => img.url);
        
        if (imageUrls.length === 0) {
          alert('No valid image URLs found.');
          return;
        }

        console.log(`Requesting zip from backend for ${imageUrls.length} images...`);
        
        // Call backend endpoint to create and download zip
        const zipBlob = await downloadImagesZip(imageUrls, tabName);
        
        // Download the zip file
        const url = window.URL.createObjectURL(zipBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${tabName}_${new Date().getTime()}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.log(`✓ Successfully downloaded zip with ${imageUrls.length} images!`);
      } catch (error) {
        console.error('Error downloading zip file:', error);
        alert(`Error downloading images: ${error.message}. Please check the console for details.`);
      }
    },

    async downloadModalImage() {
      if (this.selectedImage && this.selectedImage.url) {
        await this.downloadImage(this.selectedImage);
      }
    },
    
    
    handleImageError(event, imageType) {
      // Handle image loading errors for morphological images
      console.warn(`Failed to load morphological image: ${imageType}`);
      const imgElement = event.target;
      imgElement.style.display = 'none';
      
      // Optionally show a placeholder or error message
      const parent = imgElement.parentElement;
      if (parent) {
        const errorMsg = document.createElement('div');
        errorMsg.className = 'image-error';
        errorMsg.innerHTML = `<p>Image not available: ${imageType}</p>`;
        errorMsg.style.cssText = 'color: #fbbf24; text-align: center; padding: 20px; font-style: italic;';
        parent.appendChild(errorMsg);
      }
    },
    
  },
  
  emits: ['export', 'share']
}
</script>

<style scoped>
.analysis-results {
  padding: 24px;
  position: fixed;
  top: 200px;
  left: 380px;
  width: 76%;
  height: 73%;
  backdrop-filter: blur(30px);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Custom scrollbar styles for the results area */
.analysis-results ::-webkit-scrollbar {
  width: 35px;
}

.analysis-results ::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.26);
  border-radius: 4px;
}

.analysis-results ::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  transition: background 0.3s ease;
}

.analysis-results ::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.705);
}

.analysis-results ::-webkit-scrollbar-corner {
  background: transparent;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.results-title {
  color: white;
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.results-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
  margin-right: -8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) rgba(255, 255, 255, 0.1);
}

.analysis-status {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.status-complete {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-no-results {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

/* No results state */
.no-results {
  text-align: center;
  /* Place the message in the center of the screen */
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.no-results-message h4 {
  color: white;
  font-size: 40px;
  margin-bottom: 16px;
}

.no-results-message p {
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
}

/* Results available */
.results-available {
  padding-bottom: 20px;
}

.results-available > div {
  margin-bottom: 32px;
}

.results-available h4 {
  color: white;
  font-size: 18px;
  margin-bottom: 16px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.results-summary {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.summary-label {
  font-weight: 500;
}

/* Tabs Styles */
.tabs-container {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.tabs-header {
  display: flex;
  background: rgba(255, 255, 255, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  justify-content: center;
  overflow-x: auto;
}

.sticky-tabs {
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.15);
}

.tab-button {
  padding: 12px 20px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  font-size: 15px;
  font-weight: 800;
  white-space: nowrap;
  transition: all 0.2s ease;
  border-bottom: 2px solid transparent;
}

.tab-button:hover {
  color: white;
  background: rgba(255, 255, 255, 0.05);
}

.tab-button.active {
  color: white;
  background: rgba(255, 255, 255, 0.1);
  border-bottom-color: #4ade80;
}

.tab-content {
  padding: 20px;
}

.tab-panel {
  min-height: 400px;
}

/* Image grid styles */
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

/* Image Tab Header */
.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.tab-header h3 {
  color: white;
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

/* Download All Images Button */
.download-all-btn {
  padding: 8px 16px;
  background: #000000;
  color: #ffffff;
  border: 1px solid #000000;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.download-all-btn:hover {
  background: #333333;
  border-color: #333333;
}

.image-item {
  background: rgba(0, 0, 0, 0.25);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
}

.image-title {
  color: white;
  margin-top: 12px;
  margin-bottom: 0px;
  font-size: 16px;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: rgb(255, 255, 255);
  text-underline-offset: 8px;
  text-decoration-thickness: 4px;
  display: inline-block;
  width: fit-content;
  margin-left: auto;
  margin-right: auto;
}

.result-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.result-image.clickable {
  cursor: pointer;
}

.result-image.clickable:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.no-images-message {
  text-align: center;
  padding: 40px 20px;
  color: white;
}

.no-images-message h4 {
  font-size: 20px;
  margin-bottom: 16px;
  color: #fbbf24;
}

.no-images-message p {
  margin-bottom: 12px;
  line-height: 1.5;
}

.no-images-message strong {
  color: #4ade80;
}

.no-image-placeholder {
  background: rgba(255, 255, 255, 0.05);
  border: 2px dashed rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-image-placeholder p {
  margin: 0;
  font-style: italic;
}

/* Table Controls */
.table-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 14px;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.6);
}

/* Download Button - Black background with white text */
.download-btn {
  padding: 8px 16px;
  background: #000000;
  color: #ffffff;
  border: 1px solid #000000;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.download-btn:hover {
  background: #333333;
  border-color: #333333;
}

/* Table Styles - Professional design */
.table-container {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
}

.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  color: white;
  font-size: 14px;
  font-weight: bold;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.data-table th { 
  background: #500000;
  padding: 16px 12px;
  text-align: center;
  font-weight: bold;
  font-size: 15px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  border-bottom: 2px solid rgba(255, 255, 255, 0.3);
  position: relative;
  white-space: nowrap;
  color: white;
}

.data-table th:not(:last-child) {
  border-right: 1px solid rgba(0, 31, 63, 0.5);
}

.data-table td {
  padding: 14px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: bold;
  font-size: 14px;
  text-align: center;
  transition: all 0.2s ease;
  color: white;
}

.data-table td:not(:last-child) {
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.data-table tbody tr {
  transition: all 0.2s ease;
}

.data-table tbody tr:nth-child(even) {
  background: rgba(0, 0, 0, 0.3);
}

.data-table tbody tr:nth-child(odd) {
  background: rgba(0, 0, 0, 0.25);
}

.data-table tbody tr:hover {
  background: rgba(0, 0, 0, 0.4);
  transform: scale(1.001);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.data-table tbody tr:hover td {
  color: rgba(255, 255, 255, 0.95);
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.sortable-header {
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
  text-align: center;
  position: relative;
}

.sortable-header:hover {
  background: #003366;
}

.sortable-header:active {
  transform: scale(0.98);
}

.sort-indicator {
  margin-left: 6px;
  font-weight: bold;
  color: #4ade80;
  font-size: 12px;
  display: inline-block;
  transition: transform 0.2s ease;
}

.no-data-message {
  text-align: center;
  padding: 40px 20px;
  color: white;
}

.no-data-message h4 {
  font-size: 20px;
  margin-bottom: 16px;
  color: #fbbf24;
}

.no-data-message p {
  margin-bottom: 12px;
  line-height: 1.5;
}

/* Image Modal Styles */
.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(10px);
}

.modal-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.modal-header {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 10px;
  z-index: 10;
}

.modal-close {
  background: #000000;
  border: none;
  color: #ffffff;
  font-size: 20px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
  font-weight: bold;
}

.modal-close:hover {
  background: #333333;
}

.modal-download {
  background: #000000;
  border: none;
  color: #ffffff;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
}

.modal-download:hover {
  background: #333333;
}

.modal-image {
  max-width: 100%;
  max-height: 55vh;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.modal-title {
  color: #000000;
  margin-top: 16px;
  font-size: 24px;
  font-weight: 600;
}

/* Timeline Configuration Styles */
.timeline-config {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 24px;
  margin-top: 20px;
}

.config-section {
  margin-bottom: 24px;
}

.config-section:last-child {
  margin-bottom: 0;
}

.config-label {
  display: block;
  color: white;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.config-select {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 14px;
  transition: all 0.2s ease;
}

.config-select:focus {
  outline: none;
  border-color: #4ade80;
  background: rgba(255, 255, 255, 0.15);
}

.config-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.config-select option {
  background: #333;
  color: white;
}

.display-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: #4ade80;
}

.number-input-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.number-input-group label {
  color: white;
  font-size: 14px;
  white-space: nowrap;
}

.number-input {
  width: 80px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 14px;
  text-align: center;
}

.number-input:focus {
  outline: none;
  border-color: #4ade80;
}

.number-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.generate-chart-btn {
  width: 100%;
  padding: 16px;
  background: #4ade80;
  color: #000000;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  text-shadow: none;
}

.generate-chart-btn:hover:not(:disabled) {
  background: #22c55e;
  transform: translateY(-1px);
}

.generate-chart-btn:disabled {
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.5);
  cursor: not-allowed;
  transform: none;
}

/* Morphological Images Loading and Error States */
.image-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: rgba(255, 255, 255, 0.7);
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.image-error {
  color: #fbbf24;
  text-align: center;
  padding: 20px;
  font-style: italic;
  background: rgba(251, 191, 36, 0.1);
  border-radius: 8px;
  margin-top: 10px;
}

.image-error p {
  margin: 0;
  font-size: 14px;
}

/* Charts Tab Styles */
.charts-tab {
  color: white;
}

.charts-container {
  padding: 20px 0;
}

.charts-section {
  margin-bottom: 60px;
}

.charts-section:last-child {
  margin-bottom: 0;
}

.section-title {
  color: white;
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 30px;
  text-align: center;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  border-bottom: 3px solid rgba(255, 255, 255, 0.3);
  padding-bottom: 15px;
}

.correlation-charts {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 30px;
  margin-top: 30px;
}

.chart-item {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  max-width: 300px;  /* Increased from 500px - adjust as needed */
  flex: 1 1 450px;    /* Increased from 400px - adjust as needed */
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.chart-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
}

.chart-title {
  color: white;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 15px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.chart-image {
  max-width: 75%;
  width: 550px;        /* Fixed width for correlation charts - adjust as needed */
  height: auto;         /* Maintains aspect ratio */
  border-radius: 8px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.chart-image.clickable {
  cursor: pointer;
}

.chart-image.clickable:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

.remaining-plots {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));  /* Increased from 300px - adjust as needed */
  gap: 25px;
  margin-top: 30px;
}

.plot-item {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.plot-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
}

.plot-title {
  color: white;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.plot-image {
  max-width: 100%;
  width: 450px;         /* Fixed width for remaining plots - adjust as needed */
  height: auto;         /* Maintains aspect ratio */
  border-radius: 8px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.plot-image.clickable {
  cursor: pointer;
}

.plot-image.clickable:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

/* Responsive design */
@media (max-width: 1200px) {
  .image-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .plot-image {
    width: 100%;
    max-width: 400px;
  }
}

@media (max-width: 1024px) {
  .tabs-header {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .tab-button {
    font-size: 13px;
    padding: 10px 16px;
  }
  
  .image-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  
  .image-item {
    padding: 12px;
  }
  
  .image-title {
    font-size: 13px;
  }
  
  .plot-image {
    width: 100%;
    max-width: 350px;
  }
}

@media (max-width: 768px) {
  .tabs-container {
    margin-bottom: 20px;
  }
  
  .tabs-header {
    gap: 6px;
  }
  
  .tab-button {
    font-size: 12px;
    padding: 8px 12px;
    flex: 1;
    min-width: 0;
  }
  
  .tab-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .tab-header h3 {
    font-size: 18px;
  }
  
  .download-all-btn {
    width: 100%;
    font-size: 13px;
    padding: 10px 16px;
  }
  
  .image-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .image-item {
    padding: 10px;
  }
  
  .result-image {
    width: 100%;
    height: auto;
  }
  
  .image-title {
    font-size: 12px;
  }
  
  .plot-image {
    width: 100%;
    max-width: 100%;
  }
  
  .modal-content {
    max-width: 95%;
    padding: 20px;
  }
  
  .modal-image {
    max-width: 100%;
    max-height: 70vh;
  }
  
  .modal-title {
    font-size: 16px;
  }
}

@media (max-width: 480px) {
  .tabs-header {
    gap: 4px;
  }
  
  .tab-button {
    font-size: 11px;
    padding: 6px 10px;
  }
  
  .tab-header h3 {
    font-size: 16px;
  }
  
  .download-all-btn {
    font-size: 12px;
    padding: 8px 14px;
  }
  
  .image-grid {
    gap: 12px;
  }
  
  .image-item {
    padding: 8px;
  }
  
  .image-title {
    font-size: 11px;
  }
  
  .no-images-message h4 {
    font-size: 16px;
  }
  
  .no-images-message p {
    font-size: 13px;
  }
  
  .modal-content {
    max-width: 98%;
    padding: 15px;
  }
  
  .modal-image {
    max-height: 60vh;
  }
  
  .modal-title {
    font-size: 14px;
  }
  
  .close-modal {
    font-size: 28px;
    top: 10px;
    right: 10px;
  }
  
  .plot-image {
    width: 100%;
  }
  
  .plot-title {
    font-size: 14px;
  }
}
</style>
