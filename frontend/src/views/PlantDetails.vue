<template>
  <div id="plant-details">
    <!-- Background layers -->
    <div class="background-container">

      <!-- Gradient overlay -->
      <div
        class="gradient-overlay"
        :style="gradientStyle"
      ></div>
    </div>

    <!-- Content -->
    <div class="app-content">
      <AppHeader :whiteBars="[
        { width: 2216, height: 15, x: -10, y: 175, opacity: 0.8 },
        { width: 15, height: 750, x: 350, y: 200, opacity: 0.8 }]"
      />

      <main class="content">
        <!-- Main content layout with left sidebar -->
        <div class="content-layout">
          <!-- Parameters Section - Left Side -->
          <div class="parameters-section">
            <!-- Back Button -->
            <div class="back-button-container">
              <button @click="goBack" class="back-button-icon" title="Back to Selection">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M19 12H5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M12 19L5 12L12 5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
            <h3 class="parameters-title">Analysis Parameters</h3>

            <!-- Plant ID Selection -->
            <div class="parameter-group">
              <ConfigurableDropdown
                v-model="selectedPlantId"                
                :options="plantIdOptions"
                :display-text="isLoadingPlants ? 'Loading plants...' : plantIdDisplayText"
                label="Plant ID"
                placeholder="Select Plant ID"
                size="small"
                :searchable="true"
                :disabled="isLoadingPlants"
                @change="handlePlantIdChange"
                class="dropdown"
              />
            </div>

            <!-- Date Selection -->
            <div class="parameter-group">
              <ConfigurableDropdown
                v-model="selectedDate"
                :options="dateOptions"
                :display-text="isLoadingDates ? 'Loading dates...' : dateDisplayText"
                label="Analysis Date"
                placeholder="Select Date"
                size="small"
                :disabled="!selectedPlantId || isLoadingDates"
                :searchable="true"
                @change="handleDateChange"
                class="dropdown"
              />
            </div>

            <!-- Segmentation Method Selection -->
            <!-- <div class="parameter-group">
              <label class="parameter-label">Segmentation Method</label>
              <select 
                v-model="segmentationMethod" 
                class="segmentation-select"
                :disabled="!selectedDate"
              >
                <option value="sam3">SAM3 (Default)</option>
                <option value="rmbg">RMBG-2.0</option>
              </select>
              <p class="method-hint">
                <strong>SAM3</strong>: Advanced segmentation (recommended for sorghum)<br>
                <strong>RMBG-2.0</strong>: Legacy background removal
              </p>
            </div> -->

            <!-- Back Button -->
            <!-- <ConfigurableButton
                text="← Back to Selection"
                variant="secondary"
                size="medium"
                @click="goBack"
                class="back-button"
              /> -->

            <!-- Analysis Button -->
            <div class="parameter-group">
              <ConfigurableButton
                text="Start Analysis"
                variant="primary"
                size="medium"
                :disabled="!canStartAnalysis"
                @click="handleAnalyzeClick"
                class="analyze-button"
              />
            </div>

            <!-- Reset Button -->
            <div class="parameter-group">
              <ConfigurableButton
                text="Reset Parameters"
                variant="outline"
                size="medium"
                @click="resetParameters"
                class="reset-button"
              />
            </div>


            <!-- Status Display -->
            <div class="status-area">
              <div v-if="!selectedPlantId" class="status-message">
                <h3>Step 1: Select Plant ID</h3>
                <p>Choose a Plant ID from the parameters panel to begin analysis.</p>
              </div>

              <div v-else-if="!selectedDate" class="status-message">
                <h3>Step 2: Select Analysis Date</h3>
                <p>Plant ID <strong>{{ getDisplayText(selectedPlantId) }}</strong> selected. Now choose an analysis date.</p>
              </div>

              <div v-else class="status-message">
                <!-- Loading Progress Indicator -->
                <div v-if="isAnalyzing" class="loading-section">
                  <h3>Analysis in Progress...</h3>
                  <div class="progress-container">
                    <div class="progress-bar">
                      <div class="progress-fill" :style="{ width: analysisProgress + '%' }"></div>
                    </div>
                    <div class="progress-text">{{ Math.round(analysisProgress) }}%</div>
                  </div>
                  <p>Please wait while we process your data...</p>
                </div>
                
                <!-- Analysis Results Status -->
                <div v-else>
                  <h3 v-if="results">Analysis Successful</h3>
                  <h3 v-else-if="analysisFailed">Analysis Failed, Please try again</h3>
                  <h3 v-else>Ready for Analysis</h3>
                  <div class="config-summary">
                    <div class="config-item">
                      <strong>Plant Species:</strong> {{ species }}
                    </div>
                    <div class="config-item">
                      <strong>Plant ID:</strong> {{ getDisplayText(selectedPlantId) }}
                    </div>
                    <div class="config-item">
                      <strong>Date:</strong> {{ getDisplayText(selectedDate) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Main Content Area - Right Side -->
          <div class="main-content-area">
            <div class="content-header">
              <!-- <h1 class="title">{{ species }}</h1>
              <h2 class="subtitle">Plant Analysis Dashboard</h2> -->
              
            </div>

            <!-- Analysis Results Component -->
            <AnalysisResults
              :plant-name="species"
              :plant-id="selectedPlantId"
              :species="species"
              :analysis-date="selectedDate"
              :has-started-analysis="hasStartedAnalysis"
              :is-analyzing="isAnalyzing"
              :analysis-progress="analysisProgress"
              :results="results"
              :show-charts="true"
              title="Phenotyping Analysis Results"
              @export="handleExport"
              @share="handleShare"
              class = "analysis-results"
            />
          </div>
        </div> 
      </main>
      
    </div>
  </div>
</template>

<script>
import AppHeader from '../components/AppHeader.vue'
// import backgroundImage from '@/assets/greenhouse-img2.jpg'
import ConfigurableButton from '../components/ConfigurableButton.vue'
import ConfigurableDropdown from '@/components/ConfigurableDropdown.vue';
import AnalysisResults from '../components/AnalysisResults.vue'
import { getPlantResults, analyzePlant, getDatabaseData, getAvailablePlants } from '@/api.js'
import axios from 'axios'

// Use environment variable for API base URL, fallback to localhost for development
const API_BASE = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api';

export default {
  name: 'PlantDetails',
  components: {
    AppHeader,
    ConfigurableDropdown,
    ConfigurableButton,
    AnalysisResults
  },
  data() {
    return {
      species: this.$route.params.speciesName,
      // Background configuration
      // backgroundImage: backgroundImage,
      // backgroundImageOpacity: 0.90,

      // Gradient configuration
      gradientTopColor: '#08B6E0',
      gradientBottomColor: '#05AF6B',
      gradientOpacity: 1.0,

      // Form data
      selectedPlantId: null,
      selectedDate: null,
      segmentationMethod: 'sam3', // Default segmentation method

      // Analysis state
      hasStartedAnalysis: false,
      isAnalyzing: false,
      analysisProgress: 0,
      results: null,
      analysisFailed: false,

      // Options data - will be populated from database
      plantIdOptions: [],
      dateOptions: [],
      
      // Loading states
      isLoadingPlants: false,
      isLoadingDates: false
     
    };
  },
  
  async mounted() {
    // console.log('PlantDetails: mounted, backgroundImage:', this.backgroundImage);
    
    // For Mullet, sync plants from S3 first to ensure they're in the database
    if (this.species.toLowerCase() === 'mullet') {
      try {
        await axios.post(`${API_BASE}/sync-plants-from-s3/Mullet?date=2025-10-24`);
        console.log('Synced Mullet plants from S3');
      } catch (error) {
        console.warn('Failed to sync Mullet plants from S3:', error);
        // Continue anyway - plants might already exist
      }
    }
    
    await this.loadPlantData();
    
    // Check for query parameters to auto-select plant and date
    if (this.$route.query.plantId) {
      const plantIdValue = this.$route.query.plantId;
      // Find matching plant option
      const plantOption = this.plantIdOptions.find(opt => opt.value === plantIdValue);
      if (plantOption) {
        this.selectedPlantId = plantOption;
        // Load dates for this plant (loadDateOptions expects an object with value property)
        await this.loadDateOptions(plantOption);
        
        // Set date if provided
        if (this.$route.query.date) {
          const dateValue = this.$route.query.date;
          const dateOption = this.dateOptions.find(opt => opt.value === dateValue);
          if (dateOption) {
            this.selectedDate = dateOption;
            // Automatically trigger analysis after a short delay to ensure UI is ready
            this.$nextTick(() => {
              setTimeout(() => {
                this.handleAnalyzeClick();
              }, 500);
            });
          }
        }
      }
    }
  },
  
  computed: {
    // backgroundImageStyle() {
    //   if (!this.backgroundImage) {
    //     console.warn('PlantDetails: backgroundImage is not set');
    //     return {};
    //   }

    //   const style = {
    //     backgroundImage: `url(${this.backgroundImage})`,
    //     opacity: this.backgroundImageOpacity
    //   };
    //   console.log('PlantDetails: backgroundImageStyle', style);
    //   return style;
    // },

    gradientStyle() {
      const topColor = this.hexToRgba(this.gradientTopColor, this.gradientOpacity);
      const bottomColor = this.hexToRgba(this.gradientBottomColor, this.gradientOpacity);

      return {
        background: `linear-gradient(to bottom, ${topColor}, ${bottomColor})`
      };
    },

    canStartAnalysis() {
      return this.selectedPlantId && this.selectedDate;
    },

    plantIdDisplayText() {
      if (!this.selectedPlantId) return "Select a Plant ID";
      
      // Find the option that matches the selected value
      const selectedOption = this.plantIdOptions.find(option => 
        option.value === this.selectedPlantId
      );
      
      return selectedOption ? selectedOption.label : this.selectedPlantId.label;
    },
    
    dateDisplayText() {
      if (!this.selectedDate) return "Select a Date";
      
      // Find the option that matches the selected value
      const selectedOption = this.dateOptions.find(option => 
        option.value === this.selectedDate
      );
      
      return selectedOption ? selectedOption.label : this.selectedDate.label;
    }
  },
  methods: {
    async loadPlantData() {
      try {
        this.isLoadingPlants = true;
        const data = await getAvailablePlants();
        if(data){
          console.log("Data is loaded");
        }
        
        // Find plants for the current species
        const speciesPlants = data.plants_by_species[this.species] || [];
        
        // Convert to dropdown options format and ensure numerical sorting
        this.plantIdOptions = speciesPlants.map(plant => {
          // Extract just the number from the plant ID (e.g., "plant1" -> "1")
          const plantNumber = plant.id.replace(/\D/g, '');
          return {
            label: `Plant ${plantNumber}`,
            value: plant.id
          };
        }).sort((a, b) => {
          // Extract numbers from plant IDs for numerical sorting
          const aNum = parseInt(a.value.replace(/\D/g, '')) || 0;
          const bNum = parseInt(b.value.replace(/\D/g, '')) || 0;
          return aNum - bNum;
        });
        
        console.log(`Loaded ${this.plantIdOptions.length} plants for species ${this.species}`, speciesPlants);
        
      } catch (error) {
        console.error('Error loading plant data:', error);
        
      } finally {
        this.isLoadingPlants = false;
      }
    },
    
    async loadDateOptions(plantId) {
      if (!plantId) {
        this.dateOptions = [];
        return;
      }
      
      try {
        this.isLoadingDates = true;
        const data = await getAvailablePlants();
        
        // Find the specific plant
        const speciesPlants = data.plants_by_species[this.species] || [];
        const plant = speciesPlants.find(p => p.id === plantId.value);
        
        if (plant && plant.dates_captured) {
          this.dateOptions = plant.dates_captured
            .sort((a, b) => new Date(a) - new Date(b)) // Sort dates chronologically
            .map(date => ({
              label: date,
              value: date
            }));
        } else {
          this.dateOptions = [];
        }
        
        console.log(`Loaded ${this.dateOptions.length} dates for ${plantId}`);
        
      } catch (error) {
        console.error('Error loading date options:', error);
        // Fallback to default dates if API fails
        this.dateOptions = [
          { label: '2024-12-04', value: '2024-12-04' },
          { label: '2024-12-10', value: '2024-12-10' },
          { label: '2024-12-16', value: '2024-12-16' },
          { label: '2025-01-13', value: '2025-01-13' },
          { label: '2025-01-24', value: '2025-01-24' },
          { label: '2025-01-31', value: '2025-01-31' },
          { label: '2025-02-05', value: '2025-02-05' },
          { label: '2025-02-14', value: '2025-02-14' },
          { label: '2025-03-03', value: '2025-03-03' },
          { label: '2025-03-12', value: '2025-03-12' },
          { label: '2025-03-24', value: '2025-03-24' },
          { label: '2025-04-01', value: '2025-04-01' },
          { label: '2025-04-15', value: '2025-04-15' },
          { label: '2025-04-16', value: '2025-04-16' },
          { label: '2025-04-17', value: '2025-04-17' },
          { label: '2025-04-21', value: '2025-04-21' }
        ];
      } finally {
        this.isLoadingDates = false;
      }
    },
    
    goBack() {
      // Navigate back to home page using router
      this.$router.push({ name: 'HomePage' });
    },

    async handlePlantIdChange(plantId) {
      console.log('Plant ID changed to:', plantId);
      // Update the selected plant ID
      this.selectedPlantId = plantId;
      // Clear date selection when plant ID changes
      this.selectedDate = null;
      this.results = null;
      
      // Load available dates for the selected plant
      await this.loadDateOptions(plantId);
    },

    handleDateChange(date) {
      this.selectedDate = date; 
      this.results = null;
      console.log('Date changed to:', date);

    },

    handleAnalyzeClick() {
      if (this.canStartAnalysis) {
        console.log('Starting analysis for:', {
          species: this.species,
          plantId: this.selectedPlantId,
          date: this.selectedDate,
          segmentationMethod: this.segmentationMethod
        });

        // Start the analysis process
        this.hasStartedAnalysis = true;
        this.isAnalyzing = true;
        this.analysisProgress = 0;
        this.results = null;
        this.analysisFailed = false;
        
        // For Mullet (and other species that need pipeline processing), trigger pipeline first
        // Then fetch results after processing completes
        if (this.species.toLowerCase() === 'mullet') {
          this.processAndFetchResults(this.species, this.selectedPlantId.value, this.selectedDate.value, this.segmentationMethod);
        } else {
          // For other species, just fetch from database
          this.fetchDatabaseData(this.species, this.selectedPlantId.value, this.selectedDate.value);
        }
      }
    },

  async processAndFetchResults(species, plantId, date, segmentationMethod) {
    this.isAnalyzing = true;
    this.analysisProgress = 10;
    this.analysisFailed = false;
    console.log('processAndFetchResults: Processing and fetching results for', species, plantId, date);
    
    try {
      // Step 1: Trigger pipeline analysis with selected segmentation method
      this.analysisProgress = 20;
      console.log('Triggering pipeline analysis with segmentation method:', segmentationMethod);
      const analysisResponse = await analyzePlant(species, plantId, date, segmentationMethod);
      
      if (analysisResponse && analysisResponse.task_id) {
        // Step 2: Poll for task completion
        this.analysisProgress = 30;
        console.log('Pipeline task started, task_id:', analysisResponse.task_id);
        
        // Poll for task status
        const maxAttempts = 300; // 5 minutes max (1 second intervals) - pipeline can take time
        let attempts = 0;
        
        const pollInterval = setInterval(async () => {
          attempts++;
          try {
            const statusResponse = await axios.get(`${API_BASE}/task-status/${analysisResponse.task_id}`);
            const status = statusResponse.data.status;
            
            // Update progress (30% to 90%)
            this.analysisProgress = 30 + Math.min(60, (attempts / maxAttempts) * 60);
            
            if (status === 'SUCCESS') {
              clearInterval(pollInterval);
              this.analysisProgress = 90;
              
              // Step 3: Wait a bit for database to be updated, then fetch results
              console.log('Pipeline completed, fetching results from database...');
              await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
              
              const result = await getDatabaseData(species, plantId, date);
              
              if (result) {
                this.results = result;
                this.analysisProgress = 100;
                this.isAnalyzing = false;
                this.analysisFailed = false;
                console.log('Successfully processed and fetched results for', species, plantId, date);
              } else {
                // If no results in DB yet, try again after a longer wait
                console.log('Results not in database yet, waiting longer...');
                await new Promise(resolve => setTimeout(resolve, 5000));
                const retryResult = await getDatabaseData(species, plantId, date);
                if (retryResult) {
                  this.results = retryResult;
                  this.analysisProgress = 100;
                  this.isAnalyzing = false;
                  this.analysisFailed = false;
                } else {
                  throw new Error('Pipeline completed but results not found in database');
                }
              }
            } else if (status === 'FAILURE') {
              clearInterval(pollInterval);
              this.isAnalyzing = false;
              this.analysisFailed = true;
              this.analysisProgress = 0;
              console.error('Pipeline analysis failed');
              alert('Analysis failed. Please try again.');
            } else if (attempts >= maxAttempts) {
              clearInterval(pollInterval);
              this.isAnalyzing = false;
              this.analysisFailed = true;
              this.analysisProgress = 0;
              console.error('Pipeline analysis timeout');
              alert('Analysis is taking too long. Please check back later.');
            }
          } catch (error) {
            console.error('Error polling task status:', error);
            if (attempts >= maxAttempts) {
              clearInterval(pollInterval);
              this.isAnalyzing = false;
              this.analysisFailed = true;
              this.analysisProgress = 0;
            }
          }
        }, 1000); // Poll every second
      } else {
        throw new Error('Failed to start pipeline analysis task');
      }
    } catch (error) {
      console.error('Error in processAndFetchResults:', error);
      this.isAnalyzing = false;
      this.analysisFailed = true;
      this.analysisProgress = 0;
      alert('Failed to start analysis. Please try again.');
    }
  },

  async reRunAnalysisWithSegmentation(species, plantId, date, segmentationMethod) {
    this.isAnalyzing = true;
    this.analysisProgress = 10;
    this.analysisFailed = false;
    console.log('reRunAnalysisWithSegmentation: Starting analysis with', segmentationMethod, 'for', species, plantId, date);
    
    try {
      // Step 1: Trigger analysis with selected segmentation method
      this.analysisProgress = 20;
      console.log('Triggering analysis with segmentation method:', segmentationMethod);
      const analysisResponse = await analyzePlant(species, plantId, date, segmentationMethod);
      
      if (analysisResponse && analysisResponse.task_id) {
        // Step 2: Poll for task completion
        this.analysisProgress = 30;
        console.log('Analysis task started, task_id:', analysisResponse.task_id);
        
        // Poll for task status
        const maxAttempts = 120; // 2 minutes max (1 second intervals)
        let attempts = 0;
        
        const pollInterval = setInterval(async () => {
          attempts++;
          try {
            const statusResponse = await axios.get(`${API_BASE}/task-status/${analysisResponse.task_id}`);
            const status = statusResponse.data.status;
            
            // Update progress (30% to 90%)
            this.analysisProgress = 30 + Math.min(60, (attempts / maxAttempts) * 60);
            
            if (status === 'SUCCESS') {
              clearInterval(pollInterval);
              this.analysisProgress = 90;
              
              // Step 3: Fetch results from database after analysis completes
              console.log('Analysis completed, fetching results from database...');
              const result = await getDatabaseData(species, plantId, date);
              
              if (result) {
                this.results = result;
                this.analysisProgress = 100;
                this.isAnalyzing = false;
                this.analysisFailed = false;
                console.log('Analysis succeeded with', segmentationMethod, 'segmentation method');
              } else {
                throw new Error('Analysis completed but no results found in database');
              }
            } else if (status === 'FAILURE') {
              clearInterval(pollInterval);
              this.isAnalyzing = false;
              this.analysisFailed = true;
              this.analysisProgress = 0;
              console.error('Analysis failed');
              alert('Analysis failed. Please try again.');
            } else if (attempts >= maxAttempts) {
              clearInterval(pollInterval);
              this.isAnalyzing = false;
              this.analysisFailed = true;
              this.analysisProgress = 0;
              console.error('Analysis timeout');
              alert('Analysis is taking too long. Please check back later.');
            }
          } catch (error) {
            console.error('Error polling task status:', error);
            if (attempts >= maxAttempts) {
              clearInterval(pollInterval);
              this.isAnalyzing = false;
              this.analysisFailed = true;
              this.analysisProgress = 0;
            }
          }
        }, 1000); // Poll every second
      } else {
        throw new Error('Failed to start analysis task');
      }
    } catch (error) {
      console.error('Error in reRunAnalysisWithSegmentation:', error);
      this.isAnalyzing = false;
      this.analysisFailed = true;
      this.analysisProgress = 0;
      alert('Failed to start analysis. Please try again.');
    }
  },

  async fetchDatabaseData(species, plantId, date) {
    this.isAnalyzing = true;
    this.analysisProgress = 0;
    this.analysisFailed = false;
    console.log('fetchDatabaseData: started for', species, plantId, date);
    
    const result = await getDatabaseData(species, plantId, date);
    
    // ADD THESE DEBUG LINES
    console.log('=== DEBUG: Full API Response ===');
    console.log('Result object:', result);
    console.log('Result keys:', Object.keys(result || {}));
    console.log('Morphology table:', result?.morphologyFeaturesTable);
    console.log('Morphology table length:', result?.morphologyFeaturesTable?.length);
    console.log('Morphology table type:', typeof result?.morphologyFeaturesTable);
    console.log('=== END DEBUG ===');
    
    if (result){
      this.results = result;
      this.analysisProgress = 100;
      this.isAnalyzing = false;
      this.analysisFailed = false;
      console.log('fetchDatabaseData: Analysis succeeded, results fetched from DATABASE.');
    }
},

    async fetchResults(species, plantId, date) {
      this.isAnalyzing = true;
      this.analysisProgress = 0;
      this.analysisFailed = false;
      console.log('fetchResults: started for', species, plantId, date);
      try {
        const result = await getPlantResults(species, plantId, date);
        if (result && result.error) {
          console.error('fetchResults: Analysis failed:', result.error);
          this.isAnalyzing = false;
          this.analysisProgress = 0;
          this.analysisFailed = true;
          alert(result.error);
          return;
        }
        this.results = result;
        this.analysisProgress = 100;
        this.isAnalyzing = false;
        this.analysisFailed = false;
        console.log('fetchResults: Analysis succeeded, results fetched from backend.');
      } catch (e) {
        if (e.response && e.response.status === 404) {
          try {
            console.log('fetchResults: No results found, triggering analysis...');
            await analyzePlant(species, plantId, date);
            this.results = await getPlantResults(species, plantId, date);
            this.analysisProgress = 100;
            this.isAnalyzing = false;
            this.analysisFailed = false;
            console.log('fetchResults: Analysis triggered and results fetched.');
          } catch (analysisError) {
            console.error('fetchResults: Analysis failed after triggering:', analysisError);
            this.isAnalyzing = false;
            this.analysisProgress = 0;
            this.analysisFailed = true;
            alert('Failed to analyze plant. Please try again later.');
          }
        } else {
          console.error('fetchResults: Failed to load results:', e);
          this.isAnalyzing = false;
          this.analysisProgress = 0;
          this.analysisFailed = true;
          alert('Error loading results. Please try again later.');
        }
      }
    },

    pollForResult(species, plantId, date) {
      this.analysisProgress = 10;
      let progress = 10;
      const poll = setInterval(async () => {
        try {
          const result = await getPlantResults(species, plantId, date);
          if (result) {
            this.results = result;
            progress += Math.random() * 20 + 10;
            this.analysisProgress = Math.min(progress, 95);
            if (this.allResultsReady(result)) {
              this.analysisProgress = 100;
              this.isAnalyzing = false;
              clearInterval(poll);
              console.log('Analysis succeeded: Results are now ready.');
            }
          }
        } catch (e) {
          // Still processing, keep polling
        }
      }, 3000);
    },

    allResultsReady(result) {
      // Check for main images
      const mainImages = ['original', 'mask', 'overlay', 'segmented'];
      const allMainImages = mainImages.every(k => result && result[k]);
      // Check for at least one vegetation index image
      const vegIndexKeys = [
        'ndvi', 'gndvi', 'evi2', 'ndre', 'ndwi', 'ngrdi', 'ari', 'ari2', 'avi', 'ccci', 
        'cigreen', 'cire', 'cvi', 'dswi4', 'dvi', 'exr', 'gemi', 'gosavi', 'grndvi', 
        'grvi', 'gsavi', 'ipvi', 'lci', 'mcari', 'mcari1', 'mcari2', 'mgrvi', 'msavi', 
        'msr', 'mtvi1', 'mtvi2', 'nli', 'osavi', 'pvi', 'rdvi', 'ri', 'rri1', 'sipi2', 
        'sr', 'tcari', 'tcariosavi', 'tndvi', 'tsavi', 'wdvi'
      ];
      const allVegIndices = vegIndexKeys.some(name => result && result[`vegetation_indices_${name}`]);
      // Check for morphology features
      const morph = result && result.morphology_features;
      const hasMorph = morph && Object.keys(morph).length > 0;
      return allMainImages && allVegIndices && hasMorph;
    },

    resetParameters() {
      this.selectedPlantId = null;
      this.selectedDate = null;
      this.species = null;
      this.hasStartedAnalysis = false;
      this.isAnalyzing = false;
      this.analysisProgress = 0;
      this.results = null;
      this.analysisFailed = false;
      console.log('Parameters reset');
    },

    handleExport(exportData) {
      console.log('Export requested:', exportData);
      // Implement export logic here
      if (exportData.type === 'csv') {
        alert('CSV export would be implemented here');
      } else if (exportData.type === 'pdf') {
        alert('PDF export would be implemented here');
      }
    },

    handleShare(data) {
      console.log('Share requested:', data);
      // Implement sharing logic here
      alert('Sharing functionality would be implemented here');
    },

    getDisplayText(option) {
      if (!option) return '';

      if (typeof option === 'string' || typeof option === 'number') {
        return option.toString();
      }

      return option.label || option.toString();
    },

    // Helper method to convert hex color to rgba with opacity
    hexToRgba(hex, opacity) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }
  }
}
</script>

<style>
/* Global styles - allow scrolling for PlantDetails */
html, body {
  overflow: auto;
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}

/* Styled scrollbars for webkit browsers */
::-webkit-scrollbar {
  width: 10px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* Styled scrollbars for Firefox */
html {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) rgba(0, 0, 0, 0.1);
}
</style>

<style scoped>

#plant-details {
  font-family: Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  position: relative;
  height: 100vh;
  width: 100vw;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Background container that covers the entire screen */
.background-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
}

/* Background image layer */
.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-attachment: fixed;
}

/* Gradient overlay */
.gradient-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* Content container */
.app-content {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;
}

.content {
  width: 100%;
  max-width: 1400px;
  padding-top: 120px;
}

/* Main layout with left sidebar */
.content-layout {
  display: flex;
  gap: 30px;
  min-height: calc(100vh - 200px);
  align-items: flex-start;
}

/* Parameters Section - Left Sidebar */
.parameters-section {
  width: 300px;
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(30px);
  position: fixed;
  top: 180px;
  left: 0px;
}

/* Back Button Container */
.back-button-container {
  position: absolute;
  top: 20px;
  left: 10;
  z-index: 5;
}

.back-button-icon {
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
}

.back-button-icon:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

.back-button-icon svg {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  display: block;
}

.parameters-title {
  color: white;
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 24px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  text-align: center;
  border-bottom: 2px solid rgba(255, 255, 255, 0.2);
  padding-bottom: 12px;
  opacity: 0.8;
}


.parameter-group {
  margin-bottom: 20px;
}

.parameter-label {
  display: block;
  color: white;
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 14px;
}

.segmentation-select {
  width: 100%;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.segmentation-select:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.segmentation-select:focus {
  outline: none;
  border-color: #08B6E0;
  box-shadow: 0 0 0 3px rgba(8, 182, 224, 0.2);
}

.segmentation-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.segmentation-select option {
  background: #1a1a1a;
  color: white;
}

.method-hint {
  margin-top: 8px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.5;
}

.method-hint strong {
  color: #08B6E0;
}

.dropdown {
  width: 70%;
}

.analyze-button,
.reset-button {
  width: 70%;
  margin-top: 8px;
  font-weight: bold;
}

/* Main Content Area - Right Side */
.main-content-area {
  flex: 1;
  min-height: 500px;
}

.content-header {
  text-align: center;
  margin-bottom: 40px;
}

.content-header .title {
  font-size: 48px;
  margin-bottom: 10px;
}

.content-header .subtitle {
  font-size: 32px;
  margin-bottom: 20px;
}


/* Status Area */
.status-area {
  height: 225px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 32px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  text-align: center;
}

.status-message {
  margin-top: -30px;
  color: white;
}

.status-message h3 {
  font-size: 28px;
  margin-bottom: 16px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.status-message p {
  font-size: 18px;
  line-height: 1.6;
  opacity: 0.9;
  margin-bottom: 20px;
}

.config-summary {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  margin: 20px 0;
  text-align: left;
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 16px;
}

.config-item:last-child {
  border-bottom: none;
}

.title {
  color: white;
  font-size: 64px;
  margin-top: 200px;
  margin-bottom: 10px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  font-weight: 700;
}

.subtitle {
  color: white;
  font-size: 60px;
  margin-bottom: 10px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  font-weight: 500;
}



.plant-info {
  margin-top: 40px;
}

.plant-description {
  color: white;
  font-size: 24px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  margin: 20px 0;
}

.details-content {
  color: white;
  font-size: 18px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  max-width: 600px;
  margin: 0 auto;
  text-align: left;
}

.details-content ul {
  margin: 20px 0;
  padding-left: 20px;
}

.details-content li {
  margin: 8px 0;
  line-height: 1.5;
}

/* Loading Progress Indicator Styles */
.loading-section {
  margin-top: -30px;
  color: white;
}

.loading-section h3 {
  font-size: 28px;
  margin-bottom: 16px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.progress-container {
  position: relative;
  width: 100%;
  height: 20px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-bar {
  position: relative;
  height: 100%;
  width: 100%;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(to right, #4ade80, #22c55e);
  border-radius: 10px;
  transition: width 0.3s ease-in-out;
  min-width: 0%;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 14px;
  font-weight: bold;
  color: white;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  z-index: 1;
}

/* Responsive design */

/* Large screens (1440px and above) */
@media (min-width: 1440px) {
  .content {
    max-width: 1600px;
  }
  
  .parameters-section {
    width: 320px;
  }
}

/* Medium-large screens (1200px - 1024px) */
@media (max-width: 1200px) {
  .content {
    max-width: 100%;
    padding: 0 20px;
  }
  
  .content-layout {
    gap: 20px;
  }
  
  .parameters-section {
    width: 280px;
    padding: 20px;
  }
  
  .title {
    font-size: 56px;
  }
  
  .subtitle {
    font-size: 52px;
  }
}

/* Tablets (1024px and below) */
@media (max-width: 1024px) {
  .content-layout {
    flex-direction: column;
    gap: 24px;
  }
  
  .parameters-section {
    position: static;
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
    top: auto;
    left: auto;
  }
  
  .back-button-container {
    position: relative;
    top: 0;
    left: 0;
    margin-bottom: 10px;
  }
  
  .content {
    padding-top: 100px;
  }
  
  .title {
    font-size: 48px;
    margin-top: 150px;
  }
  
  .subtitle {
    font-size: 44px;
  }
  
  .content-header .title {
    font-size: 42px;
  }
  
  .content-header .subtitle {
    font-size: 32px;
  }
  
  .background-image {
    background-attachment: scroll;
  }
  
  .back-button-container {
    position: relative;
    top: 0;
    left: 0;
    margin-bottom: 10px;
  }
}

/* Medium tablets and small laptops (900px - 768px) */
@media (max-width: 900px) {
  .title {
    font-size: 42px;
    margin-top: 120px;
  }
  
  .subtitle {
    font-size: 38px;
  }
  
  .parameters-section {
    padding: 18px;
  }
  
  .parameters-title {
    font-size: 22px;
  }
  
  .content-header .title {
    font-size: 38px;
  }
  
  .content-header .subtitle {
    font-size: 28px;
  }
  
  .status-message h3 {
    font-size: 24px;
  }
  
  .status-message p {
    font-size: 16px;
  }
}

/* Mobile devices (768px and below) */
@media (max-width: 768px) {
  .app-content {
    padding: 15px;
  }
  
  .content {
    padding-top: 80px;
  }
  
  .title {
    font-size: 36px;
    margin-top: 100px;
    margin-bottom: 8px;
  }
  
  .subtitle {
    font-size: 32px;
    margin-bottom: 8px;
  }
  
  .parameters-section {
    padding: 16px;
    border-radius: 12px;
  }
  
  .parameters-title {
    font-size: 20px;
    margin-bottom: 20px;
  }
  
  .parameter-group {
    margin-bottom: 16px;
  }
  
  .dropdown {
    width: 100%;
  }
  
  .analyze-button,
  .reset-button {
    width: 100%;
  }
  
  .content-layout {
    gap: 20px;
  }
  
  .main-content-area {
    width: 100%;
  }
  
  .content-header .title {
    font-size: 32px;
  }
  
  .content-header .subtitle {
    font-size: 24px;
  }
  
  .status-area {
    padding: 24px;
    height: auto;
    min-height: 200px;
  }
  
  .status-message {
    margin-top: 0;
  }
  
  .status-message h3 {
    font-size: 22px;
  }
  
  .status-message p {
    font-size: 15px;
  }
  
  .plant-description {
    font-size: 20px;
  }
  
  .details-content {
    font-size: 16px;
    max-width: 100%;
  }
  
  .config-summary {
    padding: 16px;
  }
  
  .config-item {
    font-size: 14px;
  }
  
  .back-button-container {
    top: -45px;
  }
  
  .back-button-icon {
    width: 36px;
    height: 36px;
    padding: 6px;
  }
  
  .back-button-icon svg {
    width: 20px;
    height: 20px;
  }
}

/* Small mobile devices (480px and below) */
@media (max-width: 480px) {
  .app-content {
    padding: 10px;
  }
  
  .content {
    padding-top: 60px;
  }
  
  .title {
    font-size: 28px;
    margin-top: 80px;
  }
  
  .subtitle {
    font-size: 24px;
  }
  
  .parameters-section {
    padding: 14px;
  }
  
  .parameters-title {
    font-size: 18px;
    margin-bottom: 16px;
  }
  
  .parameter-label {
    font-size: 13px;
  }
  
  .content-header .title {
    font-size: 28px;
  }
  
  .content-header .subtitle {
    font-size: 20px;
  }
  
  .status-area {
    padding: 20px;
  }
  
  .status-message h3 {
    font-size: 20px;
  }
  
  .status-message p {
    font-size: 14px;
  }
  
  .plant-description {
    font-size: 18px;
  }
  
  .details-content {
    font-size: 14px;
  }
  
  .config-item {
    font-size: 13px;
    padding: 6px 0;
  }
  
  .progress-text {
    font-size: 12px;
  }
  
  .segmentation-select {
    font-size: 13px;
    padding: 8px 10px;
  }
}

/* Extra small devices (360px and below) */
@media (max-width: 360px) {
  .title {
    font-size: 24px;
    margin-top: 60px;
  }
  
  .subtitle {
    font-size: 20px;
  }
  
  .parameters-section {
    padding: 12px;
  }
  
  .parameters-title {
    font-size: 16px;
  }
  
  .content-header .title {
    font-size: 24px;
  }
  
  .content-header .subtitle {
    font-size: 18px;
  }
  
  .status-message h3 {
    font-size: 18px;
  }
  
  .status-message p {
    font-size: 13px;
  }
}

</style>